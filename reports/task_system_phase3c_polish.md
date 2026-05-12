# Task System — Phase 3c Polish Verification

**Date:** 2026-05-12
**Safety tag (pre-change):** `safety/task-system-phase3c-20260512-115348`
**Phase 3c HEAD:** *(this report's commit)*
**Commits:** 4 commits (C37–C40 including this report + sidebar update)

## Commit Log

```
<this commit>  docs(task-phase3c): Phase 3c polish verification + sidebar link
97c88d0        feat(task-phase3c): recurring add/edit modal
52be8ae        feat(task-phase3c): /tasks/recurring page
f06bd41        feat(task-phase3c): notifications bell in dashboard
```

## What Phase 3c delivers

Phase 3b said "no recurring-tasks UI, no notifications bell — both deferred." Phase 3c closes both gaps.

### 1. Notifications bell (C37)

New bell + dropdown in the dashboard topbar, sitting next to the existing teacher-deliveries bell. Visible only to users with task access via `.mx-tasks-link`.

- Polls `/api/notifications/unread-count` every 60 seconds + on bell click
- Dropdown shows last 20 notifications from `/api/notifications`
- Each row is a clickable `<a>` linking to `/tasks/<task_id>` (when applicable)
- Click on unread row → fires `POST /api/notifications/<id>/read` then navigates
- "علّم كل المقروء" header button → bulk mark-read (parallel calls, optimistic DOM update)
- "عرض كل المهام" footer link → `/tasks`
- Outside-click closes the dropdown
- 99+ display for huge counts

The existing `#md-tb-bell` teacher-deliveries bell is preserved 100% intact.

### 2. `/tasks/recurring` page (C38)

New page route + role-aware list.

- Shows the C23 endpoint's template list with frequency-specific pills:
  - **daily** — amber "📅 يومي"
  - **weekly** — blue "📅 أسبوعي — \<Arabic day name\>" (0=Sun..6=Sat)
  - **monthly** — purple "📅 شهري — يوم N"
  - **inactive** — grey "⏸️ معطّل"
- "Show inactive templates" toggle (switches `?is_active=1` filter on/off)
- "+ قالب متكرر جديد" button
- Edit pencil + delete trash (soft-delete via DELETE → `is_active=0`)
- Action buttons gated to admin OR creator (matches C23 backend RBAC)

### 3. Recurring add/edit modal (C39)

Modal spliced into the recurring page.

- All 8 fields from the spec: title, description, dept, assignee, priority, hours, frequency, tags
- Frequency picker has 3 pills (daily / weekly / monthly) that toggle conditional rows:
  - **weekly** → day_of_week dropdown (Sunday-anchored Arabic labels)
  - **monthly** → day_of_month input (capped at 28 per the C23 schema constraint)
- Non-admin sees the assignee field locked to self (same UX guardrail as the C30 task modal)
- Validation messages exactly match the C23 backend errors
- POST/PATCH/DELETE routes existing C23 endpoints

### 4. Sidebar (this commit)

Added 1 new nav anchor to the existing "📋 نظام المهام" section:

```html
<a class="md-sb-link mx-tasks-link" href="/tasks/recurring">
  🔁 القوالب المتكررة
</a>
```

Inserted between the "لوحة الفريق" entry and the admin-only "تحليل الأداء" entry, so it appears in the natural visual order within the section. The `mx-tasks-link` gating mirrors every other link in the section.

## Smoke summary

| Commit | Script | Pass |
|---|---|---|
| C37 | `smoke_task_phase3c_c37.py` (13 markup + 3 endpoint + 8 regression) | ✅ |
| C38 | `smoke_task_phase3c_c38.py` (9 markup + 3 role paths) | ✅ |
| C39 | `smoke_task_phase3c_c39.py` (12 markup + E2E PATCH freq) | ✅ |
| **total** | | **48 assertions, all green** |

## Live spot-check (admin session)

| Endpoint / page | HTTP | Notes |
|---|---|---|
| `/dashboard` | 200 | Now has 2 bells in the topbar (task-notifications + teacher-deliveries) |
| `/dashboard` sidebar has 5 task links | ✅ | tasks / personal / team / recurring / admin |
| `/tasks/recurring` (admin) | 200 | Full list with frequency pills + modal |
| `/tasks/recurring` (raed) | 200 | Sees only own templates (API auto-scoping) |
| `/tasks/recurring` (student) | 403 | Polite page |
| `/api/notifications/unread-count` | 200 | `{ok:true, count:N}` |
| `/api/notifications?limit=20` | 200 | Last 20 newest-first |
| `POST /api/notifications/<id>/read` | 200 | Owner only |
| `POST /api/recurring-tasks` | 200 | Validates frequency cross-requirements |
| `PATCH /api/recurring-tasks/<id>` | 200 | Frequency changes apply day-of-week/month correctly |
| `DELETE /api/recurring-tasks/<id>` | 200 | Soft delete (is_active=0) |

## Regression confirmed

All Phase 1 / 2a / 2b / 3b surfaces continue to respond correctly:

- `/parent`, `/points/manage`, `/portal/parent-hub/points` unchanged
- `/expenses`, `/assets`, `/database`, `/groups`, `/attendance` all 200
- `/dashboard` still renders the existing 28 cards + the new bell adjacent to the old bell
- Phase 3b's 5 task pages (`/tasks`, `/tasks/<id>`, `/tasks/dashboard/personal`, `/tasks/dashboard/team`, `/tasks/dashboard/admin`) all 200
- BYTEA serve paths (`/api/rewards/<id>/image`, `/api/books/<id>/view`) untouched
- Financial system endpoints all respond

## What is NOT in Phase 3c

- **Scheduler** — recurring templates still don't auto-generate child tasks. That requires a separate worker (cron-on-Render OR request-time check) and is genuinely Phase 4 work. The recurring-tasks table now has UI to create/edit/delete templates; the scheduler turning them into actual tasks rows is deferred.
- **Notifications page** — a dedicated `/notifications` page that shows the full history beyond the 20-row dropdown. Most users won't need this; the dropdown + per-task notifications are enough for v1.

## Rollback

`safety/task-system-phase3c-20260512-115348` is the commit immediately before C37. To revert all 4 commits:

```
git reset --hard safety/task-system-phase3c-20260512-115348
git push --force-with-lease origin main
```

Phase 1 + Phase 2a + Phase 2b + Phase 3b stay intact. Only the bell, the recurring page, the modal, and the new sidebar link disappear cleanly.

---

🛑 **Phase 3c complete. Notifications bell + recurring-tasks UI live. The task management system's UI surface is now complete — every Phase 2 API endpoint has a corresponding UI hook. Awaiting owner final acceptance or guidance for the deferred scheduler (Phase 4).**
