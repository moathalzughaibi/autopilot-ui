import os, re, json, time, hashlib, subprocess, httpx, pandas as pd
from datetime import datetime, timezone
from pathlib import Path

ENV="/workspace/secrets/notion.env"
if os.path.exists(ENV):
    for ln in open(ENV, encoding="utf-8"):
        ln=ln.strip()
        if ln and "=" in ln and not ln.startswith("#"):
            k,v=ln.split("=",1); os.environ.setdefault(k.strip(), v.strip())

TOKEN   = os.environ["NOTION_TOKEN"]
DB_TASK = os.environ["DB_TASKS"]        # سنستخدم Tasks كقاعدة "Project Timeline"
NV      = os.environ.get("NOTION_VERSION","2022-06-28")
BASE    = "https://api.notion.com/v1"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": NV,
    "Content-Type": "application/json",
}

STATE   = Path("/workspace/data/processed/notion/timeline_state.json")
STATE.parent.mkdir(parents=True, exist_ok=True)
state   = json.load(open(STATE)) if STATE.exists() else {"seen": {}}

def _sha1(txt:str)->str:
    return hashlib.sha1(txt.encode("utf-8","ignore")).hexdigest()

def _http(method, path, body=None):
    url = f"{BASE}{path}"
    with httpx.Client(timeout=60) as c:
        r = c.request(method, url, headers=HEADERS, json=body)
        if r.status_code >= 400:
            raise RuntimeError(f"{method} {path} -> {r.status_code} {r.text}")
        return r.json()

def db_properties(dbid:str)->dict:
    info = _http("GET", f"/databases/{dbid}")
    return info.get("properties", {})

def safe_page_create(dbid:str, title:str, props:dict, children=None):
    # اجلب خصائص القاعدة لتفعيل التوافق
    props_def = db_properties(dbid)
    # ابحث عن عمود العنوان (title)
    title_key = None
    for k,v in props_def.items():
        if v.get("type")=="title":
            title_key = k
            break
    if not title_key:
        title_key = "Name"  # احتياط اسم شائع

    notion_props = {
        title_key: {"title":[{"type":"text","text":{"content": title[:2000]}}]}
    }

    # مرّر فقط الخصائص الموجودة فعلاً بالقاعدة
    for k, v in (props or {}).items():
        if k not in props_def: 
            continue
        t = props_def[k].get("type")
        if t=="select" and isinstance(v, str):
            notion_props[k] = {"select":{"name": v}}
        elif t=="multi_select" and isinstance(v, (list,tuple)):
            notion_props[k] = {"multi_select":[{"name": x} for x in v]}
        elif t in ("rich_text","text") and isinstance(v, str):
            notion_props[k] = {"rich_text":[{"type":"text","text":{"content": v[:2000]}}]}
        elif t=="date":
            if isinstance(v, str):
                notion_props[k] = {"date":{"start": v}}
            elif isinstance(v, dict):
                notion_props[k] = {"date": v}
        elif t=="status" and isinstance(v, str):
            notion_props[k] = {"status":{"name": v}}
        elif t=="number" and isinstance(v,(int,float)):
            notion_props[k] = {"number": v}
        elif t=="checkbox" and isinstance(v,bool):
            notion_props[k] = {"checkbox": v}
        # غير ذلك: نتجاهله بهدوء

    body = {
        "parent": {"database_id": dbid},
        "properties": notion_props
    }
    if children:
        body["children"] = children
    return _http("POST","/pages", body)

def md_children_block(markdown_text:str):
    # نرسل المحتوى كفقرة واحدة مختصرة (Notion API لا يدعم Markdown كامل مباشرة)
    snippet = markdown_text if len(markdown_text)<=1800 else markdown_text[:1800]+"..."
    return [{"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content": snippet}}]}}]

