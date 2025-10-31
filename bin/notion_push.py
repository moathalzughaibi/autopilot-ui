import os, json, httpx, hashlib
from datetime import datetime, timezone

# Load env file (key=value)
ENV="/workspace/secrets/notion.env"
if os.path.exists(ENV):
    for ln in open(ENV, encoding="utf-8"):
        ln=ln.strip()
        if ln and "=" in ln and not ln.startswith("#"):
            k,v=ln.split("=",1); os.environ.setdefault(k.strip(), v.strip())

TOKEN  = os.environ["NOTION_TOKEN"]
DB_T   = os.environ["DB_TASKS"]
BASE   = "https://api.notion.com/v1"
NV     = os.environ.get("NOTION_VERSION","2022-06-28")

HDRS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": NV,
    "Content-Type": "application/json",
}

def req(method, path, body=None):
    r = httpx.request(method, BASE+path, headers=HDRS, json=body, timeout=30)
    if r.status_code >= 300:
        raise RuntimeError(f"Notion API {method} {path} -> {r.status_code} {r.text[:300]}")
    return r.json()

def get_db_schema(dbid: str):
    meta = req("GET", f"/databases/{dbid}")
    props = meta.get("properties", {})
    m = {"title":None, "status":None, "type":None, "date":None, "summary":None, "tags":None, "url":None}
    for name, p in props.items():
        t = p.get("type")
        if t=="title"       and not m["title"]:   m["title"]=name
        elif t=="status"    and not m["status"]:  m["status"]=name
        elif t=="select"    and not m["type"]:    m["type"]=name
        elif t=="date"      and not m["date"]:    m["date"]=name
        elif t=="rich_text" and not m["summary"]: m["summary"]=name
        elif t=="multi_select" and not m["tags"]: m["tags"]=name
        elif t=="url"       and not m["url"]:     m["url"]=name
    return m

def _ensure_option(dbid, field_name, kind, value):
    # kind: "status" or "select"
    if not field_name or not value:
        return None
    meta = req("GET", f"/databases/{dbid}")
    prop = meta["properties"][field_name]
    if prop.get("type") != kind: return None
    key = "status" if kind=="status" else "select"
    opts = prop[key]["options"]
    for o in opts:
        if o["name"].lower()==value.lower():
            return {"name": o["name"]}
    # add option
    opts = opts + [{"name": value}]
    req("PATCH", f"/databases/{dbid}", {"properties": {field_name: {key: {"options": opts}}}})
    return {"name": value}

def create_page(dbid, mapping, title, summary=None, type_value=None, status_value=None, date_iso=None, tags=None, url=None):
    props={}
    if mapping["title"]:
        props[mapping["title"]]={"title":[{"type":"text","text":{"content":title[:200]}}]}
    if summary and mapping["summary"]:
        props[mapping["summary"]]={"rich_text":[{"type":"text","text":{"content":summary[:1800]}}]}
    if type_value and mapping["type"]:
        sel=_ensure_option(dbid, mapping["type"], "select", type_value)
        if sel: props[mapping["type"]]={"select": sel}
    if status_value and mapping["status"]:
        st=_ensure_option(dbid, mapping["status"], "status", status_value)
        if st: props[mapping["status"]]={"status": st}
    if date_iso and mapping["date"]:
        props[mapping["date"]]={"date":{"start": date_iso}}
    if tags and mapping["tags"]:
        props[mapping["tags"]]={"multi_select":[{"name":t[:80]} for t in tags[:10]]}
    if url and mapping["url"]:
        props[mapping["url"]]={"url": url}
    body={"parent":{"database_id":dbid}, "properties":props}
    return req("POST","/pages", body)

def push_session_report(md_path, dbid):
    txt=open(md_path,"r",encoding="utf-8",errors="ignore").read()
    name=os.path.basename(md_path)
    now=datetime.now(timezone.utc).isoformat()
    mapping=get_db_schema(dbid)
    return create_page(
        dbid=dbid, mapping=mapping,
        title=f"Session Report – {name}",
        summary=txt[:1800],
        type_value="Report",
        status_value="Done",
        date_iso=now,
        tags=["session","autopilot","report"]
    )

def push_error_event(event, dbid):
    # event: {source, when, message, solution}
    mapping=get_db_schema(dbid)
    title=f"Error – {event.get('source','system')}"
    summary=f"[{event.get('when')}] {event.get('message','')}\nSolution: {event.get('solution','')}"
    return create_page(
        dbid=dbid, mapping=mapping,
        title=title,
        summary=summary,
        type_value="Error",
        status_value="Open",
        date_iso=event.get("when"),
        tags=["error","autopilot"]
    )

def scan_logs_and_push(dbid, log_paths):
    cache="/workspace/data/logs/errors.ndjson"
    seen=set()
    if os.path.exists(cache):
        for ln in open(cache,"r",encoding="utf-8"):
            try:
                obj=json.loads(ln); seen.add(obj.get("fp"))
            except: pass
    KEY=("ERROR","ERR:","Traceback","Exception","failed","CRITICAL")
    pushed=0
    for p in log_paths:
        if not os.path.exists(p): continue
        lines=open(p,"r",encoding="utf-8",errors="ignore").read().splitlines()[-2000:]
        for i,ln in enumerate(lines):
            if any(k.lower() in ln.lower() for k in KEY):
                ctx="\n".join(lines[max(0,i-2):i+3])
                fp=hashlib.sha1(ctx.encode("utf-8","ignore")).hexdigest()[:16]
                if fp in seen: continue
                evt={
                    "source": os.path.basename(p),
                    "when": datetime.now(timezone.utc).isoformat(),
                    "message": ctx[:1500],
                    "solution": ""
                }
                push_error_event(evt, dbid)
                with open(cache,"a",encoding="utf-8") as f:
                    f.write(json.dumps({"fp":fp,"at":evt["when"]})+"\n")
                seen.add(fp); pushed+=1
    return pushed

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--db", default=DB_T)
    ap.add_argument("--push-session", nargs="*", default=[])
    ap.add_argument("--scan-logs", action="store_true")
    ap.add_argument("--logs", nargs="*", default=[
        "/workspace/data/logs/streamlit_8891.log",
        "/workspace/data/logs/inbox.log",
        "/workspace/data/logs/updater.log",
        "/workspace/data/logs/backup_daily.log",
        "/workspace/data/logs/git_sync.log",
        "/workspace/data/logs/notion_watcher.log",
    ])
    args=ap.parse_args()

    for p in args.push_session:
        if os.path.exists(p):
            push_session_report(p, args.db)

    if args.scan_logs:
        n=scan_logs_and_push(args.db, args.logs)
        print(f"PUSHED_ERRORS={n}")
