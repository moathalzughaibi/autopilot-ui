
import os, json, pandas as pd, numpy as np
from datetime import date, datetime
PROC="/workspace/data/processed"

def _json_default(o):
    if isinstance(o, (datetime, date)): return o.isoformat()
    if isinstance(o, (np.floating,)):   return float(o)
    if isinstance(o, (np.integer,)):    return int(o)
    return str(o)

def _wjson(p,obj): 
    json.dump(obj, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=2, default=_json_default)

def ingest_profiles(csv_path:str):
    df = pd.read_csv(csv_path).fillna("")
    for _,r in df.iterrows():
        out = {
            "symbol": r["symbol"],
            "name":   (r.get("name") or None),
            "listing_date": (pd.to_datetime(r.get("listing_date"), errors="coerce").date().isoformat()
                             if r.get("listing_date") else None),
            "exchange": r.get("exchange") or None,
            "sector":   r.get("sector") or None,
            "industry": r.get("industry") or None,
            "country":  r.get("country") or None
        }
        _wjson(os.path.join(PROC, f"{r['symbol']}_profile.json"), out)
    return "profiles"

def ingest_fin_q(csv_path:str):
    df = pd.read_csv(csv_path)
    if "period_end" in df: df["period_end"] = pd.to_datetime(df["period_end"], errors="coerce")
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("period_end").reset_index(drop=True)
        g.to_parquet(os.path.join(PROC, f"{sym}_fin_quarterly.parquet"), index=False)
        if "fiscal_y" in g.columns:
            agg = g.groupby("fiscal_y").agg({
                "revenue":"sum","operating_income":"sum","net_income":"sum",
                "eps":"mean","assets":"last","liabilities":"last","equity":"last",
                "cfo":"sum","capex":"sum","dividends_paid":"sum"
            }).reset_index()
            agg.to_parquet(os.path.join(PROC, f"{sym}_fin_yearly.parquet"), index=False)
            lasty = agg.iloc[-1].to_dict() if len(agg) else {}
            _wjson(os.path.join(PROC, f"{sym}_fin_summary.json"), {"symbol":sym,"last_year":lasty})
    return "financials_quarterly"

def ingest_dividends(csv_path:str):
    df = pd.read_csv(csv_path)
    for col in ("ex_date","record_date","pay_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for sym, g in df.groupby("symbol"):
        g = g.sort_values(["ex_date","pay_date"]).reset_index(drop=True)
        # نسخة قابلة للتسلسل (ISO strings للتواريخ)
        g2 = g.copy()
        for col in ("ex_date","record_date","pay_date"):
            if col in g2.columns:
                g2[col] = g2[col].dt.date.astype(str)
        g.to_parquet(os.path.join(PROC, f"{sym}_dividends.parquet"), index=False)
        _wjson(os.path.join(PROC, f"{sym}_dividends_summary.json"),
               {"symbol":sym,"last10":g2.tail(10).to_dict(orient="records")})
    return "dividends"

def ingest_corp_actions(csv_path:str):
    df = pd.read_csv(csv_path)
    if "action_date" in df.columns:
        df["action_date"] = pd.to_datetime(df["action_date"], errors="coerce")
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("action_date").reset_index(drop=True)
        g2 = g.copy()
        if "action_date" in g2.columns:
            g2["action_date"] = g2["action_date"].dt.date.astype(str)
        g.to_parquet(os.path.join(PROC, f"{sym}_corp_actions.parquet"), index=False)
        _wjson(os.path.join(PROC, f"{sym}_corp_actions_summary.json"),
               {"symbol":sym,"last":g2.tail(10).to_dict(orient="records")})
    return "corporate_actions"

def ingest_any(path:str):
    name = os.path.basename(path).lower()
    if   "profile"   in name: return ingest_profiles(path)
    elif "financial" in name: return ingest_fin_q(path)
    elif "dividend"  in name: return ingest_dividends(path)
    elif "corp" in name or "action" in name: return ingest_corp_actions(path)
    else:
        df = pd.read_csv(path, nrows=2)
        cols = set(c.lower() for c in df.columns)
        if "listing_date" in cols:  return ingest_profiles(path)
        if "period_end"  in cols:   return ingest_fin_q(path)
        if "ex_date"     in cols:   return ingest_dividends(path)
        if "action_date" in cols:   return ingest_corp_actions(path)
        raise ValueError("لم أتعرف على نوع الملف تلقائياً.")
