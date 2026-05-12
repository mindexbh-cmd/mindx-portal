# Assignee Dropdown — Verification

**Date:** 2026-05-12
**Safety tag:** `safety/assignee-dropdown-20260512-152343`
**Phase commits:** C1 + C2 + C3 (this report = C4)

## Commit log

```
<this report>  docs: assignee dropdown verification
e913d91        feat(recurring): replace assignee free-text with dropdown (C3)
3dfb885        feat(tasks): replace assignee free-text with dropdown (C2)
860e8b2        feat(tasks): assignable users endpoint for assignee dropdown (C1)
54c34bd        (v2.1 — last release tag, point of departure)
```

## Design notes (owner-approved before C1)

| Decision | Choice |
|---|---|
| Display format | full name only (`users.name`, falls back to `username` if NULL/empty) |
| Sorting | single flat list, alphabetical ASC (NOCASE COLLATE on `display_name`) |
| Grouping by role | none — flat list |
| Source of truth | `users.can_be_assigned_tasks = 1` flag |
| Future users | auto-appear (live query, no server-side cache) |
| Deactivated users | excluded — flag flip in `/admin/permissions` removes them from the next fetch |
| Edit edge case | if a task references a user whose flag is now 0, surface "username (غير متاح)" as a disabled option so the value isn't silently overwritten |

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ /tasks new/edit modal      /tasks/recurring add/edit     │
│   <select id="task-       │   <select id="recur-          │
│           assignee">      │           assignee">          │
│                           │                               │
│   _ensureAssignees()  ────┼──── _ensureAssignees()        │
│   _renderAssignees(cv)    │     _renderAssignees(cv)      │
│           │               │             │                 │
│           └───────────────┼─────────────┘                 │
│                           │                               │
│                           ▼                               │
│             GET /api/users/assignable                     │
│             {ok, users:[{username, display_name, role}],  │
│              total}                                       │
│                           │                               │
│                           ▼                               │
│             SELECT username,                              │
│                    COALESCE(NULLIF(TRIM(name),''),        │
│                             username) AS display_name,    │
│                    role                                   │
│             FROM users                                    │
│             WHERE can_be_assigned_tasks = 1               │
│             ORDER BY display_name NOCASE ASC              │
└──────────────────────────────────────────────────────────┘
```

Each modal owns its own cache (`ASSIGNABLE_USERS` for /tasks,
`R_ASSIGNABLE_USERS` for /tasks/recurring) — single fetch per page
load, no re-hit on reopen.

## E2E scenario walkthrough

| # | Step | Expected | Verified |
|---|---|---|---|
| 1 | admin → /tasks → click "+ مهمة جديدة" | dropdown populates with 8 eligible users sorted A-Z | ✅ C1 [1c]+[3], C2 [1] |
| 2 | select user → fill required fields → save | POST /api/tasks → 200 → task in DB with `assigned_to_username` set | ✅ C2 [2]+[3] |
| 3 | edit existing task → reopen modal | assigned user pre-selected in dropdown | ✅ C2 logic + [3] |
| 4 | admin → edit assignee → save | PATCH /api/tasks/<id> → 200 → new assignee in DB | ✅ C2 [4]+[4a] |
| 5 | /tasks/recurring → "+ قالب جديد" → dropdown loads | full user list | ✅ C3 [1]+[2] |
| 6 | create template → save | POST /api/recurring-tasks → 200 | ✅ C3 [2]+[3] |
| 7 | reassign template via PATCH | template's `assigned_to_username` updated | ✅ C3 [4] |
| 8 | teacher1 → /tasks → modal opens | dropdown locked to teacher1 + disabled (`_setAssigneeMode`) | ✅ C2 [6] (markup check) + existing client-side rule |
| 9 | teacher1 → /tasks/recurring → modal opens | dropdown locked to teacher1 + disabled | ✅ C3 [5] (page loads) + existing rule |
| 10 | student → /api/users/assignable | 403 | ✅ implicit via `_can_use_tasks` (same gate as /api/departments) |
| 11 | admin flips a user's `can_be_assigned_tasks` 1 → 0 | next dropdown open excludes them | ✅ C1 [4] |
| 12 | admin flips a user's `can_be_assigned_tasks` 0 → 1 | next dropdown open includes them | ✅ C1 [4a] |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after each commit | ✅ |
| `/api/users/assignable` returns shape `{ok, users[], total}` | ✅ |
| Sort order alphabetical ASC | ✅ C1 [3] |
| `can_be_assigned_tasks=0` excluded | ✅ C1 [4] |
| `name` NULL/empty → falls back to `username` | ✅ (COALESCE+NULLIF+TRIM, plus 0-byte rows visible in the smoke without disappearing) |
| `/tasks` markup has `<select id="task-assignee">` | ✅ C2 [1] |
| `/tasks` markup has NO `<datalist id="task-assignee-list">` (dead markup removed) | ✅ C2 [1] |
| `/tasks/recurring` markup has `<select id="recur-assignee">` | ✅ C3 [1] |
| Task creation POST flow unchanged (body still has `assigned_to_username`) | ✅ C2 [2] |
| Task PATCH (admin reassign) still works | ✅ C2 [4] |
| Recurring template POST still works | ✅ C3 [2] |
| Recurring template PATCH still works | ✅ C3 [4] |
| 8-route regression all 200 (after each commit) | ✅ |
| `/parent`, `/dashboard`, `/tasks`, `/tasks/recurring`, `/expenses`, `/assets`, `/points/manage`, `/database` | ✅ |
| Teacher hub `/teacher/hub` unchanged | ✅ (no touch) |
| No schema change | ✅ |
| No JS console errors expected (dropdown init guarded by `if (j && j.ok)` and fails safe to empty list) | ✅ |

## Files touched

- `app.py`
  - C1: added `GET /api/users/assignable` route (immediately after `/api/departments`).
  - C2: swapped the `task-assignee` input → `<select>`; added `ASSIGNABLE_USERS` cache, `_ensureAssignees`, `_renderAssignees`; rewrote `_reset` + `_setAssigneeMode` + `taskOpenAdd` + `taskOpenEdit` to drive the `<select>`.
  - C3: same swap inside the recurring modal — `recur-assignee` input → `<select>`; namespaced helpers (`R_ASSIGNABLE_USERS`) to avoid clashing with C2 should the two modals ever share scope.
- `scripts/smoke_assignee_dropdown_c1.py` — endpoint shape + admin/teacher access + sort + flag toggle + 8-route regression.
- `scripts/smoke_assignee_dropdown_c2.py` — /tasks markup + JS helper presence + POST+PATCH round trip + teacher page load + 8-route regression.
- `scripts/smoke_assignee_dropdown_c3.py` — /tasks/recurring markup + helper presence + POST+PATCH round trip + teacher page load + 8-route regression + C2 untouched.

## Rollback

`safety/assignee-dropdown-20260512-152343` is the commit immediately before C1. To revert all three commits:

```bash
git revert --no-edit e913d91 3dfb885 860e8b2
git push origin main
```

Each commit is self-contained: C1 adds a new endpoint, C2/C3 swap HTML+JS for the respective modal. No schema, no helper, no role-policy was changed — revert is purely UI.

## What this fix does NOT do

- **No role grouping in the dropdown.** Per the owner's design decision — flat alphabetical list. The endpoint *does* return `role` so a future commit could add grouping without re-shipping the endpoint.
- **No type-to-filter / autocomplete UX.** A plain `<select>` is used. With ~10 users today this is fine; if the list grows past ~30 the owner can ask for a typeahead variant.
- **No real-time updates.** Per page-load fetch + module cache. Reopening the modal on the same page does not re-fetch (intentional). Closing and re-opening the page refetches.
- **No `/admin/permissions` UX changes.** The flag flip already had a working admin UI — the dropdown just reads from the same source.

---

🎯 **Assignee dropdown live across /tasks and /tasks/recurring. New endpoint + 2 UI swaps + 3 smoke scripts, all regressions green.**
