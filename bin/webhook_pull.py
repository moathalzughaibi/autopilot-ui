
import os, hmac, hashlib, subprocess, time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

LOG  = "/workspace/data/logs/webhook_pull.log"
ENV  = "/workspace/secrets/webhook.env"   # contains: GITHUB_WEBHOOK_SECRET=...
REPO = "/workspace/data"

def _log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def _load_secret() -> str:
    if os.path.exists(ENV):
        for ln in open(ENV, encoding="utf-8"):
            ln = ln.strip()
            if ln and "=" in ln and not ln.startswith("#"):
                k, v = ln.split("=", 1)
                if k.strip() == "GITHUB_WEBHOOK_SECRET":
                    return v.strip()
    return "change_me"

SECRET = _load_secret()

def _verify_sig(sig_header: str, body: bytes) -> None:
    if not sig_header or not sig_header.startswith("sha256="):
        raise HTTPException(status_code=401, detail="missing signature")
    sent = sig_header.split("=", 1)[1]
    calc = hmac.new(SECRET.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sent, calc):
        raise HTTPException(status_code=401, detail="bad signature")

def _git(cmd: str) -> str:
    p = subprocess.run(cmd, shell=True, cwd=REPO, text=True,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.stdout.strip()

app = FastAPI()

@app.get("/health")
def health():
    return PlainTextResponse("ok")

@app.post("/hook")
async def hook(request: Request):
    body  = await request.body()
    event = request.headers.get("X-GitHub-Event", "")
    sig   = request.headers.get("X-Hub-Signature-256", "")

    if event == "ping":
        _log("PING")
        return PlainTextResponse("pong")

    _verify_sig(sig, body)

    if event == "push":
        _log("PUSH: git pull")
        out = _git("git fetch --all && git reset --hard origin/main || true && git pull --rebase --autostash || true")
        _log(f"GIT:\n{out}")
        return PlainTextResponse("ok")

    _log(f"IGNORED event={event}")
    return PlainTextResponse("ignored")
