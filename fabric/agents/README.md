# Durable Agent Runtime Module

The bundled `viewsense_agent_runtime` is a PostgreSQL-backed bounded state machine. It provides
idempotent run creation, optimistic versioning, checkpoints, approval/rejection, step budgets,
cancellation, terminal states, and ordered safe events through Agent Run v1.

It deliberately does not put an LLM loop inside an HTTP request. Future workers claim durable runs
and use only the LLM, memory, MCP, workflow, governance, and policy APIs. LangGraph and other engines
remain replaceable adapters behind the same run contract. Agent steps never gain permissions from
model output.

The default Helm, Compose, and Kubernetes development profiles install the runtime and its owned
database and execute its approval lifecycle in the smoke suite.
