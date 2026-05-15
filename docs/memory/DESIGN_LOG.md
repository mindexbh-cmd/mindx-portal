# DESIGN_LOG.md

UI/UX evolution log for the mindex-portal codebase. Maintained by `memory-keeper-agent`. Sources: commits touching `*_HTML` template constants, palette / spacing / layout discussions, dashboard redesign tags.

## Visual identity

**Palette** (canonical):
- `#4a148c` — primary purple (brand, headers, primary buttons)
- `#6B3FA0` — secondary purple (hover states, mid-emphasis)
- `#8B5CC8` — lighter accent (introduced in points board)
- State colors: `#2e7d32` (success/paid/present), `#c62828` (destructive/absent/overdue), `#f57f17` (warning/late), `#1565c0` (info)
- Neutral grays: `#f5f5f5`, `#e0e0e0`, `#9e9e9e`, `#424242`

⚠️ Palette drift detected in `POINTS_BOARD_HTML` (May 2026): introduced `#fce4ec`, `#e1bee7`, `#bbdefb`, `#c4a8e8`, `#ede7f6`, `#faf7ff`, `#f3e5f5`, `#f8f3ff` — purple/lavender derivatives that diluted the canonical pair. Flagged by `ui-designer-agent` review. Cleanup deferred.

**Typography**: System font stack `-apple-system, Segoe UI, Tahoma, Arial`. Body 14-16 px (mobile floor 14, iOS-zoom-safe inputs at 16). Section headers 18-20 px / 600. Page titles 22-24 px. No custom @font-face.

**Spacing rhythm**: 4/8/12/16/20/24/32/40/48/64 px. Drift values like 6/7/22 px have appeared and been flagged.

**Border-radius**: drift detected — 6, 8, 9, 10, 14, 16 all used. No canonical ladder established.

## Major design events

### 2026-04-29 — Full dashboard redesign
Safety tagged: `dashboard-restyle-safepoint-20260429-160915`, `dashboard-full-redesign-20260429-165722`. Significant rework of the post-login landing page; specifics not extracted from commits at write time.

### 2026-04-28 → 04-29 — Attendance UX wave
Multiple commits in close succession:
- Attendance anomaly warning
- Attendance completeness check
- Attendance summary block
- Attendance empty-status fix
- Attendance students-and-scroll fix
Safety tags: `pre-attendance-anomaly-warning-20260428-1754`, `pre-attendance-completeness-check-20260428-1923`, `pre-attendance-empty-cleanup`, `pre-attendance-empty-status-fix`, `pre-attendance-students-and-scroll-fix-20260429-1913`, `pre-attendance-summary-block-20260428-1726`.

### 2026-05-04 — Points board kid-facing redesign
Adds the gamified card grid with avatar + balance + level + per-student session-points badge. Pulse animations on grant. Sticky toolbar + sticky budget bar. Hover-lift on cards. Distribute-evenly modal (⚖️). Stats modal (📊). Behaviors picker bottom-sheet.

### 2026-05-04 — Egg-hatch mechanic
"فقس البيوض" class-wide hatch button on points board. Avatar reveal animation. Per-student egg balance tracked separately.

### 2026-05-08 → 05-11 — Parent shop ground-up
Card-based redemption shop in parent hub. Prize tile dimensions iterated multiple times (110px→200px height for landscape, 90px→150px height for portrait — the bumped commits are in `BUGS_LOG.md`). Image-fit changed to `contain` so portrait prizes don't crop badly. "اطلب الآن" button auto-disables when student lacks points.

### 2026-05-12 — Parent hub navigation polish
PID-preserving back button across all hub pages (evaluations, payments, books). Without this, parents had to re-enter their child's CPR each time they bounced between sections.

### 2026-05-13 — Books library tile UI
Empty-state buttons added ("ارفع أول كتاب" / "إنشاء أول مجلد"). Folder grid card design. Custom PDF viewer page (`/parent/book/<bid>/viewer`) introduced — a page-image renderer using `pypdfium2` to strip the Chrome PDF toolbar's download button for view-only access.

