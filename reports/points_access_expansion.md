# Points Management Access Expansion — Verification

**Date:** 2026-05-12
**Safety tag:** `safety/points-access-raed-ahmed-20260512-153438`
**Phase commits:** C1 + C2 (this report = C3)

## Commit log

```
<this report>  docs: points access expansion verification
414a50e        feat(points): show points-manage link to authorized non-admins (C2)
0ea4ec6        feat(points): grant raed + ahmed_ibrahim access to points management (C1)
6ab591f        (assignee dropdown verification — point of departure)
```

## Change summary

Granted full `/points/manage` + `/api/points/*` admin-equivalent access to:

- `raed`
- `ahmed_ibrahim`

Implementation:

| Layer | Mechanism |
|---|---|
| Allowlist | `POINTS_MANAGER_USERNAMES = {"raed", "ahmed_ibrahim"}` |
| Boolean helper | `_can_manage_points(user)` — True for admin role OR allowlist username |
| Role spoofing (scoped) | `_pts_user_role(user)` returns `"admin"` for allowlist usernames — flows through every `role in ("admin", "manager")` check inside the points subsystem |
| Strict-admin gate alternative | `_require_points_admin_response()` — drop-in replacement for `_require_admin_response()` inside the 10 points endpoints that use the strict gate |
| UI gate | `body[data-can-manage-points="1"]` injected on `/dashboard` render, paired with `.mx-points-manage-link` class on the sidebar + dashboard card |
| Page route | `/points/manage` now checks `_can_manage_points(user)` instead of `role != "admin"` |

## Endpoints + routes affected

Page route:

| Route | Before | After |
|---|---|---|
| `GET /points/manage` | `role == "admin"` redirect-else | `_can_manage_points(user)` redirect-else |

Points API endpoints whose strict admin gate moved to the new helper:

| Endpoint | Old gate | New gate |
|---|---|---|
| `GET /api/points/reports/admin` | `_require_admin_response()` | `_require_points_admin_response()` |
| `POST /api/points/rewards` | strict | points-admin |
| `PATCH /api/points/rewards/<id>` | strict | points-admin |
| `POST /api/points/redemptions/<id>/cancel` | strict | points-admin |
| `POST /api/points/redemptions/<id>/approve` | strict | points-admin |
| `POST /api/points/redemptions/<id>/reject` | strict | points-admin |
| `GET /api/points/notifications` | strict | points-admin |
| `POST /api/points/digest/run` | strict | points-admin |
| `GET /api/points/digest/next` | strict | points-admin |
| `POST /api/points/notifications/<id>/sent` | strict | points-admin |

≈15 other points endpoints (behaviors CRUD, grant, rewards GET, redeem flow, reports/student, reports/group, levels, board, etc.) didn't use the strict gate — they use `_pts_user_role(user)` membership checks which automatically honour the spoof.

Routes that DID NOT move (still strict admin):
- `/api/backups/*`
- `/api/admin/table-audit`
- `/api/admin/parents/*`
- `/admin/permissions`
- `/database`
- `/admin/violations*`

## E2E scenario walkthrough

| # | Step | Expected | Verified |
|---|---|---|---|
| 1 | admin → `/dashboard` | sees points-manage card | ✅ existing |
| 2 | admin → `/points/manage` | 200 | ✅ C1 [1] |
| 3 | raed → login | dashboard with role=reception | ✅ C2 [2] |
| 4 | raed → `/dashboard` body | `data-can-manage-points="1"` injected | ✅ C2 [2] |
| 5 | raed → sidebar | "إدارة نظام النقاط" entry visible (CSS rule un-hides) | ✅ via class + CSS rule (C2 [1]+[5]) |
| 6 | raed → dashboard card | `#dh-points-manage` revealed by extended JS block | ✅ C2 [6] |
| 7 | raed → click → `/points/manage` | 200 | ✅ C1 [2] |
| 8 | raed → POST `/api/points/rewards` | 200 (creates row) | ✅ C1 [5b] |
| 9 | raed → GET `/api/points/reports/admin` | 200 | ✅ C1 [6b] |
| 10 | raed → POST `/api/points/behaviors` | 200, `is_global=1` (admin-equivalent grant) | ✅ C1 [7] |
| 11 | ahmed_ibrahim → same flow | identical to raed | ✅ C1 [3] + C2 [3] |
| 12 | teacher1 → `/points/manage` | 302 (still blocked) | ✅ C1 [4] |
| 13 | teacher1 → POST `/api/points/rewards` | 403 (still blocked) | ✅ C1 [5c] |
| 14 | teacher1 → GET `/api/points/reports/admin` | 403 (still blocked) | ✅ C1 [6c] |
| 15 | raed → `/database` (sanity) | 403 (still blocked) | ✅ C1 [8a] |
| 16 | raed → `/admin/permissions` (sanity) | 403 (still blocked) | ✅ C1 [8b] |
| 17 | reception (non-allowlist) → `/dashboard` | `data-can-manage-points="0"`, link hidden | ✅ C2 [4] |
| 18 | student/parent → `/dashboard` | redirected away from dashboard (existing rule) | ✅ existing |

