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

### 2026-05-16 — Operator terminology: "منصة" is the EXPERIENCE, not a template name; 6-card parent hub restored

Shipped via commit `d7cc70c` (immediately remediating the empty-منصة regression from `3ad90c1`). See ADR-018 for the role-dispatched template-selection decision, and `BUGS_LOG.md` 2026-05-16 entry "Empty parent منصة after V1-consolidation" for the process lesson.

**Vocabulary clarification (important for future designers):** The operator calls "منصة" the FULL hub experience users see when they tap into the parent-portal — cards, buttons, store, sub-pages, everything wired together. They use "منصة" regardless of which underlying template constant is involved. Two templates carry the burden of being called "منصة" by operator at different times:

- `PORTAL_PARENT_HUB_HTML` — internal Arabic title says "بوابة", but renders the 6-card hub that operator calls "منصة" for `role=student` users (child-PID-as-username single-child case).
- `PORTAL_PARENT_HTML` — internal Arabic title says "منصة", and renders the V1 multi-child points-focused view for `role=parent` users (multi-child via `linked_parent_for`).

**The internal titles are a red herring** — they contributed to a mis-diagnosis in the 2026-05-16 regression. Never map operator vocabulary onto Python identifiers without asking; always confirm the surface the operator is talking about (which URL, which auth state, what they expect to see).

**What users see now (after `d7cc70c`):**

| Visitor state | Entry URL | Resulting page |
|---|---|---|
| Anonymous | `/parent` or `/parent/legacy` | 302 → `/login` (unchanged from ADR-017) |
| Anonymous | `/portal/parent*` | 302 → `/` (login_required gate, unchanged) |
| Logged-in `role=student` | `/portal/parent` | `PORTAL_PARENT_HUB_HTML` — 6-card hub (NEW vs `3ad90c1`) |
| Logged-in `role=parent` | `/portal/parent` | `PORTAL_PARENT_HTML` — V1 multi-child (unchanged) |
| Logged-in any role | `/portal/parent-hub/payments` | `PORTAL_PARENT_PAYMENTS_HTML` (RESTORED) |
| Logged-in any role | `/portal/parent-hub/attendance` | `PORTAL_PARENT_ATTENDANCE_HTML` (RESTORED) |
| Logged-in any role | `/portal/parent-hub/points` | `PORTAL_STUDENT_HTML` — points + متجر (RESTORED) |
| Logged-in any role | `/portal/parent-hub/messages` | `PORTAL_PARENT_MESSAGES_HTML` (RESTORED) |
| Logged-in any role | `/portal/parent-hub/evaluations` | `PORTAL_PARENT_EVALUATIONS_HTML` (RESTORED) |
| Logged-in any role | `/portal/parent-hub/curriculum` | `PORTAL_BOOKS_HTML` (RESTORED) |
| Logged-in any role | bare `/portal/parent-hub` | 302 → `/portal/parent` (URL consolidation, kept from ADR-017) |

**The 6-card hub (`PORTAL_PARENT_HUB_HTML`)** is the canonical "feature surface" for `role=student` users. Each card opens its sub-page directly:
1. **المدفوعات** — payments + installments view.
2. **الحضور والغياب** — attendance ledger.
3. **النقاط** — points balance + history + متجر المكافآت (rewards store; lives inside `PORTAL_STUDENT_HTML`).
4. **الرسائل** — teacher broadcast inbox.
5. **التقييمات** — monthly evaluation form view.
6. **المناهج** — curriculum library (books / PDFs the student is assigned).

The store ("متجر") is reached one level deeper than the hub — operator-facing terminology is "متجر داخل بوابة النقاط" (the store inside the points page). Designers touching the points sub-page should remember the store is the highest-value tile inside it; it must not be regressed when the points page is reworked.

**Verification harness committed:** `scripts/personas/parent_hub_verify.py` walks all 4 test personas (student_test / parent_test / admin_test / teacher_test) and asserts feature-button visibility on every parent surface, with 13 reference screenshots under `scripts/screenshots/20260516-0042..0043*`. Re-run this before any future change that touches parent template dispatch.

### 2026-05-16 — Formal STUDENT CARD restored as `role=student` layout; `__SESSION_PID__` injection + pre-paint CSS suppression + `DIRECT_HREF` tab pattern

