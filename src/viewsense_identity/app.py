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

    requested_tenant = form.get("tenant_id", [""])[0].strip()
    fixed_tenant = str(client.get("tenant_id", "")).strip()
    if fixed_tenant and requested_tenant and requested_tenant != fixed_tenant:
        raise HTTPException(403, "fixed-tenant client cannot delegate another tenant")
    tenant_id = fixed_tenant or requested_tenant
    if requested_tenant and not fixed_tenant and not client.get("can_delegate_tenant", False):
        raise HTTPException(403, "client is not allowed to delegate tenant context")
    if tenant_id and (len(tenant_id) > 128 or not tenant_id.replace("-", "").isalnum()):
        raise HTTPException(400, "invalid tenant_id")

    subject = form.get("subject", [client_id])[0].strip() or client_id
    purpose = form.get("purpose", ["service-operation"])[0].strip()
    classification = form.get("classification", ["internal"])[0].strip()
    request_id = form.get("request_id", [""])[0].strip()
    if any(len(value) > 128 for value in (subject, purpose, classification, request_id)):
        raise HTTPException(400, "trust envelope field is too long")

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
    if tenant_id:
        claims["tenant_id"] = tenant_id
        claims["vs_ctx"] = {
            "version": "1",
            "tenant_id": tenant_id,
            "delegated_by": client_id,
            "subject": subject,
            "purpose": purpose or "service-operation",
            "classification": classification or "internal",
            "request_id": request_id or None,
        }
    access_token = jwt.encode(claims, PRIVATE_KEY, algorithm="RS256")
    return {"access_token": access_token, "token_type": "Bearer", "expires_in": expires_in}
