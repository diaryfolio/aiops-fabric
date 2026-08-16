# ViewSense Component and Ownership Model

## Edge API

Owns external authentication integration, tenant derivation, schema validation, rate limits, and public compatibility. It does not select provider URLs, hold provider credentials, or implement agent loops.

## Request orchestrator

Owns a bounded request state machine: policy evaluation, context assembly, inference calls, optional approved tools, and response assembly. Long-running durable business processes belong behind a workflow-provider API, not inside request handlers.

## LLM gateway

Normalizes model IDs, capabilities, errors, token usage, routing, and deadlines. Local vLLM/Ollama
and cloud OpenAI/Azure/other endpoints are adapters. Provider credentials belong only to the owning
adapter, not the LLM gateway. The gateway must not store conversation memory.

The bundled OpenAI adapter translates the internal mTLS/scoped-token request into an OpenAI Bearer
request. It owns the API key, exact upstream URL, configured model, outbound field minimization,
timeout, and safe error translation. It owns no memory: retrieved memory reaches it only as bounded
request context assembled by the orchestrator.

## Memory gateway and providers

The gateway enforces tenant/purpose policy and exposes canonical records. A provider implements storage, embedding, retrieval, filtering, retention, and export. The reference provider uses PostgreSQL/pgvector. The Mem0 OSS/Platform adapter is executable and keeps its API key, tenant/owner pseudonymization, upstream paths, and response normalization inside the provider boundary; Mem0 remains separate from the stable gateway.

Memory is split conceptually into:

- episodic/user memory;
- governed knowledge/RAG documents;
- short-lived request/session context.

These have different retention and authorization and must not be merged into one unclassified vector collection.

## MCP gateway and runtime

The gateway owns the approved server catalog, capability metadata, policy checks, invocation audit, timeouts, and egress allow-list. MCP servers run as untrusted provider workloads with dedicated identities and network/credential boundaries. Registration never grants execution automatically; production adds certification and approval state.

## Workflow provider (planned)

Durable workflow engines (Temporal, Argo Workflows, n8n, or an enterprise product) implement a workflow contract. The platform does not assume that a low-code engine is safe for autonomous tool loops. Workflow definitions are versioned artifacts with bounded execution and human approval points.

## Agent runtime and ingestion

The bundled online agent runtime is a persistent bounded state machine. It implements idempotent run
creation, optimistic versions, step/cost/tool budgets, checkpoint, approval/rejection, cancellation,
terminal states, and ordered event history in its own PostgreSQL database. It owns run/checkpoint
state but no provider data. Automatic plan/model/tool workers and external workflow adapters are not
yet implemented. The ingestion service owns document ingestion jobs and deterministic chunking;
parsing, enrichment, embeddings, and vector persistence remain replaceable stages.

## Identity and policy

Human identity federates through enterprise OIDC; the edge verifier supports generic OIDC and
Keycloak-compatible issuer/JWKS/claim mapping. Workload identity uses SPIFFE/SPIRE, mesh identity,
or equivalent. SPIRE is installed as a platform dependency and ViewSense consumes SVIDs through an
SDS-capable proxy/mesh rather than embedding SPIRE into application code. Provider admission uses
the built-in checks or a fail-closed OPA decision API; the chart can place OPA beside governance.
The repository's issuer and static PKI are development-only.

## Governance and evidence

The governance API owns provider passports, evaluation evidence, admission state, and safe
execution evidence. Providers cannot mark themselves admitted, and callers cannot choose an
evidence producer: both transitions are derived or enforced server-side. Its database is owned
and unreachable from other applications. Production policy engines, signature/transparency
verification, immutable evidence export, retention, and legal hold remain separate adapters and
maturity gates.

## Observability and audit

All components emit OpenTelemetry metrics/traces/log correlation. Security audit records are append-only, payload-minimized, and separate from troubleshooting logs. Audit pipeline failure follows tenant policy and can fail closed for regulated tool/model operations.

## Reference versus replaceable choices

| Capability | Reference slice | Replaceable examples |
|---|---|---|
| LLM provider | deterministic mock; OpenAI credential adapter | vLLM, Ollama, Azure OpenAI |
| memory provider | PostgreSQL + pgvector; Mem0 adapter | Qdrant adapter, managed vector service |
| agent runtime | persistent bounded state machine | LangGraph-compatible adapter |
| MCP provider | echo test server | certified enterprise MCP servers |
| identity | local RSA token issuer | enterprise IdP + workload identity |
| governance/evidence | owned PostgreSQL reference | external policy and immutable evidence sinks |
| deployment | Kustomize development base | Helm/GitOps environment overlays |

## Repository module boundary

Runtime implementations remain small, independently deployable Python packages under `src/viewsense_*`; they are not nested inside deployment packaging. The `fabric/<capability>/` directories are the machine-readable installable catalog. Every capability directory contains a `module.json` descriptor and README that declare maturity, owned contracts, implementation paths, Helm selection paths, data ownership, and bundled/external provider choices. `fabric/module.schema.json` defines the descriptor format and the catalog conformance test rejects missing, undocumented, or dangling module entries.

This separation avoids coupling application source layout to Helm or a future operator while ensuring packaging folders are executable metadata rather than placeholders. A `contract-only` catalog entry is deliberately visible but cannot be represented as implemented; Helm and documentation must retain the same maturity statement.
