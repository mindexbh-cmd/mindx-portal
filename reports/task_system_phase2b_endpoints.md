# Task System — Phase 2b Endpoints Verification

**Date:** 2026-05-12
**Safety tag (pre-change):** `safety/task-system-phase2b-20260512-102708`
**Phase 2b HEAD:** `2ebc4be feat(task-phase2b): in-site notifications API`
**Commits:** 12 atomic commits (C16–C27) + this report

## Commit Log

```
2ebc4be  feat(task-phase2b): in-site notifications API
a3aa492  feat(task-phase2b): admin full performance dashboard
5f2cb76  feat(task-phase2b): motivational team dashboard
b63166c  feat(task-phase2b): personal task dashboard data
273529e  feat(task-phase2b): recurring task templates CRUD
c4a83cd  feat(task-phase2b): view + amend evaluations with delta audit trail
11ddc9f  feat(task-phase2b): task evaluation with motivational points
fc65288  feat(task-phase2b): delete task attachment with ownership
5ef715d  feat(task-phase2b): serve task attachment bytes + list metadata
10ada45  feat(task-phase2b): BYTEA attachment upload for tasks
15c2433  feat(task-phase2b): delete comment with strict ownership
c5e5db6  feat(task-phase2b): comments POST + GET on tasks
```

## Endpoint inventory — 17 new method/path pairs (13 logical endpoints)

| # | Method | Path | Permission | Purpose |
|---|---|---|---|---|
| 1 | POST | `/api/tasks/<tid>/comments` | `_can_use_tasks` + `_can_see_task` | Add a comment; notifies other stakeholders |
| 2 | GET | `/api/tasks/<tid>/comments` | same | List comments (ASC by created_at) |
| 3 | DELETE | `/api/tasks/<tid>/comments/<cid>` | admin OR author | Delete with ownership check |
| 4 | POST | `/api/tasks/<tid>/attachments` | `_can_use_tasks` + `_can_see_task` | BYTEA upload (5MB, magic-byte validated) |
| 5 | GET | `/api/tasks/<tid>/attachments` | same | Metadata-only listing |
| 6 | GET | `/api/tasks/<tid>/attachments/<aid>` | same | Stream raw bytes with correct disposition |
| 7 | DELETE | `/api/tasks/<tid>/attachments/<aid>` | admin OR uploader | Delete |
| 8 | POST | `/api/tasks/<tid>/evaluate` | admin only | Create evaluation + atomically award points |
| 9 | GET | `/api/tasks/<tid>/evaluation` | `_can_see_task` | View evaluation |
| 10 | PATCH | `/api/tasks/<tid>/evaluation` | admin only | Amend with delta audit trail in employee_points |
| 11 | POST | `/api/recurring-tasks` | `_can_use_tasks` + RBAC | Create recurring template |
| 12 | GET | `/api/recurring-tasks` | `_can_use_tasks` (scoped) | List templates |
| 13 | PATCH | `/api/recurring-tasks/<rid>` | admin OR creator | Update template |
| 14 | DELETE | `/api/recurring-tasks/<rid>` | admin OR creator | Soft-delete (is_active=0) |
| 15 | GET | `/api/tasks/dashboard/personal` | `_can_use_tasks` | Per-user dashboard data |
| 16 | GET | `/api/tasks/dashboard/team` | `_can_use_tasks` | Motivational team view (top 3 only) |
| 17 | GET | `/api/tasks/dashboard/admin` | admin only | Deep analytics |
| 18 | GET | `/api/notifications` | `_can_use_tasks` | List user's notifications |
| 19 | POST | `/api/notifications/<nid>/read` | recipient only | Mark as read |
| 20 | GET | `/api/notifications/unread-count` | `_can_use_tasks` | Lightweight count for bell badge |

## Helpers introduced (in C16)

```python
_get_task_or_404(tid)           # returns (row, None) or (None, response)
_create_notification(...)       # best-effort INSERT, returns id or None
_notify_task_stakeholders(...)  # fan to creator+assignee minus excluded
```

