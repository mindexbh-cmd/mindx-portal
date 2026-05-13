# Parent cart — defensive rebuild (v2.9.9-safe)

## Context

The first cart attempt (`v2.9.9`) introduced a regression that broke
parent navigation — clicking a hub card landed back on the search
page. The diff couldn't pinpoint a single deterministic-throw line,
so we rolled back to `v2.9.8.1` and rebuilt the feature with strict
isolation rules.

## What changed (5 small commits, all additive)

| Commit  | Scope |
| ------- | ----- |
| `9e546b0` | `cart_items` table — `init_db()` + idempotent else-branch CREATE TABLE IF NOT EXISTS + `_TBL_AUDIT_FEATURE` entry. |
| `0bdc993` | Five backend endpoints at end of `app.py`. PID-authenticated via `_store_parent_pid_resolve`, rate-limited via `_parent_rate_check`. UPDATE-then-INSERT upsert; checkout writes `redemptions(status='pending')` so points debit per `_pts_balance`. |
| `434c26c` | Cart modal HTML at end of `<body>` in `PARENT_HTML`. Inline `<style>` scoped to `.cart-*` selectors; every id starts with `cart`. No JS, no boot-time wiring. |
| `ff48218` | Cart JS in an IIFE at end of `<script>`. `'use strict'`. All bodies wrapped in `try/catch`, all DOM access through `getEl()` with null check, all fetches through `cartFetch()` with `.catch(()=>null)`. Init fires only on `window.load + 200ms`. |
| `9284fe0` | Floating `<button id="cartFab">` at body end, hidden by default; the IIFE reveals it when items_count > 0. |

## What was NOT touched (the zero-touching guarantee)

`_ppFormatStoreCard`, `_ppRender`, `loadStoreMenu`,
`ppBootAutoLookup`, and `ppSectionOnlyView` are byte-identical to
`v2.9.8.1`. The smoke (#10) asserts this by checking that neither
the prior rewrite's `var actionHtml`, the prior per-tile
`ppTileAddToCart` wiring, nor the prior `window.ppCartRefresh` hook
inside `loadStoreMenu` leaked back in — and that the renderer still
emits the active-button label `'اطلب الآن'`.

The "أضف للسلة" button on prize tiles is **deferred** to a later
iteration. The cart is reached only via the floating 🛒 button —
which doesn't show until the cart has items, so on a first visit
the page reads exactly the same as `v2.9.8.1` (no new UI).

## Defensive isolation choices

- **IIFE wrapper.** No module-level vars except the IIFE's own
  `_cart` record. The `window.cart*` surface is intentional.
- **`window.load + 200ms` init.** By the time `setTimeout` fires,
  `ppBootAutoLookup`'s fetch has resolved or its 4s scroll polling
  has exhausted, and `ppSectionOnlyView` has either applied or
  given up. No race with the legacy boot.
- **Null checks on every DOM lookup.** `getEl()` returns `null`
  instead of throwing if the element disappears.
- **`.catch(()=>null)` on every fetch.** Network errors don't
  bubble.
- **No hooks.** No `_ppRender` interception, no `loadStoreMenu`
  trampoline, no event-bus subscribers — the cart code is on its
  own island.

## Smoke (10 invariants, all passing)

`scripts/smoke_parent_cart_safe.py`:

1. `/parent/legacy?pid=…` returns 200.
2. Boot-path functions all still present in source.
3. `cart_items` table exists in live DB.
4. All 5 cart endpoints registered with correct methods.
5. Cart modal markup present.
6. Cart floating button + badge present.
7. `window.cartModalOpen` defined exactly once.
8. `window.cartAdd` defined exactly once.
9. IIFE + `'use strict'` wrapper present.
10. None of the v2.9.9-era hooks / rewrites leaked in.

## Browser test plan (run after deploy)

1. Open `/parent?pid=<pid>` — hub renders.
2. Click any card — lands on `/parent/legacy?pid=<pid>#section-…`
   with the correct section visible (the regression we were
   debugging). Confirm navigation works.
3. With an empty cart, the floating 🛒 button stays hidden.
4. Use the JS console to call `cartAdd(<reward_id>, 1)` (or wait
   for the per-tile button iteration). Confirm a toast appears
   and the 🛒 button shows with badge `1`.
5. Click 🛒 — cart modal opens; balance + total are correct.
6. Use ± and 🗑️ buttons; checkout writes `redemptions` rows with
   `status='pending'` and clears the cart.

## What's deferred

- Per-prize "أضف للسلة" button on each tile. The legacy "اطلب
  الآن" button still works through the legacy
  `/api/parent/store/request` endpoint, so parents are not blocked.
- Cart UI accessible from anywhere other than the floating 🛒
  fab.
- The owner can add these in a future commit once the rebuild is
  confirmed safe in browser testing.
