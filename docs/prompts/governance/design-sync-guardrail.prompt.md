# Design Sync Guardrail Prompt

Use this prompt before making code changes in this repository.

---

You are operating in `aiops-fabric`.

Your first responsibility is to keep implementation and architecture design in sync.

## Mandatory Workflow

1. Classify the requested change as `minor` or `major` using `docs/prompts/governance/major-change-policy.md`.
2. If `major`, update relevant docs in `docs/design/high-level/` in the same change set.
3. Provide a `Design Impact Summary` that maps code changes to design sections.
4. Refuse to mark the task complete if major code changes are done without design updates.

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
- Sync Status: <PASS|FAIL>
```

If `Sync Status` is `FAIL`, include exactly what is missing.

---

Do not bypass these rules.
