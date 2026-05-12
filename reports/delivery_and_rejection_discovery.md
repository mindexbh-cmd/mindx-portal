# Delivery Tracking + Rejection Display — Discovery

**Date:** 2026-05-12
**Mode:** READ-ONLY. No code changes in this commit.

---

## §A — `redemptions` table schema

Confirmed via `PRAGMA table_info(redemptions)` against local DB (mirrors prod):

| column | type | notes |
|---|---|---|
| id | INTEGER | PK |
| student_id | INTEGER | FK → students.id |
| student_name | TEXT | denormalised |
| reward_id | INTEGER | FK → rewards.id |
| reward_name | TEXT | denormalised |
| points_spent | INTEGER | frozen at purchase |
| redeemed_at | DATETIME DEFAULT CURRENT_TIMESTAMP | |
| status | TEXT DEFAULT 'pending' | see §B |
| delivered_by | INTEGER | nullable, users.id of hand-off actor |
| delivered_at | DATETIME | nullable |
| request_source | TEXT DEFAULT '' | `''`, `'parent_pid'`, `'staff'`, `'admin_on_behalf'` |

**Missing columns we'll need:**
- ❌ `rejection_reason TEXT` — **does NOT exist**. The reject endpoint writes the reason to the `_audit` log only (per its own docstring: "no dedicated column to avoid a schema change in this commit"). Parents have no way to see it.
- ❌ `approved_by` / `approved_at` — not present. Approval flips `requested → pending` with no actor capture. Acceptable for v1: the `_audit` log captures who/when.

**Already there (good):**
- ✅ `delivered_by`, `delivered_at` — present and used by the existing `/deliver` endpoint.
- ✅ `request_source` — present, holds the audit-source tag.

## §B — Status lifecycle

Confirmed via grep + endpoint reading:

```
Parent flow (parent flow uses public /parent/store):
  ┌─────────────┐
  │ 'requested' │  ← created by POST /api/parent/store/request
  └──────┬──────┘     no debit, no stock decrement
         │ admin approves
         ▼
  ┌─────────────┐
  │ 'pending'   │  ← debits balance + decrements stock
  └──────┬──────┘     (this is the "approved, awaiting hand-off" state)
         │ admin delivers
         ▼
  ┌─────────────┐
  │ 'delivered' │  ← stamps delivered_by + delivered_at
  └─────────────┘

Or, after the admin approves:
  'pending' ─cancel─▶ 'cancelled'  (refunds via _pts_balance excluding cancelled)

Or, if admin rejects the parent request:
  'requested' ─reject─▶ 'rejected'   (no debit, no stock change, reason → audit log only)

Staff direct (admin-on-behalf, v2.3):
  POST /api/points/admin-purchase
  ┌────────────────────────────────┐
  │ 'delivered'                    │  ← inserted directly with this status
  │ + request_source='admin_on_behalf'│   stamps delivered_by + delivered_at
  └────────────────────────────────┘     bypasses pending state entirely

Staff direct (legacy, /api/points/redeem):
  Inserts as 'pending' with request_source=''. Admin then delivers.
```

**Important spec-vs-reality clarification:** the spec text uses `'approved'` as the state name for "approved and awaiting delivery". The actual code uses `'pending'` for that same state (see `api_pts_redeem_approve` at line 36288: `UPDATE redemptions SET status='pending' WHERE id=? AND status='requested'`). The new endpoints (C3 deliver, C4 undeliver) will honor the existing convention and gate on `status='pending'`. UI labels will read "في انتظار التسليم" for users — the underlying status string is `'pending'`.

## §C — Rejection endpoint

`POST /api/points/redemptions/<id>/reject` at `app.py:36354`:

```python
def api_pts_redeem_reject(redeem_id):
    """Optional body {reason: <text>} is recorded in the audit log
    only — no dedicated column to avoid a schema change in this
    commit. Reason is informational."""
    ...
    body = request.get_json(silent=True) or {}
    reason = (body.get("reason") or "").strip()
    ...
    db.execute("UPDATE redemptions SET status='rejected' "
               "WHERE id=? AND status='requested'", (redeem_id,))
    db.commit()
    if reason:
        try:
            _audit("redemptions.reject", target_type="redemptions",
                   target_id=redeem_id,
                   new_value={"status": "rejected", "reason": reason})
        except Exception: pass
```

**The bug we're fixing:** `reason` is captured from the body, but only written to the `audit_log` table — NOT to the redemption row itself. So the parent's API has no way to surface it without a JOIN against `audit_log`, which is admin-private. C2 fixes this by adding a `rejection_reason TEXT` column to redemptions and writing the body's `reason` to it in the same UPDATE that flips the status.

## §D — Parent portal — redemption display

There are two parent-facing surfaces:

### D.1 — Public PID-store at `/parent`

