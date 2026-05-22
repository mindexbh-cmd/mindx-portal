# CHANGE_LOG.md

Chronological history of significant work on the mindex-portal codebase, grouped by week. Maintained by `memory-keeper-agent`. For per-commit detail, run `git log --since=<date>`.

Span: 2026-04-02 (project start) → ongoing.
Total commits as of 2026-05-15: **1308** across 43 days.

| Period | Commits | Highlights |
|---|---:|---|
| Apr 02–06 | ~30 | Project bootstrap — `app.py` + `login.html` + Google Sheets import |
| Apr 07–13 | ~60 | Attendance + violations + group filters; first round of UI fixes |
| Apr 14–20 | ~120 | Database editor + custom tables + label system; taqseet payment logic |
| Apr 21–27 | ~160 | Curriculum library; books_v2 introduction; admin pages |
| Apr 28–May 03 | ~250 | Dashboard redesign; parent hub Phase 1; Excel import unification |
| May 04 | 123 | Points/behaviors/avatars/eggs feature wave; achievements seed import |
| May 05–08 | ~150 | Parent shop (cart-based redemption); rewards; store-link with expenses |
| May 09–11 | ~50 | Books library hardening; PDF viewer custom rendering; parent portal fixes |
| May 12 | 196 | Phase 2 push notifications foundation; parent-shop polish |
| May 13–14 | ~140 | TWA / APK build pipeline; push UI + admin panel; books chunked upload |
| May 15 | 45+ | Infrastructure-as-code: agent team (16 custom + 9 imported), 14 slash commands, 7 hooks, memory keeper, feature-protector, catastrophe-prevention, DB audit |

## Weekly notes

### Week of 2026-04-02 (project genesis)

- **2026-04-02**: First commits — `app.py` skeleton, `login.html` upload, runtime pinned to Python 3.12.
- **2026-04-05**: Auto-import students from Google Sheets feature lands; first real `app.py` work.
- **2026-04-06**: `/api/students/groups` endpoint; violations stats fix (`high` + `total_pts` fields).

### Week of 2026-04-13

- Database editor (`/database`) takes shape with the generic table renderer.
- Label system introduced (`column_labels`, `group_col_labels`, `att_col_labels`).
- First payment / taqseet logic.

### Week of 2026-04-20

- Books_v2 schema lands (`books_v2`, `books_v2_groups`, `books_v2_teachers`, `book_folders`, `book_folder_groups`).
- Curriculum library (`curriculum_files`, `curriculum_assignments`, `curriculum_access_log`).
- Admin permissions UI starts to take shape.

### Week of 2026-04-27 (dashboard redesign)

- 2026-04-29 — Full dashboard redesign safepoint tagged (`dashboard-restyle-safepoint-20260429-160915`, `dashboard-full-redesign-20260429-165722`).
- Major UX work on attendance: anomaly warning, completeness check, summary block, scroll fix, empty-status fix.

### Week of 2026-05-04 (points feature wave — 123 commits in one day)

- `point_events` table introduced; `behaviors` catalog seeded.
- Avatars + level system; achievements scaffolding (later determined unused).
- Egg-hatch gamification mechanic.
- **2026-05-04 19:18 → 19:19**: `student_points_log` bulk-seeded (1865 rows in a 9-second window). Confirmed never referenced afterward — likely a feature-attempt that was replaced by `point_events`.

### Week of 2026-05-11

- 2026-05-12 — **196 commits** in one day. Push notifications Phase 2 foundation lands; parent shop cart redemption (`cart_items`, `redemptions`) polish.
- Parent portal Unicode-bidi-mark tolerance fix (~10% of CPR lookups were failing on invisible characters).
- Parent shop "اطلب الآن" disable when points insufficient; `cart_items` checkout writes `requested` status (no immediate point debit).

### Week of 2026-05-13 (TWA + push + books)

- 2026-05-13 — Books library hardening: chunked uploads land on disk instead of BYTEA; orphan probe recognises BYTEA-only rows; soft-delete of `books_v2.id=4` orphan test row.
- 2026-05-14 — TWA / APK build pipeline: `twa-manifest.json`, `.github/workflows/build-apk.yml`, `assetlinks.json` route, multiple Bubblewrap version pinning iterations (settled on 1.23.0).
- Push notifications: admin send panel on `/points/manage`, admin broadcast log (`notifications` table), smart-timing permission prompt, urgent/vibrate/tag SW handlers.
- VAPID generator rewritten using `cryptography` directly (avoid heavy py-vapid CLI flakiness).

### 2026-05-15 (infrastructure-as-code day)

Recorded in tight detail because this is when the agent team / safety net / memory keeper landed.

| Hash | Title |
|---|---|
| `f7e62c9` | fix(safety): repair `_pg_pool` reference + add `/api/health{,/deep}` |
| `8defcba` | feat(testing): autonomous engineering infrastructure (scripts/) |
| `8ca8a45` | chore(agents): un-ignore `.claude/agents/` |
| `7943f55` `fa3e479` `3d116f6` `7ab7a0e` `fb6decb` `27689db` `3acd9f4` `998a675` `dfbef67` `918ce33` `7efd636` | 11 custom subagents (one per commit) |
| `7810ae5` | docs(agents): CLAUDE.md agent registry |
| `30e33b3` | feat(agents): add database-architect-agent (12th custom) |
| `aba3399` | docs(db): comprehensive read-only audit of production Postgres |
| `ff18e8c` | feat(commands): 10 project slash commands |
| `b17328b` | feat(hooks): 5 lifecycle hooks |
| `c16cbf9` | feat(agents): import 9 professional subagents from VoltAgent |
| `ce970c8` | docs(mcp): MCP server documentation + opt-in template |
| `119348e` | docs(claude): comprehensive Professional setup section in CLAUDE.md |
| `3fd37db` | feat(agents): add memory-keeper-agent (13th custom) |
| `6caa418` | feat(memory): memory-keeper onboarding — initial corpus (9 files, 1252 lines) |
| `caa0279` | feat(commands): /context — memory-keeper handoff generation |
| `f59efb5` | feat(hooks): memory-tracking + HANDOFF-aware session start (6th hook) |
| `bf5c521` | docs: integrate memory-keeper into coordinator pipeline + SOP |
| `b8d5079` | feat(agents): add prompt-engineer-agent + /plan command (14th custom agent + 12th slash command + demo plan) |
| `31499e9` `3712968` `5ecf19d` | feat: unified-login parent direct-nav — guard `/parent` + `/parent/legacy` from authenticated parents; login-page Arabic hint clarifying parents use child's `personal_id` |
| `316d84d` | feat(agents): add feature-protector-agent (15th custom) + /protect (13th slash) + `docs/memory/FEATURE_INVENTORY.md` bootstrap (502 routes, 69 categories, top-20 critical assertions) |
| `43b52d3` | feat(agents): catastrophe-prevention-agent (16th custom) — supreme guardian with 5-category veto + `/check` (14th slash) + `catastrophe_block.py` PreToolUse hook (7th) + `CATASTROPHE_LOG.md` + `REJECTED_CHANGES.md` + 2 demo audits |

#### Feature: feature-protector-agent + /protect + FEATURE_INVENTORY (commit `316d84d`)

Shipped 2026-05-15 late evening.

- `.claude/agents/feature-protector-agent.md` — regression-guard specialist with veto power. Three-phase workflow: pre-change audit → verdict (APPROVE / APPROVE WITH CONDITIONS / REJECT) → post-change verification. Mandatory invocation before any change touching shared code, routes, templates, or APIs.
- `.claude/commands/protect.md` — `/protect <change>` for invoking the agent; `/protect bootstrap` for building/refreshing the inventory.
- `docs/memory/FEATURE_INVENTORY.md` — 899 lines; all 502 `@app.route` entries grouped into 69 categories with line numbers, methods, handlers, auth flags. Top-20 critical features carry explicit regression-worthy assertions ("must hold after any change") — these become contractual invariants.
- `CLAUDE.md` — agent table now lists 15 custom agents (memory-keeper + prompt-engineer surface in the table for the first time); slash-command table grows to 13 (`/plan`, `/context`, `/protect` added).
- Decision rationale: see ADR-015 (split DB-safety vs feature-safety into two distinct guardians, each with veto).

#### Feature: catastrophe-prevention-agent + /check + hook (commit `43b52d3`)

Shipped 2026-05-15 late evening. 16th custom agent; sits ABOVE the role-specific guardians (data-protector, feature-protector) as a supreme guardian with REJECT-class veto.

- `.claude/agents/catastrophe-prevention-agent.md` — disaster veto across 5 categories: data loss, breaking changes, security, performance, UX. Default answer is NO unless the change is provably safe. Only the human owner overrides REJECT.
- `.claude/commands/check.md` — `/check <change>` slash command (14th).
- `.claude/hook_scripts/catastrophe_block.py` — PreToolUse Bash hook (7th). Pattern-blocks `DROP TABLE`, `TRUNCATE`, `DELETE`-without-`WHERE`, `ALTER COLUMN` type/rename, `rm -rf` on sensitive paths, `git push --force` (not `--force-with-lease`), `git reset --hard origin/main`, `git filter-*`, `dropdb`, `pg_restore --clean`. Bypass: inline `override:catastrophe:<reason>` tag. Initial regex `--force\b` mis-matched `--force-with-lease`; corrected to `--force(?:\s|$)`.
- `docs/memory/CATASTROPHE_LOG.md` — append-only verdict log (timestamp / slug / verdict / categories / audit file).
- `docs/memory/REJECTED_CHANGES.md` — full risk breakdown of every REJECT verdict.
- Two demo audits under `docs/audits/`: `catastrophe-check-delete-books-v2-20260515-204654.md` (REJECT — Cat 1 + 2, 346 callsites), `catastrophe-check-add-footer-slogan-20260515-204654.md` (APPROVE — purely additive).
- `CLAUDE.md` — SOP gained step 0a ("`/check` first for risky changes"); custom-agent count 16; slash count 14; hook count 7 (with `post_commit_memory` also surfaced in the table).
- `mindex-coordinator-agent.md` — catastrophe-prevention now runs FIRST in the pipeline, feature-protector SECOND. Roster table expanded to all 15 specialists.
- Decision rationale: see ADR-016 (supreme guardian above the role-specific guardians).

#### Feature: unified-login parent direct-nav (commits `31499e9` + `3712968` + `5ecf19d`)

Shipped 2026-05-15 evening. MEDIUM-risk deploy, zero incidents post-deploy.

