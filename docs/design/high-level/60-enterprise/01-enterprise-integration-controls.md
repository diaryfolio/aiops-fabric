# ViewSense Enterprise Integration and Control Matrix

This document is the acceptance checklist for an enterprise installation. A feature is “catered for” when ViewSense defines its boundary and integration contract; a production deployment is ready only when the enterprise-selected implementation is configured and the evidence test passes.

| Domain | Required capability | Integration contract | Acceptance evidence |
|---|---|---|---|
| SSO | OIDC federation, MFA/conditional access at IdP, group/role claims | standard OIDC discovery/JWKS; issuer/audience/claim mapping config | login, logout, expiry, group change, disabled user, wrong issuer/audience tests |
| workload identity | unique renewable identity per component | SPIFFE/mesh/cloud workload identity and mTLS | peer spoof/expired cert tests and automated rotation |
| authorization | RBAC plus resource/data ABAC | policy decision API/bundle with subject, tenant, action, resource, classification, purpose | allow/deny matrix, policy outage fail-closed, decision audit |
| secrets | dynamic/rotated provider and database credentials | Vault/cloud secret manager through workload identity | no Git/image secrets, revocation and rotation drill |
| API management | validation, quotas, rate limiting, WAF, version policy | OpenAPI import plus gateway-neutral policy requirements | malformed/oversize/rate/tenant abuse tests |
| logging | structured JSON Lines on stdout/stderr from every container | stable field schema; collector via Kubernetes/OTel agent | schema validation and ingestion into chosen backend |
| SIEM | Elastic, Splunk, Sentinel, or equivalent | OTel Collector/Fluent Bit/Vector routing; JSON remains vendor-neutral | search by request/trace/tenant pseudonym and security alert drill |
| metrics | RED/USE and AI-specific metrics | Prometheus/OpenMetrics through OTel Collector | dashboards, recording rules, burn-rate alerts |
| tracing | distributed traces across edge, memory, model, workflow, and MCP | W3C Trace Context and OTLP | one request visible end-to-end with dependency timings |
| security audit | immutable auth, policy, model route, memory admin, MCP, and configuration events | versioned audit-event schema to append-only sink | completeness/replay check, tamper/retention controls |
| data governance | classification, purpose, retention, deletion, legal hold, residency | mandatory metadata and policy hooks on ingest/retrieve/export | retention/deletion/hold and cross-region deny tests |
| privacy | payload minimization, masking/tokenization, access-controlled diagnostics | logging classes and redaction policies | PII canary absent from standard logs and traces |
| model governance | approved catalog, version, capabilities, evaluations, route rationale | provider descriptor and evaluation/promotion API | unapproved model denied; rollback and quality gate |
| MCP governance | catalog, certification, scopes, side effects, approval, egress | MCP gateway administration/invocation contracts | SSRF, injection, undeclared tool, approval, credential isolation tests |
| supply chain | SBOM, signing, provenance, vulnerability/admission policy | OCI artifacts and standard attestations | unsigned/vulnerable image admission is denied |
| resilience | HA, PDB, topology spread, backup, PITR, DR | Kubernetes overlays and state-owner runbooks | node loss, rolling upgrade, restore, region/cluster exercise |
| operations | SLOs, ownership, runbooks, incident/change management | OTel data plus enterprise ITSM/on-call webhooks/APIs | alert-to-ticket/page and incident exercise |
| cost | tenant/provider/token/storage/tool attribution and limits | usage event schema and export API | showback reconciliation and tenant stop-loss test |
| lifecycle | tenant/provider onboarding, offboarding, export, deletion | idempotent admin APIs and GitOps workflows | complete offboarding and credential/data cleanup evidence |
| provider admission | expiring passports, capabilities, evaluations, residency, provenance and revocation | provider passport/evaluation APIs plus policy decision | expired/revoked/unevaluated provider cannot receive new traffic |
| execution evidence | payload-minimized lineage and decision events | append-only evidence API and immutable export | reconstruct route/policy/approval sequence without sensitive payloads |

