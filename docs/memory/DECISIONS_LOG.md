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

### ADR-014: `/parent` stays public for anonymous WhatsApp visitors; redirect only authenticated users
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: Unified-login feature needed to decide what happens when a parent who is already logged in visits `/parent` (or the legacy alias `/parent/legacy`). Two interpretations on the table:
  - **Interpretation A**: Make `/parent` strictly authenticated. Any anonymous hit → redirect to `/login`. Cleanest URL semantics; one canonical entry per role.
  - **Interpretation B** (recommended): Keep `/parent` public for anonymous visitors (preserves the public CPR prompt that legacy WhatsApp deep-links rely on); only redirect when `session["user"]` is already populated — `role=student` → `/portal/parent-hub`, `role=parent` → `/portal/parent`.
- **Decision**: Operator chose Interpretation B. Authenticated parents/students now skip the redundant CPR prompt; anonymous visitors arriving from WhatsApp links keep the public PID flow unchanged.
- **Alternatives considered**: Interpretation A (above); a feature flag toggle (rejected — adds permanent config surface for a one-time UX cleanup); detecting WhatsApp UA (rejected — fragile, easy to break by browser updates).
- **Consequences**:
  - Additive guards only — zero break on legacy `/parent?pid=...` deep-links circulating in WhatsApp messages.
  - Two well-trodden public surfaces remain (`/parent`, `/parent/legacy`) but they no longer waste a click for already-authenticated visitors.
  - Means `/parent` semantics differ by auth state. Documented inline at `app.py` ~28800 and ~28825 so future maintainers don't "simplify" the guard away.
- **Reference**: commits `31499e9` (route guards) + `3712968` (login hint) + `5ecf19d` (plan/handoff). Plan doc: `docs/plans/unified-login-parent-direct-nav-20260515-222200.md`. Safety tag: `safety/pre-unified-login-parent-direct-nav-20260515-225736`.

