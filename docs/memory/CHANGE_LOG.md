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

### 2026-05-16

| Hash | Title |
|---|---|
| `6a94497` | fix(parent-portal): display student name + kill PID-prompt flash on `/parent/legacy` |
| `3ad90c1` | refactor(parent-portal): consolidate onto منصة V1; retire بوابة V2 entry points |
| `d7cc70c` | fix(parent-portal): restore full feature hub at `/portal/parent` (6 cards) |
| `3b940c4` | fix(parent-portal): restore the formal student-card layout at `/portal/parent` |
| `3465c6f` | fix(parent-portal): repair 500 on `/api/portal/student/attendance` (Postgres) |
| `e51642b` | test(personas): commit durable parent-portal verification harnesses |

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

## How to append

memory-keeper appends new entries here in passive-tracking mode (PostToolUse on `feat:`/`fix:`/`refactor:` commits). Format for a single-day entry:

```
### 2026-MM-DD
- `<short-hash>` — <commit subject> (<scope inference>)
```

Group by week once a week is complete; keep the most recent week as per-day until the week closes.
