
import os, json, pandas as pd, numpy as np
from datetime import datetime, timezone
PROC="/workspace/data/processed"

def _j(path, default=None):
    try:
        return json.load(open(path,"r",encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def _safe_last_close(sym):
    for name in (f"{sym}_features.parquet", f"{sym}_prices.parquet"):
        p=os.path.join(PROC, name)
        if os.path.exists(p):
            df=pd.read_parquet(p).sort_values("Date")
            if "Close" in df.columns and len(df):
                return float(df["Close"].iloc[-1])
    return None

def _fmt_num(x, nd=2):
    if x is None or x!=x: return None
    return float(round(x, nd))

def build_daily_report(symbols):
    rows=[]
    for s in symbols:
        dec   = _j(os.path.join(PROC, f"{s}_decision.json"), {})
        rules = _j(os.path.join(PROC, f"{s}_rules_metrics.json"), {})
        val   = _j(os.path.join(PROC, f"{s}_valuation.json"), {})
        sha   = _j(os.path.join(PROC, f"{s}_shariah.json"), {})
        alrt  = _j(os.path.join(PROC, f"{s}_alerts.json"), {"alerts":[]})
        mtf   = _j(os.path.join(PROC, f"{s}_mtf.json"), {})

        close = _safe_last_close(s)
        fv    = val.get("fair_value")
        under = None
        if fv is not None and close:
            under = (fv/close) - 1.0

        rows.append({
            "Symbol": s,
            "Close": _fmt_num(close,2),
            "Decision": dec.get("decision"),
            "Stop": _fmt_num(dec.get("stop"),2),
            "Take": _fmt_num(dec.get("take"),2),
            "MTF": _fmt_num(mtf.get("composite"),2),
            "FairValue": _fmt_num(fv,2),
            "Undervaluation%": _fmt_num(under*100,2) if under is not None else None,
            "Shariah": sha.get("class","UNKNOWN"),
            "Alerts": len(alrt.get("alerts",[])),
            "RulesCAGR%": _fmt_num((rules.get("cagr") or 0)*100,2) if rules else None,
            "MaxDD": _fmt_num(rules.get("maxdd"),3) if rules else None,
        })

    df = pd.DataFrame(rows)
    asof = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    csv_path  = os.path.join(PROC, "daily_report.csv")
    html_path = os.path.join(PROC, "daily_report.html")

    df.to_csv(csv_path, index=False)

    # HTML بسيط وأنيق
    style = '''
    <style>
      body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;padding:16px}
      h1{margin:0 0 12px 0;font-size:20px}
      .meta{color:#555;margin-bottom:14px}
      table{border-collapse:collapse;width:100%}
      th,td{border:1px solid #ddd;padding:8px;font-size:13px}
      th{background:#f7f7f7;text-align:left}
      tr:nth-child(even){background:#fafafa}
    </style>
    '''
    table = df.to_html(index=False, na_rep="—")
    html = f"{style}<h1>Daily Report</h1><div class='meta'>As of: {asof}</div>{table}"
    open(html_path,"w",encoding="utf-8").write(html)

    # إشارة صغيرة للداشبورد
    open(os.path.join(PROC,"_last_report.json"),"w",encoding="utf-8").write(
        json.dumps({"asof":asof,"rows":len(df)}, ensure_ascii=False, indent=2)
    )
    return {"csv": csv_path, "html": html_path, "rows": len(df), "asof": asof}
