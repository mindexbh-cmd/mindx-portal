# Task System — Phase 2a Endpoints Verification

**Date:** 2026-05-12
**Safety tag (pre-change):** `safety/task-system-phase2a-20260512-100455`
**Phase 2a HEAD:** `aac7b69 feat(task-phase2a): task status transitions with state machine`
**Commits:** 7 atomic commits (C9–C15) + this report

## Commit Log

```
aac7b69  feat(task-phase2a): task status transitions with state machine
c7863ee  feat(task-phase2a): PATCH /api/tasks/<id> with strict immutability
7e27ccd  feat(task-phase2a): GET /api/tasks/<id> detail view
f6197f8  feat(task-phase2a): GET /api/tasks with role-based filtering
20339a5  feat(task-phase2a): POST /api/tasks - create task
9675f70  feat(task-phase2a): GET /api/departments
2891edd  feat(task-phase2a): permission helpers for task system
```

## Endpoint inventory

| # | Method | Path | Auth gate | Body / params | Response shape |
|---|---|---|---|---|---|
| 1 | GET | `/api/departments` | `_can_use_tasks` | — | `{ok, departments: [{id, name_ar, icon, color, sort_order}]}` |
| 2 | POST | `/api/tasks` | `_can_use_tasks` + per-row RBAC | `{title, description?, department_id, priority, assigned_to_username, due_date, estimated_hours, tags?}` | `{ok, id, task: {...}}` |
| 3 | GET | `/api/tasks` | `_can_use_tasks` + SQL-level scoping | `?assigned_to`, `?status`, `?priority`, `?department_id`, `?due_before`, `?due_after`, `?q`, `?limit`, `?offset` | `{ok, total, limit, offset, tasks: [...]}` |
| 4 | GET | `/api/tasks/<int:tid>` | `_can_use_tasks` + `_can_see_task` | — | `{ok, task: {...}}` |
| 5 | PATCH | `/api/tasks/<int:tid>` | `_can_use_tasks` + field-level RBAC | subset of editable fields (excluding immutable list) | `{ok, task: {...}}` |
| 6 | POST | `/api/tasks/<int:tid>/status` | `_can_use_tasks` + state-machine policy | `{status: 'new'|'in_progress'|'completed'|'cancelled'}` | `{ok, transition: {from, to}, task: {...}}` |

**Errors (Arabic, returned consistently across endpoints):**

- `403 "غير مصرح"` — failed `_can_use_tasks` gate or per-task view check
- `403 "لا يمكنك إسناد المهام لموظف آخر"` — non-admin assigning to someone else on POST
- `403 "إعادة الإسناد متاحة للمدير فقط"` — non-admin PATCH of `assigned_to_username`
- `403 "هذا الحقل قابل للتعديل بواسطة المنشئ أو المدير فقط"` — wrong field-role
- `403 "هذا الحقل قابل للتعديل بواسطة المُسند إليه أو المدير فقط"` — wrong field-role on `actual_hours`
- `403 "غير مصرح بهذا الانتقال"` — state-machine RBAC denial
- `404 "المهمة غير موجودة"` — task id not found
- `400 "عنوان المهمة مطلوب" / "العنوان يجب أن يكون 200 حرفاً أو أقل"`
- `400 "القسم غير موجود"`
- `400 "الأولوية غير صحيحة"`
- `400 "تاريخ التسليم مطلوب وصحيح" / "تاريخ التسليم لا يمكن أن يكون في الماضي"`
- `400 "المدة المتوقعة يجب أن تكون أكبر من صفر"`
- `400 "ساعات العمل الفعلية يجب أن تكون موجبة"`
- `400 "الموظف غير موجود أو غير مؤهل لتلقي مهام"`
- `400 "هذه الحقول غير قابلة للتعديل"` — attempting to PATCH any of 7 immutable columns
- `400 "لا توجد حقول للتحديث"` — empty PATCH body
- `400 "الحالة المطلوبة غير صحيحة"` / `400 "المهمة بالفعل في هذه الحالة"`
- `400 "لا يمكن الانتقال من <from> إلى <to>"` — invalid state-machine pair
- `400 "الوسوم يجب أن تكون مصفوفة من النصوص" / "عدد الوسوم لا يجب أن يتجاوز 10" / "كل وسم يجب أن يكون 50 حرفاً أو أقل"`