Shipped via commits `3b940c4` (formal student-card restoration) and `3465c6f` (follow-on attendance-500 repair). See ADR-019 for the template-selection codification, and `BUGS_LOG.md` 2026-05-16 entries "V2-hub vs PID-hub template mix-up" and "Route-200 ≠ page-works" for the process lessons.

**Canonical `role=student` layout** at `/portal/parent` is now `PORTAL_PARENT_PID_HUB_HTML` — the **formal STUDENT CARD** layout:

- **Header**: "STUDENT CARD · بطاقة طالب" + year
- **ID row**: student's personal ID prominently displayed
- **Avatar placeholder box**: currently shows the student's initial letter; designed to hold a student photo when the photo-upload feature lands
- **Info grid** (2-column on desktop, single-column on mobile): اسم الطالب / المجموعة / المستوى / الصف / المعلمة / الحالة
- **Hours summary bar**: aggregate hours-attended indicator
- **5 horizontal action tabs**: الحضور / المدفوعات / المناهج / التقييمات / النقاط — each opens its `/portal/parent-hub/<area>` sub-page directly

**Reusable patterns introduced (worth promoting beyond parent-portal):**

#### Pattern 1: `__SESSION_PID__` server-side injection for logged-in single-identifier surfaces

`PORTAL_PARENT_PID_HUB_HTML` is shared between two consumers:
- **Anonymous** at `/parent/legacy?pid=<X>` — deep-link traffic from WhatsApp (now retired per ADR-017 but the template still exists in source).
- **Logged-in** at `/portal/parent` for `role=student` — session carries `linked_student_id`.

For the logged-in case the route resolves the PID server-side from `session.user.linked_student_id` → `students.personal_id` and substitutes it into the template via the `__SESSION_PID__` placeholder. The rendered HTML carries the PID literal so the page can auto-lookup without manual entry. **This is reusable for any logged-in template that wraps a public-prompt UI — render server-side, inject the resolved identifier, let the page auto-skip the prompt.**

#### Pattern 2: Pre-paint inline-script + CSS class suppression (no flash)

```html
<head>
  <!-- pre-paint inline script -->
  <script>
    (function(){
      var sid = "__SESSION_PID__";
      if (sid && sid !== "__SESSION_PID__") {
        document.documentElement.classList.add("has-session-pid");
        window._SESSION_PID = sid;
      }
    })();
  </script>
  <style>
    html.has-session-pid #lookup-card { display: none !important; }
  </style>
</head>
```

The script runs BEFORE the body paints, adds `.has-session-pid` to `<html>`, and the matching CSS rule suppresses the public-prompt card before first paint. No flash, no jump, no visible "anonymous → authenticated" transition.

**Reusable for any template that has a public-prompt UI but wants to skip the prompt when auth state already supplies the identifier.** The trick is: put the script in `<head>` BEFORE the stylesheet, put the suppression rule INLINE in `<head>` (not in an external stylesheet — external would arrive after first paint). Two requirements to remember when reusing:
1. The placeholder substitution check (`if sid && sid !== "__SESSION_PID__"`) is necessary because the literal placeholder string ships in the anonymous template path.
2. The CSS rule must be `!important` because the public-prompt element's own `display:block` rule may override otherwise.

#### Pattern 3: `DIRECT_HREF` action-tab map for logged-in vs anonymous routing

The 5 action tabs in the formal student card use a JS `DIRECT_HREF` map that resolves at click-time:

```js
var DIRECT_HREF = {
  attendance:   "/portal/parent-hub/attendance",
  payments:     "/portal/parent-hub/payments",
  curriculum:   "/portal/parent-hub/curriculum",
  evaluations:  "/portal/parent-hub/evaluations",
  points:       "/portal/parent-hub/points"
};
function tabHref(area){
  if (window._SESSION_PID) return DIRECT_HREF[area];
  return "/parent/legacy?pid=" + encodeURIComponent(currentPid) + "#" + area;
}
```

When the session PID is set, tabs link directly to the logged-in sub-page route. When anonymous, tabs fall back to the public `/parent/legacy` flow with a hash anchor. **No redirect hop for the logged-in case** — saves a round-trip and removes a brief "redirecting…" flash.

#### Pattern 4: Defensive `information_schema.columns` fallback for potentially-drifted Postgres schema

Introduced in `api_portal_student_attendance` alongside the `attendance_msg_cols_v1` migration (commit `3465c6f`). The pattern is worth promoting as a general technique for any user-data SELECT that touches columns added after the prod DB's first init:

