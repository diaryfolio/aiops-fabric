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
4. Install owned data services or bind to managed equivalents.
5. Deploy identity/policy dependencies, provider adapters, control services, then edge.
6. Run conformance and zero-trust negative tests before accepting traffic.
7. Register real providers through audited configuration and remove mocks.

## Sizing method

Control-plane sizing is driven by concurrent requests and provider wait time. Inference sizing is driven by tokens, context length, batching, quantization, and model/GPU class:

$$
replicas = \left\lceil \frac{requests/sec \times average\ total\ tokens}{measured\ tokens/sec/replica \times target\ utilization} \right\rceil
$$

Use load tests from the actual model/runtime; nominal GPU specifications are insufficient. Reserve 25–35% failure/burst headroom for production. Memory-provider sizing includes corpus size, vector dimension, write rate, filter cardinality, index build overhead, and retention. MCP runtimes are sized per connector side effects and external rate limits rather than token load.

## Provider placement and routing

Provider descriptors include locality, residency, classification ceiling, capabilities, and cost class. Routing may cross clusters only through authenticated encrypted endpoints. It must never silently move restricted data from a local route to a public-cloud fallback. DNS names and provider URLs are configuration validated against egress policy.

## Development workflow in this repository

`scripts/k8s-deploy-dev.sh` builds the image, imports it to the active k3d cluster, creates generated Secrets, applies `deploy/kubernetes/base`, and waits for rollout in `viewsense-dev`. `scripts/k8s-test.sh` runs a namespaced smoke Job. The scripts validate their fixed namespace before mutation.

## Production gaps from the reference

Production requires an ingress/API gateway, enterprise OIDC, SPIFFE/mesh certificates, external secrets, signed immutable images, HA databases or managed data services, autoscaling, PDBs, telemetry collectors, backup schedules, policy engine integration, and GitOps overlays. These gaps are explicit rather than hidden behind the development manifest.
