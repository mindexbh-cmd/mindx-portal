# Phase 3 — Stats + Bulk + Polish — Verification

**Owner has not yet browser-tested Phase 1 or 2.** This
verification doc consolidates the entire Phase 1+2+3 feature
so the owner can walk it end-to-end in one session.

**Safety tag:** `safety/points-budget-phase3-20260513-154619`
(created before C1).

**Strict verification protocol followed:** after every commit,
`python -c "import app"` + `smoke_points_budget_phase1.py` +
`smoke_points_phase2_js.py` all passed before the next commit
was made.

## Commit chain (on `main`)

| Hash       | Subject                                                  |
|------------|----------------------------------------------------------|
| `045f443`  | feat(points): /api/points/session-stats endpoint         |
| `a29133f`  | feat(points-ui): session stats modal                     |
| `b4b43ce`  | feat(points): /api/points/bulk-grant endpoint            |
| `487fbf1`  | feat(points-ui): distribute evenly button                |
| `4e7d91d`  | ui(points): polish animations + mobile refinements       |
| `f443541`  | test(points): full integration smoke Phase 1+2+3         |
| `4fac1f5`  | test(points): Phase 3 JS validation                      |
| (this PR)  | docs: Phase 3 verification                               |

## What's NEW in Phase 3

### 1. Session-stats endpoint (C1)

`GET /api/points/session-stats?group=<name>&date=<YYYY-MM-DD>`

Returns the full end-of-session roll-up in one fetch:
budget triple, active/awarded/skipped counts, top 3 students,
behaviour breakdown, and undo count.

### 2. Stats modal UI (C2)

Tap **📊 إحصائيات** on the budget bar header → modal with:

- 6-number summary grid (budget / used / remaining / percent /
  awarded students / skipped students)
- 🏆 Top 3 students with medal icons (🥇 🥈 🥉) and signed totals
- 📚 Behaviour breakdown table (count + signed total per row,
  positive green, negative red)
- ↩ Undo-usage line (only shown when count > 0)

### 3. Bulk-grant endpoint (C3)

`POST /api/points/bulk-grant`

Awards the same signed amount to every present student in a
group. Same cap, same absent rules, same admin bypass + audit
trail as `/api/points/grant`. Returns `skipped_absent[]` so
the UI can name who didn't get points.

### 4. Distribute-evenly UI (C4)

Tap **⚖️ توزيع عادل** on the budget bar header → modal with:

- Amount picker (+1 / +2 / +5)
- Live preview: `4 طلاب حاضرين × 2 = 8 نقطة من الرصيد`
- Preview flips red when the cost would exceed budget
- One submit fires `/api/points/bulk-grant`; success integrates
  with the existing undo pill so the bulk action can be
  reversed in one click.

### 5. UI polish (C5)

- Budget bar is sticky on desktop (`>600px`); stays inline on
  mobile so student-card real estate is preserved.
- Bar fill uses `cubic-bezier(.22,.78,.31,1)` for a softer
  width animation; bar-color crossfade extended to 350ms.
- Per-student chip "bumps" (scale 1 → 1.22 → 1) only when the
  rendered total actually changed (no spam on first paint).
- Extra-tight `<480px` breakpoint (thinner bar, tighter
  quick-action row gaps).
- Header action buttons get a desktop-only hover lift via
  `@media (hover:hover) and (pointer:fine)` — no stuck hover
  state on touch devices.

## Owner browser-test scenarios (single comprehensive pass)

### Setup

  1. Open `/points/board/<a real group>` as a **teacher**.
  2. Take attendance for the group first via 📋 button so the
     budget reflects actual attendees. (If you skip this, the
     budget falls back to roster size — also fine.)

### Phase 1 — cap enforcement

  1. **Budget bar appears at top** with green color, showing
     `0 / N نقطة • متبقي N`.
  2. Click **+2** on any student card → chip `+2 في الحصة`
     appears (with bump animation), bar advances, balance
     updates.
  3. Keep awarding until you cross 80% → expect an **orange
     toast** "تنبيه: متبقي N نقطة فقط" and the bar turns
     orange.
  4. Push past 100% → **red toast** "انتهى رصيد الحصة..." +
     bar turns red + quick buttons gray out.
  5. **Try +1 anywhere now** → it's disabled (gray).
  6. **Log in as admin**, retry → admin succeeds despite cap
     (Phase 1 bypass).

