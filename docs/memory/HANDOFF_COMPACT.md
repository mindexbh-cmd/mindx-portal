# Mindex Portal — AI Handoff (compact)

*Auto-generated 2026-05-15. Last commit: 8c7dcb6 (2026-05-15 20:42 +0300). For full briefing see `docs/memory/HANDOFF.md`; for workflow rules see `CLAUDE.md`.*

## Operator preferences
Arabic for user-facing text, English for code talk. Concise answers, no fluff. Direct action over discussion. Don't ask what's already documented. Multi-phase requests get committed phase-by-phase. Operator often opens with "Auto-accept all" / "Bypass mode" — ship end-to-end without intermediate clarification.

## What it is
Arabic RTL mobile-first portal for a Bahraini education center. Attendance, points/avatars/eggs, taqseet payments, parent hub with cart redemption, books + curriculum libraries, lessons log, evaluations, parent messages, trips, push notifications, sideloaded Android TWA.

## Stack
Flask + single `app.py` (~105K lines, 502 routes, 874 funcs) → gunicorn 2×4 → Render Starter ($7/mo, 512 MB / 1 GB disk at `/var/data`) → Postgres prod, SQLite local. Python 3.12.3. Playwright (Chromium cached on disk). pypdfium2. pywebpush. Bubblewrap 1.23.0. No Jinja, no JS framework, no pytest. All HTML is inline Python strings.

## Current state
- WORKING: 502 routes; e2e 8/8 green; `/api/health{,/deep}`; `safe_deploy.py` auto-rollback; 14 custom + 9 imported agents; 12 slash commands; 6 lifecycle hooks; memory-keeper corpus live
- BROKEN / TECH-DEBT: 8 orphan `point_events`; 156 NULL `students.personal_id` (48%); 6 cryptic `students.col_*` columns; ≥1 evaluations row with Excel-serial date; 2105 stranded rows in 3 dead tables
- IN PROGRESS: agent ecosystem dry-run audit just shipped (commit 8c7dcb6); memory-keeper integrated into coordinator pipeline (bf5c521)
- NEXT: action DATABASE_AUDIT.md §7 migrations; push-notifications operational tuning; adopt `/plan` for vague asks

## Recent work (last 14 days)
- 2026-05-15: agent team (14 custom + 9 imported), 12 slash commands, 6 hooks, MCP docs, DB audit, memory keeper corpus + `/context`, prompt-engineer + `/plan`, coordinator SOP integration, ecosystem dry-run audit
- 2026-05-14: TWA APK pipeline + push UI + books chunked upload + VAPID regenerator (cryptography-direct)
- 2026-05-13: books library hardening; curriculum orphan fix; PDF viewer custom rendering
- 2026-05-12 (196 commits): push Phase 2; parent-shop cart redemption; bidi-mark CPR-lookup fix
- 2026-05-04 (123 commits): points/behaviors/avatars/eggs wave

## Critical rules (full list in CLAUDE.md)
- NEVER `DROP TABLE` / `DELETE FROM <whole>` / `TRUNCATE` on user-data tables
- Every new column/table goes in BOTH `init_db()` AND the else-branch migration
- `_PgConnection.execute` auto-appends `RETURNING id`; new id-less tables MUST be added to `_NO_ID_COLUMN_TABLES` or migration tags re-run forever
- Arabic stored as HTML entities in HTML blobs OR `\uXXXX` in `<script>`; NEVER raw Arabic in `app.py` (Windows/Render mangles it)
- All table/column references go through `get_setting()` + `_is_safe_ident()` validation
- Postgres is strict on types: never `COALESCE(<ts_col>, '')` or `WHERE ts_col = ''` — use NULL
- Attendance: dates as `YYYY-MM-DD` via `_att_normalize_date`; names whitespace-folded
- Students sync: `mxLoadStudentsSchema()` + `mxAppendCustomFields()`; never hardcode columns
- data-protector-agent is MANDATORY before any DDL or bulk write

## Test environment
- Prod: <https://mindx-portal-1.onrender.com>
- Local: `python app.py` on <http://localhost:5000>
- `admin_test` / `TestAdmin2026!` (admin)
- `teacher_test` / `TestTeacher2026!` (teacher)
- `student_test` / `TestStudent2026!` (student, PID `TEST-STUDENT-0001`)
- `parent_test` / `TestParent2026!` (parent of TEST-STUDENT-0001)
- Seed via `python scripts/seed_test_users.py`

## Key files
- `app.py` — the monolith (~105K lines)
- `CLAUDE.md` — workflow SOP + agent registry + all the RULES
- `docs/DATABASE_AUDIT.md` — 2026-05-15 prod-Postgres read-only audit
- `docs/memory/PROJECT_BIBLE.md` — master reference
- `.claude/agents/*.md` — 14 custom + 9 imported under `imported/`
- `.claude/commands/*.md` — 12 slash commands incl. `/context` and `/plan`
- `.claude/hook_scripts/*.py` — 6 lifecycle hooks
- `scripts/safe_deploy.py` / `run_e2e.py` / `db_query.py` / `seed_test_users.py`

## Useful commands
`/plan <vague request>` `/test` `/deploy <slug>` `/audit` `/logs <kw>` `/backup` `/rollback` `/health` `/feature <desc>` `/sql <q>` `/screenshots <path>` `/context [compact|full|recent]`

## Deep dives
`docs/memory/{PROJECT_BIBLE,CHANGE_LOG,DECISIONS_LOG,BUGS_LOG,DESIGN_LOG,CODE_GENEALOGY,CONVERSATION_THEMES}.md`, `docs/DATABASE_AUDIT.md`, `docs/MCP_SETUP.md`, `CLAUDE.md`.
