# Enterprise AI Platform on Kubernetes - Technical System Design 02

## 1. Deployment Topology (Multi-Cloud)

This document defines the reference deployment topologies for EKS, GKE, AKS, and bare-metal Kubernetes while preserving a single logical platform model.

## 2. Environment Model

- Management plane:
  - GitOps controllers (Argo CD or Flux), policy controllers, fleet metadata.
- Shared services plane:
  - CI artifacts, image registry, secrets integration, central observability backends.
- Runtime plane:
  - Per-environment clusters (`dev`, `staging`, `prod`) with tenancy boundaries.

Recommended pattern: separate production inference/memory workloads from non-production clusters to reduce noisy neighbor impact and simplify compliance scope.

## 3. Cluster Archetypes

### 3.1 Control Cluster

Hosts low-latency and platform control APIs:

- AI orchestrator APIs
- MCP registry/control plane
- workflow API frontends
- platform authn/authz adapters

Node profile:

- CPU optimized nodes, no GPUs
- strict PDB and anti-affinity for control services

### 3.2 Inference Cluster

Hosts LLM runtime workloads:

- vLLM, Triton, optional Ollama services
- model gateway adapters
- async inference workers

Node profile:

- GPU pools by class (cost/performance tiers)
- dedicated node pools for premium SLO models

### 3.3 Data Cluster (Optional Dedicated)

Hosts memory and stateful data services:

- vector database
- metadata PostgreSQL
- Redis
- queue systems where not managed externally

Node profile:

- memory/storage optimized, zone distributed

## 4. Tenant Isolation Patterns

### Pattern A: Soft Multi-Tenancy (Default)

- Namespace-level isolation.
- Tenant-scoped RBAC and network policies.
- Shared control and inference planes with strict quotas.

Use when:

- medium risk profile
- cost efficiency prioritized

### Pattern B: Hard Multi-Tenancy

- Dedicated namespace groups plus dedicated node pools.
- Optional separate clusters per regulated tenant.
- Isolated storage partitions and keys per tenant.

Use when:

- high compliance or regulated data
- strict performance isolation required

## 5. Capacity and Sizing Baseline

Sizing should be based on measured token demand rather than request count alone.

### 5.1 Key Inputs

- Concurrent sessions by tenant
- Average prompt tokens and completion tokens
- Target p95 latency per model tier
- Tool-call amplification factor for agent workflows

### 5.2 Inference Capacity Formula (Practical)

Let:

- $R$ = requests per second
- $T$ = average total tokens per request
- $S$ = target served tokens per second per replica
- $U$ = utilization target (for example, $0.65$)

Required replicas approximately:

$$
N = \left\lceil \frac{R \times T}{S \times U} \right\rceil
$$

Add headroom for burst and failover (minimum additional 20-30% for production tiers).

## 6. Traffic Engineering

- Global traffic entry via cloud load balancing + regional ingress.
- Weighted routing by model tier and tenant policy.
- Retry policy with idempotency keys for non-streaming calls.
- Streaming path with circuit breakers and timeout budgets per upstream.

Service mesh policy recommendations:

- strict mTLS
- locality-aware load balancing
- outlier detection on inference pods

## 7. Stateful Services Placement

- Vector DB:
  - zone-aware shards/replicas
  - SSD-backed storage classes
- PostgreSQL:
  - HA pair or managed HA service
  - PITR enabled
- Redis:
  - sentinel/cluster mode based on throughput and keyspace size
- Queue bus:
  - NATS JetStream for lightweight operations
  - Kafka for heavy replay and analytics retention

## 8. GitOps and Promotion Topology

- Repository layout by layers:
  - `platform/base`
  - `platform/overlays/dev`
  - `platform/overlays/staging`
  - `platform/overlays/prod`
- Promotion by pull request with policy checks and signed commits.
- Progressive delivery gates:
  - canary in staging
  - synthetic load verification
  - controlled tenant pilot in production

## 9. Cloud-Specific Notes

- EKS:
  - use IRSA for workload identity.
  - isolate GPU node groups with taints.
- GKE:
  - use Workload Identity and node auto provisioning controls.
  - enforce binary authorization where available.
- AKS:
  - use managed identity and Azure Policy integration.
  - separate system and user node pools.
- Bare metal:
  - validate CNI and storage stack reliability under failure injection.
  - ensure GPU operator lifecycle and firmware compatibility control.

## 10. Availability Targets by Tier

- Tier 0 (control plane APIs): 99.9+
- Tier 1 (premium inference endpoints): 99.5+
- Tier 2 (standard inference and background workflows): 99.0+

Each tier must define explicit SLO, error budget policy, and auto-roll back criteria.
