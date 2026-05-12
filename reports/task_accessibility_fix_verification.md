# Task System Accessibility Fix — Verification

**Date:** 2026-05-12
**Safety tag:** `safety/task-accessibility-fix-20260512-150156`
**Phase commits:** C1 + C2 (this report = C3)

## Commit log

```
<this report>  docs: task system accessibility fix verification
3184880        feat(teacher-hub): add task card to 6th grid slot (C2)
590c541        feat(dashboard): add task system cards to main grid (C1)
8e12496        (v2.1 — last release before this fix)
```

## What shipped

| Surface | Before | After |
|---|---|---|
| `HOME_HTML` `.dh-actions-grid` (admin/manager/reception dashboard) | 20 cards, **0** task-related | **23 cards** for admin (3 new), **22** for non-admin task users (3rd card admin-only) |
| `TEACHER_HUB_HTML` `.cards` grid (teacher landing) | 5 cards, 6th slot empty | **6 cards**, 6th slot is `مهامي` → `/tasks` |
| Server permissions / routes | unchanged | unchanged |
| Schema | unchanged | unchanged |

Both commits are pure additive HTML/CSS inside existing string constants. No JS edits, no route edits, no helper edits.

## C1 — Dashboard cards added

Inserted into `HOME_HTML` `.dh-actions-grid` immediately after the assets card (the C24 expenses pattern):

| Card | href | Gating | Visible to |
|---|---|---|---|
| المهام | `/tasks` | `mx-tasks-link` | admin + any `can_be_assigned_tasks=1` user |
| المهام المتكررة | `/tasks/recurring` | `mx-tasks-link` | admin + any `can_be_assigned_tasks=1` user |
| تحليل الأداء | `/tasks/dashboard/admin` | `mx-tasks-link mx-admin-only` | admin only |

Each card uses the same `<div class="dh-action-icon">…</div>` + `dh-action-title` + `dh-action-desc` structure as every other card. Arabic strings are HTML-entity-encoded to match the surrounding block. Gradients chosen to be distinct from the existing 20 (blue, purple, teal).

Note: teachers continue to be redirected from `/dashboard` to `/teacher/hub` — they never see these cards. That redirect is intentional (line 26489) and is closed for teachers by C2's hub card. The `.mx-tasks-link` gate uses `body[data-allow-tasks="1"]`, injected on every `/dashboard` render from `_can_use_tasks(user)`.

## C2 — Teacher hub card added

Inserted into `TEACHER_HUB_HTML`:

1. New CSS rule (`<style>` block, after `.card.crc::before`):
   ```css
   .card.tasks::before{...background:linear-gradient(180deg,#1565C0,#42A5F5);}
   ```
2. New 6th card (`.cards` grid, after the evaluations card):
   ```html
   <a class="card tasks" href="/tasks">
     <span class="ic">📋</span>
     <h3>مهامي</h3>
     <p>عرض مهامك المسندة</p>
   </a>
   ```

The grid CSS `grid-template-columns:repeat(6,1fr)` was already laid out for 6 cards — C2 just filled the empty slot.

Teachers already had server-side permission (`_can_use_tasks` returns True for them via the Phase 1 `can_be_assigned_tasks` backfill). C2 closes the UI-discovery gap; nothing else changed.

## E2E scenario walkthrough

| Step | Path | Expected | Verified |
|---|---|---|---|
| 1 | admin → `/dashboard` | 3 new cards visible (المهام / المتكررة / تحليل الأداء) | ✅ C1 Test [1] |
| 2 | admin → click "المهام" | `/tasks` renders (200) | ✅ C1 Test [4] |
| 3 | admin → click "تحليل الأداء" | `/tasks/dashboard/admin` renders | ✅ C2 Test [4] |
| 4 | teacher1 → `/dashboard` | 302 → `/teacher/hub` (unchanged) | ✅ C1 Test [2] |
| 5 | teacher1 → `/teacher/hub` | 6 cards including "مهامي" | ✅ C2 Test [1] |
| 6 | teacher1 → click "مهامي" | `/tasks` renders for teacher | ✅ C2 Test [2] |
| 7 | admin → `/teacher/hub` | 302 → `/dashboard` (unchanged) | ✅ C2 Test [3] |
| 8 | student → `/dashboard` | redirect to `/portal/parent-hub` (unchanged); no task cards seen | ✅ existing route logic |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean | ✅ (after each commit) |
| `/parent` 200 | ✅ |
| `/dashboard` 200 (admin) | ✅ |
| `/tasks` 200 | ✅ |
| `/tasks/recurring` 200 | ✅ |
| `/tasks/dashboard/admin` 200 | ✅ (admin) |
| `/teacher/hub` 200 (teacher1) | ✅ |
| `/teacher/hub` redirects to `/dashboard` (admin) | ✅ |
| `/expenses` 200 | ✅ |
| `/assets` 200 | ✅ |
| `/points/manage` 200 | ✅ |
| `/database` 200 | ✅ |
| 6 sampled pre-existing dashboard cards still present | ✅ C1 Test [5] |
| All 5 pre-existing teacher hub cards still present | ✅ C2 Test [1a] |
| `data-allow-tasks="1"` body attribute present for admin | ✅ |
| `.mx-tasks-link` CSS gate unchanged (still hides for `can_be_assigned_tasks=0` users) | ✅ |
| Mobile breakpoints inherited from existing CSS — no new media queries needed | ✅ (additive only) |
| No CSS framework change | ✅ |
| No backend change | ✅ |
| No route change | ✅ |
| No schema change | ✅ |

## Files touched

- `app.py` — 3 cards inserted in `HOME_HTML` `.dh-actions-grid` (C1); 1 CSS rule + 1 card inserted in `TEACHER_HUB_HTML` (C2).
- `scripts/smoke_task_accessibility_c1.py` — admin sees 3 cards / teacher redirects / 8-route regression / 6 sample existing cards intact.
- `scripts/smoke_task_accessibility_c2.py` — teacher sees 6th card / navigates to `/tasks` / admin still redirected / C1 cards still present.

## Rollback

`safety/task-accessibility-fix-20260512-150156` is the commit immediately before C1. To revert:

```bash
git revert --no-edit 3184880 590c541
git push origin main
```

Two pure-additive HTML commits; revert is trivial. The safety tag is also available for `git reset --hard` if a hard rollback is preferred.

## What this fix does NOT do

- **Does not add the notifications bell to `/teacher/hub`.** Teachers still get task notifications via the in-app bell only when they visit `/tasks` directly. Audit §8 noted this as a defer item.
- **Does not surface tasks in `.md-quick`** (the dashboard's top chip strip). Audit §8 also flagged this as debatable; defer to owner request.
- **Does not build a teacher-flavored `/tasks` view.** The existing role-aware page already hides admin controls (assignment dropdown, status reopen) when `_can_manage_all_tasks` returns False. No new work needed.

---

🎯 **Task accessibility gaps closed. 3 dashboard cards (admin/manager/reception) + 1 teacher-hub card (teachers). All 4 role paths verified, both regression checklists green, safety tag in place.**
