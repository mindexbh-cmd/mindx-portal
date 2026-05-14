# Parent shop Phase C — verification (v2.9.10-safe)

## What shipped

Three additive features on `/parent/legacy?pid=…`, all wired
through the existing v2.9.9.2-safe cart IIFE:

| # | Feature | Mechanism |
| - | ------- | --------- |
| 1 | Order-confirmation modal before checkout | Intercept `#cartCheckoutBtn` — strip its inline `onclick`, install an `addEventListener` that opens `#orderConfirmBack` showing a per-line summary + balance + remaining-after-order. "تأكيد" calls the original `window.cartCheckout()`. "إلغاء" closes the modal. |
| 2 | Cancel pending orders | A red 🗑️ button injected into each `.pp-pending-card`. Click → `#cancelOrderConfirmBack` danger modal → POST `/api/parent/order/cancel`. Page reloads on success so the legacy pending list + balance refresh without us hooking into `_ppRender` or `loadStoreMenu`. |
| 3 | Quantity selector per prize | A `−/input/+` stepper alongside the "🛒 أضف للسلة" button on each `.pp-store-card`. The add button reads its own input ref via a per-card closure at click time. Input clamps to `[1, 99]`, resets to `1` after each add. |

## Architecture (one paragraph)

A single new backend endpoint (`POST /api/parent/order/cancel`)
added at end of `app.py`. All client-side logic lives in the
existing cart IIFE — three new `window.cart*` and three new
`window.*Order*` public handlers, plus three new private helpers
(`_buildQtySelector`, `_getPendingArray`, `injectCancelButtons`).
The existing `MutationObserver` on `#pp-store-body` now fires
`injectCartButtons` + `injectCancelButtons` on every store
re-render, keeping both injected button sets in sync with the
legacy renderer's output. Cancel-order id resolution uses **Option
B** — read `window._ppStoreState.pending` via closure access and
index-align it with the `.pp-pending-card` DOM elements (the
legacy renderer's `forEach` iterates the same array in order).

## Zero-touching guarantee

`_ppFormatStoreCard`, `_ppRenderStore`, `_ppRender`, `loadStoreMenu`,
`ppBootAutoLookup`, and `ppSectionOnlyView` are byte-identical to
v2.9.9.2-safe (and therefore to v2.9.8.1 as well — that lineage is
preserved). Smoke #10–#12 assert this by checking the original
markers are present and v2.9.9-era regression vectors
(`var actionHtml`, `ppTileAddToCart`, `data-reward-id`,
`data-redemption-id`) are absent.

## Defensive properties

- **IIFE scope** — every helper is private; the public surface is
  six `window.cart*Order*` functions.
- **Closure-only legacy state access** — `_getPendingArray` reads
  `window._ppStoreState.pending` and treats it as immutable; we
  never write to it.
- **Idempotent button injection** — both `injectCartButtons` and
  `injectCancelButtons` skip cards that already carry the
  injected element. Re-firing the observer is a no-op.
- **Per-card closure for qty** — each add button captures its own
  input ref; one card's qty change can't bleed into another's.
- **Read-at-click, not read-at-injection** — the qty value is read
  from the live input on click, so the latest value always wins.
- **`removeAttribute('onclick')` + sentinel** — the checkout
  intercept can't double-wire (`data-confirm-wired="1"` guards
  re-runs).
- **try/catch everywhere** — every public handler body is wrapped;
  errors can't bubble to the legacy boot path.
- **Reload-on-cancel** — the page-reload after a successful cancel
  avoids any need to re-call `_ppRender` / `loadStoreMenu`
  ourselves (zero-touching).

## Smoke (15 invariants, all passing)

`scripts/smoke_parent_phase_c.py`:

1. `/parent/legacy` → 200, boot-path functions intact.
2. `POST /api/parent/order/cancel` registered.
3. `#orderConfirmBack` + body + go-button present.
4. `#cancelOrderConfirmBack` + go-button present.
5. `window.orderConfirmShow` defined exactly once.
6. `window.cancelOrderShow` defined exactly once.
7. `injectCancelButtons` defined inside the IIFE.
8. `_buildQtySelector` + `cart-qty-selector` + `cart-qty-num-input`
   classes present.
9. `setupCheckoutConfirm` + `data-confirm-wired` sentinel present.
10. `_ppFormatStoreCard` untouched (legacy `'اطلب الآن'` label
    present; none of `var actionHtml`, `data-reward-id`,
    `data-redemption-id`, `ppTileAddToCart` leaked in).
11. `_ppRender` declaration present.
12. `loadStoreMenu` declaration present.
13. Brace balance in the script: **365/365**.
14. All 6 Phase C window handlers defined exactly once each.
15. All five cart endpoints + legacy `/api/parent/store/request`
    still registered.

## Browser test plan

1. Open `/parent?pid=<pid>` → click متجر والنقاط → land on
   `/parent/legacy?pid=<pid>#section-points`. Navigation must
   still work (regression guard).
2. About **1.5 s** after the store renders, each available tile
   should show a `−/1/+` qty stepper plus a "🛒 أضف للسلة"
   button BELOW the original "اطلب الآن" button. Disabled
   tiles get nothing new.
3. Click `+` twice → input reads `3`. Click "🛒 أضف للسلة"
   → toast "أضيف إلى السلة", input resets to `1`, fab shows
   badge `3`.
4. Click the floating 🛒 → cart modal opens with 3 of that prize.
5. Click "إتمام الطلب" → **the new confirmation modal opens**
   listing the cart (reward × qty = subtotal) + balance + total
   + remaining-after pill. "تأكيد الطلب" proceeds; "إلغاء" stays
   on the cart.
6. After successful checkout, the store re-renders. A new
   "قيد المراجعة" callout should appear (if the cart used the
   legacy single-shot path it'd be `requested`; cart-checkout
   uses `pending`, which is currently filtered out of the
   `pending_requests` JSON — so cart-checkout callouts may not
   appear in the pending list. This is a separate display-side
   issue, not a Phase C bug).
7. Trigger a "اطلب الآن" on a different prize (the legacy
   immediate-order path) so a `requested` redemption lands in
   the pending list. After the store re-renders, that callout
   should show a red 🗑️ "إلغاء الطلب" button on the LEFT.
8. Click it → danger modal opens with the warning text. "نعم،
   إلغاء الطلب" posts to `/api/parent/order/cancel` and the page
   reloads with the pending callout gone and the balance refreshed.

## Open question / follow-up

The cancel feature shows on `pending_requests` from the menu
endpoint, which today filters `WHERE status='requested'` only.
Cart-checkout redemptions write `status='pending'` and won't
appear in that list — so they're not cancellable through this
UI path today. If the owner wants cart-checkout redemptions to
also be cancellable, the menu endpoint's pending SELECT needs
its WHERE clause widened to `status IN ('requested','pending')`.
That's a one-line backend edit (in `app.py` ~line 28430), low
risk, no render touch. Flagged but NOT shipped in Phase C.

## Awaiting

Owner browser-test of the 8 steps above.
