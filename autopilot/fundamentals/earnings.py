
import os, json, pandas as pd, yfinance as yf
PROC="/workspace/data/processed"

def compute_earnings(symbol: str) -> dict:
    out = {"symbol":symbol, "asof":str(pd.Timestamp.utcnow().date()), "events":[]}
    try:
        tk = yf.Ticker(symbol)
        # yfinance يعيد أحيانًا calendar أو earnings_dates حسب الرمز
        cal = getattr(tk, "calendar", None)
        if isinstance(cal, pd.DataFrame) and not cal.empty:
            # نحاول استخراج Earnings Date أو Earnings Call Date
            dates = []
            for k in ["Earnings Date", "Earnings Call Date", "Ex-Dividend Date"]:
                if k in cal.index:
                    v = cal.loc[k].dropna()
                    for d in v.values:
                        try:
                            dates.append(pd.to_datetime(d).date())
                        except Exception:
                            pass
            dates = sorted(set(dates))
        else:
            # محاولة ثانية: earnings_dates مع نافذة قريبة
            try:
                ed = tk.get_earnings_dates(limit=8)
                dates = sorted([pd.to_datetime(d).date() for d in ed.index])
            except Exception:
                dates = []
        # خزّن
        for d in dates:
            out["events"].append({"date": str(d), "type":"earnings"})
    except Exception:
        pass
    p = os.path.join(PROC, f"{symbol}_earnings.json")
    with open(p,"w",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2)
    return out
