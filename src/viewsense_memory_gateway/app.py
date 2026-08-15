from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from viewsense_common.auth import TokenVerifier
from viewsense_common.client import ServiceClient
from viewsense_common.tenant import delegated_tenant

app = FastAPI(title="ViewSense Memory Gateway API", version="1.0.0")
auth = TokenVerifier("memory-gateway")
client = ServiceClient()
PROVIDER_URL = os.getenv("VS_MEMORY_PROVIDER_URL", "https://memory-postgres:8443")
PROVIDER_AUDIENCE = os.getenv("VS_MEMORY_PROVIDER_AUDIENCE", "memory-postgres")


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "memory-gateway", "provider": PROVIDER_AUDIENCE}


async def _proxy(request: Request, path: str, scope: str) -> JSONResponse:
    auth.from_request(request, scope)
    tenant_id = delegated_tenant(request)
    upstream = await client.request(
        request.method,
        f"{PROVIDER_URL}{path}",
        audience=PROVIDER_AUDIENCE,
        scope="provider.invoke",
        tenant_id=tenant_id,
        json=await request.json(),
    )
    return JSONResponse(status_code=upstream.status_code, content=upstream.json())


@app.post("/v1/memories", status_code=201)
async def create_memory(request: Request) -> JSONResponse:
    return await _proxy(request, "/v1/memories", "memory.write")


@app.post("/v1/memories/search")
async def search_memories(request: Request) -> JSONResponse:
    return await _proxy(request, "/v1/memories/search", "memory.read")
