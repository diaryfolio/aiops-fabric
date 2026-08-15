# Memory Module

The `memory-gateway` owns the stable API and policy boundary. Products implement that API behind it.

- `postgres-pgvector`: bundled reference provider and owned PostgreSQL database.
- `mem0-compatible-external`: external adapter endpoint; no bundled database/provider pod.

Choose with `products.memory.product`, `products.memory.endpoint`, and `products.memory.audience` in the ViewSense Helm chart. A new product must pass the memory conformance suite and document export/import, filters, retention, embedding compatibility, residency, backup, and failure semantics.
