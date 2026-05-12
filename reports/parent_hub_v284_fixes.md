# Parent Hub v2.8.4 Fixes — Verification

**Date:** 2026-05-13
**Safety tag:** `safety/parent-hub-fixes-20260513-013000`
**Commits:** C1 → C4 (this report = C5)

## Commit log

```
<this report>  docs: v2.8.4 fixes verification
fd4e6a8        test(parent): v2.8.4 fixes smoke
1b2a0a1        ui(parent): remove 'للموقع الرئيسي' link from hub topbar
198216b        fix(parent): back button keeps PID in hub URL
aa1350e        fix(parent): ppStoreCard only shows for section-points
```

## Issue #1 — Store card leaked into non-points sections

**Reported:** "The store card (ppStoreCard) appears on ALL section
views, not just #section-points."

**Root cause:** `loadStoreMenu` is called by `_ppRender` at the
end of every lookup, fetches `/api/parent/store/menu`
asynchronously, and on success sets `card.style.display = ''`
(app.py:10241). The v2.8.3 `ppSectionOnlyView` walker hides the
store card inline BEFORE the fetch resolves, but `loadStoreMenu`
then revives the card moments later by overwriting the inline
style.

**Fix (aa1350e):** New `injectHideRules(target)` helper inside
the section-only IIFE. When target ≠ section-points, it appends a
`<style id="pp-section-only-hide">` to `<head>` with:

```css
#ppStoreCard { display: none !important; }
```

(Plus `#pp-evals-card` / `#pp-books-card` defensively, in case a
future loader ever revives them async too.)

CSS `!important` wins over later inline-style assignments, so the
async revival is harmless — the card stays hidden as long as the
parent is in section-only mode.

## Issue #2 — Back button dropped the PID

**Reported:** "The 'back to hub' button links to /parent which
restarts the PID lookup."

**Root cause:** `addBackButton` hard-coded `a.href = '/parent'`.

**Fix (198216b):** Two coordinated changes:

1. The back-button href now reads `?pid=` from
   `window.location.search` and constructs
   `/parent?pid=<encoded>` when present, falling back to bare
   `/parent` when not.

2. A new `phBootFromUrl` IIFE in `PORTAL_PARENT_PID_HUB_HTML`
   reads `?pid=` on hub load — if present, pre-fills the input
   AND auto-triggers `phLookup()` so the hub renders the populated
   5-card grid instantly. When no `?pid` is in the URL, the
   previous autofocus-on-load behavior is preserved unchanged.

End-to-end result: tap any hub card → land on
`/parent/legacy?pid=X#section-Y` (auto-lookup + section-only) →
tap "← العودة" → land on `/parent?pid=X` (auto-rehydrate hub) →
tap a different card → repeat. Single click each step.

## Issue #3 — Unwanted topbar link

**Reported:** "The hub topbar has a 'للموقع الرئيسي' link.
Owner wants it removed."

**Fix (1b2a0a1):** One-line deletion of the `<a href="/">…</a>`
inside the hub's `.topbar` div. The 🏠 h1 stays.

## Coexistence summary

PARENT_HTML's script block now hosts **four** IIFEs at the
bottom, each narrowly scoped + try/catch-guarded:

| IIFE | Ships | Purpose |
|---|---|---|
| `ppBootAutoLookup` | v2.8.1 | Reads `?pid=…` and auto-fires `ppLookup()` |
| `ppToggleFolder` helper | v2.8.2 | Replaces the broken `\'collapsed\'` inline expression |
| `ppSectionOnlyView` | v2.8.3 | Hides non-target sections when URL has `#section-*` |
| `injectHideRules` (in same IIFE) | v2.8.4 | Adds `!important` CSS to defeat the loadStoreMenu race |
| Back-button PID preservation | v2.8.4 | `addBackButton` builds href from `window.location.search` |

`PORTAL_PARENT_PID_HUB_HTML` gains one new IIFE:

| IIFE | Ships | Purpose |
|---|---|---|
| `phBootFromUrl` | v2.8.4 | Reads `?pid=…` on hub load and auto-fires `phLookup()` |

## Smoke results

`scripts/smoke_parent_v284_fixes.py` — 7 invariants, all green:

