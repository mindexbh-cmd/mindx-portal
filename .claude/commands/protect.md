---
description: Feature-protector review — check whether a proposed change risks breaking existing features. Usage. /protect <change-description-or-path>
argument-hint: <change-description-or-paths>
---

Delegate to `feature-protector-agent` to audit a proposed change for regression risk against the existing feature inventory.

Argument: `$ARGUMENTS`

If `$ARGUMENTS` is empty, ask the operator what change they want audited and stop — the agent needs a target.

## Invocation

```
Agent({
  subagent_type: "feature-protector-agent",
  description: "Protect: $ARGUMENTS",
  prompt: "Mode: pre-change audit.
           Change to audit: $ARGUMENTS.

           Run the full three-phase workflow:
             Phase 1 — scope + dependencies + impact report
             Phase 2 — verdict (APPROVE / APPROVE WITH CONDITIONS / REJECT)
             Phase 3 — if the operator says ship, define the post-deploy verification plan

           Consult docs/memory/FEATURE_INVENTORY.md as your source of truth.
           If the inventory is missing or stale, say so explicitly in the report.

           Return the structured Feature Protection Report verbatim."
})
```

## Bootstrap mode

If the operator runs `/protect bootstrap` (or `/protect init`), invoke the agent to build the initial `docs/memory/FEATURE_INVENTORY.md` from `app.py`:

```
Agent({
  subagent_type: "feature-protector-agent",
  description: "Protect: bootstrap inventory",
  prompt: "Mode: initial bootstrap.
           Task: scan app.py and produce docs/memory/FEATURE_INVENTORY.md per your bootstrap spec.
           Source of truth: every '@app.route' line in app.py (~500 routes),
           the inline *_HTML templates, scripts/run_e2e.py test names,
           and CLAUDE.md route/feature sections.

           Group by user role + feature area + criticality.
           Mark the top 20 features with explicit critical assertions.
           Report the file path + a 500-char preview when done."
})
```

## Output to the operator

Forward the agent's report verbatim. Highlight the verdict line first:

- ✅ **APPROVE** → proceed.
- ⚠️ **APPROVE WITH CONDITIONS** → list the conditions and ask the operator to confirm before they ship.
- ❌ **REJECT** → block. Surface the specific risks the agent flagged.

## After the operator answers

- **"Override / ship anyway"** → relay to the coordinator with `feature-protector verdict: REJECT, operator override` in the context so memory-keeper can log it.
- **"Mitigate"** → ask which condition to address, then re-invoke `/protect` after the mitigation is in place.
- **"Drop the change"** → confirm; the inventory stays untouched.

## Examples

```
/protect bootstrap                                  → build the initial FEATURE_INVENTORY.md
/protect rename /api/parent/lookup → /api/parent/v2/lookup
/protect remove the legacy /parent route
/protect refactor PORTAL_PARENT_HUB_HTML cards
/protect docs/plans/unified-login-parent-direct-nav-20260515-222200.md
```
