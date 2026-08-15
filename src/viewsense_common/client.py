from __future__ import annotations

import asyncio
import os
import ssl
import time
from dataclasses import dataclass
from typing import Any

import httpx

from viewsense_common.logging import request_id_context
from viewsense_common.settings import required


@dataclass
class CachedToken:
    value: str
    expires_at: float


class ServiceClient:
    """mTLS HTTP client that obtains short-lived, audience-bound workload tokens."""

    def __init__(self) -> None:
        self.identity_url = os.getenv("VS_IDENTITY_URL", "https://identity:8443")
        self.client_id = required("VS_CLIENT_ID")
        self.client_secret = required("VS_CLIENT_SECRET")
        self.ca_file = required("VS_TLS_CA_FILE")
        self.cert_file = required("VS_TLS_CERT_FILE")
        self.key_file = required("VS_TLS_KEY_FILE")
        self._tokens: dict[tuple[str, str], CachedToken] = {}
        self._lock = asyncio.Lock()

    def http(self, timeout: float = 20.0) -> httpx.AsyncClient:
        context = ssl.create_default_context(cafile=self.ca_file)
        context.load_cert_chain(self.cert_file, self.key_file)
        return httpx.AsyncClient(verify=context, timeout=timeout)

    async def token(self, audience: str, scope: str) -> str:
        key = (audience, scope)
        cached = self._tokens.get(key)
        if cached and cached.expires_at > time.time() + 15:
            return cached.value
        async with self._lock:
            cached = self._tokens.get(key)
            if cached and cached.expires_at > time.time() + 15:
                return cached.value
            async with self.http() as client:
                response = await client.post(
                    f"{self.identity_url}/oauth2/token",
                    auth=(self.client_id, self.client_secret),
                    data={
                        "grant_type": "client_credentials",
                        "audience": audience,
                        "scope": scope,
                    },
                )
                response.raise_for_status()
                payload = response.json()
            token = str(payload["access_token"])
            self._tokens[key] = CachedToken(token, time.time() + int(payload["expires_in"]))
            return token

    async def request(
        self,
        method: str,
        url: str,
        *,
        audience: str,
        scope: str,
        tenant_id: str | None = None,
        json: Any = None,
        timeout: float = 20.0,
    ) -> httpx.Response:
        token = await self.token(audience, scope)
        headers = {"Authorization": f"Bearer {token}"}
        request_id = request_id_context.get()
        if request_id:
            headers["X-Request-ID"] = request_id
        if tenant_id:
            headers["X-ViewSense-Tenant"] = tenant_id
        async with self.http(timeout=timeout) as client:
            return await client.request(method, url, headers=headers, json=json)
