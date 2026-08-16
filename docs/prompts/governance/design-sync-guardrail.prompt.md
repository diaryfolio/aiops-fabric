# Design Sync Guardrail Prompt

Use this prompt before making code changes in this repository.

---

You are operating in `aiops-fabric`.

Your first responsibility is to keep implementation and architecture design in sync.

## Mandatory Workflow

1. Classify the requested change as `minor` or `major` using `docs/prompts/governance/major-change-policy.md`.
2. Update `docs/design/high-level/00-implementation-conformance.md` when routes, runtime edges, state owners, provider maturity, trust boundaries, or verification paths change.
3. If `major`, update relevant docs in `docs/design/high-level/` in the same change set.
4. Provide a `Design Impact Summary` that maps code changes to design sections.
5. Refuse to mark the task complete if major code changes are done without design updates.

## Hard Rules

- Never merge major implementation changes without matching updates to high-level design docs.
- If architecture assumptions changed, update the affected `design_0x.md` files and document rationale.
- If unsure whether a change is major, treat it as major.

## Required Output Block

Return this block at the end of your work:

```text
Design Sync Report
- Change Classification: <minor|major>
- Design Docs Updated: <list>
- Code Areas Updated: <list>
- Architecture Delta: <summary>
- Tests/Evidence: <list>
- Known Production Gaps: <list or none>
- Sync Status: <PASS|FAIL>
```

If `Sync Status` is `FAIL`, include exactly what is missing.

---

Do not bypass these rules.
