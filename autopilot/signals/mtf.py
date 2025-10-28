
import os, json, pandas as pd, numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD

PROC = "/workspace/data/processed"

def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    d = df.copy()
    d["Date"] = pd.to_datetime(d["Date"])
    d = d.set_index("Date").resample(rule, label="right", closed="right").agg({
        "Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"
    }).dropna(subset=["Open","High","Low","Close"]).reset_index()
    return d

def _add_feats(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["SMA_20"] = d["Close"].rolling(20).mean()
    d["SMA_50"] = d["Close"].rolling(50).mean()
    rsi = RSIIndicator(close=d["Close"], window=14)
    mac = MACD(close=d["Close"], window_slow=26, window_fast=12, window_sign=9)
    d["RSI_14"]   = rsi.rsi()
    d["MACD"]     = mac.macd()
    d["MACD_SIG"] = mac.macd_signal()
    return d

def _score_last(d: pd.DataFrame) -> int:
    if d.empty: return 0
    x = d.iloc[-1].to_dict()
    score = int(float(x.get("Close", np.nan)) > float(x.get("SMA_20", np.inf))) \
          + int(float(x.get("RSI_14", 50)) > 50) \
          + int(float(x.get("MACD", 0)) > float(x.get("MACD_SIG", 0)))
    return int(score)

def compute_mtf(symbol: str):
    p = os.path.join(PROC, f"{symbol}_prices.parquet")
    if not os.path.exists(p): 
        raise FileNotFoundError(p)
    df = pd.read_parquet(p).copy()

    # توحيد أسماء الأعمدة إن كانت Close_XXXX
    ren = {c:c.split("_")[0] for c in df.columns if c!="Date" and "_" in c}
    df = df.rename(columns=ren).sort_values("Date").reset_index(drop=True)

    # Daily (D), Weekly (W-FRI), Monthly (M)
    D = _add_feats(df)
    W = _add_feats(_resample_ohlcv(df, "W-FRI"))
    M = _add_feats(_resample_ohlcv(df, "ME"))

    d_s = _score_last(D)
    w_s = _score_last(W)
    m_s = _score_last(M)

    # مركّب بسيط (0..3) بأوزان: 0.5D, 0.3W, 0.2M
    composite = round(0.5*d_s + 0.3*w_s + 0.2*m_s, 2)

    out = {
        "symbol": symbol,
        "asof": str(D["Date"].iloc[-1]) if not D.empty else None,
        "daily": d_s, "weekly": w_s, "monthly": m_s,
        "composite": composite
    }
    with open(os.path.join(PROC, f"{symbol}_mtf.json"), "w") as f:
        json.dump(out, f, indent=2)
    return out
