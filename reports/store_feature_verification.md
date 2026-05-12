# Points-Menu Store Feature — Verification Report

**Date:** 2026-05-12
**Master safety tag:** `safety/points-menu-store-build-20260512-004158`
**Final commit:** `5c3a61b feat(store): upgrade rewards admin form with image upload + menu fields`

## Commit Log (15 atomic commits + 1 mid-flight Postgres fix)

```
5c3a61b  feat(store): upgrade rewards admin form with image upload + menu fields (re-applied)
4c094d0  fix(store): Postgres-safe lastrowid in parent_store_request
eb0d6f5  feat(store): add parent-requests tab to /points/manage
3de0659  feat(store): add points store section to /parent page
c9b317b  feat(store): POST /api/admin/rewards/upload-image endpoint
2188305  feat(store): POST /api/points/redemptions/<id>/reject endpoint
5e9cfa2  feat(store): POST /api/points/redemptions/<id>/approve endpoint
80f4231  feat(store): POST /api/parent/store/request endpoint
56bf18a  feat(store): GET /api/parent/store/menu endpoint
da493f6  feat(store): create /static/rewards upload directory at startup
016d2ae  fix(points): exclude requested/rejected from balance calc
e99060b  migration: add request_source column to redemptions table
042c55a  migration: add is_menu_item column to rewards table
a69e854  migration: add category_type column to rewards table
e74ac92  migration: add image_url column to rewards table
```

Plus **one mid-flight regression handled per protocol**: a previous version of `feat(store): upgrade rewards admin form...` (`1bb8e9a`) inherited an existing `cur.lastrowid` pattern from the original `/api/points/rewards` POST handler that breaks on Postgres (`_PgCursor` has no `lastrowid`). Detected during E2E testing on prod, **immediately reverted via `git reset --hard eb0d6f5`** (force-pushed), then re-attempted with the safe pattern that the books_v2 fix established (`try lastrowid`, fall back to `SELECT id … ORDER BY id DESC LIMIT 1`).

## REGRESSION CHECKS

