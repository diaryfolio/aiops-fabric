# Repo Governance Prompt Pack

This folder contains strict prompt and checklist assets to enforce design-code synchronization.

## Goal

Ensure high-level architecture docs under `docs/design/high-level/` are updated whenever a major code or platform change is introduced.

## Files

1. `design-sync-guardrail.prompt.md`
   - Reusable prompt for AI/code-assist workflows.
   - Forces architectural impact analysis and mandatory documentation updates.
2. `major-change-policy.md`
   - Defines what counts as a major change.
   - Defines required design documentation touchpoints.
3. `design-sync-checklist.md`
   - PR/merge checklist to block incomplete architecture updates.
4. `major-change-template.md`
   - Standard template for documenting major changes and design deltas.

## Usage

1. Start every significant implementation with `design-sync-guardrail.prompt.md`.
2. Classify change severity using `major-change-policy.md`.
3. For major changes, complete `major-change-template.md` and update required design docs.
4. Validate merge readiness using `design-sync-checklist.md`.
