# ViewSense Operations Baseline

## Release unit

Each service and adapter is independently versioned and deployable. A release records image digest, SBOM, signature, API-contract version, database migration, configuration schema, and rollback compatibility. Production promotion is GitOps-only.

## Required operational controls

- startup, readiness, and liveness behavior appropriate to dependencies;
- graceful termination and bounded connection draining;
- resource requests/limits and disruption budgets;
- horizontal scaling for stateless gateways;
- migration jobs that are backward compatible during rollout;
- telemetry for request rate, error rate, latency, saturation, token use, retrieval behavior, and tool calls;
- tested backup/restore for each state owner;
- provider health that cannot leak secrets or make the whole control plane depend on one vendor.

## Configuration

Routing, provider catalogs, model aliases, tenant policy, and feature flags are configuration resources with schema validation and audit history. Secrets contain only credentials/keys and come from an external secret manager in production. Environment variables are acceptable for the development reference but are not the desired dynamic control plane.

## Initial SLO classes

| Class | Availability target | Primary latency indicator |
|---|---:|---|
| edge/control API | 99.9% | p95 non-provider overhead |
| memory retrieval | 99.9% | p95 query latency by collection size |
| model route | provider-tier dependent | time to first token and completion |
| MCP invocation | tool-tier dependent | completion/timeout ratio |

End-to-end SLOs must not hide provider performance. Each hop reports its own budget and dependency contribution.

## Reference test gates

The repository requires static checks, unit security/embedding tests, rendered Kubernetes validation, and an end-to-end smoke job that verifies denial without a token, a full model request, persisted memory retrieval, MCP registration, and an authorized MCP call.
