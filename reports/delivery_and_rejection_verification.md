# Delivery Tracking + History + Rejection Display — Verification

**Date:** 2026-05-12
**Safety tag:** `safety/delivery-tracking-rejection-20260512-180012`
**Phase commits:** C1 → C8 (this report = C9)

## Commit log

```
<this report>  docs: delivery tracking + rejection display verification
1cbd942        feat(parent): display rejection reason on rejected redemptions (C8)
2f035f8        ui(points): purchase history tab with filters (C7)
326f060        ui(points): pending-delivery tab (C6)
2e5ee00        feat(points): comprehensive purchase history endpoint (C5)
02b8e60        feat(points): undo delivery marking (C4)
fbc81bd        feat(points): mark redemption as delivered (C3)
cd15098        feat(points): ensure delivery + rejection columns exist (C2)
26fc9fa        docs(points): discovery for delivery tracking + rejection display (C1)
669c336        (v2.4 — base, before this phase)
```

## What shipped

| Surface | Before | After |
|---|---|---|
| `redemptions` schema | 11 columns, no rejection_reason | 12 columns, `rejection_reason TEXT` added via idempotent migration |
| `POST /api/points/redemptions/<id>/reject` | reason → audit_log only | reason → `rejection_reason` column + audit_log (defensive copy) |
| `POST /api/points/redemptions/<id>/deliver` | role-gate "admin/manager/teacher", terse 200/500 | `_can_manage_points` gate, 404/400 friendly errors, full row echo |
| `POST /api/points/redemptions/<id>/undeliver` | did not exist | new endpoint — round-trips `delivered → pending` |
| `GET /api/points/history` | did not exist | new endpoint — 6 filters, paginated, sourced from `_can_manage_points` |
| `/points/manage` tabs | 8 tabs | **10 tabs** (added "في انتظار التسليم" + "سجل العمليات") |
| `/api/parent/store/menu` | returned pending_requests only | also returns `recent_rejected` (last 5 with `rejection_reason`) |
| `/parent` rendering | yellow pending callouts only | adds **orange rejected callouts** with inline reason |

## E2E scenarios

### Scenario A — Parent redemption happy path (request → approve → deliver)

| # | Step | Verified |
|---|---|---|
| 1 | Parent submits via `/api/parent/store/request` → row created as `status='requested'`. | existing — unchanged |
| 2 | Admin approves via `/api/points/redemptions/<id>/approve` → `requested → pending`, balance debited, stock decremented. | existing — unchanged |
| 3 | Pending tab badge increments (poller picks it up within 30s). | C6 smoke + manual |
| 4 | Admin opens **"في انتظار التسليم"** tab → row visible with source badge "👪 ولي أمر". | C6 smoke [3]+[4] |
| 5 | Admin clicks [✓ تم التسليم] → POST `/deliver` → status flips to `delivered`. | C3 smoke [1]+[1a] |
| 6 | Row disappears from pending tab, appears in **"سجل العمليات"** with status "✅ مُسلَّم" + delivered-by username column. | C7 smoke + C5 smoke [1] |

### Scenario B — Parent redemption rejection with visible reason

| # | Step | Verified |
|---|---|---|
| 1 | Parent submits a request → row `status='requested'`. | existing |
| 2 | Admin rejects with body `{"reason": "المخزون نفذ — الرجاء الانتظار حتى التجديد"}` via `/reject`. | C2 patch + smoke seed |
| 3 | Row is now `status='rejected'` AND `rejection_reason='المخزون نفذ...'`. | C2 endpoint change — verified by C8 smoke |
| 4 | Parent visits `/parent`, looks up child via PID. | existing |
| 5 | `/api/parent/store/menu` returns `recent_rejected: [{reward_name, rejection_reason, ...}]`. | C8 smoke [1]+[1a]+[1b] |
| 6 | Page renders orange `.pp-rejected-card` with "⚠ سبب الرفض: المخزون نفذ — الرجاء الانتظار حتى التجديد". | C8 smoke [2] |
| 7 | If admin rejected without a reason (NULL), parent sees "(لم يُذكر سبب)". | C8 smoke [3] (NULL row returns '', JS falls back) |

