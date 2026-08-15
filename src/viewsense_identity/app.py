from __future__ import annotations

import base64
import json
import os
import secrets
import time
from pathlib import Path
from urllib.parse import parse_qs

import jwt
from fastapi import FastAPI, HTTPException, Request

from viewsense_common.settings import read_required, required

app = FastAPI(title="ViewSense Identity", version="0.1.0")
ISSUER = os.getenv("VS_IDENTITY_ISSUER", "https://identity:8443")
PRIVATE_KEY = read_required("VS_IDENTITY_PRIVATE_KEY_FILE")
CLIENTS = json.loads(Path(required("VS_IDENTITY_CLIENTS_FILE")).read_text(encoding="utf-8"))


def _basic_credentials(request: Request) -> tuple[str, str]:
    authorization = request.headers.get("authorization", "")
    scheme, _, encoded = authorization.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        raise HTTPException(401, "client authentication required")
    try:
        decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
        return tuple(decoded.split(":", 1))  # type: ignore[return-value]
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(401, "invalid client authentication") from exc


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "identity"}


@app.post("/oauth2/token")
async def issue_token(request: Request) -> dict:
    client_id, client_secret = _basic_credentials(request)
    client = CLIENTS.get(client_id)
    if not client or not secrets.compare_digest(str(client.get("secret", "")), client_secret):
        raise HTTPException(401, "invalid client credentials")

    form = parse_qs((await request.body()).decode("utf-8"))
    if form.get("grant_type", [""])[0] != "client_credentials":
        raise HTTPException(400, "unsupported grant_type")
    audience = form.get("audience", [""])[0]
    requested_scopes = set(form.get("scope", [""])[0].split())
    grant = client.get("grants", {}).get(audience)
    if not grant or not requested_scopes or not requested_scopes.issubset(set(grant)):
        raise HTTPException(403, "requested audience or scope is not granted")

    now = int(time.time())
    expires_in = int(os.getenv("VS_TOKEN_TTL_SECONDS", "300"))
    claims = {
        "iss": ISSUER,
        "sub": client_id,
        "aud": audience,
        "iat": now,
        "nbf": now - 1,
        "exp": now + expires_in,
        "jti": secrets.token_urlsafe(16),
        "scope": " ".join(sorted(requested_scopes)),
    }
    if client.get("tenant_id"):
        claims["tenant_id"] = client["tenant_id"]
    access_token = jwt.encode(claims, PRIVATE_KEY, algorithm="RS256")
    return {"access_token": access_token, "token_type": "Bearer", "expires_in": expires_in}
