# ViewSense Fabric Module Catalog

`fabric/` is machine-readable installable product metadata, not a second copy of application source. Runtime packages live under `src/viewsense_*`; module descriptors connect them to their contracts, Helm controls, provider choices, data ownership, and maturity.

| Directory | Capability | Current maturity |
|---|---|---|
| `core/` | edge API and request orchestration | implemented reference |
| `identity/` | development workload issuer and enterprise identity boundary | implemented reference |
| `llm/` | model gateway and inference providers | implemented reference |
| `memory/` | memory gateway and vector providers | implemented reference |
| `mcp-registry/` | MCP catalog and invocation boundary | implemented reference |
| `ingestion/` | governed document chunking and indexing entry point | implemented reference |
| `agents/` | durable bounded agent runs | contract only |
| `workflows/` | n8n/Temporal/Argo provider boundary | contract only |
| `observability/` | JSON/OTel/SIEM integration boundary | partial reference |

Each capability directory must contain:

- `README.md` for operators and developers;
- `module.json` conforming to `module.schema.json`;
- valid paths to its implementation and design contracts;
- honest provider status: `bundled`, `external`, or `planned`.

The umbrella chart is `fabric/charts/viewsense`. Each runtime module can be independently enabled and provider products are selected through `products.*`. External Secrets, workload identity, and production provider charts remain enterprise overlays. Run `make catalog-check` to reject missing modules, dangling paths, or README-only placeholders.
