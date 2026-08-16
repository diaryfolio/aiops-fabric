# Core API and Orchestration Module

The core module contains the external response API and bounded request orchestrator. The current
response path composes identity, memory, and LLM APIs and owns none of their provider data or
credentials. MCP remains a separately callable gateway until an authorized agent/tool worker ships.

- Runtime: `viewsense_gateway` and `viewsense_orchestrator`
- Public reference contract: `POST /v1/responses`
- Helm controls: `modules.gateway` and `modules.orchestrator`

Long-running agent and business processes do not belong in request handlers; they use the agent/workflow contracts.
