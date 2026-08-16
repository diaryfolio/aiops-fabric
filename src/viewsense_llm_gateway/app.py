from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from viewsense_common.auth import TokenVerifier
from viewsense_common.client import ServiceClient
from viewsense_common.tenant import delegated_tenant

app = FastAPI(title="ViewSense AI® LLM Gateway API", version="1.0.0")
auth = TokenVerifier("llm-gateway")
client = ServiceClient()
PROVIDER_URL = os.getenv("VS_LLM_PROVIDER_URL", "https://mock-llm:8443")
PROVIDER_AUDIENCE = os.getenv("VS_LLM_PROVIDER_AUDIENCE", "mock-llm")


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "llm-gateway", "provider": PROVIDER_AUDIENCE}


@app.post("/v1/chat/completions")
async def completions(request: Request) -> JSONResponse:
    principal = auth.from_request(request, "llm.invoke")
    tenant_id = delegated_tenant(request)
    payload: dict[str, Any] = await request.json()
    upstream = await client.request(
        "POST",
        f"{PROVIDER_URL}/v1/chat/completions",
        audience=PROVIDER_AUDIENCE,
        scope="provider.invoke",
        tenant_id=tenant_id,
        trust_envelope=principal.trust_envelope,
        json=payload,
        timeout=50,
    )
    return JSONResponse(status_code=upstream.status_code, content=upstream.json())
