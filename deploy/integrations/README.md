# ViewSense Enterprise Integration Profiles

ViewSense does not hide upstream operators inside its application chart. Cluster-scoped products
are installed and upgraded independently, then connected through these contracts:

| Product | ViewSense integration | Install ownership |
|---|---|---|
| Mem0 OSS/Platform | `memory-mem0` REST adapter and memory conformance suite | AI platform team |
| SPIRE | SPIFFE Workload API/SDS profile and service-account registrations | cluster security team |
| OPA | bundled governance sidecar or external Data API | policy team |
| Keycloak | edge OIDC/JWKS validation and claim mapping | identity team |
| n8n/Temporal/Argo | workflow start/status/signal/cancel contract | automation team |
| OpenTelemetry Collector | OTLP/JSON collection profile | observability team |
| Elastic/Splunk | collector export; never direct service SDK coupling | SIEM team |

Use `fabric/product-catalog.json` to distinguish validated, configuration-ready, and planned paths.
Selection never implies certification: provider passports and environment-specific conformance tests
must pass before admission.

The Mem0 OSS profile uses an exact namespace/pod-label/port NetworkPolicy selector for a managed
in-cluster server. Remote products use explicit CIDRs or an approved CNI FQDN policy.
