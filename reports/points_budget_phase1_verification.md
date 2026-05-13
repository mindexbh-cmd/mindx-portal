# Phase 1 — Per-session points budget — Verification

**Scope:** schema + API enforcement only. No UI changes. The
class panel (`/points/board`) still renders the existing v1
behavior buttons; the cap and budget endpoint are wired but
not yet visualised — Phase 2 will surface the progress bar,
quick-action buttons, and warning toasts.

**Safety tag:** `safety/points-budget-phase1-20260513-144510`
(created before C1).

**Atomic commits on `main`:**

| Hash       | Subject                                                |
|------------|--------------------------------------------------------|
| `ba3d02d`  | feat(points): add session_date column to point_events  |
| `a26d6e6`  | feat(points): session budget helpers                   |
| `e0c9bda`  | feat(points): /api/points/session-budget endpoint      |
| `a8de0a1`  | feat(points): enforce session budget in grant          |
| `6e379d0`  | feat(points): admin override for session budget        |
| `52b606e`  | feat(points): backfill session_date for existing rows  |
| `a7b1ae2`  | test(points): Phase 1 smoke                            |
| (this PR)  | docs: Phase 1 verification                             |

## What ships in Phase 1

### 1. Schema migration — `points_session_date_v1`

- Added nullable `session_date TEXT` column to `point_events`.
- Added composite index `idx_point_events_session ON
  point_events(group_name, session_date)`.
- Dual-write: `init_db()` `CREATE TABLE` (line 1071-1086) and
  the existing-DB else-branch migration (line 8564-8597). The
  init-branch index is wrapped in try/except since
  `CREATE TABLE IF NOT EXISTS` is a no-op on pre-existing tables
  (the actual ALTER lives in the else-branch).
- Migration tag is persisted in `schema_migrations` — one-shot,
  re-runs safely.

### 2. Helpers (app.py:35806-35909)

- `PTS_PER_STUDENT_CAP = 10` — per-active-student point ceiling.
- `_pts_bahrain_today()` — `(utcnow + 3h).date().isoformat()`,
  used everywhere a session date is needed.
- `_pts_active_students_count(db, group, date)` — strategy 1:
  `COUNT(DISTINCT student_name) FROM attendance WHERE group +
  date AND status IN ('حاضر','متأخر')`; strategy 2: roster
  size when no attendance row exists yet (so teachers can award
  before recording attendance).
- `_pts_session_budget(db, group, date)` — `active × cap`.
- `_pts_session_used(db, group, date)` — `SUM(ABS(points_value))`
  so negatives count toward the cap at absolute value.
- `_pts_session_remaining(db, group, date)` — `(used, budget,
  remaining)` triple with `remaining` clamped at 0.

### 3. `GET /api/points/session-budget` (app.py:36334-36392)

Auth: `_pts_can_grant` — admin/manager always, teacher only on
groups they own.

Query: `?group=<name>` (required) + `?date=YYYY-MM-DD`
(optional, defaults to today in Bahrain TZ).

Response:
```json
{
  "ok": true,
  "group_name": "مجموعة 01",
  "session_date": "2026-05-13",
  "active_students": 5,
  "per_student_cap": 10,
  "budget": 50,
  "used": 18,
  "remaining": 32,
  "percent_used": 36,
  "status": "ok"
}
```

`status` ∈ `{empty, ok, warning, full}` — Phase 2's UI uses
these directly to render the progress bar colour.

### 4. Cap enforcement in `POST /api/points/grant`

- Computes `session_date = _pts_bahrain_today()` once per
  request.
- Sums the intended cost atomically: `intended = |pv| × |sids|`.
- Reads `(used, budget, remaining)` for the session.
- **Non-admin caller** + `intended + used > budget` →
  HTTP 400 with the structured payload:
  ```json
  { "ok": false,
    "error": "تجاوزت رصيد المجموعة في هذه الحصة",
    "budget": 50, "used": 48, "remaining": 2,
    "requested": 10, "session_date": "2026-05-13",
    "group_name": "مجموعة 01" }
  ```
- **Admin/manager caller** — bypass is the default policy.
- Every successful `INSERT INTO point_events` now carries
  `session_date` in the column list.

### 5. Admin override + audit (`audit_log`)

- Reads `override` from the query string OR the JSON body.
- After successful inserts:
  - If caller is admin AND (`override=1` OR the grant
    actually would have exceeded the cap) → one row in
    `audit_log` with `action='points_budget_override'`,
    `target_type='group'`, `target_id=group_name`, and a
    JSON `details` blob carrying
    `{session_date, group_name, behavior_id, behavior_name,
      points_value, budget, used_before, requested,
      would_exceed, explicit, event_ids, student_ids}`.
