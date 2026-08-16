# Governance and Evidence Module

This module is the initial ViewSense AI® sovereign-control plane. It owns provider passports, evaluation records, explicit admission decisions, and payload-minimized execution evidence through an authenticated API and its own PostgreSQL database.

The bundled service is an executable reference. It does not yet claim production policy-engine integration, signed supply-chain verification, immutable/WORM export, legal hold, or automatic routing enforcement. Those controls remain explicit maturity gates in the design and roadmap.

Helm controls are `modules.governance` and `datastores.governance`. Applications never write its database directly.
