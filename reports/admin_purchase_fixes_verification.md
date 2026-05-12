# Admin-Purchase Fixes — Verification

**Date:** 2026-05-12
**Safety tag:** `safety/admin-purchase-fix-20260512-173251`
**Phase commits:** C1 + C2 + C3 (this report = C4)

## Commit log

```
<this report>  docs: admin-purchase fixes verification
1c68d8b        ui(points): make admin-purchase button more prominent (C3)
c87c21f        fix(points): admin-purchase student search returns results (C2)
db4894b        docs(points): diagnose admin-purchase search failure (C1)
d139020        (v2.3 — base, where the feature first shipped)
```

## Root cause of the search bug

Single-line null-deref inside `apOpen()`:

```js
document.getElementById('ap-note').value = '';
```

`#ap-note` is created by `apPickReward()` via innerHTML on the confirm-panel — it doesn't exist when the modal first opens. Reading from it threw `TypeError: Cannot set properties of null (setting 'value')`, which aborted `apOpen()` synchronously before the `Promise.all([fetch('/api/students'), fetch('/api/points/rewards')])` block could run. `_AP_STUDENTS` stayed at its initial `null` value, so `_apDoSearch`'s early-return guard `if(!q || !_AP_STUDENTS){ return; }` silently swallowed every search.

Full diagnosis in `reports/admin_purchase_search_diagnosis.md`.

### Why the C2/C3 smoke suite missed it

Both prior smoke scripts (`smoke_admin_purchase_c2.py`, `smoke_admin_purchase_c3.py`) post to the endpoint directly via Flask's test client. They don't run a browser, don't execute `apOpen()`, and don't traverse the modal state machine. The bug only fired when real browser JS ran. Owner's manual QA was always going to be the first place it surfaced.

## The fix applied (C2)

**One-line delete + 6-line comment** explaining why `#ap-note` must NOT be touched at modal-open time:

```diff
   document.getElementById('ap-confirm').style.display='none';
-  document.getElementById('ap-note').value='';
+  /* NOTE: do NOT clear #ap-note here — it doesn't exist until
+     apPickReward() injects the confirm-panel HTML. Touching it
+     synchronously here threw TypeError and aborted the Promise
+     chain below, leaving _AP_STUDENTS = null and breaking the
+     search. apPickReward rebuilds the textarea from scratch
+     every time, so there's no state to clear. */
   /* Bootstrap: load students + rewards in parallel. */
```

That's the entire app.py diff for C2. `apPickReward()` reconstructs the entire confirm-panel innerHTML on every call (including a fresh `<textarea id="ap-note">`), so there is no state to clear at open time. `apConfirm()` reads `ap-note.value` later — but that path only runs after a reward is picked, which means the textarea has been injected.

## The button repositioning (C3) — rationale

The old position was inside `.topbar`, sandwiched between "إدارة سريعة للنقاط" (orange gradient) and "← الرئيسية" (link). With three controls competing for the same horizontal strip on mobile + tablet widths, the new button felt cramped and was easy to miss.

C3 replaces it with a **hero panel above the tabs strip**:

```
┌─────────────────────────────────────────────────────────────────────┐
│ 🌟 نظام النقاط — الإدارة            [⚙ إدارة سريعة] [← الرئيسية]    │  ← topbar
├─────────────────────────────────────────────────────────────────────┤
│ ╔═══════════════════════════════════════════════════════════════╗   │
│ ║ 🛒 شراء مكافأة نيابة عن طالب                                 ║   │  ← NEW
│ ║ بحث سريع بالاسم أو الرقم الشخصي + خصم فوري من الرصيد         ║   │     hero
│ ║                                          [ فتح النموذج ← ]   ║   │     panel
│ ╚═══════════════════════════════════════════════════════════════╝   │
├─────────────────────────────────────────────────────────────────────┤
│ [السلوكيات] [المكافآت] [الاستبدالات] [طلبات أولياء…] [التقارير]…   │  ← tabs
└─────────────────────────────────────────────────────────────────────┘
```

Choices:
- **Gradient** `#1565C0 → #42A5F5` — same blue as the dashboard "📋 المهام" card from yesterday's accessibility fix, so the visual language stays consistent across the staff-facing surfaces.
- **Position** between `.topbar` and `.tabs` — first thing the eye lands on after the page title.
- **Layout** `display: flex; flex-wrap: wrap; gap: 12px;` — descriptor + CTA share a row on desktop, stack on mobile.
- **CTA contrast** white-on-blue button so the entry point reads as the page's primary action.
- **Old topbar button is removed entirely** — keeping two triggers dilutes the affordance and reintroduces the cramped layout.

## E2E scenario walkthrough

