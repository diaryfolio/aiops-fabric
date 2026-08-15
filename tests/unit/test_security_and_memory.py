from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from pydantic import ValidationError

from viewsense_common.auth import TokenVerifier


def _keys() -> tuple[bytes, bytes]:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_pem, public_pem


def test_token_verifier_enforces_audience_and_scope(tmp_path, monkeypatch):
    private_key, public_key = _keys()
    public_file = tmp_path / "public.pem"
    public_file.write_bytes(public_key)
    monkeypatch.setenv("VS_IDENTITY_PUBLIC_KEY_FILE", str(public_file))
    monkeypatch.setenv("VS_IDENTITY_ISSUER", "https://identity.test")
    now = int(time.time())
    claims = {
        "iss": "https://identity.test",
        "sub": "caller",
        "aud": "memory-gateway",
        "iat": now,
        "exp": now + 60,
        "scope": "memory.read",
        "tenant_id": "tenant-a",
        "vs_ctx": {
            "version": "1",
            "tenant_id": "tenant-a",
            "delegated_by": "caller",
            "subject": "caller",
            "purpose": "test",
            "classification": "internal",
        },
    }
    token = jwt.encode(claims, private_key, algorithm="RS256")
    principal = TokenVerifier("memory-gateway").verify(token, {"memory.read"})
    assert principal.tenant_id == "tenant-a"
    with pytest.raises(HTTPException) as denied:
        TokenVerifier("memory-gateway").verify(token, {"memory.write"})
    assert denied.value.status_code == 403
    with pytest.raises(HTTPException) as wrong_audience:
        TokenVerifier("llm-gateway").verify(token, {"memory.read"})
    assert wrong_audience.value.status_code == 401

    without_envelope = {key: value for key, value in claims.items() if key != "vs_ctx"}
    with pytest.raises(HTTPException) as unsigned_context:
        TokenVerifier("memory-gateway").verify(
            jwt.encode(without_envelope, private_key, algorithm="RS256"), {"memory.read"}
        )
    assert unsigned_context.value.status_code == 401

    inconsistent = {**claims, "vs_ctx": {**claims["vs_ctx"], "tenant_id": "tenant-b"}}
    with pytest.raises(HTTPException) as inconsistent_context:
        TokenVerifier("memory-gateway").verify(
            jwt.encode(inconsistent, private_key, algorithm="RS256"), {"memory.read"}
        )
    assert inconsistent_context.value.status_code == 401


def test_provider_url_policy_is_exact_host_match(monkeypatch, tmp_path):
    _, public_key = _keys()
    public_file = tmp_path / "public.pem"
    public_file.write_bytes(public_key)
    monkeypatch.setenv("VS_IDENTITY_PUBLIC_KEY_FILE", str(public_file))
    monkeypatch.setenv("VS_MCP_ALLOWED_HOSTS", "mock-mcp")
    monkeypatch.setenv("VS_CLIENT_ID", "test")
    monkeypatch.setenv("VS_CLIENT_SECRET", "test")
    monkeypatch.setenv("VS_TLS_CA_FILE", str(public_file))
    monkeypatch.setenv("VS_TLS_CERT_FILE", str(public_file))
    monkeypatch.setenv("VS_TLS_KEY_FILE", str(public_file))
    from viewsense_mcp_gateway.app import validate_provider_url

    validate_provider_url("https://mock-mcp:8443")
    for value in ("http://mock-mcp:8443", "https://mock-mcp.attacker.invalid", "https://127.0.0.1"):
        with pytest.raises(HTTPException):
            validate_provider_url(value)


def test_deterministic_embedding_is_normalized(monkeypatch, tmp_path):
    _, public_key = _keys()
    public_file = tmp_path / "public.pem"
    public_file.write_bytes(public_key)
    monkeypatch.setenv("VS_IDENTITY_PUBLIC_KEY_FILE", str(public_file))
    from viewsense_memory_postgres.app import DIMENSIONS, embed

    first = embed("portable enterprise memory")
    assert first == embed("portable enterprise memory")
    assert len(first) == DIMENSIONS
    assert sum(value * value for value in first) == pytest.approx(1.0)


def test_chunking_preserves_content_and_hard_limit():
    from viewsense_ingestion.chunking import chunk_text

    text = ("First section has useful context. " * 20) + "\n\n" + (
        "Second section contains a different topic. " * 20
    )
    chunks = chunk_text(text, max_characters=240, overlap=30)
    assert len(chunks) > 2
    assert all(0 < len(chunk) <= 240 for chunk in chunks)
    assert "First section" in chunks[0]
    assert any("Second section" in chunk for chunk in chunks)


def test_governance_models_reject_self_admission_and_sensitive_evidence(monkeypatch, tmp_path):
    _, public_key = _keys()
    public_file = tmp_path / "public.pem"
    public_file.write_bytes(public_key)
    monkeypatch.setenv("VS_IDENTITY_PUBLIC_KEY_FILE", str(public_file))

    from viewsense_governance.app import EvidenceEvent, ProviderPassport

    passport = {
        "name": "private-llm",
        "kind": "llm",
        "endpoint": "https://llm.example.test",
        "residencies": ["gb"],
        "data_classifications": ["internal"],
        "owner": "platform-team",
        "expires_at": datetime.now(UTC) + timedelta(days=1),
    }
    assert ProviderPassport(**passport).status == "draft"
    with pytest.raises(ValidationError):
        ProviderPassport(**passport, status="admitted")
    with pytest.raises(ValidationError):
        ProviderPassport(**{**passport, "endpoint": "http://llm.example.test"})
    with pytest.raises(ValidationError):
        EvidenceEvent(
            run_id="run-1",
            event_type="agent.observed",
            outcome="success",
            metadata={"safe": {"prompt": "must not be captured"}},
        )
