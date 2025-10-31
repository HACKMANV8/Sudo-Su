from __future__ import annotations

import time
from typing import Optional

import hmac
import base64
import json as _json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


JWT_SECRET = b"dev-secret"

router = APIRouter()


class TokenRequest(BaseModel):
    username: str
    password: str


@router.post("/auth/token")
async def token(req: TokenRequest) -> dict:
    if not (req.username == "dev" and req.password == "dev"):
        raise HTTPException(status_code=401, detail="invalid credentials")
    payload = {"sub": req.username, "role": "admin", "exp": int(time.time()) + 3600}
    body = base64.urlsafe_b64encode(_json.dumps(payload).encode()).rstrip(b"=")
    sig = base64.urlsafe_b64encode(hmac.new(JWT_SECRET, body, digestmod="sha256").digest()).rstrip(b"=")
    tok = body.decode() + "." + sig.decode()
    return {"access_token": tok, "token_type": "bearer"}


