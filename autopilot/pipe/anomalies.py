import os, json
import pandas as pd
import numpy as np

PROC = "/workspace/data/processed"

def detect(symbol: str, ret_sigma: float = 2.0, vol_sigma: float = 2.0) -> str:
    p_feat = os.path.join(PROC, f"{symbol}_features.parquet")
    assert os.path.exists(p_feat), f"Missing features: {p_feat}"
    df = pd.read_parquet(p_feat).copy().sort_values("Date")

    events = []
    # قفز العائد
    mu, sd = df["ret"].rolling(60).mean(), df["ret"].rolling(60).std()
    z = (df["ret"] - mu) / (sd.replace(0, np.nan))
    for dt, val in df.loc[z.abs() >= ret_sigma, ["Date","ret"]].itertuples(index=False):
        events.append({"date": str(dt), "type": "RET_SPIKE", "score": float(val)})

    # قفز الحجم
    vmu, vsd = df["Volume"].rolling(60).mean(), df["Volume"].rolling(60).std()
    vz = (df["Volume"] - vmu) / (vsd.replace(0, np.nan))
    for dt, val in df.loc[vz >= vol_sigma, ["Date","Volume"]].itertuples(index=False):
        events.append({"date": str(dt), "type": "VOL_SPIKE", "score": float(val)})

    # تقاطعات SMA20/50
    cross = (df["SMA_20"] > df["SMA_50"]).astype(int).diff()
    for dt, c in df.loc[cross.abs()==1, ["Date","Close"]].itertuples(index=False):
        ev = "GOLDEN_CROSS" if c else "DEATH_CROSS"
        events.append({"date": str(dt), "type": ev, "score": float(c)})

    out = os.path.join(PROC, f"{symbol}_events.json")
    with open(out, "w") as f:
        json.dump({"symbol": symbol, "events": events[-200:]}, f, ensure_ascii=False, indent=2)
    return out