### Phase 2 — quick actions, undo, absent

  7. Click **📝** next to any student → note modal opens,
     focus is in the textarea, char counter at `0 / 200`,
     `+2` pre-selected. Type "ممتاز اليوم", pick +5, click
     **حفظ ومنح**. Toast confirms, modal closes.
  8. Within 10s of any award, look bottom-left for the
     **↩ تراجع pill**. Click it. Toast says "✅ تم التراجع",
     the chip retreats, the bar shrinks.
  9. In a second browser tab, open **/teacher/attendance**
     and mark one student `غائب` today. Refresh the board.
  10. ✅ That student's card is **grayscale** with **❌ غائب**
      pill; quick buttons hidden.
  11. As admin, manually `POST /api/points/grant` for that
      student → expect **HTTP 400** with the structured
      `absent` payload (`{absent: [{student_id, name}, …]}`).

### Phase 3 — stats + bulk

  12. Click **📊 إحصائيات** on the budget bar.
      ✅ Modal opens with the date in the header, six big
      numbers, 🥇🥈🥉 list of top earners, behaviour table
      below.
  13. Close the stats modal (X or ESC).
  14. Click **⚖️ توزيع عادل**.
      ✅ Compact modal: amount buttons, preview line.
  15. Pick `+1`, click **تنفيذ**.
      ✅ Toast `✅ تم توزيع +1 على N طالب` (N = present count).
      ✅ The previously-absent student is **skipped** — the
      toast includes "تم تخطي 1 غائب".
      ✅ Budget bar updates; every present student's chip bumps
      by +1.
  16. Click the **↩ تراجع** pill within 10s.
      ✅ All bulk awards are undone (one DELETE per event id).

### Mobile responsiveness

  17. Resize browser to 360 × 800 (DevTools → toggle device).
      ✅ Budget bar collapses to a single-column layout, text
      stays legible. Quick-action buttons remain ≥40px tall.
      ✅ Stats modal's 6-number grid collapses from 3-up to
      2-up.
      ✅ Distribute modal stays usable; preview line wraps
      cleanly.

## What does NOT change (regression guard)

- `/api/points/session-budget` response shape — **unchanged**.
- `/api/points/grant` signature — **unchanged**.
- Phase 1 cap-check ordering inside `/api/points/grant` —
  **unchanged**.
- Admin override + audit_log writes from Phase 1 C5 — preserved
  byte-for-byte; the bulk endpoint mirrors the convention with
  `details.via='bulk-grant'`.
- Behavior catalog + seeded point values — **untouched**.
- Multi-select toolbar + behavior-category modal — still
  works for categorised grants (e.g. "إنجاز الواجب").
- Sound effects, pulse animation, level/avatar chips —
  unchanged.

## Smoke status

  - `smoke_points_budget_phase1.py` — 10/10 scenarios green.
  - `smoke_points_phase2_js.py` — 34 Phase 2+3 markers
    present, 8 regression markers preserved, every script
    block parses via node Function.
  - `smoke_points_integration.py` — 12/12 end-to-end
    scenarios green (Phase 1 cap, Phase 2 absent + undo,
    Phase 3 stats + bulk-grant + bulk-absent).

## Tag

After this commit:
  `git tag -a v2.9-phase3-pts HEAD -m "Phase 3 — Stats + Bulk + Polish"`

## Deployment

1. `git push origin main` + `git push origin v2.9-phase3-pts`.
2. Render auto-deploys; no new migrations
   (`points_session_date_v1` from Phase 1 already ran on prod).
3. Owner walks the 17 scenarios above on prod.

## Known limitations / Phase 4 hooks

- **WhatsApp auto-send** — still PARTIAL per the original
  diagnosis. `point_notifications` queue accumulates pending
  rows; no backend send API yet.
- **Bulk-grant -1 deduction** — UI currently shows only
  `+1 / +2 / +5`. Easy to add `-1` later if owner wants a
  group-wide deduction.
- **Stats modal export** — no "send to parent" or "share"
  button. Phase 4 candidate.

## Awaiting owner browser-test

Phase 1+2+3 ship together for the first comprehensive walk-
through. The 17 scenarios above cover every code path. Pause
Phase 4 (WhatsApp) until the owner confirms the budget feature
behaves as expected on a real device.
