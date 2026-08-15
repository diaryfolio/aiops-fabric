# ViewSense Machine-Readable Contracts

These schemas are the portable boundary between independently replaceable components. Runtime models and contract tests must evolve with them. Provider payloads stay behind adapters; callers exchange ViewSense-owned envelopes only.

- `trust-envelope-v1.schema.json` describes identity-signed tenant, purpose, subject, and classification context.
- `provider-passport-v1.schema.json` describes admission input for a model, memory, MCP, workflow, agent, or ingestion provider.
- `evidence-event-v1.schema.json` describes payload-minimized execution evidence input. The API derives producer and tenant from authenticated identity.

Schemas are versioned rather than silently changed. Breaking field or semantic changes require a new major contract and migration plan.
