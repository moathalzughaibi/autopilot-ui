import os, pandas as pd, httpx

ENV="/workspace/secrets/notion.env"
if os.path.exists(ENV):
    for ln in open(ENV, encoding="utf-8"):
        ln=ln.strip()
        if ln and "=" in ln and not ln.startswith("#"):
            k,v=ln.split("=",1); os.environ.setdefault(k.strip(), v.strip())

TOKEN  = os.environ["NOTION_TOKEN"]
DB_G   = os.environ["DB_GLOSSARY"]
DB_V   = os.environ["DB_VARIABLES"]
DB_T   = os.environ["DB_TASKS"]
OUTDIR = "/workspace/data/processed/notion"
os.makedirs(OUTDIR, exist_ok=True)

NOTION_VERSION = os.environ.get("NOTION_VERSION", "2022-06-28")
BASE = "https://api.notion.com/v1"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

def _cell(p):
    t = p.get("type")
    if t == "title":        return "".join(x.get("plain_text","") for x in p.get("title",[]))
    if t == "rich_text":    return "".join(x.get("plain_text","") for x in p.get("rich_text",[]))
    if t == "select":       return (p.get("select") or {}).get("name","")
    if t == "multi_select": return ",".join(x.get("name","") for x in (p.get("multi_select") or []))
    if t == "checkbox":     return bool(p.get("checkbox"))
    if t == "number":       return p.get("number")
    if t == "date":         return (p.get("date") or {}).get("start") or ""
    return ""

def _db_query_all(dbid:str):
    url = f"{BASE}/databases/{dbid}/query"
    payload = {}
    with httpx.Client(timeout=30.0) as c:
        while True:
            r = c.post(url, headers=headers, json=payload)
            r.raise_for_status()
            data = r.json()
            yield from data.get("results", [])
            if not data.get("has_more"):
                break
            payload = {"start_cursor": data.get("next_cursor")}

def read_db_to_df(dbid:str) -> pd.DataFrame:
    rows=[]
    for item in _db_query_all(dbid):
        props = item.get("properties", {})
        row   = {"id": item.get("id")}
        for k,v in props.items():
            try:
                row[k] = _cell(v)
            except Exception:
                row[k] = ""
        rows.append(row)
    return pd.DataFrame(rows)

def pull():
    read_db_to_df(DB_G).to_csv(f"{OUTDIR}/glossary.csv",  index=False)
    read_db_to_df(DB_V).to_csv(f"{OUTDIR}/variables.csv", index=False)
    read_db_to_df(DB_T).to_csv(f"{OUTDIR}/tasks.csv",     index=False)
    print("OK: notion → CSVs @", OUTDIR)

if __name__ == "__main__":
    pull()
