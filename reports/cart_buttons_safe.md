# Per-tile "أضف للسلة" buttons via observer (v2.9.9.1-safe)

## Context

`v2.9.9-safe` shipped the cart system reachable only through the
floating 🛒 fab. The owner wanted per-tile "أضف للسلة" buttons
on the prize cards too — but the first attempt (`v2.9.9`) regressed
parent navigation precisely because it modified `_ppFormatStoreCard`.

The investigation surfaced a constraint:
- Prize cards have **no** `data-reward-id` attribute (confirmed by
  source-code grep — the reward id appears only inside
  `onclick="requestStoreItem(N)"` on the button).
- Adding a data attribute *is* a render change, with the same
  risk profile as the v2.9.9 regression.

**Option A** — adopted here — avoids all render changes by
reading the reward id from the existing button's `onclick`
attribute via regex.

## What changed

A single commit adds `injectCartButtons` + `setupCartButtonObserver`
inside the existing v2.9.9-safe IIFE in `PARENT_HTML`. No file
outside `app.py:10783–11075` was touched, and no existing function
inside that range was modified — both new functions are pure
additions inside the IIFE's closure.

## How it works

1. The legacy renderer `_ppFormatStoreCard` emits its tiles
   unchanged. Each available tile has a `<button class="pp-store-btn"
   onclick="requestStoreItem(N)">اطلب الآن</button>`. Disabled tiles
   have the same button without the `onclick`.

2. After `window.load + 200 ms`, the IIFE calls
   `setupCartButtonObserver()`. It attaches a `MutationObserver`
   scoped to `#section-points` (the store anchor in PARENT_HTML)
   with `childList: true, subtree: true`. It also fires
   `injectCartButtons()` once via `setTimeout` for the initial paint.

3. `injectCartButtons()` queries `document.querySelectorAll(
   '.pp-store-card')`. For each card:
   - Skip if a `.cart-add-btn` was already injected (idempotent).
   - Read the sibling `.pp-store-btn`'s `onclick` attribute.
   - Match `requestStoreItem\((\d+)\)` — if no match (disabled
     tile), skip silently.
   - Create a `<button class="cart-add-btn"
     data-cart-reward="<N>">🛒 أضف للسلة</button>` with inline
     purple-gradient styling.
   - Attach the click handler via `addEventListener('click', …)`
     — **not** an inline `onclick` (defends against quote-
     escaping issues in the rendered HTML).
   - Insert it as a SIBLING after the existing `.pp-store-btn`,
     so the original "اطلب الآن" path remains intact and clickable.

4. The handler reads the reward id from
   `event.currentTarget.getAttribute('data-cart-reward')` and
   calls `window.cartAdd(rewardId, 1)` (defined in the v2.9.9-safe
   IIFE).

## Defensive properties

- **No render code touched.** `_ppFormatStoreCard`, `_ppRender`,
  `loadStoreMenu` are byte-identical to v2.9.8.1.
- **Disabled tiles fall through.** No onclick → no regex match
  → no button injected → no accidental "add" of an unaddable
  prize.
- **Idempotent.** Re-running `injectCartButtons` after the
  observer fires never doubles the buttons because the
  `card.querySelector('.cart-add-btn')` guard returns early.
- **Sibling insertion, not replacement.** The original "اطلب
  الآن" button is preserved — parents can still use the legacy
  immediate-order path if they want, while the cart is opt-in.
- **All wrapped in try/catch.** A thrown error inside
  `injectCartButtons` cannot bubble to the legacy boot path.
- **MutationObserver is optional.** Old browsers without
  `MutationObserver` skip the observer (try/catch guards the
  `new MutationObserver(…)` call), but the initial `setTimeout`
  sweep still runs once — so a single render still gets buttons.

## Smoke (10 invariants, all passing)

`scripts/smoke_cart_buttons_safe.py`:

1. `/parent/legacy` returns 200.
2. Boot-path functions intact.
3. Renderer untouched — `'اطلب الآن'` label still present, no
   `data-reward-id` leaked in, no `ppTileAddToCart`, no
   `var actionHtml`.
4. `injectCartButtons` + `setupCartButtonObserver` defined inside
   the IIFE.
5. `MutationObserver` with `childList: true, subtree: true`.
6. `requestStoreItem\((\d+)\)` regex extraction pattern present.
7. Injected button click handler uses `addEventListener`, not
   inline `onclick=`.
8. All 5 cart endpoints still registered.
9. `window.cartAdd` defined exactly once.
10. JS braces balanced (281/281).

## Browser test plan

1. Open `/parent?pid=<a real student PID>`. Click the **متجر
   والنقاط** card → land on `/parent/legacy?pid=<pid>#section-points`.
   The store should render with prize tiles — navigation must
   continue to work (the v2.9.9 regression we explicitly tested
   against).
2. **~700 ms after the store renders** (initial 500 ms inject
   + DOM settle), each available tile should show a purple
   "🛒 أضف للسلة" button BELOW the existing "اطلب الآن"
   button.
3. Disabled tiles (greyed "غير متاح" / "نفد المخزون" / "قيد
   المراجعة") should show ONLY the original disabled button —
   no cart button injected.
4. Click "🛒 أضف للسلة" → toast "أضيف إلى السلة" appears, the
   floating 🛒 fab at bottom-left shows up with badge "1".
5. Click the fab → cart modal opens listing that prize.
6. Click "اطلب الآن" on a different tile — the legacy immediate-
   order path still works (regression guard).

## What's still deferred

- The cart modal's per-line ± / 🗑️ controls already work
  (shipped in v2.9.9-safe).
- Checkout already works (shipped in v2.9.9-safe).
- Future polish: replace inline styles on the injected button
  with a class in the page's `<style>` block, once the approach
  is confirmed safe in browser testing.