## Regression checklist

| Check | Result |
|---|---|
| admin retains full access | ✅ C1 [1]+[5a]+[6a] |
| raed has full access | ✅ C1 [2]+[5b]+[6b]+[7]; C2 [2] |
| ahmed_ibrahim has full access | ✅ C1 [3]; C2 [3] |
| teacher1 still blocked | ✅ C1 [4]+[5c]+[6c] |
| Non-allowlist reception still blocked | ✅ C2 [4] (data-can-manage-points=0) |
| Students/parents still blocked | ✅ existing dashboard redirect rule (no change) |
| raed CANNOT access `/database` | ✅ C1 [8a] |
| raed CANNOT access `/admin/permissions` | ✅ C1 [8b] |
| Strict `_require_admin_response()` callsites preserved | ✅ 17 callsites untouched (backups + table-audit + parent admin) |
| `/api/backups/run`, `/api/admin/parents`, etc. still strict | ✅ same source code as before |
| 8-route admin regression all 200 | ✅ C1 [9] + C2 [8] |
| `/parent`, `/dashboard`, `/tasks`, `/tasks/recurring`, `/expenses`, `/assets`, `/points/manage`, `/database` all 200 | ✅ |
| No JS console errors expected (reveal block guarded by `&&`) | ✅ |
| App imports cleanly after each commit | ✅ |
| CSS pattern matches existing `mx-expenses-link` / `mx-tasks-link` (no new framework concept) | ✅ |
| Sidebar entry still semantically labeled "إدارة نظام النقاط" | ✅ (only class changed, text + icon intact) |
| No schema change | ✅ |
| No data mutation in C1/C2 | ✅ (smoke creates + deletes its own test rows) |

## Files touched

- `app.py`
  - Added `POINTS_MANAGER_USERNAMES`, `_can_manage_points`, `_require_points_admin_response` (C1).
  - Modified `_pts_user_role` to spoof allowlist usernames as `"admin"` inside the points subsystem (C1).
  - Modified `_pts_can_admin` to delegate to `_can_manage_points` (C1).
  - Updated `/points/manage` route to use `_can_manage_points` (C1).
  - Replaced `_require_admin_response()` with `_require_points_admin_response()` in 10 points endpoints (C1).
  - Added CSS rule for `.mx-points-manage-link` (C2).
  - Added `dataset.canManagePoints` body attribute injection (C2).
  - Added `POINTS_MANAGE_ACCESS_PLACEHOLDER` substitution in `/dashboard` render (C2).
  - Updated sidebar entry class `mx-admin-only` → `mx-points-manage-link` (C2).
  - Added `mx-points-manage-link` class to `#dh-points-manage` card (C2).
  - Extended dashboard JS reveal block to also fire for `canManagePoints === "1"` non-admins (C2).
- `scripts/smoke_points_access_c1.py` — 9 backend test groups (route, API endpoints, sanity-other-admin-pages, regression).
- `scripts/smoke_points_access_c2.py` — 9 UI test groups (data-attribute injection, CSS rule, JS reveal, role-by-role expectations).

## Rollback

`safety/points-access-raed-ahmed-20260512-153438` is the commit immediately before C1. To revert both commits:

```bash
git revert --no-edit 414a50e 0ea4ec6
git push origin main
```

Both commits are self-contained. C2 depends on C1 (the `_can_manage_points` helper). Reverting both restores the strict admin-only points policy.

## Future extensibility note

To **grant** access to more users:
```python
POINTS_MANAGER_USERNAMES = {"raed", "ahmed_ibrahim", "new_user"}
```
(Single-line change in `app.py`, no migration needed.)

To **revoke** access:
```python
POINTS_MANAGER_USERNAMES = {"ahmed_ibrahim"}  # raed removed
```

For more granular control (per-user toggleable from the admin permissions UI), the recommended migration path is a `users.can_manage_points INTEGER DEFAULT 0` column with a dual-path schema seed + admin UI flip + replacing `_can_manage_points` body to `SELECT can_manage_points FROM users WHERE username=?`. The single-allowlist approach was chosen for v1 because the change set is bounded and the audit trail (a code commit) is auditable in git history.

---

🎯 **Points management access expansion complete. raed + ahmed_ibrahim get full points-system admin rights via a narrow allowlist that does NOT widen any other admin gate. UI surfaces follow the existing `mx-*-link` pattern.**
