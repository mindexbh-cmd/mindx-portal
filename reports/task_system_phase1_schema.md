# Task System — Phase 1 Schema Verification

**Date:** 2026-05-12
**Safety tag (pre-change):** `safety/task-system-phase1-20260512-094134`
**Phase 1 HEAD:** `22e6583 feat(task-phase1): indexes + register tables in _TBL_AUDIT_FEATURE`
**Commits:** 8 atomic commits (C1–C8) + this report

## Commit Log

```
22e6583  feat(task-phase1): indexes + register tables in _TBL_AUDIT_FEATURE
28507bd  feat(task-phase1): motivational points log + in-site notifications
a3acd35  feat(task-phase1): recurring task templates
40b4a26  feat(task-phase1): comments + BYTEA attachments for tasks
84349d6  feat(task-phase1): task evaluations with stars + badges + points
d8deca2  feat(task-phase1): core tasks table
88a5317  feat(task-phase1): extend users with primary_department + assignable flag
629970e  feat(task-phase1): departments table with 9 Mindex divisions
```

## Tables — verbatim CREATE statements

Every statement below is present in BOTH `init_db()` (fresh-DB path) AND the `else`-branch always-runs migration block, per CLAUDE.md's dual-path schema policy. The else-branch uses `CREATE TABLE IF NOT EXISTS` so re-runs against a populated DB are no-ops.

### 1. departments

```sql
CREATE TABLE IF NOT EXISTS departments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name_ar TEXT NOT NULL UNIQUE,
  icon TEXT,
  color TEXT,
  sort_order INTEGER DEFAULT 0,
  is_active INTEGER DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2. users — ALTER (additive only)

```sql
ALTER TABLE users ADD COLUMN primary_department_id INTEGER;
ALTER TABLE users ADD COLUMN can_be_assigned_tasks INTEGER DEFAULT 0;
```
…wrapped in the existing `for _col, _decl in [ ... ]` loop in the else-branch with a try/except for "column already exists". Fresh-DB path adds them to the `users` CREATE TABLE directly.

### 3. tasks

```sql
CREATE TABLE IF NOT EXISTS tasks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  department_id INTEGER REFERENCES departments(id),
  priority TEXT NOT NULL DEFAULT 'normal'
      CHECK(priority IN ('critical','urgent','normal','low')),
  status TEXT NOT NULL DEFAULT 'new'
      CHECK(status IN ('new','in_progress','completed','cancelled')),
  assigned_to_username TEXT NOT NULL,
  created_by_username TEXT NOT NULL,
  due_date DATE NOT NULL,
  estimated_hours REAL NOT NULL,
  actual_hours REAL,
  tags TEXT,
  recurring_id INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  started_at DATETIME,
  completed_at DATETIME
);
```

### 4. task_evaluations

```sql
CREATE TABLE IF NOT EXISTS task_evaluations(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL UNIQUE
          REFERENCES tasks(id) ON DELETE CASCADE,
  rating_stars INTEGER NOT NULL CHECK(rating_stars BETWEEN 1 AND 5),
  strength_badges TEXT,
  admin_comment TEXT,
  evaluated_by TEXT NOT NULL,
  evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  points_awarded INTEGER NOT NULL DEFAULT 0
);
```

### 5. task_comments

```sql
CREATE TABLE IF NOT EXISTS task_comments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL
          REFERENCES tasks(id) ON DELETE CASCADE,
  author_username TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 6. task_attachments

