# Mindex Portal — AI Assistant Handoff

*Auto-generated: 2026-05-15 by memory-keeper onboarding*
*Last activity: commit 3fd37db — feat(agents): add memory-keeper-agent*

## Instructions for the AI reading this

You are now briefed on the **Mindex Portal** project. Read this ENTIRE document before answering. The operator prefers:

- **Arabic for user-facing text**, English when discussing code
- **Concise answers** — no fluff, no over-explanation
- **Direct action over discussion** — they often write "Auto-accept all, bypass mode active"
- **Acknowledgment of context** — don't ask what's documented; this file IS the documentation
- **Visual formatting** — lists, tables, code blocks
- **Multi-phase requests** are committed phase-by-phase as separate commits

When they paste credentials, treat them as transient: use, never log/commit, flag rotation at end.

## Project identity

**Mindex Portal** is an Arabic, RTL, mobile-first web app serving a Bahraini education center. It handles attendance, points/behaviors with avatar gamification, payments (taqseet installment plans), parent-facing hub with cart-based prize redemption, books library, curriculum library, lessons log, evaluations, parent messages, school trips, evaluations, push notifications, and a sideloaded Android TWA APK. Operator: mindex.bh@gmail.com.

## Tech stack

- **Backend**: Flask (Python 3.12.3), single file `app.py` ~105K lines
- **Production DB**: Postgres on Render (`mindex_db_pw2a`)
- **Local DB**: SQLite (`mindx.db`)
- **App server**: gunicorn 21.2.0, 2×4 workers, 300 s timeout
- **Host**: Render Starter ($7/mo, 512 MB RAM, 1 GB disk at `/var/data`)
- **Browser automation**: Playwright Chromium
- **PDF**: pypdfium2 + pypdf + reportlab + arabic-reshaper + python-bidi==0.4.2
- **Push**: pywebpush + py-vapid
- **TWA**: Bubblewrap 1.23.0 via GitHub Actions
- **No** Jinja templates, no JS framework, no pytest, no Node frontend

## Current state (as of 2026-05-15)

### Working
- All 502 routes in `app.py`
- E2E suite (`python scripts/run_e2e.py`) — 8/8 passing locally and against prod
- `/api/health` + `/api/health/deep` — added 2026-05-15
- Safe-deploy with auto-rollback (`scripts/safe_deploy.py`)
- 13 custom + 9 imported subagents
- 10 slash commands + `/context`
- 5 lifecycle hooks (precommit/prepush/post-pyedit/session-start/prompt-hints)
- Test users seeded on local + prod (`admin_test`/`teacher_test`/`student_test`/`parent_test`)

### Broken / risky
- 8 silent orphan rows in `point_events` (student_id → deleted students)
- 156 of 327 students with NULL `personal_id` (48%)
- 6 cryptic `students.col_*` columns with real data behind awful names
- ≥1 `evaluations.form_fill_date` row with unconverted Excel serial `46079`
- 2105 stranded rows in legacy `student_points_log` / `student_achievements` / `achievements`

### In progress
- This handoff (memory keeper onboarding)

### Planned next (from operator's roadmap)
- Database-audit-driven migrations (see DATABASE_AUDIT.md §7) — staggered E-M-C
- Push-notifications operational tuning (Phase 4)

## Recent work (last 14 days)

| Date | What |
|---|---|
| 2026-05-15 | Memory keeper onboarding (THIS commit); 12-agent team + 9 imported; 10 slash commands; 5 hooks; MCP docs; database audit |
| 2026-05-14 | TWA APK build pipeline; push UI admin panel; books chunked upload; VAPID regenerator rewrite |
| 2026-05-13 | Books library hardening (BYTEA orphan probe, chunked uploads on disk); curriculum orphan recognition |
| 2026-05-12 | Push Phase 2 foundation; parent-shop cart polish; PID-preserving back nav; Unicode bidi fix |
| 2026-05-11 | Payment portal warnings; parent portal Unicode robustness |
| 2026-05-04 | Points feature wave (123 commits in one day) — avatars, eggs, achievements |

## Active issues (sorted)

| Severity | Issue | Reference |
|---|---|---|
| Critical | 8 `point_events` orphan rows | DATABASE_AUDIT.md §7.1 |
| High | 156 NULL `students.personal_id` (48% of all rows) | DATABASE_AUDIT.md §7.4 |
| High | 6 cryptic students columns with real data | DATABASE_AUDIT.md §7.2 |
| High | 3 dead tables totaling 2105 rows of stranded data | DATABASE_AUDIT.md §7.3 |
| Medium | `evaluations.form_fill_date=46079` (Excel serial) | DATABASE_AUDIT.md §7.7 |
| Medium | Missing indexes on `attendance(group_name, attendance_date)` and `users(username)` | DATABASE_AUDIT.md §7.5, §7.6 |
| Medium | 9 missing FKs on core join paths | DATABASE_AUDIT.md §7.8 |
| Low | ~15 empty feature-scaffold tables (trip_*, task_*, etc.) | DATABASE_AUDIT.md §7.9 |