### ADR-015: Split DB-safety from feature-safety — two distinct guardians, each with veto
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: `data-protector-agent` already gates every destructive DB op (DROP / DELETE / TRUNCATE / migration / bulk UPDATE). But "what works today" at the application surface — 502 routes, the parent shop checkout flow, the books_v2 chunked upload, the attendance loose-comparison rule, the taqseet ↔ student_payments mirror — was only implicit in `CLAUDE.md` and `PROJECT_BIBLE.md`. A well-meaning change to a shared helper could regress a feature without tripping the DB-safety agent at all. Operator wanted a second, peer-level guardian whose entire job is "does this break any existing feature?".
- **Decision**: Introduce `feature-protector-agent` (15th custom) as a regression-guard specialist with REJECT-class veto over the coordinator. Three-phase workflow: (1) pre-change audit against `docs/memory/FEATURE_INVENTORY.md` — which routes / templates / shared helpers does the diff touch?; (2) verdict — APPROVE / APPROVE WITH CONDITIONS / REJECT, with conditions enumerated as test obligations; (3) post-change verification — assertions from the inventory re-checked after merge. Inventory is append-only / incrementally updated, never regenerated from scratch (so historical critical-feature annotations don't get washed away by route renames).
- **Alternatives considered**:
  - Fold feature-safety into `data-protector-agent` (rejected — different scope, different review surface, would muddy data-protector's narrow DB-safety remit).
  - Make it advisory only, no veto (rejected — operator wanted a peer to data-protector, not a suggestion box).
  - Lean on `real-user-tester-agent` + `code-architect-agent` for regression coverage (rejected — they look for code quality / persona fit, not feature-surface preservation).
- **Consequences**:
  - Every non-trivial change now passes through two veto-empowered guardians (data-protector on the DB side, feature-protector on the feature side). Together they gate every risky change.
  - The top-20 critical-feature assertions in `FEATURE_INVENTORY.md` are now contractual invariants — breaking one is a REJECT, not a discussion.
  - Cost: one extra agent invocation per non-trivial task. Coordinator pipeline grows by one mandatory stage when the diff touches shared code, routes, templates, or APIs.
  - Inventory drift is the main risk — the agent must incrementally update `FEATURE_INVENTORY.md` whenever a route is added/removed/renamed. `/protect bootstrap` exists for the occasional sync but should be rare in steady state.
- **Reference**: commit `316d84d`; `.claude/agents/feature-protector-agent.md`; `.claude/commands/protect.md`; `docs/memory/FEATURE_INVENTORY.md` (502 routes, 69 categories, top-20 assertions). Complements ADR-007 (Expand-Migrate-Contract, DB-side) and the data-protector mandate in CLAUDE.md "Specialist agent team".

### ADR-016: Supreme catastrophe-prevention guardian above the role-specific guardians; veto power; only the human owner overrides REJECT
- **Date**: 2026-05-15
- **Status**: accepted
- **Context**: The existing guardians are scoped — `data-protector-agent` gates DDL / bulk-data ops (ADR-007 territory); `feature-protector-agent` gates regressions against the 502-route surface (ADR-015 territory). Neither one looks at a change holistically across all disaster categories. A change can be DB-clean and feature-clean yet still be a catastrophe: a `git push --force` to `main`, a security-hole rewrite, a p95-blowing query, or a UX cliff that nukes adoption. Operator wanted a SUPREME guardian above the role-specific ones whose entire job is "would this be a catastrophe for the project across any axis?".
- **Decision**: Introduce `catastrophe-prevention-agent` (16th custom) as a supreme guardian. Runs FIRST in the coordinator pipeline, before feature-protector and before data-protector. Reviews every change against 5 disaster categories: (1) data loss; (2) breaking changes; (3) security; (4) performance; (5) UX disasters. Default answer is NO unless the change is provably safe. Has REJECT-class veto power. **Only the human owner overrides REJECT** — no other agent, no coordinator, no operator-impersonating script. Bypass at the Bash-hook level requires the inline `override:catastrophe:<reason>` tag, which is logged.
- **Alternatives considered**:
  - Fold catastrophe-checks into data-protector or feature-protector (rejected — different scope, would muddy each agent's narrow remit; security + performance + UX disasters fall outside both).
  - Make the agent advisory only, no veto (rejected — operator wanted a hard stop, not a suggestion box).
  - Rely on the imported `security-auditor` + `performance-watchdog` + `incident-responder` already in the team (rejected — those are reactive / domain-narrow, not a unified disaster veto running on every change).
  - Single-category catastrophe agents (one for security, one for performance, etc.) — rejected as a category explosion that wouldn't deliver the holistic "is this a catastrophe?" verdict the operator asked for.
- **Consequences**:
  - Every non-trivial change now passes through THREE veto-empowered guardians in series: catastrophe-prevention (first) → feature-protector (second) → data-protector (DB-touching changes only). Together they form a defense-in-depth gate.
  - SOP gained step 0a ("Run `/check` first for risky changes") and is documented in `CLAUDE.md`.
  - PreToolUse Bash hook `catastrophe_block.py` (7th hook) provides a fast pattern-based block at the shell layer for the most dangerous literal commands (DROP TABLE, TRUNCATE, DELETE-without-WHERE, ALTER COLUMN type/rename, `rm -rf` on sensitive paths, `git push --force` without `--force-with-lease`, `git reset --hard origin/main`, `git filter-*`, `dropdb`, `pg_restore --clean`). Bypass tag `override:catastrophe:<reason>` is required inline; the hook also blocks the dangerous string when used as DATA (e.g. inside `echo`) so documenting these patterns in commit messages or scripts requires the override.
  - Cost: one extra agent invocation upfront per non-trivial task. Coordinator pipeline grows by one mandatory stage. Hook adds a few ms to every Bash call.
  - All REJECT verdicts land in `docs/memory/REJECTED_CHANGES.md` (full risk breakdown) and all verdicts (REJECT + APPROVE) land in `docs/memory/CATASTROPHE_LOG.md` (append-only ledger).
- **Reference**: commit `43b52d3`; `.claude/agents/catastrophe-prevention-agent.md`; `.claude/commands/check.md`; `.claude/hook_scripts/catastrophe_block.py`; `docs/memory/CATASTROPHE_LOG.md`; `docs/memory/REJECTED_CHANGES.md`; demo audits `docs/audits/catastrophe-check-delete-books-v2-20260515-204654.md` (REJECT) and `docs/audits/catastrophe-check-add-footer-slogan-20260515-204654.md` (APPROVE). Complements ADR-007 (Expand-Migrate-Contract), ADR-009 (auto-rollback safety tags), and ADR-015 (feature-protector).

### ADR-017: Consolidate parent UX onto منصة V1 (`/portal/parent`); retire بوابة V2 entry points; keep templates one release cycle for revert safety
- **Date**: 2026-05-16
- **Status**: accepted (supersedes the V2-direction implicit in ADR-014)
- **Context**: The codebase carried two parallel parent surfaces:
  - **منصة V1** — `/portal/parent`, role=parent, `PORTAL_PARENT_HTML`, points-focused. Renders the multi-child JSON in `linked_parent_for`.
  - **بوابة V2** — `/portal/parent-hub` + 6 sub-pages (`/attendance`, `/payments`, `/messages`, `/evaluations`, `/books`, plus the PID-hub variant) + the public `/parent` + `/parent/legacy` CPR-prompt flow used by WhatsApp deep-links.
  ADR-014 (2026-05-15) chose Interpretation B — keep `/parent` public for anonymous WhatsApp visitors, redirect only authenticated parents/students — under the assumption that V2 was the canonical authenticated surface for parents/students. Operator clarified that "نستخدم فقط منصة ولي الأمر" — V1 is the only parent surface they actually use; V2 is unused product surface. Keeping both creates maintenance drag (two templates to keep RTL-clean, two role dispatch paths, two sets of API endpoints) and ships UI that operators don't want users to see.
- **Decision**: Retire V2 as an entry point. `_pts_parent_children_ids` now also accepts `role=student` (returns `[linked_student_id]`) so V1 renders for the parent-with-child-PID-as-username pattern. `/login` dispatch routes `role=student` AND `role=parent` to `/portal/parent` (legacy `landing_page=parent_hub`/`student_portal` also rerouted). All 7 `/portal/parent-hub*` routes return 302 → `/portal/parent`. `/parent` and `/parent/legacy` redirect anonymous visitors to `/login` (no more public PID prompt). The login-page hint "أولياء الأمور: استخدم الرقم الشخصي" (shipped 2026-05-15 in commit `3712968`) is removed — it was V2-flow-specific and now misleading. **Templates intentionally kept in source for one release cycle as a revert safety net**: `PORTAL_PARENT_HUB_HTML`, `PORTAL_PARENT_PID_HUB_HTML`, `PORTAL_PARENT_ATTENDANCE_HTML`, `PORTAL_PARENT_PAYMENTS_HTML`, `PORTAL_PARENT_MESSAGES_HTML`, `PORTAL_PARENT_EVALUATIONS_HTML`, `PARENT_HTML`. These will be removed in a follow-up commit after the consolidation has soaked in prod without rollback.
- **Alternatives considered**:
  - Keep both surfaces, mark V2 as legacy in CLAUDE.md (rejected — operator wanted V2 gone from the user-visible surface, not just labelled; maintenance drag continues otherwise).
  - Delete the V2 templates in the same commit (rejected — no safety net if a surprise consumer surfaces; one-release-cycle soak time costs nothing).
  - Keep `/parent` + `/parent/legacy` public for WhatsApp deep-links per ADR-014 (rejected — operator confirmed the public CPR flow is unused; redirecting anonymous visitors to `/login` is cleaner; the operator-instruction "نستخدم فقط منصة ولي الأمر" effectively supersedes ADR-014's Interpretation B for this codebase).
  - Add a feature flag toggle between V1/V2 (rejected — adds permanent config surface for a one-time consolidation).
- **Consequences**:
  - V1 (`/portal/parent`) is now the single canonical parent/student surface. Multi-child parents and child-PID-as-username students both render through one template + one API endpoint pair.
  - URL compatibility preserved for saved bookmarks — every `/portal/parent-hub*` URL still resolves (via 302 to V1). No 404 surface for users who bookmarked V2 pages.
  - `/parent` and `/parent/legacy` lose their public PID-prompt flow. WhatsApp deep-links carrying `?pid=` will now redirect to `/login` for anonymous visitors. Operator confirmed this flow is unused; no behavioural surprise expected.
  - One release cycle of soak time before the V2 templates are physically removed from source — if a surprise consumer surfaces, revert the dispatch logic only and the templates are still wired up.
  - ADR-014's redirect rule for authenticated visitors on `/parent` survives in spirit (`role=parent`/`role=student` → V1) but the anonymous-visitor branch of ADR-014 is superseded.
- **Reference**: commit `3ad90c1` (consolidation), prior commit `6a94497` (parent-portal name + PID-flash fix shipped immediately before, now mostly moot for `/parent/legacy` after this consolidation but still useful for `PORTAL_PARENT_PID_HUB_HTML` rendering during the soak). Prod SHA `3ad90c147d05`; safety tag `safety/pre-consolidate-to-v1-platform-20260516-002351`. Operator quote: "نستخدم فقط منصة ولي الأمر".

### ADR-018: `/portal/parent` serves different templates by role — V2 hub (`PORTAL_PARENT_HUB_HTML`) for `role=student`, V1 points-only (`PORTAL_PARENT_HTML`) for `role=parent`; six sub-page handlers remain at `/portal/parent-hub/*` and serve their content directly
- **Date**: 2026-05-16
- **Status**: accepted (remediates / partially supersedes ADR-017)
- **Context**: ADR-017 (2026-05-16) consolidated parent UX onto منصة V1 by routing every parent-portal entry to `/portal/parent` and serving `PORTAL_PARENT_HTML`. In the same wave (commit `3ad90c1`), the six V2 sub-page handlers (`/portal/parent-hub/{payments,attendance,points,messages,evaluations,curriculum}`) were collapsed into 302 redirects to `/portal/parent`. Operator immediately reported: "كل البيانات التي كانت تظهر سابقا في المنصة عند دخول ولي الامر بالرقم الشخصي للطالب اصبحت الان غير ظاهرة" — every feature button vanished. Root cause was a terminology / template-selection mismatch: V1's `PORTAL_PARENT_HTML` is built around `linked_parent_for` multi-child JSON for `role=parent`; it does NOT render the feature-card hub that operator and users actually call "منصة" when they think of the parent experience. The 6-card hub lives in `PORTAL_PARENT_HUB_HTML` (despite its internal title "بوابة"), and it's what the operator wanted preserved. ADR-017 retired the wrong template.
- **Decision**:
  - `/portal/parent` dispatches by role:
    - `role=student` → `PORTAL_PARENT_HUB_HTML` (the 6-card hub: payments / attendance / points / messages / evaluations / curriculum).
    - `role=parent` → `PORTAL_PARENT_HTML` (V1 multi-child render, unchanged from pre-consolidation behaviour).
  - The 6 V2 sub-page handlers at `/portal/parent-hub/*` are restored to **serving their full content directly** (no redirects):
    - `/portal/parent-hub/payments` → `PORTAL_PARENT_PAYMENTS_HTML`
    - `/portal/parent-hub/attendance` → `PORTAL_PARENT_ATTENDANCE_HTML`
    - `/portal/parent-hub/points` → `PORTAL_STUDENT_HTML` (the points/store view — يحوي متجر المكافآت)
    - `/portal/parent-hub/messages` → `PORTAL_PARENT_MESSAGES_HTML`
    - `/portal/parent-hub/evaluations` → `PORTAL_PARENT_EVALUATIONS_HTML`
    - `/portal/parent-hub/curriculum` → `PORTAL_BOOKS_HTML`
  - **Bare `/portal/parent-hub` (no sub-path) still 302 → `/portal/parent`** — URL consolidation at the entry point is preserved as a gesture to ADR-017's spirit. Saved bookmarks for `/portal/parent-hub/*` sub-paths keep working without redirects.
  - `/parent` and `/parent/legacy` redirect rules from ADR-017 are unchanged (anonymous → `/login`; logged-in → `/portal/parent`). Operator confirmed they do NOT want the public PID prompt back.
- **Alternatives considered**:
  - Revert `3ad90c1` entirely (rejected — would re-introduce the V2-direction implicit in ADR-014 with its public CPR-prompt entry that operator confirmed is unused; also would forfeit the URL-consolidation gain at the entry point).
  - Serve `PORTAL_PARENT_HUB_HTML` to BOTH roles at `/portal/parent` (rejected — would break the multi-child `role=parent` flow which has its own established UI shape in `PORTAL_PARENT_HTML`; the two role shapes have different data contracts and the V1 template is the only one wired for multi-child).
  - Keep the sub-page handlers as redirects and embed all 6 views as tabs inside `PORTAL_PARENT_HUB_HTML` (rejected — large refactor scope for a regression fix; would mean re-wiring every sub-page's API consumer to a single-page app pattern; out of scope for an emergency restore).
  - Add a new "hub" template purpose-built for `role=student` (rejected — `PORTAL_PARENT_HUB_HTML` already exists and renders correctly; building a third template would be duplication).
- **Consequences**:
  - Two visible templates serve `/portal/parent` depending on role. Documented inline in the route handler so a future maintainer doesn't "simplify" the dispatch away. The internal Arabic titles inside each template ("بوابة" inside `PORTAL_PARENT_HUB_HTML`, "منصة" inside `PORTAL_PARENT_HTML`) are no longer authoritative for what operator/users call the surface — both surfaces are referred to as "منصة" in operator vocabulary depending on context.
  - The 6 V2 sub-pages are part of the production surface again. They were never deleted — `3ad90c1` only converted their handlers to redirects; the template constants stayed in source per ADR-017's "one release cycle revert safety net". This fix re-wires the handlers back to those preserved constants.
  - ADR-017's claim that V2 is "retired" is partially superseded: the V2 *hub navigation chrome* AND the 6 sub-pages are alive; only the public PID-prompt flow at `/parent` + `/parent/legacy` remains retired (operator confirmed unused — that part of ADR-017 stands).
  - Verification posture going forward: any change to which template a route serves MUST go through `real-user-tester-agent` (4 personas: student_test / parent_test / admin_test / teacher_test) BEFORE `safe_deploy`. Curl-only verification of status codes is insufficient. This is also captured as a `BUGS_LOG.md` prevention rule under the 2026-05-16 "Empty parent منصة after V1-consolidation" entry.
- **Reference**: commit `d7cc70c` (fix); prior commit `3ad90c1` (regression); safety tag `safety/pre-restore-parent-hub-features-20260516-004528`; verification harness `scripts/personas/parent_hub_verify.py`; reference screenshots `scripts/screenshots/20260516-0042..0043*`. Operator quote (regression report): "كل البيانات التي كانت تظهر سابقا في المنصة عند دخول ولي الامر بالرقم الشخصي للطالب اصبحت الان غير ظاهرة". Supersedes the "consolidate everything onto V1" part of ADR-017 for `role=student`; leaves the `/parent` + `/parent/legacy` retirement (anonymous PID-prompt flow killed) intact.

### ADR-019: `/portal/parent` for `role=student` serves the formal student-card layout (`PORTAL_PARENT_PID_HUB_HTML`), NOT the 6-floating-card V2 hub
- **Date**: 2026-05-16
- **Status**: accepted (supersedes the `role=student`-template choice from ADR-018)
- **Context**: ADR-018 (also 2026-05-16) chose `PORTAL_PARENT_HUB_HTML` (the 6-floating-card V2 hub) as the `role=student` template at `/portal/parent`. Operator's regression report after that fix landed (commit `d7cc70c`) revealed the wrong template was chosen: "خربت منصة ولي الامر التي كانت تعرض معلومات الطلبة بشكل منسخق وكل شي ذهب للاسف عملي ضاع. كان كل طالب تظهر له واجهة جميلة مكتوب فيها معلوماته الاساسية من اسمه ورقم مجموته ومكان لصورته والازرار بشكل منظم وكل زر كان يعمل ليس مثل الان للاسف الشديد انفكت الارتباطات وكل شي". The "واجهة جميلة" the operator described is the formal **STUDENT CARD layout** in `PORTAL_PARENT_PID_HUB_HTML`: header "STUDENT CARD · بطاقة طالب", year, ID row, avatar placeholder box (currently shows initial letter; designed to hold the student photo), info grid (اسم الطالب / المجموعة / المستوى / الصف / المعلمة / الحالة), hours summary bar, and 5 horizontal action tabs (الحضور / المدفوعات / المناهج / التقييمات / النقاط). The V2 hub (`PORTAL_PARENT_HUB_HTML`) renders a different shape — 6 floating feature cards, no student card, no avatar placeholder, no info grid. Two consecutive misreadings of operator vocabulary caused the regression chain (`d7cc70c` served V2 hub; `3b940c4` corrects to PID hub).
- **Decision**:
  - `/portal/parent` for `role=student` serves `PORTAL_PARENT_PID_HUB_HTML` (formal student card with avatar placeholder + info grid + 5 action tabs). This is the canonical "student card" surface for the logged-in single-child case.
  - Session PID injection mechanism: `__SESSION_PID__` placeholder in the template is resolved server-side from `session.user.linked_student_id` → `students.personal_id`. The rendered HTML carries the PID literal so the page can auto-lookup without manual entry.
  - Pre-paint inline `<script>` in `<head>` reads the injected PID, adds `.has-session-pid` class to `<html>`, exposes `window._SESSION_PID`. CSS rule `html.has-session-pid #lookup-card{display:none !important}` suppresses the PID lookup form before first paint — no flash.
  - `phBoot()` precedence: session PID (injected) → URL `?pid=` (deep-link) → focus input (anonymous fallback).
  - Action tabs build hrefs via a `DIRECT_HREF` JS map → `/portal/parent-hub/{attendance,payments,curriculum,evaluations,points}` directly when `window._SESSION_PID` is set (no detour through `/parent/legacy`). Anonymous fallback to `/parent/legacy?pid=<X>#anchor` preserved for deep-link traffic.
  - `role=parent` (V1 multi-child via `linked_parent_for` JSON) continues serving `PORTAL_PARENT_HTML` unchanged.
  - The V2 hub template (`PORTAL_PARENT_HUB_HTML`) is **not** removed — it remains in source for the one-release-cycle revert safety net per ADR-017's discipline.
- **Alternatives considered**:
  - Keep `PORTAL_PARENT_HUB_HTML` (V2 hub) per ADR-018 (rejected — operator explicitly described the formal STUDENT CARD as the "واجهة جميلة" they want preserved; the 6-floating-card layout does not match their description).
  - Build a third template combining both shapes (rejected — `PORTAL_PARENT_PID_HUB_HTML` already exists with the exact layout operator described; duplicating it would be wasteful).
  - Serve `PORTAL_PARENT_PID_HUB_HTML` to both `role=student` AND `role=parent` (rejected — the V1 multi-child shape in `PORTAL_PARENT_HTML` is the established UX for `role=parent`; the single-child card layout doesn't fit the multi-child data contract).
- **Consequences**:
  - Three distinct visible templates now serve `/portal/parent` depending on role + auth state: `role=parent` → `PORTAL_PARENT_HTML` (V1 multi-child); `role=student` → `PORTAL_PARENT_PID_HUB_HTML` (formal student card with session-PID injection); anonymous → 302 `/login` (unchanged from ADR-017). Documented inline in the route handler.
  - The `__SESSION_PID__` injection mechanism + the `.has-session-pid` pre-paint CSS suppression pattern are now first-class techniques for any future logged-in template that wraps a public-PID-prompt UI. Pattern is reusable across other surfaces that have a public-prompt entry but want to skip the prompt when auth state already carries the identifier.
  - The action-tab `DIRECT_HREF` map removes a redirect hop when the session PID is known. Pages load faster and saved bookmarks for `/portal/parent-hub/*` sub-paths still resolve via the existing handlers (restored to direct content in ADR-018).
  - Supersedes ADR-018's `role=student` template choice; the rest of ADR-018 (sub-page handlers serving content directly, bare `/portal/parent-hub` → 302 `/portal/parent`) is unchanged.
- **Reference**: commit `3b940c4` (fix); prior commits `d7cc70c` (wrong-template regression), `3ad90c1` (V1 consolidation), `6a94497` (PID-hub student name + flash kill — the PID-hub layout used here was scaffolded across these commits); safety tag `safety/pre-restore-formal-student-card-20260516-010728`; verification harness `scripts/personas/parent_portal_walk.py` (committed in `e51642b`). Prod SHA `3465c6f3eeda` (final state after follow-on attendance-500 fix `3465c6f`). Operator quote (regression report): "خربت منصة ولي الامر التي كانت تعرض معلومات الطلبة بشكل منسخق ... كان كل طالب تظهر له واجهة جميلة مكتوب فيها معلوماته الاساسية من اسمه ورقم مجموته ومكان لصورته والازرار بشكل منظم".

### ADR-020: Red + confirm logout button is canonical across ALL parent surfaces; bare-purple logout adjacent to a back link is forbidden
- **Date**: 2026-05-16
- **Status**: accepted (cross-links ADR-019; closes the parent-portal UX-trap chain that ran 3b940c4 → 3465c6f → f6aee45)
- **Context**: Three operator escalations in a single parent-portal session, each reporting that "all buttons on /portal/parent kick us out to the login screen". The first two escalations were diagnosed as routing / data-load failures (templates dispatched per role, attendance API 500). The third escalation revealed a separate UX disaster: the parent surface templates shipped a bare purple `<a href="/logout">خروج</a>` link styled identically to navigation pills, sitting adjacent to "← العودة للبوابة" with no confirm guard. On `PORTAL_PARENT_HTML` (V1, `role=parent`) the topbar had ONLY that single clickable button, so when operator said "ALL buttons throw us out" the statement was literally accurate — there was one button and it was logout. On the 6 sub-pages (`PORTAL_PARENT_ATTENDANCE/PAYMENTS/MESSAGES/EVALUATIONS_HTML` + `PORTAL_STUDENT_HTML` + `PORTAL_BOOKS_HTML`) the bare logout link sat adjacent to the back link with identical purple styling — visually indistinguishable from a benign nav action. Operator quote (third escalation in the same session): "لازالت الازرار في منصة ولي الامر اذا نضغط عليها تخرجنا وترجعنا لصفحة تسجيل الدخول من جديد. اين الايجنتس الذي يختبر بشكل واقعي؟؟؟". The earlier commits `3b940c4` (formal student-card layout) and `3465c6f` (attendance API repair) had already received the red+confirm logout pattern on `PORTAL_PARENT_PID_HUB_HTML`, but the same fix was never applied to V1 or the sub-pages. The escalation chain stopped only when a hostile-mode persona walk explicitly tested BOTH `student_test` AND `parent_test` sessions on `/portal/parent` and walked all 6 sub-pages — at which point the bare-purple-pill UX trap surfaced.
- **Decision**:
  - **Canonical logout button pattern across ALL parent surfaces** — required visual + interaction shape:
    - CSS: `background: linear-gradient(135deg, #c62828, #e53935)` (red, destructive palette per DESIGN_LOG state-color spec; same destructive flavor as `#c62828` already used for absent/overdue states).
    - Icon: `🔒` prefix glyph in the visible label ("🔒 تسجيل الخروج").
    - Confirm guard: `onclick="return confirm('هل تريد تسجيل الخروج من منصة ولي الأمر؟')"` — JS-level confirm before the `/logout` navigation. Returns false → click cancelled.
    - Geometrically separated from benign navigation links (no adjacency to `← العودة` back links with matching styling).
  - **Forbidden**: bare purple `<a href="/logout">خروج</a>` (or any auth-clearing endpoint) styled like navigation, with no confirm guard, sitting adjacent to a back link. This is the exact trap that produced three operator escalations in one session.
  - **Sub-pages carry NO logout link.** Only the main hub topbar carries the logout button. Sub-pages have ONLY the "← العودة للبوابة" back link. The rationale: a parent navigating away from a feature sub-page wants to return to the hub, not log out; making both actions available at the sub-page topbar creates the misclick trap. Logout is intentional, deliberate, single-source.
  - **Surfaces affected** (all using the canonical pattern):
    - `PORTAL_PARENT_HTML` (V1, `role=parent`) — replaced bare purple logout pill in topbar (`app.py:77869`) with red+confirm.
    - `PORTAL_PARENT_PID_HUB_HTML` (formal student-card, `role=student`) — already had the pattern from prior commits; unchanged.
    - `PORTAL_PARENT_HUB_HTML` (V2 6-card hub, dead code per ADR-018/019 but kept in source per ADR-017 one-release-cycle revert safety net) — defensively patched with the same pattern so a future route rewire can't reintroduce the trap.
    - 6 sub-page templates (`PORTAL_PARENT_ATTENDANCE_HTML`, `PORTAL_PARENT_PAYMENTS_HTML`, `PORTAL_PARENT_MESSAGES_HTML`, `PORTAL_PARENT_EVALUATIONS_HTML`, `PORTAL_STUDENT_HTML`, `PORTAL_BOOKS_HTML`) — bare logout link removed entirely; only back link remains.
  - **Exception** — `PORTAL_PARENT_HTML` rendered for `role=teacher` at `/teacher/hub` keeps its bare "خروج" link unchanged. That page has no adjacent "back" link, so the misclick hazard does not apply. The trap is specifically about adjacency-with-identical-styling, not about logout links in general.
- **Alternatives considered**:
  - Keep bare-purple logout but add `onclick` confirm only (rejected — visual distinctness is half the antidote; relying on JS confirm alone fails operators who reflexively click-through dialogs, and fails entirely if JS is disabled).
  - Move logout to a hamburger menu / overflow drawer (rejected — adds a layer of navigation operator must learn; the red+confirm pattern keeps logout one-click-away but unmistakable).
  - Apply red+confirm only on V1 + student-card, leave sub-pages untouched (rejected — sub-page logout adjacency was the actual misclick trap; removing it entirely is cleaner than recoloring it).
  - Different palette (orange / dark gray instead of red) (rejected — `#c62828` is already the established destructive state color across the portal per DESIGN_LOG; reusing it preserves visual consistency).
- **Consequences**:
  - The red+confirm pattern becomes the project-wide canonical shape for any destructive navigation link (logout, account deletion, irreversible state changes). Future surfaces that introduce auth-clearing links must follow this pattern OR pass through `feature-protector-agent` + `catastrophe-prevention-agent` (Category 5 — UX disaster) for an explicit exception.
  - Sub-pages across the parent portal are simpler — single back-link in the topbar, no destructive action exposure at the leaf level. Logout flow is exclusively top-of-hub.
  - The hostile-mode persona walk pattern (commit `27ca5ba`, `scripts/personas/hostile_parent_portal_logout_hunt.py`) is now the canonical pre-deploy check for any change touching parent-portal templates — it aggressively enumerates every clickable element on `/portal/parent` and the 6 sub-pages across BOTH role-dispatched templates (student_test + parent_test), flagging any path that reaches `/login` or `/logout` without user confirmation. Re-run before any future change to parent template dispatch or topbar navigation.
  - `real-user-tester-agent` invocation discipline updated: when testing a URL that serves different templates per role (the `/portal/parent` role-dispatch case from ADR-019), the agent MUST walk EVERY persona whose login lands on that URL — not just one. Logged separately in `BUGS_LOG.md` as the persona-x-template coverage rule.
- **Reference**: commit `f6aee45` (fix); prior commits `3b940c4` (student-card logout already patched; pattern source), `3465c6f` (attendance API repair — exposed the latent UX trap by making the sub-pages reachable again), `27ca5ba` (hostile-mode persona harness committed). Safety tag `safety/pre-fix-logout-misclick-v1-20260516-022143`. Prod SHA `27ca5bac980e`. Verification harness `scripts/personas/hostile_parent_portal_logout_hunt.py`. Operator quote (third escalation in the same session): "لازالت الازرار في منصة ولي الامر اذا نضغط عليها تخرجنا وترجعنا لصفحة تسجيل الدخول من جديد. اين الايجنتس الذي يختبر بشكل واقعي؟؟؟". Cross-links: ADR-019 (formal student-card pin at `/portal/parent` for `role=student` — the same template that originally received the red+confirm pattern), ADR-018 (role-dispatched template selection at `/portal/parent`), ADR-017 (V1 consolidation + one-release-cycle template-preservation discipline).

### ADR-021: Orphan books_v2 row → cleanup-orphans (soft-delete), NOT rollback
- **Date**: 2026-05-16
- **Status**: accepted
- **Context**: After commit `0fc833f` (friendly missing-file UX) shipped, the operator reported "ALL books show the missing_file page" and asked whether to roll back. Diagnosis (`/api/books/storage-check` + admin list) showed only ONE active row in `books_v2` (book id 53, title "1", uploaded 2026-05-15 by `010307885`). That single row's `file_path` was `/opt/render/project/src/data/books_v2/53_1.pdf` — the ephemeral repo path that gets wiped each deploy, not the persistent disk at `/var/data/books_v2`. So every parent who tried to open any book in the table was hitting that one broken row. Pre-deploy: the same row returned raw JSON 410. Post-deploy: same row, same 410, friendlier HTML page. The visual sharpness of the new page made one broken row look like a fleet-wide failure.
- **Decision**: Soft-delete the orphan row via `POST /api/books/cleanup-orphans`. Keep commit `0fc833f` in place. Once the parent UI shows an honest empty state, the operator re-uploads the PDF through `/admin/books` — that flow writes into `/var/data/books_v2/` (current code; the ephemeral-fallback bug was fixed earlier per the docstring in `_books_v2_storage_dir`).
- **Alternatives considered**:
  - **Roll back `0fc833f`** (`git reset --hard safety/pre-missing-file-ux-20260516-105201`) — rejected. The new HTML page is not the bug; the orphan row is. Rolling back restores the ugly JSON without fixing the broken book. The exact same parent experience, just less polished.
  - **Re-upload over the existing row id 53** (via `/api/books/<bid>/reupload`) — viable but heavier (multi-megabyte upload through the operator's browser) and requires the operator to do it immediately. Cleanup-orphans is instant and reversible, and the operator can re-upload at their own pace as a brand-new row.
  - **Manual `UPDATE books_v2 SET file_path='...' WHERE id=53` to a corrected path** — rejected. The file on the persistent disk doesn't exist either (storage-check returned `missing: 0, outside_storage: 1` — meaning the only row IS outside storage; there's no orphan file *inside* `/var/data/books_v2/` to point at).
  - **Hard-delete the row** — rejected. `cleanup-orphans` is `is_deleted=1` only (fully reversible via `UPDATE books_v2 SET is_deleted=0 WHERE id=53` if a path is ever restored), and the orphan row carries audit-useful metadata (uploader, original size, group assignments). Soft-delete preserves it.
- **Consequences**:
  - Confirmed empty state on prod: `storage-check` → `rows: 0`, admin `/api/books` → `count: 0, books: []`, parent curriculum page renders the empty-state copy (`لا توجد ...`) instead of any book card. Direct fetch of `/api/books/53/view` returns HTTP 404 `غير موجود` (row-not-found branch), NOT the 410 missing-file page — so the friendly page no longer fires anywhere.
  - The general lesson: **a polished error page is louder than a raw JSON 410.** Future "UX-only" fixes that make an existing failure mode more visible should be paired with a data audit (`storage-check`-style endpoint) and an operator note about the underlying state. Otherwise the polish itself looks like the regression.
  - Cross-link: BUGS_LOG entry under 2026-05-16 documents the misperception ("polished error → looks like fleet failure") as a recurring class of feedback.
- **Reference**: cleanup commit verified live at 2026-05-16 ~10:54 UTC via `POST /api/books/cleanup-orphans` (admin_test session), response `{count: 1, deleted: [{id:53, title:"1", file_path:".../53_1.pdf"}]}`. Codebase: `_books_v2_send_file` / `_books_v2_send_file_public` (`app.py:89175`, `app.py:89460`) — the 410 callers; `/api/books/cleanup-orphans` (`app.py:91440`) — the soft-delete endpoint; `_books_v2_storage_dir()` — the resolver that fixes future uploads. Related: ADR-001 (single-file architecture), ADR-020 (red+confirm patterns), and the safety tag `safety/pre-missing-file-ux-20260516-105201` kept on origin in case we ever want to compare.

### ADR-022: Per-teacher evaluation coverage — universe = active group students; teacher phone deferred (no schema change)
- **Date**: 2026-05-16
- **Status**: accepted
- **Context**: Admin wanted a per-teacher drill-down on `/admin/teacher-deliveries` showing which students have a monthly evaluation submitted and which are pending, with a "remind teacher" button. Two definitional choices and one constraint shaped the implementation:
  1. **What counts as the "expected universe" of students for a teacher this month?**
  2. **Where does the reminder go — WhatsApp, in-app, or deferred?**
  3. The `users` table has **no `phone`/`whatsapp` column** today, so a phone-targeted `wa.me/<phone>?text=` URL isn't possible without a schema change.
- **Decision**:
  - **Universe = active students in groups currently assigned to that teacher** (via `student_groups.teacher_name` match + `_pm_group_recipients(db, group)` for the active-student filter). Submitted = `evaluations` rows for `(teacher_id, evaluation_month)` with `is_deleted=0`. Pending = universe − submitted. Submitted-but-no-longer-in-universe rows are ignored (they don't appear in either list) so the count answers the admin's actual question: "is this teacher up-to-date on their CURRENT students this month?".
  - **Reminder button opens `https://wa.me/?text=<prefilled body>` in a new tab** with NO phone number. Admin picks the teacher's contact in WhatsApp's chat-picker. Honors the user's preferred reminder channel without adding a schema migration, and matches the existing one-click no-background-job pattern used by the evaluation-to-parent send flow. Long pending lists (>10 names) get a confirm modal first; body capped at 20 names with an "… و N طالبة أخرى" tail to keep URL length under WhatsApp's practical limit.
  - **No DB schema change in this commit.** Adding `users.phone` is a separate decision that needs (a) admin form work to enter/edit phones per teacher, (b) bcrypt-style audit decisions about PII storage, (c) a migration block updating both the `init_db()` CREATE and the `else`-branch ALTER per CLAUDE.md's dual-path schema rule. None of those are blockers for v1.
- **Alternatives considered**:
  - **History-based universe** (every student ever evaluated by this teacher) — rejected. Misses students newly enrolled in the teacher's group this month who haven't been evaluated yet, which is exactly the case the admin needs to catch.
  - **Show both counts** (current + historical) — rejected as v1 clutter. Can add as a tab later if needed.
  - **In-app reminder** (open the existing `tm-req-overlay` modal, prefill with the pending list) — viable, no new deps, but doesn't reach the teacher's phone. The user's preference was WhatsApp; deferring the phone-targeting compromise is the smaller cost than building an in-app-only reminder that doesn't match the request.
  - **Server-side WhatsApp send** (queue a `message_log` row for an external bridge to dispatch) — rejected. Existing parent-message flow uses the "click → wa.me opens, admin clicks send" pattern, not a background sender. Matching that pattern keeps mental models consistent.
  - **Add `users.phone` column now** + targeted `wa.me/<phone>?text=` URL — rejected for this commit, kept as a follow-up (`pending decision candidates` below). Cost-benefit favored shipping the read-only feature first and adding phone targeting in a follow-up once admins have validated the list is what they wanted.
- **Consequences**:
  - The summary endpoint's worst-case query count is `O(unique_groups)` for `_pm_group_recipients` calls + 4 fixed queries (users, student_groups, submissions, plus the per-group calls). On current prod (~50 groups, ~10 teachers) that's well under 60 queries per page-load — fine. If group count grows to thousands the per-group call should be batched into a single SQL with grouping; not needed today.
  - The reminder UX has one extra step (admin picks contact in WhatsApp picker) compared to a phone-targeted URL. Acceptable for v1; documented in the button's `title` attribute ("افتح واتساب مع نص جاهز — اختر جهة المعلمة من القائمة").
  - The plan doc (`docs/plans/2026-05-16-teacher-evaluation-coverage.md`) records the deferred phone column as the natural follow-up; do it when an admin asks for one-click reminders.
- **Reference**: commits `7c63c37` (backend), `9b00b85` (UI list), `f65f492` (reminder). Safety tag `safety/pre-teacher-eval-coverage-20260516-124334`. Plan: `docs/plans/2026-05-16-teacher-evaluation-coverage.md`. Endpoints live under `/api/monthly-evaluations/teachers/coverage` + `/api/monthly-evaluations/teachers/<int:tid>/coverage`. Cross-link: ADR-001 (single-file architecture means UI lives inline in `ADMIN_TEACHER_DELIVERIES_HTML`).

### ADR-023: ad-hoc orphan-student backfill (no admin UI, no migration) — and the security trade-off of leaving PID as permanent password
- **Date**: 2026-05-16
- **Status**: accepted
- **Context**: Operator reported a specific student (200910132 / علي محمد أحمد) "can't log in even with PID/PID". Read-only investigation found that the `students` row existed but no matching `users` row did — and that 30 active students in the recent enrollment cohort (`students.id 4729–5045`) were in the same shape. The existing admin UI `POST /api/admin/parents` only creates the V1-phone-as-username pattern, not the PID-as-username `role=student` pattern these accounts need; the 135 working accounts (like Tasneem) appear to have been bulk-created by an off-repo import script that's no longer in service.
- **Decision**:
  - **Backfill via direct prod SQL**, not via admin UI. Transaction-wrapped INSERT of 30 rows in the Tasneem shape (`role='student'`, `username=personal_id`, `password=sha256(personal_id)`, `linked_student_id=<sid>`, `must_change_pw=1`, `is_active=1`). Ledger of new ids saved to `inserted_ids.txt`. Pre-state snapshot saved to `backups/users_pre-orphan-backfill-20260516-103010.json` (entire users table, JSON; `pg_dump` not available on this Windows box).
  - **Set `must_change_pw=0` after operator request** so parents log in with PID/PID and go directly to `/portal/parent` without the forced change-password step. UPDATE scoped by `id = ANY(<30 ids>) AND role='student'`; idempotent in body (`SET mcp=0 WHERE mcp=1`) so the row that self-onboarded mid-operation was left alone.
- **Alternatives considered**:
  - **Build an admin UI for PID-mode account creation first** — rejected for this incident. The 30 students need login NOW; an admin UI would take a plan + safe_deploy cycle and still need a one-shot to handle the existing 30. Kept as a follow-up (`pending decision candidates`).
  - **Use the existing `POST /api/admin/parents` flow** — rejected. Wrong shape (phone-as-username + random 8-char password). Parents would have to be onboarded with a generated password they don't have; defeats the purpose of the backfill.
  - **Hard-code the 30 inserts in a one-shot migration tag** — rejected. Migrations should be schema operations, not data backfills for a particular cohort; would be reverse-engineerable from `schema_migrations`. Ad-hoc one-shot SQL with backup + ledger is the better fit for an incident response.
  - **Keep `must_change_pw=1`** (force change on first login) — rejected by operator. Operational reasoning: parents are not comfortable with the change-password flow and were calling support; the existing 135 accounts have lived with PID-as-password for the term, so consistency wins over security improvement.
- **Consequences**:
  - **Security trade-off codified**: for these 30 accounts (and the existing 135 that were never forced to change), the `personal_id` is now a permanent password until each parent voluntarily changes it. The PID is semi-public (used as the username everywhere, in attendance, in parent-portal URLs); anyone who knows a child's PID can log into that parent's account. Acceptable for v1 per operator; long-term mitigation is a parent-portal "change password" prompt nag, or a real forgot-password flow.
  - **Rollback artifacts preserved**: `inserted_ids.txt` (149 bytes, ids 3159–3188) + the JSON snapshot. Rollback SQL: `DELETE FROM users WHERE id IN (<list>)`. Window for blind rollback closes the moment any of the 30 parents change their password (since rolling back would wipe their new credentials).
  - **5 students remain un-onboardable**: their `personal_id` is empty/NULL. Staff data-entry to populate; then re-run the same backfill query (idempotent — picks up only rows missing a `users` match).
- **Reference**: incident timeline in CHANGE_LOG entry under 2026-05-16. Working files: `inserted_ids.txt`, `backups/users_pre-orphan-backfill-20260516-103010.json`. Related: ADR-022 (the parent-portal coverage feature that surfaced the orphan as the operator started using it actively). No commit hash because this was data-only.

### ADR-024: Per-teacher coverage detail returns groups[] (not flat submitted/pending) + month picker
- **Date**: 2026-05-16
- **Status**: accepted (supersedes the flat-list shape from ADR-022)
- **Context**: Operator wanted to see WHICH students under WHICH groups still need a monthly evaluation, and to pick any historical month (not just the current one). The flat `submitted[]`/`pending[]` arrays the original detail endpoint returned (commit `7c63c37` per ADR-022) mixed students across all of a teacher's groups, making it hard to see per-group coverage at a glance.
- **Decision**:
  - **Per-teacher detail endpoint returns `groups[]`** each with own `{name, stats, submitted, pending}`. `overall_stats` keeps the across-all-groups totals so the summary endpoint's per-teacher row stays consistent with the detail-endpoint sum. Flat top-level `submitted`/`pending` removed. Empty groups (0 students) skipped — would otherwise render as misleading `0/0 100%`.
  - **Students dedup is first-group-wins**: a student enrolled in two of a teacher's groups appears under the alphabetically-first group only. Preserves the original ADR-022 universe semantics (no double-counting).
  - **New `GET /api/monthly-evaluations/months` endpoint** lists distinct `evaluation_month` from `evaluations`, descending, with the current month always pinned at index 0 even when it has zero data yet. Both coverage endpoints already accept `?month=YYYY-MM` (resolver `_ev_coverage_resolve_month`); no change there.
  - **Frontend month picker** above the teacher list. On change → clear cache, close all rows, refetch summary.
  - **Frontend per-group sub-rows** inside each expanded teacher: same progress bar + emoji + click-to-expand pattern as the outer teacher row. First group expanded by default.
- **Alternatives considered**:
  - **Keep flat shape + add a `group` field per student** (which the original `submitted`/`pending` items already had) — rejected. Forces the frontend to do the per-group GROUP BY in JS, and the per-group `stats` derivation has to be duplicated client-side. Cleaner to do it server-side once.
  - **Show all groups expanded by default** — rejected. A teacher with 10 groups would scroll the page off-screen; first-only matches typical drill-down UX where the most-frequently-needed information is visible immediately.
  - **Backwards-compat: return BOTH `groups[]` AND flat `submitted`/`pending`** — rejected. Atomic commits land via one `safe_deploy`; no real backwards-compat window. Kept a defensive fallback in `tmCovBuildReminderText` only (the wa.me text builder) since reminder text might be invoked against a stale `covDetailCache` if someone hot-reloads the JS mid-session.
- **Consequences**:
  - **Numerical consistency**: outer teacher row's `submitted/total` (from summary endpoint) MUST equal the SUM of group `submitted`/`total` (from detail endpoint). Both use the same `_pm_group_recipients` + `_ev_coverage_submissions` helpers, so this holds by construction. Audit script (if ever needed): compare `summary.teachers[i]` against `sum(detail.groups[i].stats)` per teacher.
  - **Empty-group skip**: a group with 0 active students never appears in the response. If admins ever wonder "why don't I see مجموعة X for this teacher?", the answer is the group exists in `student_groups` but has zero active students this term. The summary's `groups` field (which lists raw group_name assignments) still includes empty ones, so this is detectable.
  - **Mobile responsiveness**: nested expand/collapse means three layers (month picker → teacher row → group row). Tested CSS at the existing 680px breakpoint; both row types stack the progress bar full-width when the viewport is narrow.
- **Reference**: commits `ca993c1` (backend) + `c9f5fd4` (month picker) + `edda6dd` (group rows) + `999665e` (reminder body). Safety tag `safety/pre-teacher-cov-enhancements-20260516-142400`. Plan: `docs/plans/2026-05-16-teacher-coverage-enhancements.md`. Cross-link: ADR-022 (the v1 of this feature; this ADR refines the detail-endpoint shape).

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
- `users.phone` column for one-click teacher WhatsApp reminders (ADR-022 deferred this). Needs admin form for entry/edit + decision on PII storage + dual-path migration block.
