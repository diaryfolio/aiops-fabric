from __future__ import annotations

import hashlib
import os
import ssl
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from viewsense_common.auth import TokenVerifier
from viewsense_common.tenant import delegated_tenant

app = FastAPI(title="ViewSense Mem0 Memory Adapter", version="1.0.0")
auth = TokenVerifier("memory-mem0")
MEM0_URL = os.getenv("VS_MEM0_URL", "https://mem0.example.invalid").rstrip("/")
MEM0_API_KEY = os.getenv("VS_MEM0_API_KEY", "")
MEM0_MODE = os.getenv("VS_MEM0_MODE", "oss")


class MemoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=100_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySearch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=100_000)
    limit: int = Field(default=5, ge=1, le=50)


def validate_mem0_url(value: str, *, allow_insecure: bool = False) -> str:
    parsed = urlparse(value)
    allowed_scheme = parsed.scheme == "https" or (allow_insecure and parsed.scheme == "http")
    if not allowed_scheme or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Mem0 URL must be an HTTPS origin without user information")
    if parsed.query or parsed.fragment:
        raise ValueError("Mem0 URL must not include a query or fragment")
    return value.rstrip("/")


def external_owner(tenant_id: str, owner_id: str) -> str:
    digest = hashlib.sha256(f"{tenant_id}\0{owner_id}".encode()).hexdigest()
    return f"viewsense-{digest}"


def mem0_path(operation: str, mode: str = MEM0_MODE) -> str:
    prefix = "/v1" if mode == "platform" else ""
    return f"{prefix}/{operation}"


def first_memory_id(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for key in ("id", "memory_id"):
            if payload.get(key):
                return str(payload[key])
        for key in ("results", "memories", "data"):
            result = first_memory_id(payload.get(key))
            if result:
                return result
    if isinstance(payload, list):
        for item in payload:
            result = first_memory_id(item)
            if result:
                return result
    return None


def normalize_search(payload: Any, limit: int) -> list[dict[str, Any]]:
    candidates = (
        payload.get("results", payload.get("memories", []))
        if isinstance(payload, dict)
        else payload
    )
    if not isinstance(candidates, list):
        return []
    items: list[dict[str, Any]] = []
    for candidate in candidates[:limit]:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("memory", candidate.get("text", candidate.get("content")))
        if not isinstance(content, str):
            continue
        items.append(
            {
                "id": str(candidate.get("id", candidate.get("memory_id", "unknown"))),
                "content": content,
                "metadata": candidate.get("metadata", {}),
                "score": candidate.get("score"),
            }
        )
    return items


def mem0_http() -> httpx.AsyncClient:
    try:
        base_url = validate_mem0_url(
            MEM0_URL,
            allow_insecure=os.getenv("VS_MEM0_ALLOW_INSECURE", "false").lower() == "true",
        )
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if not MEM0_API_KEY:
        raise HTTPException(503, "Mem0 credential is not configured")
    context = ssl.create_default_context(cafile=os.getenv("VS_MEM0_CA_FILE"))
    client_cert = os.getenv("VS_MEM0_CLIENT_CERT_FILE")
    client_key = os.getenv("VS_MEM0_CLIENT_KEY_FILE")
    if client_cert and client_key:
        context.load_cert_chain(client_cert, client_key)
    return httpx.AsyncClient(
        base_url=base_url,
        headers={"X-API-Key": MEM0_API_KEY},
        verify=context,
        timeout=httpx.Timeout(30, connect=5),
    )


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "memory-mem0", "mode": MEM0_MODE}


@app.post("/v1/memories", status_code=201)
async def create_memory(body: MemoryCreate, request: Request) -> dict:
    auth.from_request(request, "provider.invoke")
    tenant_id = delegated_tenant(request)
    payload = {
        "messages": [{"role": "user", "content": body.content}],
        "user_id": external_owner(tenant_id, body.owner_id),
        "metadata": body.metadata,
    }
    try:
        async with mem0_http() as client:
            upstream = await client.post(mem0_path("memories"), json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Mem0 create operation unavailable") from exc
    if upstream.status_code >= 400:
        raise HTTPException(502, "Mem0 create operation failed")
    try:
        memory_id = first_memory_id(upstream.json())
    except ValueError as exc:
        raise HTTPException(502, "Mem0 create response was not valid JSON") from exc
    if memory_id is None:
        raise HTTPException(502, "Mem0 create response did not contain a memory identifier")
    return {"id": memory_id, "tenant_id": tenant_id, "owner_id": body.owner_id}


@app.post("/v1/memories/search")
async def search_memories(body: MemorySearch, request: Request) -> dict:
    auth.from_request(request, "provider.invoke")
    tenant_id = delegated_tenant(request)
    payload = {
        "query": body.query,
        "user_id": external_owner(tenant_id, body.owner_id),
        "limit": body.limit,
    }
    try:
        async with mem0_http() as client:
            upstream = await client.post(mem0_path("search"), json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(502, "Mem0 search operation unavailable") from exc
    if upstream.status_code >= 400:
        raise HTTPException(502, "Mem0 search operation failed")
    try:
        result = normalize_search(upstream.json(), body.limit)
    except ValueError as exc:
        raise HTTPException(502, "Mem0 search response was not valid JSON") from exc
    return {"items": result}
