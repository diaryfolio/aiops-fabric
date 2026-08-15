# Workflow Provider Module

Workflow engines integrate behind a ViewSense start/status/signal/cancel/event contract.

- n8n: best suited to triggers, broad SaaS integration, low-code business automation, and approval channels.
- Temporal: best suited to long-lived durable execution, timers, retries, and compensation.
- Argo Workflows: best suited to Kubernetes-native batch, ingestion, evaluation, and GPU jobs.
- LangGraph-class runtime: best suited to checkpointed agent graphs and human-in-the-loop agent state.

Do not embed a provider SDK into the orchestrator. Provider credentials remain in the adapter/engine namespace. Definitions are versioned, bounded, and audited. The operator and adapters are roadmap items; the API boundary is defined in the agentic design.

This entry remains `contract-only`. Selecting a product in Helm records intent but does not currently install a workflow engine or adapter; `module.json` prevents that distinction from being hidden.