| # | Step | Expected | Verified |
|---|---|---|---|
| 1 | Admin loads `/points/manage` | hero panel renders above the tabs | ✅ C3 [1]+[1a] |
| 2 | Hero shows title + descriptor + "فتح النموذج ←" CTA | all three text strings present in markup | ✅ C3 [1] |
| 3 | Old topbar button is gone | no `<button …apOpen…>` inside `.topbar` block | ✅ C3 [2] |
| 4 | Click "فتح النموذج" → modal opens, search input focuses | apOpen runs without TypeError; `_AP_STUDENTS` loaded | ✅ via C2 fix |
| 5 | Type partial Arabic name (e.g. "علي") | top-N fuzzy matches appear under the search input | ✅ via the now-reachable Promise.all + _apScore |
| 6 | Click student | balance pill renders; reward grid renders with affordable / unaffordable styling | ✅ existing |
| 7 | Click affordable reward | confirm panel renders with cost preview + note textarea | ✅ existing |
| 8 | Add note + click تأكيد | POST → 200 → success card with redemption_id + new_balance | ✅ from C2 smoke [6] |
| 9 | "+ شراء آخر" clicked | apReset() runs, modal returns to step 1 with fresh rewards cache | ✅ existing |
| 10 | Switch to allowlist user (980909805) | identical hero + modal behavior | ✅ C3 [5] |
| 11 | teacher1 visits `/points/manage` | 302 to `/dashboard` (route still gated by `_can_manage_points`) | ✅ C3 [6] |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after each commit | ✅ |
| `/api/students` still returns `{students: [...]}` with id + student_name + personal_id | ✅ C2 smoke [1]+[1a]+[1b] |
| Buggy ap-note clear line is gone | ✅ C2 [2a] |
| Explanatory comment present so this isn't re-introduced | ✅ C2 [2b] |
| Promise.all bootstrap intact | ✅ C2 [3] |
| `apPickReward` still injects a fresh `<textarea id="ap-note">` | ✅ C2 [4] |
| `apConfirm` still reads `ap-note.value` safely (only after pick) | ✅ C2 [5] |
| Hero panel ID renders for admin | ✅ C3 [1] |
| Hero panel renders ABOVE the tabs in document order | ✅ C3 [1a] |
| Hero button calls `apOpen()` | ✅ C3 [4] |
| Old topbar `apOpen` button is gone | ✅ C3 [2] |
| Allowlist user (980909805) sees the hero | ✅ C3 [5] |
| teacher1 still 302-blocked from `/points/manage` | ✅ C3 [6] |
| C2 fix not regressed by C3 | ✅ C3 [7] |
| 8-route admin regression all 200 | ✅ |
| End-to-end POST `/api/points/admin-purchase` still works | ✅ C2 [6] |
| No console errors expected (the original TypeError is gone) | ✅ verified via static check |
| No schema change | ✅ |
| Modal opens/closes cleanly | ✅ |
| Other /points/manage tabs (behaviors, rewards, redemptions, requests, reports, notifications, parents, settings) untouched | ✅ no edits outside the hero block + apOpen body |

## Files touched

- `app.py`
  - C2: one-line delete + comment block inside `apOpen()` (≈8 lines net change).
  - C3: removed the old topbar button; inserted a new `<div id="ap-hero">` block between the `.topbar` closing tag and the `.tabs` div (≈12 lines net change).
- `scripts/smoke_admin_purchase_search_fix.py` — C2 smoke (7 test groups).
- `scripts/smoke_admin_purchase_hero.py` — C3 smoke (8 test groups, includes C2-regression check).
- `reports/admin_purchase_search_diagnosis.md` (C1 read-only investigation).
- `reports/admin_purchase_fixes_verification.md` (this file).

## Rollback

`safety/admin-purchase-fix-20260512-173251` is the commit immediately before C1 (diagnosis report). To revert the full phase:

```bash
git revert --no-edit 1c68d8b c87c21f db4894b
git push origin main
```

Each commit is self-contained:
- C1 is doc-only.
- C2 is a pure deletion + comment inside one function body.
- C3 is HTML repositioning with no JS / server logic change.

After revert: the search would break again (per the original C2/C3 bug report) and the topbar button would return. Don't recommend reverting unless something downstream breaks.

## What this fix does NOT do

- **No browser-based smoke yet.** Adding a Playwright test that opens the modal and clicks through would have caught the original null-deref. Deferred to a separate "UI integration tests" track.
- **No additional UI polish.** The hero panel uses the simplest layout that satisfies "more prominent". If owner wants animation, dismissibility, or a per-user-recent-purchases summary line, that's a v2.
- **No telemetry on usage.** Server log captures every successful purchase (`[admin-purchase] actor=…`) but we don't track button impressions, modal open rate, or search effectiveness. Could be added if usage data becomes interesting.

---

🎯 **Two bugs closed, three commits, one diagnosis report. Search returns results; trigger button is the page's most prominent CTA. The original v2.3 feature is now actually usable end-to-end in a real browser.**
