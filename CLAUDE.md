# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Standard operating procedure

For every non-trivial task, follow this loop:

0. **Vague request? Run `/plan` first.** If the operator's ask is a sentence-level wish ("الموقع بطيء", "أريد ميزة كذا"), invoke `prompt-engineer-agent` via `/plan <description>` to convert it into a phased plan with concrete agent invocations, scripts, and approval gates. Skip this step only when the work is clearly scoped (e.g. "fix the typo on line 1234" — no plan needed).
0a. **Risky-looking change? Run `/check` first.** Invoke `catastrophe-prevention-agent` via `/check <description>` for any change that touches data, removes/renames routes or columns, modifies auth, or could degrade UX. Only the human owner can override a REJECT verdict (via the explicit `override:catastrophe:<reason>` tag). The Bash hook auto-blocks the most dangerous patterns (DROP TABLE, DELETE FROM without WHERE, rm -rf, git push --force, etc.) until `/check` clears them.
1. **Investigate first.** Read the relevant code, query the DB with `scripts/db_query.py` if needed, scan recent commits with `git log -n 20 --oneline`. Don't propose changes until you understand the current behaviour.
2. **Create a safety tag.** Before any risky change, `git tag safety/pre-<feature>-<timestamp> HEAD`. `scripts/safe_deploy.py` does this automatically for deploys; for purely-local work, do it by hand if you're about to touch >5 files or migration code.
3. **Implement with atomic commits.** One concern per commit. Run `python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read())"` after every meaningful change to catch syntax issues before they ride a push to Render.
4. **Test locally.** `python app.py` in one terminal, `python scripts/run_e2e.py` in another. The e2e suite covers login + the four critical pages (dashboard, attendance, database, points board) — full pass before any push.
5. **Deploy through safe_deploy.** `python scripts/safe_deploy.py --feature <slug>` will tag, push, poll `/api/health`, run the smoke e2e against prod, and roll back automatically if anything goes red. Don't push to `main` by hand for non-trivial changes — you lose the auto-rollback.
6. **Verify against prod.** After the deploy lands, run `python scripts/run_e2e.py --base https://mindx-portal-1.onrender.com` once more. Same suite, different target — this catches Postgres-only failures that SQLite swallowed locally.
7. **Only report 'done' when verified.** If a safe_deploy rolls back, fix the root cause and retry — don't paper over with a "deploy is flaky" note. The protocol is the floor, not the ceiling.
8. **Log to memory-keeper.** After any feat:/fix:/refactor: commit lands (or the coordinator pipeline completes), invoke `memory-keeper-agent` in passive-tracking mode with the commit hash + task summary. The agent appends to `docs/memory/CHANGE_LOG.md` and any other relevant log (BUGS_LOG / DECISIONS_LOG / DESIGN_LOG). The post-commit hook surfaces a hint for qualifying commits — act on it.
9. **Regenerate handoff on session boundaries.** If the work concludes a session or hands off to another operator/AI, run `/context compact` (or `/context full` for the comprehensive version) so the next session opens with current state.

### Scripts you'll use constantly

| Script | Purpose |
|---|---|
| `scripts/seed_test_users.py` | Idempotent seed of admin_test / teacher_test / student_test / parent_test. Run once locally; run once against prod via `DATABASE_URL=... python scripts/seed_test_users.py` before your first `safe_deploy`. |
| `scripts/auto_test.py` | Library — Playwright `BrowserSession` with `login_as / navigate / click_button / screenshot / get_console_errors / check_no_500`. Import from your own probes. |
| `scripts/run_e2e.py` | Black-box e2e runner. `--smoke` for the bare minimum, `--base <url>` to target prod. Screenshots land in `scripts/screenshots/`. |
| `scripts/safe_deploy.py` | Tag → push → poll `/api/health` → run smoke e2e → auto-rollback. `--no-op` validates the protocol without changing code; `--no-push` is a dry run. |
| `scripts/get_logs.py` | Pulls Render logs filtered by `--since 30m --keyword foo --level error`. Requires `RENDER_API_KEY` / `RENDER_SERVICE_ID` / `RENDER_OWNER_ID`; falls back to the dashboard URL if any are unset. |
| `scripts/db_query.py` | Read-only DB shell. `--tables` lists, `--schema <table>` shows columns, positional arg runs a SELECT. Refuses non-read statements unless `--force-write`. Works against local SQLite by default; set `DATABASE_URL` for prod. |
| `scripts/db_backup.py` | Snapshots local SQLite to `backups/mindx-<ts>.db` or pg_dumps prod to `backups/mindx-<ts>.sql`. |
| `scripts/db_restore.py` | Replaces the live DB from a backup. **Destructive.** Refuses without `--yes-i-really-mean-it` and writes a `.before-restore-<ts>` safety copy on local restores. |

### Health endpoints

- `GET /api/health` — DB ping + scratch disk write. Used by `safe_deploy` as the deploy gate. Returns 503 if either fails.
- `GET /api/health/deep` — also returns row counts for every critical user-data table and verifies the books storage dir is writable. Cheap but more comprehensive; call from operator tooling, not on every probe.

Both endpoints are intentionally unauthenticated so a deploy script can hit them before the login form is reachable.

### Test credentials

Created by `scripts/seed_test_users.py` — keep these stable; the e2e suite depends on the exact strings:

- `admin_test` / `TestAdmin2026!` — role=admin
- `teacher_test` / `TestTeacher2026!` — role=teacher
- `student_test` / `TestStudent2026!` — role=student, linked to a `students` row with `personal_id=TEST-STUDENT-0001`
- `parent_test` / `TestParent2026!` — role=parent, linked_parent_for=`TEST-STUDENT-0001`

The seeded students row uses `personal_id='TEST-STUDENT-0001'` so it's trivially identifiable in the DB and won't collide with a real Bahraini CPR.

## Professional setup — complete reference

Every piece of automation lives under `.claude/` (committed) plus `scripts/` and `docs/`. Operator-personal settings stay in `.claude/settings.local.json` (gitignored).