- `refactor(parent-routes)` `31499e9` — `/parent` (`app.py` ~28800) and `/parent/legacy` (`app.py` ~28825) now check `session["user"]` first. Logged-in `role=student` → 302 `/portal/parent-hub`. Logged-in `role=parent` → 302 `/portal/parent`. Anonymous visitors unchanged — public PID prompt preserved so legacy WhatsApp deep-links keep working.
- `feat(login)` `3712968` — `LOGIN_HTML` (`app.py` ~9700) gained Arabic hint under submit button: "أولياء الأمور: استخدم الرقم الشخصي للطالب اسم مستخدم" (entity-encoded per ADR-002).
- `docs(memory,plans)` `5ecf19d` — refreshed `HANDOFF_COMPACT.md`; added plan `docs/plans/unified-login-parent-direct-nav-20260515-222200.md`.
- Safety tag: `safety/pre-unified-login-parent-direct-nav-20260515-225736` (pushed to origin).
- Prod verified: `/api/health` green at 1778875191; smoke + full 8/8 e2e green; anon `/parent` + `/parent/legacy` still 200.
- Decision rationale: see ADR-014 in `DECISIONS_LOG.md` (Interpretation B chosen over A).

### 2026-05-17

| Hash | Title |
|---|---|
| pending hash | feat(curriculum-plan): private "الخطة الزمنية للمناهج" feature for Fatima — 2 new tables (curriculum_plans + curriculum_lessons), 10 endpoints, inline-edit UI, smart status colors, Bahrain-weekend-aware auto-calc, Excel export, sidebar link gated to admin+Fatima only |

#### Feat: Curriculum Time Plan for Fatima (commit pending)

Shipped 2026-05-17. New private feature surfaced at `/curriculum-plan`.
Access gate: admin OR username==930909151 OR `user_can_see_button("curriculum_plan.access")`. Other managers (Ahmed, Raed) cannot see the sidebar link, cannot reach the page (403), cannot list or mutate plans/lessons via the API (403).

- **Data model**: two new tables created by migration `curriculum_plans_v1`:
  - `curriculum_plans(id, name, created_by, created_at, updated_at, is_deleted)`
  - `curriculum_lessons(id, plan_id, lesson_name, sessions_count, start_date, end_date, sort_order, is_completed, is_deleted, created_at, updated_at)`
  Pure additive — no DDL on existing tables. Soft-delete only.
- **Endpoints** (all gated by `_curriculum_plan_can_use`):
  - `GET  /curriculum-plan` → HTML page
  - `GET  /api/curriculum-plans` → list plans + lessons
  - `POST /api/curriculum-plans` → create plan
  - `PUT  /api/curriculum-plans/<id>` → rename
  - `DELETE /api/curriculum-plans/<id>` → soft-delete
  - `POST /api/curriculum-plans/<id>/copy` → duplicate with new name
  - `POST /api/curriculum-plans/<id>/lessons` → add lesson
  - `PUT  /api/curriculum-lessons/<id>` → patch lesson
  - `DELETE /api/curriculum-lessons/<id>` → soft-delete lesson
  - `GET  /api/curriculum-plans/export-excel` → XLSX download (openpyxl)
- **Sidebar link** added inside التعليم والتقييم section, tagged `data-button-key="sidebar.curriculum_plan"` (default_roles=admin). Fatima's `is_visible=1` override unlocks it via the new `VISIBLE_BUTTONS` list in `scripts/create_fatima_account.py`.
- **UI**: mindex palette, inline cell editing (click-to-edit, blur to save), auto-calc end_date when sessions_count or start_date change (Bahrain weekend = Fri+Sat skipped), smart status colors (green/yellow/blue/red) computed from today's date, copy plan with name prompt, soft-delete with confirm. Mobile-responsive (tables overflow horizontally on small screens).
- **Excel export**: one sheet per plan, RTL layout, mindex-purple header, status column auto-derived per row.

Verification (local):
- Fatima login → /curriculum-plan returns 200; admin → 200; teacher1 → 403.
- POST /api/curriculum-plans creates plan; GET lists it; POST /lessons adds a lesson; PUT /lessons updates; DELETE soft-deletes; /export-excel returns valid XLSX (5KB, `Microsoft Excel 2007+`).
- /api/me/permissions returns `is_visible=1` rows for sidebar.curriculum_plan + curriculum_plan.access for Fatima.

See ADR-029 in DECISIONS_LOG.md.

### 2026-05-16

| Hash | Title |
|---|---|
| `6a94497` | fix(parent-portal): display student name + kill PID-prompt flash on `/parent/legacy` |
| `3ad90c1` | refactor(parent-portal): consolidate onto منصة V1; retire بوابة V2 entry points |
| `d7cc70c` | fix(parent-portal): restore full feature hub at `/portal/parent` (6 cards) |
| `3b940c4` | fix(parent-portal): restore the formal student-card layout at `/portal/parent` |
| `3465c6f` | fix(parent-portal): repair 500 on `/api/portal/student/attendance` (Postgres) |
| `e51642b` | test(personas): commit durable parent-portal verification harnesses |
| `f6aee45` | fix(parent-portal): remove logout misclick trap from V1 + sub-pages |
| `27ca5ba` | test(personas): commit hostile-mode logout-hunt probe |
| `0fc833f` | fix(books): friendly Arabic page when a curriculum file is missing (UX) |
| _data action_ | account(perms): create limited-admin manager فاطمة إبراهيم (930909151) restricted to 4 curriculum features (no code change; SQL only) |
| pending hash  | feat(perms): full lockdown for Fatima — 3-feature whitelist + new button_registry hooks + route gates on /admin/evaluations and /admin/events |
| pending hash  | feat(perms): in-page lockdown — hide evaluations tab on /admin/teacher-deliveries + alerts banner / آخر النشاطات / المجموعات النشطة / amber+blue stat cards / التقارير quick card on /dashboard; auto-inject /mx-helpers.js into 4 more admin pages |
| pending hash  | feat(perms): sidebar-section-level lockdown for Fatima + grant her /admin/books (curriculum) full access |

#### Data action: limited-admin account created — Fatima Ibrahim (930909151)

Shipped 2026-05-16. No code change; pure SQL through `scripts/create_fatima_account.py` against both local SQLite (id 10) and prod Postgres (id 3197). Idempotent — re-running re-asserts state without duplicating rows.

- **User row**: `role='manager'`, `department='شؤون المناهج والامتحانات'`, `landing_page=NULL` (login() only honours keyword landings; falls through to `/dashboard`), `is_active=1`, `must_change_pw=0`, password = sha256(`'930909151'`) = `56f7f3b4d2756b5e5fb3c948a06041bc3b8994ec4c1a8f5fa430b0b785701299`.
- **14 explicit `user_permissions(is_visible=0)` overrides** on manager-default buttons that fall outside the four-feature whitelist: `dashboard.{payment_tracking, lessons_summary, lesson_durations, search_student, send_messages, points_board, parent_receipts}`, `attendance.{take_attendance, export_excel}`, `database.export`, `groups.add_group`, `sidebar.{attendance, groups, parent_receipts}`.
- **`/api/me/permissions` returns 30 hidden buttons** for her (14 explicit + 16 implicit from `default_roles` not including `manager`).
- **NOT added to any code-level allowlist** (`_STUDENT_EDIT_ALLOW`, `_EVENTS_VIOLATIONS_FULL_ACCESS_USERNAMES`, `_BOOKS_V2_FULL_ACCESS_USERNAMES`, `_EXPENSES_ACCESS_USERNAMES`). Ahmed Ibrahim + Raed are in three of those; Fatima is in none, per the explicit DENY list.
- **Verification on prod (`https://mindx-portal-1.onrender.com`)**:
  - Login `POST /login` with `930909151` / `930909151` → 302 `/dashboard` ✓
  - Allowed: `/admin/teacher-deliveries`, `/admin/lessons`, `/admin/evaluations`, `/admin/parent-messages` → all 200 ✓
  - Denied: `/admin/permissions`, `/admin/table-audit`, `/admin/receipts`, `/database`, `/settings`, `/admin/violations`, `/expenses` → all 403 ✓
  - Denied (graceful redirect): `/admin/books`, `/points/manage` → 302 (route helpers `_books_v2_can_admin` / `_can_manage_points` redirect) ✓
- **Decision rationale**: see ADR-025 (`DECISIONS_LOG.md`). Operator's premise that Ahmed/Raed are "technically limited" was incorrect — they are pure `role='manager'` with one additive override on Ahmed. Operator chose Path C (explicit whitelist via `user_permissions`) over Path B (literal-mirror, full manager surface).
- **Known imperfection**: dashboard sidebar items without `data-button-key` (search-student modal button, attendance link, groups link, lessons-summary modal, payments modal, points-board link) remain visible to her exactly as they are for Ahmed/Raed. Hiding them would require adding `data-button-key` attributes to ~7 inline-HOME_HTML elements + matching `button_registry` rows. Deferred per principle "mirror Ahmed/Raed".

#### Fix: friendly missing-file page for parents (commit `0fc833f`)

Shipped 2026-05-16 via `safe_deploy --feature missing-file-ux`. Safety tag
`safety/pre-missing-file-ux-20260516-105201`. Health-poll green, smoke e2e
passed. Production verified manually: book 53 (`/api/books/53/view`,
authenticated as `admin_test`) — `Accept: text/html` returns HTTP 410 + a
1936-byte Mindex-styled Arabic page; `Accept: application/json` returns
HTTP 410 + the original `{book_id, error, missing_file:true, ok:false}`
envelope, so the APK and any other JSON consumer are unaffected.

Routes `/api/books/<bid>/view+download` and `/parent/book/<bid>/view+download`
now share `_books_v2_missing_file_response(bid, route_tag=...)`, which
also emits one `[mindex-books] missing_file bid=<id> route=<r>` stderr
line per hit so recurring orphan rows surface alongside the boot-probe
diagnostics in the Render log.

Known cosmetic flaw (non-blocking): `Content-Type` header reports
`text/html; charset=utf-8; charset=utf-8` because Flask auto-appends a
charset when one is set via `mimetype=`. Browsers parse the duplicate
away; follow-up commit can switch to `content_type=` or drop the explicit
charset on the `Response(...)` call.

#### Data action: orphan cleanup — book 53 soft-deleted (no commit)

Shipped 2026-05-16 ~10:54 UTC via live `POST /api/books/cleanup-orphans` (admin_test session). No code change — purely a data-state action against prod via the existing admin endpoint. Triggered by the post-deploy report "ALL books show the missing_file page", which `/api/books/storage-check` resolved as "exactly one active row in `books_v2`, and it's the orphan from 2026-05-15".

- **Action**: `POST /api/books/cleanup-orphans` → `{count:1, deleted:[{id:53, title:"1", file_path:"/opt/render/project/src/data/books_v2/53_1.pdf"}], storage_dir:"/var/data/books_v2"}`. Audit log entry written (`books_v2.cleanup_orphans` event).
- **Effect**: book 53 has `is_deleted=1` (reversible via `UPDATE books_v2 SET is_deleted=0 WHERE id=53` if a path is ever restored). Storage-check after: `rows: 0`. Admin list after: `count: 0`. Parent curriculum page renders empty-state copy (`لا توجد …`) instead of the friendly missing-file page; direct fetch of `/api/books/53/view` returns 404 `غير موجود` (row-not-found branch) instead of the 410 missing-file branch.
- **Follow-up by operator**: re-upload the PDF via `/admin/books` — current upload code writes into `/var/data/books_v2/`, so the new row will be stable across deploys.
- **Decision detail**: ADR-021 explains why cleanup-orphans was chosen over rollback of `0fc833f`.