## Key files

| Path | Purpose |
|---|---|
| `app.py` | The monolith — 105K lines, all routes + inline HTML |
| `CLAUDE.md` | Active workflow rules + agent registry |
| `render.yaml` | Render service config + env var slots |
| `requirements.txt` | Pip deps (Python 3.12.3) |
| `docs/DATABASE_AUDIT.md` | 2026-05-15 read-only audit (8 sections) |
| `docs/memory/PROJECT_BIBLE.md` | Master reference doc (this directory) |
| `docs/memory/CHANGE_LOG.md` | History by week |
| `docs/memory/DECISIONS_LOG.md` | ADR-style decisions (12 captured) |
| `docs/memory/BUGS_LOG.md` | Bug catalog from `fix:` commits |
| `docs/MCP_SETUP.md` | Optional MCP servers |
| `.claude/agents/*.md` | 13 custom subagents + 9 imported |
| `.claude/commands/*.md` | 11 slash commands |
| `.claude/hook_scripts/*.py` | 5 lifecycle hooks |
| `scripts/safe_deploy.py` | Tag → push → poll → rollback |
| `scripts/run_e2e.py` | 8-test Playwright e2e |
| `scripts/db_query.py` | Read-only DB shell |

## Critical constraints

- **512 MB RAM** ceiling on Render Starter → split between 2 workers
- **300 s gunicorn timeout** → no requests longer than 5 min (file uploads excepted via chunking)
- **p95 ≤ 2 s** target for routes that load pages
- **DATA SAFETY**: NEVER `DROP TABLE` / `DELETE FROM <whole>` / `TRUNCATE` on user-data tables. Every migration is `IF NOT EXISTS` / `ADD COLUMN`. Always tag before risky ops.
- **Dynamic Configuration Rule**: all table/column references go through `get_setting()` + `_is_safe_ident()`. Never hardcode.
- **Arabic encoding rule**: HTML numeric entities in HTML blobs, `\uXXXX` JS escapes in `<script>` blocks. NEVER raw Arabic in `app.py`.
- **Postgres strictness**: never `COALESCE(<ts_col>, '')` or `WHERE ts_col = ''`. SQLite lies, PG throws.

## Test environment

- **Prod URL**: <https://mindx-portal-1.onrender.com>
- **Local URL**: <http://localhost:5000> (`python app.py`)
- **Test creds** (seeded both locally and on prod):
  - `admin_test` / `TestAdmin2026!`
  - `teacher_test` / `TestTeacher2026!`
  - `student_test` / `TestStudent2026!`
  - `parent_test` / `TestParent2026!` (linked to personal_id `TEST-STUDENT-0001`)
- **Test DB ID**: `students.personal_id = 'TEST-STUDENT-0001'`

## Conversation context (recent themes)

1. **Infrastructure-as-code** — building the agent team, hooks, scripts, memory keeper
2. **Database hygiene** — audit surfaced 8 migration candidates; none yet picked to action
3. **Push / TWA operational** — Phase 3 landed; operational tuning is the next conversation
4. See `docs/memory/CONVERSATION_THEMES.md` for the full picture

## Useful slash commands

| Command | Use case |
|---|---|
| `/test` | Run the e2e suite (8 tests) |
| `/deploy <slug>` | Auto-rollback deploy via safe_deploy.py |
| `/audit` | 5-specialist fan-out review → `docs/audits/audit-<ts>.md` |
| `/logs <keyword>` | Render production logs filtered |
| `/backup` | Snapshot prod via pg_dump |
| `/rollback` | List safety/* tags + interactive reset |
| `/health` | Quick + deep health probe |
| `/feature <description>` | Full coordinator pipeline |
| `/sql <query>` | Read-only DB query |
| `/screenshots <path>` | 360/768/1280 viewport captures |
| `/context [compact\|full\|topic]` | Regenerate this file or topic-specific brief |

## Deep dives

- `docs/DATABASE_AUDIT.md` — schema details + 8 migration candidates
- `CLAUDE.md` — active workflow rules
- `docs/memory/PROJECT_BIBLE.md` — master reference
- `docs/memory/DECISIONS_LOG.md` — design rationale (12 ADRs)
- `docs/memory/BUGS_LOG.md` — known issue catalog
- `docs/memory/CHANGE_LOG.md` — history by week
- `docs/memory/DESIGN_LOG.md` — UI/UX evolution + palette
- `docs/memory/CODE_GENEALOGY.md` — per-file history
- `docs/memory/CONVERSATION_THEMES.md` — operator's recent priorities
- `docs/MCP_SETUP.md` — optional MCP servers
- `docs/APK_BUILD.md` — TWA / Bubblewrap notes
