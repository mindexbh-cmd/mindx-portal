# Task System Phase 4 — Recurring Task Auto-Generation Verification

**Date:** 2026-05-12
**Phase HEAD:** `17aec64`
**Commits in phase:** 3 (C41 → C42 → C43) + this report

## Commit Log

```
<this report>  docs(task-phase4): scheduler verification report
17aec64        feat(tasks): admin manual-trigger for recurring scheduler (C43)
3105136        feat(task-phase4): request-time scheduler hook with throttle (C42)
4d7e099        feat(task-phase4): recurring task scheduler core logic (C41)
```

## Owner design decisions (locked in)

| Decision | Choice |
|---|---|
| Generation mechanism | Request-time check (no cron / no background worker) |
| Generation timing | Start of due date (00:00 — i.e. when `target_date == today`) |
| Backlog policy | Last 2 days only (yesterday + today). Anything older is skipped. |
| Throttle window | 1 hour between automatic checks |
| Failure mode | Silent — scheduler errors never block a page render |
| Admin override | POST /api/recurring-tasks/run-scheduler bypasses the throttle |

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│ Request enters one of 5 task-page routes:                  │
│   /dashboard  /tasks  /tasks/recurring                     │
│   /tasks/dashboard/personal  /tasks/dashboard/admin        │
└────────────┬───────────────────────────────────────────────┘
             │
             ▼
   _maybe_run_recurring_scheduler()       ← C42 throttle hook
             │
             ├── if last run < 1 hour ago → skip (cache warm)
             │
             └── else: lock + call ↓
                       │
                       ▼
            _generate_due_recurring_tasks(db)   ← C41 core
                       │
                       ├── for each active template:
                       │     compute backlog window (last 2 days)
                       │     for each day in window:
                       │       if matches frequency rule:
                       │         INSERT task row + back-link recurring_id
                       │         UPDATE template.last_generated_date = today
                       │
                       └── returns (count, details[])

Admin manual trigger (C43):
   POST /api/recurring-tasks/run-scheduler
       └── _can_manage_all_tasks check
       └── force _LAST_RECURRING_CHECK = None
       └── call _generate_due_recurring_tasks(db) directly
       └── return JSON {ok, generated, details[]}
