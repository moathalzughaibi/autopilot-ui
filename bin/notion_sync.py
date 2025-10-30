import os, json, pandas as pd
from notion_client import Client

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

cli = Client(auth=TOKEN)

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

def _db_query(dbid, start_cursor=None):
    # مسار A: الطريقة الرسمية
    if hasattr(cli, "databases") and hasattr(cli.databases, "query"):
        if start_cursor:
            return cli.databases.query(database_id=dbid, start_cursor=start_cursor)
        return cli.databases.query(database_id=dbid)
    # مسار B: Low-level fallback
    body = {}
    if start_cursor: body["start_cursor"] = start_cursor
    # client.request متاح في 2.x — إن لم يكن، حاول _client.request
    req = getattr(cli, "request", None) or getattr(cli, "_client", None).request
    return req({"path": f"/v1/databases/{dbid}/query", "method": "post", "body": body})

def read_db(dbid:str) -> pd.DataFrame:
    rows=[]; cur=None
    while True:
        rsp = _db_query(dbid, start_cursor=cur)
        for r in rsp.get("results", []):
            props = r.get("properties", {})
            row = {"id": r.get("id")}
            for k,v in props.items():
                try: row[k] = _cell(v)
                except Exception: row[k] = ""
            rows.append(row)
        if not rsp.get("has_more"): break
        cur = rsp.get("next_cursor")
        if not cur: break
    return pd.DataFrame(rows)

def pull():
    read_db(DB_G).to_csv(f"{OUTDIR}/glossary.csv",  index=False)
    read_db(DB_V).to_csv(f"{OUTDIR}/variables.csv", index=False)
    read_db(DB_T).to_csv(f"{OUTDIR}/tasks.csv",     index=False)
    print("OK: notion → CSVs @", OUTDIR)

if __name__ == "__main__":
    pull()
