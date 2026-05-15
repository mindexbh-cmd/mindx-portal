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

## How to append

memory-keeper appends new entries here in passive-tracking mode (PostToolUse on `feat:`/`fix:`/`refactor:` commits). Format for a single-day entry:

```
### 2026-MM-DD
- `<short-hash>` — <commit subject> (<scope inference>)
```

Group by week once a week is complete; keep the most recent week as per-day until the week closes.
