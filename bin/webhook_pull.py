import os, hmac, hashlib, json, subprocess, time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

LOG = "/workspace/data/logs/webhook_pull.log"
APP_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

app = FastAPI()

def _log(msg:str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG,"a",encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def _verify(signature_header:str, body:bytes)->bool:
    # GitHub: X-Hub-Signature-256: sha256=...
    if not APP_SECRET:
        _log("WARN: no secret set, skipping verification")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    sent = signature_header.split("=",1)[1]
    calc = hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent, calc)

@app.post("/hook")
async def hook(req: Request):
    body = await req.body()
    sig  = req.headers.get("X-Hub-Signature-256", "")
    ev   = req.headers.get("X-GitHub-Event", "")
    _log(f"EVENT={ev} len={len(body)}")

    if not _verify(sig, body):
        _log("ERROR: signature verification failed")
        raise HTTPException(status_code=401, detail="bad signature")

    try:
        # سحب آخر تغيير وتشغيل مزامنة التايملاين (بخنق داخلي لو حاب لاحقًا)
        out1 = subprocess.check_output(
            ["bash","-lc","cd /workspace/data && git pull --rebase --autostash origin main"],
            stderr=subprocess.STDOUT, text=True
        )
        _log("git pull:\n" + out1[-4000:])

        # تشغيل المزامنة (لو كانت عندك)
        run_timeline = "/workspace/data/bin/throttled_timeline_sync.sh"
        if os.path.exists(run_timeline):
            out2 = subprocess.check_output([run_timeline,"30"], stderr=subprocess.STDOUT, text=True)
            _log("timeline:\n" + out2[-4000:])
    except subprocess.CalledProcessError as e:
        _log("ERROR during pull/sync:\n" + e.output[-4000:])

    return PlainTextResponse("ok")