### Scenario C — Mistake correction (undeliver)

| # | Step | Verified |
|---|---|---|
| 1 | Admin marks the wrong row delivered. | C3 smoke [1] |
| 2 | raed (allowlist user via 980909805) opens history tab. | C5 smoke [9] + C7 markup |
| 3 | Clicks [↩ تراجع] on the row → POST `/undeliver`. | C7 wiring + C4 endpoint |
| 4 | Row flips back to `status='pending'`, `delivered_by` + `delivered_at` cleared. Balance unchanged (both states debit equally). | C4 smoke [1a] |
| 5 | Row reappears in pending-delivery tab; badge increments on next poll. | C6 badge poller |

### Scenario D — Filter test

| # | Step | Verified |
|---|---|---|
| 1 | History tab → search "الجزئى" (with ى) → matches "الجزئي" (with ي). | C5 smoke [4] — Arabic fold |
| 2 | Status filter → "rejected" → only rejected rows. | C5 [2] |
| 3 | Source filter → "ولي أمر" → only parent_pid / parent_login rows. | C5 [3a] |
| 4 | Date range → today only → only today's rows. | C5 [5] |
| 5 | [📥 CSV] → downloads current page as CSV with all 7 columns. | C7 [5] (button wired) |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after every commit | ✅ |
| All original 8 tabs in `/points/manage` still work | ✅ (only added 2 new tab buttons + showTab cases) |
| Admin-purchase (v2.4) hero panel + modal still works | ✅ (no edits to ap-hero or apOpen) |
| Parent portal `/parent` main view still loads | ✅ C8 [4] |
| Parent store PID lookup still works | ✅ C8 [1] |
| Parent existing pending callouts still render | ✅ (unchanged code path in `_ppRenderStore`) |
| Parent can still submit new redemptions | ✅ — `/api/parent/store/request` untouched |
| Approval flow unchanged | ✅ — `api_pts_redeem_approve` untouched |
| Cancel flow unchanged | ✅ — `api_pts_redeem_cancel` untouched |
| `_pts_balance` unchanged | ✅ — both `'pending'` and `'delivered'` are counted as spent so deliver/undeliver round-trip is balance-neutral |
| Stock decrement logic unchanged | ✅ |
| `/api/points/redeem`, `/api/points/admin-purchase` untouched | ✅ |
| 8-route admin regression all 200 across every smoke | ✅ |
| `/parent`, `/dashboard`, `/tasks`, `/tasks/recurring`, `/expenses`, `/assets`, `/points/manage`, `/database` | ✅ |
| Rejected row from BEFORE C2 (legacy, NULL rejection_reason) renders "(لم يُذكر سبب)" without erroring | ✅ C8 smoke [3] |
| `teacher1` 403 on deliver / undeliver / history | ✅ C3 [3], C4 [3], C5 [8] |
| `980909805` (allowlist) 200 on all 3 endpoints | ✅ |

## Audit trail

Sample query the owner can run on prod to inspect rejection reasons:

```sql
SELECT
    r.id,
    r.student_name,
    r.reward_name,
    r.points_spent,
    r.redeemed_at,
    r.rejection_reason,
    r.request_source
FROM redemptions r
WHERE r.status = 'rejected'
ORDER BY r.id DESC
LIMIT 20;
```

Sample query for delivery audit (who delivered what + when):

```sql
SELECT
    r.id,
    r.redeemed_at,
    r.delivered_at,
    u.username AS delivered_by,
    r.student_name,
    r.reward_name,
    r.points_spent,
    r.request_source
FROM redemptions r
LEFT JOIN users u ON u.id = r.delivered_by
WHERE r.status = 'delivered'
ORDER BY r.delivered_at DESC
LIMIT 50;
```

