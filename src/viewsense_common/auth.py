from __future__ import annotations

import os
from dataclasses import dataclass

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