The store renders inside `PORTAL_PARENT_HTML` (older parent flow). The store data comes from `GET /api/parent/store/menu?pid=<X>` (line 26813), which currently returns:

```json
{
  "ok": true,
  "balance": 47,
  "student_name": "...",
  "items": { "food": [...], "toy": [...] },
  "pending_requests": [
    { "redemption_id": …, "reward_name": …, "points_spent": …, "requested_at": … }
  ]
}
```

`pending_requests` only includes rows with `status='requested'`. **Rejected rows are not returned at all.** The frontend (line 10108 in `app.py`) iterates `_ppStoreState.pending` and renders a `<div class="pp-pending-card">` for each — a yellow "قيد المراجعة" callout. There is no current rendering path for rejected items.

### D.2 — Logged-in parent hub at `/portal/parent-hub`

`GET /api/portal/parent/me` (line 75959) returns `children` with `events`, `weekly`, `month_pos`, `month_neg` — but NO redemption history. Redemptions on this surface are only surfaced via `events` (the points-events feed) which records redemption-related debits without distinguishing approved-vs-rejected.

### Decision for C8

The owner's intent is "show rejection reasons to parents". The public `/parent` store is where parents interact with rewards — it's the natural surface. We'll:

1. Extend `/api/parent/store/menu` to also return `recent_rejected` (last 5 `status='rejected'` rows for this student, with `rejection_reason` + `rejected_at`).
2. Add a new rendering block in `_ppRenderStore` (between balance and pending-cards) that shows each rejected row in an orange callout with the reason inline.

This keeps the change scoped to the existing surface — no new routes, no schema migration on the parent side, no changes to `/portal/parent-hub`.

## §E — Proposed fix for rejection display

Plan:
1. **C2 schema:** add `rejection_reason TEXT` column to `redemptions` via idempotent ALTER TABLE in the schema_migrations block + tag-gate it.
2. **C2 endpoint update:** the reject endpoint writes `rejection_reason` to the column in the same UPDATE statement (so existing audit-log behavior remains as a belt-and-suspenders trail).
3. **C5 history endpoint:** SELECTs `rejection_reason` so the staff history tab can display it inline on rejected rows.
4. **C8 parent backend:** `/api/parent/store/menu` adds `recent_rejected: [{redemption_id, reward_name, points_spent, rejection_reason, rejected_at}]` (last 5).
5. **C8 parent frontend:** new `_ppRenderRejected` block in the store-render loop, styled with the spec's `.rejection-reason` CSS variant.

## §F — Existing tabs in `POINTS_MANAGE_HTML`

8 tabs today (line 76228-76235):

| key | label |
|---|---|
| `behaviors` | السلوكيات |
| `rewards` | المكافآت |
| `redemptions` | الاستبدالات |
| `requests` | طلبات أولياء الأمور (with badge count) |
| `reports` | التقارير |
| `notifications` | إشعارات الواتساب |
| `parents` | أولياء الأمور |
| `settings` | إعدادات |

We'll add 2 more (C6 + C7):
- `pending-delivery` → "في انتظار التسليم" (with delivered-pending badge count)
- `history` → "سجل العمليات"

## §G — Implementation summary

| Commit | File / section | Type |
|---|---|---|
| C1 | `reports/delivery_and_rejection_discovery.md` | doc-only |
| C2 | `app.py` schema_migrations block (around line 8100) | ALTER TABLE rejection_reason + `tag='redemption_rejection_reason_v1'` gate; also patches `api_pts_redeem_reject` to UPDATE the column |
| C3 | `app.py:36228` `api_pts_redeem_deliver` | widen permission to `_can_manage_points`; add 404 + 400 friendly errors; richer response |
| C4 | new endpoint near C3 | POST `/api/points/redemptions/<id>/undeliver` — same permission, flips `delivered → pending` |
| C5 | new endpoint near C3 | GET `/api/points/history` — filterable list, gated by `_can_manage_points` |
| C6 | `POINTS_MANAGE_HTML` | new tab button + render block "في انتظار التسليم" + JS loader + delivery-mark handler |
| C7 | `POINTS_MANAGE_HTML` | new tab button + render block "سجل العمليات" + filter row + CSV export + per-row action buttons |
| C8 | `app.py:26813` `/api/parent/store/menu` + `app.py:10096` `_ppRenderStore` | `recent_rejected` field in response + new render block + scoped CSS |
| C9 | `reports/delivery_and_rejection_verification.md` | doc-only |

Estimated total: ≈700 lines net additions (≈250 backend, ≈400 UI markup+JS+CSS, ≈50 schema + helper edits).

---

🎯 **Discovery complete. 8 tabs today, 10 after this phase. One schema column missing (rejection_reason) — idempotent ALTER TABLE in C2 fixes it. One endpoint widening (deliver gate), two new endpoints (undeliver, history), one parent-facing API extension. Existing parent-portal store flow and admin-purchase flow are untouched.**