```

## Frequency rules

- **daily** — generate every day in the backlog window
- **weekly** — generate only when `_mindex_weekday(date) == template.day_of_week`
  - Mindex weekday: Sun=0..Sat=6 (vs Python's Mon=0..Sun=6).
  - Conversion: `_mindex_weekday(d) = (d.weekday() + 1) % 7`
- **monthly** — generate only when `date.day == template.day_of_month`

`is_active = 0` templates are always skipped.
`last_generated_date >= target_date` is the idempotency guard.

## Idempotency

`_generate_due_recurring_tasks` is **safe to call any number of times**:

1. For each candidate date, the generator checks `last_generated_date` and refuses to re-generate for a date already past that threshold.
2. After successfully inserting a row, the template's `last_generated_date` is stamped to TODAY in the same transaction.
3. C42 smoke (Test [2]) and C43 smoke (Test [3]) both explicitly verify back-to-back calls return `generated=0`.

## Throttle (C42)

Module-level state:
```python
_LAST_RECURRING_CHECK = None
_RECURRING_THROTTLE_SECONDS = 3600  # 1 hour
```

The hook is fire-and-forget — `_maybe_run_recurring_scheduler()` returns void; the caller never knows or cares whether the scheduler actually ran.

Silent-failure mode: every exception inside the hook is swallowed (with a stderr log line). A broken scheduler will never break a route. C42 smoke Test [5] verifies this by monkey-patching `_generate_due_recurring_tasks` to raise — the hooked route still responds 200.

## C43 admin override

The button on `/tasks/recurring` is gated by `R_IS_ADMIN`. The endpoint itself runs a stronger check: `_can_manage_all_tasks(user)` (matches the wider task-admin policy from Phase 2b). teacher1 (and any non-admin) receives `403 { ok:false, error:"هذه العملية متاحة للمدير فقط" }`.

The endpoint sets `_LAST_RECURRING_CHECK = None` before running so it bypasses the throttle, then restamps it after — so the next automatic check still respects the 1-hour cooldown.

## E2E scenario — admin run

Setup: a daily template with `last_generated_date = 5 days ago`.

| Step | Expected | Actual (smoke) |
|---|---|---|
| admin POST /api/recurring-tasks/run-scheduler | `generated >= 2`, includes today + yesterday | ✅ `generated=4` (2 for the test template + 2 leftover from a prior smoke run) |
| Verify `tasks` table — 2 new rows with `recurring_id = template.id`, `due_date in (today, yesterday)` | rows present | ✅ |
| Verify template's `last_generated_date` advanced to today | YYYY-MM-DD == today | ✅ (C41 Test [3]) |
| admin POSTs again immediately | `generated=0` (idempotent) | ✅ |

## E2E scenario — non-admin visiting /tasks

| Step | Expected | Actual |
|---|---|---|
| teacher1 visits /tasks | 200 — scheduler hook fires silently (no error) | ✅ |
| teacher1 visits /tasks/recurring | 200, `R_IS_ADMIN=false`, button hidden by JS | ✅ (C43 Test [4]) |
| teacher1 POSTs /api/recurring-tasks/run-scheduler | 403 "هذه العملية متاحة للمدير فقط" | ✅ (C43 Test [1]) |

## E2E scenario — throttle

| Step | Expected | Actual |
|---|---|---|
| admin visits /tasks (cold) | hook fires, `_LAST_RECURRING_CHECK` is stamped | ✅ |
| admin visits /tasks again (warm, same hour) | hook skips, timestamp unchanged | ✅ (C42 Test [2]) |
| admin visits /dashboard | hook skips (same global throttle) | ✅ (C42 Test [3]) |
| admin force-resets `_LAST_RECURRING_CHECK = None` | next visit re-fires | ✅ (C42 Test [4]) |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean | ✅ |
| C41 smoke (5 frequency-rule tests) | ✅ pass |
| C42 smoke (6 tests including silent-failure) | ✅ pass |
| C43 smoke (5 tests including 8-route regression) | ✅ pass |
| `/parent` 200 | ✅ |
| `/dashboard` 200 | ✅ |
| `/tasks` 200 | ✅ |
| `/tasks/recurring` 200 | ✅ |
| `/expenses` 200 | ✅ |
| `/assets` 200 | ✅ |
| `/points/manage` 200 | ✅ |
| `/database` 200 | ✅ |
| Idempotency holds across cold + warm + force-reset paths | ✅ |
| Silent-failure mode keeps pages alive when scheduler crashes | ✅ |
| No background thread / worker / cron added | ✅ (request-time only) |
| Throttle uses module-level globals — no extra DB table | ✅ |

## Files touched

- `app.py` — added `_mindex_weekday`, `_generate_due_recurring_tasks`, `_maybe_run_recurring_scheduler`, `_LAST_RECURRING_CHECK`, `_RECURRING_THROTTLE_SECONDS`; hook calls at top of 5 routes; POST `/api/recurring-tasks/run-scheduler`; "توليد المهام الآن" button + JS handler in `TASKS_RECURRING_HTML`.
- `scripts/smoke_task_phase4_c41.py` — frequency rule smoke (5 templates).
- `scripts/smoke_task_phase4_c42.py` — hook + throttle smoke.
- `scripts/smoke_task_phase4_c43.py` — admin endpoint + button visibility smoke.

## Postgres safety

The scheduler is Postgres-safe:
- Uses `cur.lastrowid or fallback SELECT ... ORDER BY id DESC LIMIT 1` for new-task IDs (Phase 1 helper pattern).
- Stamps `last_generated_date` as ISO `YYYY-MM-DD` string (TEXT column).
- No `COALESCE(<ts>, '')` anti-patterns introduced.
- All INSERTs include only declared columns; no implicit-empty-string failures.

The local smoke runs against SQLite — same Postgres-wrapper code path executes on Render. C43's response body (`{ ok, generated, details[] }`) was sized to keep transit small; `details[]` includes only `template_id, template_title, target_date, new_task_id`.

## Rollback

To disable Phase 4 in one step (e.g. emergency rollback):

```bash
git revert --no-edit 17aec64 3105136 4d7e099
git push origin main
```

This restores the prior Phase 3c HEAD. No schema changes were introduced in Phase 4 — `recurring_tasks` already had `last_generated_date`, `frequency`, `day_of_week`, `day_of_month`, `is_active` from Phase 1 (C6), and `tasks.recurring_id` from Phase 1 (C3). Phase 4 only adds *behaviour* on top of the existing tables.

## What Phase 4 does NOT do (deferred / non-goals)

- **No catch-up beyond 2 days.** A template that's been quiet for a month will only generate yesterday + today on the next request. Per the owner's design.
- **No timezone handling.** `dt.date.today()` uses the server's local time. Render runs UTC; the team is GMT+3. Tasks marked "today" before 03:00 local will technically be generated on what UTC calls "yesterday". This is acceptable for v1.1.
- **No notification on auto-generation.** New tasks born from the scheduler don't trigger `task_notifications` rows yet. Could be added in v1.2 as a one-liner in the generator loop.
- **No "next run preview"** in the UI. The /tasks/recurring page shows last_generated_date but not next_will_generate_on. Could be a future polish.

---

🎯 **Phase 4 complete. 3 commits, 3 smoke scripts, all green. Recurring task auto-generation is live with request-time check + 1-hour throttle + last-2-days backlog + admin manual-trigger. Task Management System v1.1 is now FEATURE-COMPLETE.**