Plus per-feature constants/helpers in later commits:

```python
# C18 attachment validation
_TASK_ATTACH_ALLOWED_MIMES, _TASK_ATTACH_MAX_BYTES
_validate_task_attachment_b64(b64, mime, filename)

# C21/C22 evaluations
_TASK_STRENGTH_BADGES, _TASK_PRIORITY_BONUS
_validate_strength_badges(raw)
_compute_task_points(task_row, rating_stars)
_serialize_evaluation(row)

# C23 recurring tasks
_RECURRING_FREQ
_validate_recurring_payload(d, allow_partial)
_check_recurring_freq_requirements(cleaned, current=None)
_serialize_recurring_row(row)

# C25 team dashboard
_MOTIVATIONAL_MESSAGES  # 5-message Arabic pool
```

## Full E2E scenario — verbatim run output

```
════════════ SCENARIO A: ADMIN BOOTSTRAP ════════════
[A1] POST /api/recurring-tasks -> 200 id= 5 title: E2E daily backup check
[A2] POST /api/tasks -> 200 id= 42
[A3] POST attachment -> 200 aid= 7 size= 68

════════════ SCENARIO B: RAED INTERACTS ════════════
[B4] raed unread-count before comment: 1
[B5] POST comment -> 200 cid= 8
[B6a] new→in_progress -> 200 started_at: 2026-05-12 07:56:04
[B6b] in_progress→completed -> 200 completed_at: 2026-05-12 07:56:04

════════════ SCENARIO C: ADMIN EVALUATES ════════════
[C7] evaluate -> 200 points: 70
[C8] employee_points: [{'employee_username': '980909805', 'points': 70}]
[C9] amend 5→4 -> 200 delta: -10 new_total: 60
[C9a] audit points trail: [70, -10]

════════════ SCENARIO D: NOTIFICATIONS ════════════
raed notifications:
    - completed / تم تقييم مهمتك: 5 نجوم
    - comment / مرفق جديد على: E2E تجهيز قاعة الفعالية
admin notifications:
    - comment / تعليق جديد من 980909805 على: E2E تجهيز قاعة الفعالية

════════════ SCENARIO E: DASHBOARDS ════════════
admin: overview {avg_rating:4.0, completed:1, total_tasks:1, ...}
       raed entry: completed=1, avg_rating=4.0, total_points=60,
                    on_time_rate=100.0
raed personal: my_points.total=60, completed=1
team: team_total=1, top=[{username:980909805, completed_count:1}]

════════════ SCENARIO F: REGRESSION ════════════
/parent /points/manage /dashboard /expenses /assets /database
/groups /attendance /api/departments /api/tasks → all 200

ALL Phase 2b E2E SCENARIOS PASSED.
```

The full script lives at `scripts/smoke_task_phase2b_e2e.py` and is committed alongside this report.

## Smoke summary

| Commit | Script | Assertions | Pass |
|---|---|---|---|
| C16 | `smoke_task_phase2b_c16.py` | 9 | ✅ |
| C17 | `smoke_task_phase2b_c17.py` | 5 | ✅ |
| C18 | `smoke_task_phase2b_c18.py` | 9 | ✅ |
| C19 | `smoke_task_phase2b_c19.py` | 8 | ✅ |
| C20 | `smoke_task_phase2b_c20.py` | 5 | ✅ |
| C21 | `smoke_task_phase2b_c21.py` | 9 | ✅ |
| C22 | `smoke_task_phase2b_c22.py` | 8 | ✅ |
| C23 | `smoke_task_phase2b_c23.py` | 17 | ✅ |
| C24 | `smoke_task_phase2b_c24.py` | 3 | ✅ |
| C25 | `smoke_task_phase2b_c25.py` | 4 | ✅ |
| C26 | `smoke_task_phase2b_c26.py` | 3 | ✅ |
| C27 | `smoke_task_phase2b_c27.py` | 9 | ✅ |
| E2E | `smoke_task_phase2b_e2e.py` | 25 | ✅ |
| **total** | | **114** | **✅ all green** |

