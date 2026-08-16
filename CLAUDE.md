# ViewSense AI® Repository Instructions

These instructions apply to every human or AI-assisted change in this repository.

## Mission

ViewSense AI® is a Kubernetes-native, API-first, zero-trust enterprise AI backbone. Preserve component replaceability, provider neutrality, tenant isolation, workload identity, and data ownership boundaries in every change.

## Mandatory design-sync workflow

Before editing code, APIs, deployment assets, policy, dependencies, or runtime configuration:

1. Read `docs/prompts/governance/major-change-policy.md` and classify the change as `minor` or `major`. If uncertain, use `major`.
2. Read the relevant documents under `docs/design/high-level/`, including the enterprise control matrix for changes affecting identity, telemetry, governance, security, operations, or integrations.
3. Record which contracts, trust boundaries, data owners, deployment resources, SLOs, and failure modes change.

In the same change set:

1. Update affected design documents before declaring implementation complete.
2. Update `docs/design/high-level/00-implementation-conformance.md` whenever a service, route, runtime edge, state owner, provider maturity, trust boundary, or verification path changes.
3. Update OpenAPI/event/provider contracts and compatibility notes when behavior changes.
4. Update security controls, threat model, NetworkPolicy/RBAC/secret requirements, and audit events when data flow or access changes.
5. Update deployment manifests, probes, resources, upgrade/rollback, backup/restore, and observability requirements when runtime behavior changes.
6. Add or update unit, contract, integration, and negative security tests proportional to risk.
7. Keep all service logs as structured JSON Lines and preserve request/trace correlation. Never log tokens, credentials, prompts, memory content, or tool payloads by default.
8. When a published Markdown page is added, moved, or renamed, update both `scripts/build-docs.sh`
   and `zensical.toml`; never edit generated `docs-site/` or `site/` content.

## Architecture rules

- Use `ViewSense AI®` for the human-facing product name in prose, generated documentation,
  API titles, and operator messages. Preserve established ASCII protocol and deployment identifiers
  such as `X-ViewSense-Tenant`, `viewsense-dev`, `VS_*`, package names, image names, and URLs.
- Communicate across components only through versioned APIs/events; never read another service's database.
- Keep provider SDKs and credentials inside provider adapters.
- Require encrypted transport plus explicit audience/scoped authorization at every internal hop.
- Derive tenant from verified identity; never trust caller-selected tenant headers.
- Use deny-by-default network and authorization policy, least privilege, bounded deadlines/retries, and fail-closed security behavior.
- Keep Kubernetes as the canonical packaging target and confine development resources to `viewsense-dev` unless an environment overlay explicitly defines another namespace.
- Mark mocks, local issuers, static development PKI, and deterministic embeddings as non-production.
- Avoid vendor lock-in in logging/metrics/traces. The production target is JSON stdout, propagated W3C trace context, OpenMetrics, and OTLP-compatible telemetry routed through collectors/exporters; record any implementation gap in the conformance map.

## Required validation

At minimum run:

```bash
make unit
make lint
kubectl kustomize deploy/kubernetes/base >/dev/null
```

For any change to published documentation or its navigation, also run:

```bash
make docs-build
```

For runtime, security, contract, or Kubernetes changes, also run:

```bash
make k8s-deploy
make k8s-test
```

Do not claim Kubernetes security enforcement from manifest validation alone; verify the cluster CNI enforces NetworkPolicy and include negative connectivity tests for production readiness.

## Required completion block

Every completed change must include:

```text
Design Sync Report
- Change Classification: <minor|major>
- Design Docs Updated: <list>
- Code Areas Updated: <list>
- Architecture Delta: <summary>
- Tests/Evidence: <list>
- Known Production Gaps: <list or none>
- Sync Status: <PASS|FAIL>
```

`Sync Status` is `FAIL` when implementation, contracts, security, deployment, observability, tests, or design documentation disagree. Do not merge a failed design sync.
