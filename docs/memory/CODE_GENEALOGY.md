# CODE_GENEALOGY.md

Per-file / per-route history for the mindex-portal codebase. Maintained by `memory-keeper-agent`. For each major surface: when it was created, why, the major rewrites since, and current state.

For per-line blame, use `git log -L <line>,<line>:<file>`. This file is the higher-altitude view.

## `app.py` (the monolith)

- **Origin**: 2026-04-02. The first commit was a barely-running Flask app with a login form and a stub home page.
- **Growth trajectory**: ~250 LOC at start → ~5000 LOC end of April → 25K mid May → **~105,500 LOC** at audit (2026-05-15).
- **Function count**: 874 (`grep -c '^def '`).
- **Route count**: 502 (`grep -c '@app.route'`).
- **Decision**: never split (ADR-001). Multiple blueprint-split candidates noted; not actioned.

## Page templates (top-level `*_HTML` constants)

| Constant | Approx line | Introduced | Purpose |
|---|---|---|---|
| `LOGIN_HTML` | 326 | 2026-04 (week 1) | Login form, the one place users hit before auth |
| `HOME_HTML` | 376 | 2026-04 (week 1) | Post-login landing (per-role variant) |
| `ATTENDANCE_HTML` | 494 | 2026-04 (week 1) | Attendance taking page |
| `DATABASE_HTML` | 1019 | 2026-04 (week 2) | Generic spreadsheet-style table editor |
| `GROUPS_HTML` | 3684 | 2026-04 (week 2) | Group CRUD + filters |
| `ADMIN_BACKUPS_HTML` | * | 2026-04 (week 3) | DB snapshot / restore UI |
| `ADMIN_BOOKS_HTML` | * | 2026-04 (week 4) | Books library admin |
| `ADMIN_DOCS_HTML` | * | 2026-04 | Docs/onboarding page editor |
| `ADMIN_EVALUATIONS_HTML` | * | 2026-04 | Evaluations admin view |
| `ADMIN_EVENT_*_HTML` (3) | * | 2026-05 | Event-planning module (`ev_*` tables) |
| `ADMIN_LESSONS_HTML` | * | 2026-04 | Lessons-log admin |
| `ADMIN_PARENT_MESSAGES_HTML` | * | 2026-04 | Parent message broadcast UI |
| `ADMIN_PERMISSIONS_HTML` | * | 2026-04 | User permissions admin |
| `ADMIN_RECEIPTS_HTML` | * | 2026-04 | Payment receipts admin |
| `ADMIN_TEACHER_DELIVERIES_HTML` | * | 2026-05 | Books-to-teacher delivery tracking |
| `ADMIN_VIOLATIONS_*_HTML` (2) | * | 2026-05 | Violations catalog + records |
| `ASSETS_HTML` | * | 2026-05 | Asset tracking page (empty in prod) |
| `EXPENSES_ADMIN_HTML`, `EXPENSES_RAED_HTML` | * | 2026-05 | Expense management |
| `POINTS_BOARD_HTML` | 81439 | 2026-05-04 | The kid-facing points board |
| `POINTS_BULK_ADJUST_HTML` | * | 2026-05 | Manual points adjustment page |
| `POINTS_MANAGE_HTML` | * | 2026-05 | Points manager (admin/teacher) |
| `PARENT_HTML` | * | 2026-04 | Parent hub landing |
| `PARENT_HUB_*_HTML` (many) | * | 2026-05 | Parent hub sub-views |
| `PARENT_SHOP_HTML` | * | 2026-05-08 | Cart-based redemption |
| `BOOK_VIEWER_HTML` | * | 2026-05-13 | Custom view-only PDF renderer |

(* line numbers fluctuate; use `Grep '^<NAME>_HTML\s*='` to find current location.)

## Key feature subsystems

### Attendance (~April 2026)
- First write path: 2026-04 week 1 (`/attendance` page + `/api/attendance/*`).
- Rewrite milestone: `att_normalize_v1` migration (April–May) — fixed the legacy `D/M/YYYY` / `D/M-YYYYم` date formats. Codified the ISO-YYYY-MM-DD rule (ATTENDANCE RULE in CLAUDE.md).
- Current state: 3618 rows on prod, 100% ISO-date-formatted. Three canonical status values.

### Database editor + custom tables (~April week 2)
- `_compute_table_schema(tid)` introduced as single source of truth (SYNC RULE in CLAUDE.md).
- `column_labels`, `group_col_labels`, `att_col_labels`, `taqseet_col_labels`, `paylog_col_labels`, `eval_col_labels` — per-table label tables.
- `custom_tables` + `custom_table_cols` + `custom_table_rows` — runtime user-defined tables. 0 rows in prod — feature exists but unused.

### Taqseet + payments (~April week 3)
- `taqseet` table introduced with 30 Arabic-named columns (`القسط_1`..`القسط_12`, `تاريخ_الاستحقاق_*`, etc.). ADR-014 candidate to rename to ASCII.
- `student_payments` for per-student-per-installment mirroring.
- `payment_log` (older flat log) preserved alongside.
- 2026-04 (commit 85f15ed): mirror `student_payments.paid` into `taqseet.paidN`.