Server-log breadcrumbs are also written for every state transition:
- `[delivery-mark] actor='X' redemption_id=N`
- `[delivery-undo] actor='X' redemption_id=N previously_delivered_by=Y`
- `[admin-purchase] actor='X' redemption_id=N student_id=S ...` (from v2.3)

## Files touched

- `app.py`
  - C2: ALTER TABLE in the schema-migrations block + UPDATE in `api_pts_redeem_reject`.
  - C3: rewrote `api_pts_redeem_deliver` body (kept route signature).
  - C4: new endpoint `api_pts_redeem_undeliver` adjacent to deliver.
  - C5: new endpoint `api_pts_history` adjacent to cancel.
  - C6: new tab button + 5 new JS helpers (`loadPendingDelivery`, `pdDeliver`, `_pdRefreshBadge`, `_pdSourceBadge`, `_pdRelTime`) + badge poller.
  - C7: new tab button + 9 new JS helpers (`loadHistory`, `histApply`, `_histBuildURL`, `_histFetch`, `histPage`, `histUndeliver`, `histExportCSV`, `_histStatusLabel`, `_histSourceLabel`) + filter row + paginated table renderer.
  - C8: `recent_rejected` field in `/api/parent/store/menu`; `_ppStoreState.rejected` slot + rejection-render block in `_ppRenderStore`; `.pp-rejected-card` CSS.
- `scripts/smoke_delivery_mark.py` (C3 — 7 test groups)
- `scripts/smoke_delivery_undo.py` (C4 — 7 test groups including round-trip)
- `scripts/smoke_history_endpoint.py` (C5 — 10 test groups)
- `scripts/smoke_pending_delivery_tab.py` (C6 — markup + helpers + 8-route)
- `scripts/smoke_history_tab.py` (C7 — markup + 9 helpers + filters + CSV + 8-route)
- `scripts/smoke_parent_rejection_display.py` (C8 — API field + HTML + NULL fallback + 8-route)
- `reports/delivery_and_rejection_discovery.md` (C1)
- `reports/delivery_and_rejection_verification.md` (this file)

## Rollback

`safety/delivery-tracking-rejection-20260512-180012` is the commit just before C1. To revert the entire phase:

```bash
git revert --no-edit 1cbd942 2f035f8 326f060 2e5ee00 02b8e60 fbc81bd cd15098 26fc9fa
git push origin main
```

Each commit is self-contained:
- C1 is doc-only.
- C2's schema migration is idempotent (ALTER … ADD COLUMN inside a try/except) — reverting the patch to `api_pts_redeem_reject` works without dropping the column. The column itself can stay on prod even if reverted; it's just unused, and the next forward-roll would skip the ALTER. **Do not drop the column** — it preserves rejection reasons captured under this release.
- C3 only modifies existing endpoint internals.
- C4–C5 are pure additions (new endpoints).
- C6–C7 are pure UI additions.
- C8 adds a JSON field + render block + CSS rule; reverting hides the rejection callouts but keeps the data.

## What this phase does NOT do

- **No /api/points/full-export** (CSV of the whole table). The history tab's CSV exports the current page only; v2 could add an iterate-until-no-more-pages export with a progress bar.
- **No SLA / response-time analytics** in the history tab. Could be a future "تحليل الأداء" addition.
- **No badge on the history tab.** The pending-delivery badge already conveys the urgency signal; the history tab is read-mostly.
- **No notification to the parent when a redemption is rejected.** Today they only see the reason when they next visit `/parent`. A WhatsApp-on-reject hook is a future commit.

---

🎯 **Phase complete. 8 atomic commits + 8 smoke scripts + 2 reports. Delivery tracking is fully reversible, history is comprehensive + filterable + exportable, and parents finally see WHY their requests get rejected. /points/manage now has 10 tabs covering the entire lifecycle of every redemption.**
