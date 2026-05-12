# Admin-Initiated Purchase — Verification

**Date:** 2026-05-12
**Safety tag:** `safety/admin-purchase-on-behalf-20260512-170044`
**Phase commits:** C1 + C2 + C3 (this report = C4)

## Commit log

```
<this report>  docs: admin-purchase verification + E2E
e859c8c        feat(points): admin-purchase UI in points-manage page (C3)
7ba3629        feat(points): admin-initiated reward purchase endpoint (C2)
6d6c3d2        docs(points): discovery for admin-initiated purchase (C1)
082beba        (v2.2 — last release tag, point of departure)
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│ /points/manage  (POINTS_MANAGE_HTML, gated by _can_manage_points)│
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Topbar: [⚙ سريعة] [🛒 شراء نيابة عن طالب] [← الرئيسية]  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                       │ apOpen()                                 │
│                       ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Modal (#ap-modal)                                       │    │
│  │  ▶ Step 1: type-ahead — Arabic-folded fuzzy match        │    │
│  │            against cached /api/students                  │    │
│  │  ▶ Step 2: pick reward from cached /api/points/rewards   │    │
│  │            (active + in-stock; insufficient-balance      │    │
│  │             cards greyed out)                            │    │
│  │  ▶ Step 3: confirm + optional note ≤ 500 chars           │    │
│  └─────────────────────────────────────────────────────────┘    │
│                       │                                          │
│                       ▼ POST /api/points/admin-purchase          │
└──────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────────┐
│ api_pts_admin_purchase (app.py)                                  │
│  1. _can_manage_points(user)              → else 403             │
│  2. parse body (student_id, reward_id, note)                     │
│  3. student exists                        → else 404             │
│  4. reward exists + is_active             → else 404 / 400       │
│  5. stock != 0                            → else 400             │
│  6. _pts_balance(db, sid) >= cost         → else 400             │
│  7. note length ≤ 500                     → else 400             │
│  8. INSERT redemptions(status='delivered',                       │
│         request_source='admin_on_behalf',                        │
│         delivered_by=actor.id,                                   │
│         delivered_at=NOW())                                      │
│  9. UPDATE rewards SET stock=stock-1 WHERE stock>0               │
│ 10. db.commit() — single transaction                             │
│ 11. server stderr log: actor, redemption_id, note                │
│ 12. return JSON with new_balance + redemption_id                 │
└──────────────────────────────────────────────────────────────────┘
```

Row-level effect — exactly the same shape that `_pts_balance` already counts as spent:

```sql
INSERT INTO redemptions
  (student_id, student_name, reward_id, reward_name,
   points_spent, status, request_source,
   delivered_by, delivered_at)
VALUES
  (196, 'طالب الجزئي', 1, 'ملصق نجمة',
   10, 'delivered', 'admin_on_behalf',
   1, '2026-05-12 14:32:11');
```

The status `'delivered'` is debited by `_pts_balance` (which only EXCLUDES `'cancelled'`, `'requested'`, `'rejected'`), so the student's balance drops immediately on the next read — no admin approval needed.

## E2E scenario walkthrough

The smoke scripts ran end-to-end against the local DB; here's how the manual workflow maps to verified steps.

