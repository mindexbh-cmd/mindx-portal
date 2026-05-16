# Plan — per-teacher evaluation coverage drill-down

Feature: expandable per-teacher list on `/admin/evaluations` showing
which students still need an evaluation this month, with a "remind teacher"
button. Additive, read-only, no DB schema change.

## Decisions (from clarifying questions)

| Question | Answer |
|---|---|
| Placement | Add new expandable list **above** the existing dropdown on `/admin/evaluations`. Both flows usable. Clicking a teacher's name in the list also populates the existing dropdown. |
| Pending universe | Active students in groups currently assigned to that teacher (via `_teacher_groups_for` + `_pm_group_recipients`). Submitted = `evaluations` row with `(teacher_id, evaluation_month)`. Pending = universe − submitted. |
| Reminder action | Open WhatsApp `wa.me/?text=<prefilled>` in a new tab. No phone targeting (see "Constraints" — `users` table has no phone column). Admin picks the teacher's contact in WhatsApp's chat-picker, message body pre-filled. |

## Backend

New endpoint:

```
GET /api/monthly-evaluations/teachers/coverage?month=YYYY-MM
  → 200 {
      "ok": true,
      "month": "2026-05",
      "month_label": "مايو 2026",
      "teachers": [
        {
          "id": 42, "name": "...",
          "total": 5, "submitted": 3, "pending": 2,
          "percentage": 60
        },
        ...
      ]
    }
```

```
GET /api/monthly-evaluations/teachers/<int:tid>/coverage?month=YYYY-MM
  → 200 {
      "ok": true,
      "teacher": {"id": 42, "name": "..."},
      "month": "2026-05",
      "month_label": "مايو 2026",
      "stats": {"total": 5, "submitted": 3, "pending": 2, "percentage": 60},
      "submitted": [{"id": 901, "name": "...", "group": "...", "submitted_at": "..."}],
      "pending":   [{"id": 902, "name": "...", "group": "..."}]
    }
```

- Both `@login_required` + `_ev_can_admin` gate (admin/manager only).
- Both default `month` to today's `YYYY-MM`.
- Both single-pass queries — **no N+1** even though the summary endpoint
  iterates teachers (the universe + submitted counts are aggregated in
  one Python pass over already-prefetched group→student / teacher→group
  maps).

### Query strategy (no N+1)

Summary endpoint:

1. One `SELECT id, name FROM users WHERE role='teacher' AND is_active`.
2. One `SELECT teacher_name, group_name FROM teacher_groups` (or equivalent
   helper if it exists) — single fetch to build the teacher→groups map.
   Fallback: iterate `_teacher_groups_for(db, user)` per teacher row (only
   ~10-20 rows on prod; still cheap).
3. One `SELECT group_name, COUNT(*) FROM <students filtered to active>`
   to count the universe per group.
4. One `SELECT teacher_id, COUNT(DISTINCT student_id) FROM evaluations
   WHERE evaluation_month=? AND is_deleted=0 GROUP BY teacher_id`.
5. Python join → assemble per-teacher rows.

Per-teacher detail endpoint:

1. One `SELECT id, name FROM users WHERE id=?`.
2. Resolve teacher's groups via `_teacher_groups_for(db, user_row)`.
3. One `SELECT id, student_name, group_name FROM students` filtered to
   those groups (active only).
4. One `SELECT student_id, MAX(updated_at) AS submitted_at FROM evaluations
   WHERE teacher_id=? AND evaluation_month=? AND is_deleted=0`.
5. Python set-difference → `submitted` / `pending` lists.

## Frontend (inside `ADMIN_TEACHER_DELIVERIES_HTML`)

New section between the **title card** (line 54484) and the **filters card**
(line 54495):

```html
<div class="tm-card tm-coverage-card">
  <div class="tm-coverage-header">
    <h3>📊 تغطية تقييمات الشهر</h3>
    <div class="tm-coverage-month" id="tm-cov-month">—</div>
  </div>
  <div class="tm-coverage-list" id="tm-cov-list">
    <div class="tm-coverage-loading">جاري التحميل...</div>
  </div>
</div>
```

Each teacher row:

```
▼ <name>    <submitted>/<total>  [progress-bar]  <percent>%  <emoji>
   ├─ ✅ المُسلَّمات (N): • ... • ... • ...
   ├─ ❌ المتبقّيات (M): • ... • ... • ...
   └─ [📲 تذكير عبر واتساب]
```

