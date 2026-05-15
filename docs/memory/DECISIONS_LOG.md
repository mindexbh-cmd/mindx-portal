# DECISIONS_LOG.md

ADR-style records of architectural and design decisions on the mindex-portal codebase. Maintained by `memory-keeper-agent`. Append a new ADR when a load-bearing choice is made; never edit an old one (record a superseding ADR instead).

Format:
```
### ADR-NNN: <title>
- **Date**: YYYY-MM-DD
- **Status**: accepted / superseded by ADR-XXX / deprecated
- **Context**: why this came up
- **Decision**: what we chose
- **Alternatives considered**: ...
- **Consequences**: what this implies, including the tradeoffs we accepted
- **Reference**: git hash, file:line, related ADRs
```

---

### ADR-001: Everything lives in `app.py`
- **Date**: 2026-04-02 (project start)
- **Status**: accepted
- **Context**: The first commits were a single Python file. The repo never went through a "split into modules" refactor; the file has since grown to ~105K lines.
- **Decision**: Continue with a single-file architecture. No Flask blueprints (yet). All HTML stays inline as Python string constants.
- **Alternatives considered**: Jinja templates in `templates/`, Flask blueprints per feature, JS framework on the front.
- **Consequences**: Trivial to navigate by `Grep`. Trivial to deploy (one file changes = redeploy). Painful to onboard new contributors. Performance fine because routes don't take long to import. Memory-architects-agent tracks candidate blueprint splits (`books_v2`, `points`, `parent_hub`, `curriculum`) for a future refactor sprint.
- **Reference**: CLAUDE.md "Architecture"

### ADR-002: Arabic strings stored as HTML/JS escapes in source
- **Date**: ~2026-04 (recorded retroactively)
- **Status**: accepted
- **Context**: Raw Arabic in Python source got mangled on Windows/Render round-trips (mojibake on commit through Windows file encoding).
- **Decision**: All Arabic strings in `app.py` are stored as HTML numeric entities (inside HTML blobs) or `\uXXXX` JS escapes (inside `<script>` blocks). Labels saved to DB by the UI are also HTML-entity-encoded.
- **Alternatives considered**: Switch all repo files to UTF-8 with BOM; use a separate translation file; use a `.po`-style i18n system.
- **Consequences**: Source is harder to read but reliably committable. `_decode_arabic_entities()` exists to unescape labels on read. Never paste raw Arabic into `app.py` — see CLAUDE.md "Working with Arabic text".
- **Reference**: commit 74b87ac "replace mojibake Arabic strings with Unicode escapes"

### ADR-003: SHA-256 password hashing without salt
- **Date**: ~2026-04 (recorded retroactively)
- **Status**: accepted, **flagged for review**
- **Context**: Auth was implemented quickly with `hashlib.sha256(p.encode()).hexdigest()` as `hp()`.
- **Decision**: Continue with sha256-no-salt for now.
- **Alternatives considered**: bcrypt, argon2id (recommended modern choice), scrypt.
- **Consequences**: Vulnerable to offline rainbow-table attacks if the DB ever leaks. Mitigated only by the rate limit (5 fails / 15 min on staff roles). A migration to bcrypt is recommended but not yet planned.
- **Reference**: `app.py:250` (`def hp`)

### ADR-004: Dual-path schema management (init_db vs else-branch ALTERs)
- **Date**: ~2026-04 (refined throughout)
- **Status**: accepted
- **Context**: Fresh DB needs full CREATE TABLE + seeds; existing DBs need IF NOT EXISTS + ADD COLUMN to evolve without losing data.
- **Decision**: Every new column / table is added to BOTH branches: `init_db()` for fresh-DB CREATE, and the else-branch for existing-DB ALTER. Migration tags persisted in `schema_migrations`.
- **Alternatives considered**: Alembic, Flask-Migrate, hand-coded migration files.
- **Consequences**: Idempotent. Cheap. Easy to write. But trap: forget either branch and you get drift (works locally on a fresh DB, fails on prod which is always existing). The `_NO_ID_COLUMN_TABLES` wrapper trap was discovered after `schema_migrations` failed to persist due to the auto-RETURNING-id append — now codified.
- **Reference**: CLAUDE.md "Dual-path schema management", CLAUDE.md "Data safety"