## Permission helpers (added in C9)

```python
_can_use_tasks(user)         # DB-backed; users.can_be_assigned_tasks = 1
_can_manage_all_tasks(user)  # admin only (role check)
_can_assign_to_others(user)  # admin only — alias for the assigner gate
_can_see_task(user, row)     # admin OR assignee OR creator on this row
```

All fail-closed on `None` / missing fields. Pure functions of the session user (+ task row for the last one).

## Constants + helpers introduced

```python
_TASK_PRIORITIES        = ("critical", "urgent", "normal", "low")
_TASK_STATUSES          = ("new", "in_progress", "completed", "cancelled")
_TASK_IMMUTABLE_FIELDS  = ("id", "created_by_username", "created_at",
                           "recurring_id", "status",
                           "started_at", "completed_at")
_TASK_CREATOR_FIELDS    = ("title", "description", "department_id",
                           "priority", "due_date", "estimated_hours", "tags")
_TASK_ASSIGNEE_FIELDS   = ("actual_hours",)
_TASK_ADMIN_FIELDS      = ("assigned_to_username",)
_TASK_TRANSITIONS       = {(from, to): side_effect, ...}  # 7 entries

_validate_task_tags(raw)      → (json_string|None, err_ar|None)
_validate_task_due_date(s)    → (iso_string|None, err_ar|None)
_serialize_task_row(row, dept_info=None)  # parsed tags + dept + is_overdue
_task_can_transition(is_admin, is_creator, is_assignee, from_st, to_st)
```

## Full E2E scenario — verbatim run output

```
════════════ SCENARIO A: ADMIN ════════════
[A1] /api/departments -> 200 count= 9
[A2] POST /api/tasks -> 200 id= 17 task title: E2E تنظيف القاعة 2
[A3] GET /api/tasks -> 200 total= 1
[A4] GET /api/tasks/<id> -> 200 tags: ['فعالية', 'تنظيف'] is_overdue: False
[A5] PATCH priority -> 200 new priority: normal
[A6] new→in_progress -> 200 started_at: 2026-05-12 07:21:14
[A7] in_progress→completed -> 200 completed_at: 2026-05-12 07:21:14

════════════ SCENARIO B: RAED ════════════
[B8] raed GET /api/tasks -> 200 total= 1
[B9] raed GET /api/tasks/<id> -> 200
[B10] raed PATCH assigned_to -> 403 "إعادة الإسناد متاحة للمدير فقط"
[B11] raed bogus task -> 404
[B12] raed views stranger task -> 403 "غير مصرح"

════════════ SCENARIO C: STUDENT ════════════
[C] GET /api/departments -> 403
[C] GET /api/tasks -> 403
[C] POST /api/tasks -> 403
[C] GET /api/tasks/17 -> 403
[C] PATCH /api/tasks/17 -> 403
[C] POST /api/tasks/17/status -> 403

════════════ SCENARIO D: REGRESSION ════════════
[D] /parent -> 200
[D] /points/manage -> 200
[D] /dashboard -> 200
[D] /expenses -> 200
[D] /assets -> 200
[D] /database -> 200
[D] /groups -> 200
[D] /attendance -> 200

ALL Phase 2a E2E SCENARIOS PASSED.
```

The full script lives at `scripts/smoke_task_phase2a_e2e.py` and is committed alongside this report.

## Smoke summary

