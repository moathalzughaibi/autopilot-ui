import os, json
import pandas as pd
import numpy as np

PROC = "/workspace/data/processed"

def score_symbol(symbol: str) -> str:
    p_feat = os.path.join(PROC, f"{symbol}_features.parquet")
    df = pd.read_parquet(p_feat).sort_values("Date").reset_index(drop=True)
    last = df.iloc[-1]

    sma_ok  = float(last.get("Close", np.nan)) > float(last.get("SMA_20", np.inf))
    rsi_ok  = float(last.get("RSI_14", 50)) > 50
    macd_ok = float(last.get("MACD", 0)) > float(last.get("MACD_SIG", 0))
    liq_ok  = float(last.get("liq_pulse", 0)) > 0

    parts = [sma_ok, rsi_ok, macd_ok, liq_ok]
    score = int(sum(parts))  # 0..4
    signal = "BUY" if score >= 3 else ("WATCH" if score==2 else "FLAT")
    reasons = []
    if sma_ok:  reasons.append("Close>SMA20")
    if rsi_ok:  reasons.append("RSI>50")
    if macd_ok: reasons.append("MACD>Signal")
    if liq_ok:  reasons.append("Liquidity>0")

    out = os.path.join(PROC, f"{symbol}_latest_signal.json")
    with open(out, "w") as f:
        json.dump({
            "symbol": symbol,
            "signal": signal,
            "score": score,
            "reasons": reasons,
            "date": str(last["Date"]),
            "close": float(last["Close"])
        }, f, ensure_ascii=False, indent=2)
    return out
