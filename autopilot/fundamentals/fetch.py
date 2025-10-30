
import os
if os.path.exists("/workspace/data/flags/OFFLINE"):
    # وضع أوفلاين: لا نجلب من الإنترنت، ارمِ استثناء واضح
    raise RuntimeError("OFFLINE mode: network fetch disabled")


import os, json, pandas as pd, numpy as np, yfinance as yf
PROC="/workspace/data/processed"
def fetch_fundamentals(symbol: str) -> dict:
    info={}
    try:
        info = yf.Ticker(symbol).info or {}
    except Exception:
        info={}
    out = {
        "symbol": symbol,
        "asof": str(pd.Timestamp.utcnow().date()),
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "marketCap": info.get("marketCap"),
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "priceToBook": info.get("priceToBook"),
        "trailingEps": info.get("trailingEps"),
        "forwardEps": info.get("forwardEps"),
        "dividendYield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "enterpriseToEbitda": info.get("enterpriseToEbitda"),
    }
    p=os.path.join(PROC, f"{symbol}_fundamentals.json")
    json.dump(out, open(p,"w"), ensure_ascii=False, indent=2, default=lambda x: None)
    return out
