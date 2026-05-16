# Plan — teacher coverage enhancements (month picker + group breakdown)

Two additive enhancements to the per-teacher coverage drill-down shipped
in commits `7c63c37` / `9b00b85` / `f65f492` (see ADR-022). No DB schema
change. Same admin gate, same read-only posture.

## Enhancement 1: Month picker

- New endpoint `GET /api/monthly-evaluations/months` → list of months
  that have ANY non-deleted evaluations row, **plus** the current month
  even if it has zero rows yet (so admins can confirm "0 yet" instead
  of "month not shown"). Sorted DESC, current month always at the top.
  Each entry: `{value: "YYYY-MM", label: "<arabic-month> YYYY"}`.
- Existing `/teachers/coverage` and `/teachers/<int:tid>/coverage`
  already accept `?month=YYYY-MM` (`_ev_coverage_resolve_month`). No
  backend change needed for them.
- Frontend: a `<select>` between the title row and the teacher list,
  defaulted to current month. On change → reset cache, refetch summary,
  close all expanded rows.

## Enhancement 2: Group-level breakdown

The detail endpoint currently returns flat `submitted[]` + `pending[]`
lists. Reshape to:

```json
{
  "ok": true,
  "teacher": {"id":..,"name":".."},
  "month": "2026-05",
  "month_label": "مايو 2026",
  "groups": [
    {
      "name": "مجموعة 01",
      "stats": {"total":3, "submitted":2, "pending":1, "percentage":67},
      "submitted": [{"id":.., "name":"..", "group":"..", "submitted_at":".."}],
      "pending":   [{"id":.., "name":"..", "group":".."}]
    },
    ...
  ],
  "overall_stats": {"total":.., "submitted":.., "pending":.., "percentage":..}
}
```

- Students appearing in multiple groups for the same teacher are still
  deduped (first-group-wins, matches existing `seen` set logic).
- Groups with 0 active students are skipped (would render as
  meaningless "0/0 100% ✨").

Frontend: per-group sub-rows with the same progress-bar + indicator
pattern as the outer teacher row. First group expanded by default
(useful state immediately).

## Updated reminder body

`tmCovBuildReminderText` flattens pending student names into one list
today. New version groups by `group_name`:

```
السلام عليكم <اسم المعلمة>،

تذكير من إدارة مايندكس: لم يتم بعد إرسال تقييم
الطالبات التاليات لشهر <مايو 2026>:

— مجموعة 01:
  • نور حسن
  • ياسين فؤاد

— مجموعة 02:
  • خالد علي

شكراً لكم على تعاونكم.
```

Same 20-name URL cap; if hit, append `… و N طالبة أخرى`.

## Atomic commits

1. **Backend** — `/months` endpoint + reshape `/teachers/<int:tid>/coverage`
   to return `groups[]` + `overall_stats`. Summary endpoint unchanged
   (still serves the per-teacher counts the outer list needs).
2. **Frontend month plumbing** — dropdown + state + refetch wiring,
   passes `?month=` to both fetches. Still uses the old flat render
   path for detail (kept temporarily so commit 2 is shippable on its
   own; commit 3 replaces it).
3. **Frontend group breakdown** — `tmCovRenderDetail` rewrite consuming
   the new `groups[]` shape. Nested expand/collapse, first group open
   by default, mobile-responsive via existing 680px breakpoint.
4. **Frontend reminder** — `tmCovBuildReminderText` rebuilds the body
   from `groups[]`, capping at 20 students total.

Between every commit: `python -c "import ast; ast.parse(open('app.py',encoding='utf-8').read())"`.

## Deploy + verify

- `safe_deploy --feature teacher-cov-enhancements`.
- Verify on prod (admin_test session):
  - `GET /api/monthly-evaluations/months` returns array with current
    month at index 0.
  - `GET /teachers/coverage?month=2026-04` returns April data (if any
    exists — likely empty since prod has only `evaluation_month=2026-05`).
  - `GET /teachers/<real-tid>/coverage` returns `groups[]` populated.
  - `/admin/teacher-deliveries` HTML contains new markers
    (`tm-cov-month-sel`, `tm-cov-group-row`, etc.).

Cannot screenshot — visual sanity is on the operator.

## Memory

CHANGE_LOG entry + ADR-023 (universe-per-group rule; first-group-wins
dedup explicitly preserved).

## Out of scope

- No agent reviews (still don't load mid-session in Claude Code).
- No phone-targeted wa.me (still no `users.phone` — ADR-022 pending).
- No "remind all teachers under 50%" bulk action.
