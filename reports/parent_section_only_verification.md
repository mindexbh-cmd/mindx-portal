# Parent Section-Only View — Verification

**Date:** 2026-05-13
**Safety tag:** `safety/parent-section-only-20260513-010500`
**Commits:** C1 → C2 (this report = C3)

## Commit log

```
<this report>  docs: section-only view verification
1c314fd        test(parent): section-only smoke
9cb20b8        feat(parent): section-only view when URL has anchor
```

## The change

When `/parent/legacy` is reached with a hub deep-link such as
`#section-payment`, the page now hides every other section card
and shows ONLY the requested section + a back-to-hub button.
Direct visits to `/parent/legacy` (no hash) still show the full
flat-scroll page exactly as before.

## Section-isolation logic

A new IIFE `ppSectionOnlyView` lives at the bottom of
PARENT_HTML's `<script>` block, immediately after the v2.8.1
`ppBootAutoLookup` IIFE. It runs on every page load but
early-returns unless the hash matches one of the 5 whitelisted
anchors:

```js
var KNOWN = {
  'section-payment':1, 'section-attendance':1,
  'section-points':1,  'section-evaluations':1,
  'section-books':1
};
```

When the hash IS one of those, the IIFE polls every 150ms (capped
at 6s) for `pp-content` to become visible (which happens when
`_ppRender` finishes after the v2.8.1 auto-lookup fetch resolves).
Once visible, it walks `pp-content`'s direct children — each
`<span class="pp-anchor">` marks a logical section boundary, and
every `.pp-card.pp-section` after it (until the next anchor)
belongs to that section.

| Hash | Anchor span | Section card kept | Helper cards kept |
|---|---|---|---|
| `#section-attendance` | `#section-attendance` | attendance card | — |
| `#section-payment` | `#section-payment` | payment card | `pp-pick-card`, `pp-upload-card`, `pp-paid-msg` (dynamic by `_ppRender`) |
| `#section-evaluations` | `#section-evaluations` | `#pp-evals-card` | — |
| `#section-books` | `#section-books` | `#pp-books-card` | — |
| `#section-points` | `#section-points` | `#ppStoreCard` (hidden until `loadStoreMenu` shows it) | — |

The first `.pp-card.pp-section` (student info, before any anchor)
is hidden in section-only mode — the hub's hello row already shows
the student's name, so re-displaying it here is redundant. The
`#pp-lookup-card` (PID input form) is also hidden so the
single-section view doesn't include a stray "switch student" input.
Both are restorable via the back button (which navigates to
`/parent`, where the lookup happens fresh).

## Back-to-hub button

Built via DOM construction (createElement + textContent), NOT
innerHTML — this side-steps the escaped-quote class of bugs
identified in v2.8.2.

```js
var a = document.createElement('a');
a.href = '/parent';
a.textContent = '← العودة إلى القائمة الرئيسية';
// + inline gradient styling matching the rest of the page
```

Inserted just above `#pp-content` so it sits between the page
header and the lone section card.

## Coexistence with prior IIFEs

PARENT_HTML's script block now ends with three IIFEs, each
narrowly scoped and each guarded by an early-return condition:

| IIFE | When it runs | Source |
|---|---|---|
| `ppBootAutoLookup` (v2.8.1) | URL has `?pid=…` | reads query, calls `ppLookup()`, polls `_ppStudent`, smooth-scrolls to hash |
| `ppToggleFolder` helper (v2.8.2) | Called by book-folder onclick handlers | replaces the broken `\'collapsed\'` inline expression |
| `ppSectionOnlyView` (v2.8.3) | URL hash starts with `#section-` | polls `pp-content` visibility, walks children, hides non-target sections |

Each IIFE wraps its body in `try/catch`, so a malformed URL or
unexpected DOM state never breaks the page.

## Browser test scenarios (owner verification)

| # | Action | Expected |
|---|---|---|
| 1 | Open `/parent` | Hub renders with PID input. |
| 2 | Type a valid PID, press 🔍 | Hub shows 5 cards with live stats. |
| 3 | Tap `💳 متابعة الدفع` | Browser navigates to `/parent/legacy?pid=…#section-payment`. Page renders with ONLY the payment section card visible (plus dynamic pp-pick-card / pp-upload-card / pp-paid-msg if `_ppRender` chose to reveal them). |
| 4 | Tap the `← العودة` button at the top | Returns to `/parent` hub. |
| 5 | Tap `📅 متابعة الغياب` | Lands on `/parent/legacy?pid=…#section-attendance`. Page shows ONLY the attendance section + back button. |
| 6 | Tap each remaining card (`🎁`, `⭐`, `📚`) | Each navigation reveals exactly its section. |
| 7 | Direct visit `/parent/legacy` (no hash) | Full flat-scroll page — the section-only IIFE early-returns. |
| 8 | Direct visit `/parent/legacy?pid=…` (no hash) | Auto-lookup fires, full flat-scroll page renders, no isolation. |
| 9 | Visit `/parent/legacy?pid=…#section-payment` | One-shot deep-link works the same as the hub card click. |
| 10 | Direct visit `/parent/legacy#section-attendance` (no PID) | Hash is detected but PID lookup never fires → `pp-content` stays hidden → the IIFE caps out after 6s and silently exits. Page shows the bare PID input form. (Acceptable edge case.) |

