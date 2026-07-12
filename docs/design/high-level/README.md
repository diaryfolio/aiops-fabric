# High-Level Design Documents

This folder contains the enterprise AI platform high-level technical design set.

## Canonical Architecture Concept

All high-level design documents use the same baseline concept:

`Enterprise User or App -> API Gateway and Auth -> Fabric Layer`

Fabric Layer services include AI Orchestrator, Workflow Engine, LLM Gateway and Inference, Memory and RAG, and MCP Runtime. Security and Zero Trust plus Observability are cross-cutting controls applied to all Fabric services.

## Structure

1. Top-level anchor documents (`design_0x.md`) provide entry points and cross-cutting views.
2. Modular design units under numbered domain folders (for example `10-overall/`) keep topics focused and LLM-readable.

## Top-Level Documents

1. `design_01.md` - Top-level design index and hierarchy map.

## Modular Documents

1. `10-overall/01-objective-principles.md`
2. `10-overall/02-runtime-topology-flow.md`
3. `10-overall/03-api-integration-standards.md`
4. `10-overall/04-component-breakdown.md`
5. `10-overall/05-operations-and-roadmap.md`
6. `20-deployment/01-deployment-topology-sizing.md`
7. `30-security/01-zero-trust.md`
8. `40-ops/01-day2-operations-sre.md`
9. `50-roadmap/01-roadmap-maturity.md`

## Intended Reading Order

1. Start with `design_01.md` for navigation and naming rules.
2. Read modular docs in sequence (`10-overall/01` to `10-overall/05`) for architecture baseline.
3. Continue with `20-deployment/01` for deployment topology and sizing.
4. Review `30-security/01` before production onboarding.
5. Use `40-ops/01` for operational readiness and incident handling.
6. Use `50-roadmap/01` for delivery planning and governance milestones.
