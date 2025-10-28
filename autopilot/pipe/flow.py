
import os, json, numpy as np, pandas as pd

PROC = "/workspace/data/processed"

def _safe_div(a, b):
    with np.errstate(divide='ignore', invalid='ignore'):
        x = np.true_divide(a, b)
        x[~np.isfinite(x)] = np.nan
    return x

def _rolling_sum(s, w):
    return s.rolling(int(w), min_periods=int(w)).sum()

def compute_flow(symbol: str, cmf_win: int = 20, mfi_win: int = 14, z_win: int = 60):
    p = os.path.join(PROC, f"{symbol}_prices.parquet")
    if not os.path.exists(p):
        raise FileNotFoundError(p)

    df = pd.read_parquet(p).copy()
    if "Date" not in df.columns:
        raise ValueError("Date column missing in prices")

    # وحّد أسماء الأعمدة لو كانت Close_XXXX
    ren = {c: c.split("_")[0] for c in df.columns if c!="Date" and "_" in c}
    df = df.rename(columns=ren)
    df = df.sort_values("Date").reset_index(drop=True)

    need = {"Close","High","Low","Volume"}
    if not need.issubset(df.columns):
        raise ValueError(f"Missing columns: {need - set(df.columns)}")

    # 1) OBV
    ch = df["Close"].diff().fillna(0.0)
    sign = np.where(ch>0, 1, np.where(ch<0, -1, 0))
    df["OBV"] = (sign * df["Volume"].fillna(0)).cumsum()

    # 2) CMF (Chaikin Money Flow)
    mfm = _safe_div((df["Close"]-df["Low"]) - (df["High"]-df["Close"]), (df["High"]-df["Low"]))
    mfm = mfm.fillna(0.0).clip(-1,1)
    mfv = mfm * df["Volume"].fillna(0)
    cmf = _safe_div(_rolling_sum(mfv, cmf_win), _rolling_sum(df["Volume"].fillna(0), cmf_win))
    df["CMF"] = cmf

    # 3) MFI (14)
    tp = (df["High"] + df["Low"] + df["Close"]) / 3.0
    dm = tp * df["Volume"].fillna(0)
    pos = np.where(tp > tp.shift(1), dm, 0.0)
    neg = np.where(tp < tp.shift(1), dm, 0.0)
    pos_r = _rolling_sum(pd.Series(pos), mfi_win)
    neg_r = _rolling_sum(pd.Series(neg), mfi_win)
    mfr = _safe_div(pos_r, neg_r.replace(0, np.nan))
    df["MFI"] = 100 - (100 / (1 + mfr))

    # 4) Dollar Volume + Z-Score
    df["dollar_vol"] = df["Close"] * df["Volume"]
    dv_ma = df["dollar_vol"].rolling(z_win, min_periods=z_win).mean()
    dv_sd = df["dollar_vol"].rolling(z_win, min_periods=z_win).std()
    df["DV_Z"] = (df["dollar_vol"] - dv_ma) / dv_sd

    # 5) تصنيف السيولة (بسيط وواضح)
    last = df.iloc[-1]
    cmf_last = float(last.get("CMF", np.nan))
    dvz_last = float(last.get("DV_Z", np.nan))
    mfi_last = float(last.get("MFI", np.nan))

    status = "NEUTRAL"
    if cmf_last > 0.05 and dvz_last > 1.0:  # تدفّق إيجابي فوق المتوسط
        status = "INFLOW"
    elif cmf_last < -0.05 and dvz_last < -1.0:  # خروج واضح
        status = "OUTFLOW"

    # ثقة مبسطة 0..1
    conf = min(1.0, max(0.0, abs(dvz_last)/3.0))
    if status == "INFLOW" and mfi_last > 50: conf = min(1.0, conf + 0.15)
    if status == "OUTFLOW" and mfi_last < 50: conf = min(1.0, conf + 0.15)

    # حفظ النتائج
    flow_cols = ["Date","OBV","CMF","MFI","dollar_vol","DV_Z"]
    out_parq = os.path.join(PROC, f"{symbol}_flow.parquet")
    df[flow_cols].to_parquet(out_parq, index=False)

    out_json = os.path.join(PROC, f"{symbol}_flow.json")
    js = {
        "symbol": symbol,
        "date": str(last["Date"]),
        "status": status,
        "cmf": cmf_last,
        "dv_z": dvz_last,
        "mfi": mfi_last,
        "confidence": float(conf),
        "params": {"cmf_win": cmf_win, "mfi_win": mfi_win, "z_win": z_win},
    }
    with open(out_json,"w") as f:
        json.dump(js, f, indent=2)

    return {"parquet": out_parq, "json": out_json, "status": status, "confidence": float(conf)}