## Smoke results

`scripts/smoke_parent_section_only.py` — 8 invariants, all green:

| # | Check |
|---|---|
| 1 | section-only IIFE wired (13 critical snippets in served HTML) |
| 2 | All 5 anchor targets in DOM |
| 3 | 7 legacy DOM ids preserved |
| 4 | Prior IIFEs (auto-lookup + folder helper) preserved |
| 5 | PARENT_HTML `<script>` parses cleanly via node |
| 6 | Hash guard present (early-return when no `#section-*`) |
| 7 | KNOWN whitelist covers exactly the 5 hub-linkable sections |
| 8 | `/parent` hub HTML untouched (no leakage) |

All prior smokes (`smoke_parent_hub_phase1`,
`smoke_parent_legacy_autolookup`, `smoke_parent_html_js_valid`)
also still pass.

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after every commit | ✅ |
| `scripts/smoke_parent_html_js_valid.py` | ✅ all 3 constants parse |
| `scripts/smoke_parent_hub_phase1.py` | ✅ 8/8 green |
| `scripts/smoke_parent_legacy_autolookup.py` | ✅ 6/6 green |
| `scripts/smoke_parent_section_only.py` (new) | ✅ 8/8 green |
| No new endpoints, no new schema | ✅ |
| `ppBootAutoLookup` still fires on `?pid=…` URLs | ✅ — preserved in served HTML |
| `ppToggleFolder` still wired (book-folder accordion) | ✅ — preserved |
| `ppLookup`, `_ppRender`, `_ppStudent` untouched | ✅ |
| Manual PID entry (no hash, no pid) still works | ✅ — direct visit to /parent/legacy renders the form, button click triggers `ppLookup` |
| `_ppRender`'s scroll-to-pp-content still works on full-page mode | ✅ — section-only IIFE early-returns when no hash present |
| Hub HTML (`PORTAL_PARENT_PID_HUB_HTML`) untouched | ✅ — smoke [8] |
| Existing single-quote escape audit clean (no new `\'…\'` patterns) | ✅ — code uses `createElement` + `textContent` |
| Arabic UI strings stored correctly in Python | ✅ — raw Arabic in single-quoted JS strings (matches existing pattern in PARENT_HTML) |

## Files touched

- `app.py` (+95) — single IIFE added to `PARENT_HTML` right after
  the v2.8.1 auto-lookup wiring. No existing line modified.
- `scripts/smoke_parent_section_only.py` (+136, new) — 8-invariant
  smoke covering wiring + syntax + no regression.
- `reports/parent_section_only_verification.md` (this file).

## Rollback

`safety/parent-section-only-20260513-010500` is the commit
immediately before C1. To revert the entire feature:

```bash
git revert --no-edit 1c314fd 9cb20b8
git push origin main
```

Reverting only drops the IIFE + the smoke. `/parent/legacy`
returns to v2.8.2 behavior — full flat-scroll page, no
section-only mode. The hub cards still deep-link the same way;
they just stop hiding the unrelated sections.

## What this phase does NOT do

- **Doesn't switch the URL/title on section-only mode.** The
  parent's browser back button takes them to the previous page in
  history (the hub), not to a synthetic state. The explicit
  back-to-hub button is the primary navigation.
- **Doesn't lazy-load section data.** The full `/api/parent/lookup`
  payload is still fetched at page-load time — only the rendering
  is filtered client-side. A future Phase 2 of the parent-hub
  redesign could replace each anchored section with a dedicated
  sub-page that only fetches its own slice.
- **Doesn't animate the section transition.** The hidden sections
  are simply `display:none`. No fade, no slide. Considered out of
  scope for this hotfix.
- **Doesn't handle the no-PID + hash edge case specially.** If
  someone shares `/parent/legacy#section-payment` without `?pid=`,
  they see the bare PID input form (the section-only IIFE caps
  out silently after 6s). Manual PID entry still works.

---

🎯 **Section-only view shipped. Hub cards now show one section at
a time with a back button. Legacy `/parent/legacy` without hash
still shows everything. JS validated, no regression. Pure-additive
95-LOC IIFE.**