## Final regression checklist

| Check | Result |
|---|---|
| All 12 commits in `main`, atomic, descriptive | ✅ |
| App boots cleanly | ✅ `import app` succeeds with no exceptions |
| `/parent` loads | ✅ HTTP 200 |
| `/points/manage` (admin) loads | ✅ HTTP 200 |
| `/portal/parent-hub/points` renders 4 rewards | ✅ unchanged from financial-system Phase 1 |
| `/api/rewards/<rid>/image` serves bytes | ✅ unchanged |
| `/api/books/<bid>/view` serves bytes | ✅ unchanged |
| `/expenses` (admin + raed) work | ✅ HTTP 200 both flows |
| `/assets` works | ✅ HTTP 200 |
| `/dashboard` renders | ✅ HTTP 200 (28 cards from dashboard-cards commit still present) |
| All Phase 1 tables intact | ✅ no DROP/ALTER/INSERT on existing tables |
| All Phase 2a endpoints respond | ✅ POST /api/tasks → 200; GET /api/tasks/<id> → 200; PATCH; POST .../status all work |
| All Phase 2b endpoints respond | ✅ confirmed by 13 smoke scripts + E2E |
| Books_v2 untouched | ✅ no edits to any books_v2 code path |
| Financial system untouched | ✅ no edits to any /api/expenses or /api/assets code path |

## What Phase 2b delivers

- **17 new method/path pairs** completing the entire CRUD + collaboration + analytics surface of the task system
- **Comments + attachments** with consistent fan-out notification to other stakeholders, full ownership semantics on delete
- **BYTEA attachments** mirroring the rewards/books_v2/expenses pattern — 5MB cap, 8-MIME allowlist, magic-byte validation
- **Evaluations** with deterministic motivational-points formula (stars×10 + priority bonus + on-time bonus), atomic 3-write transaction (eval + points + notification), and delta-row audit trail on amendments
- **Recurring task templates** with frequency-specific day-of-week / day-of-month requirements, soft-delete, and the same RBAC as one-off tasks
- **3 dashboards**:
  - personal: every employee sees their own stats + points + badge counts
  - team: motivational top-3 only, no shaming fields ever
  - admin: deep analytics with by_employee + by_department + by_priority + 30-day trends
- **In-site notifications** with unread-count for header bell + per-id mark-read with strict recipient ownership

## What is NOT in Phase 2b

- **No frontend UI** — every endpoint is API-only; Phase 3a (mockup) + Phase 3b (implementation) come next
- **No scheduler for recurring tasks** — the templates exist but nothing fans them out to tasks rows yet. That's a separate phase deliberately deferred so the admin can preview the templates before automation kicks in
- **No WhatsApp / email notification dispatch** — `task_notifications` is in-site only for now (the bell badge)
- **No bulk operations** — every endpoint operates on a single task/comment/attachment/template
- **No archived view** — completed/cancelled tasks remain in the same list, filtered by `?status`

## Rollback

`safety/task-system-phase2b-20260512-102708` is the commit immediately before C16. To revert all 12 endpoint commits in one step:

```
git reset --hard safety/task-system-phase2b-20260512-102708
git push --force-with-lease origin main
```

Phase 1 schema + Phase 2a endpoints stay. The task_notifications, task_comments, task_attachments, task_evaluations, employee_points, recurring_tasks tables become unreferenced by new endpoint code but stay populated (the smoke scripts cleaned up after themselves so prod data is unchanged — only the helper functions + endpoint handlers disappear).

---

🛑 **Phase 2b complete. 13 advanced endpoints live: comments, BYTEA attachments, evaluations with points, recurring task templates, 3 dashboards, and notifications. All RBAC verified. Awaiting owner approval before Phase 3a (mockup).**
