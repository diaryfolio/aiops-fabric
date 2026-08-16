# ViewSense Helm Chart

The chart is the modular installation interface. All components are independently toggled under `modules.*.enabled`; provider products are selected under `products.*`. Curated combinations live under `profiles/`; render them before installation and supply the Secrets named by the selected profile.

Examples:

```bash
# Default full reference: durable agents + mock LLM + PostgreSQL/pgvector + mock MCP
helm upgrade --install viewsense ./fabric/charts/viewsense -n viewsense-dev

# OpenAI through the bundled credential-isolation adapter; mock is omitted.
# Create openai-credentials and a CNI FQDN/egress-proxy policy (or explicit CIDRs) first.
helm upgrade --install viewsense ./fabric/charts/viewsense -n viewsense-dev \
  -f ./fabric/charts/viewsense/profiles/openai.yaml

# Mem0 OSS through the bundled zero-trust adapter
helm upgrade --install viewsense ./fabric/charts/viewsense -n viewsense-dev \
  -f ./fabric/charts/viewsense/profiles/mem0-oss.yaml

# Enterprise integration intent: Keycloak OIDC + OPA + SPIRE + n8n + OTel
helm template viewsense ./fabric/charts/viewsense \
  -f ./fabric/charts/viewsense/profiles/enterprise-suite.yaml
```

External endpoints require matching identity grants, CA trust, egress policy, and Secrets from the enterprise overlay. With the built-in NetworkPolicies, each external provider also needs an explicit `externalEgress` CIDR/port rule; an empty list fails closed. The Mem0 OSS profile instead uses an exact namespace/pod-label/port selector for its managed in-cluster server. Use a CNI FQDN policy extension when endpoint addresses are dynamic. `values.schema.json` rejects unknown product names, non-HTTPS endpoints, and malformed egress entries. For production, use immutable image digests and external secret/workload-identity integrations.

For OpenAI, only `openai-adapter` receives the `api-key` field from the configured Secret. The
adapter pins `https://api.openai.com/v1`, controls the model server-side, and needs outbound HTTPS;
production should use an egress proxy or CNI FQDN policy rather than a broad Internet CIDR.

The enterprise profile declares desired integrations; it does not install cluster-scoped Keycloak,
SPIRE, n8n, or OpenTelemetry operators. Platform teams install those upstream products with pinned
versions and then run the conformance checks in `tests/README.md`. OPA is different: when selected as
`opa-sidecar`, the chart installs a local fail-closed policy decision point beside governance.

The SPIRE socket/trust-domain, workflow product, and `otlpEndpoint` values are reserved intent: no
SVID consumer, workflow adapter, or native application OTLP exporter is rendered today. JSON stdout
can be collected independently. `vllm` and generic external LLM values likewise require a future
ViewSense-compatible authentication adapter and must not be treated as a working vanilla endpoint.
