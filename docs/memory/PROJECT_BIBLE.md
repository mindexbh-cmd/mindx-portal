# PROJECT_BIBLE.md

The master reference document for the mindex-portal codebase. This file is owned by `memory-keeper-agent` and should be treated as the canonical answer to "what is this project?". For workflow rules (how to ship a change), see `CLAUDE.md`. For historical sequences (what changed when), see the other files under `docs/memory/`.

Last meaningful update: 2026-05-15 by memory-keeper onboarding.

---

## 1. Executive summary

Mindex Portal is an Arabic, RTL, mobile-first web app serving a Bahraini education center (the "Mindex" brand). It powers:

- **Attendance tracking** — teachers record present / absent / late per student per session
- **Points & behaviors** — teachers grant points for behaviors; students accumulate balances, redeem in a parent-facing "shop"; an avatar / achievement / egg-hatch gamification layer sits on top
- **Payments & taqseet** — installment plans, payment logging, parent receipts
- **Lessons log** — what was taught per group per session, with curriculum progress
- **Parent hub** — parents authenticate by their child's personal_id and see attendance, evaluations, messages, books, and the redemption shop
- **Database admin** — a generic spreadsheet-style editor over arbitrary tables, plus user-defined "custom tables" built at runtime from the UI
- **Curriculum library** — admins upload PDFs, assign to groups/students/parents/teachers with view-only / download permissions
- **Books library** — bigger PDFs delivered through a custom view-only renderer (`pypdfium2` based)
- **Trips** — registrations, payments, day-attendance, surveys for school trips
- **Evaluations** — monthly per-student form, including admin-only send-to-parent
- **Push notifications** — Web Push via VAPID, also via the sideloaded Android TWA APK

The project runs as a single Python file (`app.py`, ~105K lines as of 2026-05-15) on Render's Starter plan ($7/mo, 512 MB RAM), backed by managed Postgres in production and SQLite locally.

## 2. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Web framework | Flask | All routes in `app.py`; no Jinja templates — HTML is inline Python string constants |
| Production DB | Postgres (Render managed) | `mindex_db_pw2a` in Oregon |
| Local DB | SQLite | `mindx.db` (gitignored), schema kept in sync via the dual-path block |
| Connection wrapper | `_PgConnection` (custom) | Translates `?` → `%s`, auto-appends `RETURNING id` (with `_NO_ID_COLUMN_TABLES` exception) |
| App server | gunicorn 21.2.0 | 2 workers × 4 threads (gthread), 300s timeout |
| Hosting | Render.com | 1 GB persistent disk at `/var/data`; deploy from `main` |
| Python | 3.12.3 | Per `runtime.txt` |
| Browser automation | Playwright (Chromium) | Cached on persistent disk at `/var/data/playwright-browsers` |
| PDF rendering | `pypdfium2` (read) + `pypdf` + `reportlab` (write) + `arabic-reshaper` + `python-bidi==0.4.2` | Reshaping libs needed for Arabic watermark glyphs |
| Push | `pywebpush==2.0.0` + `py-vapid==1.9.0` | VAPID JWT signing |
| Image processing | `Pillow` + optional `pillow-heif` | HEIC fallback; install is best-effort |
| Excel | `openpyxl>=3.1.0` | Excel import pipeline |
| Cloud storage | `cloudinary>=1.40` | Optional curriculum file fallback |
| TWA / APK | Bubblewrap CLI 1.23.0 | Built via GitHub Actions |

No `package.json`, no Node frontend build, no Jinja templates, no test suite. All discipline is enforced socially through CLAUDE.md and the agent team.

## 3. Repository layout