### 2026-05-14 — Push UI
Admin send-panel landed on `/points/manage`. Smart-timing permission prompt (asks at the right moment, not on first load). History table on the admin dashboard. Notification action buttons (v3.2.3 SW). Heads-up urgency category for time-sensitive payloads.

### 2026-05-14 — TWA / Android app
PWABuilder Bubblewrap pipeline. Status bar matches `theme_color` (`#4a148c`). `assetlinks.json` route at `/.well-known/assetlinks.json` driven by `TWA_SHA256_FINGERPRINT` env var.

### 2026-05-15 — Unified-login parent direct-nav (login hint + redirect rules)

UX cleanup so authenticated parents/students don't see the redundant public CPR prompt on `/parent`. Shipped via commits `31499e9` (route guards) + `3712968` (login hint) + `5ecf19d` (plan/handoff). See ADR-014 for the A-vs-B decision.

**New Arabic hint on the login form** (`LOGIN_HTML` at `app.py` ~9700, rendered below the submit button, entity-encoded per ADR-002):

> أولياء الأمور: استخدم الرقم الشخصي للطالب اسم مستخدم

Plain Arabic: "Parents: use the student's personal ID as username". Sits as a small caption — same neutral color the form already uses for secondary text; no new palette entry introduced.

**Redirect rules on `/parent` and `/parent/legacy`** (`app.py` ~28800 and ~28825):

| Visitor state | Behavior |
|---|---|
| Anonymous (no `session["user"]`) | Unchanged — public CPR prompt rendered. Preserves legacy WhatsApp deep-link compatibility. |
| Authenticated, `role=student` | 302 → `/portal/parent-hub` |
| Authenticated, `role=parent` | 302 → `/portal/parent` |
| Authenticated, any other role | Unchanged — public CPR prompt rendered (admin/teacher visiting the parent surface still sees the public form). |

No new CSS, no new component. Pure backend redirect + one inline-template text addition.

### 2026-05-15 — `feature-protector-agent` makes the feature surface a first-class design contract

Shipped via commit `316d84d`. No visual change to the portal itself; this entry captures the fact that the UX/feature surface is now a contractually-enforced object.

**Three-phase agent workflow** (`.claude/agents/feature-protector-agent.md`):
1. **Pre-change audit** — diff vs `docs/memory/FEATURE_INVENTORY.md`. Which of the 502 routes / which shared helpers / which inline `*_HTML` templates does this change touch? Anything in the top-20 critical list?
2. **Verdict** — `APPROVE` (no risk), `APPROVE WITH CONDITIONS` (proceed only after listed test obligations), or `REJECT` (stops the coordinator outright). Veto power.
3. **Post-change verification** — assertions re-checked after merge. Inventory updated incrementally with any new/renamed routes.

**Top-20 critical features now functioning as design invariants** ("must hold after any change", quoted from `FEATURE_INVENTORY.md`):
The agent's top-20 list captures the load-bearing UX surfaces — login, attendance entry, the parent shop checkout, books_v2 chunked upload, the points board, parent hub navigation, the curriculum library access checks, the taqseet ↔ student_payments mirror, the dashboard tiles, the database editor, the import pipeline, and the `/portal/parent-hub/*` page chain. Each carries an explicit assertion of expected behavior. Breaking one is a REJECT, not a discussion.

**What this means for designers / future UI work:**
- Visual reskins of any top-20 surface still need to preserve the listed assertions (e.g. "اطلب الآن disables when student lacks points" for the parent shop redemption tile — already documented in `BUGS_LOG.md` as a fix worth not regressing).
- Adding a new top-20-tier feature means appending an assertion to `FEATURE_INVENTORY.md` in the same commit so the contract is recorded the moment the surface ships.
- Removing a feature is a deliberate act: drop its tables in the same commit (CLAUDE.md "Table creation policy"), drop its routes, drop its inventory entry, log the deprecation here and in `CHANGE_LOG.md`.