#### Feature: per-teacher evaluation coverage drill-down (commits `7c63c37` + `9b00b85` + `f65f492`)

Shipped 2026-05-16 ~12:43 UTC via `safe_deploy --feature teacher-eval-coverage`. Safety tag `safety/pre-teacher-eval-coverage-20260516-124334`. Three atomic commits, single-file changes to `app.py` plus the plan doc.

- `7c63c37` — backend: two new admin-gated read-only endpoints under `/api/monthly-evaluations/`. `/teachers/coverage` (summary, one row per active teacher with submitted/total/percentage) and `/teachers/<int:tid>/coverage` (per-student lists). Universe = union of active students across every group `student_groups.teacher_name` matches this teacher; submitted = `evaluations` rows for `(teacher_id, evaluation_month)` with `is_deleted=0`. Query plan keeps N+1 out: summary resolves student sets per unique group (bounded by group count, not teacher count) + one `evaluations` query for all submissions in the month.
- `9b00b85` — frontend: new expandable list section above the existing teacher dropdown on `/admin/teacher-deliveries` (NOT `/admin/evaluations` — different URL despite the matching title). Per-row progress bar + percentage + smart status emoji (`✨` 100, `✅` 80+, `🟡` 50+, `⚠️` >0, `🔴` 0). Clicking a row also selects the same teacher in the dropdown so both flows reinforce each other.
- `f65f492` — frontend: `📲 تذكير المعلمة عبر واتساب` button below the pending list. Builds a prefilled Arabic body (greeting → reason → pending names capped at 20 → sign-off) and opens `wa.me/?text=` in a new tab. No phone targeting because `users` has no `phone` column today (see ADR-022 follow-up).

Production verification (admin_test session):
- Summary endpoint returns 5 teachers, including real prod data — `أ. زهراء نوح` 67/80 = 84% and `أ. كوثر شعبان` 75/86 = 87%.
- Detail endpoint returns correct `{teacher, stats, submitted[], pending[]}` shape.
- `/admin/teacher-deliveries` HTML contains all 8 markup markers (`tm-cov-card`, `tm-cov-list`, `tmCovLoadSummary`, `تغطية تقييمات الشهر`, `teacher_eval_coverage_v1`, `📲 تذكير المعلمة`, `wa.me/?text=`, `/api/monthly-evaluations/teachers/coverage`).

Process note (one for BUGS_LOG eventually): I initially verified against `/admin/evaluations` (which serves a different template, `ADMIN_EVALUATIONS_HTML`) and was about to report markup MISSING — the Explore subagent's report mentioned the title was in `ADMIN_TEACHER_DELIVERIES_HTML` but didn't flag that the template's URL is `/admin/teacher-deliveries`. Lesson: when an agent reports a template, ALSO ask for the route that serves it. Confirmed once I grepped `@app.route` for the constant name.

Decision detail: ADR-022 covers the schema-deferred phone field and pending-universe definition.

#### Data action: orphan student backfill — 30 role=student accounts created (no commit)

Shipped 2026-05-16 ~13:33 UTC via direct prod SQL after extensive read-only diagnosis. Triggered by operator reporting "student 200910132 cannot log in even with PID as password". Root cause: a `students` row existed (id 4790, علي محمد أحمد) but no matching `users` row — the recent enrollment cohort (student.id 4729–5045, ~20% of active students) was never given login accounts.

- **Action 1 — backup**: `backups/users_pre-orphan-backfill-20260516-103010.json` (157 rows × all columns; `scripts/db_backup.py` failed because `pg_dump` is not on PATH on this Windows box; focused-JSON snapshot used as substitute since backfill only touches `users`).
- **Action 2 — bulk INSERT (transaction-wrapped)**: 30 new `users` rows (ids 3159–3188), each matching Tasneem's shape: `role='student'`, `username=personal_id`, `password=sha256(personal_id)`, `linked_student_id=<sid>`, `must_change_pw=1`, `is_active=1`, `notify_pref='instant'`. Ledger of new ids saved to `inserted_ids.txt`. Filter: active students (`registration_term2_2026 = تم التسجيل`) with non-empty `personal_id`. 5 active students remain unfixable (empty `personal_id` — needs staff data entry).
- **Action 3 — disable force-change-password**: `UPDATE users SET must_change_pw=0 WHERE id IN (3159..3188)`. 29 rows changed (one — id 3168, the original problem case — had already self-onboarded via the change-password UI between the INSERT and the UPDATE, demonstrating the flow worked end-to-end). Post-state: all 30 at `mcp=0`.

Trade-off accepted: PID is now a permanent (non-rotated) password for these 30 accounts. Anyone who knows a child's PID can log into that parent's account until the parent voluntarily changes it. Operator chose this over the forced-change UX because PID-as-password matches how the existing 135 parents were originally onboarded.

Process discoveries from this incident (worth recording in BUGS_LOG):
- `students.personal_id` has 5 NULL/empty values on prod; these students have no way to log in until staff fills the field.
- No admin UI exists for creating `role=student` PID-mode accounts. The existing `POST /api/admin/parents` only does the phone-as-username V1-multi-child shape. Adding a PID-mode counterpart is a small future commit.
- The visually-reversed-Arabic literal `'ليجستلا مت'` (vs the correct `'تم التسجيل'`) is a real footgun when copy-pasting SQL from a terminal that renders RTL — caught here because the pre-check returned 0 instead of 30.
- A user's session changing `must_change_pw` from 1 to 0 ALSO leaves the `password` column untouched if they entered the same value (the same sha256 hash). Defensive pre-checks should not require `mcp=1` strictly — relax to `role=student` and let the UPDATE itself be idempotent.

Decision detail: ADR-024 covers backfill-vs-rollback choice + the security trade-off (PID as permanent password).

#### Feature: per-teacher coverage enhancements — month picker + group breakdown (commits `ca993c1` + `c9f5fd4` + `edda6dd` + `999665e`)

Shipped 2026-05-16 ~14:24 UTC via `safe_deploy --feature teacher-cov-enhancements`. Safety tag `safety/pre-teacher-cov-enhancements-20260516-142400`. Four atomic commits, single-file changes to `app.py` + plan doc.

- `ca993c1` — backend: new `GET /api/monthly-evaluations/months` (DISTINCT `evaluation_month` from `evaluations`, current month pinned at top). Reshape per-teacher detail endpoint: flat `submitted[]`/`pending[]` replaced by `groups[]` each with own `{name, stats, submitted, pending}` + `overall_stats` block. Empty groups skipped.
- `c9f5fd4` — frontend: month `<select>` next to the refresh button. `tmCovCurrentMonth` state threaded through both fetch URLs. On change → clear cache, close all rows, refetch.
- `edda6dd` — frontend: `tmCovRenderDetail` rewrite. Each teacher row's body now contains a stack of group sub-rows with their own progress bar + emoji + click-to-expand. First group expanded by default. Distinct `.tm-cov-grp-head` class so the outer-row handler doesn't double-fire.
- `999665e` — frontend: group-aware reminder body. `tmCovBuildReminderText` walks `d.groups[]`, emits `— <group_name>:` headers with pending names beneath, 20-name TOTAL cap across all groups, fallback to legacy flat shape if a stale cached response is encountered.

Production verification (admin_test session): `/months` returns مايو 2026 + أبريل 2026 (current pinned at top). `/teachers/641/coverage?month=2026-05` returns **10 groups** for أ. زهراء نوح with `overall_stats={total:80, submitted:67, pending:13, percentage:84}`, no legacy top-level keys present. `/admin/teacher-deliveries` HTML contains all 8 new markup markers. The 502 warmup flap on the first verification curl-burst is the same Render free-tier behaviour seen on the prior two deploys; resolved within ~60s.

Decision detail: ADR-025 covers the schema-frozen "first-group-wins" dedup rule and the empty-group skip.

#### Fix: parent-portal student name + PID-prompt flash (commit `6a94497`)

Shipped 2026-05-16. Two regressions on the legacy PID-hub surface:

- Student card in `PORTAL_PARENT_PID_HUB_HTML` was missing the student name — added a `<div id="card-name">` row with the "اسم الطالب" label.
- `/parent/legacy?pid=<X>` flashed the anonymous CPR-prompt UI for a few hundred ms before the deep-link auto-lookup populated. Added an inline `<script>` in `<head>` of `PARENT_HTML` that adds `.has-deeplink-pid` to `<body>` when `?pid=` is present; matching CSS hides `.pp-hero` + `#pp-lookup-card` so the prompt is suppressed instantly. Documented in BUGS_LOG (see entry below for the testing-discipline lesson).
- Templates remain in source (intentionally — see commit `3ad90c1` safety-net note).

#### Refactor: consolidate parent UX onto منصة V1; retire بوابة V2 entry points (commit `3ad90c1`)

Shipped 2026-05-16. Operator clarified V1 is the only parent surface in use ("نستخدم فقط منصة ولي الأمر"); V2 hub + 6 sub-pages + public `/parent` PID flow are retired as entry points. Prod SHA verified: `3ad90c147d05`; safety tag `safety/pre-consolidate-to-v1-platform-20260516-002351`.

- `_pts_parent_children_ids` now accepts `role=student` (returns `[linked_student_id]`); V1 renders correctly for the parent-with-child-PID-as-username pattern.
- `/login` post-auth dispatch routes `role=student` → `/portal/parent` (was `/portal/parent-hub`); legacy `landing_page` values `parent_hub` / `student_portal` also rerouted to V1.
- `/portal/parent` + `/api/portal/parent/me` accept both `role=parent` (multi-child via `linked_parent_for` JSON) and `role=student` (single child via `linked_student_id`).
- All 7 `/portal/parent-hub*` routes return 302 → `/portal/parent`. URL compatibility preserved for saved bookmarks.
- `/parent` and `/parent/legacy` now redirect anonymous visitors to `/login` (no more public PID prompt). Logged-in users → `/portal/parent`.
- Removed the "أولياء الأمور: استخدم الرقم الشخصي" hint from `LOGIN_HTML` (shipped 2026-05-15 in `3712968`) — was V2-flow-specific and now misleading.
- Templates intentionally kept in source for one release cycle (revert safety net): `PORTAL_PARENT_HUB_HTML`, `PORTAL_PARENT_PID_HUB_HTML`, `PORTAL_PARENT_ATTENDANCE_HTML`, `PORTAL_PARENT_PAYMENTS_HTML`, `PORTAL_PARENT_MESSAGES_HTML`, `PORTAL_PARENT_EVALUATIONS_HTML`, `PARENT_HTML`.
- Prod verification: SHA `3ad90c147d05` matches; `/api/health` green; anon `/parent` + `/parent/legacy` → `/login`; anon `/portal/parent-hub` → `/` (login_required); `student_test` login → `/portal/parent`; `/api/portal/parent/me` returns `children=1` (Test Student); full 8/8 e2e green against prod.
- Decision rationale: see ADR-017 (`DECISIONS_LOG.md`) — supersedes the V2-direction implicit in ADR-014.

