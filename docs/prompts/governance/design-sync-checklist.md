# Design Sync Checklist

Use this checklist for every PR that touches code, infrastructure, or platform behavior.

## Classification

- [ ] I classified this change as `minor` or `major` using `major-change-policy.md`.
- [ ] If uncertain, I treated it as `major`.

## Mandatory for Major Changes

- [ ] `docs/design/high-level/design_01.md` updated for architecture impact.
- [ ] Relevant companion docs updated under:
	- `docs/design/high-level/20-deployment/`
	- `docs/design/high-level/30-security/`
	- `docs/design/high-level/40-ops/`
	- `docs/design/high-level/50-roadmap/`
- [ ] Data flow or trust boundary diagrams updated if behavior changed.
- [ ] Day-2 operations impacts documented (SLO, observability, security, HA/DR).

## Traceability

- [ ] I listed all code areas changed.
- [ ] I listed all design docs changed.
- [ ] I wrote an Architecture Delta summary.

## Quality Gate

- [ ] Design and implementation are consistent.
- [ ] Reviewer can understand system impact without reverse-engineering code.
- [ ] No major change is merged without design updates.

If any box is unchecked for a major change, do not merge.
