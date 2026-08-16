from __future__ import annotations

import os
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from viewsense_common.auth import TokenVerifier
from viewsense_common.tenant import delegated_tenant

app = FastAPI(title="ViewSense AI® OpenAI Adapter", version="1.0.0")
auth = TokenVerifier("openai-adapter")

DEFAULT_BASE_URL = "https://api.openai.com/v1"
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def openai_base_url() -> str:
    value = os.getenv("VS_OPENAI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.openai.com"
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/v1"
    ):
        raise RuntimeError("VS_OPENAI_BASE_URL must be https://api.openai.com/v1")
    return value


def configured_model() -> str:
    model = os.getenv("VS_OPENAI_MODEL", "").strip()
    if not MODEL_PATTERN.fullmatch(model):
        raise RuntimeError("VS_OPENAI_MODEL is invalid")
    return model


def normalize_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(400, "request body must be a JSON object")
    if payload.get("stream", False) is not False:
        raise HTTPException(400, "streaming is not enabled for this adapter")
    messages = payload.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= 128:
        raise HTTPException(400, "messages must contain between 1 and 128 items")
    normalized_messages: list[dict[str, str]] = []
    total_characters = 0
    for message in messages:
        if not isinstance(message, dict):
            raise HTTPException(400, "each message must be an object")
        role = message.get("role")
        content = message.get("content")
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            raise HTTPException(400, "each message requires a supported role and text content")
        if not content or len(content) > 100_000:
            raise HTTPException(400, "message content length is invalid")
        total_characters += len(content)
        normalized_messages.append({"role": role, "content": content})
    if total_characters > 200_000:
        raise HTTPException(413, "combined message content is too large")
    return {"model": configured_model(), "messages": normalized_messages, "stream": False}


def client_request_id(value: str | None) -> str | None:
    if (
        value
        and len(value) <= 128
        and value.isascii()
        and all(char.isprintable() for char in value)
    ):
        return value
    return None


def safe_upstream_error(status_code: int) -> HTTPException:
    if status_code == 429:
        return HTTPException(429, "OpenAI rate limit reached")
    if status_code in {401, 403}:
        return HTTPException(502, "OpenAI provider authentication failed")
    if status_code == 408:
        return HTTPException(504, "OpenAI provider timed out")
    return HTTPException(502, "OpenAI provider request failed")


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {
        "status": "ok" if os.getenv("VS_OPENAI_API_KEY") else "not_configured",
        "service": "openai-adapter",
        "model": configured_model(),
    }


@app.post("/v1/chat/completions")
async def completions(request: Request) -> JSONResponse:
    principal = auth.from_request(request, "provider.invoke")
    delegated_tenant(request)
    api_key = os.getenv("VS_OPENAI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(503, "OpenAI provider is not configured")
    payload = normalize_request(await request.json())
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "ViewSense-OpenAI-Adapter/1.0",
    }
    request_id = client_request_id(
        principal.trust_envelope.request_id if principal.trust_envelope else None
    )
    if request_id:
        headers["X-Client-Request-Id"] = request_id
    try:
        async with httpx.AsyncClient(
            base_url=openai_base_url(),
            timeout=httpx.Timeout(60.0, connect=10.0),
            follow_redirects=False,
        ) as client:
            upstream = await client.post("/chat/completions", headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "OpenAI provider timed out") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(502, "OpenAI provider is unavailable") from exc
    if upstream.status_code >= 400:
        raise safe_upstream_error(upstream.status_code)
    try:
        response_body = upstream.json()
        choices = response_body["choices"]
        if not isinstance(choices, list) or not choices:
            raise ValueError("missing choices")
        content = choices[0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("invalid content")
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(502, "OpenAI provider returned an invalid response") from exc
    return JSONResponse(content=response_body)