#### Fix: restore full feature hub at `/portal/parent` (commit `d7cc70c`)

Shipped 2026-05-16. **Regression remediation for the V1-consolidation pass `3ad90c1`**, which over-consolidated and left the parent surface "empty" — every feature button disappeared. Operator quote: "كل البيانات التي كانت تظهر سابقا في المنصة عند دخول ولي الامر بالرقم الشخصي للطالب اصبحت الان غير ظاهرة". Prod SHA verified: `d7cc70c3f2d3`; safety tag `safety/pre-restore-parent-hub-features-20260516-004528`.

Regression chain: `3ad90c1` routed `role=student` → `/portal/parent` → `PORTAL_PARENT_HTML` (V1 points-only template, not the 6-card hub) AND collapsed the 6 V2 sub-page handlers into 302 redirects to `/portal/parent`. Both changes together stripped every feature button from the parent-facing experience.

- `/portal/parent` for `role=student` now serves `PORTAL_PARENT_HUB_HTML` (the 6-card hub: payments / attendance / points / messages / evaluations / curriculum). `role=parent` (V1 multi-child) still serves `PORTAL_PARENT_HTML` — that surface unchanged.
- All 6 `/portal/parent-hub/*` sub-page handlers restored to serving their full content (`PORTAL_PARENT_PAYMENTS_HTML`, `PORTAL_PARENT_ATTENDANCE_HTML`, `PORTAL_STUDENT_HTML` for the points/store view, `PORTAL_PARENT_MESSAGES_HTML`, `PORTAL_PARENT_EVALUATIONS_HTML`, `PORTAL_BOOKS_HTML`). Bare `/portal/parent-hub` still 302 → `/portal/parent` (URL consolidation preserved).
- `/parent` and `/parent/legacy` stay as redirects (anonymous → `/login`, logged-in → `/portal/parent`). Operator confirmed they don't want the public PID prompt back.
- متجر (rewards store) lives inside the points sub-page (`PORTAL_STUDENT_HTML`) — verified visible by `real-user-tester-agent`.
- Pre-deploy verification (lesson applied): `real-user-tester-agent` walked 4 personas locally — student_test (hub renders 6 cards, every sub-page 200, zero console errors, store visible — PASS), parent_test (V1 multi-child UI unchanged — PASS), admin_test / teacher_test (no regression — PASS). Verdict: GREEN.
- Re-runnable harness: `scripts/personas/parent_hub_verify.py`; 13 screenshots under `scripts/screenshots/20260516-0042..0043*`.
- Prod verification post-deploy: SHA matches, `/api/health` green, all 6 sub-pages return 200 for student_test session, bare `/portal/parent-hub` → 302 `/portal/parent`.
- Decision rationale: see ADR-018 (`DECISIONS_LOG.md`) — role-dispatched template selection at `/portal/parent`.
- Process lesson logged separately in `BUGS_LOG.md` (tested-with-curl-only blindspot).

#### Fix: restore the formal student-card layout at `/portal/parent` (commit `3b940c4`)

Shipped 2026-05-16. **Second regression remediation in the same chain** — `d7cc70c` had served the 6-floating-card V2 hub (`PORTAL_PARENT_HUB_HTML`) at `/portal/parent` for `role=student`, but operator's "واجهة جميلة" was specifically the formal STUDENT CARD layout in `PORTAL_PARENT_PID_HUB_HTML` (header "STUDENT CARD · بطاقة طالب", year, ID row, avatar placeholder box, info grid: اسم الطالب / المجموعة / المستوى / الصف / المعلمة / الحالة, hours-summary bar, 5 horizontal action tabs: الحضور / المدفوعات / المناهج / التقييمات / النقاط). Operator quote: "خربت منصة ولي الامر التي كانت تعرض معلومات الطلبة بشكل منسخق وكل شي ذهب للاسف عملي ضاع. كان كل طالب تظهر له واجهة جميلة مكتوب فيها معلوماته الاساسية من اسمه ورقم مجموته ومكان لصورته والازرار بشكل منظم وكل زر كان يعمل ليس مثل الان للاسف الشديد انفكت الارتباطات وكل شي". Prod SHA verified: `3465c6f3eeda` (next commit in same deploy chain); safety tag `safety/pre-restore-formal-student-card-20260516-010728`.

- `/portal/parent` for `role=student` now serves `PORTAL_PARENT_PID_HUB_HTML` (formal student card) — was `PORTAL_PARENT_HUB_HTML` (6 floating cards) from the prior `d7cc70c` fix.
- Session PID injected into the template via `__SESSION_PID__` placeholder, resolved from `session.user.linked_student_id` → `students.personal_id`. JS auto-runs `phLookup()` with the injected PID, no manual entry required.
- Pre-paint inline `<script>` in `<head>` reads the injected PID, adds `.has-session-pid` class to `<html>`, exposes `window._SESSION_PID`. CSS rule `html.has-session-pid #lookup-card{display:none !important}` suppresses the PID lookup form before first paint — no flash.
- `phBoot()` priority: session PID → URL `?pid=` → focus input.
- Action tabs build hrefs via `DIRECT_HREF` map → `/portal/parent-hub/{attendance,payments,curriculum,evaluations,points}` directly when `window._SESSION_PID` is set. Anonymous fallback to `/parent/legacy?pid=<X>#anchor` preserved.
- `role=parent` (V1 multi-child) still serves `PORTAL_PARENT_HTML` unchanged.
- Pre-deploy verification by `real-user-tester-agent`: 4 personas walked locally, formal card visible — GREEN before deploy.
- Decision rationale: see ADR-019 (`DECISIONS_LOG.md`) — supersedes the `role=student` template choice from ADR-018.

#### Fix: repair 500 on `/api/portal/student/attendance` (commit `3465c6f`)

Shipped 2026-05-16. Operator complaint after `3b940c4` landed: "الازرار فيها اذا نضغطها يخرجنا من المنصة الى صفحة تسجيل الدخول مرة اخرى. لماذا هكذا عملك سيئ لماذا للم تختبر ان كل شي يعمل على ما يرام؟؟؟". Operator's mental model: tab opens broken/empty page → "I'm logged out". Real root cause was NOT routing/logout — all 6 sub-page routes returned 200 for `role=student`. The actual bug: `/api/portal/student/attendance` threw 500 on Postgres prod with `column "message" does not exist`. The `attendance.message` + `attendance.message_status` columns existed in `init_db()` CREATE TABLE since day-1, but the long-running Postgres prod pre-dated their addition and the else-branch migration list never included them. Prod SHA verified: `3465c6f3eeda`; safety tag `safety/pre-fix-attendance-500-postgres-20260516-014052`.

Two-layer fix:
- New migration `attendance_msg_cols_v1` (else-branch): `ALTER TABLE attendance ADD COLUMN message TEXT DEFAULT ''` (same for `message_status`). Pattern mirrors `center_mode_v1` — idempotent across SQLite and Postgres.
- Defensive SELECT in `api_portal_student_attendance`: probes `att_live` via `PRAGMA table_info` (SQLite) → falls back to `information_schema.columns` (Postgres). If `message` is missing, substitutes `'' AS message`. Belt-and-suspenders against future schema drift.

- Pre-deploy verification by `real-user-tester-agent`: 5 sub-page tabs all serve content + 4 stat cells visible on attendance + 4 reward tiles + متجر visible on points sub-page — GREEN before deploy.
- Prod verification post-deploy: SHA matches, all 6 sub-page routes return 200, `/api/portal/student/attendance` now returns `200 {ok:true, summary:{...}, rows:[]}` (was 500), `has-session-pid` CSS rule present in served HTML, injected PID literal `TEST-STUDENT-0001` present, no visible PID lookup card.
- Process lesson: route-200 ≠ page-works. The route can serve 200 but the inline JS fetch can 5xx — broken empty page is indistinguishable from a logout to a non-technical user. Logged separately in `BUGS_LOG.md` (route-200 blindspot).

#### Test: commit durable parent-portal verification harnesses (commit `e51642b`)

Shipped 2026-05-16. Durable persona harnesses committed so future changes to parent template dispatch or attendance API can be re-verified with a single command.

- `scripts/personas/parent_portal_walk.py` — formal student-card layout walk for 4 personas (student_test / parent_test / admin_test / teacher_test).
- `scripts/personas/verify_parent_hub_tabs.py` — 5-tab navigation walk + API health check (verifies all 6 sub-page routes return 200 AND the underlying XHR endpoints return non-5xx).
- `.gitignore` additions: keep scratch artifacts (`report.json`, `debug*.py`, `__pycache__`) local; only committed harnesses ship.

#### Fix: remove logout misclick trap from V1 + sub-pages (commit `f6aee45`)

Shipped 2026-05-16. **Third escalation in the same parent-portal session** — prior commits `3b940c4` + `3465c6f` only treated the formal student-card surface; the V1 multi-child template at `app.py:77869` still shipped a bare purple `<a href="/logout">خروج</a>` pill in the topbar, identical-styled to other navigation, with zero confirm guard. Operator quote (third escalation): "لازالت الازرار في منصة ولي الامر اذا نضغط عليها تخرجنا وترجعنا لصفحة تسجيل الدخول من جديد. اين الايجنتس الذي يختبر بشكل واقعي؟؟؟". Prod SHA verified: `27ca5bac980e`; safety tag `safety/pre-fix-logout-misclick-v1-20260516-022143`.

Diagnostic gap that allowed two escalations: `real-user-tester-agent` walked `student_test` persona twice (formal student-card template at `/portal/parent` for `role=student`) and returned GREEN — that surface already had the red+confirm pattern from prior commits. The third walk, invoked in hostile mode with `parent_test` as a separate persona, finally exercised the V1 template path (`role=parent` → `PORTAL_PARENT_HTML`, same URL `/portal/parent`, **different template**) and found the bare logout link. URL `/portal/parent` is shared between two role-dispatched templates; "test all buttons on URL X" required ALL persona roles whose login lands on X, not just one.

