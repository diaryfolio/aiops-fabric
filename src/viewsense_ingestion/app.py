from __future__ import annotations

import os
import uuid
from typing import Any, Literal

from fastapi import FastAPI, Request
from pydantic import BaseModel, Field

from viewsense_common.auth import TokenVerifier
from viewsense_common.client import ServiceClient
from viewsense_common.tenant import delegated_tenant
from viewsense_ingestion.chunking import chunk_text

app = FastAPI(title="ViewSense AI® Ingestion API", version="1.0.0")
auth = TokenVerifier("ingestion")
client = ServiceClient()
MEMORY_URL = os.getenv("VS_MEMORY_URL", "https://memory-gateway:8443")


class IngestionRequest(BaseModel):
    source_id: str = Field(min_length=1, max_length=512)
    owner_id: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=2_000_000)
    strategy: Literal["paragraph"] = "paragraph"
    max_characters: int = Field(default=1200, ge=100, le=8000)
    overlap: int = Field(default=100, ge=0, le=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "ingestion"}


@app.post("/v1/documents:ingest", status_code=201)
async def ingest(body: IngestionRequest, request: Request) -> dict:
    principal = auth.from_request(request, "ingest.write")
    tenant_id = delegated_tenant(request)
    chunks = chunk_text(body.content, body.max_characters, body.overlap)
    document_id = f"doc_{uuid.uuid4().hex}"
    memory_ids: list[str] = []
    for index, chunk in enumerate(chunks):
        response = await client.request(
            "POST",
            f"{MEMORY_URL}/v1/memories",
            audience="memory-gateway",
            scope="memory.write",
            tenant_id=tenant_id,
            trust_envelope=principal.trust_envelope,
            json={
                "owner_id": body.owner_id,
                "content": chunk,
                "metadata": {
                    **body.metadata,
                    "kind": "document_chunk",
                    "document_id": document_id,
                    "source_id": body.source_id,
                    "chunk_index": index,
                    "chunk_count": len(chunks),
                    "chunk_strategy": body.strategy,
                },
            },
        )
        response.raise_for_status()
        memory_ids.append(response.json()["id"])
    return {
        "id": document_id,
        "object": "ingestion_result",
        "source_id": body.source_id,
        "chunk_count": len(chunks),
        "memory_ids": memory_ids,
    }