```python
# Probe whether the column exists in the live table
def _attendance_has_msg_column(db):
    try:
        # SQLite path
        cols = {r[1] for r in db.execute("PRAGMA table_info(attendance)").fetchall()}
        if cols:
            return "message" in cols
    except Exception:
        pass
    try:
        # Postgres path
        cur = db.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'attendance' AND column_name = 'message'"
        )
        return cur.fetchone() is not None
    except Exception:
        return False

# Use the result to shape the SELECT projection
if _attendance_has_msg_column(db):
    sel_msg = "message"
else:
    sel_msg = "'' AS message"
sql = f"SELECT id, student_name, ..., {sel_msg} FROM attendance WHERE ..."
```

**Reusable for any column added via else-branch ALTER** that might not have been included in the migration list when the column was first introduced. The defensive fallback substitutes a typed-empty value when the column is missing, so the query succeeds even on a not-yet-migrated DB. Belt-and-suspenders pattern — the `attendance_msg_cols_v1` migration is the primary fix; the column probe is the failsafe.

**Verification harnesses committed (commit `e51642b`):** `scripts/personas/parent_portal_walk.py` (formal-card layout walk for 4 personas — asserts STUDENT CARD header, avatar placeholder, info grid labels, 5 action tabs visible) and `scripts/personas/verify_parent_hub_tabs.py` (5-tab navigation + API health walk — asserts every sub-page route returns 200 AND every underlying XHR returns non-5xx). Re-run both before any future change that touches parent template dispatch OR the attendance / payments / evaluations API endpoints.

### 2026-05-16 — Red+confirm logout button canonized across parent surfaces; bare-purple logout adjacent to a back link is now forbidden

Shipped via commits `f6aee45` (fix across V1 + 6 sub-pages + dead-code defensive patch) and `27ca5ba` (hostile-mode persona harness). See ADR-020 for the design contract, and `BUGS_LOG.md` 2026-05-16 entries "Same bug, different template" and "Misclick trap: bare-purple logout adjacent to a back link" for the process lessons.

**Canonical destructive-action button pattern** (project-wide reusable; applied first to logout, but the shape is intended for any irreversible destructive action — account deletion, payment cancellation, etc.):

```html
<a class="logout-btn"
   href="/logout"
   onclick="return confirm('هل تريد تسجيل الخروج من منصة ولي الأمر؟')"
   style="background: linear-gradient(135deg, #c62828, #e53935);
          color: #fff;
          padding: 8px 14px;
          border-radius: 8px;
          font-weight: 700;
          text-decoration: none;">
  🔒 تسجيل الخروج
</a>
```

Required components (all three, no exceptions):
1. **Destructive palette** — `#c62828` red gradient (matches DESIGN_LOG state-color spec for destructive / overdue / absent semantics; reuses an established color rather than introducing a new one).
2. **Icon prefix** — `🔒` (or equivalent destructive glyph) visible in the label. The icon does half the work of distinguishing destructive from benign even before color is read.
3. **JS `onclick` confirm guard** — `return confirm(...)` blocks the navigation until operator confirms. Arabic copy is mandatory for parent surfaces ("هل تريد تسجيل الخروج من منصة ولي الأمر؟"); equivalent Arabic copy required for any other destructive action.

Forbidden anti-pattern (this is the exact trap that caused three operator escalations in one session):

```html
<!-- DO NOT DO THIS -->
<a class="logout" href="/logout">خروج</a>
```

— bare logout link, purple navigation styling matching adjacent benign nav pills, no icon, no confirm guard. The trap is **adjacency-with-identical-styling**: when a logout link sits next to a "← العودة" back link with matching color/radius/padding/font, human eyes pattern-match by visual treatment first and read labels second. The labels stop being the determining factor.

**Sub-pages carry NO logout link.** Only the main hub topbar of each role's template carries the destructive action. The 6 parent sub-pages (`PORTAL_PARENT_ATTENDANCE_HTML`, `PORTAL_PARENT_PAYMENTS_HTML`, `PORTAL_PARENT_MESSAGES_HTML`, `PORTAL_PARENT_EVALUATIONS_HTML`, `PORTAL_STUDENT_HTML`, `PORTAL_BOOKS_HTML`) have ONLY the "← العودة للبوابة" back link in the topbar. Logout exists exclusively at the hub level — single source, deliberate, unmistakable. Rationale: a parent navigating away from a feature sub-page wants to return to the hub, not log out; making both actions available at the sub-page topbar creates the misclick trap. This rule applies project-wide to hub-and-spoke UX patterns.

