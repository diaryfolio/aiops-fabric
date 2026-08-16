# Memory Module

The `memory-gateway` owns the stable API and policy boundary. Products implement that API behind it.

- `postgres-pgvector`: bundled reference provider and owned PostgreSQL database.
- `mem0-oss-adapter`: bundled ViewSense adapter to an authenticated self-hosted Mem0 REST server.
- `mem0-platform-adapter`: the same boundary adapted to Mem0 Platform `/v1` paths.

Choose with `products.memory.product`, `products.memory.endpoint`, and `products.memory.audience` in the ViewSense Helm chart. A new product must pass the memory conformance suite and document export/import, filters, retention, embedding compatibility, residency, backup, and failure semantics.

The adapter hashes tenant/owner identifiers before they leave ViewSense, requires HTTPS, keeps the
Mem0 API key in its own Secret, and normalizes provider responses. The upstream Mem0 product remains
a managed dependency so its model/embedder configuration and lifecycle stay explicit.

`module.json` binds this catalog entry to the gateway/provider source, design contract, Helm paths, data ownership, and supported products.
