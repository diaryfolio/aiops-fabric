from __future__ import annotations

import importlib
import sys

import pytest
from fastapi import HTTPException


@pytest.fixture
def adapter(monkeypatch, tmp_path):
    public_file = tmp_path / "public.pem"
    public_file.write_text("test-public-key", encoding="utf-8")
    monkeypatch.setenv("VS_IDENTITY_PUBLIC_KEY_FILE", str(public_file))
    sys.modules.pop("viewsense_openai_adapter.app", None)
    return importlib.import_module("viewsense_openai_adapter.app")


def test_request_is_minimized_and_model_is_server_controlled(adapter, monkeypatch):
    monkeypatch.setenv("VS_OPENAI_MODEL", "gpt-4.1-mini")
    request = adapter.normalize_request(
        {
            "model": "caller-controlled-model",
            "messages": [{"role": "user", "content": "Use retrieved memory"}],
            "stream": False,
            "store": True,
            "metadata": {"secret": "must-not-leave"},
        }
    )
    assert request == {
        "model": "gpt-4.1-mini",
        "messages": [{"role": "user", "content": "Use retrieved memory"}],
        "stream": False,
    }


def test_openai_endpoint_and_request_id_fail_closed(adapter, monkeypatch):
    monkeypatch.setenv("VS_OPENAI_BASE_URL", "https://api.openai.com/v1")
    assert adapter.openai_base_url() == "https://api.openai.com/v1"
    assert adapter.client_request_id("request-123") == "request-123"
    assert adapter.client_request_id("bad\nheader") is None
    for value in (
        "http://api.openai.com/v1",
        "https://api.openai.com.attacker.invalid/v1",
        "https://user@api.openai.com/v1",
        "https://api.openai.com/v2",
    ):
        monkeypatch.setenv("VS_OPENAI_BASE_URL", value)
        with pytest.raises(RuntimeError):
            adapter.openai_base_url()


def test_openai_errors_do_not_expose_vendor_body(adapter):
    auth_error = adapter.safe_upstream_error(401)
    assert auth_error.status_code == 502
    assert "authentication failed" in auth_error.detail
    rate_error = adapter.safe_upstream_error(429)
    assert rate_error.status_code == 429
    with pytest.raises(HTTPException):
        adapter.normalize_request({"messages": [], "stream": False})