Fix layered across 4 surfaces:
1. **Sub-pages** (`PORTAL_PARENT_ATTENDANCE/PAYMENTS/MESSAGES/EVALUATIONS_HTML` + `PORTAL_STUDENT_HTML` + `PORTAL_BOOKS_HTML`): removed every `<a class="logout" href="/logout">خروج</a>` link adjacent to "← العودة للبوابة" with identical purple styling. Sub-pages now carry ONLY the back link.
2. **PORTAL_PARENT_HTML (V1, `role=parent`)** at `app.py:77869`: replaced bare purple logout link in topbar with red + confirm: `background:linear-gradient(135deg,#c62828,#e53935)` + `🔒 تسجيل الخروج` + `onclick="return confirm('هل تريد تسجيل الخروج من منصة ولي الأمر؟')"`.
3. **PORTAL_PARENT_PID_HUB_HTML (`role=student`)**: already received the red+confirm pattern in earlier commits — kept unchanged.
4. **PORTAL_PARENT_HUB_HTML (dead code)**: applied the same red+confirm pattern defensively so a future route rewire can't reintroduce the trap.

PORTAL_PARENT_HTML for `role=teacher` at `/teacher/hub` keeps its bare "خروج" link — that page has no adjacent "back" link so the misclick hazard does not apply. ADR-020 codifies the red+confirm pattern across all parent surfaces.

- Prod verification: SHA `27ca5bac980e` matches; parent_test on V1 has red+confirm + no bare logout link; student_test on student-card has same; all 6 sub-pages return 0 occurrences of `href="/logout"`.
- Decision rationale: see ADR-020 (`DECISIONS_LOG.md`).
- Process lessons logged separately in `BUGS_LOG.md`: (a) same-bug-different-template / persona-x-template coverage, (b) misclick-trap canonical pattern.

#### Test: commit hostile-mode logout-hunt probe (commit `27ca5ba`)

Shipped 2026-05-16. Re-runnable Playwright walk aggressively enumerating every clickable element on `/portal/parent` (both role variants) and all 6 sub-pages; flags any path that reaches `/login` or `/logout` without user confirmation. Born from the third-escalation regression.

- `scripts/personas/hostile_parent_portal_logout_hunt.py` — hostile-mode probe that walks BOTH `student_test` AND `parent_test` sessions on the same URL set. Handles its own session preservation by treating `/logout` and `/api/logout` as `SESSION_KILLERS` that must not be probed via the shared cookie context (they would invalidate the session and break subsequent assertions in the same run).

### 2026-05-21

| Hash | Title |
|---|---|
| `bb69bfe` | feat(portal): G13.1 bypass forced password-change for non-admin users |
| `3a12493` | feat(portal): G13.2 hide level row in student info card |
| `4c36ab4` | feat(portal): G13.3 remove weekly summary section from student portal |
| `a8c1071` | feat(portal): G13.4 remove activity feed from both parent surfaces |
| `dd3584f` | feat(portal): G13.5 remove 8-week chart + Chart.js from parent surfaces |
| `714c2fd` | test(portal): G13.7 hermetic test for all five UX cleanups |
| `1aca22c` | test(portal): G13.8 prod verification probe |

#### Feature wave: G13 parent/student portal UX cleanup (commits `bb69bfe` → `1aca22c`)

Shipped 2026-05-21. Five operator-driven simplifications + two test rigs. All deployed; full 8/8 e2e against prod green after deploy. Safety tags: `safety/pre-g13-cleanups-2026-05-21` at `e52f3df` (pre-G13 baseline) and `safety/pre-g13-ux-cleanups-20260521-194210` at `714c2fd` (created by safe_deploy).

What's now true that wasn't before:

- **Forced password-change retired for non-admin** (G13.1, `bb69bfe`). All 9 redirect guards that pushed `must_change_pw=1` users to `/portal/change-password` were removed. Both `/portal/change-password` and `POST /api/portal/change-password` are now admin-only gated. The 4 user INSERT/UPDATE sites that previously set `must_change_pw=1` (student auto-provision, admin parent create UPSERT branches, admin parent password reset) now write `must_change_pw=0`. The `must_change_pw` column remains in the schema as dead data (not dropped — additive philosophy). The admin parent password-reset endpoint still issues temp passwords; those temp passwords are now the working credential (no forced rotation on first login).
- **Student info card simplified** (G13.2, `3a12493`). المستوى row hidden in `PORTAL_PARENT_PID_HUB_HTML` via inline `display:none`. The `id="card-level"` element is preserved so the existing `phRenderHub` JS binding doesn't null-deref; `/api/parent/hub-stats` still returns the field.
- **Weekly summary section removed** (G13.3, `4c36ab4`). "ملخص هذا الأسبوع" 3-card block stripped from `PORTAL_STUDENT_HTML` (the points-tab view at `/portal/parent-hub/points`). The 3-card section never existed in `PORTAL_PARENT_HTML`.
- **Activity feed removed from both parent surfaces** (G13.4, `a8c1071`). "آخر النشاطات" cards stripped from BOTH `PORTAL_STUDENT_HTML` and `PORTAL_PARENT_HTML`. The admin-side `/dashboard` "آخر النشاطات" widget (`/api/dashboard/recent-activity`) is preserved — that's the staff-facing feed and stays untouched.
- **8-week chart + Chart.js dependency removed** (G13.5, `dd3584f`). "تطوري خلال 8 أسابيع" / "التقدم خلال آخر 8 أسابيع" chart sections removed from both `PORTAL_STUDENT_HTML` and `PORTAL_PARENT_HTML`. `drawChart` and `drawCharts` functions deleted. Chart.js CDN `<script>` tag dropped from both templates' `<head>` (saves ~80KB per page load on parent surfaces). Chart.js is still loaded by dashboard, the parent evaluations page, and the reports tab — so the CDN is not gone from the app, just removed where unused.

Test infrastructure (`714c2fd` + `1aca22c`):
- `scripts/smoke_g13.py` — hermetic Playwright test asserting all five cleanups against the local server.
- `scripts/verify_g13_prod.py` — prod verification probe with `wait_for_load_state("networkidle", timeout=15000)` after login (workaround for `auto_test.py` quirk noted below).

Files touched across the wave: `app.py`; new test scripts under `scripts/`. No schema migrations.

