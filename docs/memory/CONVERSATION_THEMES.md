# CONVERSATION_THEMES.md

What the operator (mindex.bh@gmail.com) has been focused on over time. Maintained by `memory-keeper-agent`. Source: commit-message frequency analysis + interactive session topics.

## By month

### 2026-04 (project bootstrap → features)
- Initial scaffolding (week 1)
- Attendance + violations (week 2)
- Database editor + custom tables + label system (week 2-3)
- Curriculum + books_v2 (week 4)
- Dashboard redesign + admin pages (end of week 4)

### 2026-05 (feature explosion + infrastructure)
- Points/behaviors/avatars wave (May 4)
- Parent shop / cart / rewards (May 5-11)
- Parent portal polish + bidi-mark fixes (May 11-12)
- Push notifications Phase 2 (May 12-14)
- TWA / Android APK build pipeline (May 14)
- **Infrastructure-as-code day** (May 15): test infrastructure, 13 custom agents, 9 imported agents, 10 slash commands, 5 hooks, MCP docs, database audit, memory keeper

## Recurring patterns

### "Feature stopped showing things to parents" → check the visibility gate FIRST
Three back-to-back NOT-A-BUG investigations on 2026-05-22 night converged on the same shape: operator's mental model is "the OLD design showed X to parents/users", investigation reveals the OLD design also had the same gate, and the actual problem is a workflow step (admin publish click, approval rhythm, etc.) that wasn't happening. Documented cases:
- **G20 round 1+2** (cart submissions): pending-redemption rows looked suspicious; turned out to be `admin_on_behalf` + pre-G15 legacy rows. Live-watch probe (poll `MAX(redemptions.id)` for 3-5 minutes during a controlled test) instantly disambiguated frontend-silent-failure vs backend-issue.
- **G20h** (evaluations not visible to parents): 156 of 157 evals on prod were sitting with `released_to_parent=0` (draft state, documented as an intentional admin-review gate). Bulk-released via existing endpoint; no code change.

**Diagnostic recipe** when the next operator reports "feature stopped showing X to parents/users": (a) does a row exist at all in the source table? (b) is its release/visibility/status flag set as the read endpoint expects? (c) is the filter on the read endpoint behaving as documented? Code regression is the LAST hypothesis, not the first. The visibility gates are usually well-documented in CLAUDE.md — search there before assuming a regression.

### "Auto-accept all, bypass mode active"
The operator frequently prefixes large requests with autonomy declarations: "Auto-accept all", "Bypass mode active", "Don't ask permission between steps". They want the assistant to ship end-to-end without prompting for clarification on intermediate steps.

### Multi-phase requests with explicit deliverables
The operator structures big asks as numbered phases with clear deliverables per phase ("Phase 1: ... Phase 2: ... commit each phase separately"). They expect each phase committed independently for clean history.

### "Report when complete with summary"
After autonomous work, the operator wants a digestible summary — what was built, what didn't work, what's next. They review by reading the summary, not by going through every file.

### Real talk about scope
When the operator pastes credentials they ask about rotation. They expect the assistant to flag security concerns proactively. They prefer prose acknowledgment over silent compliance.

## Active priorities (as of 2026-05-15)

1. **Infrastructure foundation** — agent team, slash commands, hooks, memory keeper, MCP optionality. (largely complete this week)
2. **Test infrastructure adoption** — getting `/test` into the workflow, getting `safe_deploy` to be the default ship path.
3. **Database audit follow-through** — DATABASE_AUDIT.md surfaced 8 migration candidates; user has not yet picked one to action.
4. **Push notifications operational** — Phase 2 foundation landed; Phase 3 (TWA, admin send panel) live; operational tuning is the next conversation.

## Stalled / deferred topics

- Bcrypt migration for `users.password` (ADR-003 flagged, not actioned)
- Blueprint split for `books_v2` / `points` / `parent_hub` / `curriculum` (ADR-001 deferred)
- Trip-family table deprecation (DATABASE_AUDIT.md §7.9 — needs business sign-off)
- Cryptic `students.col_*` rename (DATABASE_AUDIT.md §7.2 — needs business identification of what each column is)
- Missing `personal_id` backfill for 156 students (DATABASE_AUDIT.md §7.4 — needs office staff cleanup, not engineering)

## Communication signals to watch for

- **"truly stuck"** → operator gave the assistant permission to stop when a blocker is genuine. Use sparingly.
- **Pasted credentials** → operator expects: use them as needed, never log/commit them, flag rotation when done.
- **"Just proceed"** / "no clarifying questions" → operator wants action, not discussion.
- **Markdown formatting** → operator reads in monospace; tables and code blocks work well.

## Topics the assistant should NOT raise unprompted

- Pricing / billing for Render or AI usage
- Whether to rewrite `app.py` as a multi-file project (settled — ADR-001)
- Whether to add a test framework (settled — Playwright-based e2e exists; no pytest planned)
- Whether to add a JS frontend framework (no — inline HTML is the convention)
