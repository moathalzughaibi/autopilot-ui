import os, hmac, hashlib, subprocess, time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

LOG  = "/workspace/data/logs/webhook_pull.log"
ENV  = "/workspace/secrets/webhook.env"
REPO = "/workspace/data"

# --- load secret (GITHUB_WEBHOOK_SECRET=...) ---
if os.path.exists(ENV):
    for ln in open(ENV, encoding="utf-8"):
        ln = ln.strip()
        if ln and "=" in ln and not ln.startswith("#"):
            k, v = ln.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

APP_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "change_me")

app = FastAPI()

def _log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def _verify_sig(sig_header: str, body: bytes) -> bool:
    if not sig_header or not sig_header.startswith("sha256="):
        return False
    sent = sig_header.split("=", 1)[1]
    mac  = hmac.new(APP_SECRET.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, sent)

def _run(cmd: str) -> str:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    _log(f"$ {cmd}\n{out.strip()}")
    return out

@app.get("/health")
def health():
    return PlainTextResponse("ok")
@app.post("/hook")
async def hook(request: Request):
    body = await request.body()
    event    = request.headers.get("X-GitHub-Event", "")
    delivery = request.headers.get("X-GitHub-Delivery", "")
    sig      = request.headers.get("X-Hub-Signature-256", "")

    _log(f"IN: event={event} delivery={delivery} len={len(body)}")

    # ping لا يحتاج توقيع
    if event == "ping":
        _log("pong")
        return PlainTextResponse("pong")

    # باقي الأحداث تتطلب توقيع صحيح
    if not _verify_sig(sig, body):
        _log("!! signature verification failed")
        raise HTTPException(401, "bad signature")

    if event == "push":
        _run(f"git -C {REPO} fetch origin")
        _run(f"git -C {REPO} pull --rebase --autostash origin main || true")
        _run(f"{REPO}/bin/throttled_timeline_sync.sh 5 || true")
        return PlainTextResponse("ok")

    _log(f"ignored event={event}")
    return PlainTextResponse("ignored")
