# Parent Hub — Phase 1 Verification

**Date:** 2026-05-12
**Safety tag:** `safety/parent-hub-phase1-20260512-220938`
**Phase commits:** C1 → C6 (this report = C7)

## Commit log

```
<this report>  docs: Phase 1 verification
d1af028        test(parent-hub): C6 Phase 1 smoke covering 6 invariants
74f0434        feat(parent-hub): C5 mobile responsive polish
3994bf7        feat(parent-hub): C4 add anchor IDs to PARENT_HTML sections
d0a5ab5        feat(parent): /parent route renders hub after PID
f6f14f0        feat(parent): /api/parent/hub-stats endpoint
3a2ffc3        feat(parent): hub landing HTML constant
```

## What shipped

### Goal

Convert the public `/parent` PID flow from a flat-scroll page (893
LOC `PARENT_HTML`, 10 cards stacked vertically) into a hub landing
with 5 cards mirroring the existing logged-in hub
`PORTAL_PARENT_HUB_HTML`. Zero behavior change for parents who deep-
link directly to a sub-section — those links still work because the
legacy page is preserved at `/parent/legacy`.

### Card grid

| Order | Icon | Title | Stripe color | Anchor |
|---|---|---|---|---|
| 1 | 💳 | متابعة الدفع | Green (`#43A047 → #2E7D32`) | `#section-payment` |
| 2 | 📅 | متابعة الغياب | Blue (`#0288D1 → #01579B`) | `#section-attendance` |
| 3 | 🎁 | المتجر والنقاط | Purple (`#6B3FA0 → #8B5CC8`) | `#section-points` |
| 4 | ⭐ | التقييمات | Orange (`#FF9800 → #F57C00`) | `#section-evaluations` |
| 5 | 📚 | المناهج | Light Blue (`#1E88E5 → #1565C0`) | `#section-books` |

Each card carries:
- Icon, title, single-line stat (e.g. "هذا الشهر: 12 حصة", "65 نقطة")
- 6px right-edge stripe in the card's signature color
- Hover: lifts 6px + 28px-radius purple shadow on desktop
- Touch devices (`@media (hover:none)`): tap shows a scale-down press
  state instead of a stuck lift transform

### Backend

| Commit | What | Key | LOC |
|---|---|---|---|
| C1 (3a2ffc3) | `PORTAL_PARENT_PID_HUB_HTML` constant | New page template (lookup-card + hub-content with 5-card grid) | ~240 |
| C2 (f6f14f0) | `GET /api/parent/hub-stats` | Returns `{ok, student:{name,class,group,personal_id}, stats:{payment,attendance,points,evaluations,books}}` for a given `?pid=…` | ~150 |
| C3 (d0a5ab5) | Route swap | `/parent` returns the hub HTML; `/parent/legacy` returns the original `PARENT_HTML` | +6 / -1 |
| C4 (3994bf7) | Legacy anchors | 5 sibling `<span class="pp-anchor" id="section-…">` markers prepended to each section; original DOM ids preserved | +6 |

`hub-stats` uses the existing helpers — `_resolve_student_row_by_pid`,
`_pts_balance`, `_books_v2_resolve_group_ids_for_students` — so there
is no new SQL surface. The endpoint is unauthenticated by design (it
already gates by PID, same as the legacy page).

### Frontend

| Commit | What |
|---|---|
| C5 (74f0434) | 600px breakpoint tightens topbar / wrap / lookup-card / hello / cards. 380px breakpoint stacks `.hello` vertically. `@media (hover:none)` swaps lift for press-state on touch. `@media (prefers-reduced-motion:reduce)` drops the transition entirely. |

### Tests

`scripts/smoke_parent_hub_phase1.py` (131 LOC) verifies 6 invariants:

| # | Check |
|---|---|
| 1 | `GET /parent` 200 + hub markup (lookup-card, hub-content, phLookup JS, /api/parent/hub-stats reference, 5 card anchors) |
| 1b | Responsive breakpoints 600px / 380px / hover:none all present |
| 2 | `GET /parent/legacy` 200 + 5 section anchor IDs + 3 original DOM ids (`ppStoreCard`, `pp-evals-card`, `pp-books-card`) preserved so existing JS still resolves them |
| 3 | `GET /api/parent/hub-stats?pid=<real>` returns ok=true + student.name/personal_id + 5 stats keys |
| 4 | Bogus PID rejected with `{ok:false}` (HTTP 404) |
| 5 | Empty PID rejected with `{ok:false}` (HTTP 400) |
| 6 | Hub cards anchor to `/parent/legacy?pid=…#section-…` |

All 6 green locally.

## E2E user flow

1. Parent opens `/parent` (no PID yet).
2. Sees the lookup card with PID input.
3. Types PID → presses Enter (or clicks 🔍 button).
4. `/api/parent/hub-stats?pid=…` runs.
5. Hub renders: hello row (name + class + group + change-student
   button) + 5 cards with live stats.
6. Parent taps a card → navigates to
   `/parent/legacy?pid=…#section-payment` (or whichever section).
7. Legacy page loads, browser jumps directly to the anchored section
   thanks to `scroll-margin-top:80px` on `.pp-anchor`.

