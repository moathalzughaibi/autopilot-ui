import os, hmac, hashlib, json, subprocess, time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

APP_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "change_me")  # بدّلها لاحقًا بنفس السر في GitHub
LOG = "/workspace/data/logs/webhook_pull.log"

app = FastAPI()

def _log(msg:str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG,"a",encoding="utf-8") as f: f.write(f"[{ts}] {msg}\n")

def _verify_sig(signature_header:str, body:bytes)->bool:
    # GitHub يرسل: X-Hub-Signature-256: sha256=...
    if not signature_header or not signature_header.startswith("sha256="): return False
    sent = signature_header.split("=",1)[1]
    mac  = hmac.new(APP_SECRET.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sent)

def _run(cmd):
    return subprocess.check_output(["bash","-lc",cmd], text=True, stderr=subprocess.STDOUT)

@app.post("/hook", response_class=PlainTextResponse)
async def hook(req: Request):
    body = await req.body()
    sig  = req.headers.get("X-Hub-Signature-256","")
    ev   = req.headers.get("X-GitHub-Event","")
    if not _verify_sig(sig, body):
        _log("WARN: bad signature"); raise HTTPException(401, "bad signature")

    # اسحب فقط على push/merge
    if ev not in ("push","pull_request"):
        _log(f"IGNORE event {ev}"); return "ignored"

    try:
        _log("== PULL start ==")
        _run("cd /workspace/data && git fetch origin && git rev-parse HEAD > /tmp/old_head && git rev-parse origin/main > /tmp/new_head && if [ \"$(cat /tmp/old_head)\" != \"$(cat /tmp/new_head)\" ]; then git pull --rebase --autostash origin main; changed=1; else changed=0; fi; echo CHANGED=$changed")
        # إعادة تشغيل الداشبورد فقط لو فيه تغييرات
        changed = 0
        with open("/workspace/data/CHANGED_FLAG","r") as f:
            pass
    except FileNotFoundError:
        pass  # أول مرّة
    except Exception:
        pass

    # احسب هل تغيّر HEAD فعلاً
    changed_flag = 0
    try:
        old_head = open("/tmp/old_head").read().strip()
        new_head = open("/tmp/new_head").read().strip()
        changed_flag = int(old_head != new_head)
    except Exception:
        changed_flag = 1  # اعتبرها تغيّرت كافتراض آمن

    if changed_flag:
        try:
            # أعد تشغيل الداشبورد
            _run("/workspace/data/bin/stop_dash.sh 8891 || true")
            _run("/workspace/data/bin/start_dash.sh 8891")
            # سجّل في Notion Timeline (بدون خنق)
            _run("source /workspace/data/.venv/bin/activate || true; python /workspace/data/bin/notion_timeline_sync.py || true")
            _log("PULL+RESTART+TIMELINE done")
        except subprocess.CalledProcessError as e:
            _log(f"ERR on restart/timeline: {e.output[-400:]}")
            raise HTTPException(500, "restart error")
    else:
        _log("No change; skipped restart.")

    return "ok"
