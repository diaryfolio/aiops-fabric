# Major Change Policy

This policy defines whether a repository change is minor or major for design synchronization.

## Major Change Criteria

A change is `major` if any of the following are true:

1. New platform service, runtime, or control-plane component is introduced.
2. Existing service boundaries, request flow, or trust boundaries are modified.
3. Any change affects one of the five core architecture layers:
   - LLM Hosting and Inference
   - AI Memory and Context
   - Hosted MCP Runtime
   - Workflow Orchestration
   - Cloud-Native Foundation
4. Security model changes (RBAC/ABAC, auth, mesh policy, key/secret handling, data isolation).
5. Deployment topology changes (cluster model, tenancy model, failover model, GitOps model).
6. SLO, HA, DR, observability, or operational model changes.
7. Any breaking API/protocol change across internal platform components.

If none apply, classify as `minor`.

## Required Documentation Updates for Major Changes

At minimum, update:

1. `docs/design/high-level/00-implementation-conformance.md` for the exact implemented/partial/planned state and its evidence.
2. `docs/design/high-level/design_01.md` for architecture and flow impact.
3. One or more domain documents depending on impact area:
   - `docs/design/high-level/20-deployment/`
   - `docs/design/high-level/30-security/`
   - `docs/design/high-level/40-ops/`
   - `docs/design/high-level/50-roadmap/`
4. `docs/design/high-level/README.md` if reading order or scope changed.

## Merge Gate Rule

Major change PRs must include:

1. `Change Classification: major`
2. Explicit list of updated design docs.
3. Architecture delta summary.
4. Tests/evidence and known production gaps.

If any item is missing, PR is not ready to merge.
