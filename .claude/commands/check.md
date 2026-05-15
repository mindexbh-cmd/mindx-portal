---
description: Supreme-guardian catastrophe check across 5 categories. Usage. /check <change-description-or-paths>
argument-hint: <change-description-or-paths>
---

Delegate to `catastrophe-prevention-agent` for a 5-category disaster check against a proposed change.

Argument: `$ARGUMENTS`

If `$ARGUMENTS` is empty, ask the operator what change they want checked and stop — the agent needs a target.

## Invocation

```
Agent({
  subagent_type: "catastrophe-prevention-agent",
  description: "Catastrophe check: $ARGUMENTS",
  prompt: "Mode: pre-change disaster audit.
           Change to audit: $ARGUMENTS.

           Walk your standard four-phase workflow:
             Phase 1 — Scan (categorize + identify applicable categories)
             Phase 2 — Deep check (run category-specific checks across all 5)
             Phase 3 — Verdict (APPROVE / APPROVE WITH CONDITIONS / REJECT)
             Phase 4 — Report (write to docs/audits/catastrophe-check-<slug>-<ts>.md)

           Run the always-on scans even if not in stated scope:
             - secret scan
             - auth decorator count vs baseline
             - critical route presence
             - test users intact
             - Render Starter sanity

           After writing the audit report, append a row to
           docs/memory/CATASTROPHE_LOG.md (timestamp, slug, verdict,
           categories flagged). If REJECT, also append the full
           breakdown to docs/memory/REJECTED_CHANGES.md.

           Print the verdict line FIRST at the top of your response."
})
```

## Output to the operator

Forward the agent's verdict verbatim at the top. Then:

- ✅ **APPROVE** → proceed.
- ⚠️ **APPROVE WITH CONDITIONS** → list every condition and require explicit operator confirmation before any work begins.
- ❌ **REJECT** → block. Surface the specific risks per category. Offer the operator three options:
  1. Apply the suggested remediation and re-run `/check`.
  2. Pick the suggested alternative approach.
  3. Explicit override (must use `override:catastrophe:<reason>` in the eventual commit).

## After the operator answers

- **"Apply remediation"** → ask which item to address, then re-invoke `/check` once done.
- **"Override / ship anyway"** → relay to the coordinator with `catastrophe verdict: REJECT, operator override` in context. Memory-keeper logs the override.
- **"Drop the change"** → confirm; logs stay as a prevented-disaster record.

## Examples

```
/check delete the books_v2 table
   → expect REJECT (Category 1: data loss)

/check rename /api/parent/lookup to /api/parent/v2/lookup
   → expect REJECT (Category 2: breaking WhatsApp deep-links)

/check add a footer with the centre slogan
   → expect APPROVE (no category applies; additive UI text only)

/check refactor PORTAL_PARENT_HUB_HTML card grid to 5 columns
   → expect APPROVE WITH CONDITIONS (Category 5 mobile viewport check)

/check docs/plans/unified-login-parent-direct-nav-20260515-222200.md
   → audits a pre-written plan file
```

## Hook integration

The hook script `.claude/hook_scripts/catastrophe_block.py` pre-blocks the most dangerous Bash patterns (`DROP TABLE`, `DELETE FROM` without WHERE, `TRUNCATE`, `rm -rf`, `git push --force`, `git reset --hard origin/*`) and asks the operator to run `/check <intent>` first. The block is hard until either `/check` returns APPROVE or the operator pastes the override tag.
