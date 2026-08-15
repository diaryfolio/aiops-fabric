# ViewSense Component and Ownership Model

## Edge API

Owns external authentication integration, tenant derivation, schema validation, rate limits, and public compatibility. It does not select provider URLs, hold provider credentials, or implement agent loops.

## Request orchestrator

Owns a bounded request state machine: policy evaluation, context assembly, inference calls, optional approved tools, and response assembly. Long-running durable business processes belong behind a workflow-provider API, not inside request handlers.

## LLM gateway

Normalizes model IDs, capabilities, errors, token usage, routing, deadlines, and provider credentials. Local vLLM/Ollama and cloud OpenAI/Azure/other endpoints are adapters. The gateway must not store conversation memory.

## Memory gateway and providers

The gateway enforces tenant/purpose policy and exposes canonical records. A provider implements storage, embedding, retrieval, filtering, retention, and export. The reference provider uses PostgreSQL/pgvector; Mem0 is a future adapter, not a replacement for the stable gateway.

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

The online agent runtime is a durable, bounded state machine that uses only the LLM, memory, policy, workflow, and MCP APIs. It owns run/checkpoint state but no provider data. The ingestion service owns document ingestion jobs and deterministic chunking; parsing, enrichment, embeddings, and vector persistence remain replaceable stages. See the dedicated agentic design for tool loops, approvals, ingestion poisoning controls, and workflow-provider selection.

## Identity and policy

Human identity federates through enterprise OIDC. Workload identity uses SPIFFE/SPIRE, mesh identity, or equivalent. An external policy decision point such as OPA can evaluate tenant, classification, model, memory purpose, tool side effects, and residency. The repository's issuer is development-only.

## Observability and audit

All components emit OpenTelemetry metrics/traces/log correlation. Security audit records are append-only, payload-minimized, and separate from troubleshooting logs. Audit pipeline failure follows tenant policy and can fail closed for regulated tool/model operations.

## Reference versus replaceable choices

| Capability | Reference slice | Replaceable examples |
|---|---|---|
| LLM provider | deterministic mock | vLLM, Ollama, OpenAI, Azure OpenAI |
| memory provider | PostgreSQL + pgvector | Mem0 adapter, Qdrant adapter, managed vector service |
| MCP provider | echo test server | certified enterprise MCP servers |
| identity | local RSA token issuer | enterprise IdP + workload identity |
| deployment | Kustomize development base | Helm/GitOps environment overlays |

## Repository module boundary

Runtime implementations remain small, independently deployable Python packages under `src/viewsense_*`; they are not nested inside deployment packaging. The `fabric/<capability>/` directories are the machine-readable installable catalog. Every capability directory contains a `module.json` descriptor and README that declare maturity, owned contracts, implementation paths, Helm selection paths, data ownership, and bundled/external provider choices. `fabric/module.schema.json` defines the descriptor format and the catalog conformance test rejects missing, undocumented, or dangling module entries.

This separation avoids coupling application source layout to Helm or a future operator while ensuring packaging folders are executable metadata rather than placeholders. A `contract-only` catalog entry is deliberately visible but cannot be represented as implemented; Helm and documentation must retain the same maturity statement.
