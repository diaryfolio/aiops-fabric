from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from viewsense_common.auth import TokenVerifier
from viewsense_common.tenant import delegated_tenant

app = FastAPI(title="ViewSense AI® Mock MCP Provider", version="1.0.0")
auth = TokenVerifier("mock-mcp")


class ToolCall(BaseModel):
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "mock-mcp"}


@app.post("/v1/tools/call")
async def call_tool(body: ToolCall, request: Request) -> dict:
    auth.from_request(request, "provider.invoke")
    delegated_tenant(request)
    if body.tool != "echo":
        raise HTTPException(404, "tool not found")
    return {
        "content": [{"type": "text", "text": str(body.arguments.get("text", ""))}],
        "is_error": False,
    }