### Custom subagent team (16 including coordinator)

| Agent | Specialty | Invoke when |
|---|---|---|
| `mindex-coordinator-agent` | Orchestrator | Any non-trivial task; "review X", "ship Y" |
| `catastrophe-prevention-agent` | **Supreme guardian** — 5-category disaster veto (data loss / breaking / security / performance / UX) | **MANDATORY** before any risky change. Only human owner overrides REJECT |
| `code-architect-agent` | Code organization (100K-line app.py) | Before major features, refactors |
| `database-architect-agent` | Expand-Migrate-Contract schema changes | Any schema change, DB optimization, audits |
| `data-protector-agent` | DROP/DELETE/migration gatekeeper | **MANDATORY** before any DDL |
| `feature-protector-agent` | Regression guard — vetoes changes that risk breaking existing features | **MANDATORY** before any change touching shared code, routes, templates, or APIs |
| `ui-designer-agent` | Palette / spacing / RTL | After HTML/CSS changes |
| `arabic-quality-agent` | Arabic grammar / terminology / labels | After user-facing text changes |
| `ux-employee-agent` | Workflow efficiency | Before approving features |
| `mobile-first-agent` | 360 px viewport / TWA / iOS | After UI changes; before APK |
| `real-user-tester-agent` | Persona walk-throughs | After UI changes; before "done" |
| `performance-watchdog` | p95 / memory / queries | Before heavy ops; on OOM |
| `business-analyst-agent` | Adoption / ROI / deprecation | Before features; quarterly |
| `documentation-keeper` | CHANGELOG / docs upkeep | After features; before releases |
| `memory-keeper-agent` | Project memory — CHANGE_LOG / DECISIONS_LOG / handoff briefings | After every feat/fix commit; on session boundaries |
| `prompt-engineer-agent` | Turns vague wishes into phased plans | Vague request? Run `/plan` first |

### Imported professional subagents (9, MIT-licensed)

Vendored from [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents) under `.claude/agents/imported/`. Each carries an HTML-comment attribution block and is renamed with the `imported-` prefix. See `.claude/agents/imported/README.md` for when to pick imported vs custom.

| Imported name | Specialty |
|---|---|
| `imported-security-auditor` | OWASP / compliance audits |
| `imported-code-reviewer` | PR-shaped review |
| `imported-sql-pro` | Advanced SQL optimization |
| `imported-debugger` | Stack-trace-driven debugging |
| `imported-incident-responder` | Active outage / breach response |
| `imported-python-pro` | Modern type-safe Python |
| `imported-api-designer` | REST/GraphQL design |
| `imported-test-automator` | Test framework architecture |
| `imported-postgres-pro` | Postgres-specific tuning, HA |

### Slash commands (14)

Project-specific commands under `.claude/commands/`. Each is a Markdown file with a frontmatter description and a body that becomes the prompt when `/command` is invoked.

| Command | Purpose |
|---|---|
| `/test` | Run `scripts/run_e2e.py` against the local dev server |
| `/deploy <slug>` | `scripts/safe_deploy.py` with pre-flight + DB-change detection |
| `/audit` | Fan out to 5 specialists; aggregate to `docs/audits/audit-<ts>.md` |
| `/logs <keyword>` | Pull last hour of Render logs filtered |
| `/backup` | Snapshot prod via `scripts/db_backup.py` |
| `/rollback` | List safety tags, double-confirm, reset |
| `/health` | Hit `/api/health` + `/api/health/deep`, per-subsystem report |
| `/feature <description>` | Delegate the full pipeline to `mindex-coordinator-agent` |
| `/sql <query>` | Read-only DB query (refuses writes) |
| `/screenshots <path>` | 360 / 768 / 1280 viewport captures via Playwright |
| `/plan <description>` | Turn a vague request into a phased plan via `prompt-engineer-agent` |
| `/context [compact\|full\|recent\|<topic>]` | Memory-keeper handoff generation / retrospective extraction |
| `/protect <change>` | `feature-protector-agent` regression-risk audit of a proposed change |
| `/check <change>` | `catastrophe-prevention-agent` 5-category disaster veto (data / breaking / security / performance / UX) |

### Lifecycle hooks (7)

Configured in `.claude/settings.local.json` (operator-personal, gitignored). Hook scripts ship in `.claude/hook_scripts/` (committed).

| Hook | Event / matcher | Behavior |
|---|---|---|
| `catastrophe_block.py` | PreToolUse / `Bash` | Pattern-blocks DROP TABLE / TRUNCATE / DELETE-without-WHERE / ALTER COLUMN / `rm -rf` on sensitive paths / `git push --force` / `git reset --hard origin/main` / `git filter-*` / `dropdb` / `pg_restore --clean`. Operator can bypass with `override:catastrophe:<reason>` inline tag. |
| `precommit_check.py` | PreToolUse / `Bash(git commit *)` | Block on `app.py` syntax errors or secrets in the staged diff (rnd_/ghp_/sk- + quoted-literal password/api_key/token/secret) |
| `prepush_check.py` | PreToolUse / `Bash(git push *)` | Warn on non-main branch, dirty tree, stale test marker. Never blocks. |
| `post_pyedit_syntax.py` | PostToolUse / `Edit\|Write` | `ast.parse` on .py; surface SyntaxError as a system message |
| `post_commit_memory.py` | PostToolUse / `Bash(git commit *)` | Surface memory-keeper hint when a qualifying commit lands (feat/fix/refactor) |
| `session_start.py` | SessionStart | Inject branch + `git status --short` + `git log -5` into context |
| `prompt_hints.py` | UserPromptSubmit | Keyword reminders (deploy/test/logs) + credential-rotation warning when token shape detected |

Each clone needs to enable these manually — `.claude/settings.local.json` is gitignored by design (some operators may want different per-user behavior).

### Optional MCP servers

