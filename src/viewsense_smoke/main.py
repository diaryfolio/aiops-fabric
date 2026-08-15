from __future__ import annotations

import asyncio
import os
import sys
import uuid

import httpx

from viewsense_common.client import ServiceClient


async def wait_for(client: ServiceClient, url: str) -> None:
    for _ in range(60):
        try:
            async with client.http(timeout=2) as http:
                response = await http.get(url)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        await asyncio.sleep(1)
    raise RuntimeError(f"service did not become ready: {url}")


async def main() -> None:
    client = ServiceClient()
    gateway = os.getenv("VS_GATEWAY_URL", "https://gateway:8443")
    ingestion = os.getenv("VS_INGESTION_URL", "https://ingestion:8443")
    memory = os.getenv("VS_MEMORY_URL", "https://memory-gateway:8443")
    mcp = os.getenv("VS_MCP_URL", "https://mcp-gateway:8443")
    for url in (gateway, ingestion, memory, mcp):
        await wait_for(client, f"{url}/healthz")
    user_id = f"smoke-{uuid.uuid4().hex}"

    async with client.http() as http:
        unauthorized = await http.post(
            f"{gateway}/v1/responses", json={"input": "blocked", "user_id": user_id}
        )
    assert unauthorized.status_code == 401, unauthorized.text

    gateway_token = await client.token("gateway", "api.invoke")
    async with client.http(timeout=60) as http:
        first = await http.post(
            f"{gateway}/v1/responses",
            headers={"Authorization": f"Bearer {gateway_token}"},
            json={"input": "Remember that the production region is London.", "user_id": user_id},
        )
        first.raise_for_status()
        second = await http.post(
            f"{gateway}/v1/responses",
            headers={"Authorization": f"Bearer {gateway_token}"},
            json={"input": "Which production region did I mention?", "user_id": user_id},
        )
        second.raise_for_status()
    assert first.json()["memory_hits"] == 0, first.text
    assert second.json()["memory_hits"] >= 1, second.text

    ingestion_token = await client.token("ingestion", "ingest.write")
    async with client.http() as http:
        ingested = await http.post(
            f"{ingestion}/v1/documents:ingest",
            headers={
                "Authorization": f"Bearer {ingestion_token}",
                "X-ViewSense-Tenant": "tenant-a",
            },
            json={
                "source_id": "smoke://agentic-ingestion",
                "owner_id": user_id,
                "content": ("A governed document paragraph. " * 80),
                "max_characters": 300,
                "overlap": 30,
            },
        )
        ingested.raise_for_status()
    assert ingested.json()["chunk_count"] > 1, ingested.text

    mcp_admin = await client.token("mcp-gateway", "mcp.admin")
    async with client.http() as http:
        registered = await http.put(
            f"{mcp}/v1/servers/mock",
            headers={"Authorization": f"Bearer {mcp_admin}"},
            json={
                "name": "mock",
                "base_url": "https://mock-mcp:8443",
                "audience": "mock-mcp",
                "metadata": {"test": True},
            },
        )
        registered.raise_for_status()
    mcp_invoke = await client.token("mcp-gateway", "mcp.invoke")
    async with client.http() as http:
        called = await http.post(
            f"{mcp}/v1/tools/call",
            headers={
                "Authorization": f"Bearer {mcp_invoke}",
                "X-ViewSense-Tenant": "tenant-a",
            },
            json={"server": "mock", "tool": "echo", "arguments": {"text": "zero-trust-ok"}},
        )
        called.raise_for_status()
    assert called.json()["content"][0]["text"] == "zero-trust-ok", called.text
    print("ViewSense end-to-end smoke tests passed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"ViewSense smoke test failed: {exc}", file=sys.stderr)
        raise
