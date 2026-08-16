# ViewSense Agent Runtime, Ingestion, and Workflow Design

## Design decision

ViewSense treats “agentic” as a governed execution capability, not permission for a model to call arbitrary tools. It separates three replaceable capabilities:

1. **Online agent runtime:** bounded plan/act/observe execution for interactive or background goals.
2. **Ingestion pipeline:** resumable document processing that can use deterministic and AI-assisted stages before memory/index writes.
3. **Workflow provider:** durable business/event orchestration and human approvals through n8n, Temporal, Argo Workflows, or another adapter.

All three use APIs; none can directly read another service's database or receive all provider credentials.

## Online agent state machine

```mermaid
stateDiagram-v2
    [*] --> Received
    Received --> PolicyChecked
    PolicyChecked --> ContextRetrieved
    ContextRetrieved --> Planned
    Planned --> ApprovalPending: consequential action
    ApprovalPending --> Acting: approved or edited
    ApprovalPending --> Cancelled: rejected or expired
    Planned --> Acting: read-only approved tool
    Acting --> Observed
    Observed --> Evaluated
    Evaluated --> Planned: more work and budget remains
    Evaluated --> Committing: goal satisfied
    Committing --> Completed
    Planned --> Failed: step/deadline budget exhausted
```

The model proposes; deterministic policy authorizes; the MCP gateway executes. Run state includes tenant, subject, objective, immutable policy/config/model versions, current step, observations, token/tool/time/cost budgets, pending approvals, and checkpoint version. Provider credentials and raw long-term memory do not belong in agent state.

### Agent API contract

- `POST /v1/agent-runs` creates an idempotent run and returns a run resource.
- `GET /v1/agent-runs/{id}` reads current state and safe event summaries.
- `POST /v1/agent-runs/{id}:resume` supplies an approval/edited action or external signal.
- `POST /v1/agent-runs/{id}:cancel` requests cooperative cancellation.
- `GET /v1/agent-runs/{id}/events` returns ordered versioned state events; SSE is a compatible
  future transport.

Implementations such as a built-in state machine or LangGraph remain behind this contract. Durable state is mandatory for background runs and approval pauses. Side effects use idempotency keys and are recorded before/after execution to prevent replay after recovery.

### Guardrails

- maximum steps, model calls, tool calls, wall time, tokens, cost, parallel branches, and observation size;
- per-tool read/write/destructive classification and argument policy;
- mandatory human approval for high-impact or irreversible actions;
- no tool discovered from prompt content becomes callable without catalog approval;
- tool output is untrusted data and cannot alter system policy;
- cancellation, checkpoint, retry, and compensation semantics per step;
- output/evidence evaluation before committing memory or side effects;
- complete model-route, policy-decision, approval, and MCP invocation audit.

The bundled reference now persists tenant-bound state transitions and approval actors in an ordered
run-event table and exposes them through the Agent API. The separate governance API implements the
payload-minimized Evidence Event v1 boundary. Exporting every agent event transactionally to that
evidence boundary, SSE streaming, autonomous plan/tool workers, and side-effect replay protection
remain next slices. Prompts, completions, memory, arguments, results, credentials, and personal data
are excluded from baseline events.

## Governed ingestion pipeline

```mermaid
flowchart LR
    S["Source connector"] --> Q["Ingestion job"]
    Q --> P["Parse / OCR"]
    P --> C["Classify, malware scan, redact"]
    C --> K["Deterministic structure-aware chunking"]
    K --> E["Optional agentic enrichment"]
    E --> V["Embedding gateway"]
    V --> W["Memory/index writer"]
    W --> X["Retrieval evaluation and publish"]
    X -->|"pass"| A["Active collection"]
    X -->|"fail"| R["Quarantine / review"]
```

Chunking is a strategy provider. Baseline strategies are paragraph/basic, by-title/section, by-page, table-aware, code-aware, and semantic similarity. Hard limits come from the selected embedding/model capability. Overlap is explicit and versioned. The original artifact and parsed element lineage are retained so an index can be rebuilt without trusting old vectors.

