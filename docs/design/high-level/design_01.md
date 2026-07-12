# LatticeCore® Platform - Top-Level Design Index

## Why this file is small

This file is intentionally lightweight. Detailed content is split into modular design files so architecture remains readable, maintainable, and easy for LLM-driven workflows to consume.

## Canonical Architecture Concept

`Enterprise User or App -> API Gateway and Auth -> Fabric Layer`

Fabric Layer services: AI Orchestrator, Workflow Engine, LLM Gateway and Inference, Memory and RAG, MCP Runtime.

Cross-cutting controls across all Fabric services: Security and Zero Trust, Observability.

## Design Hierarchy

Top level:

- [docs/design/high-level/design_01.md](docs/design/high-level/design_01.md): architecture entry point and navigation.

Modular level:

1. [docs/design/high-level/10-overall/01-objective-principles.md](docs/design/high-level/10-overall/01-objective-principles.md)
2. [docs/design/high-level/10-overall/02-runtime-topology-flow.md](docs/design/high-level/10-overall/02-runtime-topology-flow.md)
3. [docs/design/high-level/10-overall/03-api-integration-standards.md](docs/design/high-level/10-overall/03-api-integration-standards.md)
4. [docs/design/high-level/10-overall/04-component-breakdown.md](docs/design/high-level/10-overall/04-component-breakdown.md)
5. [docs/design/high-level/10-overall/05-operations-and-roadmap.md](docs/design/high-level/10-overall/05-operations-and-roadmap.md)

Companion design set:

- [docs/design/high-level/20-deployment/01-deployment-topology-sizing.md](docs/design/high-level/20-deployment/01-deployment-topology-sizing.md): multi-cloud deployment topology and sizing.
- [docs/design/high-level/30-security/01-zero-trust.md](docs/design/high-level/30-security/01-zero-trust.md): security, governance, and zero-trust model.
- [docs/design/high-level/40-ops/01-day2-operations-sre.md](docs/design/high-level/40-ops/01-day2-operations-sre.md): day-2 operations and SRE model.
- [docs/design/high-level/50-roadmap/01-roadmap-maturity.md](docs/design/high-level/50-roadmap/01-roadmap-maturity.md): phased implementation roadmap and maturity model.

## Naming Convention

- Top-level design anchors: design_0x.md
- Modular design units: <domain>/<sequence>-<topic>.md

Example:

- 10-overall/03-api-integration-standards.md

## Design Sync Rule

When major platform changes are introduced:

1. Update the affected modular files first.
2. Update companion design documents where relevant.
3. Keep this index updated if hierarchy or naming changes.
