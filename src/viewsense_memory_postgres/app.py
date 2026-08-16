from __future__ import annotations

import hashlib
import json
import math
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any

import asyncpg
from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from viewsense_common.auth import TokenVerifier
from viewsense_common.database import create_pool_with_retry
from viewsense_common.tenant import delegated_tenant

DIMENSIONS = 64
pool: asyncpg.Pool | None = None


def embed(text: str) -> list[float]:
    """Small deterministic test embedding; production deployments use an embedding adapter."""
    values = [0.0] * DIMENSIONS
    for token in text.lower().split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:2], "big") % DIMENSIONS
        values[index] += -1.0 if digest[2] & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


@asynccontextmanager
async def lifespan(_: FastAPI):
    global pool
    pool = await create_pool_with_retry(os.environ["VS_DATABASE_URL"])
    async with pool.acquire() as connection:
        await connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await connection.execute(
            f"""
            CREATE TABLE IF NOT EXISTS memories (
                id UUID PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                embedding vector({DIMENSIONS}) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        await connection.execute(
            "CREATE INDEX IF NOT EXISTS memories_tenant_owner_idx ON memories (tenant_id, owner_id)"
        )
    yield
    await pool.close()
    pool = None


app = FastAPI(title="ViewSense PostgreSQL Memory Provider", version="1.0.0", lifespan=lifespan)
auth = TokenVerifier("memory-postgres")


class MemoryCreate(BaseModel):
    owner_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=100_000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemorySearch(BaseModel):
    owner_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=100_000)
    limit: int = Field(default=5, ge=1, le=50)


def database() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("memory database is not ready")
    return pool


def decode_metadata(value: Any) -> dict[str, Any]:
    return json.loads(value) if isinstance(value, str) else dict(value)


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    if pool is None:
        return {"status": "starting", "service": "memory-postgres"}
    async with pool.acquire() as connection:
        await connection.fetchval("SELECT 1")
    return {"status": "ok", "service": "memory-postgres"}


@app.post("/v1/memories", status_code=201)
async def create_memory(body: MemoryCreate, request: Request) -> dict:
    auth.from_request(request, "provider.invoke")
    tenant_id = delegated_tenant(request)
    memory_id = uuid.uuid4()
    async with database().acquire() as connection:
        await connection.execute(
            "INSERT INTO memories(id, tenant_id, owner_id, content, metadata, embedding) "
            "VALUES($1, $2, $3, $4, $5::jsonb, $6::vector)",
            memory_id,
            tenant_id,
            body.owner_id,
            body.content,
            json.dumps(body.metadata),
            vector_literal(embed(body.content)),
        )
    return {"id": str(memory_id), "tenant_id": tenant_id, "owner_id": body.owner_id}


@app.post("/v1/memories/search")
async def search_memories(body: MemorySearch, request: Request) -> dict:
    auth.from_request(request, "provider.invoke")
    tenant_id = delegated_tenant(request)
    async with database().acquire() as connection:
        rows = await connection.fetch(
            "SELECT id, owner_id, content, metadata, created_at, "
            "1 - (embedding <=> $3::vector) AS score "
            "FROM memories WHERE tenant_id = $1 AND owner_id = $2 "
            "ORDER BY embedding <=> $3::vector LIMIT $4",
            tenant_id,
            body.owner_id,
            vector_literal(embed(body.query)),
            body.limit,
        )
    return {
        "items": [
            {
                "id": str(row["id"]),
                "owner_id": row["owner_id"],
                "content": row["content"],
                "metadata": decode_metadata(row["metadata"]),
                "score": float(row["score"]),
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]
    }
