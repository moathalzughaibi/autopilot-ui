import os, sys, pandas as pd
from notion_client import Client

ENV="/workspace/secrets/notion.env"
if os.path.exists(ENV):
    for ln in open(ENV, encoding="utf-8"):
        if "=" in ln:
            k, v = ln.strip().split("=", 1)
            os.environ.setdefault(k, v)

TOKEN = os.environ["NOTION_TOKEN"]
DB_G = os.environ["DB_GLOSSARY"]
DB_V = os.environ["DB_VARIABLES"]
DB_T = os.environ["DB_TASKS"]

OUT = "/workspace/data/processed/notion"
os.makedirs(OUT, exist_ok=True)
cli = Client(auth=TOKEN)

def read_db(dbid):
    rows, cur = [], None
    while True:
        rsp = cli.databases.query(database_id=dbid, start_cursor=cur)
        for r in rsp.get("results", []):
            props = r["properties"]
            row = {"id": r["id"]}
            for k, p in props.items():
                t = p.get("type")
                row[k] = (
                    "".join(x["plain_text"] for x in p["title"]) if t == "title" else
                    "".join(x["plain_text"] for x in p["rich_text"]) if t == "rich_text" else
                    (p["select"]["name"] if p["select"] else "") if t == "select" else
                    ",".join(x["name"] for x in p["multi_select"]) if t == "multi_select" else
                    p["number"] if t == "number" else
                    (p["date"]["start"] if p["date"] else "") if t == "date" else
                    bool(p["checkbox"]) if t == "checkbox" else
                    str(p.get(t))
                )
            rows.append(row)
        if not rsp.get("has_more"):
            break
        cur = rsp.get("next_cursor")
    return pd.DataFrame(rows)

def pull():
    read_db(DB_G).to_csv(f"{OUT}/glossary.csv", index=False)
    read_db(DB_V).to_csv(f"{OUT}/variables.csv", index=False)
    read_db(DB_T).to_csv(f"{OUT}/tasks.csv", index=False)
    print("✅ Pull done. Files written to:", OUT)

if __name__ == "__main__":
    pull()
