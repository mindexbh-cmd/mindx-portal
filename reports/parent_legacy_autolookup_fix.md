# /parent/legacy Auto-Lookup Fix — Verification

**Date:** 2026-05-12
**Safety tag:** `safety/parent-legacy-autolookup-20260512-235500`
**Commits:** C1 → C2 (this report = C3)

## The bug

Owner browser-tested the v2.8 parent hub and reported a UX regression:

> When I click a hub card, I land on
> `/parent/legacy?pid=150710640#section-payment` but the legacy page
> still shows the PID lookup form, forcing me to re-type the same
> PID I just typed into the hub.

The hub had been doing its job — passing the resolved PID forward
in the URL — but the legacy page wasn't reading the query string.
The 5 anchor IDs landed correctly, but because the legacy page had
no rendered student data above them, the scroll target was a tiny
empty section header at the top of the document with the lookup
form filling the screen below.

## Root cause

`PARENT_HTML` was written before the hub existed. Its boot path is
"render manual PID form, wait for click". The new hub flow (added
in v2.8) embeds the PID in the URL — but no code in `PARENT_HTML`
ever called `URLSearchParams(window.location.search).get('pid')`.

## The fix

Pure-additive 40-line IIFE inserted just before the closing
`</script>` of `PARENT_HTML`:

```js
(function ppBootAutoLookup(){
  try {
    var params = new URLSearchParams(window.location.search);
    var pidFromUrl = (params.get('pid') || '').trim();
    if (!pidFromUrl) return;
    var input = document.getElementById('pp-pid');
    if (input) input.value = pidFromUrl;
    if (typeof ppLookup !== 'function') return;
    ppLookup();
    var hash = (window.location.hash || '').trim();
    if (!hash || hash.length < 2) return;
    var tries = 0;
    var iv = setInterval(function(){
      tries++;
      if (typeof _ppStudent !== 'undefined' && _ppStudent){
        clearInterval(iv);
        setTimeout(function(){
          try {
            var el = document.querySelector(hash);
            if (el && el.scrollIntoView){
              el.scrollIntoView({behavior:'smooth', block:'start'});
            }
          } catch(_) {}
        }, 250);
      } else if (tries > 40){ clearInterval(iv); }
    }, 100);
  } catch(_) {}
})();
```

**Key design choices:**

| Decision | Why |
|---|---|
| IIFE at end of `<script>` | All function/variable declarations above (`ppLookup`, `_ppStudent`) are hoisted into module scope by the time this runs. No re-ordering of existing code. |
| Pre-fill `#pp-pid` before lookup | Visual continuity — parent sees the same PID echoed back in the input, can edit it manually to switch students if they want. |
| Call `ppLookup()` instead of duplicating fetch logic | One place to maintain the lookup flow. The hub-side path and the URL-bootstrap path converge after this call. |
| Poll `_ppStudent` instead of `setTimeout(1500)` | Lookup latency varies. Polling lets fast lookups scroll sooner; slow lookups still get the right anchor; failed lookups never scroll at all (so the legacy page's error toast remains the only feedback). |
| 40 × 100ms = 4-second poll cap | Generous enough for slow Render cold-starts. After cap, silently stop polling — parent sees the page rendered, scroll just doesn't happen, no harm done. |
| `try/catch` at every boundary | A malformed URL (e.g. unicode confusion in `hash`) never throws an uncaught exception that would crash the rest of the page. |
| 250ms delay between data-ready and scroll | `_ppStudent` is set before `_ppRender` finishes painting; the small delay ensures the anchor element has its final layout position. |

## What this does NOT do

- **Does not hide the manual lookup form.** A parent can still type
  a different PID and click 🔍 to switch students — same as before.
- **Does not consume the `?pid` from the URL.** The browser URL
  stays `/parent/legacy?pid=…#section-…` so refresh works.
- **Does not modify any existing function.** `ppLookup`, `_ppRender`,
  `_ppStudent` all unchanged.
- **Does not affect the new hub.** The hub (`PORTAL_PARENT_PID_HUB_HTML`)
  has its own boot logic; this IIFE only lives in the legacy template.

## Smoke test

`scripts/smoke_parent_legacy_autolookup.py` (98 LOC) — 6 invariants:

| # | Check | Result |
|---|---|---|
| 1 | `GET /parent/legacy` returns 200 + manual PID form intact (`#pp-pid` input, `onclick="ppLookup()"`) | ✅ |
| 2 | `ppBootAutoLookup` IIFE wired — 7 critical snippets present (`URLSearchParams`, `params.get('pid')`, `ppLookup();`, `_ppStudent`, `scrollIntoView`, …) | ✅ |
| 3a | All 5 section anchors in DOM (`section-payment`, `section-attendance`, `section-points`, `section-evaluations`, `section-books`) | ✅ |
| 3b | 6 legacy DOM ids preserved (`ppStoreCard`, `pp-evals-card`, `pp-books-card`, `pp-lookup-card`, `pp-info-rows`, `pp-go`) — existing JS unaffected | ✅ |
| 5 | Route accepts `?pid=…`, `?pid=…&foo=bar`, empty `?pid=` without 500ing | ✅ |
| 6 | `/parent` hub HTML untouched — IIFE only in legacy template, no leakage | ✅ |

All 6 green locally.

## Files touched

- `app.py` — +40 LOC inside `PARENT_HTML`, just before closing
  `</script>`. Zero LOC deleted.
- `scripts/smoke_parent_legacy_autolookup.py` — new 98-line smoke.
- `reports/parent_legacy_autolookup_fix.md` — this file.

## Rollback

`safety/parent-legacy-autolookup-20260512-235500` is the commit
immediately before C1. To revert:

```bash
git revert --no-edit 87517b8 72c809f
git push origin main
```

Reverting removes only the IIFE and the smoke. The hub-side
behavior (cards still link to `/parent/legacy?pid=…#anchor`) is
unaffected — parents would just see the regression again, not a
crash.

## Owner browser-test checklist

1. Open `/parent`, type a real PID, click 🔍.
2. Hub renders with 5 cards.
3. Click 💳 متابعة الدفع.
4. Browser navigates to `/parent/legacy?pid=…#section-payment`.
5. **EXPECTED:** Page loads, PID auto-fills, lookup runs, after
   ~1–2 seconds the page smooth-scrolls down to the payment section.
6. **EXPECTED:** Lookup form is still visible at the top — parent
   can type a different PID to switch students.
7. Click browser back → returns to hub with state intact.
8. Try `/parent/legacy` directly with no `?pid` → expected to show
   the lookup form, no auto-trigger.

---

🎯 **/parent/legacy auto-lookup fix shipped. Hub cards deep-link
into anchored sections without re-prompting for PID. Manual entry
still works. All smoke green. 40 LOC additive change with full
rollback.**
