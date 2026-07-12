# Design 10.4 - Component Breakdown

## Concept Alignment

Canonical flow: `Enterprise User or App -> API Gateway and Auth -> Fabric Layer`.

The layers below define Fabric internals. Security and Zero Trust plus Observability are cross-cutting requirements for every layer.

## Layer A - LLM Hosting and Inference

- Primary serving runtime: vLLM.
- Optional runtimes: Triton and Ollama through abstraction gateway.
- Autoscaling: KEDA and optional Knative profiles.
- Caching and async: Redis and queue bus integration.

## Layer B - Memory and Context

- Context API and retrieval pipeline with hybrid search.
- Storage separation:
  - vector index
  - metadata catalog
  - object artifacts
- Recommended stores: Qdrant or Milvus or pgvector, PostgreSQL, object storage.

## Layer C - Hosted MCP Runtime

- Control plane for registry, policy, and lifecycle.
- Data plane for isolated connector execution.
- Security: workload identity, short-lived secrets, RBAC/ABAC policy checks.

## Layer D - Workflow Orchestration

- n8n or Tines for deterministic orchestration.
- Supports synchronous and asynchronous execution paths.
- Enforced loop guardrails for cost and safety.

## Layer E - Cloud-Native Foundation

- GitOps with Argo CD or Flux.
- Service mesh with mTLS and traffic policy.
- Policy enforcement with OPA/Gatekeeper or Kyverno.
- Multi-cloud deployment baseline (EKS/GKE/AKS/bare metal).

## Replaceability Matrix

- LLM runtime: swappable via gateway contract.
- Vector database: swappable behind retrieval API.
- Workflow engine: swappable behind orchestration API.
- MCP connector provider: swappable via connector contract.