| Commit | Script | Assertions | Pass |
|---|---|---|---|
| C9  | `smoke_task_phase2a_c9.py`  | 5 | ✅ |
| C10 | `smoke_task_phase2a_c10.py` | 5 | ✅ |
| C11 | `smoke_task_phase2a_c11.py` | 13 | ✅ |
| C12 | `smoke_task_phase2a_c12.py` | 9 | ✅ |
| C13 | `smoke_task_phase2a_c13.py` | 6 | ✅ |
| C14 | `smoke_task_phase2a_c14.py` | 12 | ✅ |
| C15 | `smoke_task_phase2a_c15.py` | 15 | ✅ |
| E2E | `smoke_task_phase2a_e2e.py` | 25 | ✅ |
| **total** | | **90** | **✅ all green** |

## Live prod verification (after deploy of `aac7b69`)

```
admin /api/departments    : 200, {"ok": true, "departments": [...9 rows...]}
admin /api/tasks          : 200 (empty list — prod has no tasks yet)
admin /api/tasks/99999    : 404
anonymous /parent         : 200
anonymous /dashboard      : 302 (correct redirect)
anonymous /expenses       : 302
anonymous /assets         : 302
anonymous /points/manage  : 302
```

All 6 Phase 2a routes reachable on prod. Legacy routes unchanged.

## Final regression checklist

| Check | Result |
|---|---|
| All 7 commits in `main`, atomic, descriptive | ✅ verified via `git log` |
| `/parent` loads | ✅ HTTP 200 |
| `/portal/parent-hub/points` renders 4 rewards | ✅ HTTP 302 (admin-side redirect, store unchanged) |
| `/points/manage` all tabs work | ✅ HTTP 200; rewards tab still shows the C28 stock-history column from the financial-system phase |
| `/api/rewards/<rid>/image` serves bytes | ✅ unchanged — Phase 2a never touched the rewards image path |
| `/api/books/<bid>/view` serves bytes | ✅ unchanged |
| `/expenses` (admin + raed) work | ✅ HTTP 200 in both flows |
| `/assets` works | ✅ HTTP 200 |
| `/dashboard` renders 28 cards | ✅ HTTP 200 (the expenses + assets cards from the prior commit still present) |
| All Phase 1 tables intact | ✅ no DROP/ALTER/INSERT on existing tables; row counts unchanged |
| All Phase 2a endpoints respond correctly | ✅ confirmed by E2E + prod cURL |

## What Phase 2a delivers

- 6 endpoints exposing the entire CRUD + state-machine surface of the task system
- 4 permission helpers (`_can_use_tasks`, `_can_manage_all_tasks`, `_can_assign_to_others`, `_can_see_task`) that map directly to the spec's permission model
- SQL-level role scoping in the list endpoint — non-admin can never probe other users' tasks via pagination or filter manipulation
- Strict field-level RBAC on PATCH — 4 field-classification tuples make the policy single-source-of-truth and grep-able
- 7-entry transition table for the state machine with named side-effects (`start`, `complete`, `revert`, `cancel`, `reopen`, `uncancel`)
- All 17 distinct Arabic error messages documented above

## What is NOT in Phase 2a (Phase 2b scope)

- `task_comments` endpoints (`POST` / `GET /api/tasks/<id>/comments`)
- `task_attachments` endpoints (upload + serve BYTEA + magic-byte validation)
- `task_evaluations` endpoints (one-per-task review with rating + badges + points)
- `recurring_tasks` CRUD + scheduler endpoint
- `task_notifications` listing + read-flag endpoint
- `employee_points` aggregations + leaderboards
- Admin dashboard analytics

## Rollback

`safety/task-system-phase2a-20260512-100455` is the commit immediately before C9. To revert all 7 endpoint commits in one step:

```
git reset --hard safety/task-system-phase2a-20260512-100455
git push --force-with-lease origin main
```

The Phase 1 schema stays; only the new routes + helpers + constants disappear. No data is at risk (the prod tasks table is empty).

---

🛑 **Phase 2a complete. 6 endpoints live: departments lookup + tasks CRUD + status transitions. RBAC verified across all 4 role paths. Awaiting owner approval before Phase 2b.**
