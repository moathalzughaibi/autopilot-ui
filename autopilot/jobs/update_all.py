
import os, json, pandas as pd, yfinance as yf
import yaml

# --- Optional modules guarded ---
try:
    from autopilot.pipe.anomalies import detect as anomalies_detect
except Exception:
    anomalies_detect = None

from autopilot.pipe.liquidity import compute_liquidity
from autopilot.signals.score import score_symbol
from autopilot.pipe.flow import compute_flow
from autopilot.signals.mtf import compute_mtf
from autopilot.backtest.policy import run_backtest
from autopilot.events.cases import compute_cases
from autopilot.engine.rules import decide_today
from autopilot.backtest.rules_bt import run_rules_backtest
from autopilot.alerts.risk import compute_risk_alerts
from autopilot.fundamentals.fetch import fetch_fundamentals
from autopilot.fundamentals.sector import build_sector_snapshot
from autopilot.fundamentals.valuation import fair_value
from autopilot.fundamentals.earnings import compute_earnings
from autopilot.compliance.shariah import classify as shariah_classify
from autopilot.trade.paper import daily_run as paper_daily_run
from autopilot.news.rss import fetch_news

PROC = "/workspace/data/processed"
os.makedirs(PROC, exist_ok=True)

SYMS = []
symlist = "/workspace/data/symbols.txt"
if os.path.exists(symlist):
    SYMS = [s.strip() for s in open(symlist, encoding="utf-8") if s.strip()]
if not SYMS:
    SYMS = ["2010.SR","1120.SR","7010.SR"]

def fetch_prices(sym: str, retries: int = 3, wait: float = 2.0):
    import time
    last_ok = f"{PROC}/{sym}_prices.parquet"
    df=None
    err=None
    for i in range(retries):
        try:
            df = yf.download(sym, period="max", interval="1d", auto_adjust=True, progress=False)
            if df is not None and len(df)>0:
                break
        except Exception as e:
            err=e
        time.sleep(wait)
    if df is None or len(df)==0:
        # fallback إلى الملف السابق إن وجد
        if Path(last_ok).exists():
            print(f"prices   : {sym} Fallback → {last_ok}")
            return last_ok, len(pd.read_parquet(last_ok))
        # وإلا نرجّع إطارًا فارغًا لكن ما نكسر البايبلاين
        print(f"prices   : {sym} ERR: {err}")
        import pandas as _pd
        df = _pd.DataFrame(columns=["Date","Open","High","Low","Close","Volume"])
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = ["_".join([c for c in tup if c]) for tup in df.columns.to_list()]
    df.index = pd.to_datetime(df.index); df.index.name = "Date"
    df = df.reset_index().drop_duplicates(subset=["Date"]).sort_values("Date")
    ren = {c: c.split("_")[0] for c in df.columns if c!="Date" and "_" in c}
    df = df.rename(columns=ren)
    out = f"{PROC}/{sym}_prices.parquet"
    df.to_parquet(out, index=False)
    print(f"prices   : {sym} {len(df)} → {out}")
    return out

