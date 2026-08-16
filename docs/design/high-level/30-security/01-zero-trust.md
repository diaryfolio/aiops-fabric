# ViewSense Zero-Trust Security Model

## Security objective

Compromise of one component must not grant implicit access to another component, another tenant, provider credentials, or a different data plane. Controls are layered: network reachability, workload TLS identity, audience/scoped authorization, tenant/data policy, provider egress policy, and audit.

## Trust boundaries and controls

| Boundary | Authentication | Authorization | Containment |
|---|---|---|---|
| client → edge | enterprise OIDC and optional client mTLS | tenant/user RBAC, ABAC, quota | ingress/WAF and no direct internal exposure |
| edge → orchestrator | workload mTLS + audience token | `orchestrate.invoke` | explicit NetworkPolicy |
| orchestrator → gateway | workload mTLS + audience token | capability-specific scope | no provider credential in orchestrator |
| gateway → provider | workload mTLS + provider audience | `provider.invoke`, provider policy | dedicated provider network/namespace |
| provider → database | database identity and TLS | owner schema/user only | only owning provider can reach store |
| MCP → enterprise system | connector workload identity | per-tool/action/data policy | egress allow-list and isolated credentials |

## Identity

Human identity federates to the enterprise IdP using OIDC Authorization Code + PKCE or workload-appropriate OAuth flows. Workloads receive renewable, short-lived identities through SPIFFE/SPIRE, service mesh, or cloud workload identity. Application tokens have exact `aud`, narrow scopes, expiry, unique ID, and issuer. Shared bearer tokens, namespace trust, and long-lived API keys are prohibited.

The development issuer uses client credentials and RS256 plus a generated CA to make these properties testable. It is not an enterprise IdP and must not be promoted. At the edge, the external OIDC verifier pins an HTTPS issuer and JWKS URL, exact audience, supported signature algorithms, required scopes, subject, and configured tenant claim. Keycloak is one compatible IdP, not a mandatory control-plane component. JWKS/IdP unavailability fails authentication closed.

SPIRE is a cluster workload-identity authority, not an application library or proof of authorization.
Production installs its server/agent lifecycle separately, maps each service account to a unique
SPIFFE ID, rotates SVIDs, and presents them through an SDS-capable proxy or service mesh. ViewSense
still requires exact token audience/scopes and tenant policy after mTLS succeeds.

## Tenant, Trust Envelope, and authorization

The edge derives tenant from verified claims. Tenant and business context are signed claims, never an unsigned transport header. Trust Envelope v1 binds tenant, delegating workload, subject, purpose, classification, request correlation, audience, scopes, and expiry. Only registered delegators may request tenant-bound downstream tokens; fixed-tenant clients cannot change tenant. Receivers reject legacy tenant headers, missing envelopes, audience mismatch, inconsistent top-level/envelope tenants, and unsupported versions.

Production uses standards-based token exchange or equivalent workload delegation while retaining the ViewSense envelope schema. Each hop obtains a new audience token rather than forwarding a human token or mutable context header. Data queries include tenant and owner/purpose predicates. Production adds policy decisions for classification, legal basis, retention, model class, connector action, and residency both before retrieval and after candidate retrieval.

Provider admission may consult OPA through its Data API. The bundled OPA profile runs a policy
sidecar in the governance pod; policy input contains provider metadata and requested constraints,
not credentials or payloads. Timeout, malformed response, non-success response, missing result, and
explicit deny all fail closed. OPA does not replace API authorization or workload identity.

## Provider and evidence trust

Provider passports are untrusted assertions until signature, provenance, evaluation, ownership, expiry, residency, and policy checks succeed. Admission is time-bound and revocable. An admitted provider receives no credentials until workload identity and egress policy also allow the connection.

Evidence APIs accept payload-minimized metadata only. Append-only API semantics do not make the reference PostgreSQL database an immutable audit store; production exports to an independently controlled integrity and retention system.

## MCP threat model

MCP servers and returned content are untrusted. Controls include exact HTTPS host allow-lists, signed/approved server descriptors, schema validation, bounded payload/time, side-effect classification, human approval for consequential actions, response content isolation, SSRF/DNS rebinding protection, separate credentials, and immutable invocation audit. A catalog record is not execution approval.

## AI-specific threats

- Prompt injection: retrieved/tool content is marked as data, tools are authorized independently of model output, and high-risk actions require deterministic policy or approval.
- Data exfiltration: outbound providers are chosen by data policy; payload logging is off by default; egress is deny-by-default.
- Cross-tenant retrieval: tenant predicates, provider-level isolation, negative tests, and post-retrieval policy filters.
- Cost/resource exhaustion: input/output/tool-loop limits, quotas, deadlines, concurrency controls, and cancellation.
- Model/provider substitution: signed configuration, capability/residency validation, immutable image digests, and audited route decisions.

## Secrets and cryptography

Production secrets originate in Vault or a cloud secret manager, arrive through workload identity, rotate automatically, and are never present in Git or images. Certificates are short-lived and automatically renewed. Databases, backups, and object storage use enterprise-managed encryption keys. Algorithms and issuers are configuration with a tested rotation/overlap procedure.

## Supply chain

CI generates SBOMs, scans dependencies/images/IaC, signs artifacts and provenance, and admits only trusted digests. Pods use restricted security contexts. Provider and MCP adapter additions require threat modeling, conformance tests, and review of their network and secret permissions.

## Required negative tests

- missing/expired token, wrong audience, wrong scope, and untrusted client certificate;
- caller-supplied tenant substitution and cross-tenant memory search;
- missing/malformed Trust Envelope, fixed-tenant delegation attempt, and legacy tenant header;
- expired/revoked/unevaluated provider admission and sensitive evidence metadata;
- disallowed MCP URL, DNS/IP/redirect SSRF cases, and undeclared tool;
- direct orchestrator-to-provider/database network attempts;
- provider credential absence in callers;
- policy/identity unavailability fails closed for protected operations.
- OIDC wrong issuer/audience/algorithm, missing tenant/scope, stale key, and JWKS outage;
- OPA timeout/malformed/deny and SPIFFE ID/SVID rotation or spoof failures;
- agent approval with `agent.run` only, stale version replay, invalid state transition, and budget exhaustion.
