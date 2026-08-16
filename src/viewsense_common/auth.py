from __future__ import annotations

import os
import ssl
from dataclasses import dataclass
from urllib.parse import urlparse

import jwt
from fastapi import HTTPException, Request, status

from viewsense_common.settings import read_required


@dataclass(frozen=True)
class TrustEnvelope:
    version: str
    tenant_id: str
    delegated_by: str
    subject: str
    purpose: str
    classification: str
    request_id: str | None


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str | None
    scopes: frozenset[str]
    claims: dict
    trust_envelope: TrustEnvelope | None


class TokenVerifier:
    def __init__(self, audience: str):
        self.audience = audience
        self.issuer = os.getenv("VS_IDENTITY_ISSUER", "https://identity:8443")
        self.public_key = read_required("VS_IDENTITY_PUBLIC_KEY_FILE")

    def verify(self, token: str, required_scopes: set[str]) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid access token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        scopes = frozenset(str(claims.get("scope", "")).split())
        if not required_scopes.issubset(scopes):
            raise HTTPException(status_code=403, detail="insufficient token scope")
        tenant_id = claims.get("tenant_id")
        envelope_claim = claims.get("vs_ctx")
        envelope = None
        if tenant_id:
            if not isinstance(envelope_claim, dict):
                raise HTTPException(status_code=401, detail="signed trust envelope required")
            required = {
                "version",
                "tenant_id",
                "delegated_by",
                "subject",
                "purpose",
                "classification",
            }
            if not required.issubset(envelope_claim) or envelope_claim.get("version") != "1":
                raise HTTPException(status_code=401, detail="invalid trust envelope")
            if envelope_claim.get("tenant_id") != tenant_id:
                raise HTTPException(status_code=401, detail="inconsistent trust envelope tenant")
            envelope = TrustEnvelope(
                version="1",
                tenant_id=str(tenant_id),
                delegated_by=str(envelope_claim["delegated_by"]),
                subject=str(envelope_claim["subject"]),
                purpose=str(envelope_claim["purpose"]),
                classification=str(envelope_claim["classification"]),
                request_id=(
                    str(envelope_claim["request_id"])
                    if envelope_claim.get("request_id")
                    else None
                ),
            )
            if not all(
                (
                    envelope.delegated_by,
                    envelope.subject,
                    envelope.purpose,
                    envelope.classification,
                )
            ):
                raise HTTPException(status_code=401, detail="invalid trust envelope fields")
        return Principal(
            subject=str(claims["sub"]),
            tenant_id=tenant_id,
            scopes=scopes,
            claims=claims,
            trust_envelope=envelope,
        )

    def from_request(self, request: Request, *required_scopes: str) -> Principal:
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="bearer token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        principal = self.verify(token, set(required_scopes))
        request.state.principal = principal.subject
        if principal.tenant_id:
            request.state.tenant_id = principal.tenant_id
        if principal.trust_envelope:
            request.state.trust_envelope = principal.trust_envelope
        return principal


def validate_oidc_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("OIDC URL must use HTTPS without user information")
    return value


class OIDCTokenVerifier:
    """Validate enterprise OIDC at the edge and establish a local trust envelope."""

    def __init__(self) -> None:
        self.issuer = validate_oidc_url(os.environ["VS_EXTERNAL_OIDC_ISSUER"])
        self.jwks_url = validate_oidc_url(os.environ["VS_EXTERNAL_OIDC_JWKS_URL"])
        self.audience = os.environ["VS_EXTERNAL_OIDC_AUDIENCE"]
        self.tenant_claim = os.getenv("VS_EXTERNAL_OIDC_TENANT_CLAIM", "tenant_id")
        self.scope_claim = os.getenv("VS_EXTERNAL_OIDC_SCOPE_CLAIM", "scope")
        ca_file = os.getenv("VS_EXTERNAL_OIDC_CA_FILE")
        ssl_context = ssl.create_default_context(cafile=ca_file) if ca_file else None
        self.jwks = jwt.PyJWKClient(
            self.jwks_url,
            cache_keys=True,
            timeout=5,
            ssl_context=ssl_context,
        )

    def from_request(self, request: Request, *required_scopes: str) -> Principal:
        authorization = request.headers.get("authorization", "")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="bearer token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            signing_key = self.jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "iss", "sub", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise HTTPException(401, "invalid external access token") from exc
        scope_value = claims.get(self.scope_claim, "")
        if isinstance(scope_value, list):
            scopes = frozenset(str(scope) for scope in scope_value)
        else:
            scopes = frozenset(str(scope_value).split())
        if not set(required_scopes).issubset(scopes):
            raise HTTPException(403, "insufficient external token scope")
        tenant_id = str(claims.get(self.tenant_claim, "")).strip()
        if (
            not tenant_id
            or len(tenant_id) > 128
            or not tenant_id.replace("-", "").isalnum()
        ):
            raise HTTPException(403, "external token has no valid tenant claim")
        subject = str(claims["sub"])
        if not subject or len(subject) > 128:
            raise HTTPException(403, "external token has no valid subject")
        classification = str(claims.get("classification", "internal")).strip() or "internal"
        envelope = TrustEnvelope(
            version="1",
            tenant_id=tenant_id,
            delegated_by=self.issuer,
            subject=subject,
            purpose="external-api-request",
            classification=classification[:128],
            request_id=getattr(request.state, "request_id", None),
        )
        principal = Principal(
            subject=subject,
            tenant_id=tenant_id,
            scopes=scopes,
            claims=claims,
            trust_envelope=envelope,
        )
        request.state.principal = subject
        request.state.tenant_id = tenant_id
        request.state.trust_envelope = envelope
        return principal
