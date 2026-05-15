# Mindex Portal — AI Handoff (compact)

*Auto-generated 2026-05-15. For full briefing see `docs/memory/HANDOFF.md`. For workflow rules see `CLAUDE.md`.*

## Operator preferences
Arabic for user-facing text, English for code talk. Concise answers. Direct action over discussion. Don't ask what's documented. Multi-phase requests get committed phase-by-phase.

## What it is
Arabic RTL mobile-first portal for a Bahraini education center. Attendance, points/avatars/eggs, taqseet payments, parent hub with cart redemption, books + curriculum libraries, lessons log, evaluations, parent messages, trips, push notifications, sideloaded Android TWA.

## Stack
Flask + single `app.py` (~105K lines, 502 routes, 874 funcs) → gunicorn 2×4 → Render Starter (512 MB / 1 GB disk at `/var/data`) → Postgres prod, SQLite local. Python 3.12. Playwright. pypdfium2. pywebpush. Bubblewrap 1.23.0. No Jinja, no JS framework, no pytest.

## Current state
- WORKING: 502 routes; e2e 8/8; `/api/health{,/deep}`; `safe_deploy.py` auto-rollback; 13 custom + 9 imported agents; 11 slash commands; 5 hooks
- BROKEN: 8 orphan `point_events`; 156 NULL `students.personal_id` (48%); 6 cryptic `students.col_*` columns; ≥1 evaluations row with Excel-serial date; 2105 stranded rows in 3 dead tables
- IN PROGRESS: memory-keeper onboarding
- NEXT: database-audit-driven migrations (see DATABASE_AUDIT.md §7), push-notifications operational tuning

## Recent work
- 2026-05-15: agent team + scripts + slash commands + hooks + MCP docs + DB audit + memory keeper
- 2026-05-14: TWA APK pipeline + push UI + books chunked upload + VAPID regenerator
- 2026-05-13: books hardening; curriculum orphan fix
- 2026-05-12: push Phase 2; parent-shop cart; PID-preserving back nav
- 2026-05-04: points feature wave (123 commits in a day)

## Critical rules
- NEVER `DROP TABLE` / `DELETE FROM <whole>` / `TRUNCATE` on user-data
- Every column / table added to BOTH `init_db()` AND the else-branch migration
- `_PgConnection.execute` auto-appends `RETURNING id`; new id-less tables go in `_NO_ID_COLUMN_TABLES`
- Arabic = HTML entities in HTML blobs OR `\uXXXX` in `<script>`; NEVER raw Arabic in `app.py`
- All table/column refs through `get_setting()` + `_is_safe_ident()`
- Postgres strict on types: never `COALESCE(<ts_col>, '')` or `WHERE ts_col = ''`

## Test env
- Prod: <https://mindx-portal-1.onrender.com>
- Local: <http://localhost:5000>
- `admin_test` / `TestAdmin2026!`; `teacher_test` / `TestTeacher2026!`; `student_test` / `TestStudent2026!`; `parent_test` / `TestParent2026!` (PID `TEST-STUDENT-0001`)

## Key files
- `app.py` — the monolith
- `CLAUDE.md` — workflow rules + agent registry
- `docs/DATABASE_AUDIT.md` — 2026-05-15 audit
- `docs/memory/PROJECT_BIBLE.md` — master ref
- `.claude/agents/*.md` (13 custom + 9 imported under `imported/`)
- `.claude/commands/*.md` (10 + /context)
- `scripts/safe_deploy.py` / `run_e2e.py` / `db_query.py`

## Useful commands
`/test` `/deploy <slug>` `/audit` `/logs <kw>` `/backup` `/rollback` `/health` `/feature <desc>` `/sql <q>` `/screenshots <path>` `/context [compact|full|topic]`

## Deep dives
For more: `docs/memory/{PROJECT_BIBLE,CHANGE_LOG,DECISIONS_LOG,BUGS_LOG,DESIGN_LOG,CODE_GENEALOGY,CONVERSATION_THEMES}.md`, `docs/DATABASE_AUDIT.md`, `docs/MCP_SETUP.md`, `CLAUDE.md`.
