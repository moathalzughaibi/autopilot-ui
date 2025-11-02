import os, hmac, hashlib, subprocess, time
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse

LOG="/workspace/data/logs/webhook_pull.log"
ENV="/workspace/secrets/webhook.env"
REPM="/workspace/data"

if os.path.exists(ENV):
    for ln= open(ENV, encoding="utf-8"