### Books_v2 (~April week 4)
- Schema: `books_v2`, `books_v2_groups`, `books_v2_teachers`, `book_folders`, `book_folder_groups`.
- Custom view-only PDF renderer at `/parent/book/<bid>/viewer` (May 13). Uses `pypdfium2` for page rasterisation.
- Chunked upload via `upload_sessions` (May 13).
- Orphan probe at boot — fixed May 15 (commit f7e62c9).

### Curriculum library (~April week 4)
- `curriculum_files` + `curriculum_assignments` + `curriculum_access_log`.
- PDFs on persistent disk at `/var/data/curriculum/<sha256>.pdf`.
- Cloudinary fallback when configured.
- Per-target permission model (group / student / parent / teacher).
- Migration tag: `curriculum_v1`.

### Points / behaviors / avatars / achievements (~May 2026)
- 2026-05-04: feature wave (123 commits in one day).
- `point_events` is the active table (624 rows).
- `student_points_log` (1865 rows), `student_achievements` (225), `achievements` (15) — bulk-seeded then orphaned. See DATABASE_AUDIT.md §5.1.
- 2026-05-12: redemption shop ground-up.
- 2026-05-15: egg-hatch class-wide button.

### Parent hub (~April–May 2026)
- `/portal/parent-hub/*` family.
- 2026-05-11: Unicode bidi mark tolerance fix.
- 2026-05-12: PID-preserving back-button across views.
- 2026-05-13: evaluations back button preserves PID.

### Lessons log (~April 2026)
- Migration tag: `lessons_v1`.
- Teacher-only write within today/yesterday window.
- Admin retroactive edit (audit-trailed).

### Evaluations (~April 2026, v2 May)
- Migration tags: `evaluations_v1`, `evaluations_v2`.
- v2 added INTEGER score fields, `evaluation_month` YYYY-MM, computed `overall_score`, parent-release + WhatsApp-send audit columns.

### Trips (~May 2026)
- 8 trip-family tables. Scaffolded, never shipped.

### Push notifications (Phase 2, May 12–14)
- `pywebpush` + `py-vapid`.
- VAPID generator script: `scripts/generate_vapid.py`.
- 2026-05-14: VAPID generator rewritten using `cryptography` directly (more reliable than py-vapid CLI).
- 15 push subscriptions on prod.
- `notifications` table (admin broadcast log, 26 rows).
- Service worker v3.2.3 — heads-up category, action buttons, vibrate, tag/topic.

### TWA / Android APK (Phase 3, May 14)
- `twa-manifest.json` + `.github/workflows/build-apk.yml`.
- Bubblewrap CLI 1.23.0 (after multiple version-pinning iterations).
- `/.well-known/assetlinks.json` route driven by `TWA_SHA256_FINGERPRINT` env.

### Test infrastructure (May 15)
- `scripts/seed_test_users.py` — idempotent test user seed.
- `scripts/auto_test.py` — Playwright `BrowserSession` library.
- `scripts/run_e2e.py` — 8-test e2e suite.
- `scripts/safe_deploy.py` — tag → push → poll → rollback.
- `scripts/get_logs.py` — Render logs API.
- `scripts/db_query.py` / `db_backup.py` / `db_restore.py`.
- Two health endpoints in `app.py` (`/api/health`, `/api/health/deep`).

### Agent team (May 15)
- 13 custom subagents under `.claude/agents/`.
- 9 imported professional agents under `.claude/agents/imported/` (MIT, VoltAgent).
- Coordinator agent (`mindex-coordinator-agent`).
- Memory keeper agent (`memory-keeper-agent`) — owns `docs/memory/`.

### Slash commands (May 15)
- 10 under `.claude/commands/` + `/context` for memory-keeper handoff.

### Hooks (May 15)
- 5 Python helpers under `.claude/hook_scripts/`.
- 6th planned: post-commit memory tracker.

## Scripts (`scripts/` — 113 files)

Of 113 files, ~109 are historical `smoke_*.py` per-feature probes. The non-smoke files are:

| File | Purpose | Created |
|---|---|---|
| `backfill_session_date.py` | One-shot DB backfill (session_date column) | ~April |
| `generate_vapid.py` | One-shot VAPID keypair generator | 2026-05-12 |
| `seed_test_users.py` | Test user seed (idempotent) | 2026-05-15 |
| `auto_test.py` | Playwright library | 2026-05-15 |
| `run_e2e.py` | E2E suite | 2026-05-15 |
| `safe_deploy.py` | Auto-rollback deploy | 2026-05-15 |
| `get_logs.py` | Render logs | 2026-05-15 |
| `db_query.py` | Read-only DB shell | 2026-05-15 |
| `db_backup.py` | DB snapshot | 2026-05-15 |
| `db_restore.py` | DB restore | 2026-05-15 |

The `smoke_*.py` files are mostly stale (each was written to verify a specific feature at the time it landed). They are not part of the e2e suite; they're historical proof-of-work.

## `.claude/` ownership (this directory)

| Path | Owner | Notes |
|---|---|---|
| `.claude/agents/*.md` | various agents | 13 custom |
| `.claude/agents/imported/*.md` | VoltAgent (vendored) | 9 imported, MIT |
| `.claude/commands/*.md` | project-shared | 10 commands + /context |
| `.claude/hook_scripts/*.py` | project-shared | 5 hook helpers |
| `.claude/mcp_servers.json` | template | All disabled by default |
| `.claude/settings.local.json` | operator-personal | Gitignored |