```
mindx-portal/
├── app.py                       105 K lines — everything
├── login.html                   Standalone copy of LOGIN_HTML (unused)
├── app.html                     Placeholder
├── requirements.txt             Pip deps
├── runtime.txt                  Python 3.12.3
├── render.yaml                  Render service config
├── Procfile                     gunicorn entrypoint (mirror of render.yaml)
├── manifest.json                PWA manifest
├── service-worker.js            PWA SW
├── CLAUDE.md                    Active workflow rules + agent registry
├── README.md                    (sparse)
├── .gitignore                   Ignores .claude/* except agents/commands/hook_scripts/mcp_servers.json
├── .claude/
│   ├── agents/                  13 custom + 9 imported subagents
│   │   ├── *.md                 each agent definition
│   │   └── imported/
│   ├── commands/                10 slash commands (.md)
│   ├── hook_scripts/            5 Python helpers wired via settings.local.json
│   ├── mcp_servers.json         Opt-in MCP template (all disabled)
│   └── settings.local.json      Operator-personal (gitignored)
├── scripts/                     113 .py files (smoke tests + ops tooling)
│   ├── auto_test.py             Playwright BrowserSession library
│   ├── run_e2e.py               8-test e2e suite
│   ├── safe_deploy.py           Auto-rollback deploy pipeline
│   ├── seed_test_users.py       Test user seed (idempotent)
│   ├── get_logs.py              Render logs API wrapper
│   ├── db_query.py / db_backup.py / db_restore.py
│   ├── generate_vapid.py        One-shot VAPID keygen
│   └── smoke_*.py               109 historic smoke probes per feature
├── docs/
│   ├── DATABASE_AUDIT.md        2026-05-15 read-only audit
│   ├── MCP_SETUP.md             Optional MCP servers
│   ├── APK_BUILD.md             TWA / Bubblewrap notes
│   ├── audits/                  Timestamped /audit outputs (auto)
│   ├── screenshots/             /screenshots outputs
│   └── memory/                  THIS DIRECTORY — memory-keeper's domain
├── static/                      Static assets (icons, avatars, rewards)
├── reports/                     Ad-hoc diagnosis writeups
└── backups/                     Local DB snapshots (gitignored)
```

## 4. Architecture

### 4.1 Page templating (inline strings)

Every page is a module-level string constant in `app.py`:
- `LOGIN_HTML` ~ line 326
- `HOME_HTML` ~ 376
- `ATTENDANCE_HTML` ~ 494
- `DATABASE_HTML` ~ 1019
- `GROUPS_HTML` ~ 3684
- `POINTS_BOARD_HTML` ~ 81439
- plus ~15 other `*_HTML` constants for admin pages, parent hub views, etc.

Templating is `.replace("__PLACEHOLDER__", value)` — never Jinja. There is no `templates/` directory.

Arabic strings inside HTML blobs are stored as HTML numeric entities (`&#x627;`). Arabic strings inside inline `<script>` blocks are stored as `\uXXXX` JS escapes. Raw Arabic in `app.py` gets mangled on Windows/Render round-trips — see CLAUDE.md "Working with Arabic text".

### 4.2 Dual-path schema management

`app.py` runs schema setup at import time, split into two branches:
- **Fresh DB** → `init_db()` runs full `CREATE TABLE` + seeds
- **Existing DB** → else-branch with idempotent `CREATE TABLE IF NOT EXISTS` + `ALTER TABLE ADD COLUMN`

Every new column must be added to BOTH branches. Migration tags live in `schema_migrations` (102 tags as of audit). See CLAUDE.md for the wrapper caveat (`_NO_ID_COLUMN_TABLES`).

### 4.3 Auth

Session cookie + `@login_required` decorator. Passwords hashed via `hp()` (SHA-256, no salt). `session["user"]` holds the full users-row dict. Roles exist (admin, manager, reception, teacher, student, parent, plus a few specialised ones) but role enforcement is per-route, not at the decorator level.

Rate limit: 5 failed logins / 15 min, scoped only to staff roles (student/parent rate limit skipped — parents often mistype CPRs).

### 4.4 Data access

`get_db()` lazily opens a connection on `g.db`; `teardown_appcontext` closes. The `_PgConnection` wrapper handles `?`→`%s` translation. SQLite and Postgres share the same `db.execute` shape.

### 4.5 Routes

502 routes registered on `@app.route`. Page routes return HTML strings; data routes are under `/api/*` and return JSON. Categorical highlights:

| Prefix | Count (approx) | Purpose |
|---|---|---|
| `/api/points/*` | ~30 | Behaviors, grants, leaderboards, avatars, achievements, egg-hatch |
| `/api/groups/*` | ~25 | Group CRUD + filters |
| `/api/books/*` | ~25 | Books library + chunked upload |
| `/api/curriculum/*` | ~15 | Curriculum library |
| `/api/parent/*` and `/portal/parent-hub/*` | ~30 | Parent-facing views |
| `/api/payments/*` | ~10 | Payment logging + taqseet mirror |
| `/api/evaluations/*` | ~10 | Monthly evaluation form |
| `/api/lessons/*` | ~8 | Lessons log |
| `/api/trips/*` and `/trips/*` | ~25 | Trip registrations / day attendance / surveys |
| `/api/import` | 1 | Universal Excel import |
| `/api/admin/*` | ~50 | Backups, table audit, permissions, docs system |
| `/api/health` + `/api/health/deep` | 2 | Health probes (added 2026-05-15) |

### 4.6 Critical helpers

- `_att_normalize_date(s)` — accepts every historic format, returns ISO YYYY-MM-DD. Used everywhere attendance dates are written or read.
- `_groups_days_column(db)` + `_extract_days_from_row(rd)` — resolves the authoritative "أيام الدراسة" column (may be `study_days` or a user-added custom column). Critical: don't hardcode `study_days`.
- `_parse_study_days(text)` — splits Arabic day-list cells on `، / و / -` etc., folds variants (`الإثنين`/`الاثنين`, `الأربعاء`/`الاربعاء`) to canonical names. Use this, NEVER substring-search.
- `_decode_arabic_entities()` — unescapes HTML numeric entities saved in `*_col_labels`.
- `get_setting(page, component, default)` — Dynamic Configuration System lookup. Every reference to a table/column name must route through this with a default fallback.
- `_is_safe_ident(...)` — SQL identifier safety check; required when interpolating a `get_setting`-derived value into SQL.

### 4.7 Cross-table integrities (application-level)

- `student_payments.paidN` ↔ `taqseet.paidN` — payments mirror amounts. See CLAUDE.md "Taqseet ↔ student_payments sync".
- `attendance(group_name, attendance_date, student_name)` — natural key (no enforced unique).
- `users.linked_student_id` → `students.id` — no FK, default 0 (the FK-as-zero footgun documented in DATABASE_AUDIT.md).
- `users.linked_parent_for` → `students.personal_id` — TEXT key, no FK.

## 5. Feature inventory

### 5.1 Attendance
3618 rows on prod. ISO-date format enforced by `_att_normalize_date`. Status canonical: `حاضر` / `غائب` / `متأخر` (Arabic, UTF-8 bytes verified in audit). The `att_normalize_v1` migration retroactively cleaned up legacy `D/M/YYYY` / `D/M-YYYYم` rows.

### 5.2 Points / behaviors / avatars / eggs / achievements
- `point_events` (624 rows on prod) — every grant is one row. Indexed on `(group_name, session_date)`.
- `behaviors` (15 catalog entries) — what teachers can grant for.
- `avatars` (31 designs) + `egg-hatch` mechanic — kid-facing gamification.
- **Legacy**: `student_points_log` (1865 rows), `student_achievements` (225), `achievements` (15) — all unreferenced in `app.py`. Bulk-seeded 2026-05-04 and never read. Recommend DROP per DATABASE_AUDIT.md §7.3.

### 5.3 Payments / taqseet
- `taqseet` (1 row, but 30 Arabic-named columns: `طريقة_التقسيط` / `القسط_1`...`القسط_12` / `تاريخ_الاستحقاق_*`) — installment plan templates keyed by `taqseet_method`.
- `student_payments` (3 rows) — per-student-per-installment.
- `payment_log` (325 rows) — older flat log; `personal_id` migrated in but 169 NULLs remain (4.7%, legacy).
- `parent_receipts` (8 rows) — PDF receipts.
- `payment_messages` (89) — WhatsApp message log.

### 5.4 Books library
`books_v2` (10 rows, 67 MB total — BYTEA dominates). Storage path resolved by `_books_v2_storage_dir()`; orphan probe `_books_v2_orphan_probe()` runs at boot (fixed 2026-05-15 — was silent NameError on `_pg_pool`). `books_v2_groups` + `books_v2_teachers` for access control, `book_folders` for organisation.

