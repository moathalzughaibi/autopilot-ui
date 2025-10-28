
import os, json, time, feedparser, pandas as pd
PROC="/workspace/data/processed"

def _q(sym:str)->str:
    # استعلام بسيط: الرمز + سوق السعودية
    return f"{sym} site:news.google.com OR السعودية OR Saudi"

def fetch_news(symbol: str, max_items: int = 20) -> dict:
    q = _q(symbol)
    url = f"https://news.google.com/rss/search?q={q.replace(' ','%20')}&hl=ar&gl=SA&ceid=SA:ar"
    feed = feedparser.parse(url)
    out = {"symbol":symbol, "asof":str(pd.Timestamp.utcnow()), "items":[]}
    for e in feed.entries[:max_items]:
        out["items"].append({
            "title": e.get("title"),
            "link": e.get("link"),
            "published": e.get("published", e.get("updated","")),
            "source": (e.get("source") or {}).get("title")
        })
    p = os.path.join(PROC, f"{symbol}_news.json")
    json.dump(out, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    return out
