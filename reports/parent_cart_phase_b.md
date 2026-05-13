# Parent shop cart system — Phase B verification (v2.9.9)

## What shipped

A persistent shopping cart for the public parent points-store at
`/parent/legacy?pid=…#section-points`. Parents can stage multiple
prizes with quantities, review the running total against the live
balance, and check out atomically. Checkout writes
`redemptions(status='pending')` rows so points debit immediately
per `_pts_balance` semantics — admin still sees them in the
existing delivery workflow.

## Architecture

### Storage
- **`cart_items(id, student_id, reward_id, quantity, created_at,
  updated_at, UNIQUE(student_id, reward_id))`** — `init_db()`
  (line 1121 area) AND idempotent else-branch CREATE TABLE IF
  NOT EXISTS (line 7438 area). Index on `student_id`. Registered
  in `_TBL_AUDIT_FEATURE` so the audit dashboard recognises it.

### Endpoints (5, all PID-authenticated, rate-limited)
| Method | Route | Purpose |
| ------ | ----- | ------- |
| `POST` | `/api/parent/cart/add` | Upsert one prize (UPDATE-then-INSERT pattern). Body `{pid, reward_id, quantity?}`. |
| `GET`  | `/api/parent/cart` | Return items + total + balance + valid flag + has_unavailable. |
| `PUT`  | `/api/parent/cart/<cid>/quantity` | Set absolute quantity; `0` deletes the line. Verifies ownership against pid. |
| `DELETE` | `/api/parent/cart/<cid>` | Remove one line. Pid via querystring. Ownership-checked. |
| `POST` | `/api/parent/cart/checkout` | Server re-validates `total ≤ _pts_balance`, expands each cart line into `quantity` separate `redemptions` rows with `status='pending'` (admin's one-row-per-prize-instance UX), clears the cart. |

Shared helper `_cart_compute(db, sid)` joins `cart_items` with
`rewards` so each cart row carries live name / cost / stock
state — an inactive or out-of-stock prize is flagged
`available=False`, the UI shows it, and checkout refuses until
the parent removes it.

### UI
- **Floating fab** `#ppCartFab` — bottom-left, `🛒` with a pink
  badge showing items_count. Hidden when count is 0, shown
  otherwise. Persists across sessions via the cart_items table.
- **Cart modal** `#ppCartBack` — list of lines (thumb + name +
  cost × qty + ± buttons + 🗑️), footer with balance / total /
  remaining-or-deficit pill and an "إتمام الطلب" button that
  disables when total > balance OR any line is unavailable.
- **Prize tile (available state)** — replaces the old single
  "اطلب الآن" button with `[−][1][+] 🛒 أضف للسلة`. Disabled
  states (pending / out of stock / insufficient balance) keep
  the existing greyed button + hint UX unchanged.

## Browser test plan (run after v2.9.9 deploys)

1. Open `/parent/legacy?pid=<a real student PID>` → scroll to
   `#section-points`. The store renders with the new tile UX:
   each available prize has the qty stepper + "🛒 أضف للسلة".
2. Click `+` once on a tile (qty becomes 2). Click "🛒 أضف
   للسلة". Toast: "أضيف إلى السلة". The floating 🛒 fab
   appears bottom-left with badge "2".
3. Click another tile's add button. Badge updates to 3, 4, ...
4. Click the fab → modal opens listing every line with
   thumbnail, name, cost × qty, ± buttons, 🗑️. Footer shows
   balance, total, remaining.
5. Click `+` next to a line → quantity goes up; total + remaining
   recompute server-side. Click `−` enough times to take the line
   to 0 → it disappears from the modal.
6. Click 🗑️ → line removed; if it was the last line, the modal
   shows "🛒 السلة فارغة" and the fab hides.
7. Add prizes until the total exceeds the student's balance — the
   "إتمام الطلب" button greys out and reads "النقاط غير كافية";
   the remaining pill goes red.
8. Reduce quantities so total ≤ balance. The button re-enables.
   Click → toast: "تم إرسال طلبك (N قطعة)". Modal closes, fab
   disappears, store re-fetches with the new balance.
9. Verify in the admin redemptions page that N rows appear with
   `status='pending'`, `request_source='parent_cart'`,
   `points_spent=cost` (one row per prize-instance, as designed).
10. Refresh the page and re-enter the same PID — the cart is now
    empty (checkout cleared it). Add 2 prizes, navigate away,
    return. The cart is still there with 2 items (persisted in
    `cart_items`).

## Regression checks (covered by `scripts/smoke_parent_cart.py`)

- `app.py` parses + imports cleanly.
- `cart_items` table created at boot.
- All 5 cart endpoints registered with correct methods.
- Cart modal markup + fab + badge in source.
- Renderer emits the per-tile qty selector + add-to-cart wiring.
- Six generic-name aliases (`addToCart`, `openCart`, `closeCart`,
  `updateQuantity`, `removeFromCart`, `checkout`) defined exactly
  once each.
- **Legacy `POST /api/parent/store/request` endpoint still
  registered** — Phase A flow untouched.
- Add-to-cart uses the project's cross-DB upsert idiom
  (UPDATE-then-INSERT).
- Checkout re-fetches `_pts_balance` server-side, rejects on
  `total > balance`, and writes `status='pending'` so points
  debit per `_pts_balance` semantics.

## What Phase B does NOT touch

- The legacy `/api/parent/store/request` endpoint and its
  `status='requested'` flow.
- `_pts_balance` calculation logic.
- The admin redemptions list / approval workflow.
- The Phase A image fixes + zoom modal + insufficient-points
  client guard (still wired alongside).
- The `requestStoreItem` function (the old immediate-order
  helper) — kept callable for any third-party integrators but
  the renderer no longer wires the active-tile button to it.

## Open question / design decision (flagged for owner)

The checkout writes `status='pending'`, which **immediately
debits** the student's points per `_pts_balance`. The legacy
single-button flow used to write `status='requested'` (no debit
until admin approval). If the owner wants cart checkout to
preserve the admin-approval-before-debit gate, the change is
a one-word edit in `api_parent_cart_checkout` — flag it and
I'll switch.

## Awaiting

Owner browser-test of the 10 steps above.
