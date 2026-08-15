# Agent and Ingestion Modules

The current `viewsense_ingestion` service proves governed paragraph-aware chunking through the memory API. The planned agent-runtime module implements a durable bounded state machine through LLM, memory, workflow, policy, and MCP gateway contracts.

Helm installs modules; a future operator reconciles provider and agent-profile lifecycle. Agent steps never gain permissions from model output, and agentic enrichment never replaces source text or bypasses data classification/evaluation.

This directory is intentionally `contract-only`, not empty or implemented. `module.json` makes that maturity machine-readable so packaging cannot imply that an agent runtime currently ships.