The 502-route catalog also doubles as a coverage map for `/audit` runs and persona walk-throughs — `real-user-tester-agent` can cross-reference its persona scripts against the inventory to ensure no critical path is uncovered.

### 2026-05-15 — `catastrophe-prevention-agent` 5-category disaster model + `override:catastrophe:` bypass convention

Shipped via commit `43b52d3`. No visual change to the portal itself; this entry captures the design-level invariant that every change is now reviewed against a 5-category disaster taxonomy before it can ship.

**The 5 categories** (any one tripping → REJECT, agent runs FIRST in the coordinator pipeline):

1. **Data loss** — any DROP / TRUNCATE / DELETE-without-WHERE / column-rename / table-rename / migration that could destroy or orphan user rows. Overlaps with `data-protector-agent` (ADR-007) but catastrophe-prevention treats it as a project-level disaster, not just a DB concern.
2. **Breaking changes** — schema changes called out by N+ existing routes, removed endpoints, renamed signatures, deleted shared helpers, modified inline `*_HTML` template constants that other features depend on.
3. **Security** — auth-bypass shapes, secret leaks (rnd_/ghp_/sk-), unbounded admin-impersonation, SQL constructed via f-strings, missing `@login_required` on data endpoints, `eval()` / `exec()` on user input, CORS gone wild.
4. **Performance** — p95 budget threats: queries inside loops, missing indexes on filter columns, megabyte-class responses, missing pagination, blocking calls on the request thread, OOM-risk allocations on the 512 MB Render Starter plan.
5. **UX disasters** — adoption-killing regressions: parent shop checkout broken, attendance entry gone, books_v2 viewer broken, login broken, RTL layout flipped, Arabic-entity decoding regressed. Top-20 invariants in `FEATURE_INVENTORY.md` are inputs here.

**The `override:catastrophe:<reason>` bypass convention** — codified as the only path past the PreToolUse Bash hook `catastrophe_block.py`. Operator includes the literal tag inline in the command (e.g. `git push --force-with-lease  # override:catastrophe:rebase-after-secret-scrub`). Hook logs the bypass with reason. No silent override path exists. Documentation/test commands that need to MENTION a dangerous pattern as data (e.g. `echo "never DROP TABLE users"`) also require the tag — defense-in-depth, no false-negative carve-outs.

**Why this matters for design / UX work:**
- A REJECT verdict cannot be argued past by any other agent or by the coordinator. Only the human owner overrides. This makes the 5 categories functionally an inviolable design contract — a UI redesign that breaks the parent shop checkout flow gets stopped here even if every other reviewer approves.
- The two demo audits (`docs/audits/catastrophe-check-delete-books-v2-20260515-204654.md` and `catastrophe-check-add-footer-slogan-20260515-204654.md`) serve as the canonical examples of REJECT vs APPROVE shape — future designers can read them to calibrate what reads as catastrophic vs purely additive.

### 2026-05-16 — Parent UX consolidated onto منصة V1; بوابة V2 entry points retired

Shipped via commits `6a94497` (PID-hub student name + flash kill) and `3ad90c1` (V1 consolidation). The visible parent surface across the portal is now exactly one template — `PORTAL_PARENT_HTML` at `/portal/parent`. See ADR-017 for the A-vs-B-vs-keep-both decision.

**What users see now:**

| Visitor state | Entry URL hit | Resulting page |
|---|---|---|
| Anonymous | `/parent` or `/parent/legacy` | 302 → `/login` (no more public CPR prompt) |
| Anonymous | `/portal/parent-hub*` (any of 7 routes) | 302 → `/` (login_required gate) |
| Logged-in `role=parent` | `/login` → dispatch | `/portal/parent` (V1) |
| Logged-in `role=student` (child PID as username) | `/login` → dispatch | `/portal/parent` (V1, single-child render) |
| Logged-in any role | `/portal/parent-hub*` (saved bookmark) | 302 → `/portal/parent` |
| Logged-in any role | `/parent` or `/parent/legacy` | 302 → `/portal/parent` |

