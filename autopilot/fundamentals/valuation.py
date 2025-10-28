
import os, json, numpy as np, pandas as pd
PROC="/workspace/data/processed"
def _load_json(p): 
    return json.load(open(p)) if os.path.exists(p) else {}
def fair_value(symbol: str, snapshot: dict | None=None) -> dict:
    f = _load_json(os.path.join(PROC, f"{symbol}_fundamentals.json"))
    p = os.path.join(PROC, f"{symbol}_prices.parquet")
    close = None
    if os.path.exists(p):
        try:
            df = pd.read_parquet(p).sort_values("Date")
            close = float(df["Close"].iloc[-1])
        except Exception: pass
    sector = f.get("sector")
    eps = f.get("trailingEps")
    pe_peer = None
    if snapshot is None:
        snapshot = _load_json(os.path.join(PROC,"_sector_snapshot.json"))
    if snapshot:
        pe_peer = snapshot.get("sector_median_pe",{}).get(sector) or snapshot.get("sector_median_pe",{}).get("Unknown")
    # نموذج PE نسبي
    fv_pe = float(eps*pe_peer) if (eps not in (None,0) and pe_peer not in (None,0)) else None
    # Gordon-lite (على EPS كنـائب للتوزيع) — تبسيط
    g, r = 0.05, 0.11
    fv_gordon = float(eps*(1+g)/(r-g)) if (eps not in (None,0) and r>g) else None
    # مركّب بسيط: متوسط المتاح
    vals=[v for v in [fv_pe, fv_gordon] if isinstance(v,(int,float)) and v==v and v>0]
    fv_comp = float(np.mean(vals)) if vals else None
    upside = float(fv_comp/close - 1.0) if (fv_comp and close) else None
    out={"symbol":symbol,"asof": str(pd.Timestamp.utcnow().date()),"close":close,
         "sector":sector,"fv_pe":fv_pe,"fv_gordon":fv_gordon,"fv_comp":fv_comp,"upside":upside}
    json.dump(out, open(os.path.join(PROC, f"{symbol}_valuation.json"),"w"), ensure_ascii=False, indent=2, default=lambda x: None)
    return out