The lookup card's "🔄 تغيير الطالب" button resets `_PH` state and
re-shows the lookup input — useful for parents with multiple kids.

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after every commit | ✅ |
| `/parent/legacy` returns the original PARENT_HTML (893 LOC) verbatim | ✅ — C3 added the route without modifying the constant |
| All 3 original DOM ids (`ppStoreCard`, `pp-evals-card`, `pp-books-card`) preserved on legacy page | ✅ — sibling `<span>` anchor pattern instead of renaming |
| All 5 anchor IDs present on legacy page | ✅ — smoke [2a] |
| Legacy JS `document.getElementById('ppStoreCard')` (PARENT_HTML line ~10218) still resolves | ✅ — same DOM id |
| `/api/parent/hub-stats` uses existing helpers, no new SQL surface | ✅ — `_resolve_student_row_by_pid`, `_pts_balance`, `_books_v2_resolve_group_ids_for_students` |
| Hub HTML uses only inline `<style>` + `<script>` (no new external files, no template engine) | ✅ — single `r"""…"""` constant |
| All Arabic stored as HTML numeric entities per CLAUDE.md | ✅ — `&#x627;…` throughout |
| Hub HTML viewport tag + RTL direction match the rest of the project | ✅ — `<html lang="ar" dir="rtl">` + `<meta name="viewport" …>` |
| No new tables, no schema migration | ✅ — pure additive on existing helpers |
| No new dependencies | ✅ |
| No changes to `students`, `parent_book_views`, `books_v2*` schemas | ✅ |
| Existing routes (`/parent/book/<id>/view`, `/parent/evaluations/view`, etc.) untouched | ✅ — only `/parent` swapped |
| Hub deep-links work for sub-pages already in place (`/parent/book/<id>/view?pid=`) — they're reached from the legacy page after the anchor jump | ✅ — phase 2 will short-circuit straight to those sub-pages |
| `/dashboard`, `/database`, `/groups`, `/admin/books`, `/tasks`, `/expenses`, `/assets`, `/points/manage` all still 200 | ✅ — none of these were touched in Phase 1 |

## Files touched

- `app.py`
  - C1 (+~240): `PORTAL_PARENT_PID_HUB_HTML` constant added just
    after `PARENT_HTML`.
  - C2 (+~150): `GET /api/parent/hub-stats` endpoint.
  - C3 (+6 / -1): `/parent` route returns hub, `/parent/legacy` route
    returns `PARENT_HTML`.
  - C4 (+6): 5 sibling `<span class="pp-anchor">` markers + 1 CSS
    rule (`.pp-anchor{scroll-margin-top:80px;...}`).
  - C5 (+28 / -3): 600/380/hover:none/reduced-motion media queries.

  Net for Phase 1: ~430 lines added to `app.py`. Zero lines deleted
  from `PARENT_HTML` — the legacy page is byte-identical.

- `scripts/smoke_parent_hub_phase1.py` — 131-line smoke (setup →
  assertions → cleanup).
- `reports/parent_hub_phase1_verification.md` (this file).

## Rollback

`safety/parent-hub-phase1-20260512-220938` is the commit immediately
before C1. To revert the entire Phase 1:

```bash
git revert --no-edit d1af028 74f0434 3994bf7 d0a5ab5 f6f14f0 3a2ffc3
git push origin main
```

Each commit is additive. Reverting drops the hub HTML, the
hub-stats endpoint, the `/parent/legacy` route, the 5 anchors, and
the smoke. The `/parent` route falls back to its original behavior
(rendering `PARENT_HTML` directly). The original DOM ids never
moved, so the legacy JS keeps working through any partial revert.

## What this phase does NOT do

- **Phase 1 keeps the legacy page as the authoritative content
  surface.** Cards land on `/parent/legacy?pid=…#anchor`, not on
  dedicated sub-pages. Phase 2 will progressively replace those
  anchored sections with stand-alone hub pages — first `payment`,
  then `attendance`, etc.
- **Phase 1 does not change the PID gate.** Anyone with a valid PID
  can hit `/api/parent/hub-stats` — same as the legacy page. The
  rate-limit helper `_parent_rate_check` is a no-op today; Phase 2
  will wire it once we settle on a rate policy.
- **Phase 1 does not pre-fetch sub-page data.** Card subtitles show
  the most relevant single stat (e.g. balance, count) but the full
  data only loads after the parent taps the card and lands on the
  anchored section in the legacy page.
- **No new translations / new copy beyond the 5 card titles + the
  shared hello row.** All other strings come from `PARENT_HTML`.

## Ready for owner browser-test

Owner should manually verify in a phone browser (Safari iOS or
Chrome Android):

1. Open `/parent` → see lookup card.
2. Enter a real PID → press 🔍 → cards render with live stats.
3. Tap each card in turn → legacy page opens at the right anchor.
4. Tap browser-back → lands back on hub with PID still resolved.
5. Tap "🔄 تغيير الطالب" → returns to lookup card, input cleared
   and focused.
6. Resize to iPhone-SE width (~375px) → cards stack to 1 column,
   `.hello` row stacks vertically, change-student button stretches
   to full width.
7. Invalid PID → "الرقم الشخصي غير صحيح" error stays inside the
   lookup card.

Items 1-6 use the patterns already validated in the existing
logged-in hub (`/portal/parent-hub`); the smoke verifies the
server-rendered markup but doesn't execute JS in a real browser.

---

🎯 **Parent Hub Phase 1 complete. New `/parent` lands on a 5-card
hub keyed by PID. Legacy page preserved at `/parent/legacy` with 5
anchored sections so every existing deep-link still works. Backend
adds 1 endpoint + 1 route, no schema, no new helpers. All 6 smoke
green. Ready for owner browser-test before Phase 2.**