### ADR-005: NEVER use `_pg_pool` — open a fresh psycopg2 connection per call when outside the request context
- **Date**: 2026-05-15 (commit f7e62c9)
- **Status**: accepted
- **Context**: The books_v2 orphan probe referenced `_pg_pool` which never existed in this codebase. It silent-NameError'd on every boot, leaving the data-loss alarm dead.
- **Decision**: Boot-time / out-of-request probes open their own `psycopg2.connect(DATABASE_URL)`, wrap in `_PgConnection`, close in `finally`. Mirror `_new_connection()`.
- **Consequences**: Slightly more boilerplate per probe. No silent NameError surface.
- **Reference**: commit f7e62c9, `app.py:93786`

### ADR-006: 12-agent custom team + 9 imported professional agents + coordinator
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: A single-file codebase + Arabic + Postgres+SQLite-duality + tight memory budget made it impractical for one generic AI to review changes. Specialists needed.
- **Decision**: 12 custom agents calibrated to the codebase (mindex-coordinator + 11 specialists + database-architect added later); 9 imported MIT-licensed generalist agents from VoltAgent for breadth (security-auditor, code-reviewer, python-pro, etc.). Coordinator orchestrates per-task.
- **Alternatives considered**: One mega-agent with everything stuffed into its prompt; relying on the parent assistant alone.
- **Consequences**: Reviews are higher quality but slower (multi-agent fan-out costs more tokens). Each agent has a narrow scope — easier to audit and improve. Custom + imported clearly separated under `.claude/agents/` vs `.claude/agents/imported/`.
- **Reference**: CLAUDE.md "Professional setup", `.claude/agents/`

### ADR-007: Expand-Migrate-Contract for ALL schema changes
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: Multiple past schema changes had to be hot-fixed because they broke routes that still read the old column. Migration risk was real.
- **Decision**: `database-architect-agent` enforces Expand → Migrate → Contract across three separate deploys. Phase A adds the new without removing the old. Phase B migrates call sites one commit at a time. Phase C drops the old after `Grep` confirms zero references AND 48h of clean logs.
- **Alternatives considered**: In-place rename via `ALTER ... RENAME COLUMN`.
- **Consequences**: A column rename now takes 1-2 weeks calendar time. Zero downtime. Rollback possible at any phase boundary.
- **Reference**: `.claude/agents/database-architect-agent.md`, CLAUDE.md "Specialist agent team"

### ADR-008: Test users seeded in prod (not test-mode flag)
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: e2e tests need to authenticate via the standard `/login` route. A test-mode shim would add a code path to maintain.
- **Decision**: Seed `admin_test` / `teacher_test` / `student_test` / `parent_test` as real users in the prod DB via `scripts/seed_test_users.py`. They use the standard SHA-256 hash and the normal session flow. `personal_id=TEST-STUDENT-0001` avoids collision with real CPRs.
- **Alternatives considered**: ENV-gated bypass-login; mock auth in tests.
- **Consequences**: Prod has 4 extra rows in `users`. Tests run against the exact code path real users use. No special-casing.
- **Reference**: `scripts/seed_test_users.py`

### ADR-009: Auto-rollback via safety tags
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: A bad deploy with no rollback path is the worst-case outage. Render auto-rollback exists but is slow.
- **Decision**: `scripts/safe_deploy.py` tags `safety/pre-<feature>-<timestamp>` before every push, polls `/api/health` for 5 minutes, runs smoke e2e against prod, then `--force-with-lease` resets main on any failure.
- **Alternatives considered**: Blue-green via Render preview environments (more complex, costs more); manual rollback (slower, human in loop).
- **Consequences**: One safety tag per deploy accumulates. 69 currently in the tag list, cluttering `git tag` output but cheap. No accidental rollback on shared work because `--force-with-lease` honors others' pushes.
- **Reference**: `scripts/safe_deploy.py`, CLAUDE.md "Health endpoints"