`docs/MCP_SETUP.md` documents seven candidate MCP servers with use cases. `.claude/mcp_servers.json` is the template — every server is disabled by default (keys prefixed with `_`). Copy to `.mcp.json` and remove the underscore to enable.

Recommended starter set: **playwright** (interactive browser) + **postgres** via pgEdge or Zed fork with a dedicated read-only role (NOT the write-capable prod URL).

### Scripts

| Script | Purpose |
|---|---|
| `scripts/seed_test_users.py` | Idempotent seed of `admin_test` / `teacher_test` / `student_test` / `parent_test` |
| `scripts/auto_test.py` | Playwright `BrowserSession` library |
| `scripts/run_e2e.py` | 8-test e2e suite |
| `scripts/safe_deploy.py` | Tag → push → poll `/api/health` → smoke e2e → auto-rollback |
| `scripts/get_logs.py` | Render API wrapper |
| `scripts/db_query.py` | Read-only DB shell (refuses writes) |
| `scripts/db_backup.py` | Local SQLite or `pg_dump` snapshot |
| `scripts/db_restore.py` | Restore with safety copy |

### Health endpoints

- `GET /api/health` — DB ping + scratch disk write. Used by `safe_deploy` as the deploy gate.
- `GET /api/health/deep` — row counts + books storage writability.

### Workflow examples

**Ship a UI change to the points page:**
1. Edit `app.py` and `python scripts/run_e2e.py` locally.
2. `/audit` — fan out the 5-specialist review.
3. Fix any rejects, re-run `/audit` until clean.
4. `/deploy points-board-fixes` — auto-rollback on red.

**Ship a schema migration:**
1. `Agent(subagent_type: "database-architect-agent", prompt: "Discovery for column X")` — produces `docs/migrations/<name>-discovery.md`, STOPS for approval.
2. Approve plan → agent produces `<name>-plan.md`, STOPS again.
3. Approve → Phase A (Expand) commit + `/deploy <slug>-phase-a`. Monitor 24h.
4. Phase B (Migrate) — one call site per commit, `/deploy` each.
5. Phase C (Contract) — drop the old column. `/deploy <slug>-contract`.

**Quarterly architecture sweep:**
1. `/feature "quarterly review — flag deprecation candidates, audit migrations"`
2. Coordinator runs `business-analyst-agent` + `code-architect-agent` + `data-protector-agent` in parallel.
3. `documentation-keeper` consolidates findings; commits to `docs/audits/`.

**Live incident:**
1. `/health` — quick triage.
2. `/logs <keyword>` — recent errors.
3. `Agent(subagent_type: "imported-incident-responder", prompt: "<symptoms>")`.
4. If a recent deploy is the suspect: `/rollback`.
5. Postmortem written by `documentation-keeper` to `docs/incidents/`.

## Specialist agent team

Sixteen subagents live under `.claude/agents/`. Each is committed to the repo so every clone gets the same team. Invoke them through the `Agent` tool by `subagent_type` (the filename minus `.md`).

