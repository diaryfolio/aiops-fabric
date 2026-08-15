from __future__ import annotations

import os
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from viewsense_common.auth import TokenVerifier
from viewsense_common.client import ServiceClient

app = FastAPI(title="ViewSense Edge API", version="1.0.0")
auth = TokenVerifier("gateway")
client = ServiceClient()
ORCHESTRATOR_URL = os.getenv("VS_ORCHESTRATOR_URL", "https://orchestrator:8443")


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "gateway"}


@app.post("/v1/responses")
async def responses(request: Request) -> JSONResponse:
    principal = auth.from_request(request, "api.invoke")
    if not principal.tenant_id:
        raise HTTPException(403, "tenant-bound identity required")
    payload = await request.json()
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    payload["request_id"] = request_id
    upstream = await client.request(
        "POST",
        f"{ORCHESTRATOR_URL}/v1/responses",
        audience="orchestrator",
        scope="orchestrate.invoke",
        tenant_id=principal.tenant_id,
        json=payload,
        timeout=60,
    )
    return JSONResponse(
        status_code=upstream.status_code,
        content=upstream.json(),
        headers={"X-Request-ID": request_id},
    )
