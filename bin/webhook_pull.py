import os, hmac, hashlib, subprocess, time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

LOG  = "/workspace/data/logs/webhook_pull.log"
ENV  = "/workspace/secrets/webhook.env"          # يحتوي: GITHUB_WEBHOOK_SECRET=...
REPO = "/workspace/data"                          # مسار الريبو على البود

# --- load secret ---
if os.path.exists(ENV):
    for ln in open(ENV, encoding="utf-8"):
        ln = ln.strip()
        if ln and "=" in ln and not ln.startswith("#"):
            k, v = ln.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
APP_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "change_me").strip()

app = FastAPI()

def _log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")

def _verify(signature_header: str, body: bytes) -> bool:
    # GitHub يرسل: X-Hub-Signature-256: sha256=...
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    sent = signature_header.split("=",1)[1]
    mac  = hmac.new(APP_SECRET.encode(), msg=body, digestmod=hashlib.sha256).hexdigest()
    return hmac.compare_digest(sent, mac)

@app.get("/health")
def health():
    return PlainTextResponse("ok")

@app.post("/hook")
async def hook(request: Request):
    body = await request.body()
    event = request.headers.get("X-GitHub-Event","").strip()
    sig   = request.headers.get("X-Hub-Signature-256","")

    # ping لا يحتاج توقيع
    if event == "ping":
        _log("ping ✓")
        return PlainTextResponse("pong")

    # نتحقق للتحديثات الحساسة (push / pull_request)
    if event in ("push", "pull_request"):
        if not APP_SECRET or APP_SECRET == "change_me":
            raise HTTPException(status_code=400, detail="secret_not_set")
        if not _verify(sig, body):
            _log("signature ❌")
            raise HTTPException(status_code=401, detail="bad_signature")

        _log(f"event={event} → pulling repo…")
        cmds = [
            ["git","-C",REPO,"fetch","origin"],
            ["git","-C",REPO,"checkout","-B","main","--track","origin/main"],
            ["git","-C",REPO,"pull","--rebase","--autostash","--allow-unrelated-histories","origin","main"],
        ]
        for c in cmds:
            try:
                out = subprocess.check_output(c, stderr=subprocess.STDOUT, text=True, timeout=120)
                _log("$ " + " ".join(c)); _log(out.strip())
            except subprocess.CalledProcessError as e:
                _log(f"CMD FAIL: {' '.join(c)}\n{e.output}")
                raise HTTPException(status_code=500, detail="git_failed")
        _log("pull ✓")
        return PlainTextResponse("ok")

    # أي حدث آخر نتجاهله بهدوء
    _log(f"ignored event={event}")
    return PlainTextResponse("ignored")