### ADR-010: Sync rule — single source of truth for table schema
- **Date**: ~2026-04 (refined throughout)
- **Status**: accepted
- **Context**: The "تعديل الجدول" modal and the table display kept drifting because each had its own column list.
- **Decision**: `_compute_table_schema(tid)` is the one place that computes "the ordered column list for a table". Every endpoint and the modal both go through it. Client-side, `window.refreshTable(tid)` is the post-mutation refresh hook.
- **Reference**: CLAUDE.md "Schema sync (SYNC RULE)"

### ADR-011: Memory-keeper owns `docs/memory/`
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: Cross-conversation context was being lost. Auto-memory at `~/.claude/projects/.../memory/` covers operator profile but not project history.
- **Decision**: New `memory-keeper-agent` (13th custom) writes append-only history to `docs/memory/*.md`. Generates `HANDOFF.md` + `HANDOFF_COMPACT.md` on demand for AI handoffs.
- **Consequences**: Boundary: auto-memory = operator; memory-keeper = project. Don't cross-write.
- **Reference**: `.claude/agents/memory-keeper-agent.md`

### ADR-013: Separate `prompt-engineer-agent` for plan-writing
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: Operator requests often arrive as a single sentence ("الموقع بطيء", "أريد ميزة كذا"). Routing those directly to `mindex-coordinator-agent` was muddying the coordinator's job (which is to orchestrate reviewers around an existing plan, not to invent the plan).
- **Decision**: Introduce a dedicated `prompt-engineer-agent` whose only job is plan-writing — six-phase workflow ending in a markdown document under `docs/plans/`. `/plan <description>` routes to it. SOP Step 0: "Vague request? Run `/plan` first."
- **Alternatives considered**: Have the coordinator do both planning and orchestration; rely on the parent assistant to write plans inline.
- **Consequences**: Two new artifacts per non-trivial task — the plan doc and the coordinator's review trail. The plan doc becomes a reviewable, refinable, version-controlled object. Cost: an extra agent invocation upfront for every wishful request.
- **Reference**: `.claude/agents/prompt-engineer-agent.md` (commit b8d5079), `docs/plans/parent-payment-reminders-20260515-194500.md` (demo)

### ADR-014: `/parent` stays public for anonymous WhatsApp visitors; redirect only authenticated users
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: Unified-login feature needed to decide what happens when a parent who is already logged in visits `/parent` (or the legacy alias `/parent/legacy`). Two interpretations on the table:
  - **Interpretation A**: Make `/parent` strictly authenticated. Any anonymous hit → redirect to `/login`. Cleanest URL semantics; one canonical entry per role.
  - **Interpretation B** (recommended): Keep `/parent` public for anonymous visitors (preserves the public CPR prompt that legacy WhatsApp deep-links rely on); only redirect when `session["user"]` is already populated — `role=student` → `/portal/parent-hub`, `role=parent` → `/portal/parent`.
- **Decision**: Operator chose Interpretation B. Authenticated parents/students now skip the redundant CPR prompt; anonymous visitors arriving from WhatsApp links keep the public PID flow unchanged.
- **Alternatives considered**: Interpretation A (above); a feature flag toggle (rejected — adds permanent config surface for a one-time UX cleanup); detecting WhatsApp UA (rejected — fragile, easy to break by browser updates).
- **Consequences**:
  - Additive guards only — zero break on legacy `/parent?pid=...` deep-links circulating in WhatsApp messages.
  - Two well-trodden public surfaces remain (`/parent`, `/parent/legacy`) but they no longer waste a click for already-authenticated visitors.
  - Means `/parent` semantics differ by auth state. Documented inline at `app.py` ~28800 and ~28825 so future maintainers don't "simplify" the guard away.
