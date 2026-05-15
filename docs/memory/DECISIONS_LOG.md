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
