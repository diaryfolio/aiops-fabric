# MCP Gateway Module

This module is the stable tool-provider catalog and invocation boundary. The current provider
contract is ViewSense AI®-owned `POST /v1/tools/call`; native MCP Streamable HTTP translation and MCP
server hosting are planned. Provider workloads remain separately deployable and do not receive
registry/database access.

The chart enables the gateway, its owned registry database, and an optional safe mock provider
independently. Registration uses an authenticated API and exact HTTPS host allow-list, but no
immutable invocation audit or certification controller ships yet.

`module.json` binds the gateway, registry ownership, design contract, chart controls, and provider maturity into the validated catalog.