| Agent | Specialty | Invoke when |
|---|---|---|
| `mindex-coordinator-agent` | Orchestrator — plans which specialists to run, aggregates verdicts, makes go/no-go | Any non-trivial task; "review X", "ship Y" |
| `catastrophe-prevention-agent` | **Supreme guardian** — 5-category disaster veto (data loss / breaking / security / performance / UX). Writes verdicts to `docs/memory/CATASTROPHE_LOG.md` + `docs/memory/REJECTED_CHANGES.md` | **MANDATORY** before any risky change. Only human owner overrides REJECT |
| `code-architect-agent` | Code organization for the 100K-line app.py | Before major features, refactors, code reviews |
| `database-architect-agent` | Expand-Migrate-Contract schema changes | Schema changes, DB optimization, audits |
| `data-protector-agent` | DB safety — DROP/DELETE/TRUNCATE/migration/bulk-UPDATE gatekeeper | **MANDATORY** before any schema change or bulk data op |
| `feature-protector-agent` | Regression guard — vetoes changes that risk breaking existing features. Maintains `docs/memory/FEATURE_INVENTORY.md` | **MANDATORY** before any change touching shared code, routes, templates, or APIs |
| `ui-designer-agent` | Mindex palette (#4a148c / #6B3FA0), spacing rhythm, RTL | After HTML/CSS changes to the inline templates |
| `arabic-quality-agent` | Arabic grammar, terminology, RTL with mixed content | After any user-facing text change |
| `ux-employee-agent` | Workflow efficiency for busy teachers/admins | Before approving new features; on UX complaints |
| `mobile-first-agent` | 360 px viewport, touch targets, TWA/PWA, iOS Safari quirks | After UI changes; before APK releases |
| `real-user-tester-agent` | Persona walk-throughs (Umm Ahmed / Fatima / Mohammed / Admin) | After UI changes; before declaring done |
| `performance-watchdog` | 512 MB RAM, p95 ≤ 2 s, query counts | Before heavy ops; on slow reports; after OOM |
| `business-analyst-agent` | Usage analytics, ROI, deprecation calls | Before major features; quarterly reviews |
| `documentation-keeper` | CHANGELOG / docs/API.md / docs/ARCHITECTURE.md upkeep | After significant features; before releases |
| `memory-keeper-agent` | Project memory — CHANGE_LOG / DECISIONS_LOG / DESIGN_LOG / BUGS_LOG / handoff briefings | After every feat/fix commit; on session boundaries |
| `prompt-engineer-agent` | Turns vague wishes into phased plans | Vague request? Run `/plan` first |

### Example workflows

**Reviewing a UI change to the points page:**
```
Agent({subagent_type: "mindex-coordinator-agent",
       prompt: "Review the new points-grant modal at app.py:37450. Coordinate the full UI pipeline."})
```
The coordinator runs code-architect → ui-designer + arabic-quality + mobile-first (parallel) → ux-employee → real-user-tester → aggregates.

**Shipping a schema migration:**
```
Agent({subagent_type: "mindex-coordinator-agent",
       prompt: "Plan to add column 'parent_phone_verified' to students. Run the full safety pipeline."})
```
The coordinator runs data-protector FIRST (mandatory), then code-architect, then documentation-keeper. Only after all approve does it recommend `python scripts/safe_deploy.py --feature parent-phone-verified`.

**Quarterly architecture sweep:**
```
Agent({subagent_type: "mindex-coordinator-agent",
       prompt: "Quarterly review — flag deprecation candidates, audit migrations, identify blueprint-split targets."})
```
The coordinator runs business-analyst + code-architect + data-protector in parallel; documentation-keeper consolidates the writeup.

**Direct specialist invocation (skip the coordinator):**
```
Agent({subagent_type: "performance-watchdog",
       prompt: "Investigate the /api/groups/<gid>/detail slow-response report — p95 has crept past 3 s."})
```
Use direct invocation when only one specialist is needed; use the coordinator when multiple concerns overlap.

### Discipline

- **Never skip a mandatory reviewer.** data-protector is mandatory for any DB-touching change; the coordinator will refuse to give a green verdict without it.
- **Don't paraphrase a specialist.** When relaying their verdict, quote their report block verbatim or include the full text — don't summarise away the actionable details.
- **One coordinator at a time.** Running two coordinators in parallel on overlapping scope causes contradictory verdicts.
- **The deploy step is the coordinator's call.** Specialists recommend; the coordinator decides; `safe_deploy.py` executes.

## Running & deploying

- `pip install -r requirements.txt` — install deps (Flask + gunicorn, Python 3.12.3 per `runtime.txt`).
- `python app.py` — local dev server on `PORT` (default 5000), `host=0.0.0.0`.
- `gunicorn app:app --bind 0.0.0.0:$PORT` — production entrypoint (see `Procfile`, `render.yaml`). Deployed on Render.com.
- No test suite, linter, or build step exists. There is no `package.json`, no Jinja templates, no frontend build pipeline.

Environment variables:
- `SECRET_KEY` — Flask session key (generated by Render; local default `"mindx2026secret"`).
- `DB_PATH` — SQLite file path (prod uses `/tmp/mindx.db`; local default `mindx.db`).

## Architecture

**Everything lives in `app.py` (~4100 lines).** The only other source files are `login.html` (an unused standalone copy of the login page) and `app.html` (placeholder). All served HTML is inline Python string constants.

Page templates are module-level strings concatenated at request time — not Jinja:
- `LOGIN_HTML` (line ~326), `HOME_HTML` (~376), `ATTENDANCE_HTML` (~494), `DATABASE_HTML` (~1019), `GROUPS_HTML` (~3684).
- Routes return these strings directly; `render_login()` does a `.replace("ERROR_PLACEHOLDER", ...)` for the only templating. Do not introduce `render_template` — there is no `templates/` directory.

**Dual-path schema management.** `app.py` runs schema setup at import time (lines ~167–316), split into two branches:
- If `DB_PATH` does not exist → `init_db()` runs full `CREATE TABLE` statements and seeds default rows/users.
- If it exists → an idempotent block re-runs `CREATE TABLE IF NOT EXISTS` for any newer tables, then `ALTER TABLE ... ADD COLUMN` for any columns in the `new_cols` / `tq_existing` lists that aren't present yet.

When adding a column, you must update **both** branches: the `CREATE TABLE` in `init_db()` AND the migration list in the `else` branch. Otherwise existing deployments (Render's persistent `/tmp/mindx.db`) won't get the column. Same applies for new tables — add `CREATE TABLE IF NOT EXISTS` to both branches.

**Tables:** `users`, `students`, `student_groups`, `attendance`, `taqseet` (installment plan templates, keyed by `taqseet_method`), `student_payments` (per-student-per-installment), `lessons_log` (Category B feature table — teacher-recorded lesson topics + curriculum progress per group per session, with admin-only retroactive `lesson_date` edit; introduced by migration `lessons_v1`), `parent_messages` + `parent_message_reads` (Category B feature tables — teacher broadcast "ماذا تريد أن يعرف ولي الأمر" structured form per group; broadcasts are queued through the existing `message_log` WhatsApp pipeline and surfaced to parents in `/portal/parent-hub/messages` with read-state tracking; introduced by migration `parent_messages_v1`), `evaluations` (Category B feature table — monthly evaluation form "استمارة التقييم الشهري"; v2 columns added by migration `evaluations_v2` extend the legacy form-fill schema with INTEGER 1-10 `score_*` fields, `evaluation_month` YYYY-MM, `student_id` / `teacher_id` joins, computed `overall_score`, plus `released_to_parent` portal-visibility flag and `whatsapp_sent_at` / `whatsapp_sent_by` admin send-to-parent audit. Legacy TEXT columns kept intact for backwards compat — never drop), `curriculum_files` + `curriculum_assignments` + `curriculum_access_log` (Category B feature tables — مكتبة المناهج: admin/manager uploads PDFs and assigns each to specific groups, students, parents, or teachers with optional view-only / download permission. PDF binaries live on the persistent disk at `/var/data/curriculum/<sha256>.pdf` (local fallback `./data/curriculum/`) — NEVER under `/static/`. `curriculum_assignments.target_type` ∈ {`group`,`student`,`parent`,`teacher`} with `target_id` carrying the matching identifier (group_name TEXT for groups, students.id for students, users.id for parents/teachers). `curriculum_access_log` records every view/download attempt with `user_id` + `ip_address`. Introduced by migration `curriculum_v1`), plus label/visibility tables `column_labels`, `group_col_labels`, `att_col_labels`, and the generic `custom_tables` / `custom_table_cols` / `custom_table_rows` trio (user-defined tables built at runtime via the UI).

**Authoritative scheduled-days column.** The `student_groups` table ships with a canonical `study_days` TEXT column, but the admin's "تعديل الجدول" modal can also add a custom column labelled "أيام الدراسة" (the label is stored in `group_col_labels` with an auto-generated `col_<timestamp>` internal name). **Crucially, the edit-table modal stores Arabic labels as HTML numeric entities** (e.g. `&#x623;&#x64A;&#x627;&#x645; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;` for "أيام الدراسة"), so any code looking up a column by label MUST first run the stored value through `_decode_arabic_entities` and then compare folded forms (`_grp_norm` on both sides) — a literal-string compare against raw Arabic will silently miss the user-added column and the resolver will fall back to the empty `study_days` legacy column. This is what `_groups_days_column(db)` does today. Whenever code needs a group's scheduled-days value it MUST go through `_groups_days_column(db)` + `_extract_days_from_row(rd)`:

**أيام الدراسة column format.** Real human data entry mixes:
- The Arabic conjunction " و " as the day separator (`"الجمعة و السبت"`, `"الإثنين و الاربعاء"`).
- Legacy commas / Arabic comma `، / ,` and slashes `/` and ` - ` from older imports.
- Spelling variants — `ا/أ/إ/آ`, `ة/ه`, with/without diacritics — within the same column (`الإثنين` vs `الاثنين`, `الأربعاء` vs `الاربعاء`, `الجمعه` vs `الجمعة`).

Always parse via the shared `_parse_study_days(text)` helper (or its alias `_grp_extract_days(text)`). It Arabic-folds via `_grp_norm`, splits on every separator, and looks each token up in a folded → canonical map so every spelling collapses to ONE canonical name per weekday (`الإثنين` / `الأربعاء` / `الجمعة` / etc.). NEVER hardcode `text.split('،')` or substring-search the raw cell — it produces duplicate weekday entries in the days facet and breaks anomaly detection.
- `_groups_days_column(db)` resolves which physical column on `student_groups` the admin currently treats as authoritative (custom-labelled column wins; defaults to `study_days`). Result is cached on `flask.g._groups_days_col` per request.
- `_extract_days_from_row(rd)` runs the resolved column as **Strategy 0** before falling back to `study_days` (Strategy 1) and the legacy heuristics (Strategies 2–4). Self-primes via flask.g if a handler forgot to call `_groups_days_column` first.
- SELECTs that previously listed `study_days` explicitly must add the resolved column too (search for `extra_days = ('"' + days_col + '", ')` for the established pattern). SELECT * already picks it up automatically.
- Per-row fallback: `_row_days_authoritative(rd, days_col)` prefers the custom column for THIS row and falls back to study_days when the new column is empty for THIS row, so a partially-migrated table doesn't lose day-of-week info.

The legacy `study_days` column is preserved (do NOT drop it). Reads go through the resolver; writes still target whatever column the user is editing in the database UI.

**Taqseet ↔ student_payments sync.** `POST /api/payments/<sid>/<n>` writes to `student_payments` AND mirrors the paid amount into `taqseet.paidN` for the row whose `taqseet_method` matches the student's `installment_type`. If you touch payment logic, keep that mirroring intact (see recent commit `85f15ed`).

**DB access pattern.** `get_db()` lazily opens a `sqlite3` connection on `g.db` with `Row` factory; `teardown_appcontext` closes it. Passwords hashed via `hp()` (SHA-256, no salt). Auth is a session cookie + `@login_required` decorator; `session["user"]` holds the full user row as a dict. Roles exist (`admin`, `reception`, `teacher`, etc.) but are **not currently enforced** in routes — the decorator only checks login.

**Route layout.** `/` renders login and clears session; `/login` (POST) authenticates; `/dashboard`, `/database`, `/attendance`, `/groups` return their respective HTML blobs. All data endpoints are under `/api/*` and return JSON. See lines ~3026–4103 for the full route table.

## Dynamic Configuration System

**CRITICAL RULE:** Any new feature, button, dropdown, or page that references a table name or column name MUST:
1. Read the reference via `get_setting(page, component, default)` with a sensible fallback default.
2. Add its configuration entry to the `settings` table seed (both `init_db()` and the `settings_seed_v1` migration in the else branch) and — if applicable — surface it on the `/settings` page.
3. Never hardcode table or column names directly in routes or HTML that serves data.

This rule has no exceptions. The `settings` table stores `(page, component, label, value, value_type)` and is seeded on a fresh DB; the `/api/settings` endpoints read/write it and the `/settings` page is the admin UI.

The helper API:
- `get_setting(page, component, default)` — never raises; returns `default` on any error.
- `get_all_tables()` — lists every `public` Postgres table (or `sqlite_master` table, locally).
- `get_table_columns(table_name)` — `PRAGMA table_info` wrapper (safe-ident validated).
- `GET /api/settings` — all settings grouped by page.
- `PATCH /api/settings` — body `{page, component, value}` upserts one row.
- `GET /api/settings/tables` — table list for the UI.
- `GET /api/settings/columns/<table_name>` — columns for the dependent dropdown.

Any SQL string that interpolates a value from `get_setting` MUST pass it through `_is_safe_ident(...)` and fall back to the hardcoded default on failure — `get_setting` does not do that validation itself.

## Table creation policy

**Before creating any new table:**

1. Document its purpose, owning feature, and lifecycle in this file (under the migration that introduces it).
2. Add it to one of the three classification sets in the table-audit module (`_TBL_AUDIT_CORE`, `_TBL_AUDIT_FEATURE`, `_TBL_AUDIT_SYSTEM`) so it doesn't surface as a Category-D orphan in the audit UI.
3. Update the dual-path schema block: `init_db()` `CREATE TABLE` for fresh DBs **AND** an `else`-branch `CREATE TABLE IF NOT EXISTS` migration tag for existing DBs.
4. Never create temporary or experimental tables in production. If you need to prototype, do it in a local SQLite DB or under a feature-flagged migration tag that's reverted before merge.
5. **If a feature is dropped, drop its tables in the same commit** — don't leave orphan tables behind. Update both the migration block and the table-audit classification sets.
6. Quarterly run `GET /api/admin/table-audit` (or open the UI at `/admin/table-audit`) and clean up any Category-D orphans.

The audit UI is admin-only and goes through the auto-pre-destructive-backup flow before any DROP. Approved-keep tables are persisted in `settings(page='table_audit', component='approved_<name>')` so they stay quiet across audits.

A startup warning fires once per process if any orphan candidate is detected (Category D + empty + not approved-keep) — check the Render logs after every deploy.

## Deployment notes

- Hosted on **Render Starter plan** ($7/mo) with a 1 GB persistent disk mounted at `/var/data`. Same disk holds the SQLite DB (`/var/data/mindx.db`) and the Playwright browser cache.
- Build command (committed in `render.yaml`):
  ```
  pip install -r requirements.txt &&
  python -m playwright install chromium &&
  (python -m playwright install-deps chromium || echo "[deploy] install-deps non-fatal failure")
  ```
  `install-deps` is best-effort — if the build environment refuses (e.g. future Render image change), the deploy still succeeds and the docs system falls back to manual upload.
- Required env vars (also in `render.yaml`):
  - `SECRET_KEY` (auto-generated by Render)
  - `DB_PATH=/var/data/mindx.db`
  - `PLAYWRIGHT_BROWSERS_PATH=/var/data/playwright-browsers` — caches the ~150 MB Chromium binary on the persistent disk so it doesn't re-download every deploy.
  - `PYTHONUNBUFFERED=1` so the boot log lines stream out promptly.
- **`render.yaml` doesn't auto-apply on existing services.** When you change build configuration via this file, also paste the new build command into the Render dashboard manually:
  > Render dashboard → mindx-portal service → Settings → Build & Deploy → **Build Command** → paste the multi-line command above → Save Changes → **Manual Deploy** → "Clear build cache & deploy".
  Subsequent deploys will reuse the cached Chromium from `/var/data/playwright-browsers`, so they're fast. The first deploy after the change pays the one-time download cost.
- **Boot probe**: `_docs_startup_chromium_check()` runs on every process import and prints one of two lines to stderr (visible in Render's "Logs" tab):
  - `[mindex-docs] ✅ Playwright + Chromium ready. Auto-capture enabled.`
  - `[mindex-docs] ⚠ Auto-capture unavailable — <reason> — falling back to manual upload.`
  - If you see the warning, check the most recent build log first for `playwright install chromium` errors before debugging anywhere else.
- The probe actually launches headless Chromium (not just `import playwright`) because the Python lib imports cleanly even when the browser binary is missing — that's the silent-failure mode that broke auto-capture before this fix landed.

## Database type notes

**DATABASE TYPE NOTES: Production runs on PostgreSQL (Render). PostgreSQL is strict about types — never use empty string `''` as a fallback for `timestamp`, `integer`, or other non-text columns. Use `NULL` or a proper typed default. Test all SQL queries against PostgreSQL behavior, not SQLite.**

The `_PgConnection` wrapper translates `?` → `%s` and auto-appends `RETURNING id` (with the `_NO_ID_COLUMN_TABLES` exception list), but it does NOT rewrite SQL semantics — so type-mismatch errors that SQLite swallows silently will surface on prod. Common pitfalls:

- `COALESCE(<timestamp_col>, '')` — Postgres error: "invalid input syntax for type timestamp". Drop the COALESCE and let JSON `null` reach the frontend (most renderers already show `—` for falsy), or cast first: `COALESCE(<col>::text, '')`.
- `COALESCE(<int_col>, '')` — same problem. Use `COALESCE(<col>, 0)`.
- Inserting empty strings into typed columns. On INSERT/UPDATE, pass Python `None` (→ SQL `NULL`) for missing timestamps/numbers, never `''`.
- `WHERE ts_col = ''` — Postgres error. Use `WHERE ts_col IS NULL` for the same intent.
- Column type mismatches between `init_db()` and the `else`-branch `ALTER TABLE`. The fresh-DB CREATE and the existing-DB ALTER must declare the same SQL type (e.g. both `DATETIME`/`TIMESTAMP`, not one `TEXT`). SQLite is forgiving; Postgres is not.

When in doubt, mentally compile the query with `psql` semantics — that's the runtime that matters.

## Data safety (CRITICAL DATA SAFETY RULE)

**NEVER** use `DROP TABLE`, `DELETE FROM <whole-table>`, or `TRUNCATE` on any user-data table in `app.py`. Every deployment must leave existing rows 100% intact.

- `init_db()` is gated by `if not os.path.exists(DB_PATH)` for SQLite and by `USE_PG` branching for Postgres; it only runs full `CREATE TABLE` + seed on a truly empty DB. Existing DBs go through the `else` branch, which must use **`CREATE TABLE IF NOT EXISTS`** and **`ALTER TABLE ... ADD COLUMN`** only — never `DROP`, never `DELETE`, never `TRUNCATE`.
- Seeding default rows (users, settings, label rows) must be gated by an emptiness check or an `ON CONFLICT DO NOTHING` clause — never blind inserts that duplicate or wipe data.
- Gate every destructive migration behind a `schema_migrations` tag **plus** verify the tag actually persists (see next bullet). If it doesn't, the "one-shot" runs forever.
- **Postgres INSERT-through-wrapper caveat (fixed in commit after dd36a0c):** `_PgConnection.execute` auto-appends `RETURNING id` to every `INSERT`. Tables without an `id` column (e.g. `schema_migrations` with `tag TEXT PRIMARY KEY`) raise an `UndefinedColumn` error that the migration's `try/except` swallows silently, so the tag never gets saved and the "one-shot" migration runs on every boot. The wrapper now consults `_NO_ID_COLUMN_TABLES` to skip the auto-RETURNING for those tables. If you add another id-less table, **append it to that set** or migrations gated by its tags will re-run forever.
- After any migration edit, eyeball prod `schema_migrations` (`SELECT tag FROM schema_migrations ORDER BY tag`) to make sure the tags you expect are persisted.
- The destructive `drop_paylog_v1` migration that used to wipe `payment_log` has been removed from the code. The tag is still seeded on prod to be defensive — never re-add a `DROP TABLE` guarded only by a migration tag for a user-data table.

Row-level `DELETE` (individual user-initiated deletes, e.g. one student, one attendance record, one template) is fine and required for the app's features. The rule is about never losing **other** users' rows through a code change.

## Schema sync (SYNC RULE)

**SYNC RULE:** The تعديل الجدول modal and the table display must always use the same data source — `/api/table/<tid>/schema` (or the older `/api/custom-table/<tid>/columns` alias, which is a superset). After any column operation, always call `window.refreshTable(tid)` to update both. Never maintain separate column lists.

Canonical helpers:
- **Server:** `_compute_table_schema(tid)` in `app.py` is the one place that computes "the ordered list of columns for a table". Reads `PRAGMA table_info(<live_table>)` for built-ins or `custom_table_cols` for numeric tids, joins with `*_col_labels` for display names / types, and orders by `col_order` with the live-schema position as a tie-breaker. Every endpoint that returns columns — `/api/custom-table/<tid>/columns`, `/api/table/<tid>/schema`, and the `updated_schema` echo on every mutation route — goes through this helper.
- **Client:** `window.refreshTable(tid)` in `/mx-helpers.js` clears `_MX_COLKEY_CACHE`, fires the page-level reloader via `TABLE_REFRESH_HOOKS` (so tbody re-renders from fresh data), and — if the UTEM modal is currently open for the same tid — re-opens it to pick up the fresh schema. Call this after **every** successful add / delete / rename / reorder / type-change.

Mutation endpoints return `updated_schema` alongside `ok:true`, so a caller can skip a round-trip if it wants to. The client side currently just calls `refreshTable`, which is one fetch; using `updated_schema` as an optimisation is optional.

**Do not** — in any new code —
- hardcode a column-name list in a renderer (taqseet's `baseFields` is the lingering pre-SYNC-RULE example; replace it when touching that area).
- fetch `/api/custom-table/<tid>/columns` directly from a mutation success handler; call `refreshTable(tid)` instead so the UTEM modal and the tbody stay in lock-step.

## Excel import pipeline

**IMPORT RULE:** When implementing or modifying any Excel import for any table, always check ALL pages, dropdowns, buttons, and statistics that reference that table and ensure imported data appears correctly everywhere immediately after import.

Every table on the database page imports via `POST /api/import` with body `{table, rows, auto_create?, column_labels?}`. The endpoint:

- Whitespace-folds every text value (strip + collapse internal runs) via `_import_normalize_value()`.
- Maps attendance `status` values to canonical Arabic: `غياب→غائب`, `تأخير→متأخر`, `حضور→حاضر`, plus the English variants `absent/late/present`. See `STATUS_REMAP`.
- Validates typed columns (نص / رقم / تاريخ / نعم-لا / قائمة منسدلة / تقييم) from the corresponding `*_col_labels` table via `_import_coerce_by_type()`. Invalid values are skipped with a reason.
- Upserts on natural keys declared in `IMPORT_TABLE_KEYS`: `students.personal_id`, `student_groups.group_name`, `attendance(group_name, attendance_date, student_name)`, `taqseet(taqseet_method, student_name)`, `evaluations(form_fill_date, group_name, student_name)`, `payment_log.student_name`. When every key column is non-empty AND a matching row exists, the non-key columns are UPDATED (only where the incoming value is non-empty, so blanks never overwrite existing data). Otherwise INSERT.
- Returns `{ok, table, inserted, updated, skipped, errors, received, skip_reasons[], last_error, fields_used[]}` — the clients display a toast with those counts and dispatch a `mx-imported` CustomEvent.

**When adding a new importable table:**
1. Add its field list to `IMPORT_TABLE_FIELDS` and its INSERT skeleton to `IMPORT_TABLE_SQL`.
2. Declare the natural key tuple in `IMPORT_TABLE_KEYS` (omit to disable upsert — only safe for custom-tables where the user owns identity).
3. If the table has typed columns, register its labels table in `IMPORT_LABEL_TABLES` so type validation kicks in.
4. Add the refresh-hook names (e.g. `loadXxx`) to `TABLE_REFRESH_HOOKS` inside `MX_HELPERS_JS` so a successful import immediately repopulates the current page.
5. If any **other** page references this table (dropdowns, stats, dashboards), verify those pages pull live from their API endpoint (not a cached JS global). Cross-page refresh is unnecessary because each page refetches on load; the rule exists to prevent stale in-page caches.

## Attendance data format (ATTENDANCE RULE)

**ATTENDANCE RULE:** All attendance records must store dates as `YYYY-MM-DD`, group names and student names must be stripped of extra spaces. The attendance page must use normalized comparison (whitespace-tolerant trim) when loading records, never exact string match.

Root bug this rule prevents: the DB briefly shipped with dates written as `31/1-2026م` / `9/2/2026م` (Arabic era suffix, mixed separators). The `<input type="date">` in the attendance page always sends ISO `YYYY-MM-DD`, so the existing `WHERE attendance_date = ?` matched zero rows and the page showed blank dropdowns on groups that clearly had imported data.

Guardrails now in place:
- `_att_normalize_date(s)` — accepts every historic format (`D/M/YYYY`, `D/M-YYYYم`, `Y/M/D`, `DD-MM-YYYY`, etc.) and returns ISO `YYYY-MM-DD`.
- `_import_normalize_value` routes any field in `DATE_FIELD_NAMES` through `_att_normalize_date`, so no future Excel row can re-introduce the problem.
- `/api/attendance/check` fetches every row matching the trimmed group name, then filters by normalised date on the Python side. Legacy values written by a path that bypassed import still resolve correctly.
- `att_normalize_v1` migration (in the else-branch of schema management, gated by `schema_migrations.tag`) rewrites every existing row's `attendance_date`, `group_name`, `student_name`, and `status` on first boot after deploy.

When adding any code that reads or writes `attendance.*`:
1. Store dates via `_att_normalize_date(value)`.
2. Store group/student names via `" ".join(name.split())` (strip + collapse whitespace).
3. Never compare dates with plain `=` — either normalise both sides first or use the loose filter-in-Python pattern shown in `api_attendance_check`.
4. Status values must be canonical: `حاضر`, `غائب`, `متأخر`. Use `STATUS_REMAP` to fold imports.

## Display labels (LABELS RULE)

**LABELS RULE:** Users must NEVER see internal DB names. Always use Arabic display labels in UI. Internal names are only used in backend queries. Every new column or table must have an Arabic display name registered in the labels system.

Label lookup precedence (all go through helpers in `app.py`):
1. **Tables** — `_table_display_label(name)` reads `table_labels.tbl_label` first, then falls back to `BUILT_IN_TABLE_LABELS`, then the raw name.
2. **Columns** — `_column_label_map(table)` merges the per-table `*_col_labels.col_label` row (for tables listed in `_LABELS_TABLE_FOR`) over `BUILT_IN_COLUMN_LABELS`, then the raw column name.
3. **Entity decoding** — legacy rows stored labels as HTML numeric entities (`&#x627;...`). `_decode_arabic_entities()` unescapes them so `_esc()` on the JS side doesn't double-encode the `&`.

Endpoints that now return `{name, label}` pairs instead of bare strings:
- `GET /api/settings/tables` — table dropdowns in `/settings`.
- `GET /api/settings/columns/<table_name>` — column dropdowns in `/settings`.
- `GET /api/custom-table/<tid>/columns` — تعديل الجدول modal. Also returns `db_table_label` alongside `db_table`.

**When adding a new table:**
1. Add a row to `table_labels` (both `init_db()` seed and the `table_labels_seed_v1` migration block in the else-branch — same dual-write pattern as any other table).
2. If the table has typed columns, also seed Arabic `col_label` rows in the corresponding `*_col_labels` table; otherwise append fallback entries to `BUILT_IN_COLUMN_LABELS` so every column renders Arabic in /settings and تعديل الجدول on day one.

**When adding a new column:**
1. Register a label via the per-table labels table (e.g. `INSERT INTO column_labels(col_key, col_label, ...)`) or add it to `BUILT_IN_COLUMN_LABELS`.
2. Keep the internal name ASCII/snake_case; Arabic goes into the label column only.

Never concatenate a raw column/table name into user-visible HTML. Route it through one of the helpers.

## Working with Arabic text

The UI is Arabic, RTL (`<html lang="ar" dir="rtl">`). Arabic strings in Python source are stored as HTML numeric entities (`&#x627;` etc.) inside the HTML blobs, and as `\uXXXX` JS escapes inside inline `<script>` blocks. This is deliberate — see commit `74b87ac` ("replace mojibake Arabic strings with Unicode escapes"). Do not paste raw Arabic into `app.py`; it gets mangled on Windows/Render round-trips. When adding new UI strings, use the existing escape style of the surrounding block.

**Surrogate-pair caveat:** never write JS escapes for non-BMP codepoints (e.g. `🔒`) inside a Python triple-quoted string — Python parses them as actual Unicode escapes, leaving lone surrogates in the in-memory string that crash UTF-8 response encoding at request time. Build the codepoint at runtime instead (e.g. `String.fromCodePoint(0x1F512)`).

## Student sync (STUDENT SYNC RULE)

**STUDENT SYNC RULE:** بحث عن طالب and إضافة طالب must ALWAYS use `/api/table/students/schema` to get current columns dynamically. Never hardcode student-table columns in these two features. Any column change in the `students` table must automatically reflect in both surfaces.

How this is enforced today:
- **Backend** — `POST /api/students` and `PUT/PATCH /api/students/<id>` are dynamic: they whitelist body keys against `PRAGMA table_info(students)` at request time. New columns added via the table-edit modal are auto-supported. PUT/PATCH only update the keys actually sent — no more silent NULL-overwrites of unchanged columns when the search-detail save flow sends only diffs.
- **Duplicate check** — `POST` and PID-renaming `PUT/PATCH` reject duplicates with HTTP 409 + `{duplicate:true, existing_name, existing_id}` so the UI can surface "هذا الرقم الشخصي مسجل مسبقاً للطالب: [name]".
- **Frontend (`/mx-helpers.js`)** — `mxLoadStudentsSchema()` (cached 30s) and `mxAppendCustomFields(container, idPrefix, knownIds, schema, valuesByKey, opts)` render any column NOT in the static field list as an extra control under the existing modal/card layout. Each control carries a `data-mx-field` attribute keyed by the DB column name; `mxCollectCustomFieldValues` reads the values back.
- **إضافة طالب modal (`STUDENT_FORM_MODAL_HTML`)** — has a `<div id="sra-extras">` slot at the end of its grid. `srOpenAddStudent` repopulates it on every open. `srSaveAddStudent` merges its values into the POST body.
- **بحث عن طالب card (`_srRenderCard`)** — has a `<div id="sr-extras">` slot. The renderer hooks `mxAppendCustomFields` after the static fields and snapshots the values into `_srOriginal['__extra_<col>']` so `_srComputeDiff` includes them in the change set.

When you add a new feature that reads or writes the students table:
1. **Never** hardcode a list of student columns in JS. Always go through `mxLoadStudentsSchema()` or `mxAppendCustomFields()`.
2. **Never** hardcode a list of student columns in a server route. Always whitelist against `_students_live_columns(db)`.
3. If the new feature needs a special widget for a specific column (e.g. linked dropdown), branch on `col_type` / `col_options` from the schema rather than the column name.

## Seeded credentials

`init_db()` seeds: `admin/admin123`, `reception/rec123`, `teacher1/tea123`, `teacher2/tea456`. The login page (`login.html` and `LOGIN_HTML`) advertises additional role quick-buttons (`students/students123`, `curriculum/curriculum123`, `parent/parent123`, `zahraa/zahraa123`, `kauthar/kauthar123`, `media/media123`) that are **not seeded** — those buttons will fail unless those users are added.
