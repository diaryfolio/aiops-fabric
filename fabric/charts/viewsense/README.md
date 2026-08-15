# ViewSense Helm Chart

The chart is the modular installation interface. All components are independently toggled under `modules.*.enabled`; provider products are selected under `products.*`.

Examples:

```bash
# Default local reference: mock LLM + PostgreSQL/pgvector + mock MCP
helm upgrade --install viewsense ./fabric/charts/viewsense -n viewsense-dev

# External OpenAI-compatible model endpoint; bundled mock is omitted
helm upgrade --install viewsense ./fabric/charts/viewsense -n viewsense-dev \
  --set products.llm.product=openai-compatible-external \
  --set products.llm.endpoint=https://llm-gateway.enterprise.example/v1 \
  --set products.llm.audience=enterprise-llm \
  --set products.llm.externalEgress[0].cidr=203.0.113.10/32 \
  --set products.llm.externalEgress[0].port=443

# External Mem0-compatible memory adapter; bundled provider/database are omitted
helm upgrade --install viewsense ./fabric/charts/viewsense -n viewsense-dev \
  --set products.memory.product=mem0-compatible-external \
  --set products.memory.endpoint=https://memory.enterprise.example \
  --set products.memory.audience=enterprise-memory
```

External endpoints require matching identity grants, CA trust, egress policy, and Secrets from the enterprise overlay. With the built-in NetworkPolicies, each external provider also needs an explicit `externalEgress` CIDR/port rule; an empty list fails closed. Use a CNI FQDN policy extension when endpoint addresses are dynamic. `values.schema.json` rejects unknown product names, non-HTTPS endpoints, and malformed egress entries. For production, use immutable image digests and external secret/workload-identity integrations.