def main():
    # 0) Fundamentals first pass (so sector snapshot can use all symbols)
    for s in SYMS:
        try:
            fetch_prices(s)
        except Exception as e:
            print("prices   :", s, "ERR:", e)

    for s in SYMS:
        try:
            fetch_fundamentals(s)
        except Exception as e:
            print("fundamentals:", s, "ERR:", e)

    # sector snapshot (once)
    try:
        snapshot = build_sector_snapshot(SYMS)
        print("sector   : snapshot built")
    except Exception as e:
        snapshot = {}
        print("sector   : ERR:", e)

    # 1) Per-symbol pipeline
    for s in SYMS:
        # features / liquidity
        try:
            compute_liquidity(s)
            fpath = f"{PROC}/{s}_features.parquet"
            if os.path.exists(fpath):
                print(f"features : {s} → {fpath}")
            else:
                print(f"features : {s} OK")
        except Exception as e:
            print("features :", s, "ERR:", e)

        # anomalies (optional module)
        if anomalies_detect is not None:
            try:
                anomalies_detect(s)
                print("events   :", s, "OK")
            except Exception as e:
                print("events   :", s, "ERR:", e)

        # scoring
        try:
            print(score_symbol(s))
        except Exception as e:
            print("score    :", s, "ERR:", e)

        # flow
        try:
            fl = compute_flow(s)
            print("flow     :", s, "→", fl.get("class"), "conf", fl.get("confidence"))
        except Exception as e:
            print("flow     :", s, "ERR:", e)

        # MTF
        try:
            mtf = compute_mtf(s)
            print("mtf      :", s, "→", mtf)
        except Exception as e:
            print("mtf      :", s, "ERR:", e)

        # cases (big up/down events)
        try:
            compute_cases(s)
            compute_earnings(s)
            print("cases    :", s, "OK")
        except Exception as e:
            print("cases    :", s, "ERR:", e)

        # backtest (policy)
        try:
            bt_p, bt_j, m = run_backtest(s)
            print(f"backtest : {s} → CAGR={m.get('cagr')}  MaxDD={m.get('maxdd')}")
        except Exception as e:
            print("backtest :", s, "ERR:", e)

        # decision today (rules)
        try:
            d = decide_today(s)
            print("decision :", s, "→", d.get("decision"))
        except Exception as e:
            print("decision :", s, "ERR:", e)

        # rules backtest (v1)
        try:
            cfg = yaml.safe_load(open("/workspace/data/autopilot/config/rules.yaml","r",encoding="utf-8"))
        except Exception:
            cfg = {}
        try:
            rbp, rbj, rm = run_rules_backtest(s, cfg)
            print(f"rules-bt : {s} → CAGR={rm.get('cagr')}  MaxDD={rm.get('maxdd')}")
        except Exception as e:
            print("rules-bt :", s, "ERR:", e)

        # risk alerts
        try:
            al = compute_risk_alerts(s)
            print("alerts   :", s, "→", len(al.get("alerts", [])))
        except Exception as e:
            print("alerts   :", s, "ERR:", e)

        # valuation + shariah (use built snapshot)
        try:
            fv = fair_value(s, snapshot)
            print("valuation:", s, "→", fv.get("fv_comp"))
        except Exception as e:
            print("valuation:", s, "ERR:", e)
        try:
            sh = shariah_classify(s)
            print("shariah  :", s, "→", sh.get("status"))
        except Exception as e:
            print("shariah  :", s, "ERR:", e)

    # 2) Paper trading (all symbols)
    try:
        res = paper_daily_run(SYMS)
        print("paper-trading :", res)
    except Exception as e:
        print("paper-trading : ERR", e)

if __name__ == "__main__":
    main()


# --- END PIPELINE ---
try:
    import json, pandas as pd, time, os
    PROC = "/workspace/data/processed"
    os.makedirs(PROC, exist_ok=True)
    summary = {
        "asof": str(pd.Timestamp.utcnow()),
        "symbols": SYMS,
    }
    with open(f"{PROC}/_last_update.json","w",encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
except Exception as _e:
    pass


# === Daily Report (appended) ===
try:
    from autopilot.reports.daily import build_daily_report as _build_daily_report_
    rp = _build_daily_report_(SYMS)
    print(f"report   : {rp['csv']} | rows={rp['rows']}")
except Exception as e:
    print("report   : ERR", e)



# ### AUTO_BACKTEST_SUMMARY ###
try:
    import os, glob, json, pandas as _pd
    PROC = "/workspace/data/processed"
    rows = []
    for f in glob.glob(os.path.join(PROC, "*_rules_metrics.json")):
        j = json.load(open(f))
        sym = os.path.basename(f).split("_")[0]
        rows.append({"symbol": sym,
                     "Rules_CAGR": j.get("CAGR"),
                     "Rules_MaxDD": j.get("MaxDD"),
                     "Rules_Vol":  j.get("Volatility") or j.get("Vol")})
    _pd.DataFrame(rows).to_csv(os.path.join(PROC, "backtest_summary.csv"), index=False)
    print("backtests : summary rebuilt ->", os.path.join(PROC, "backtest_summary.csv"))
except Exception as e:
    print("backtests : summary ERR", e)
