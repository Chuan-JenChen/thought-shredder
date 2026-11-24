import base64
import hashlib
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Header, HTTPException, Request

from .bot import handle
from .db import init_db

log = logging.getLogger("bot")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="水電記帳機器人", lifespan=lifespan)


@app.get("/")
def health() -> dict:
    return {"status": "ok"}


def verify(body: bytes, signature: str | None) -> bool:
    secret = os.getenv("LINE_CHANNEL_SECRET", "")
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature)


def reply(token: str, text: str) -> None:
    access = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not access:
        log.warning("LINE_CHANNEL_ACCESS_TOKEN 未設定，略過回覆：%s", text)
        return
    httpx.post(
        "https://api.line.me/v2/bot/message/reply",
        headers={"Authorization": f"Bearer {access}"},
        json={"replyToken": token, "messages": [{"type": "text", "text": text[:5000]}]},
        timeout=10,
    )


@app.post("/callback")
async def callback(request: Request, x_line_signature: str | None = Header(None)):
    body = await request.body()
    if not verify(body, x_line_signature):
        raise HTTPException(400, "invalid signature")
    for ev in json.loads(body).get("events", []):
        if ev.get("type") != "message" or ev["message"].get("type") != "text":
            continue
        src = ev.get("source", {})
        owner = src.get("groupId") or src.get("roomId") or src.get("userId", "unknown")
        reply(ev["replyToken"], handle(owner, ev["message"]["text"]))
    return {"ok": True}
