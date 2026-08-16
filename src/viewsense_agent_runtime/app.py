from __future__ import annotations

import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Literal

import asyncpg
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from viewsense_common.auth import TokenVerifier
from viewsense_common.database import create_pool_with_retry
from viewsense_common.tenant import delegated_tenant

pool: asyncpg.Pool | None = None
RunState = Literal[
    "received",
    "running",
    "approval_pending",
    "completed",
    "cancelled",
    "rejected",
    "failed",
]
Action = Literal["start", "checkpoint", "request_approval", "approve", "reject", "complete", "fail"]
TRANSITIONS: dict[tuple[str, str], str] = {
    ("received", "start"): "running",
    ("running", "checkpoint"): "running",
    ("running", "request_approval"): "approval_pending",
    ("approval_pending", "approve"): "running",
    ("approval_pending", "reject"): "rejected",
    ("running", "complete"): "completed",
    ("running", "fail"): "failed",
}
TERMINAL_STATES = {"completed", "cancelled", "rejected", "failed"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    global pool
    pool = await create_pool_with_retry(os.environ["VS_DATABASE_URL"])
    async with pool.acquire() as connection:
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id UUID PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                created_by TEXT NOT NULL,
                profile TEXT NOT NULL,
                objective TEXT NOT NULL,
                state TEXT NOT NULL,
                version INTEGER NOT NULL,
                step_count INTEGER NOT NULL,
                max_steps INTEGER NOT NULL,
                max_tool_calls INTEGER NOT NULL,
                max_cost_units INTEGER NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (tenant_id, idempotency_key)
            );
            CREATE TABLE IF NOT EXISTS agent_events (
                id BIGSERIAL PRIMARY KEY,
                run_id UUID NOT NULL REFERENCES agent_runs(id),
                sequence INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                actor TEXT NOT NULL,
                state TEXT NOT NULL,
                metadata JSONB NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (run_id, sequence)
            );
            CREATE INDEX IF NOT EXISTS agent_runs_tenant_updated_idx
              ON agent_runs (tenant_id, updated_at DESC);
            """
        )
    yield
    await pool.close()
    pool = None


app = FastAPI(title="ViewSense AI® Durable Agent Runtime", version="1.0.0", lifespan=lifespan)
auth = TokenVerifier("agent-runtime")


def database() -> asyncpg.Pool:
    if pool is None:
        raise RuntimeError("agent database is not ready")
    return pool


def next_state(current: str, action: str) -> str:
    target = TRANSITIONS.get((current, action))
    if target is None:
        raise ValueError(f"action {action} is invalid while run is {current}")
    return target


class AgentRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=1, max_length=20_000)
    profile: str = Field(default="bounded-default", pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    max_steps: int = Field(default=12, ge=1, le=100)
    max_tool_calls: int = Field(default=8, ge=0, le=100)
    max_cost_units: int = Field(default=100, ge=1, le=1_000_000)


class AgentResume(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Action
    expected_version: int = Field(ge=1)
    reason: str | None = Field(default=None, max_length=512)


def run_document(row: asyncpg.Record, *, include_objective: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": str(row["id"]),
        "profile": row["profile"],
        "state": row["state"],
        "version": row["version"],
        "step_count": row["step_count"],
        "budgets": {
            "max_steps": row["max_steps"],
            "max_tool_calls": row["max_tool_calls"],
            "max_cost_units": row["max_cost_units"],
        },
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }
    if include_objective:
        result["objective"] = row["objective"]
    return result


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    async with database().acquire() as connection:
        await connection.fetchval("SELECT 1")
    return {"status": "ok", "service": "agent-runtime"}


@app.post("/v1/agent-runs", status_code=201)
async def create_run(
    body: AgentRunCreate,
    request: Request,
    idempotency_key: str = Header(min_length=8, max_length=128),
) -> dict:
    principal = auth.from_request(request, "agent.run")
    tenant_id = delegated_tenant(request)
    run_id = uuid.uuid4()
    async with database().acquire() as connection, connection.transaction():
        row = await connection.fetchrow(
            """
            INSERT INTO agent_runs(
              id, tenant_id, idempotency_key, created_by, profile, objective,
              state, version, step_count, max_steps, max_tool_calls, max_cost_units
            ) VALUES($1,$2,$3,$4,$5,$6,'received',1,0,$7,$8,$9)
            ON CONFLICT(tenant_id, idempotency_key) DO NOTHING
            RETURNING *
            """,
            run_id,
            tenant_id,
            idempotency_key,
            principal.subject,
            body.profile,
            body.objective,
            body.max_steps,
            body.max_tool_calls,
            body.max_cost_units,
        )
        created = row is not None
        if row is None:
            row = await connection.fetchrow(
                "SELECT * FROM agent_runs WHERE tenant_id=$1 AND idempotency_key=$2",
                tenant_id,
                idempotency_key,
            )
            existing_request = (
                row["profile"],
                row["objective"],
                row["max_steps"],
                row["max_tool_calls"],
                row["max_cost_units"],
            )
            submitted_request = (
                body.profile,
                body.objective,
                body.max_steps,
                body.max_tool_calls,
                body.max_cost_units,
            )
            if existing_request != submitted_request:
                raise HTTPException(409, "idempotency key was used for a different agent run")
        if created:
            await connection.execute(
                "INSERT INTO agent_events(run_id, sequence, event_type, actor, state, metadata) "
                "VALUES($1,1,'run.received',$2,'received',$3::jsonb)",
                row["id"],
                principal.subject,
                json.dumps({"profile": body.profile}),
            )
    result = run_document(row)
    result["idempotent_replay"] = not created
    return result


@app.get("/v1/agent-runs/{run_id}")
async def get_run(run_id: uuid.UUID, request: Request) -> dict:
    auth.from_request(request, "agent.run")
    tenant_id = delegated_tenant(request)
    async with database().acquire() as connection:
        row = await connection.fetchrow(
            "SELECT * FROM agent_runs WHERE tenant_id=$1 AND id=$2", tenant_id, run_id
        )
    if row is None:
        raise HTTPException(404, "agent run not found")
    return run_document(row, include_objective=True)


@app.post("/v1/agent-runs/{run_id}:resume")
async def resume_run(run_id: uuid.UUID, body: AgentResume, request: Request) -> dict:
    required_scope = "agent.approve" if body.action in {"approve", "reject"} else "agent.run"
    principal = auth.from_request(request, required_scope)
    tenant_id = delegated_tenant(request)
    async with database().acquire() as connection, connection.transaction():
        row = await connection.fetchrow(
            "SELECT * FROM agent_runs WHERE tenant_id=$1 AND id=$2 FOR UPDATE",
            tenant_id,
            run_id,
        )
        if row is None:
            raise HTTPException(404, "agent run not found")
        if row["version"] != body.expected_version:
            raise HTTPException(409, "agent run version conflict")
        try:
            target = next_state(row["state"], body.action)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        step_count = row["step_count"] + (1 if body.action in {"start", "checkpoint"} else 0)
        if step_count > row["max_steps"]:
            raise HTTPException(409, "agent step budget exhausted")
        version = row["version"] + 1
        updated = await connection.fetchrow(
            "UPDATE agent_runs SET state=$1, version=$2, step_count=$3, updated_at=now() "
            "WHERE id=$4 RETURNING *",
            target,
            version,
            step_count,
            run_id,
        )
        await connection.execute(
            "INSERT INTO agent_events(run_id, sequence, event_type, actor, state, metadata) "
            "VALUES($1,$2,$3,$4,$5,$6::jsonb)",
            run_id,
            version,
            f"run.{body.action}",
            principal.subject,
            target,
            json.dumps({"reason": body.reason} if body.reason else {}),
        )
    return run_document(updated)


@app.post("/v1/agent-runs/{run_id}:cancel")
async def cancel_run(run_id: uuid.UUID, request: Request) -> dict:
    principal = auth.from_request(request, "agent.run")
    tenant_id = delegated_tenant(request)
    async with database().acquire() as connection, connection.transaction():
        row = await connection.fetchrow(
            "SELECT * FROM agent_runs WHERE tenant_id=$1 AND id=$2 FOR UPDATE",
            tenant_id,
            run_id,
        )
        if row is None:
            raise HTTPException(404, "agent run not found")
        if row["state"] in TERMINAL_STATES:
            raise HTTPException(409, "agent run is already terminal")
        version = row["version"] + 1
        updated = await connection.fetchrow(
            "UPDATE agent_runs SET state='cancelled', version=$1, updated_at=now() "
            "WHERE id=$2 RETURNING *",
            version,
            run_id,
        )
        await connection.execute(
            "INSERT INTO agent_events(run_id, sequence, event_type, actor, state, metadata) "
            "VALUES($1,$2,'run.cancel',$3,'cancelled','{}'::jsonb)",
            run_id,
            version,
            principal.subject,
        )
    return run_document(updated)


@app.get("/v1/agent-runs/{run_id}/events")
async def get_events(run_id: uuid.UUID, request: Request) -> dict:
    auth.from_request(request, "agent.run")
    tenant_id = delegated_tenant(request)
    async with database().acquire() as connection:
        exists = await connection.fetchval(
            "SELECT 1 FROM agent_runs WHERE tenant_id=$1 AND id=$2", tenant_id, run_id
        )
        if not exists:
            raise HTTPException(404, "agent run not found")
        rows = await connection.fetch(
            "SELECT sequence, event_type, actor, state, metadata, occurred_at "
            "FROM agent_events WHERE run_id=$1 ORDER BY sequence",
            run_id,
        )
    return {
        "items": [
            {
                "sequence": row["sequence"],
                "event_type": row["event_type"],
                "actor": row["actor"],
                "state": row["state"],
                "metadata": json.loads(row["metadata"])
                if isinstance(row["metadata"], str)
                else row["metadata"],
                "occurred_at": row["occurred_at"].isoformat(),
            }
            for row in rows
        ]
    }
