import os, glob, json
import pandas as pd

BASE="/workspace/data"
PROC=f"{BASE}/processed"
STOR=f"{BASE}/storage"

def list_symbols():
    files=glob.glob(f"{PROC}/*_prices.parquet")
    syms=[os.path.basename(p).replace("_prices.parquet","") for p in files]
    return sorted(syms)

def load_prices(sym):
    p=f"{PROC}/{sym}_prices.parquet"
    df=pd.read_parquet(p).copy()
    # وحّد الأسماء إن كانت مثل Close_2010.SR
    ren={c:c.split("_")[0] for c in df.columns if c!="Date" and "_" in c}
    if ren: df=df.rename(columns=ren)
    return df.sort_values("Date").reset_index(drop=True)

def load_features(sym):
    p=f"{PROC}/{sym}_features.parquet"
    if not os.path.exists(p): return pd.DataFrame()
    return pd.read_parquet(p).sort_values("Date").reset_index(drop=True)

def save_features(sym, df):
    p=f"{PROC}/{sym}_features.parquet"
    df.to_parquet(p, index=False)
    return p

def save_anomalies(sym, df):
    out=f"{STOR}/anomalies/{sym}.parquet"
    df.to_parquet(out, index=False)
    return out
