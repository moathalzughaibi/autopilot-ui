
import os, json, glob, pandas as pd, numpy as np
PROC = "/workspace/data/processed"

def _nanmedian(x):
    try: 
        return float(np.nanmedian(x)) if len(x) else np.nan
    except Exception:
        return np.nan

def build_sector_snapshot(*args, **kwargs):
    rows=[]
    for jf in glob.glob(os.path.join(PROC, "*_fundamentals.json")):
        try:
            rows.append(json.load(open(jf,"r",encoding="utf-8")))
        except Exception:
            pass
    out = {"asof": str(pd.Timestamp.utcnow().date()), "sectors":[]}
    if not rows:
        json.dump(out, open(os.path.join(PROC,"_sector_snapshot.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        return out

    df=pd.DataFrame(rows)
    for c in ["trailingPE","forwardPE","priceToBook","beta","marketCap"]:
        if c in df.columns:
            df[c]=pd.to_numeric(df[c], errors="coerce")

    sectors=[]
    for sec, g in df.groupby(df.get("sector", pd.Series(["Unknown"]*len(df)))):
        pe_stack = pd.concat([
            g["trailingPE"] if "trailingPE" in g else pd.Series(dtype=float),
            g["forwardPE"]  if "forwardPE"  in g else pd.Series(dtype=float)
        ], axis=1).stack().astype(float).values if len(g) else np.array([])
        pe_med = _nanmedian(pe_stack)
        pb_med = _nanmedian(g["priceToBook"].astype(float).values) if "priceToBook" in g else np.nan
        sectors.append({
            "sector": None if (pd.isna(sec) or sec=="") else str(sec),
            "n": int(len(g)),
            "median_pe": None if pd.isna(pe_med) else round(pe_med,2),
            "median_pb": None if pd.isna(pb_med) else round(pb_med,2),
        })
    out["sectors"]=sectors
    json.dump(out, open(os.path.join(PROC,"_sector_snapshot.json"),"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    return out
