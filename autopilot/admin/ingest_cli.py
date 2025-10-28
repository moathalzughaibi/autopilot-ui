import os, json, pandas as pd, argparse
BASE="/workspace/data"; PROC=f"{BASE}/processed"; os.makedirs(PROC, exist_ok=True)
def _write_json(p, obj): json.dump(obj, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def ingest_profiles(csv_path:str):
    df = pd.read_csv(csv_path).fillna("")
    for _,r in df.iterrows():
        out = {"symbol": r["symbol"],"name": r.get("name") or None,
               "listing_date": str(pd.to_datetime(r.get("listing_date")).date()) if r.get("listing_date") else None,
               "exchange": r.get("exchange") or None,"sector": r.get("sector") or None,
               "industry": r.get("industry") or None,"country": r.get("country") or None}
        _write_json(os.path.join(PROC, f"{r['symbol']}_profile.json"), out)

def ingest_fin_q(csv_path:str):
    df = pd.read_csv(csv_path)
    df["period_end"] = pd.to_datetime(df["period_end"], errors="coerce")
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("period_end").reset_index(drop=True)
        g.to_parquet(os.path.join(PROC, f"{sym}_fin_quarterly.parquet"), index=False)
        if "fiscal_y" in g.columns:
            agg = g.groupby("fiscal_y").agg({
                "revenue":"sum","operating_income":"sum","net_income":"sum",
                "eps":"mean","assets":"last","liabilities":"last","equity":"last",
                "cfo":"sum","capex":"sum","dividends_paid":"sum"}).reset_index()
            agg.to_parquet(os.path.join(PROC, f"{sym}_fin_yearly.parquet"), index=False)
            lasty = agg.iloc[-1].to_dict() if len(agg) else {}
            _write_json(os.path.join(PROC, f"{sym}_fin_summary.json"), {"symbol":sym,"last_year":lasty})

def ingest_dividends(csv_path:str):
    df = pd.read_csv(csv_path)
    for col in ("ex_date","record_date","pay_date"):
        if col in df.columns: df[col] = pd.to_datetime(df[col], errors="coerce")
    for sym, g in df.groupby("symbol"):
        g = g.sort_values(["ex_date","pay_date"]).reset_index(drop=True)
        g.to_parquet(os.path.join(PROC, f"{sym}_dividends.parquet"), index=False)
        _write_json(os.path.join(PROC, f"{sym}_dividends_summary.json"),
                    {"symbol":sym,"last":g.tail(5).to_dict(orient="records")})

def ingest_corp_actions(csv_path:str):
    df = pd.read_csv(csv_path)
    if "action_date" in df.columns:
        df["action_date"] = pd.to_datetime(df["action_date"], errors="coerce")
    for sym, g in df.groupby("symbol"):
        g = g.sort_values("action_date").reset_index(drop=True)
        g.to_parquet(os.path.join(PROC, f"{sym}_corp_actions.parquet"), index=False)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles")
    ap.add_argument("--financials_q")
    ap.add_argument("--dividends")
    ap.add_argument("--corp_actions")
    args = ap.parse_args()
    if args.profiles:      ingest_profiles(args.profiles)
    if args.financials_q:  ingest_fin_q(args.financials_q)
    if args.dividends:     ingest_dividends(args.dividends)
    if args.corp_actions:  ingest_corp_actions(args.corp_actions)
    print("OK: ingest done")
