import os, re, json, time, hashlib, subprocess, httpx
from datetime import datetime, timezone
from pathlib import Path

# --- تحميل الأسرار ---
ENV="/workspace/secrets/notion.env"
if os.path.exists(ENV):
    for ln in open(ENV, encoding="utf-8"):
        ln=ln.strip()
        if ln and "=" in ln and not ln.startswith("#"):
            k,v=ln.split("=",1); os.environ.setdefault(k.strip(), v.strip())

TOKEN   = os.environ["NOTION_TOKEN"]
DB_TASK = os.environ["DB_TASKS"]  # قاعدة الـTasks في Notion

BASE   = "https://api.notion.com/v1"
NV     = os.environ.get("NOTION_VERSION","2022-06-28")
HDRS   = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": NV, "Content-Type":"application/json"}

OUTDIR = Path("/workspace/data/processed/notion")
OUTDIR.mkdir(parents=True, exist_ok=True)
STATE  = OUTDIR / "timeline_state.json"

# خريطة أسماء الحقول (عدّل لو عندك أسماء مختلفة في Notion)
PROPS_MAP = {
    "name":    "Name",
    "type":    "Type",
    "status":  "Status",
    "date":    "Date",
    "summary": "Summary",
    "hash":    "Hash",
}

def _now_iso():
    return datetime.now(timezone.utc).isoformat()

def _sha1(text:str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def _load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"pushed": []}

def _save_state(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")

def _create_page(payload:dict):
    r = httpx.post(f"{BASE}/pages", headers=HDRS, json=payload, timeout=60.0)
    if r.status_code >= 300:
        raise RuntimeError(f"Notion create failed: {r.status_code} {r.text[:300]}")
    return r.json()

def _props(name, typ, status, date_iso, summary, hash_):
    # يشكّل خصائص الصفحة وفق PROPS_MAP
    return {
        PROPS_MAP["name"]:    { "title":     [ { "text": { "content": name[:200] } } ] },
        PROPS_MAP["type"]:    { "select":    { "name": typ } },
        PROPS_MAP["status"]:  { "select":    { "name": status } },
        PROPS_MAP["date"]:    { "date":      { "start": date_iso } },
        PROPS_MAP["summary"]: { "rich_text": [ { "text": { "content": summary[:2000] } } ] },
        PROPS_MAP["hash"]:    { "rich_text": [ { "text": { "content": hash_ } } ] },
    }

def collect_session_reports():
    items=[]
    for p in sorted(Path("/workspace/data").glob("Session_Report_*.md")):
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # تاريخ من الاسم إن أمكن
        m = re.search(r"(\d{4}-\d{2}-\d{2})", p.name)
        d = f"{m.group(1)}T00:00:00Z" if m else _now_iso()
        title = f"Session {p.name}"
        h = _sha1("session|" + p.name + "|" + txt[:2000])
        items.append({
            "name": title,
            "type": "Session",
            "status": "Captured",
            "date": d,
            "summary": txt[:1900],
            "hash": h,
        })
    return items

def collect_logs_tail(max_lines=200):
    items=[]
    logs = sorted(Path("/workspace/data/logs").glob("*.log"))
    for lf in logs[-5:]:  # آخر 5 لوجات فقط
        try:
            tail = "\n".join(lf.read_text(encoding="utf-8", errors="ignore").splitlines()[-max_lines:])
        except Exception:
            continue
        d = _now_iso()
        title = f"Log tail: {lf.name}"
        h = _sha1("log|" + lf.name + "|" + tail[:2000])
        items.append({
            "name": title,
            "type": "Log",
            "status": "Captured",
            "date": d,
            "summary": tail[:1900],
            "hash": h,
        })
    return items

def collect_git_commits(n=20):
    items=[]
    try:
        out = subprocess.check_output(
            ["bash","-lc","cd /workspace/data && git log -n %d --pretty=format:'%%h|%%ad|%%s' --date=iso" % n],
            text=True, stderr=subprocess.STDOUT
        )
        lines = [ln.strip().strip("'").strip() for ln in out.splitlines() if ln.strip()]
        for ln in lines:
            parts = ln.split("|", 2)
            if len(parts) != 3: 
                continue
            hsh, dt, msg = parts
            title = f"Git: {hsh} {msg[:120]}"
            d = dt if re.match(r"\d{4}-\d{2}-\d{2}", dt) else _now_iso()
            h = _sha1("git|" + hsh)
            items.append({
                "name": title,
                "type": "Git",
                "status": "Captured",
                "date": d,
                "summary": msg[:1900],
                "hash": h,
            })
    except Exception as e:
        # لو git غير مهيأ، تجاهل
        pass
    return items

def push_items(items):
    st = _load_state()
    pushed = set(st.get("pushed") or [])
    new_count = 0
    for it in items:
        if it["hash"] in pushed:
            continue
        payload = {
            "parent": { "database_id": DB_TASK },
            "properties": _props(it["name"], it["type"], it["status"], it["date"], it["summary"], it["hash"])
        }
        _create_page(payload)
        pushed.add(it["hash"])
        new_count += 1
        time.sleep(0.3)  # تلطيف المعدل
    st["pushed"] = list(pushed)
    _save_state(st)
    print(f"PUSHED_TIMELINE={new_count}")

def main():
    items = []
    items += collect_session_reports()
    items += collect_logs_tail()
    items += collect_git_commits()
    push_items(items)

if __name__ == "__main__":
    main()