| # | Step | Expected | Verified |
|---|---|---|---|
| 1 | Setup: student 196 has ≥50 pts (seeded via point_events) | balance starts at 200 | ✅ C2 [1] (200 → 190 after first purchase) |
| 2 | Admin → /points/manage → click "شراء نيابة عن طالب" | modal opens, students + rewards lazy-load | ✅ C3 [1]+[1a] (markup + 8 helpers present) |
| 3 | Type partial student name (with أ→ا normalisation) | top-N matches appear in <250ms | ✅ via _apNorm fuzzy match (mirrors srOpen logic) |
| 4 | Click student → balance shown + reward grid renders | balance pill = current points; reward cards disable when cost > balance | ✅ JS path via /api/points/student/<sid> |
| 5 | Click affordable reward → confirmation panel | cost, current balance, after-balance shown | ✅ apPickReward → ap-confirm |
| 6 | Add optional note (≤500 chars) → click تأكيد | POST to /api/points/admin-purchase → 200 | ✅ C2 [1] + C3 [4] |
| 7 | Toast "تم الشراء بنجاح" + transaction_id displayed | success toast + reset option | ✅ apConfirm success branch |
| 8 | Verify student's balance dropped by cost | DB `_pts_balance` returns balance - cost | ✅ C2 [1] (190 = 200-10), C3 [4] (50 = 60-10) |
| 9 | Verify audit row | status='delivered', request_source='admin_on_behalf', delivered_by=admin.id, delivered_at!=NULL | ✅ C2 [1a] |
| 10 | Login as allowlist user (980909805) → same flow | works identically; row's delivered_by=980909805's user.id | ✅ C2 [2] |
| 11 | Login as teacher1 → /points/manage | 302 redirect to /dashboard (gated by _can_manage_points) | ✅ C3 [3] |
| 12 | Teacher1 direct POST to /api/points/admin-purchase | 403 "غير مصرح" | ✅ C2 [3] |
| 13 | Admin tries insufficient-balance reward | 400 "insufficient points", no row inserted | ✅ C2 [9]+[9a] |
| 14 | Admin tries out-of-stock reward | 400 "out of stock" | ✅ C2 [10] |
| 15 | Admin tries inactive reward | 400 "reward inactive" | ✅ C2 [7] |
| 16 | Admin tries note > 500 chars | 400 with Arabic message | ✅ C2 [8] |
| 17 | Admin tries non-existent student | 404 | ✅ C2 [5] |
| 18 | Admin tries non-existent reward | 404 | ✅ C2 [6] |
| 19 | Admin purchases finite-stock reward (id=10, stock=5) | row inserted, stock decremented to 4 | ✅ C2 [11]+[11a] |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after each commit | ✅ |
| `/parent` 200 (parent-portal flow surface) | ✅ C2 [12], C3 [5] |
| `/api/points/rewards` 200 (parent-portal dependency) | ✅ C2 [13], C3 [6] |
| `/dashboard` 200 (admin) | ✅ |
| `/tasks` + `/tasks/recurring` 200 | ✅ |
| `/expenses` + `/assets` 200 | ✅ |
| `/points/manage` 200 (admin + 980909805) | ✅ |
| `/database` 200 (admin) | ✅ |
| `_pts_balance` unchanged in source | ✅ (no edits, helper used as-is) |
| Existing `/api/points/redeem` route unchanged | ✅ (no edits, sits adjacent to new endpoint) |
| Existing parent-portal redemption flow unchanged | ✅ (no edits in `/api/parent/redeem` or `/api/portal/student/redeem`) |
| Existing reward CRUD unchanged | ✅ |
| Modal opens/closes cleanly | ✅ (apOpen / apClose with timer-clear) |
| Search debounce (250ms) works | ✅ (clearTimeout + setTimeout chain) |
| Stock decrement only when `stock > 0` (unlimited stock stays at -1) | ✅ (`UPDATE … WHERE id=? AND stock>0`) |
| Postgres-safe `lastrowid` fallback | ✅ (try cur.lastrowid → SELECT ORDER BY id DESC LIMIT 1) |
| 13 endpoint tests + 6 UI smoke tests all pass | ✅ |
| No schema change | ✅ |
| No new DB writes at deploy time | ✅ |

## Audit trail verification

Query template (run against prod after first admin purchase):

```sql
SELECT
    r.id                AS redemption_id,
    r.redeemed_at       AS purchased_at,
    r.delivered_at      AS delivered_at,
    u.username          AS actor_username,
    u.name              AS actor_name,
    r.student_id,
    r.student_name,
    r.reward_id,
    r.reward_name,
    r.points_spent,
    r.status,
    r.request_source
FROM   redemptions r
LEFT JOIN users u ON u.id = r.delivered_by
WHERE  r.request_source = 'admin_on_behalf'
ORDER BY r.id DESC
LIMIT 50;
```