**Role-x-template duality at `/portal/parent`** — design discipline note:

The URL `/portal/parent` serves **different templates for different roles** (per ADR-018/019):

| Role | Template | Layout shape |
|---|---|---|
| `role=parent` | `PORTAL_PARENT_HTML` (V1) | Multi-child points-focused view; topbar has logout (now red+confirm). |
| `role=student` | `PORTAL_PARENT_PID_HUB_HTML` | Formal STUDENT CARD with avatar placeholder + info grid + 5 horizontal action tabs; topbar has logout (red+confirm). |
| Anonymous | 302 → `/login` | No template served. |

**Both role-dispatched templates must follow the same UX patterns.** Fixing destructive-action discipline on one template is NOT evidence the other is sound. Three operator escalations in one session traced back to this: prior commits patched only `PORTAL_PARENT_PID_HUB_HTML` (formal student-card) and left `PORTAL_PARENT_HTML` (V1) with the bare-purple-pill trap. Any change to parent-portal UX (palette, topbar layout, destructive actions, navigation structure) must be applied to BOTH templates simultaneously and verified with a persona-per-role walk.

**Hostile-mode persona harness** (`scripts/personas/hostile_parent_portal_logout_hunt.py`, committed in `27ca5ba`) — re-runnable Playwright walk that exercises BOTH `student_test` AND `parent_test` sessions on `/portal/parent` and all 6 sub-pages, aggressively enumerating every clickable element and flagging any path that reaches `/login` or `/logout` without user confirmation. The probe handles its own session preservation by treating `/logout` and `/api/logout` as `SESSION_KILLERS` that must not be probed via the shared cookie context. Re-run before any change to parent-portal templates or topbar navigation. The hostile-walk pattern is reusable for any UX-trap-prone surface (admin DDL controls, payment refunds, irreversible bulk operations).

**Exception** — `PORTAL_PARENT_HTML` rendered for `role=teacher` at `/teacher/hub` keeps its bare "خروج" link unchanged. That page has no adjacent "back" link, so the misclick hazard (adjacency-with-identical-styling) does not apply. The rule is specifically about adjacency, not about logout links in general.

### 2026-05-21 — G13 parent/student portal simplification: analytics removed

Operator-driven UX cleanup (commits `3a12493` / `4c36ab4` / `a8c1071` / `dd3584f`). Four widgets stripped from the parent-facing surfaces; Chart.js CDN tag dropped from `<head>` of both templates. See ADR-031.

Removed from `PORTAL_PARENT_PID_HUB_HTML` (formal student-card, `role=student`):
- **المستوى row** in the student info grid — hidden via inline `display:none` on `#card-level`. Element + JS binding preserved so `phRenderHub` doesn't null-deref; data still flows from `/api/parent/hub-stats`.

Removed from `PORTAL_STUDENT_HTML` (points-tab view at `/portal/parent-hub/points`):
- **"ملخص هذا الأسبوع"** 3-card weekly summary block — section deleted entirely.

Removed from BOTH `PORTAL_STUDENT_HTML` AND `PORTAL_PARENT_HTML`:
- **"آخر النشاطات"** activity-feed cards — section deleted entirely. The admin-side `/dashboard` "آخر النشاطات" widget (`/api/dashboard/recent-activity`) is preserved unchanged.
- **"تطوري خلال 8 أسابيع" / "التقدم خلال آخر 8 أسابيع"** 8-week chart sections — HTML deleted, `drawChart` / `drawCharts` functions deleted, Chart.js `<script src=...>` line dropped from `<head>`. Page weight on parent surfaces drops by ~80KB.

Chart.js is still loaded by `/dashboard`, the parent evaluations page, and the reports tab — the CDN is not gone from the app, just removed from the parent templates where unused.

**Design principle codified**: analytics widgets belong on admin surfaces (dashboard, reports), not on parent surfaces. Parent-facing pages are "card + action tabs" — single hero, clear actions, no decorative metrics. Any future analytics-feature ask on the parent side has to explicitly re-litigate ADR-031.

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
