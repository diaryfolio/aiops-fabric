# Design 10.3 - API and Integration Standards

## REST API-First Mandate

- All platform and connector integrations must expose REST APIs as the primary interface.
- OpenAPI specifications are required for all published REST contracts.
- API contracts must be versioned and backward-compatible.

## Internal Protocol Policy

- REST/JSON is the default for service-to-service communication.
- gRPC is allowed only when justified by throughput or latency constraints.
- If gRPC is used, a REST facade is still required for interoperability.

## Required API Capabilities

- OAuth2/OIDC authentication integration.
- RBAC/ABAC authorization checks.
- Consistent pagination and filtering semantics.
- Rate limiting and quota controls.
- Idempotency keys for retriable write operations.
- Request/response audit tagging with tenant and trace correlation.

## Integration Design Rules

- Adapter layer required for third-party systems.
- Provider-specific logic must not leak into domain services.
- Deprecation policy must include overlap window and migration guidance.
