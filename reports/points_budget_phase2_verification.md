# Phase 2 — Points board UI integration — Verification

**Scope:** teacher-facing UI on `/points/board/<group>` and the
thin server-side affordances it requires (per-student session
roll-up, attendance-driven absent block, single-event undo).
Phase 1's cap enforcement is untouched.

**Safety tag:** `safety/points-budget-phase2-20260513-151026`
(created before C1).

## Commit chain (on `main`)

| Hash       | Subject                                                   |
|------------|-----------------------------------------------------------|
| `61a7ab4`  | feat(points-ui): budget progress bar at top of board      |
| `ca445ea`  | feat(points-ui): per-student session counter              |
| `babda74`  | feat(points-ui): quick-action point buttons               |
| `504ae08`  | feat(points-ui): warnings at 80% and 100% usage           |
| `eae4d22`  | feat(points): undo last award endpoint + UI               |
| `7792339`  | feat(points): no awards for absent students               |
| `55e8fc6`  | feat(points-ui): optional reason note field               |
| `91c5e65`  | feat(points-ui): refresh budget after award               |
| `7ecdc46`  | test(points): Phase 2 JS validation                       |
| (this PR)  | docs: Phase 2 verification                                |

## Feature summary

### 1. Budget progress bar (C1)

Sticky-feeling card at the top of `/points/board/<group>`:

  - Title: 💰 رصيد الحصة
  - Numbers: `used / budget نقطة • متبقي remaining`
  - Bar: animated width with three colour states
    (green &lt;80% / orange ≥80% / red ≥100%).
  - Data source: `GET /api/points/session-budget`.
  - Refreshes on group change + after every successful grant.

### 2. Per-student session chip (C2)

Each card now displays a coloured pill (top-right corner) with
that student's session-total:
  - `+N في الحصة` (green) for net-positive
  - `N في الحصة` (red) for net-negative
  - `0 في الحصة` (gray) when unchanged

Backend: new lightweight roll-up endpoint
`GET /api/points/session-events?group=<name>&date=<YYYY-MM-DD>`.

### 3. Quick-action buttons (C3)

Inline action row on every student card:
`[+1] [+2] [+5] [+10] [-1] [📝]`

  - Single-student grants — bypasses the multi-select +
    behavior-modal flow for the common case.
  - +1/+2/-1 hit seeded behaviors directly by exact value
    match.
  - +5/+10 use the first active positive behavior + a
    `points_override` delta (same bulk-adjust pattern, no new
    behaviors seeded).
  - Min 44px tap target on mobile.
  - Client-side budget pre-check + server-side cap from
    Phase 1 are both active.

### 4. Warnings at 80% / 100% (C4)

  - 80% threshold crossing → orange toast
    `تنبيه: متبقي N نقطة فقط`.
  - 100% threshold crossing → red toast
    `انتهى رصيد الحصة. لا يمكن منح نقاط إضافية.`
  - Quick buttons whose delta would exceed budget are
    disabled (grayed + non-clickable).
  - Toasts fire exactly once per upward transition (the
    `STATE._lastPctSeen` guard prevents spam on refresh).

### 5. Undo last award (C5)

  - New endpoint: `DELETE /api/points/grant/<event_id>`.
  - Permission: awarder OR admin/manager.
  - Window: today's session only (Bahrain TZ).
  - Hard-deletes the row, writes an `audit_log` entry with
    `action='points_event_undo'`.
  - Floating ↩ تراجع pill at bottom-left, visible 10s after
    each grant.

