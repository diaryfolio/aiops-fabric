# ViewSense Kubernetes Deployment Design

## Canonical packaging

Kubernetes is the deployment contract. The portable base uses Deployments, StatefulSets, Services, Secrets, PVCs, probes, resource controls, service accounts, and NetworkPolicy. EKS, GKE, AKS, OpenShift, and bare-metal differences belong in overlays. Docker Compose mirrors process/network boundaries only and is not a production topology.

## Namespace and cluster patterns

| Profile | Isolation | Suitable for |
|---|---|---|
| development | one `viewsense-dev` namespace, single replicas | contract and integration testing |
| standard | separate edge/control/provider/data namespaces | normal enterprise production |
| regulated | dedicated provider/data cluster or tenant cell | strict residency and blast-radius controls |
| GPU scale | control cluster plus one or more inference clusters | large model fleets and independent capacity |

The current manifests intentionally touch only `viewsense-dev`. Production overlays must not reuse development keys, issuer, mock providers, image tags, `imagePullPolicy: Never`, or single-replica databases.

## Workload rules

- one service account and workload identity per component;
- no automatic Kubernetes API token mounts unless a component genuinely calls the API;
- restricted Pod Security, non-root users, read-only roots, no added capabilities;
- default-deny ingress and egress, then explicit source/destination/port policies;
- provider credentials mounted only into the owning adapter;
- topology spread, anti-affinity, disruption budgets, and at least two replicas for stateless production services;
- stateful services use encrypted storage, topology-aware placement, backups, and tested restore.

## Installation sequence

1. Verify context, namespace, admission policies, storage class, ingress, DNS, and network-policy enforcement.
2. Install workload identity/certificate automation and external secret synchronization.
3. Create the ViewSense namespaces and default-deny policies.
4. Install owned data services or bind to managed equivalents, including the isolated governance store.
5. Deploy identity/policy and governance dependencies, provider adapters, control services, then edge.
6. Run conformance and zero-trust negative tests before accepting traffic.
7. Register real providers through audited configuration and remove mocks.

## Product installation modes

- `bundled`: ViewSense deploys and tests the component and owns its lifecycle, such as the bounded
  agent runtime and PostgreSQL/pgvector reference provider.
- `adapter`: ViewSense deploys the contract/credential boundary while the product is separate, such
  as the Mem0 adapter.
- `managed-dependency`: a platform team installs the cluster service with its upstream lifecycle,
  such as SPIRE, an OpenTelemetry Collector, or external secrets.
- `external`: ViewSense configures an authenticated endpoint, such as Keycloak/OIDC, a cloud LLM,
  or a workflow system.

The `enterprise-suite` profile describes integration intent. It does not create cluster-scoped
Keycloak, SPIRE, n8n, or OpenTelemetry operators. OPA can be embedded as a governance sidecar
because it is a stateless local policy decision point with a narrow loopback API. Every external or
managed selection requires credentials, CA trust, explicit egress, conformance tests, version
pinning, upgrade/rollback ownership, and a provider passport before production routing.

The `openai` Helm profile deploys only the ViewSense `openai-adapter`; it does not create or manage
an OpenAI account. Its Secret must be supplied by the platform secret controller. The development
overlay permits public IPv4 HTTPS while excluding private, loopback, link-local, and reserved
ranges. Production must replace that broad rule with an egress proxy or CNI FQDN policy restricted
to `api.openai.com`, plus DNS/proxy failure tests. `make openai-disable` restores the mock route and
deletes the development credential Secret and adapter resources.

## Sizing method

Control-plane sizing is driven by concurrent requests and provider wait time. Inference sizing is driven by tokens, context length, batching, quantization, and model/GPU class:

$$
replicas = \left\lceil \frac{requests/sec \times average\ total\ tokens}{measured\ tokens/sec/replica \times target\ utilization} \right\rceil
$$

Use load tests from the actual model/runtime; nominal GPU specifications are insufficient. Reserve 25–35% failure/burst headroom for production. Memory-provider sizing includes corpus size, vector dimension, write rate, filter cardinality, index build overhead, and retention. MCP runtimes are sized per connector side effects and external rate limits rather than token load.

## Provider placement and routing

Provider descriptors include locality, residency, classification ceiling, capabilities, and cost class. Routing may cross clusters only through authenticated encrypted endpoints. It must never silently move restricted data from a local route to a public-cloud fallback. DNS names and provider URLs are configuration validated against egress policy.

## Development workflow in this repository

`scripts/k8s-deploy-dev.sh` builds the image, imports it to the active k3d cluster, creates generated Secrets, applies `deploy/kubernetes/base`, and waits for rollout in `viewsense-dev`. It is an installation/update operation, not a routine cluster-start command. An existing stopped cluster resumes with `k3d cluster start cks`, after which Kubernetes restores its workloads and retained volumes. The base includes an independently addressed governance API and database with explicit NetworkPolicy. On an installed suite, `make openai-enable` prompts without echo, creates the provider Secret, and applies `deploy/kubernetes/overlays/openai` without rebuilding images; `make openai-enable-fresh` performs the full deployment first. `scripts/k8s-test.sh` runs a namespaced smoke Job that validates provider admission and evidence alongside the core AI path. The scripts validate their fixed namespace before mutation. The operator-oriented lifecycle and recovery commands are maintained in the top-level `QUICKSTART.md`.

## Production gaps from the reference

Production requires an ingress/API gateway, enterprise OIDC, SPIFFE/mesh certificates, external secrets, signed immutable images, HA databases or managed data services, autoscaling, PDBs, telemetry collectors, backup schedules, policy engine integration, and GitOps overlays. These gaps are explicit rather than hidden behind the development manifest.
