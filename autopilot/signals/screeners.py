import os

import os, json, pandas as pd, numpy as np
PROC = "/workspace/data/processed"

def _load_flow(sym: str):
    p = os.path.join(PROC, f"{sym}_flow.parquet")
    if os.path.exists(p):
        try:
            df = pd.read_parquet(p)
            if "Date" in df.columns: df["Date"] = pd.to_datetime(df["Date"])
            return df.sort_values("Date").reset_index(drop=True)
        except Exception: pass
    return pd.DataFrame()

def _load_mtf(sym: str):
    p = os.path.join(PROC, f"{sym}_mtf.json")
    if os.path.exists(p):
        try: return json.load(open(p))
        except Exception: pass
    return {"daily":np.nan,"weekly":np.nan,"monthly":np.nan,"composite":np.nan}

def _row_from_feat(sym: str, df: pd.DataFrame) -> dict:
    row = {"Symbol": sym}
    if df.empty or "Date" not in df.columns: return row

    df = df.sort_values("Date").reset_index(drop=True)
    last = df.iloc[-1]
    g = lambda name, default=np.nan: float(last[name]) if name in last and pd.notna(last[name]) else default

    close, sma20, sma50 = g("Close"), g("SMA_20", g("Close")), g("SMA_50", g("Close"))
    rsi, macd, sig = g("RSI_14", 50), g("MACD", 0), g("MACD_SIG", 0)
    atr = g("ATR_14", np.nan); eq = g("eq_curve", np.nan); bh = g("bh_curve", np.nan)

    def pct(col, n):
        if col not in df.columns or len(df)<(n+1): return np.nan
        a = df[col].iloc[-(n+1)]; b = df[col].iloc[-1]
        return (b/a - 1.0) * 100.0 if a and pd.notna(a) else np.nan

    ch_5d, ch_1m, ch_3m = pct("Close",5), pct("Close",21), pct("Close",63)

    last_52w = df.tail(252)
    if not last_52w.empty:
        hi52, lo52 = float(np.nanmax(last_52w["Close"])), float(np.nanmin(last_52w["Close"]))
    else:
        hi52 = lo52 = np.nan
    near52w = (close/hi52 - 1.0)*100.0 if hi52 and pd.notna(hi52) else np.nan

    # Flow
    flow = _load_flow(sym); liq_label, liq_z = "NA", np.nan
    if not flow.empty:
        f_last = flow.iloc[-1]; liq_z = float(f_last.get("DV_Z", np.nan)); cmf = float(f_last.get("CMF", np.nan))
        if cmf > 0.05 and liq_z > 1.0: liq_label = "INFLOW"
        elif cmf < -0.05 and liq_z < -1.0: liq_label = "OUTFLOW"
        else: liq_label = "NEUTRAL"

    # MTF
    mtf = _load_mtf(sym)
    mtf_d, mtf_w, mtf_m, mtf_comp = mtf.get("daily"), mtf.get("weekly"), mtf.get("monthly"), mtf.get("composite")
    bias = "UP" if (pd.notna(mtf_comp) and mtf_comp>=2.0) else ("DOWN" if pd.notna(mtf_comp) and mtf_comp<=1.0 else "NEUTRAL")

    momo_score = int(close > sma20) + int(rsi>50) + int(macd>sig)
    breakout50 = int(close > sma50)
    atr_pct = (atr/close*100.0) if atr and close else np.nan

    row.update({
        "Date": last["Date"], "Close": close,
        "RSI_14": rsi, "SMA_20": sma20, "SMA_50": sma50, "ATR_%": atr_pct,
        "MomScore(0-3)": momo_score, "Break50": breakout50,
        "1W%": ch_5d, "1M%": ch_1m, "3M%": ch_3m, "Near52W%": near52w,
        "LiqZ": liq_z, "Liquidity": liq_label,
        "MTF_D": mtf_d, "MTF_W": mtf_w, "MTF_M": mtf_m, "MTF_Score": mtf_comp, "Bias": bias,
        "EqCurve": eq, "BuyHold": bh,
    })
    return row

def build_overview(features_map: dict) -> pd.DataFrame:
    rows = []
    for sym, df in features_map.items():
        try: rows.append(_row_from_feat(sym, df))
        except Exception: rows.append({"Symbol": sym})
    out = pd.DataFrame(rows)
    if not out.empty and "Date" in out.columns:
        out = out.sort_values(["Bias","Liquidity","MTF_Score","1M%"], ascending=[True, True, False, False])
    return out