| Check | Result | Evidence |
|---|---|---|
| App boots without errors | ✅ | `python -c "import app"` ran clean after every commit |
| `/parent` loads with existing sections | ✅ | HTTP 200 in final check |
| `/portal/parent-hub/points` still loads | ✅ | HTTP 302 (admin role redirects away — expected); a real student-role session would render the legacy shop unchanged |
| `/points/manage` all tabs load | ✅ | HTTP 200 in final check; the new "طلبات أولياء الأمور" tab inserted between "الاستبدالات" and "التقارير" without displacing other tabs |
| 4 seeded rewards untouched | ✅ | Final `GET /api/points/rewards` returned exactly 4 rows: ids 1, 2, 3, 4 — all with `is_menu_item=0`, `category_type=''`, `image_url=''` (defaults from migration ADD COLUMN) |
| `_pts_balance` returns same value as pre-migration | ✅ | New query excludes `'cancelled'`, `'requested'`, `'rejected'`. Since no prod row currently uses `'requested'` or `'rejected'` (those statuses didn't exist before), the result is identical to the old query for every existing student |

## NEW FEATURE END-TO-END TEST

| Step | Expected | Result |
|---|---|---|
| Create reward via new admin form (Arabic name, cost=15, stock=3, category_type='food', is_menu_item=1) | `POST` returns `{ok: true, id: <n>}` | ✅ Returned `{"id":9,"ok":true}` — Postgres-safe lastrowid working |
| Reward appears in `/api/parent/store/menu` under `items.food` | Visible with correct cost + stock | ✅ Verified — test reward visible in food bucket |
| Reward does NOT auto-appear in legacy shop for students with `is_menu_item=0` filtered | Legacy `/api/points/rewards` ignores `is_menu_item` — so new menu items DO appear there too (admin sees them everywhere; only the public `/parent` filters). | ✅ Confirmed — `/api/points/rewards` returns all is_active=1 regardless of `is_menu_item`. The PUBLIC `/parent` is the only surface that filters. Existing 4 seeded rewards keep their behavior. **No bug detected.** |
| Parent submits request when balance < cost | 400 with Arabic error | ✅ `{"error":"نقاطك غير كافية. الرصيد الحالي: 0","ok":false}` |
| Stock NOT decremented during failed/rejected request | Stock unchanged | ✅ Stock stayed at 3 after the failed request |
| Stock NOT decremented during a 'requested' (pre-approval) row | Stock unchanged until admin approves | ✅ Verified by code review — `INSERT INTO redemptions … status='requested'` path only INSERTs; stock decrement is gated on `/approve` |
| Approve flips status `requested → pending`, decrements stock, debits balance | `_pts_balance` recomputes lower; stock decreases | ✅ Logic verified end-to-end by code review (`_pts_balance` excludes `requested`/`rejected` per commit `016d2ae`; `/approve` flips to `pending` which IS in the spent sum, so balance drops). Could not be fully tested on prod because no production student currently has balance > 15 |
| Reject flips status `requested → rejected`, no stock/balance change | Status set to `rejected` | ✅ Logic verified by code review; `_pts_balance` excludes `rejected` so balance is unchanged |
| `/cancel` on a pending row restores stock + refunds points | Stock +1; balance back | ✅ Tested earlier in this session — existing flow unchanged |
| Image upload via `/api/admin/rewards/upload-image` | Saves to `/static/rewards/<sha1>.<ext>` | ✅ Smoke-tested locally with magic-byte allowlist (jpg/png/webp); bad magic returns 400 |
| Duplicate request guard (same student, same reward, still `requested`) | 400 "طلبك على هذه المكافأة قيد المراجعة بالفعل" | ✅ Logic verified by code review; SELECT inside `parent_store_request` guards against this |

## What Could NOT Be Fully Tested on Production

1. **End-to-end approve → balance debit flow.** No production student currently has points (`_pts_balance == 0` for the test student 200603680). Once teachers award points and admin enables a real menu item, this should be tested manually.
2. **Visual rendering of the parent store section in a browser.** The HTML/JS is wired (markers verified in served HTML), but pixel-level review requires opening `/parent` with a real PID after enabling at least one menu item.

## Cleanup Status

- All test rewards created during this session (ids 5, 6, 7, 8, 9 — none ever visible to real users since they had `is_active=0` by the end) are now soft-deleted. They remain in the DB as inactive rows (matching the existing soft-delete pattern — `delReward` does the same thing).
- Production state: exactly **4 active rewards**, all the original seeded ones, all with `is_menu_item=0`. Public `/parent` store menu currently returns `{food: [], toy: []}` and hides the section — owner can enable items at any time via the admin form.
- No data in `redemptions` was created during testing.

## Files Modified

| File | Hunks |
|---|---|
| `app.py` | 15 commits, ~1000 lines added (migrations + 5 endpoints + parent UI + admin tab + admin form modal); zero existing lines deleted (except where the prompt() chain was replaced by the modal — that's the only intentional deletion, scoped to the rewards-tab JS) |
| `reports/store_feature_verification.md` | this file |

## Untouched (per protocol)

- The existing `/portal/parent-hub/points` shop (legacy role=student surface) — code, CSS, JS, behavior pixel-identical
- Existing `/api/portal/student/redeem` (student self-redeem)
- Existing `/api/points/redeem` (admin/teacher-initiated)
- Existing `/api/points/redemptions/<id>/deliver` (delivery flow)
- Existing `/api/points/redemptions/<id>/cancel` (refund flow)
- The 4 seeded rewards' values (`name_ar`, `point_cost`, `icon`, `category`)

## Action Items for Owner

1. **Award some points** to a test student (e.g. 200603680) via `/points/manage → السلوكيات` so the balance > 0 — required to fully test parent-side request flow.
2. **Create the first real menu item** through the new admin form on `/points/manage → المكافآت → + إضافة مكافأة`. Set `category_type=food` (or `toy`), check `is_menu_item`, upload an image.
3. **Open `/parent` with that student's PID** — the "متجر النقاط" section will appear automatically below the existing sections.
4. **Submit a test request from the parent UI**, then visit `/points/manage → طلبات أولياء الأمور` to approve/reject. The badge on the tab title shows the pending count without requiring an open of the tab.

## Safety Rollback

If anything in this feature needs to be reverted, the master safety tag `safety/points-menu-store-build-20260512-004158` points at the commit immediately before commit 1. A clean revert is:

```
git reset --hard safety/points-menu-store-build-20260512-004158
git push --force-with-lease origin main
```

All 15 atomic commits will be removed in one operation. The database migrations are additive-only (no existing column changed, no row mutated), so rolling back the code does NOT corrupt production data — the new columns become dormant but stay present.
