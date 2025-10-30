
import os, pandas as pd
from notion_client import Client

ENV="/workspace/secrets/notion.env"
if os.path.exists(ENV):
    for ln in open(ENV, encoding="utf-8"):
        ln = ln.strip()
        if ln and "=" in ln and not ln.startswith("#"):
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

TOKEN  = os.environ["NOTION_TOKEN"]
DB_G   = os.environ["DB_GLOSSARY"]
DB_V   = os.environ["DB_VARIABLES"]
DB_T   = os.environ["DB_TASKS"]
OUTDIR = "/workspace/data/processed/notion"
os.makedirs(OUTDIR, exist_ok=True)

cli = Client(auth=TOKEN)

def _cell(p):
    t = p.get("type")
    if t == "title":        return "".join(x["plain_text"] for x in p["title"])
    if t == "rich_text":    return "".join(x["plain_text"] for x in p["rich_text"])
    if t == "select":       return (p.get("select") or {}).get("name","")
    if t == "multi_select": return ",".join(x["name"] for x in p.get("multi_select") or [])
    if t == "number":       return p.get("number")
    if t == "date":         return (p.get("date") or {}).get("start","")
    if t == "checkbox":     return bool(p.get("checkbox"))
    if t == "status":       return (p.get("status") or {}).get("name","")
    return str(p.get(t))

def read_db(dbid: str) -> pd.DataFrame:
    rows, cur = [], None
    while True:
        rsp = cli.databases.query(database_id=dbid, start_cursor=cur)
        for r in rsp.get("results", []):
            row = {"id": r["id"]}
            for k, prop in r["properties"].items():
                row[k] = _cell(prop)
            rows.append(row)
        if not rsp.get("has_more"): break
        cur = rsp.get("next_cursor")
    return pd.DataFrame(rows)

def pull():
    read_db(DB_G).to_csv(f"{OUTDIR}/glossary.csv",  index=False)
    read_db(DB_V).to_csv(f"{OUTDIR}/variables.csv", index=False)
    read_db(DB_T).to_csv(f"{OUTDIR}/tasks.csv",     index=False)
    print("✅ Notion pull ->", OUTDIR)

if __name__ == "__main__":
    pull()