Chunked upload supported via `upload_sessions`. View-only PDFs go through a custom `pypdfium2` page-image renderer at `/parent/book/<bid>/viewer` (the standard PDF iframe leaks download buttons).

### 5.5 Curriculum library
`curriculum_files` + `curriculum_assignments` + `curriculum_access_log`. PDFs on persistent disk at `/var/data/curriculum/<sha256>.pdf` (NEVER under `/static/`). Permissions are per-target-type: group / student / parent / teacher. Access log records every view/download with `user_id` + `ip_address`.

### 5.6 Parent hub
`/portal/parent-hub/*` views — attendance summary, evaluations, messages, books, curriculum, points-balance, parent shop (cart-based redemption from `rewards`). Parents authenticate by their child's `personal_id`. Recent regression: `linked_parent_for` field was empty for many parent rows — added a fallback lookup by PID query param.

### 5.7 Lessons log
`lessons_log` (4 rows). Teachers record per-group per-session: topic, curriculum progress, notes. Admin can retroactively edit `lesson_date` (audit-trailed). Migration tag: `lessons_v1`.

### 5.8 Parent messages
`parent_messages` (4 rows broadcast) + `parent_message_reads` (0 reads tracked). Teachers fill a structured "ماذا تريد أن يعرف ولي الأمر" form; broadcast through the WhatsApp pipeline AND surfaced in `/portal/parent-hub/messages` with per-student read state. Migration tag: `parent_messages_v1`.

### 5.9 Evaluations
`evaluations` (250 rows). Monthly form "استمارة التقييم الشهري". `evaluations_v2` migration added INTEGER 1-10 `score_*` fields + `evaluation_month` (YYYY-MM) + `student_id` / `teacher_id` joins + computed `overall_score`. Admin can release-to-parent and send-via-WhatsApp (audit columns).

⚠️ Data quality: at least one row stores `46079` (Excel serial date) in `form_fill_date`. See DATABASE_AUDIT.md §7.7.

### 5.10 Trips
8 trip-family tables. **All currently empty** except `trips` (1 placeholder row). The feature is scaffolded but never shipped to production users. Candidate for deprecation per DATABASE_AUDIT.md §7.9.

### 5.11 Violations
`violations` (18) + `violations_catalog` (32) + `violations_action_templates` (42). Recently introduced.

### 5.12 Events (ev_*)
`ev_events` (15) + `ev_registrations` (3) + `ev_items` (75) + `ev_costs` (75) + `ev_schedule` (20) + `ev_tasks` (240) + `ev_msg_templates` (4). Event-planning module — quizzes, recitals, etc.

### 5.13 Tasks (the `tasks` table family)
`tasks` (0 rows), `task_evaluations`, `task_comments`, `task_attachments`, `task_notifications`, `recurring_tasks`. **Scaffolded, never live.**

### 5.14 Database editor (generic)
`/database` page renders any built-in or `custom_tables` user-defined table with full edit-mode (add/remove rows, add/remove columns via "تعديل الجدول" modal). Column labels stored as HTML numeric entities in `column_labels` / `group_col_labels` / `att_col_labels` / `taqseet_col_labels` / `paylog_col_labels` / `eval_col_labels`. The Sync Rule (CLAUDE.md) requires both the modal and the table display to read from `_compute_table_schema(tid)`.

### 5.15 Excel import pipeline
`POST /api/import`. Universal. Body: `{table, rows, auto_create?, column_labels?}`. Upserts on natural keys per `IMPORT_TABLE_KEYS`. Whitespace-folds, status-remaps, date-normalises. Returns `{ok, inserted, updated, skipped, errors[], received, skip_reasons[], fields_used[]}`.

### 5.16 Settings system
`settings` (100 rows) — `(page, component, label, value, value_type)`. Read via `get_setting(page, component, default)`. CRITICAL: any feature referencing a table/column name MUST go through `get_setting` with a fallback, and must `_is_safe_ident` validate before interpolating into SQL.

### 5.17 Permissions admin
`users.is_active` (added by `permissions_v1`), `users.primary_department_id`, `users.can_be_assigned_tasks`. Per-user permission grants via `user_permissions` (1 row). Page: `/admin/permissions`.

### 5.18 Docs / onboarding system
`docs_pages` (22 rows) + `docs_screenshots`. Playwright Chromium-based auto-capture for site-tour-style help docs.