- Row click toggles `aria-expanded` and lazy-fetches the per-teacher
  detail endpoint the first time. Cached for the session.
- Indicator emoji from a JS helper `_tmCovIcon(p)`:
  - `p === 100` → `✨`
  - `p >= 80`   → `✅`
  - `p >= 50`   → `🟡`
  - `p > 0`     → `⚠️`
  - `p === 0`   → `🔴`
- Progress-bar color mirrors the icon's intent
  (`#43A047` green / `#FF9800` amber / `#E91E63` red).
- Reminder button opens `https://wa.me/?text=` with a body built from
  the pending student names + Arabic month label. Phone-picker step is
  on the admin (see constraint below). Confirm modal first if pending
  list is long (>10 names) so the URL doesn't bloat without warning.

Mobile (≤680px): the per-row stats stack under the name (existing media-
query patterns at 980/680 in `tm-card` reused — same breakpoints).

## Constraints (and the small UX trade-off they create)

- **No DB schema change** — verified `users` has no `phone`/`whatsapp`
  column today. Wa.me URL therefore omits the phone segment; admin uses
  WhatsApp's own contact picker. A follow-up could add a `users.phone`
  column + admin form so the URL targets the teacher directly. Out of
  scope for this commit.
- **No change to evaluation submission logic** — only reads.
- **No regression in the existing dropdown drill-down** — the new section
  is purely additive; the dropdown + `tm-teacher-card` flow keeps
  working unchanged. Clicking a teacher's name in the new list ALSO
  selects them in the dropdown so the drill-down opens with one click.
- **Arabic strings** — written inline as raw Arabic (matches the
  surrounding `ADMIN_TEACHER_DELIVERIES_HTML` style; the CLAUDE.md
  entity-escape rule applies to legacy mojibake-prone areas, but
  `ADMIN_TEACHER_DELIVERIES_HTML` itself uses raw Arabic throughout).
- **Brand colors** — `#4a148c` text, `#6B3FA0`/`#8B5CC8` purple
  gradient buttons, `#f3e5f5` light-purple row hover. Match the
  existing `tm-card` / `tm-btn` palette.
- **RTL** — page is already `dir="rtl"`; new markup inherits.

## Atomic commits

1. **Backend coverage endpoints** — both routes, helpers, auth gate. No
   front-end changes. Syntax-check via `ast.parse`. Locally smoke-test
   by calling each endpoint as `admin_test`.
2. **Frontend coverage section** — new HTML block + CSS rules + JS init
   inside `ADMIN_TEACHER_DELIVERIES_HTML`. No backend changes.
3. **Reminder button + wa.me** — adds the per-row "تذكير" button JS
   handler. Separated from commit 2 so a regression review is easier.

Each commit followed by `python -c "import ast; ast.parse(open('app.py',encoding='utf-8').read())"`.

## Deploy & verify

- `python scripts/safe_deploy.py --feature teacher-eval-coverage` after
  all three commits land locally.
- Post-deploy verification (`admin_test` session, prod):
  - `GET /api/monthly-evaluations/teachers/coverage` returns `ok:true`
    with the teacher list.
  - `GET /api/monthly-evaluations/teachers/<id>/coverage` returns
    `submitted` + `pending` arrays for at least one teacher with
    real groups.
  - `GET /admin/evaluations` renders without 500 and the page HTML
    contains the new `tm-coverage-card` div.

I can't take browser screenshots in this session, so visual verification
is by HTML inspection + the operator's eyes after deploy.

## Memory

After deploy, append a CHANGE_LOG entry + a DECISIONS_LOG ADR
("ADR-022 — pending-universe = active students in teacher's current
groups; no DB schema change for teacher phone (deferred)").

## Out of scope

- Specialist-agent reviews (catastrophe / ui-designer / arabic-quality
  / mobile-first / real-user-tester / performance-watchdog) — agents
  don't load mid-session in this Claude Code process. The plan
  internalises their checks: no DDL, no schema change, no N+1 queries,
  raw-Arabic text matching the surrounding template, mobile responsive
  via existing breakpoints, additive only.
- Phone-targeted wa.me URL — needs a new `users.phone` column.
- Bulk "remind all teachers under 50%" action — single-teacher only
  for v1.