- **Reference**: commits `31499e9` (route guards) + `3712968` (login hint) + `5ecf19d` (plan/handoff). Plan doc: `docs/plans/unified-login-parent-direct-nav-20260515-222200.md`. Safety tag: `safety/pre-unified-login-parent-direct-nav-20260515-225736`.

### ADR-015: Split DB-safety from feature-safety — two distinct guardians, each with veto
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: `data-protector-agent` already gates every destructive DB op (DROP / DELETE / TRUNCATE / migration / bulk UPDATE). But "what works today" at the application surface — 502 routes, the parent shop checkout flow, the books_v2 chunked upload, the attendance loose-comparison rule, the taqseet ↔ student_payments mirror — was only implicit in `CLAUDE.md` and `PROJECT_BIBLE.md`. A well-meaning change to a shared helper could regress a feature without tripping the DB-safety agent at all. Operator wanted a second, peer-level guardian whose entire job is "does this break any existing feature?".
- **Decision**: Introduce `feature-protector-agent` (15th custom) as a regression-guard specialist with REJECT-class veto over the coordinator. Three-phase workflow: (1) pre-change audit against `docs/memory/FEATURE_INVENTORY.md` — which routes / templates / shared helpers does the diff touch?; (2) verdict — APPROVE / APPROVE WITH CONDITIONS / REJECT, with conditions enumerated as test obligations; (3) post-change verification — assertions from the inventory re-checked after merge. Inventory is append-only / incrementally updated, never regenerated from scratch (so historical critical-feature annotations don't get washed away by route renames).
- **Alternatives considered**:
  - Fold feature-safety into `data-protector-agent` (rejected — different scope, different review surface, would muddy data-protector's narrow DB-safety remit).
  - Make it advisory only, no veto (rejected — operator wanted a peer to data-protector, not a suggestion box).
  - Lean on `real-user-tester-agent` + `code-architect-agent` for regression coverage (rejected — they look for code quality / persona fit, not feature-surface preservation).
- **Consequences**:
  - Every non-trivial change now passes through two veto-empowered guardians (data-protector on the DB side, feature-protector on the feature side). Together they gate every risky change.
  - The top-20 critical-feature assertions in `FEATURE_INVENTORY.md` are now contractual invariants — breaking one is a REJECT, not a discussion.
  - Cost: one extra agent invocation per non-trivial task. Coordinator pipeline grows by one mandatory stage when the diff touches shared code, routes, templates, or APIs.
  - Inventory drift is the main risk — the agent must incrementally update `FEATURE_INVENTORY.md` whenever a route is added/removed/renamed. `/protect bootstrap` exists for the occasional sync but should be rare in steady state.
- **Reference**: commit `316d84d`; `.claude/agents/feature-protector-agent.md`; `.claude/commands/protect.md`; `docs/memory/FEATURE_INVENTORY.md` (502 routes, 69 categories, top-20 assertions). Complements ADR-007 (Expand-Migrate-Contract, DB-side) and the data-protector mandate in CLAUDE.md "Specialist agent team".

### ADR-016: Supreme catastrophe-prevention guardian above the role-specific guardians; veto power; only the human owner overrides REJECT
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: The existing guardians are scoped — `data-protector-agent` gates DDL / bulk-data ops (ADR-007 territory); `feature-protector-agent` gates regressions against the 502-route surface (ADR-015 territory). Neither one looks at a change holistically across all disaster categories. A change can be DB-clean and feature-clean yet still be a catastrophe: a `git push --force` to `main`, a security-hole rewrite, a p95-blowing query, or a UX cliff that nukes adoption. Operator wanted a SUPREME guardian above the role-specific ones whose entire job is "would this be a catastrophe for the project across any axis?".
- **Decision**: Introduce `catastrophe-prevention-agent` (16th custom) as a supreme guardian. Runs FIRST in the coordinator pipeline, before feature-protector and before data-protector. Reviews every change against 5 disaster categories: (1) data loss; (2) breaking changes; (3) security; (4) performance; (5) UX disasters. Default answer is NO unless the change is provably safe. Has REJECT-class veto power. **Only the human owner overrides REJECT** — no other agent, no coordinator, no operator-impersonating script. Bypass at the Bash-hook level requires the inline `override:catastrophe:<reason>` tag, which is logged.
- **Alternatives considered**:
  - Fold catastrophe-checks into data-protector or feature-protector (rejected — different scope, would muddy each agent's narrow remit; security + performance + UX disasters fall outside both).
  - Make the agent advisory only, no veto (rejected — operator wanted a hard stop, not a suggestion box).
  - Rely on the imported `security-auditor` + `performance-watchdog` + `incident-responder` already in the team (rejected — those are reactive / domain-narrow, not a unified disaster veto running on every change).
  - Single-category catastrophe agents (one for security, one for performance, etc.) — rejected as a category explosion that wouldn't deliver the holistic "is this a catastrophe?" verdict the operator asked for.
- **Consequences**:
  - Every non-trivial change now passes through THREE veto-empowered guardians in series: catastrophe-prevention (first) → feature-protector (second) → data-protector (DB-touching changes only). Together they form a defense-in-depth gate.
  - SOP gained step 0a ("Run `/check` first for risky changes") and is documented in `CLAUDE.md`.
  - PreToolUse Bash hook `catastrophe_block.py` (7th hook) provides a fast pattern-based block at the shell layer for the most dangerous literal commands (DROP TABLE, TRUNCATE, DELETE-without-WHERE, ALTER COLUMN type/rename, `rm -rf` on sensitive paths, `git push --force` without `--force-with-lease`, `git reset --hard origin/main`, `git filter-*`, `dropdb`, `pg_restore --clean`). Bypass tag `override:catastrophe:<reason>` is required inline; the hook also blocks the dangerous string when used as DATA (e.g. inside `echo`) so documenting these patterns in commit messages or scripts requires the override.
  - Cost: one extra agent invocation upfront per non-trivial task. Coordinator pipeline grows by one mandatory stage. Hook adds a few ms to every Bash call.
  - All REJECT verdicts land in `docs/memory/REJECTED_CHANGES.md` (full risk breakdown) and all verdicts (REJECT + APPROVE) land in `docs/memory/CATASTROPHE_LOG.md` (append-only ledger).
- **Reference**: commit `43b52d3`; `.claude/agents/catastrophe-prevention-agent.md`; `.claude/commands/check.md`; `.claude/hook_scripts/catastrophe_block.py`; `docs/memory/CATASTROPHE_LOG.md`; `docs/memory/REJECTED_CHANGES.md`; demo audits `docs/audits/catastrophe-check-delete-books-v2-20260515-204654.md` (REJECT) and `docs/audits/catastrophe-check-add-footer-slogan-20260515-204654.md` (APPROVE). Complements ADR-007 (Expand-Migrate-Contract), ADR-009 (auto-rollback safety tags), and ADR-015 (feature-protector).

### ADR-012: Postgres-archived MCP — use pgEdge or Zed fork, with read-only role
- **Date**: 2026-05-15
- **Status**: accepted (in MCP docs)
- **Context**: The official `@modelcontextprotocol/server-postgres` was archived May 2025 over an unpatched SQL-injection bug.
- **Decision**: Recommend pgEdge or Zed-patched fork. Mandate a dedicated `mindex_readonly` role in the connection string. Never point at the write-capable `DATABASE_URL`.
- **Reference**: `docs/MCP_SETUP.md`

## Pending decision candidates (not yet resolved)

- Bcrypt vs argon2id migration for `users.password` (currently sha256-no-salt — ADR-003 flagged)
- Whether to deprecate the trip-family + tasks-family + student_points_log tables (DATABASE_AUDIT §7.3, §7.9)
- Rename strategy for cryptic `students.col_*` and `____2026` columns (DATABASE_AUDIT §7.2)
- Blueprint split for `books_v2` / `points` / `parent_hub` / `curriculum` (deferred — see ADR-001)
- Backfill of 156 NULL `students.personal_id` rows (DATABASE_AUDIT §7.4 — needs staff cleanup, not engineering)
