import os, hmac, hashlib, subprocess, time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

LOG  = "/workspace/data/logs/webhook_pull.log"
ENV  = "/workspace/secrets/webhook.env"          # يحتوي: GITHUB_WEBHOOK_SECRET=...
REPO = "/workspace/data"                          # مسار الريبو على البود

# --- تحميل السر من ENV ---
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

def _verify_sig(header_sig: str, body: bytes) -> bool:
    # نعتمد sha256 (هيدر: X-Hub-Signature-256)
    if not header_sig or not header_sig.startswith("sha256="):
        return False
    given = header_sig.split("=", 1)[1]
    mac   = hmac.new(APP_SECRET.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(given, mac)

@app.get("/health")
def health():
    _log("HEALTH ping")
    return PlainTextResponse("ok")

@app.post("/hook")
async def hook(request: Request):
    body  = await request.body()
    event = request.headers.get("X-GitHub-Event", "unknown")
    sig   = request.headers.get("X-Hub-Signature-256", "")

    # ping لا يحتاج توقيع
    if event == "ping":
        _log("PING received")
        return PlainTextResponse("pong")

    # تحقق التوقيع لباقي الأحداث
    if not _verify_sig(sig, body):
        _log(f"DENY invalid signature event={event}")
        raise HTTPException(status_code=403, detail="invalid signature")

    _log(f"OK event={event} -> git pull")
    try:
        out = subprocess.check_output(
            ["bash","-lc", f"cd {REPO} && git fetch origin && git pull --rebase --autostash origin main"],
            stderr=subprocess.STDOUT, text=True, timeout=120
        )
        _log("GIT:" + out[-500:])
    except subprocess.CalledProcessError as e:
        _log("GITERR:" + e.output[-500:])
        raise HTTPException(status_code=500, detail="git failed")

    return PlainTextResponse("ok")