AI-assisted enrichment may add contextual prefixes, summaries, entities, questions, classifications, or relationship edges, but it runs after security classification and before embeddings. Generated enrichment is labelled, confidence-scored, provenance-linked, schema-validated, and never overwrites source text. Low-confidence or policy-sensitive output is quarantined. This prevents an LLM from silently corrupting enterprise knowledge.

### Ingestion API contract

- `POST /v1/ingestion-jobs` accepts a source reference, collection, strategy/config version, classification, and idempotency key.
- `GET /v1/ingestion-jobs/{id}` reports per-stage counts, failures, checkpoints, and safe diagnostics.
- `POST /v1/ingestion-jobs/{id}:cancel|retry|publish` controls lifecycle with authorization.
- events describe stage progress and dead-letter items; large artifacts use object references, not event payloads.
- re-ingestion uses content hashes and source versions to deduplicate and tombstone superseded chunks.

The current executable slice exposes synchronous `POST /v1/documents:ingest` with deterministic paragraph-aware hard-limit/overlap chunking and writes only through the memory API. Durable jobs, parsers/OCR, embedding gateway, enrichment, evaluation, quarantine, and publish phases are the next implementation slice.

## Workflow provider boundary

The workflow gateway exposes versioned start/status/signal/cancel APIs and CloudEvents. Provider adapters translate these into n8n workflows, Temporal workflows, Argo Workflows, or another engine. The agent runtime can request a workflow, and a workflow can request an agent run, but callbacks use signed correlation resources to prevent recursive/unbounded execution.

### When to use what

| Need | Preferred capability |
|---|---|
| interactive, stateful plan/tool loop | agent runtime such as a LangGraph adapter or built-in bounded graph |
| business SaaS integrations, triggers, low-code automation, approval channels | n8n adapter |
| long-lived mission-critical execution, timers, retries, compensation | Temporal adapter |
| Kubernetes batch/GPU/data pipeline jobs | Argo Workflows adapter |
| simple event fan-out | event bus/worker, not an agent |

n8n is valuable because of its connectors, AI/tool nodes, and human-review patterns, but n8n credentials stay in its provider boundary and every action still goes through ViewSense identity/policy/MCP rules. Workflow definitions are signed/versioned; production execution data is redacted and retention-controlled.

## Complete modular product suite

| Capability | Required contract | Example product class |
|---|---|---|
| edge/API management | OpenAPI, OIDC, quotas, WAF | enterprise gateway/ingress |
| identity/policy/secrets | OIDC/JWKS, workload identity, policy API | enterprise IdP, SPIFFE/mesh, OPA, Vault |
| model gateway/inference | OpenAI-compatible plus capabilities | vLLM/Ollama/local or approved cloud models |
| embeddings/reranking | provider-neutral embedding/rerank APIs | local sentence-transformer or cloud adapter |
| memory/RAG | canonical memory, export/import, filters | PostgreSQL/pgvector, Mem0, Qdrant-class adapter |
| ingestion | parse/OCR/chunk/enrich/evaluate contracts | built-in workers or Unstructured-class adapter |
| object/catalog data | S3-compatible artifacts plus governed metadata | enterprise object store and catalog |
| agent runtime | run/checkpoint/approval/event contract | built-in graph or LangGraph-class adapter |
| workflows | start/status/signal/cancel contract | n8n, Temporal, Argo Workflows |
| tools/connectors | governed MCP gateway/runtime | isolated certified MCP servers |
| evaluation/guardrails | dataset/run/score/promotion contract | offline and online evaluation providers |
| observability/SIEM | JSON, OpenMetrics, OTLP, audit events | enterprise collector to Elastic/Splunk/etc. |
| operations/FinOps | SLO, usage, quota, chargeback APIs | enterprise dashboards, ITSM, cost systems |

Selection order is security/residency → capability/quality → reliability/operability → cost. Product names stay in Helm/operator provider configuration; callers see only ViewSense contracts.

## Operator roadmap

Helm installs chosen modules. A future ViewSense operator should reconcile custom resources such as `ModelProvider`, `MemoryProvider`, `MCPServer`, `WorkflowProvider`, `AgentProfile`, and `IngestionPipeline`; validate conformance/certification; roll credentials; publish readiness; and block incompatible or policy-violating provider changes. It must not become a second workflow engine or store provider secrets in status.
