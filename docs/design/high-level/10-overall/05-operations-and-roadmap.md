# ViewSense Operations Baseline

## Target release unit

Each service and adapter is independently deployable by contract. The current repository builds one
shared `viewsense-core:dev` image containing all Python modules; per-service images, independent
versions, digests, SBOMs, signatures, migration artifacts, and GitOps promotion are production work.

```mermaid
flowchart LR
    Source["Source + contracts"] --> Build["Build + unit/security tests"]
    Build --> Render["Helm/Kustomize render"]
    Render --> Dev["viewsense-dev smoke"]
    Dev --> Conformance["selected-provider conformance"]
    Conformance --> Security["security + residency + restore gates"]
    Security --> GitOps["signed production promotion"]
    GitOps --> Observe["SLO and rollback evidence"]
```

Only build, render, development smoke, and the documented manual OpenAI check exist in this
repository. Signing, SBOM generation, GitOps promotion, HA/restore, and production SLO gates are
target controls.

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

The current reference uses environment variables, Helm values, generated development Secrets, and
static LLM/memory routes. It does not yet provide a dynamic audited routing control plane.

## Initial SLO classes

| Class | Availability target | Primary latency indicator |
|---|---:|---|
| edge/control API | 99.9% | p95 non-provider overhead |
| memory retrieval | 99.9% | p95 query latency by collection size |
| model route | provider-tier dependent | time to first token and completion |
| MCP invocation | tool-tier dependent | completion/timeout ratio |

End-to-end SLOs must not hide provider performance. Each hop reports its own budget and dependency contribution.

## Reference test gates

The repository requires static checks, unit security/embedding tests, rendered Kubernetes
validation, an end-to-end smoke job that verifies denial without a token plus the model, memory,
ingestion, MCP, governance, and agent paths, and paired in-pod probes for representative allowed and
CNI-denied connections.
