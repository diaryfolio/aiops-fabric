from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlparse

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from viewsense_common.auth import TokenVerifier
from viewsense_common.database import create_pool_with_retry
from viewsense_common.tenant import delegated_tenant

pool: asyncpg.Pool | None = None
SENSITIVE_EVIDENCE_KEYS = {
    "arguments",
    "completion",
    "content",
    "credential",
    "memory",
    "payload",
    "prompt",
    "result",
    "secret",
    "token",
}
POLICY_MODE = os.getenv("VS_POLICY_MODE", "builtin")
POLICY_URL = os.getenv(
    "VS_POLICY_URL", "http://127.0.0.1:8181/v1/data/viewsense/provider/admit"
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    global pool
    pool = await create_pool_with_retry(os.environ["VS_DATABASE_URL"])
    async with pool.acquire() as connection:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS provider_passports (
                tenant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                protocols JSONB NOT NULL,
                capabilities JSONB NOT NULL,
                residencies TEXT[] NOT NULL,
                data_classifications TEXT[] NOT NULL,
                owner TEXT NOT NULL,
                image_digest TEXT,
                sbom_uri TEXT,
                provenance_uri TEXT,
                status TEXT NOT NULL,
                expires_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (tenant_id, name)
            );
            CREATE TABLE IF NOT EXISTS provider_evaluations (
                id UUID PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                suite TEXT NOT NULL,
                passed BOOLEAN NOT NULL,
                scores JSONB NOT NULL,
                policy_version TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS provider_evaluations_lookup_idx
              ON provider_evaluations (tenant_id, provider_name, suite, created_at DESC);
            CREATE TABLE IF NOT EXISTS provider_admissions (
                id UUID PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                provider_name TEXT NOT NULL,
                admitted BOOLEAN NOT NULL,
                reasons JSONB NOT NULL,
                policy_version TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE TABLE IF NOT EXISTS evidence_events (
                id UUID PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                producer TEXT NOT NULL,
                outcome TEXT NOT NULL,
                policy_version TEXT,
                config_version TEXT,
                artifact_refs JSONB NOT NULL,
                metadata JSONB NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL,
                recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS evidence_events_run_idx
              ON evidence_events (tenant_id, run_id, occurred_at);
            """
        )
    yield
    await pool.close()
    pool = None


app = FastAPI(
    title="ViewSense Governance and Evidence API",
    version="1.0.0",
    lifespan=lifespan,
)
auth = TokenVerifier("governance")


def database() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("governance database is not ready")
    return pool


def decode_json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


async def external_policy_reasons(passport: asyncpg.Record, body: AdmissionRequest) -> list[str]:
    if POLICY_MODE == "builtin":
        return []
    policy_input = {
        "provider": {
            "name": passport["name"],
            "kind": passport["kind"],
            "capabilities": decode_json(passport["capabilities"]),
            "residencies": list(passport["residencies"]),
            "data_classifications": list(passport["data_classifications"]),
            "status": passport["status"],
        },
        "request": body.model_dump(mode="json"),
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5, connect=2)) as client:
            response = await client.post(POLICY_URL, json={"input": policy_input})
        response.raise_for_status()
        result = response.json().get("result")
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(503, "external policy decision unavailable") from exc
    if result is True:
        return []
    if isinstance(result, dict) and result.get("allow") is True:
        return []
    if isinstance(result, dict) and isinstance(result.get("reasons"), list):
        return [str(reason)[:256] for reason in result["reasons"]]
    return ["external policy denied provider admission"]


class ProviderPassport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,62}$")
    kind: Literal["llm", "embedding", "memory", "mcp", "workflow", "agent", "ingestion"]
    endpoint: str
    protocols: dict[str, str] = Field(default_factory=dict)
    capabilities: dict[str, bool] = Field(default_factory=dict)
    residencies: list[str] = Field(min_length=1, max_length=32)
    data_classifications: list[str] = Field(min_length=1, max_length=32)
    owner: str = Field(min_length=1, max_length=128)
    image_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    sbom_uri: str | None = None
    provenance_uri: str | None = None
    # Admission is an evaluated server-side transition, never a client assertion.
    status: Literal["draft", "revoked"] = "draft"
    expires_at: datetime

    @field_validator("endpoint", "sbom_uri", "provenance_uri")
    @classmethod
    def secure_uri(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            raise ValueError("URI must use HTTPS without user information")
        return value

    @field_validator("expires_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("expires_at must include a timezone")
        return value


class EvaluationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    passed: bool
    scores: dict[str, float] = Field(default_factory=dict)
    policy_version: str = Field(min_length=1, max_length=128)


class AdmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required_capabilities: list[str] = Field(default_factory=list, max_length=64)
    allowed_residencies: list[str] = Field(min_length=1, max_length=32)
    data_classification: str = Field(min_length=1, max_length=64)
    required_evaluation_suites: list[str] = Field(default_factory=list, max_length=32)
    policy_version: str = Field(min_length=1, max_length=128)


class EvidenceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(pattern=r"^[a-z][a-z0-9._-]{0,127}$")
    outcome: Literal["success", "denied", "failed", "pending", "cancelled"]
    policy_version: str | None = Field(default=None, max_length=128)
    config_version: str | None = Field(default=None, max_length=128)
    artifact_refs: list[str] = Field(default_factory=list, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("metadata")
    @classmethod
    def payload_minimized(cls, value: dict[str, Any]) -> dict[str, Any]:
        def keys(item: Any) -> set[str]:
            if isinstance(item, dict):
                return {str(key).lower() for key in item} | {
                    nested_key for nested in item.values() for nested_key in keys(nested)
                }
            if isinstance(item, list):
                return {nested_key for nested in item for nested_key in keys(nested)}
            return set()

        prohibited = keys(value) & SENSITIVE_EVIDENCE_KEYS
        if prohibited:
            raise ValueError(f"sensitive evidence keys are prohibited: {sorted(prohibited)}")
        encoded = json.dumps(value)
        if len(encoded) > 16_384:
            raise ValueError("evidence metadata exceeds 16 KiB")
        return value

    @field_validator("occurred_at")
    @classmethod
    def occurred_at_timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("occurred_at must include a timezone")
        return value


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    async with database().acquire() as connection:
        await connection.fetchval("SELECT 1")
    return {"status": "ok", "service": "governance"}


@app.put("/v1/provider-passports/{name}")
async def put_passport(name: str, body: ProviderPassport, request: Request) -> dict:
    auth.from_request(request, "governance.admin")
    tenant_id = delegated_tenant(request)
    if name != body.name:
        raise HTTPException(400, "path name must match body name")
    async with database().acquire() as connection:
        await connection.execute(
            """
            INSERT INTO provider_passports(
              tenant_id, name, kind, endpoint, protocols, capabilities, residencies,
              data_classifications, owner, image_digest, sbom_uri, provenance_uri,
              status, expires_at
            ) VALUES($1,$2,$3,$4,$5::jsonb,$6::jsonb,$7,$8,$9,$10,$11,$12,$13,$14)
            ON CONFLICT(tenant_id, name) DO UPDATE SET
              kind=EXCLUDED.kind, endpoint=EXCLUDED.endpoint, protocols=EXCLUDED.protocols,
              capabilities=EXCLUDED.capabilities, residencies=EXCLUDED.residencies,
              data_classifications=EXCLUDED.data_classifications, owner=EXCLUDED.owner,
              image_digest=EXCLUDED.image_digest, sbom_uri=EXCLUDED.sbom_uri,
              provenance_uri=EXCLUDED.provenance_uri, status=EXCLUDED.status,
              expires_at=EXCLUDED.expires_at, updated_at=now()
            """,
            tenant_id,
            body.name,
            body.kind,
            body.endpoint,
            json.dumps(body.protocols),
            json.dumps(body.capabilities),
            body.residencies,
            body.data_classifications,
            body.owner,
            body.image_digest,
            body.sbom_uri,
            body.provenance_uri,
            body.status,
            body.expires_at,
        )
    return {"name": name, "tenant_id": tenant_id, "status": body.status}


@app.get("/v1/provider-passports/{name}")
async def get_passport(name: str, request: Request) -> dict:
    auth.from_request(request, "governance.read")
    tenant_id = delegated_tenant(request)
    async with database().acquire() as connection:
        row = await connection.fetchrow(
            "SELECT * FROM provider_passports WHERE tenant_id=$1 AND name=$2", tenant_id, name
        )
    if not row:
        raise HTTPException(404, "provider passport not found")
    result = dict(row)
    result["protocols"] = decode_json(result["protocols"])
    result["capabilities"] = decode_json(result["capabilities"])
    result["expires_at"] = result["expires_at"].isoformat()
    result["updated_at"] = result["updated_at"].isoformat()
    return result


@app.post("/v1/provider-passports/{name}/evaluations", status_code=201)
async def record_evaluation(name: str, body: EvaluationRecord, request: Request) -> dict:
    auth.from_request(request, "governance.admin")
    tenant_id = delegated_tenant(request)
    evaluation_id = uuid.uuid4()
    async with database().acquire() as connection:
        exists = await connection.fetchval(
            "SELECT 1 FROM provider_passports WHERE tenant_id=$1 AND name=$2", tenant_id, name
        )
        if not exists:
            raise HTTPException(404, "provider passport not found")
        await connection.execute(
            "INSERT INTO provider_evaluations(id, tenant_id, provider_name, suite, passed, "
            "scores, policy_version) VALUES($1,$2,$3,$4,$5,$6::jsonb,$7)",
            evaluation_id,
            tenant_id,
            name,
            body.suite,
            body.passed,
            json.dumps(body.scores),
            body.policy_version,
        )
    return {"id": str(evaluation_id), "provider_name": name, "passed": body.passed}


@app.post("/v1/provider-passports/{name}:admit")
async def admit_provider(name: str, body: AdmissionRequest, request: Request) -> dict:
    auth.from_request(request, "governance.admin")
    tenant_id = delegated_tenant(request)
    reasons: list[str] = []
    async with database().acquire() as connection:
        passport = await connection.fetchrow(
            "SELECT * FROM provider_passports WHERE tenant_id=$1 AND name=$2", tenant_id, name
        )
        if not passport:
            raise HTTPException(404, "provider passport not found")
        capabilities = decode_json(passport["capabilities"])
        missing = sorted(
            capability
            for capability in body.required_capabilities
            if not capabilities.get(capability, False)
        )
        if missing:
            reasons.append("missing capabilities: " + ", ".join(missing))
        if not set(body.allowed_residencies) & set(passport["residencies"]):
            reasons.append("no allowed residency")
        if body.data_classification not in passport["data_classifications"]:
            reasons.append("data classification is not allowed")
        if passport["expires_at"] <= datetime.now(UTC):
            reasons.append("passport is expired")
        if passport["status"] == "revoked":
            reasons.append("passport is revoked")
        for suite in body.required_evaluation_suites:
            passed = await connection.fetchval(
                "SELECT passed FROM provider_evaluations WHERE tenant_id=$1 "
                "AND provider_name=$2 AND suite=$3 ORDER BY created_at DESC LIMIT 1",
                tenant_id,
                name,
                suite,
            )
            if passed is not True:
                reasons.append(f"evaluation not passing: {suite}")
        reasons.extend(await external_policy_reasons(passport, body))
        admitted = not reasons
        admission_id = uuid.uuid4()
        await connection.execute(
            "INSERT INTO provider_admissions(id, tenant_id, provider_name, admitted, reasons, "
            "policy_version) VALUES($1,$2,$3,$4,$5::jsonb,$6)",
            admission_id,
            tenant_id,
            name,
            admitted,
            json.dumps(reasons),
            body.policy_version,
        )
        if admitted:
            await connection.execute(
                "UPDATE provider_passports SET status='admitted', updated_at=now() "
                "WHERE tenant_id=$1 AND name=$2",
                tenant_id,
                name,
            )
    return {
        "id": str(admission_id),
        "provider_name": name,
        "admitted": admitted,
        "reasons": reasons,
        "policy_version": body.policy_version,
    }


@app.post("/v1/evidence-events", status_code=201)
async def append_evidence(body: EvidenceEvent, request: Request) -> dict:
    principal = auth.from_request(request, "evidence.write")
    tenant_id = delegated_tenant(request)
    event_id = uuid.uuid4()
    async with database().acquire() as connection:
        await connection.execute(
            """
            INSERT INTO evidence_events(
              id, tenant_id, run_id, event_type, producer, outcome, policy_version,
              config_version, artifact_refs, metadata, occurred_at
            ) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb,$10::jsonb,$11)
            """,
            event_id,
            tenant_id,
            body.run_id,
            body.event_type,
            principal.subject,
            body.outcome,
            body.policy_version,
            body.config_version,
            json.dumps(body.artifact_refs),
            json.dumps(body.metadata),
            body.occurred_at,
        )
    return {"id": str(event_id), "run_id": body.run_id, "recorded": True}


@app.get("/v1/evidence-events")
async def list_evidence(run_id: str, request: Request) -> dict:
    auth.from_request(request, "governance.read")
    tenant_id = delegated_tenant(request)
    async with database().acquire() as connection:
        rows = await connection.fetch(
            "SELECT id, run_id, event_type, producer, outcome, policy_version, config_version, "
            "artifact_refs, metadata, occurred_at, recorded_at FROM evidence_events "
            "WHERE tenant_id=$1 AND run_id=$2 ORDER BY occurred_at LIMIT 500",
            tenant_id,
            run_id,
        )
    return {
        "items": [
            {
                **dict(row),
                "id": str(row["id"]),
                "artifact_refs": decode_json(row["artifact_refs"]),
                "metadata": decode_json(row["metadata"]),
                "occurred_at": row["occurred_at"].isoformat(),
                "recorded_at": row["recorded_at"].isoformat(),
            }
            for row in rows
        ]
    }