### 5.19 PWA / TWA / Push
- Manifest at `/manifest.json` (Arabic, RTL, `theme_color=#4a148c`).
- Service worker (`service-worker.js`).
- VAPID Web Push via `pywebpush`. Keys in env (`VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_CLAIM_SUB`). 15 active push subscriptions on prod.
- TWA (Android APK) built via Bubblewrap 1.23.0 in GitHub Actions. `assetlinks.json` controlled by `TWA_SHA256_FINGERPRINT` env. Status bar color matches `theme_color`.

### 5.20 Audit / observability
- `audit_log` (562 rows) — append-only event log.
- `backup_log` (27 rows) — pre-destructive snapshot history.
- `/api/admin/table-audit` — Category A/B/C/D classification of every table; offers DROP-via-auto-backup for Category-D orphans.
- `/api/health` + `/api/health/deep` — added 2026-05-15.

## 6. Database schema (high-level)

See `docs/DATABASE_AUDIT.md` for the comprehensive 2026-05-15 audit (8 sections, every table inventoried).

Headline numbers:
- **70+ tables** on prod
- **39 foreign keys** — concentrated in trips/ev/tasks/expense families; ZERO FKs on `students`, `attendance`, `users`, `taqseet`, `payment_log`, `student_groups`
- **102 schema_migrations tags** persisted
- **0 triggers** — all cross-table sync is application-level

Top data-quality issues (from audit):
1. 156 of 327 students (48%) have NULL `personal_id`
2. 8 silent orphan rows in `point_events` (student_id → deleted student)
3. 6 cryptic `students.col_*` / `____2026` columns with real data behind bad names
4. At least 1 `evaluations.form_fill_date` row with Excel serial `46079`
5. 2105 rows of stranded data in `student_points_log` + `student_achievements` + `achievements`

## 7. Deployment

### 7.1 Render config (from `render.yaml`)

