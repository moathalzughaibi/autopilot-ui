
import os, json, numpy as np, pandas as pd
from datetime import timedelta

PROC = "/workspace/data/processed"

def _zscore(s, win=60):
    r = s.rolling(win).mean()
    v = s.rolling(win).std(ddof=0)
    return (s - r) / v

def _forward_return(close, k):
    # (Close[t+k]/Close[t] - 1)
    return close.shift(-k) / close - 1.0

def _nearest_earnings_days(dates, earnings_df):
    if earnings_df is None or earnings_df.empty:
        return pd.Series([np.nan]*len(dates), index=dates.index if hasattr(dates,'index') else None)
    edates = pd.to_datetime(earnings_df.index)
    out = []
    for d in pd.to_datetime(dates):
        diff = (edates - d).days
        # أقرب تاريخ بالأيام (قيمة مطلقة مع الإشارة)
        if len(diff)==0: 
            out.append(np.nan)
        else:
            i = np.argmin(np.abs(diff))
            out.append(int(diff[i]))
    return pd.Series(out, index=getattr(dates,'index',None))

def compute_cases(symbol: str, pct_thresh: float = 5.0, z_thresh: float = 2.0,
                  vol_win: int = 60, z_win: int = 60):
    p = os.path.join(PROC, f"{symbol}_prices.parquet")
    if not os.path.exists(p):
        raise FileNotFoundError(p)

    df = pd.read_parquet(p).copy()
    ren = {c: c.split("_")[0] for c in df.columns if c!="Date" and "_" in c}
    df = df.rename(columns=ren).sort_values("Date").reset_index(drop=True)
    for col in ["Date","Close","High","Low","Open","Volume"]:
        if col not in df.columns:
            raise ValueError(f"Missing {col}")

    # عائد يومي + Zscore + حجم بالدولار وعامل السبَيك
    df["ret1"] = df["Close"].pct_change()
    df["zret"] = _zscore(df["ret1"], win=z_win)
    df["dollar_vol"] = df["Close"] * df["Volume"]
    mu = df["dollar_vol"].rolling(vol_win).mean()
    df["vol_spike"] = df["dollar_vol"] / mu

    # أحداث كبيرة: إمّا |ret|>=pct_thresh% أو |zret|>=z_thresh
    big_pct = df["ret1"].abs() >= (pct_thresh/100.0)
    big_z   = df["zret"].abs() >= z_thresh
    mask = big_pct | big_z

    ev = df.loc[mask, ["Date","ret1","zret","vol_spike","Close"]].copy()
    ev["type"] = np.where(ev["ret1"]>=0, "UP", "DOWN")

    # عوائد لاحقة
    for k in [1,5,10,20]:
        ev[f"fwd_{k}d"] = _forward_return(df["Close"], k).reindex(ev.index).values

    # قرب الأرباح (إن توفّر)
    earnings_df = None
    try:
        import yfinance as yf
        tk = yf.Ticker(symbol)
        # earnings_dates متاحة لبعض الرموز؛ fallback إن لم تتوفر
        if hasattr(tk, "earnings_dates"):
            ed = tk.earnings_dates
            earnings_df = ed if isinstance(ed, pd.DataFrame) and not ed.empty else None
    except Exception:
        earnings_df = None

    ev["earnings_days"] = _nearest_earnings_days(ev["Date"], earnings_df)

    # حفظ
    out_parq = os.path.join(PROC, f"{symbol}_cases.parquet")
    ev.to_parquet(out_parq, index=False)

    # ملخص سريع لـ fwd_5d
    summ = {
        "symbol": symbol,
        "n_events": int(len(ev)),
        "pct_thresh": float(pct_thresh),
        "z_thresh": float(z_thresh),
        "win_rate_5d": float(np.nanmean((ev["fwd_5d"]>0).astype(float))) if len(ev) else None,
        "avg_5d": float(np.nanmean(ev["fwd_5d"])) if len(ev) else None,
        "median_5d": float(np.nanmedian(ev["fwd_5d"])) if len(ev) else None,
    }
    out_json = os.path.join(PROC, f"{symbol}_cases_summary.json")
    with open(out_json,"w") as f: json.dump(summ, f, ensure_ascii=False)

    return {"path": out_parq, "summary": summ}
