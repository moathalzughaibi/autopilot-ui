import os, hmac, hashlib, json, subprocess, time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

LOG = "/workspace/data/logs/webhook_pull.log"
ENV = "/workspace/secrets/webhook.env"

# load secret from /workspace/secrets/webhook.env  (line: GITHUB_WEBHOOK_SECRET=xxx)
if os.path.exists(ENV):
    for ln in open(ENV, encoding="utf-8"):
        ln=ln.strip()
        if ln and "=" in ln and not ln.startswith("#"):
            k,v=ln.split("=",1); os.environ.setdefault(k.strip(), v.strip())

APP_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "change_me")

app = FastAPI()

def _log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def _verify_sig(signature_header: str, body: bytes) -> bool:
    # GitHub header: X-Hub-Signature-256: sha256=<hexdigest>
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    sent = signature_header.split("=", 1)[1]
    mac  = hmac.new(APP_SECRET.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent, mac)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/hook", response_class=PlainTextResponse)
async def hook(request: Request):
    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    event = request.headers.get("X-GitHub-Event", "unknown")
    _log(f"INCOMING event={event}, len={len(raw)}")

    # allow "ping" without signature to simplify first test
    if event != "ping" and not _verify_sig(sig, raw):
        _log("BAD SIGNATURE")
        raise HTTPException(status_code=401, detail="bad signature")

    payload = {}
    try:
        payload = json.loads(raw or "{}")
    except Exception as e:
        _log(f"JSON error: {e}")

    if event == "ping":
        _log("PING ok")
        return "pong"

    if event == "push":
        # 1) pull latest code
        cmd_pull = ["bash","-lc","cd /workspace/data && git pull --rebase --autostash || true"]
        out_pull = subprocess.getoutput(" ".join(cmd_pull))
        _log(f"git pull ->\n{out_pull}")

        # 2) شغّل مزامنة التايملاين (مع خنق إن لزم)
        tl_cmd = ["bash","-lc","/workspace/data/bin/throttled_timeline_sync.sh 30 || true"]
        out_tl = subprocess.getoutput(" ".join(tl_cmd))
        _log(f"timeline sync ->\n{out_tl}")

        return "ok"

    _log(f"IGNORED event={event}")
    return "ignored"
