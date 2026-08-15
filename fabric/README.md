# ViewSense Fabric Modules

`fabric/` is the installable product catalog. Stable gateway modules are separated from replaceable products so an administrator selects capabilities and implementations through Helm values, not code changes.

| Module | Stable API | Product selection |
|---|---|---|
| identity integration | OAuth/OIDC and workload token boundary | development issuer or enterprise external identity |
| edge/orchestrator | `/v1/responses` | enabled independently; provider-neutral |
| LLM gateway | OpenAI-compatible inference API | mock, vLLM, or external OpenAI-compatible endpoint |
| memory gateway | ViewSense memory API | PostgreSQL/pgvector or external Mem0-compatible adapter |
| MCP gateway | registry/invocation API | bundled test provider or approved external MCP runtimes |

The umbrella chart is `fabric/charts/viewsense`. `values.schema.json` validates supported product names. Each module can be enabled/disabled, pointed at an external provider, assigned its own image/resources, and constrained by an explicit network graph. The current chart expects certificate, identity, workload, and database Secrets to be provisioned by the platform's secret-management layer.
