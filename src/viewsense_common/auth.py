from __future__ import annotations

import os
from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request, status

from viewsense_common.settings import read_required


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str | None
    scopes: frozenset[str]
    claims: dict


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
        return Principal(
            subject=str(claims["sub"]),
            tenant_id=claims.get("tenant_id"),
            scopes=scopes,
            claims=claims,
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
        return principal