## JSON log schema

Application containers write one JSON object per line and never write multiline human-formatted access logs. The reference middleware emits:

```json
{
  "timestamp": "2026-08-15T12:00:00.000000+00:00",
  "level": "info",
  "service": "gateway",
  "environment": "production",
  "logger": "viewsense.http",
  "message": "request_completed",
  "event": "http_request",
  "request_id": "...",
  "traceparent": "...",
  "tenant_id": "pseudonymous-tenant-key",
  "principal": "workload-or-user-key",
  "http_method": "POST",
  "http_path": "/v1/responses",
  "http_status": 200,
  "duration_ms": 42.1,
  "outcome": "success"
}
```

Collectors read container stdout using the Kubernetes metadata API and enrich with cluster, namespace, pod, image digest, node, and region. Routing can use OTLP, Elastic Common Schema transforms, Splunk HEC, or another sink-specific exporter. Applications do not embed Elastic/Splunk SDKs, preserving backend replaceability.

Secrets, tokens, authorization headers, raw prompts/completions, memory content, tool arguments/results, and personal data are prohibited in the baseline log class. Security audit events and diagnostic payload capture use separate access, encryption, retention, and approval policies.

## SSO and identity boundary

The edge validates external enterprise tokens against configured issuer/JWKS and maps stable subject, tenant, groups, authentication strength, and session risk. Internal services never accept human tokens as workload identity; the edge performs controlled delegation with a short-lived audience token. SCIM may automate user/group provisioning, but authorization remains based on current verified claims and policy. Break-glass identity is separate, time-bound, approval-gated, and always audited.

Keycloak is an approved integration choice, not part of the mandatory core. Use the official
Keycloak Operator or an existing enterprise service, then configure only issuer/JWKS/audience/claim
mapping in ViewSense. SPIRE is similarly operated at cluster scope. OPA is suited to a local sidecar
for low-latency fail-closed decisions, while a centrally managed external OPA endpoint is appropriate
only when its availability, mTLS, egress, and policy-bundle lifecycle meet the protected operation's
SLO.

## Suite selection rule

Every product is classified as bundled, adapter, managed dependency, or external and separately as
validated, configuration-ready, or planned. The machine-readable source is
`fabric/product-catalog.json`; Helm profiles are curated configuration, not evidence of an upstream
installation. Production acceptance requires the named conformance and failure tests in addition to
successful rendering.

## Telemetry deployment pattern

Applications emit JSON stdout, OpenMetrics, and OTLP using vendor-neutral semantic conventions. A per-cluster collector layer batches, redacts, samples, and routes data to enterprise systems. Security audit is not sampled. Tail sampling can retain errors/slow traces while limiting routine prompt-path telemetry cost. Collector unavailability uses bounded buffers and must never fill application disks; regulated operations can be configured to fail closed when mandatory audit cannot be delivered.

## Current reference status

Implemented now: JSON access/runtime logs, request correlation propagation, mTLS,
audience/scoped tokens, signed Trust Envelope tenant delegation, external OIDC edge verification,
built-in/OPA provider admission, append-only safe evidence metadata, durable bounded agent state,
PostgreSQL/pgvector and Mem0 adapter boundaries, restricted pods, network policies, API schemas,
profile rendering, and positive/negative smoke tests. Configuration-ready but environment-dependent:
the credential-isolated OpenAI adapter, Keycloak/generic OIDC, SPIRE consumption architecture, OPA
sidecar, Mem0, and collector routing. OpenAI acceptance additionally requires a provider project/key,
residency and retention review, egress enforcement, spend limits, rotation, and the documented live
memory-grounding test.
Planned: workflow adapters, SCIM, signed third-party passports, evaluation runners/datasets,
immutable evidence/audit export, full OTel instrumentation/exporters, external secrets, HA/DR,
autoscaling, supply-chain admission, and ITSM. Production readiness requires selecting and testing
those integrations; the local issuer and mock providers do not satisfy them.
