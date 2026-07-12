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

1. `docs/design/high-level/design_01.md` for architecture and flow impact.
2. One or more of `design_02.md` to `design_05.md` depending on impact area.
3. `docs/design/high-level/README.md` if reading order or scope changed.

## Merge Gate Rule

Major change PRs must include:

1. `Change Classification: major`
2. Explicit list of updated design docs.
3. Architecture delta summary.

If any item is missing, PR is not ready to merge.