# -------- مصادر الالتقاط --------
def collect_session_reports():
    out=[]
    for p in sorted(Path("/workspace/data").glob("Session_Report_*.md")):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        title = txt.splitlines()[0].strip() if txt.strip() else p.name
        ts = re.search(r"(\d{4}-\d{2}-\d{2})", p.name)
        dt = f"{ts.group(1)}T00:00:00Z" if ts else datetime.now(timezone.utc).isoformat()
        out.append({
            "kind":"Report",
            "title": title if title else "Session Report",
            "date": dt,
            "body": txt,
            "source": str(p)
        })
    return out

def collect_errors():
    out=[]
    # errors.ndjson (إن وجد)
    enf = Path("/workspace/data/logs/errors.ndjson")
    if enf.exists():
        for ln in enf.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                j = json.loads(ln)
                msg = j.get("message") or j.get("msg") or ""
                dt  = j.get("time") or j.get("ts") or datetime.now(timezone.utc).isoformat()
                out.append({"kind":"Error","title": f"Error: {msg[:60]}", "date": dt, "body": json.dumps(j, ensure_ascii=False, indent=2), "source": "errors.ndjson"})
            except Exception:
                pass
    # آخر 200 سطر من سجلات .log
    for logf in Path("/workspace/data/logs").glob("*.log"):
        tail = "\n".join(logf.read_text(encoding="utf-8", errors="ignore").splitlines()[-200:])
        if tail.strip():
            out.append({"kind":"ErrorLog","title": f"Log tail: {logf.name}", "date": datetime.now(timezone.utc).isoformat(), "body": tail, "source": str(logf)})
    return out

def collect_git_commits():
    out=[]
    try:
        raw = subprocess.check_output(
            ["bash","-lc",'cd /workspace/data && git log -n 20 --date=iso --pretty=format:"%h|%ad|%s"'],
            text=True, stderr=subprocess.STDOUT
        )
        for ln in raw.splitlines():
            if "|" not in ln: 
                continue
            h, dt, msg = ln.split("|",2)
            out.append({"kind":"Commit","title": f"Commit {h}: {msg[:80]}", "date": dt, "body": raw, "source": "git"})
    except Exception as e:
        out.append({"kind":"Commit","title":"Commit log unavailable","date": datetime.now(timezone.utc).isoformat(), "body": str(e), "source":"git"})
    return out

def dedup_key(item:dict)->str:
    base = f"{item['kind']}|{item['title']}|{item['date']}|{item.get('source','')}"
    return _sha1(base)

def push_items(items):
    pushed=0
    props_preview = []
    for it in items:
        k = dedup_key(it)
        if state["seen"].get(k): 
            continue
        # خصائص ودّية — تُستخدم إن كانت موجودة بقاعدة Tasks
        props = {
            "Type": it["kind"],                # select (إن وُجد)
            "Date": it["date"],                # date   (إن وُجد)
            "Status": "Logged",                # status (إن وُجد)
        }
        children = md_children_block(it.get("body",""))
        try:
            safe_page_create(DB_TASK, it["title"], props, children=children)
            state["seen"][k] = True
            pushed += 1
            props_preview.append(props)
        except Exception as e:
            # لو فشل، سجّل ولا توقف الدفعة
            err = f"[PUSH_ERR] {it['title']}: {e}"
            Path("/workspace/data/logs/notion_push_errors.log").write_text(
                (Path("/workspace/data/logs/notion_push_errors.log").read_text(encoding="utf-8", errors="ignore") if Path("/workspace/data/logs/notion_push_errors.log").exists() else "")
                + err + "\n",
                encoding="utf-8"
            )
    json.dump(state, open(STATE,"w"), ensure_ascii=False, indent=2)
    return pushed

def main():
    items = []
    items += collect_session_reports()
    items += collect_errors()
    items += collect_git_commits()
    # رتّب بحسب التاريخ (إن أمكن)
    def _key(x):
        try: return datetime.fromisoformat(x["date"].replace("Z","+00:00"))
        except: return datetime.now(timezone.utc)
    items = sorted(items, key=_key, reverse=False)
    n = push_items(items)
    print(f"PUSHED_TIMELINE={n}")

if __name__=="__main__":
    main()