- The grant response now echoes `"override": true|false` so
  the UI can show a confirmation when the bypass fires.
- Audit-log write failures are swallowed — they can never
  block the grant.

### 6. Backfill — `scripts/backfill_session_date.py`

- Idempotent script (safe to re-run).
- For each `point_events` row with NULL `session_date`:
  1. Look for an `attendance` row matching `(group_name,
     student_name, attendance_date within ±1 day of awarded_at,
     status IN ('حاضر','متأخر'))` → use that
     `attendance_date`.
  2. Else fall back to `awarded_at` converted to Bahrain TZ.
- Reports counts: `via_attendance / via_local_date / errors`.
- Run on prod via Render shell after deploy:
  `python scripts/backfill_session_date.py`.

### 7. Smoke — `scripts/smoke_points_budget_phase1.py`

10 scenarios covering schema markers, write path, read path,
teacher reject, admin bypass, explicit override, cumulative
sums, session boundary, legacy-row isolation. Self-sandbox +
teardown. Green locally.

## Deviations from spec (callouts for the owner)

1. **`group_name` instead of `group_id`.** The spec wrote
   `group_id INTEGER` but `point_events` has stored
   `group_name TEXT` since `points_v1` (line 5978). The entire
   points subsystem keys on the textual group name —
   `_pts_can_grant`, `_pts_visible_groups`, `_pts_balance` all
   read it that way. Introducing an integer FK would require
   refactoring every `point_events` query in the codebase
   (≈30 occurrences). Adopted `(group_name, session_date)` for
   the composite index instead. **Functionally identical** for
   the Phase 1 feature; no callers see the difference.

2. **Helpers prefixed `_pts_*`, not `_points_*`.** Sibling
   helpers in the same module (`_pts_user_role`,
   `_pts_can_grant`, `_pts_balance`, `_pts_resolve_avatar`)
   all use `_pts_`. Followed the convention.

3. **Admin bypass is the default (C4), audit fires when over
   the cap (C5).** Strict reading of C4 said "admin bypasses
   without override". C5 said "?override=1 enables bypass +
   audit log". Implemented:
   - Admin bypass = always on (C4 literal).
   - Audit row written whenever an admin grant **actually**
     exceeds the cap, OR `?override=1` is explicitly sent.
   - This catches every real bypass without spamming the log
     for routine within-budget admin grants.

4. **Negative behaviours count toward the cap at absolute
   value.** A teacher can't "earn" extra budget by stacking
   negative behaviours. If owner prefers net-sum semantics
   (where -2 frees up 2 points of remaining budget), it's a
   one-line change to `_pts_session_used` — flag for Phase 2
   review.

5. **`session_date TEXT`, not `DATE`.** Postgres has a strict
   `DATE` type; SQLite is forgiving. `attendance.attendance_date`
   is already `TEXT` (`YYYY-MM-DD` per the ATTENDANCE RULE),
   and a `TEXT = TEXT` compare is what makes the budget query
   work on both engines without casts.

## What does NOT change

- `/points/board` HTML — untouched.
- `behaviors` table + seeded categories — untouched.
- `/api/points/group`, `/api/points/student/...`, all
  redemption endpoints — untouched.
- Existing `point_events` rows — untouched until the operator
  explicitly runs the backfill script.

## Boot + smoke status

- `python -c "import app"` → ✓ clean.
- `point_events` columns post-migration: includes `session_date`.
- `idx_point_events_session` present on local DB.
- All 10 smoke scenarios green.
- Existing parent / evaluations / books smokes unaffected
  (none touch `point_events`).

## Deployment steps (Render)

1. `git push origin main` — already done as part of the
   commit chain.
2. Render auto-deploys; the migration `points_session_date_v1`
   runs at boot and adds the column + index idempotently.
3. From the Render shell:
   `python scripts/backfill_session_date.py`
   (one-time, idempotent — fills legacy rows).
4. Owner browser-tests the cap:
   - Open `/points/board/<a group>` as a teacher → grant
     a small award (still works).
   - Try to over-grant as the same teacher → 400 toast
     (UI surfacing arrives in Phase 2; for now it shows the
     raw `error` text via the existing `toast()` call).
   - Log in as admin → same over-grant succeeds → check
     `audit_log` has one fresh `points_budget_override` row.

## Awaiting Phase 2

UI changes (progress bar, quick-action buttons, warning
toasts, distribute-evenly, undo) all key off the data this
phase ships. Recommend running owner browser-test against
prod first, then proceeding.