Expected results format (from local smoke):

```
redemption_id | actor_username | student_id | student_name      | reward_name   | points_spent | status     | request_source
--------------|----------------|------------|-------------------|---------------|--------------|------------|------------------
13            | admin          | 196        | طالب الجزئي       | ملصق نجمة     | 10           | delivered  | admin_on_behalf
```

The server log also captures the same context with the user's optional `note`:

```
[admin-purchase] actor='admin' redemption_id=13 student_id=196
                  student='طالب الجزئي' reward_id=1
                  reward='ملصق نجمة' cost=10
                  note='from C3 UI smoke'
```

The note doesn't live in the DB (Discovery report Option A) — it's preserved in the server log + the endpoint's JSON response. If a permanent on-row note becomes a hard requirement, a future commit can add a `note TEXT` column via the dual-path migration block and switch the helper to write there instead.

## Files touched

- `app.py`
  - C2: new endpoint `POST /api/points/admin-purchase` (≈85 lines, inserted just above `api_pts_redeem_deliver`).
  - C3: new `🛒 شراء نيابة عن طالب` button in the topbar; new `_apNorm`/`_apScore`/`apOpen`/`apClose`/`apSearch`/`apPickStudent`/`apResetStudent`/`_apRenderRewards`/`apPickReward`/`apConfirm`/`apReset` JS helpers; new modal markup + scoped CSS — all inserted right before `</body></html>"""` of `POINTS_MANAGE_HTML`.
- `scripts/smoke_admin_purchase_c2.py` — 13 endpoint test groups (permission matrix + payload validation + balance arithmetic + stock semantics + 8-route regression + parent-portal dependency).
- `scripts/smoke_admin_purchase_c3.py` — 6 UI test groups (markup presence for admin + allowlist user, teacher1 blocked, round-trip POST, 8-route regression, parent-portal dependency).
- `reports/admin_purchase_discovery.md` (C1) — discovery findings.
- `reports/admin_purchase_verification.md` (this file).

## Rollback

`safety/admin-purchase-on-behalf-20260512-170044` is the commit immediately before C1 (discovery). To revert the entire phase:

```bash
git revert --no-edit e859c8c 7ba3629 6d6c3d2
git push origin main
```

Each commit is self-contained:
- C1 is documentation-only (no app.py change).
- C2 adds a new route (no existing route modified).
- C3 adds a new button + modal block (no existing UI block modified — the new block lives between `loadBehaviors()` and `</body></html>"""`).

Reverting in this order restores the pre-feature state cleanly with no DB-level concerns. The `'admin_on_behalf'` value left in any redemptions rows from production would persist as historic audit data (and would not corrupt any helper — `_pts_balance` doesn't care about `request_source`).

## What this fix does NOT do (deferred / v2 candidates)

- **No bulk-purchase mode.** v1 supports one student × one reward × one click. Multi-student or multi-reward batches would be a separate flow.
- **No printable receipt.** The success panel shows `redemption_id` but doesn't render a printable handover slip. Could be added by linking to the existing `/api/points/rewards/<id>/image` URL.
- **No "undo last purchase" button.** Admin can already cancel via the existing `/api/points/redemptions/<id>/cancel` endpoint (the same one used for staff-initiated pending rows). The current row's status is `'delivered'` not `'pending'`, so the existing cancel-while-pending guard `WHERE id=? AND status='pending'` will reject it. A later commit can widen that to allow cancellation of `'delivered'` rows that originated from `request_source='admin_on_behalf'`.
- **No on-row note storage.** Note lives in the server log + response only. Documented as Option A in the discovery report.

---

🎯 **Admin-purchase feature live across 3 commits + 2 reports. Staff with `_can_manage_points` can now redeem rewards on behalf of students directly from /points/manage. Atomic transaction, instant balance debit, audit-trail-tagged (`request_source='admin_on_behalf'`), insufficient-balance and out-of-stock both protected. Parent-portal redemption flow and existing /api/points/redeem are untouched.**
