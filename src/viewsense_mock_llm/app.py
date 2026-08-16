from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request

from viewsense_common.auth import TokenVerifier
from viewsense_common.tenant import delegated_tenant

app = FastAPI(title="ViewSense AI® Mock LLM Adapter", version="1.0.0")
auth = TokenVerifier("mock-llm")


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "mock-llm"}


@app.post("/v1/chat/completions")
async def completions(request: Request) -> dict:
    auth.from_request(request, "provider.invoke")
    delegated_tenant(request)
    body = await request.json()
    messages = body.get("messages", [])
    user_messages = [
        str(item.get("content", "")) for item in messages if item.get("role") == "user"
    ]
    prompt = user_messages[-1] if user_messages else ""
    content = f"ViewSense AI® mock response: {prompt}"
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "viewsense-mock"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(content.split()),
            "total_tokens": len(prompt.split()) + len(content.split()),
        },
    }
