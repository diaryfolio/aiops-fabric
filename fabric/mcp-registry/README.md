# MCP Gateway Module

This module is the stable MCP catalog, policy, and invocation boundary. MCP servers remain separately deployable provider products and do not receive registry/database access.

The chart enables the gateway, its owned registry database, and an optional safe mock provider independently. Production provider registration is an audited API/configuration action and must use an exact HTTPS host allow-list. Future operator reconciliation belongs here when server certification, rollout, health, and credential rotation require a controller.

`module.json` binds the gateway, registry ownership, design contract, chart controls, and provider maturity into the validated catalog.