```sql
CREATE TABLE IF NOT EXISTS task_attachments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL
          REFERENCES tasks(id) ON DELETE CASCADE,
  file_bytes BYTEA NOT NULL,
  file_mime TEXT NOT NULL,
  filename TEXT,
  file_size INTEGER,
  uploaded_by_username TEXT NOT NULL,
  uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 7. recurring_tasks

```sql
CREATE TABLE IF NOT EXISTS recurring_tasks(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_title TEXT NOT NULL,
  template_description TEXT,
  department_id INTEGER REFERENCES departments(id),
  priority TEXT DEFAULT 'normal',
  assigned_to_username TEXT NOT NULL,
  estimated_hours REAL NOT NULL,
  frequency TEXT NOT NULL
      CHECK(frequency IN ('daily','weekly','monthly')),
  day_of_week INTEGER,
  day_of_month INTEGER,
  tags TEXT,
  is_active INTEGER DEFAULT 1,
  last_generated_date DATE,
  created_by_username TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 8. employee_points

```sql
CREATE TABLE IF NOT EXISTS employee_points(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_username TEXT NOT NULL,
  task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
  points INTEGER NOT NULL,
  reason TEXT,
  awarded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 9. task_notifications

```sql
CREATE TABLE IF NOT EXISTS task_notifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  recipient_username TEXT NOT NULL,
  task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
  notification_type TEXT NOT NULL,
  message TEXT NOT NULL,
  is_read INTEGER DEFAULT 0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Row counts after seeding

| Table | Rows |
|---|---|
| departments | **9** (seeded) |
| tasks | 0 |
| task_evaluations | 0 |
| task_comments | 0 |
| task_attachments | 0 |
| recurring_tasks | 0 |
| employee_points | 0 |
| task_notifications | 0 |

## Seeded departments (verbatim)

| id | sort | name_ar | icon | color |
|---|---|---|---|---|
| 1 | 1 | الإدارة | 👔 | #4A148C |
| 2 | 2 | قسم المناهج والامتحانات | 📚 | #1976D2 |
| 3 | 3 | قسم الجودة | ⭐ | #F57C00 |
| 4 | 4 | قسم الإعلام | 📷 | #C2185B |
| 5 | 5 | قسم الأفكار والتحفيز | 💡 | #FBC02D |
| 6 | 6 | قسم الفعاليات | 🎉 | #FF5722 |
| 7 | 7 | قسم شؤون الطلاب | 👨‍🎓 | #388E3C |
| 8 | 8 | قسم شؤون الاستقبال | 👋 | #00838F |
| 9 | 9 | قسم شؤون المقر | 🏛️ | #5D4037 |

Seed gated by `task_phase1_departments_seed_v1` in `schema_migrations`; UNIQUE(name_ar) + per-row exists check on top of the tag gate gives three layers of defense against duplicates.

## Indexes — verbatim CREATE statements

All declared via `CREATE INDEX IF NOT EXISTS` (idempotent) in both schema-management paths.

| # | Index | Table | Columns |
|---|---|---|---|
| 1 | `idx_tasks_assigned_to` | tasks | `assigned_to_username` |
| 2 | `idx_tasks_status` | tasks | `status` |
| 3 | `idx_tasks_due_date` | tasks | `due_date` |
| 4 | `idx_tasks_dept` | tasks | `department_id` |
| 5 | `idx_tasks_recurring` | tasks | `recurring_id` |
| 6 | `idx_task_comments_task` | task_comments | `task_id` |
| 7 | `idx_task_attachments_task` | task_attachments | `task_id` |
| 8 | `idx_task_evals_task` | task_evaluations | `task_id` |
| 9 | `idx_emp_points_user` | employee_points | `employee_username` |
| 10 | `idx_notifs_recipient` | task_notifications | `(recipient_username, is_read)` — composite |
| 11 | `idx_recurring_active` | recurring_tasks | `(is_active, frequency)` — composite |

All 11 verified via PRAGMA index_list (local SQLite). On Postgres the same indexes are created at boot time through the wrapper's translation; index sizes will be near-zero until rows accumulate.

## users.can_be_assigned_tasks backfill

Tag-gated UPDATE flips `can_be_assigned_tasks = 1` for every user whose `role` (case-insensitive) is one of `admin / manager / teacher / staff`. The `COALESCE(can_be_assigned_tasks, 0) = 0` guard means admin-driven manual flips on individual rows survive subsequent boots.

Tag: `task_phase1_users_assignable_backfill_v1`.

Local DB result (9 users total):

| Role | Count | Assignable |
|---|---|---|
| admin | 2 | 2 (all) |
| manager | 2 | 2 (all) |
| teacher | 4 | 4 (all) |
| reception | 1 | 0 (correct — not in the literal spec list) |
| **total** | **9** | **8** |

The single `reception` user stayed at the column default `0`. Per the spec, only the literal list `admin/manager/teacher/staff` triggers the flip; flipping reception (or any individual user) is an admin UI action in a later phase. No `student` or `parent` users exist locally; if any exist on prod they will also stay at `0`.

## `schema_migrations` stamps

Phase 1 added 2 new tags. Total schema_migrations rows: **82** (was 80).

| Tag | Purpose |
|---|---|
| `task_phase1_departments_seed_v1` | Seeded the 9 departments (one-shot) |
| `task_phase1_users_assignable_backfill_v1` | Set assignable=1 for admin/manager/teacher/staff (one-shot) |

## `_TBL_AUDIT_FEATURE` registration

All 8 new tables appended to the dict at `app.py:38835` immediately after the financial-system block. Verified at runtime via `'<table>' in app._TBL_AUDIT_FEATURE` for each:

| Table | Label | Feature label |
|---|---|---|
| `departments` | الأقسام | نظام المهام والأداء |
| `tasks` | المهام | نظام المهام والأداء |
| `task_evaluations` | تقييمات المهام | نظام المهام والأداء |
| `task_comments` | تعليقات المهام | نظام المهام والأداء |
| `task_attachments` | مرفقات المهام | نظام المهام والأداء |
| `recurring_tasks` | قوالب المهام المتكررة | نظام المهام والأداء |
| `employee_points` | سجل نقاط الموظفين | نظام المهام والأداء |
| `task_notifications` | إشعارات المهام | نظام المهام والأداء |

All 8 now render as Category B in `/admin/table-audit` rather than as Category D orphan candidates. The boot-time orphan warning will no longer mention any of them.

## Constraint behavior verified (smoke)

| Constraint | Test | Result |
|---|---|---|
| `tasks.priority` CHECK | INSERT with `priority='bogus_priority'` | ✅ rejected with IntegrityError |
| `tasks.status` CHECK | INSERT with `status='bogus_status'` | ✅ rejected with IntegrityError |
| `task_evaluations.rating_stars` CHECK | INSERT with `rating_stars=6` | ✅ rejected with IntegrityError |
| `task_evaluations.task_id` UNIQUE | Two INSERTs for the same task_id | ✅ second rejected with IntegrityError |
| `recurring_tasks.frequency` CHECK | INSERT with `frequency='yearly'` | ✅ rejected with IntegrityError |
| `task_notifications` ON DELETE CASCADE | DELETE parent task → child row gone | ✅ verified |
| `employee_points` ON DELETE SET NULL | DELETE parent task → child row's task_id = NULL | ✅ verified |

## Regression sweep (admin session)

| Endpoint / route | HTTP | Notes |
|---|---|---|
| `/parent` | 200 | unchanged |
| `/points/manage` | 200 | rewards tab still renders the C28 stock-history column |
| `/portal/parent-hub/points` | 302 | admin → redirect (as expected) |
| `/dashboard` | 200 | 28 cards (includes the C24 + C2 dashboard-card additions) |
| `/expenses` | 200 | admin sees full analytics |
| `/assets` | 200 | grid + total-value strip |
| `/database` | 200 | admin-gated |
| `/groups` | 200 | unchanged |
| `/attendance` | 200 | unchanged |

No legacy table modified. No existing column changed. No existing row mutated. `books_v2` untouched (no edits to any books_v2 code path in this Phase 1).

## Rollback

`safety/task-system-phase1-20260512-094134` is tagged at the commit immediately before C1. To revert all 8 schema commits in one step:

```
git reset --hard safety/task-system-phase1-20260512-094134
git push --force-with-lease origin main
```

The 8 new tables become unreferenced. `users.primary_department_id` and `users.can_be_assigned_tasks` columns become dormant but stay present in the DB (Postgres/SQLite both keep ALTER-added columns even after the code that added them disappears — this is by design). Re-applying the commits restores the same dormant columns; no data loss either way.

## What is NOT in Phase 1

- **No endpoints.** `/api/tasks`, `/api/tasks/<id>/evaluate`, `/api/tasks/<id>/comments`, `/api/tasks/<id>/attachments`, `/api/recurring-tasks`, `/api/notifications/unread`, etc. — all Phase 2.
- **No UI.** No `/tasks` page, no sidebar entry, no admin dashboard card for the task system. Phase 3.
- **No scheduler.** `recurring_tasks` table exists but nothing reads from it yet; `last_generated_date` will be the idempotency marker for the future scheduler.
- **No notifications fan-out.** `task_notifications` table is empty; the Phase 2 task-creation endpoint will INSERT the initial `'assigned'` row.

---

🛑 **Phase 1 complete. 9 tables created, 11 indexes, 9 departments seeded. Users backfilled with assignable flag. Awaiting owner approval before Phase 2 endpoints.**