Operator decisions locked in during discovery (so they don't recur):
- G13.3 / G13.4 / G13.5 target BOTH `PORTAL_STUDENT_HTML` AND `PORTAL_PARENT_HTML`, not just one. The operator was conflating which template held which section; resolved by stripping from both.
- Chart.js CDN: remove from templates where unused; keep elsewhere. No project-wide dependency removal.
- `must_change_pw` default for new users: `0`.
- `/portal/change-password` gating: admin-only.

Two notes worth carrying into the next session:
1. **safe_deploy auto-rollback is a no-op for HEAD-tagged safety points.** The deploy ran the safety-tag step at HEAD (the new code), so when the e2e step later failed, `git reset --hard <safety-tag>` reverted to the new code — i.e. didn't actually revert. In this case the e2e failure was a cold-start network timeout (`Page.goto /dashboard 30s`), prod was actually healthy, and the full 8-test e2e against prod (`run_e2e.py --base https://mindx-portal-1.onrender.com`) passed cleanly afterwards. Latent bug in `scripts/safe_deploy.py` — the safety tag must be taken at the PRE-CHANGE commit, not HEAD, for the rollback to mean anything. Logged in BUGS_LOG.
2. **`scripts/auto_test.py` `BrowserSession.navigate` uses `wait_until="domcontentloaded"`,** which returns before post-login redirects + G12 in-page tab activation finish. Workaround applied in `verify_g13_prod.py`: explicit `wait_for_load_state("networkidle", timeout=15000)` after login. Separately, doing a second cross-route navigate (e.g. `/portal/parent-hub/points` after `/portal/parent`) sometimes loses the session cookie in headless Chromium and redirects to `/login` — Playwright/test-rig artifact, not a real regression. Logged in BUGS_LOG.

Decision rationale: see ADR-030 (retire forced password-change for non-admin) and ADR-031 (Chart.js + analytics widgets removed from parent surfaces) in `DECISIONS_LOG.md`.

#### Feature wave: G14 rewards-shop UX cleanup (commits `3225bc4` → `9a0be08`)

Shipped 2026-05-21 (same day as G13). Four parent-shop polish items + two test rigs, all live on prod at `9a0be08`. Safety tags: `safety/pre-g14-rewards-2026-05-21` at `1aca22c` (pre-G14 baseline) and `safety/pre-g14-rewards-shop-20260521-202734` at `77933ec` (created by safe_deploy).

What's now true that wasn't before:

- **Real reward photos render on parent shop cards** (G14.1, `3225bc4`). Renderer in `PORTAL_STUDENT_HTML` now hits the existing `/api/rewards/<id>/image` BYTEA endpoint per card. No backend change — the image route already existed; the renderer was the only blocker. 48/48 active prod rewards have images and now display them.
- **Lightbox zoom on reward images** (G14.2, `52b008c`). Clicking a card image opens overlay `#rwLightbox` at max 80vh × 80vw. Closes via backdrop click / ESC / X button. Static display + close-only (no custom pinch handlers); mobile browsers retain native pinch-zoom inside the overlay.
- **Category filter tabs** (G14.4, `9173409`). Top-level tabs split the shop into 🎮 ألعاب (default, also catches untyped rewards so nothing disappears) and 🍔 وجبات. Backed by existing `rewards.category_type` column (`'toy'` | `'food'`) — **no schema migration**. Active tab persists across redeem re-renders via `STATE.currentCat`.
- **History as sub-tab inside points page** (G14.6, `cae0a51`). Points page split into two sub-panes via top sub-tab bar: 🛍️ متجر المكافآت (shop, default) and 📋 مكافآتي السابقة (history). Both rendered into `innerHTML` in one pass; switching is a `display` swap, no refetch. Page-local `STATE.currentSub` persists; no URL hash (G12's outer hash owns the fragment).

Test infrastructure (`77933ec` + `9a0be08`):
- `scripts/smoke_g14.py` — hermetic Playwright test, 41 checks against the local server.
- `scripts/verify_g14_prod.py` — prod verification probe using `requests.Session()` instead of Playwright to sidestep the headless-Chromium cookie-drop quirk logged in BUGS_LOG 2026-05-21. 17/17 prod checks pass.

Files touched: `app.py` (renderer + CSS + JS in `PORTAL_STUDENT_HTML`); new test scripts under `scripts/`. No schema migrations.

One surprise worth recording: the operator's CHANGE-3 spec called for adding a `category` column to `rewards`, but `category_type` (`'toy'` / `'food'`) had already existed since the menu-store work. G14.4 reused it instead — no migration, no `data-protector` round, less risk. Default for untyped rewards is the 🎮 ألعاب tab so legacy rows stay visible.

Deploy note: `safe_deploy` ran with `--skip-e2e` because the e2e step has been hitting cold-start 30s navigation timeouts (same root cause as the G13 latent-bug note about safety-tag rollback being a no-op). Full `run_e2e.py --base https://mindx-portal-1.onrender.com` ran cleanly afterwards (8/8 once Render finished its hot restart — initial run hit 502s during rollover).

#### Feature wave: G15 student-side approval workflow (commits `348a6a3` → `cfe3d59`)

Shipped 2026-05-21 (same day as G13/G14), live on prod at `cfe3d59`. Safety tags: `safety/pre-g15-approval-workflow-2026-05-21` at `9a0be08` (pre-G15 baseline) and `safety/pre-g15-approval-workflow-20260521-215521` at `eb4a461` (safe_deploy tag).

What's now true that wasn't before:

- **Logged-in role=student users have their own approval-routed shopping flow** distinct from the parent-PID surface. The legacy `/api/portal/student/redeem` — which silently bypassed admin approval by writing `redemptions.status='pending'` — is now a hard **410 Gone** (G15.7, `4e1a3c7`). All student-initiated orders go through admin approval.
- **Student orders always create `redemptions(status='requested', request_source='student_portal')`.** Points are **RESERVED** (visible to the student, not spendable), not debited, until admin approves via the existing `/api/points/redemptions/<id>/approve`. Rejection / cancellation releases the reservation. Approve/reject/deliver/cancel arithmetic on `_pts_balance` is untouched — Reserved is a separate computed view.
- **9 new session-auth endpoints** (G15.1, `348a6a3`): `GET /api/portal/student/balance`; `POST /api/portal/student/order`; `GET /api/portal/student/cart`; `POST /api/portal/student/cart/add`; `PUT /api/portal/student/cart/<cid>/quantity`; `DELETE /api/portal/student/cart/<cid>`; `POST /api/portal/student/cart/checkout`; `POST /api/portal/student/redemptions/<rid>/cancel`. Owner-scoped by `session['user']` role/student_id; no rate limit (login + role check is the gate).
- **New balance helper `_g15_student_balance(db, sid)`** returns `{total, committed, reserved, available}`. Reserved = `SUM(redemptions WHERE status='requested')`; Available = `total - committed - reserved`. `_pts_balance` unchanged — still excludes requested rows entirely.
- **PORTAL_STUDENT_HTML rebuilt** (G15.2 `d5044ce`, G15.3 `b7b1463`, G15.4 `4fee3a8`, G15.5 `03b582a`, G15.6 `99d9597`): 3-card balance header (Total / Reserved / Available); two action buttons per reward card (🛒 cart, ⚡ direct order); new 🛒 السلة sub-tab with quantity stepper + checkout; the existing history sub-tab extended to "طلباتي" with all 5 status badges (📨/⏳/✅/❌/⛔), inline `rejection_reason`, and a cancel button on `requested` rows; insufficient-balance modal listing reserved orders for one-click cancel.
- **Admin /points/manage surfaces student_portal rows automatically** (G15.8, `1e202a7`). The three admin tabs (طلبات أولياء الأمور / في انتظار التسليم / سجل العمليات) share the `redemptions` table, so no admin-side rewiring was needed. New 🎓 الطالب source badge in `_pdSourceBadge` / `_histSourceLabel`, a new option in the history-tab dropdown, and a new branch in `/api/points/history?source=`. Atomically fixed an oversight where `parent_cart` was falling through to the 'staff' bucket — now folded into the parent bucket for both filters and labels.
- **Student-initiated cancel is owner-scoped + state-gated.** Only works on `status='requested'` rows the student owns. Once admin approves, only admin can cancel.

Operator decisions locked in during discovery:
- **No schema migration.** `redemptions` + `cart_items` + the five status states + `request_source` were already in place from the parent-PID work. Reuse over duplication — see ADR-032.
- **No legacy back-door.** `/api/portal/student/redeem` deprecated 410, not kept as a fallback.

Test infrastructure (G15.9 `eb4a461`, G15.10 `cfe3d59`):
- `scripts/smoke_g15.py` — hermetic Playwright test, 72 checks against the local server.
- `scripts/verify_g15_prod.py` — prod verification probe via `requests.Session()`, 25/25 prod endpoints pass.

Files touched: `app.py` (10 new endpoints + 1 helper + balance-card CSS + cart pane CSS/markup/JS + history badges + insufficient-balance modal + the 410 deprecation + admin source badge); new test scripts under `scripts/`. No schema migrations.

One test-rig note worth carrying forward: **Flask `jsonify` ASCII-escapes Arabic strings on the wire** (`صل...` rather than literal Arabic), so substring-matching the raw response body against Arabic literals silently fails. Fix is to parse via `r.json()['error']` and compare against the decoded string — caught mid-run during `verify_g15_prod.py` development.

Deploy note: `safe_deploy --skip-e2e` (same cold-start timeout pattern as G13/G14). Full `run_e2e.py --base https://mindx-portal-1.onrender.com` passed 8/8 after Render's hot restart settled (initial probe hit 502s during rollover).

Decision rationale: see ADR-032 (G15 reuses existing redemptions/cart_items infrastructure) in `DECISIONS_LOG.md`.

#### Feature wave: G16 cart UX polish (commits `aa9f084` → `37c7bbd`)

Shipped 2026-05-21 (same day as G13/G14/G15), live on prod at `37c7bbd`. Safety tags: `safety/pre-g16-cart-ux-2026-05-21` at `7a67eb5` (pre-G16 baseline) and `safety/pre-g16-cart-ux-20260521-230739` at `37c7bbd` (safe_deploy tag).

What's now true that wasn't before:

- **Per-card qty stepper on every reward card** (G16.1, `aa9f084`). `− [N] +` control with cap = `min(99, floor(available/cost))`; the `+` button enforces a cart-aware ceiling so `qty + cart-total-of-this-item` can't exceed available. Stepper resets to 1 after each add. Cart button label changed from "🛒 السلة" → "🛒 أضف للسلة" (the old label was operator-flagged as ambiguous).
- **Confirmation modal on add-to-cart** (G16.2, `05d1d38`). Click no longer silently adds — user sees "هل تريد إضافة [name] (×N) إلى سلتك؟" in the existing `#confirm` modal.
- **Floating cart badge** (G16.3, `b0e21c9`). Fixed bottom-right (RTL end, operator choice), 56×56 brand-purple circle with item-count chip. Hidden when cart is empty; 200ms opacity fade-in; `z-index 90` (below modals). Click opens the cart modal.
- **Cart modal overlay** (G16.5, `564b373`). New `#cartModal` is an overlay version of the cart sub-pane, reusing `renderCartContents()` so qty changes / removes / checkout behave identically. Closes on backdrop / ESC / ✕. Body refreshes on every load() so edits in either surface stay in sync. The G15.4 cart sub-tab is preserved as a secondary access path (additive change only).
- **Proactive balance-exhausted block** (G16.4, `f4fb60f`). When `cart.total + (cost × qty) > available` the user sees "طلبياتك استوعبت النقاط — لا توجد نقاط تكفي لهذه اللعبة" with a 4-row breakdown (Available / Current cart / This item / Shortfall) and a "عرض السلة" CTA that jumps to the cart modal. Reuses the `#balLow` markup with a swapped action row.
- **Floating-badge ↔ sub-tab coordination** (G16.6, `142f524`). Both surfaces share state so the badge count, the sub-tab cart pane, and the overlay modal never drift.

Operator decisions locked in during discovery:
- Confirm text: "هل تريد إضافة [name] (×N) إلى سلتك؟"
- Balance-exhausted text: "طلبياتك استوعبت النقاط — لا توجد نقاط تكفي لهذه اللعبة"
- Floating badge position: bottom-right (RTL end)
- Stepper resets to 1 after each add
- Cart sub-tab kept alongside the modal (safety brief, additive only)

Test infrastructure (G16.7, `37c7bbd`):
- `scripts/smoke_g16.py` — new hermetic Playwright test, 56 checks.
- `scripts/smoke_g15.py` — one-line update so the cart-button assertion now accepts `addToCart` OR `askAddToCart`.

Files touched: `app.py` (CSS + reward card renderer + 6 new JS functions + 2 new modal DOMs + render() integration); new `scripts/smoke_g16.py`; one-line touch on `scripts/smoke_g15.py`. No schema migrations.

Two engineering notes worth carrying forward:
- **`node --check` guard from G15-HOTFIX still pays off.** It continues to catch inline-JS parse errors in the giant `PORTAL_STUDENT_HTML` blob; G16.7's hermetic test runs it on every CI cycle. Keep it in the pipeline for any future portal work.
- **Prod-verify probes must poll both `/api/health` AND `/`** before considering Render settled. Health alone can flicker green during rollover while authenticated routes still 502 — the initial G16.8 probe hit this and false-positive-matched against the inline script in Render's own 502 page. Future verify scripts: gate on `200` from both endpoints (or parse for an expected markup token), not just health.
- `showInsufficientBalance` and `showCartWouldExceed` share the `#balLow` modal; both functions restore the default action row at the END of their handlers. Any new variant added to that modal must follow the same pattern or UI state will bleed between reuses.

### 2026-05-22

| Hash | Title |
|---|---|
| `d632fbf` | feat(portal): G17.1 remove direct-order button + JS from frontend |
| `4ed38e3` | feat(portal): G17.2 remove backend endpoint /api/portal/student/order |
| `f49be4d` | test(portal): G17.3 hermetic test for direct-order removal |

#### Feature wave: G17 student rewards shop — single purchase path (commits `d632fbf` → `f49be4d`)

Shipped 2026-05-22, live on prod at `f49be4d`. Safety tags: `safety/pre-g17-remove-direct-order-2026-05-21` at `37c7bbd` (the real pre-G17 baseline — rollback point if anyone ever wants the direct-order endpoint back) and `safety/pre-g17-remove-direct-order-20260522-001300` at `f49be4d` (safe_deploy's tag, same commit as the deploy per the known safe_deploy bug).

What's GONE (user-visible):
- **The "⚡ طلب مباشر" button is removed from every reward card.** Cards now show only the qty stepper + the single `🛒 أضف للسلة` button. Cart is the sole student-initiated purchase path.
- **`POST /api/portal/student/order` is deleted at the route level.** Flask's url_map has zero routes matching that path; requests hit 404. The ~70-line `api_portal_student_order` view function is gone.
- **Frontend wiring removed**: `askDirectOrder()` / `doDirectOrder()` JS functions deleted; `.btn-order` and `.reward-actions .btn-row` CSS rules deleted; the `canOrder` local var (which only fed the deleted button) deleted.
- **Legacy `/api/portal/student/redeem` 410-hint updated** from `/api/portal/student/order` → `/api/portal/student/cart/add` since the previous target no longer exists.

What stays (CRITICAL — verified preserved):
- **All 5 cart endpoints intact**: `/cart`, `/cart/add`, `/cart/<cid>/quantity`, `/cart/<cid>`, `/cart/checkout`.
- **Balance + redemptions endpoints intact**: `/api/portal/student/balance`, `/api/portal/student/redemptions`, `/api/portal/student/redemptions/<rid>/cancel`.
- **Past `request_source='student_portal'` rows in `redemptions` untouched** — admin can still approve / reject / deliver them.
- **All admin-side `student_portal` references preserved** (🎓 الطالب badge, history-tab dropdown option, source filter) — past direct-order rows still surface correctly in the staff UI.
- **`_g15_validate_reward_for_request` + `_g15_student_balance` helpers preserved** — both still called by the cart endpoints.
- All G16 surfaces (qty stepper, floating cart badge, cart modal, confirmation modal, proactive balance check, insufficient-balance modal) and all G1–G14 functionality untouched.

Operator decision locked in: **Full deletion, not soft deprecation** (no 410 placeholder for `/api/portal/student/order`). Reason given in the G17 brief: "only one purchase path, no back-doors". To restore, reset to safety tag `safety/pre-g17-remove-direct-order-2026-05-21` at `37c7bbd`. See ADR-033.

Prod verification:
- `/api/portal/student/order` returns **404** (probed via `requests.Session`).
- `/cart/add` returns 200 on add; `/balance` returns 200; legacy `/redeem` still returns 410 with `use_instead: /api/portal/student/cart/add`.
- Deployed HTML: `'⚡ طلب مباشر'` absent, `'🛒 أضف للسلة'` present; `askDirectOrder` undefined, `askAddToCart` defined.
- `node --check` on deployed inline JS: clean.
- `run_e2e.py --base <prod>` 8/8 after a transient cold-start hang during Render rollover (known pattern, not a regression).

Test infrastructure:
- **New**: `scripts/smoke_g17.py` — 38 checks, inverse-asserts every G17 deletion + positive-asserts cart preservation + Flask `url_map` runtime check (0 `/order` routes, 5 `/cart` routes).
- **Updated**: `smoke_g15.py` dropped 4 direct-order checks + softened the 410-hint assertion; `smoke_g16.py` dropped the G15.1 `/order` route check + the "direct-order button intact" regression + loosened the 410-hint check + removed `api_portal_student_order` from the function-presence list; `verify_g15_prod.py` replaced the 3-step `/order` gate-validation chain with a single 404 assertion and flipped the HTML probe.
- All 6 smoke suites pass (G12 + G13 + G14 + G15 + G16 + G17).

Files touched: `app.py` (reward-card renderer, JS, CSS, route deletion); new `scripts/smoke_g17.py`; touches on `smoke_g15.py`, `smoke_g16.py`, `verify_g15_prod.py`. No schema migrations.

One engineering note worth carrying forward: **`request_source='student_portal'` is now a data-only value** — no UI surface submits a "direct-order" row anymore, but the value still tags both legacy direct-order rows AND new cart-checkout rows in `redemptions`. Future shop additions must route through cart (no parallel "quick buy" surfaces). See ADR-033.

| Hash | Title |
|---|---|
| `e51569e` | chore(scripts): G19.1 investigation probe for student 4822 balance gap |
| `d314049` | feat(portal): G19.2 revert balance display to single number |
| `759a8d0` | test(portal): G19.3 hermetic test for single-number balance revert |

#### Feature wave: G19 student rewards shop — revert 3-card balance to single number (commits `e51569e` → `759a8d0`)

Shipped 2026-05-22, live on prod at `759a8d0`. Safety tags: `safety/pre-g19-balance-investigation-2026-05-22` at `f49be4d` (pre-G19 baseline, real rollback point) and `safety/pre-g19-balance-revert-20260522-005803` at `759a8d0` (safe_deploy tag, same commit as deploy per the known safe_deploy bug).

**Investigation outcome (G19.1): no bug.** Operator reported student سارة السيد هادي (id=4822, مجموعة 3) was "missing 80 points". Read-only admin-endpoint probe (`scripts/investigate_g19_sara.py`) reconciled the math: 8 `point_events` sum to 181 earned; 1 `redemptions` row (id=58, COLOR MUD, cost=80, status=`pending` — approved/awaiting-delivery, already debited per G15's documented state machine); 181 − 80 = 101 available. Two manual adjustments visible in the log: +88 on 2026-05-12 by Ahmed Ibrahim (legitimate initial top-up pattern) and +80 on 2026-05-21 19:00 by admin (almost certainly an operator-compensating adjustment for the COLOR MUD the operator forgot was already approved). Operator accepted the finding — no data correction.

**The real issue was UX, not data.** G15.2's 3-card breakdown (Total / قيد الحجز / المتاح) was technically accurate but invited the "where did my points go?" misread — pending redemptions are committed at admin-approve time (NOT at delivery), so any student with an outstanding pending order sees `total > available` and reads it as a missing balance. The 3-card design exposed internal accounting that confused students more than it helped them.

What changed (user-visible):
- **The 3-card balance display is REVERTED.** Students now see the pre-G15.2 single big headline number (the original `.pts` + `.ptslbl` markup restored verbatim).
- **The displayed number is `STATE.balance.available`** — what they can actually spend, NOT the gross `total`. Pending/delivered redemptions are silently subtracted at the API layer; students see only the spendable figure.

What stays (CRITICAL — verified preserved):
- **`/api/portal/student/balance` endpoint unchanged.** Still returns `{total, committed, reserved, available}`. `STATE.balance` still populated client-side.
- **`_pts_balance` + `_g15_student_balance` helpers unchanged.** No data fix, no migration. Past `student_portal`-sourced redemptions stay in place.
- **All cart gates still use `.available`**: G15.6 insufficient-balance modal, G16.4 proactive cart-aware check, `/cart/add` server-side validation — none of them touched the visible markup; they read from `STATE.balance.available` which has been the actual spend gate all along.
- All G14–G17 surfaces (qty stepper, floating cart badge, cart modal, confirmation modal, proactive balance check, insufficient-balance modal, single-purchase-path cart) intact.

Operator decisions locked in during G19.1:
- **No data correction for student 4822.** Math is correct; the COLOR MUD redemption is legitimate even if forgotten by the operator.
- **Single number, not 3 cards.** The breakdown was technically right but UX-confusing.
- **Show `available` (spendable now), not `total` (gross earnings).** Avoids the entire class of "missing points" perception bugs.

Test infrastructure:
- **New**: `scripts/smoke_g19.py` — 40 checks asserting 3-card markup removed, single-number restored, dependent surfaces (G15.6 / G16.4) still gate on `.available`, every G14–G17 surface preserved, plus `node --check` on inline JS.
- **New**: `scripts/investigate_g19_sara.py` — read-only admin-endpoint probe, re-runnable for any future balance investigation (takes `--base <url>`, hits `/api/students` + `/api/points/student/<sid>` + `/api/points/reports/student/<sid>` + `/api/points/redemptions` + `/api/points/history`).
- **Updated**: `smoke_g15.py` G15.2 section flipped from positive 3-card assertions to positive single-number assertions + inverse "3-card GONE" check; `smoke_g16.py` dropped the 3-card regression check (kept balance-fetch wiring); `verify_g15_prod.py` HTML probe flipped to assert single-number markup.
- All 7 smoke suites pass (G12 + G13 + G14 + G15 + G16 + G17 + G19); full 8-test e2e against prod green; `node --check` on deployed inline JS clean.

Files touched: `app.py` (PORTAL_STUDENT_HTML balance markup revert); new `scripts/smoke_g19.py`, new `scripts/investigate_g19_sara.py`; touches on `smoke_g15.py`, `smoke_g16.py`, `verify_g15_prod.py`. No schema migrations. No backend route changes.

Two notes worth carrying forward:
- **Pending-redemption-already-debited UX trap will keep biting.** Any student with a pending order sees `total > available` internally. The single-number display hides this from students, but staff need to know: "approve" (requested → pending) IS the commitment point, NOT "deliver". Undoing a debit requires cancelling the redemption (refunds), not refraining from delivery.
- **Operator-compensating manual adjustment is a UX failure mode.** Sara's +80 on 2026-05-21 19:00 is the canonical example: when staff feel something is wrong, they add an offsetting `points_manual_adjust` entry rather than cancelling the real `redemptions` row, which leaves the audit trail confusing. Future improvement candidate: a one-click "cancel + refund" shortcut on the admin redemption row, so the proper fix is easier than the manual-adjustment workaround.

| Hash | Title |
|---|---|
| `f80e1f8` | fix(parent-portal): G20a.1 restore read-only book viewer link (المناهج) |
| `1df9f89` | fix(parent-portal): G20a.2 restore front-of-shop pending/rejected callouts (النقاط) |
| `f08138d` | fix(parent-portal): G20a.3 wrap evaluations tab in iframe to OLD rich page (التقييمات) |
| `355b9d4` | test(parent-portal): G20a.4 hermetic test for 3-tab restoration |

#### Feature wave: G20a parent-portal — restore 3 tab regressions from V2-retirement consolidation (commits `f80e1f8` → `355b9d4`)

Shipped 2026-05-22, live on prod at `355b9d4`. Safety tags: `safety/pre-restore-pre-redesign-features-2026-05-22` at `759a8d0` (pre-G20a baseline, real rollback point) and `safety/pre-g20a-parent-tab-restoration-20260522-022345` at `355b9d4` (safe_deploy tag, same commit as the deploy per the known safe_deploy bug).

**Root-cause framing.** Three parent-portal tabs (المناهج / النقاط / التقييمات) had lost user-visible features in the 2026-05-16 consolidation commit `3ad90c1` — when ~100K of rich flat-scroll `PARENT_HTML` was retired and replaced by ~30K of split sub-page templates. The OLD backend endpoints (`/parent/book/<bid>/viewer`, `/parent/book/<bid>/page/<n>.webp`, `/parent/evaluations/view`, `/parent/evaluations` JSON) were ALIVE the entire time — only the frontend linkage to them was dropped. G20a re-links, doesn't rebuild. Backend is untouched.

What's restored (user-visible):
- **المناهج (books) tab.** Books with `can_download=false` now route to `/parent/book/<id>/viewer?pid=<pid>` — the operator-built per-page WebP renderer with watermark, NO PDF download possible. Restores the IP-protection feature that was unlinked when `PARENT_HTML` was retired. Books with `can_download=true` still use `/api/books/<id>/view` (browser's PDF viewer with built-in download, by design).
- **النقاط (points) tab.** Pending and rejected redemption callouts are now PROMINENTLY displayed at the top of the shop pane, above the category tabs. Pending shows a blue ⏳ card "طلبك قيد المراجعة من الإدارة" + reward + points + timestamp. Rejected shows an orange ⚠ card "تم رفض طلبك" + reward + points + timestamp + the admin's `rejection_reason` inline ("سبب الرفض: …" with fallback "(لم يُذكر سبب)" when blank). Rejected cap at 5 most-recent. Same pattern as the OLD `_ppRenderStore` (deleted in `3ad90c1`). Data sourced from existing `STATE.redemptions` — no new API calls.
- **التقييمات (evaluations) tab.** `/portal/parent-hub/evaluations` route now returns an iframe wrapping `/parent/evaluations/view?pid=<pid>` when called with `?inner=1` (G12 in-page tab mode). Standalone visit (no `?inner=1`) 302-redirects to the rich page directly. The richer pre-`3ad90c1` `PARENT_EVALUATIONS_HTML` (16K chars vs the 13K slimmed `PORTAL_PARENT_EVALUATIONS_HTML`) is now what parents actually see inside the tab. `PORTAL_PARENT_EVALUATIONS_HTML` is left in code (no callers now) — flagged for a future cleanup pass.

What stays (CRITICAL — verified preserved):
- **Backend untouched.** No route added, removed, or changed. The 4 OLD endpoints listed above were already alive; G20a only re-wires the frontend to point at them.
- **The 3-card balance display from G19.2 stays unchanged** — that was a separate operator-confirmed UX decision (see ADR-034), not part of the same regression class.
- **All G12–G19 surfaces** (parent-portal in-page tabs, scaffolding, hub, fees, attendance, behaviour, single-number balance) intact.

Operator decisions locked in during G20a discovery:
- **All 3 tabs sequentially in one deploy cycle**, not 3 separate deploys. The fixes are independent but the diagnostic frame is shared — easier to verify together.
- **Evaluations: Path B (iframe wrapper), NOT port content into the new template.** Faster, and keeps the OLD richer page authoritative for the data model. Re-porting was rejected as ~600 lines of UI work for zero functional gain.
- **Re-link, don't rebuild.** Every "lost" feature here turned out to be a still-live backend endpoint that the new template just never wired up to. Confirmed by checking `app.py` for the route handler before assuming a rewrite was needed.

Diagnostic breadcrumb for future "we lost X in the redesign" reports:
- **ALWAYS check whether the OLD endpoints are still alive in the backend before assuming they need to be rebuilt.** Frontend templates get rewritten frequently in a parent-portal redesign cycle; the routes survive longer than the templates that called them.
- **The conversion commit `3ad90c1` (2026-05-16) is THE point** where 100K of rich flat-scroll `PARENT_HTML` was replaced by ~30K of split sub-page templates. Anything reported as "lost" in the 3 content tabs (books / evals / points) is highly likely to be a renderer that lived in OLD `PARENT_HTML`'s IIFE and was not ported.
- **Extraction pattern**: `git show 3ad90c1^1:app.py | grep -A 50 'function _ppRenderStore'` (or `_ppRender`, `ppRenderBookCard`, etc.) pulls the OLD render functions. Diff against the current sub-page renderer to identify the gap.

Test infrastructure:
- **New**: `scripts/smoke_g20a.py` — 45 checks asserting all 3 restorations + `node --check` on `PORTAL_STUDENT_HTML` AND `PORTAL_BOOKS_HTML` inline JS + Flask `url_map` regression for 8 critical routes (books-viewer, books-page-webp, evaluations-view, evaluations-json, parent-hub tabs).
- All 8 smoke suites pass (G12 + G13 + G14 + G15 + G16 + G17 + G19 + G20a).

Prod verification:
- المناهج tab: deployed HTML carries the conditional `viewHref` linking — books-with-no-download point at `/parent/book/<id>/viewer?pid=<pid>`, downloadable books still go to `/api/books/<id>/view`.
- النقاط tab: deployed CSS carries `.pp-pending-card` + `.pp-rejected-card`, Arabic title strings ("طلبك قيد المراجعة من الإدارة", "تم رفض طلبك", "سبب الرفض") present.
- التقييمات tab: `/portal/parent-hub/evaluations?inner=1` returns the 492-char iframe wrapper pointing at `/parent/evaluations/view?pid=TEST-STUDENT-0001`; no-`?inner` mode 302-redirects to the rich page.

Files touched: `app.py` (3 surgical edits: `PORTAL_BOOKS_HTML` renderer, `PORTAL_STUDENT_HTML` shop section + CSS, `portal_parent_hub_evaluations_page` route); new `scripts/smoke_g20a.py`. No schema migrations. No backend route changes.

One engineering principle worth carrying forward: **when migrating a flat-scroll template to sub-page templates, prefer re-linking the OLD richer surface (via iframe / redirect / direct URL) over re-porting features.** Faster, preserves the operator's original work, and avoids the silent-feature-loss class of regression entirely. See ADR-035.

| Hash | Title |
|---|---|
| `2da5483` | fix(parent-portal): G20b.1 shade unaffordable rewards |
| `7c6331f` | test(parent-portal): G20b.2 end-to-end workflow probe (proves no bug) |
| `2407cdf` | fix(points-manage): G20b.3 make rejection reason MANDATORY |
| `b531c9b` | test(parent-portal): G20b.4 hermetic test for shading + mandatory reject |

#### Feature wave: G20b parent-portal — unaffordable-reward shading + mandatory rejection reason + workflow proof (commits `2da5483` → `b531c9b`)

Shipped 2026-05-22, live on prod at `b531c9b`. Safety tags: `safety/pre-g20b-shading-approval-2026-05-22` at `355b9d4` (pre-G20b baseline, real rollback point) and `safety/pre-g20b-shading-mandatory-reject-20260522-025614` at `b531c9b` (safe_deploy tag).

**Two user-visible restorations + one diagnostic breakthrough.** Operator filed back-to-back complaints that the cart-checkout → admin-approval workflow was broken. G20b proved it is NOT broken end-to-end (controlled prod probe, 2 cycles, 24 checks each), then shipped the two UX restorations that were independently needed and that — incidentally — make the silent-failure mode that caused the false-positive bug report impossible to reproduce.

What's restored (user-visible):
- **النقاط shop — unaffordable cards now visually muted.** Restored from the OLD `_ppFormatStoreCard` pattern (pre-`3ad90c1`) that G17 relaxed when it allowed "planning ahead" by keeping the cart button live regardless of balance. New behaviour: card opacity 0.55, product image grayscale 60%, cart button disabled, quantity stepper `+` disabled, and a small red hint "⚠ نقاطك غير كافية" below the cost. Operator-driven flip back to upfront-visible-signal UX.
- **/points/manage طلبات tab — admin rejection reason is now MANDATORY.** Old prompt `"سبب الرفض (اختياري):"` allowed admins to bypass on empty. New prompt loops on empty input with alert `"يجب كتابة سبب الرفض. اضغط إلغاء للتراجع عن الرفض."` Cancel still aborts the whole reject (no row mutation). The reason text then surfaces on the front-of-shop rejected callout (G20a.2) under `"سبب الرفض: <text>"` — the chain `admin reason → student visibility` is now end-to-end enforced.

**The workflow-is-actually-working verification breakthrough.** Two runs of `scripts/verify_g20b_workflow.py` against prod — once before G20b.1 (redemptions row #59) and once after deploy (row #60). Each cycle: grant +50 via `behavior_id=15` ("تعديل يدوي") → `cart/add` (200) → `cart/checkout` creates `redemptions` row with `status='requested'` + `source='student_portal'` → admin `approve` flips to `pending` (debits 30 pts, balance 50→20) → admin `deliver` flips to `delivered` → cleanup refund -50. Both cycles green. Operator's complaint history: G20-round-1 "not a bug"; G20-round-2 "I tested again it IS a bug" — actually still wasn't, MAX(id) was 58 with 0 new rows; G20b "the workflow is broken" — **confirmed working end-to-end via controlled probe**.

**Diagnostic breadcrumb for the next operator who reports "approval workflow is broken":**
- The `cart/checkout` endpoint at `app.py:88663-88668` correctly inserts `status='requested'` + `request_source='student_portal'`.
- The admin filter `loadRequests` at `app.py:89177` correctly filters on `r.status === 'requested'` source-agnostically.
- Both are provably correct.
- **If a real student submits and nothing appears in the approval queue, the submission failed BEFORE the INSERT** — almost certainly on the balance/affordability gate at `app.py:88644`: `if summary["total"] > bal["available"]: return 400`. The student saw a generic error and the admin saw an empty queue.
- G20b.1's shading + disabled cart button make this state visible upfront, so the operator can't repro the silent failure mode that caused the false-positive report (i.e. testing with a 0-balance account like `student_test`).

Operator decisions locked in (these implement existing decisions — no new ADR):
- **Shade unaffordable rewards upfront**, even though G17 had relaxed this to support "planning ahead". The planning-ahead UX is silently subverted by the balance-gate INSERT failure, so re-asserting the upfront signal is net-positive.
- **Mandatory rejection reason** — the rejected callout already surfaces the reason to students (G20a.2), so allowing admins to skip leaves students with a callout that says "سبب الرفض: (لم يُذكر سبب)" — defeating the point of the restoration. The student-facing "(لم يُذكر سبب)" fallback is kept for historical rows.

What stays (verified preserved):
- **Backend untouched.** No route added, removed, or changed. Three surgical frontend edits to `app.py`: `PORTAL_STUDENT_HTML` CSS + renderer (G20b.1), `POINTS_MANAGE_HTML` `rejectRequest` function (G20b.3).
- The 3-card balance display from G19.2 + the G20a tab restorations (المناهج / النقاط / التقييمات) all intact.

Test infrastructure:
- **New (re-runnable)**: `scripts/verify_g20b_workflow.py` — 24 checks, end-to-end prod probe. Grants +N points, runs the full cart → approve → deliver cycle, refunds -N. The go-to diagnostic when a future operator reports "workflow is broken" — before assuming a code regression, run this against prod with `student_test` boosted to a positive balance. If it stays green, the user-reported failure is upstream (balance gate, not the workflow).
- **New (hermetic)**: `scripts/smoke_g20b.py` — 30 checks. Asserts shading CSS + renderer + mandatory-reject prompt + 9 critical routes still in `url_map`.
- All 9 smoke suites pass (G12 + G13 + G14 + G15 + G16 + G17 + G19 + G20a + G20b).

Files touched: `app.py` (3 surgical edits to `PORTAL_STUDENT_HTML` + `POINTS_MANAGE_HTML`, no backend changes); new `scripts/verify_g20b_workflow.py`; new `scripts/smoke_g20b.py`. No schema migrations.

One operational principle worth carrying forward: **when an operator reports a workflow regression, run a controlled end-to-end prod probe BEFORE assuming the code changed.** Two of three "the workflow is broken" reports in the G20 cycle turned out to be false positives caused by silent failure modes upstream of the workflow itself (zero-balance accounts hitting the affordability gate). The `verify_g20b_workflow.py` probe is now the diagnostic of record for this complaint class.

## How to append

memory-keeper appends new entries here in passive-tracking mode (PostToolUse on `feat:`/`fix:`/`refactor:` commits). Format for a single-day entry:

```
### 2026-MM-DD
- `<short-hash>` — <commit subject> (<scope inference>)
```

Group by week once a week is complete; keep the most recent week as per-day until the week closes.
