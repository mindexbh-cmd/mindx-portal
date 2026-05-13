# Parent shop — Phase A verification (v2.9.8)

## What changed

Three small fixes on the parent-side points-store at
`/parent/legacy?pid=…#section-points`:

| # | Fix | Where |
| - | --- | --- |
| C2 | Prize images render full (no crop) | CSS `.pp-store-img img` — `object-fit:cover` → `contain`, faint bg + `cursor:zoom-in` (`app.py:9768`) |
| C3 | Click image → modal zoom | New `#prizeZoomBack` modal markup + CSS + `window.openPrizeZoom` / `window.closePrizeZoom` + ESC / backdrop close (`app.py` PARENT_HTML tail) |
| C4 | Insufficient-points click guard | New defense-in-depth branch inside `requestStoreItem(rewardId)` — re-checks `_ppStoreState.balance` vs the item's `point_cost` and bails with a toast before the POST (`app.py:10533+`) |

Server-side `/api/parent/store/request` was already rejecting
`balance < cost` with the same Arabic message (`app.py:27983-27988`)
— that path is untouched. Same for the renderer's pre-existing
`disabled` HTML attribute when balance < cost (`app.py:10421-10434`).

## Browser test plan (run on prod after v2.9.8 is live)

1. **Open** `/parent/legacy?pid=<a real student PID>` → scroll to
   `#section-points` (or use the deep-link).
2. **Verify**: every prize tile renders the **full** image — no
   cropping at the top/bottom (or sides for landscape images).
   Hover shows the `zoom-in` cursor.
3. **Click** any prize image → dark overlay appears, image
   re-renders at up to 80vh on a white card with the prize name
   underneath.
4. **Close** the modal three ways:
   - Click the `×` button → closes.
   - Click anywhere on the dark backdrop → closes.
   - Press **Esc** → closes.
5. **Cost guard** — pick a student whose balance is below at
   least one prize's cost (or set up such a state):
   - The unaffordable tile's button reads **"غير متاح"**, is
     visually grey, and the cursor is **not-allowed**.
   - Clicking the button does nothing (HTML `disabled` attribute,
     no `onclick` wired).
   - If a developer console manually re-enables the button and
     calls `requestStoreItem(<id>)`, a toast "نقاطك غير كافية"
     fires and no POST goes out (defense-in-depth).
   - If the user somehow gets past both guards, the server still
     returns 400 with the same Arabic message + the current
     balance and cost.

## Regression checklist (covered by `scripts/smoke_parent_shop_phase_a.py`)

- App boots cleanly; `/parent/legacy` returns 200.
- `object-fit:contain` is present in the `.pp-store-img img` rule.
- Zoom modal markup, both window handlers, and the `onclick` on
  rendered prize images are all present (and the handlers are
  defined exactly once — no late-binding stub overwrites).
- The card renderer's `balance < cost ⇒ disabled` branch is intact
  AND the new client-side guard in `requestStoreItem` references
  `_ppStoreState.balance`.

## What Phase A does NOT touch

- The `/api/parent/store/request` server endpoint (purchase flow).
- The `_pts_balance()` calculation.
- Any Arabic text outside the new modal's `إغلاق` aria-label.
- The icon-fallback path when a prize has no `image_url` — those
  tiles render the emoji, which is not clickable (no `<img>` to
  attach the zoom onclick to).

## Awaiting

Owner browser-test of the five steps above, then Phase B (cart
system) brief.