### 6. Absent student block (C6)

  - `/api/points/grant` rejects with HTTP 400 if any target
    student has an attendance row with status `غائب` for
    today.
  - Response payload pinpoints the blocked students:
    `{ absent: [{student_id, name}, ...] }`.
  - UI: grayscale + opacity + `❌ غائب` pill on absent cards;
    quick-action row hidden on those cards.
  - No-attendance-yet still allows awards (consistent with
    Phase 1's roster fallback).

### 7. Optional reason note (C7)

  - 📝 button on each card opens a focused modal:
    student name in the header, textarea (max 200 chars,
    live char counter), amount picker `+1 / +2 / +5 / +10 / -1`,
    save button.
  - Save → `POST /api/points/grant` with `note` populated.
  - Backdrop click + ESC close.

### 8. Real-time refresh (C8)

  - Single `refreshBoardState()` orchestrator fires
    `Promise.all([session-budget, session-events])` and
    applies both updates from the same snapshot.
  - Used by every grant path (multi-select, quick, note,
    undo) so the budget bar, chips, absent marks, and
    button states stay in lock-step.

### 9. JS validation smoke (C9)

  - `scripts/smoke_points_phase2_js.py` parses every
    `<script>` block in `POINTS_BOARD_HTML` with node's
    `Function` constructor, then asserts 22 Phase 2 markers
    + 8 regression markers present in the served HTML.
  - Phase 1 smoke remains green (re-run).

## What does NOT change

  - `/api/points/session-budget` response shape — additive
    only (none).
  - Phase 1 cap-enforcement logic in `/api/points/grant` —
    untouched.
  - Admin override + audit trail — untouched.
  - Behavior catalog + seeded point values — untouched.
  - Sound effects, level / avatar / balance rendering —
    untouched.
  - Quick-attendance modal, bulk-adjust page — untouched.

## Browser test scenarios for the owner

Order matters — features build on each other. Pretend you're
a teacher who just opened `/points/board/<a group>`.

### Scenario A — budget bar appears

  1. Open `/points/board/<group>`.
  2. ✅ A purple-bordered card appears at the top showing
     `0 / N نقطة • متبقي N` and a green bar.
  3. The number `N` = students-with-حاضر-or-متأخر-attendance
     × 10. If attendance not taken yet → N = roster size × 10.

### Scenario B — per-student chip

  1. Click `+2` next to فاطمة.
  2. ✅ Her balance bumps. A green chip `+2 في الحصة`
     appears on her card.
  3. Click `+5` again next to فاطمة.
  4. ✅ Chip updates to `+7 في الحصة`. Budget bar advances
     toward the right.

### Scenario C — warnings + disable

  1. Keep awarding +10s until used ≥ 80% of budget.
  2. ✅ Orange toast appears once: `تنبيه: متبقي … نقطة فقط`.
  3. ✅ Bar turns orange.
  4. Continue until 100%.
  5. ✅ Red toast: `انتهى رصيد الحصة. لا يمكن منح نقاط إضافية.`
  6. ✅ All quick-action buttons (except 📝) are grayed-out
     and unclickable. Bar turns red.

### Scenario D — undo

  1. Right after any successful grant, look bottom-left.
  2. ✅ ↩ تراجع pill is visible.
  3. Click it within 10s.
  4. ✅ Card balance drops back, chip retreats, bar shrinks,
     toast `✅ تم التراجع`.
  5. Wait 10s without clicking.
  6. ✅ Pill auto-hides.

### Scenario E — absent block

  1. Open `/teacher/attendance`, mark a student `غائب` for
     today.
  2. Return to `/points/board/<group>`.
  3. ✅ That student's card is grayed + has `❌ غائب` pill,
     quick buttons hidden.
  4. As an admin, manually POST `/api/points/grant` for
     that student → HTTP 400 with the absent payload.

### Scenario F — note modal

  1. Click 📝 on any student.
  2. ✅ Modal opens with the student's name, textarea
     focused.
  3. Type 50 characters → counter reads `50 / 200`.
  4. Tap +5, click حفظ ومنح.
  5. ✅ Modal closes, toast `✅ تم الحفظ ومنح +5`, bar +
     chip update.

### Scenario G — admin bypass

  1. Log in as admin / manager.
  2. Burn through the budget until 100%.
  3. Try a +5 quick button.
  4. ✅ Grant succeeds (admin bypass from Phase 1 is
     untouched). Bar goes into "over-100% but capped at 100%
     visually" state.
  5. Check `audit_log` — a `points_budget_override` row
     should exist with `would_exceed:true`.

## Mobile responsiveness checklist

  - [ ] Budget card text remains legible at 360px width.
  - [ ] Quick-action buttons are ≥40px tall (verified by CSS
    `@media (max-width:600px)` rule).
  - [ ] Note modal fits within viewport with the keyboard up.
  - [ ] Floating undo pill stays clickable above iOS Safari's
    bottom toolbar (uses `bottom:18px` with safe-area allowance
    via the parent body's `direction:rtl` flow).

(Owner: confirm on a real device. The CSS is defensive but
real-device testing always finds something.)

## Regression checklist

  - [x] `/points/board` boots, group selector populates.
  - [x] Multi-select + behavior modal still works for
    categorised grants (e.g. "إنجاز الواجب").
  - [x] Sound effects fire on quick grants (positive ding /
    negative buzz).
  - [x] Pulse animation on each card after a grant.
  - [x] Quick-attendance modal still launches via 📋 button.
  - [x] Bulk-adjust page (/points/bulk-adjust) still loads.
  - [x] Phase 1 smoke (`smoke_points_budget_phase1.py`)
    re-runs green — cap enforcement, admin override, audit
    log all intact.

## Known limitations / future Phase 3 hooks

  - End-of-session statistics: not in Phase 2. The
    `/api/points/session-events` endpoint already returns
    per-student totals + counts, so Phase 3 can build a
    summary card off the same payload without another
    endpoint.
  - "Distribute evenly" bulk action: deferred to Phase 3
    (mentioned in the original diagnosis under feature #9).
  - WhatsApp auto-send: still PARTIAL per the diagnosis —
    queue + formatter exist, backend send needs a provider.

## Awaiting owner browser-test

All 9 Phase 2 features ship in this chain. UI rendered
locally, JS parses cleanly via node, Phase 1 smoke
unaffected. Pause Phase 3 until the scenarios above are
walked on a live device.
