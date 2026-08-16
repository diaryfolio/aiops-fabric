from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

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
    governance = os.getenv("VS_GOVERNANCE_URL", "https://governance:8443")
    agent = os.getenv("VS_AGENT_URL", "https://agent-runtime:8443")
    for url in (gateway, ingestion, memory, mcp, governance, agent):
        await wait_for(client, f"{url}/healthz")
    user_id = f"smoke-{uuid.uuid4().hex}"

    async with client.http() as http:
        unauthorized = await http.post(
            f"{gateway}/v1/responses", json={"input": "blocked", "user_id": user_id}
        )
    assert unauthorized.status_code == 401, unauthorized.text

    memory_read_token = await client.token("memory-gateway", "memory.read")
    async with client.http() as http:
        unsigned_tenant = await http.post(
            f"{memory}/v1/memories/search",
            headers={
                "Authorization": f"Bearer {memory_read_token}",
                "X-ViewSense-Tenant": "tenant-b",
            },
            json={"owner_id": user_id, "query": "blocked", "limit": 1},
        )
    assert unsigned_tenant.status_code == 400, unsigned_tenant.text

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
            },
            json={"server": "mock", "tool": "echo", "arguments": {"text": "zero-trust-ok"}},
        )
        called.raise_for_status()
    assert called.json()["content"][0]["text"] == "zero-trust-ok", called.text

    governance_admin = await client.token("governance", "governance.admin")
    passport_name = f"smoke-llm-{uuid.uuid4().hex[:8]}"
    async with client.http() as http:
        passport = await http.put(
            f"{governance}/v1/provider-passports/{passport_name}",
            headers={"Authorization": f"Bearer {governance_admin}"},
            json={
                "name": passport_name,
                "kind": "llm",
                "endpoint": "https://mock-llm:8443",
                "protocols": {"openai-chat": "v1"},
                "capabilities": {"chat": True, "streaming": False},
                "residencies": ["local-dev"],
                "data_classifications": ["internal"],
                "owner": "viewsense-smoke",
                "status": "draft",
                "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
            },
        )
        passport.raise_for_status()
        evaluation = await http.post(
            f"{governance}/v1/provider-passports/{passport_name}/evaluations",
            headers={"Authorization": f"Bearer {governance_admin}"},
            json={
                "suite": "smoke-quality",
                "passed": True,
                "scores": {"success_rate": 1.0},
                "policy_version": "smoke-v1",
            },
        )
        evaluation.raise_for_status()
        admission = await http.post(
            f"{governance}/v1/provider-passports/{passport_name}:admit",
            headers={"Authorization": f"Bearer {governance_admin}"},
            json={
                "required_capabilities": ["chat"],
                "allowed_residencies": ["local-dev"],
                "data_classification": "internal",
                "required_evaluation_suites": ["smoke-quality"],
                "policy_version": "smoke-v1",
            },
        )
        admission.raise_for_status()
    assert admission.json()["admitted"] is True, admission.text

    evidence_token = await client.token("governance", "evidence.write")
    run_id = f"run_{uuid.uuid4().hex}"
    async with client.http() as http:
        evidence = await http.post(
            f"{governance}/v1/evidence-events",
            headers={"Authorization": f"Bearer {evidence_token}"},
            json={
                "run_id": run_id,
                "event_type": "provider.admitted",
                "outcome": "success",
                "policy_version": "smoke-v1",
                "artifact_refs": [f"provider-passport:{passport_name}"],
                "metadata": {"provider_kind": "llm"},
            },
        )
        evidence.raise_for_status()
    governance_read = await client.token("governance", "governance.read")
    async with client.http() as http:
        evidence_list = await http.get(
            f"{governance}/v1/evidence-events",
            params={"run_id": run_id},
            headers={"Authorization": f"Bearer {governance_read}"},
        )
        evidence_list.raise_for_status()
    assert len(evidence_list.json()["items"]) == 1, evidence_list.text

    agent_token = await client.token("agent-runtime", "agent.run")
    idempotency_key = f"smoke-agent-{uuid.uuid4().hex}"
    async with client.http() as http:
        created = await http.post(
            f"{agent}/v1/agent-runs",
            headers={
                "Authorization": f"Bearer {agent_token}",
                "Idempotency-Key": idempotency_key,
            },
            json={"objective": "Validate a bounded approval workflow", "max_steps": 3},
        )
        created.raise_for_status()
        replay = await http.post(
            f"{agent}/v1/agent-runs",
            headers={
                "Authorization": f"Bearer {agent_token}",
                "Idempotency-Key": idempotency_key,
            },
            json={"objective": "Validate a bounded approval workflow", "max_steps": 3},
        )
        replay.raise_for_status()
    agent_run_id = created.json()["id"]
    assert replay.json()["id"] == agent_run_id
    assert replay.json()["idempotent_replay"] is True

    version = 1
    for action in ("start", "request_approval"):
        async with client.http() as http:
            resumed = await http.post(
                f"{agent}/v1/agent-runs/{agent_run_id}:resume",
                headers={"Authorization": f"Bearer {agent_token}"},
                json={"action": action, "expected_version": version},
            )
            resumed.raise_for_status()
        version = resumed.json()["version"]
    assert resumed.json()["state"] == "approval_pending"

    approval_token = await client.token("agent-runtime", "agent.approve")
    workflow_actions = (
        ("approve", approval_token),
        ("checkpoint", agent_token),
        ("complete", agent_token),
    )
    for action, token in workflow_actions:
        async with client.http() as http:
            resumed = await http.post(
                f"{agent}/v1/agent-runs/{agent_run_id}:resume",
                headers={"Authorization": f"Bearer {token}"},
                json={"action": action, "expected_version": version},
            )
            resumed.raise_for_status()
        version = resumed.json()["version"]
    assert resumed.json()["state"] == "completed"
    async with client.http() as http:
        agent_events = await http.get(
            f"{agent}/v1/agent-runs/{agent_run_id}/events",
            headers={"Authorization": f"Bearer {agent_token}"},
        )
        agent_events.raise_for_status()
    assert len(agent_events.json()["items"]) == 6
    print("ViewSense AI® end-to-end smoke tests passed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"ViewSense AI® smoke test failed: {exc}", file=sys.stderr)
        raise