```
[1] GET /parent/legacy -> 200
[1a] injectHideRules wired with all 3 explicit cards + sections
[2a] back button preserves PID via URLSearchParams
[3a] hub topbar link removed
[3b] hub topbar h1 preserved
[4a] hub phBootFromUrl IIFE wired
[5] PARENT_HTML <script> parses cleanly
[5] HUB_HTML <script> parses cleanly
[6] all 3 prior IIFEs preserved (no regression)
[7] back button falls back to /parent when no PID present
v2.8.4 fixes smoke passed.
```

Prior smokes (Phase1, autolookup, section-only, JS syntax) all
still green.

## E2E owner browser-test checklist

| # | Action | Expected |
|---|---|---|
| 1 | Open `/parent` | Hub renders, PID input focused, NO 'للموقع الرئيسي' link in topbar. |
| 2 | Enter PID `150710640` → 🔍 | Hub shows 5 cards with live stats. |
| 3 | Tap `📅 متابعة الغياب` | `/parent/legacy?pid=150710640#section-attendance` loads → ONLY attendance card visible. **The store card should NOT appear.** |
| 4 | Tap `← العودة إلى القائمة الرئيسية` | Browser navigates to `/parent?pid=150710640`. Hub re-renders populated with the same student's 5 cards — no PID re-entry. |
| 5 | Tap `💳 متابعة الدفع` | ONLY payment card + (if applicable) `pp-pick-card` / `pp-upload-card` / `pp-paid-msg` helper cards. **No store, no evaluations, no books.** |
| 6 | Tap back → tap `🎁 المتجر والنقاط` | ONLY store/points card. |
| 7 | Tap back → tap `⭐ التقييمات` | ONLY evaluations card. **Store does NOT appear.** |
| 8 | Tap back → tap `📚 المناهج` | ONLY books card. |
| 9 | Direct visit `/parent/legacy` (no query) | Full flat-scroll page exactly as before. |
| 10 | Direct visit `/parent` (no query) | Lookup form, focus on input — unchanged manual entry flow. |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after every commit | ✅ |
| `scripts/smoke_parent_html_js_valid.py` (all 3 constants) | ✅ |
| `scripts/smoke_parent_hub_phase1.py` | ✅ 8/8 |
| `scripts/smoke_parent_legacy_autolookup.py` | ✅ 6/6 |
| `scripts/smoke_parent_section_only.py` | ✅ 8/8 |
| `scripts/smoke_parent_v284_fixes.py` (new) | ✅ 7/7 |
| `loadStoreMenu` async flow unchanged (still fetches + shows card on items > 0) | ✅ — only the !important CSS overrides the show when target ≠ section-points |
| Manual PID entry from hub still works (no `?pid` in URL) | ✅ — `phBootFromUrl` returns early without firing lookup |
| Manual PID entry from legacy page still works (no `?pid` in URL) | ✅ — `ppBootAutoLookup` returns early |
| Direct visit `/parent/legacy` shows full flat-scroll page | ✅ — `ppSectionOnlyView` returns early when no `#section-*` hash |
| Book-folder accordion still works | ✅ — `ppToggleFolder` helper untouched |
| Hub h1 still renders | ✅ — only `<a>` removed from topbar |
| No new endpoints, no new schema, no DB writes | ✅ |
| No raw single quotes inside single-quoted JS strings | ✅ — all DOM construction via createElement/textContent |

## Files touched

- `app.py`
  - C1 (+29): `injectHideRules` helper inside `ppSectionOnlyView`.
  - C2 (+34 / -3): `addBackButton` reads PID from search; new
    `phBootFromUrl` IIFE in the hub.
  - C3 (-1): topbar `<a>` deletion.
- `scripts/smoke_parent_v284_fixes.py` (+119, new) — 7-invariant
  smoke.
- `reports/parent_hub_v284_fixes.md` (this file).

## Rollback

`safety/parent-hub-fixes-20260513-013000` is the commit
immediately before C1. To revert the entire v2.8.4 ship:

```bash
git revert --no-edit fd4e6a8 1b2a0a1 198216b aa1350e
git push origin main
```

Each commit is independent (no shared file beyond `app.py` and
the new smoke). Reverting any subset works — e.g.,
`git revert aa1350e` alone restores the store-card race without
touching the back-button or topbar fixes.

---

🎯 **v2.8.4 — 3 owner-reported parent-hub UX fixes shipped.
Store card now scoped to its section, back-nav preserves PID
round-trip, topbar cleaned up. 4 commits, JS validated, 7/7
smoke green, no regression on the prior 3 parent smokes.**
