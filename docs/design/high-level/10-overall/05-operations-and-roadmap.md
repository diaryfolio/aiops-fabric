# Design 10.5 - Operations Baseline and Roadmap

## Concept Alignment

Operations and roadmap planning assume the canonical flow `Enterprise User or App -> API Gateway and Auth -> Fabric Layer`, with Security and Zero Trust plus Observability applied across all Fabric services.

## Day-2 Operations Baseline

- Security:
  - SSO, RBAC, ABAC, zero-trust enforcement.
- Observability:
  - Prometheus, Grafana, logs, OpenTelemetry traces.
- Reliability:
  - SLOs, HA policies, failover runbooks, DR testing.

## Reference Deployment Domains

- ai-edge
- ai-control-plane
- ai-inference
- ai-memory
- ai-workflows
- ai-observability
- ai-security

## Repository Alignment Guidance

Current structure is valid and extensible.

Recommended additions for maturity:

- platform or infra for GitOps overlays and environment manifests.
- fabric/observability for dashboards and telemetry collectors.
- fabric/security for policy bundles and RBAC templates.
- runbooks for operational procedures.

## Condensed Implementation Roadmap

1. Foundation: GitOps, ingress, identity, and baseline security.
2. Inference and gateway: model serving, autoscaling, API compatibility.
3. Memory and retrieval: vector, metadata, ingestion, and context APIs.
4. MCP and workflows: tool runtime, connectors, orchestration loops.
5. Day-2 maturity: SLOs, DR drills, security hardening, compliance evidence.
