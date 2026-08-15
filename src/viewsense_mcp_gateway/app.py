from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import urlparse

import asyncpg
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from viewsense_common.auth import TokenVerifier
from viewsense_common.client import ServiceClient
from viewsense_common.settings import csv
from viewsense_common.tenant import delegated_tenant

pool: asyncpg.Pool | None = None


@asynccontextmanager
async def lifespan(_: FastAPI):
    global pool
    pool = await asyncpg.create_pool(dsn=os.environ["VS_DATABASE_URL"], min_size=1, max_size=5)
    async with pool.acquire() as connection:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mcp_servers (
                name TEXT PRIMARY KEY,
                base_url TEXT NOT NULL,
                audience TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                enabled BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )
    yield
    await pool.close()
    pool = None


app = FastAPI(title="ViewSense MCP Gateway API", version="1.0.0", lifespan=lifespan)
auth = TokenVerifier("mcp-gateway")
client = ServiceClient()
ALLOWED_HOSTS = csv("VS_MCP_ALLOWED_HOSTS", "mock-mcp")


class ServerRegistration(BaseModel):
    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,62}$")
    base_url: str
    audience: str = Field(min_length=1, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCall(BaseModel):
    server: str
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def database() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("MCP registry database is not ready")
    return pool


def validate_provider_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username:
        raise HTTPException(400, "MCP provider URL is not on the HTTPS allow-list")


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "mcp-gateway"}


@app.put("/v1/servers/{name}")
async def register_server(name: str, body: ServerRegistration, request: Request) -> dict:
    auth.from_request(request, "mcp.admin")
    if name != body.name:
        raise HTTPException(400, "path name must match body name")
    validate_provider_url(body.base_url)
    async with database().acquire() as connection:
        await connection.execute(
            "INSERT INTO mcp_servers(name, base_url, audience, metadata) "
            "VALUES($1, $2, $3, $4::jsonb) "
            "ON CONFLICT(name) DO UPDATE SET "
            "base_url=EXCLUDED.base_url, audience=EXCLUDED.audience, "
            "metadata=EXCLUDED.metadata",
            body.name,
            body.base_url.rstrip("/"),
            body.audience,
            json.dumps(body.metadata),
        )
    return {"name": name, "status": "registered"}


@app.post("/v1/tools/call")
async def call_tool(body: ToolCall, request: Request) -> dict:
    auth.from_request(request, "mcp.invoke")
    tenant_id = delegated_tenant(request)
    async with database().acquire() as connection:
        server = await connection.fetchrow(
            "SELECT base_url, audience FROM mcp_servers WHERE name=$1 AND enabled=TRUE", body.server
        )
    if not server:
        raise HTTPException(404, "MCP server is not registered or enabled")
    validate_provider_url(server["base_url"])
    upstream = await client.request(
        "POST",
        f"{server['base_url']}/v1/tools/call",
        audience=server["audience"],
        scope="provider.invoke",
        tenant_id=tenant_id,
        json={"tool": body.tool, "arguments": body.arguments},
    )
    if upstream.status_code >= 400:
        raise HTTPException(upstream.status_code, "MCP provider call failed")
    return upstream.json()