- Service: `mindx-portal` (web)
- URL: `https://mindx-portal-1.onrender.com`
- Plan: Starter ($7/mo, 512 MB RAM)
- Region: implicit (Oregon, inferred from DB host)
- Disk: `mindex-data`, 1 GB at `/var/data`
- Build: `pip install -r requirements.txt && pip install pillow-heif (best-effort) && python -m playwright install chromium && python -m playwright install-deps chromium (best-effort)`
- Start: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 30 --workers 2 --threads 4`

### 7.2 Required env vars

| Name | Notes |
|---|---|
| `SECRET_KEY` | Flask session key (auto-generated by Render) |
| `DB_PATH` | `/var/data/mindx.db` (legacy SQLite path) |
| `DATABASE_URL` | Postgres connection string |
| `PLAYWRIGHT_BROWSERS_PATH` | `/var/data/playwright-browsers` — cache Chromium binary on persistent disk |
| `PYTHONUNBUFFERED` | `1` so boot logs stream |
| `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_CLAIM_SUB` | Web Push |
| `TWA_SHA256_FINGERPRINT` / `TWA_PACKAGE_NAME` | Android TWA assetlinks |
| `CLOUDINARY_CLOUD_NAME` / `_API_KEY` / `_API_SECRET` | Optional curriculum fallback |

### 7.3 Deploy protocol

Use `python scripts/safe_deploy.py --feature <slug>` (or the `/deploy <slug>` slash command):
1. Tag `safety/pre-<slug>-<timestamp>`
2. Push branch + tag
3. Poll `/api/health` for up to 5 minutes
4. Run smoke e2e (admin login + dashboard load) against prod
5. Auto-rollback (`git reset --hard <tag>` + `--force-with-lease`) on any failure

Never push to `main` for non-trivial work bypassing safe_deploy.

## 8. Test infrastructure

### 8.1 Test users (seeded by `scripts/seed_test_users.py`)

Idempotent — runs against local SQLite by default, prod Postgres if `DATABASE_URL` is set. Seeded both locally and on prod as of 2026-05-15.

- `admin_test` / `TestAdmin2026!`
- `teacher_test` / `TestTeacher2026!`
- `student_test` / `TestStudent2026!`
- `parent_test` / `TestParent2026!` (linked_parent_for=`TEST-STUDENT-0001`)

### 8.2 E2E suite (`scripts/run_e2e.py`)

Eight tests via Playwright Chromium:
1. `health_quick` — `/api/health`
2. `health_deep` — `/api/health/deep`
3. `admin_login` — form-post + redirect
4. `admin_dashboard` — `/dashboard` render
5. `admin_attendance` — `/attendance` render
6. `admin_database` — `/database` render
7. `admin_points_board` — `/points/board` render
8. `teacher_login` — alternate role auth

Screenshots land in `scripts/screenshots/` (gitignored). Pass/fail summary + 5xx detection + console-error capture.

### 8.3 Agent team (24 total)

13 custom + 9 imported professional + 1 coordinator + 1 memory-keeper. See CLAUDE.md "Specialist agent team" + `.claude/agents/imported/README.md`.

## 9. Slash commands

10 project commands under `.claude/commands/`:
`/test` `/deploy` `/audit` `/logs` `/backup` `/rollback` `/health` `/feature` `/sql` `/screenshots`
Plus `/context` (added 2026-05-15) for memory-keeper handoff generation.

See CLAUDE.md "Slash commands" for the full table.

## 10. Hooks

5 lifecycle hooks wired in `.claude/settings.local.json`:
- `precommit_check.py` — block on `app.py` SyntaxError or secrets in diff
- `prepush_check.py` — warn on non-main branch / dirty tree / stale test marker
- `post_pyedit_syntax.py` — surface SyntaxError on .py edits
- `session_start.py` — inject git status snapshot
- `prompt_hints.py` — keyword reminders + credential-rotation warning

Plus a 6th planned: PostToolUse on `Bash(git commit *)` matching `feat:|fix:|refactor:` → invoke memory-keeper-agent.

## 11. Critical rules (link to CLAUDE.md)

These rules are sacred. Each has its own CLAUDE.md section:

1. **Data Safety Rule** — Never DROP/DELETE/TRUNCATE user-data tables. Every migration is `IF NOT EXISTS` / `ADD COLUMN` only.
2. **Dynamic Configuration Rule** — All table/column references through `get_setting()` with `_is_safe_ident` validation.
3. **Schema Sync Rule** — The "تعديل الجدول" modal and table display read from `_compute_table_schema(tid)`; never maintain two column lists.
4. **Import Rule** — When implementing any Excel import, check ALL pages/dropdowns/stats that reference that table.
5. **Attendance Rule** — Dates ISO YYYY-MM-DD, names whitespace-folded, status canonical. Loose-filter on Python side for legacy.
6. **Labels Rule** — Users never see internal DB names. Every column gets an Arabic label.
7. **Student Sync Rule** — "بحث عن طالب" and "إضافة طالب" both pull from `/api/table/students/schema`. Never hardcode columns.

## 12. Communication preferences (user)

The operator (mindex.bh@gmail.com):
- Prefers Arabic for user-facing text; English when discussing code
- Wants concise answers; doesn't want over-explanation
- Prefers direct action over discussion ("auto-accept all, bypass mode active")
- Expects acknowledgment of context — don't ask what's documented
- Likes visual formatting (lists, tables, code blocks)
- Reviews via commit messages — they are the de facto changelog

## 13. Where to read next

| Question | File |
|---|---|
| What changed today? | `git log --oneline -10` |
| What changed this week? | `docs/memory/CHANGE_LOG.md` |
| Why did we choose X? | `docs/memory/DECISIONS_LOG.md` |
| How was bug Y fixed? | `docs/memory/BUGS_LOG.md` |
| How did the UI evolve? | `docs/memory/DESIGN_LOG.md` |
| When was file Z created? | `docs/memory/CODE_GENEALOGY.md` |
| What's the user been focused on? | `docs/memory/CONVERSATION_THEMES.md` |
| I'm a new AI — brief me | `docs/memory/HANDOFF.md` or `HANDOFF_COMPACT.md` |
| Active workflow rules | `CLAUDE.md` |
| DB schema details | `docs/DATABASE_AUDIT.md` |
| MCP setup | `docs/MCP_SETUP.md` |
| TWA / APK build | `docs/APK_BUILD.md` |