**Login page** (`LOGIN_HTML`): the Arabic hint "أولياء الأمور: استخدم الرقم الشخصي للطالب اسم مستخدم" (shipped 2026-05-15 in `3712968`) is now removed — it was V2-flow-specific and contradicts the V1 dispatch story. Login form returns to its pre-2026-05-15 shape (no parent-specific caption).

**V1 template now serves two role shapes** without any visual change:
- `role=parent` — multi-child render driven by `linked_parent_for` JSON array; existing UX preserved.
- `role=student` — single-child render driven by `linked_student_id` foreign key. The child's display name and points/payments/evaluations sections all populate from the one linked `students` row. No new visual treatment introduced; the template renders the same card grid and points tiles as it does for a single-child parent.

**Templates intentionally kept in source for one release cycle** (revert safety net per ADR-017): `PORTAL_PARENT_HUB_HTML`, `PORTAL_PARENT_PID_HUB_HTML`, `PORTAL_PARENT_ATTENDANCE_HTML`, `PORTAL_PARENT_PAYMENTS_HTML`, `PORTAL_PARENT_MESSAGES_HTML`, `PORTAL_PARENT_EVALUATIONS_HTML`, `PARENT_HTML`. They are unreachable through the routing table (every entry returns 302 to V1) but still parseable Python string constants. Will be physically removed in a follow-up after prod soak. The 2026-05-16 `6a94497` PID-hub fixes (student-name row in `PORTAL_PARENT_PID_HUB_HTML` + `.has-deeplink-pid` flash kill in `PARENT_HTML`) are now mostly moot at the routing layer, but they remain valuable if a revert is needed.

**Parent shop, books library, push notifications, evaluations** — all still reachable; the V1 template links to them via its existing tile grid. The retirement is of the V2 *hub navigation chrome*, not of the underlying features.

## Component patterns

### Cards (parent shop, points board, books)
- White background, 14 px border-radius, soft purple shadow `rgba(107,63,160,.12)`
- Hover-lift via `translateY(-2px)` + deeper shadow
- Selected state outlined in `#6B3FA0` with `.faf7ff` background

### Modals (across the app)
- Full-screen on mobile (`<= 600px`), centered max-width on desktop
- Header bar in a gradient: `linear-gradient(135deg, #6B3FA0, #8B5CC8)` for purple flavor, `linear-gradient(135deg, #43A047, #2E7D32)` for green (distribute), `linear-gradient(135deg, #FB8C00, #FF8F00)` for orange (stats)
- Close button is the unicode glyph in white, no SVG

### Buttons
- Primary: gradient fill, white text, 9-10 px radius, 14 px font-weight 600-700
- Secondary: white background, gray border, gray text
- Bar-action (compact): pastel bg + matching border, 5-7 px padding (⚠ may be below 44px touch target)

### Status pills (attendance, payments)
- 999 px radius (capsule)
- Colored fill matching status semantics

## Known design debt

From `ui-designer-agent` + `mobile-first-agent` reviews (recent):

1. **Palette drift in `POINTS_BOARD_HTML`** (above).
2. **Touch targets below 44 px** on `.btn` (32 px), `.pb-bar-action` (28 px), `.menu-tabs button` (40 px).
3. **Border-radius inconsistency** — 6/8/9/10/14/16 all in one file.
4. **Spacing drift** — 6/7/22 px appear alongside the 4/8/12/16/24 ladder.
5. **`backdrop-filter: blur(8px)` on sticky bars** — GPU-expensive on low-end Android; potential scroll jank.

Cleanup is queued behind feature work. Tracked as candidate audit follow-ups in `docs/audits/` when `/audit` runs.
