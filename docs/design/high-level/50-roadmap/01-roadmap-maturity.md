# ViewSense Delivery Roadmap and Maturity

## Delivery strategy

Build thin end-to-end slices and prove replaceability/security with tests before adding providers. Dates depend on enterprise controls and provider choices; exit criteria, not elapsed weeks, determine readiness.

## Phase 0 — executable contract foundation (current)

Deliver edge, orchestrator, LLM/memory/MCP gateways, mock providers, PostgreSQL/pgvector memory, development workload identity, Kubernetes packaging, network policy, and smoke tests.

Exit: a clean cluster can deploy into an isolated namespace; missing authorization is denied; model, persisted memory, and MCP paths pass end to end.

## Phase 1 — production identity and operations

Integrate enterprise OIDC, SPIFFE/mesh mTLS, external secrets, OPA-style policy decisions, OpenTelemetry, standardized errors/idempotency/deadlines, signed builds/SBOMs, GitOps overlays, PDB/HPA, and HA data services.

Exit: identity/key rotation, negative security tests, telemetry continuity, backup/restore, rolling upgrade, and rollback pass in staging.

## Phase 2 — real replaceable providers

Add and certify at least two LLM routes (one local, one cloud or second local), a real embedding provider, Mem0 or another memory adapter, memory export/import, and isolated MCP server lifecycle.

Exit: the same consumer conformance suite passes against each provider; a policy-only route/provider swap needs no caller deployment and preserves tenant/residency guarantees.

## Phase 3 — durable agents, workflows, and governance

Add the agent-runtime contract, durable run checkpoints, workflow-provider contract, n8n/Temporal/LangGraph adapters as selected, resumable ingestion jobs, human approvals, provider catalog lifecycle, evaluation service, prompt/config versioning, data retention/legal hold, chargeback, and an admin API/UI.

Exit: replay-safe workflows, bounded tool loops, audited approvals, and tenant onboarding/offboarding drills pass.

## Phase 4 — scale and regulated cells

Add multi-cluster routing, GPU fleet integration/autoscaling, regulated tenant cells, DR/failover automation, performance/cost optimization, and continuous red-team/evaluation gates.

Exit: stated SLO/RPO/RTO and isolation targets pass load, chaos, restore, failover, and security exercises.

## Maturity levels

| Level | Evidence |
|---|---|
| executable | one reference path and automated negative/positive tests |
| replaceable | two implementations pass the same contract suite |
| operable | SLOs, telemetry, upgrade/rollback, backup/restore, on-call |
| governed | policy/audit/data lifecycle and certified provider catalog |
| resilient | HA, failure isolation, DR and multi-cluster exercises |

## Principal risks

1. Treating OpenAI-compatible syntax as full semantic compatibility; mitigate with capability descriptors and conformance/evaluation tests.
2. Memory-provider lock-in through opaque embeddings/metadata; mitigate with canonical export and re-embedding plans.
3. Prompt injection causing tool actions; mitigate with independent deterministic tool authorization and approval.
4. Static development security being promoted; block production overlays that reference the dev issuer/CA/mocks.
5. Kubernetes NetworkPolicy support varying by CNI; verify enforcement, do not infer it from accepted YAML.
6. Unbounded provider fallback violating residency; route only among policy-equivalent providers.
