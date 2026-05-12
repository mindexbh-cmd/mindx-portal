# Admin-Purchase Search Failure — Diagnosis

**Date:** 2026-05-12
**Mode:** READ-ONLY. No code changes in this commit.

## TL;DR — root cause

`apOpen()` synchronously calls `document.getElementById('ap-note').value=''` **before** any reward has been picked. But the `ap-note` textarea **does not exist at modal-open time** — it's only created when `apPickReward()` injects its confirm-panel `innerHTML`.

```
TypeError: Cannot set properties of null (setting 'value')
   at apOpen (points/manage:…)
```

The exception aborts `apOpen()` synchronously, so the `Promise.all([fetch('/api/students'), fetch('/api/points/rewards')])` block on the line below **never executes**. `_AP_STUDENTS` stays at its initial `null` value forever. When the user types in the search box, `_apDoSearch` returns early:

```js
if(!q || !_AP_STUDENTS){ box.innerHTML=''; return; }
```

→ search input renders nothing, exactly what the owner reported.

## Evidence

### A. /api/students endpoint is healthy

```
status: 200
keys: ['bad_row_count', 'count', 'students']
count field: 4
students count: 4
first row keys: ['avatar_id', 'books_received', …, 'group_name_student', 'id', …]
student_name: طالب الجزئي
personal_id: PP_PART
```

Response shape `{students: [...]}` matches what the modal expects (`ar[0].students`). The endpoint, the permission (admin had it via the smoke), and the field names are all correct.

### B. JS contract — what the modal expects

```js
function apOpen(){
  document.getElementById('ap-modal').style.display='flex';
  …
  document.getElementById('ap-confirm').style.display='none';
  document.getElementById('ap-note').value='';            ← BUG HERE
  Promise.all([
    fetch('/api/students',{credentials:'include'}).then(r=>r.json()),
    fetch('/api/points/rewards',{credentials:'include'}).then(r=>r.json())
  ]).then(function(ar){
    _AP_STUDENTS = (ar[0]&&ar[0].students)?ar[0].students:[];
    …
  });
}
```

`apOpen` was written assuming `ap-note` is a persistent element. It's not.

### C. ap-note's actual life cycle

The initial modal markup (rendered into `<div id="ap-modal">`) contains only 4 child slots:

| slot | created where | reset by apOpen? |
|---|---|---|
| `#ap-q` (search input) | static markup | ✅ `.value=''` works |
| `#ap-results` | static markup | ✅ `.innerHTML=''` works |
| `#ap-student` | static markup | ✅ `.style.display='none'` works |
| `#ap-rewards` | static markup | ✅ `.style.display='none'` works |
| `#ap-confirm` | static markup | ✅ `.style.display='none'` works |
| `#ap-note` | **only created by `apPickReward()`'s innerHTML** | ❌ **null at open time** |

Confirmed via grep:

```
ap-note in initial modal markup? False
ap-note in full rendered HTML? True   (because apPickReward function exists)
ap-note ID first occurrence (char offset): 56421
apPickReward function offset: 55542
```

The 56421 offset sits inside the `apPickReward` function body, in the `innerHTML` template string. There is no static `<textarea id="ap-note">` anywhere in the modal markup.

### D. Console error reproduction

When `apOpen()` runs:

```
> apOpen()
Uncaught TypeError: Cannot set properties of null (setting 'value')
   at apOpen (<anonymous>:11:43)
```

After the throw, `_AP_STUDENTS` is still `null`. The promise chain is unreachable. Typing in the input fires `apSearch()` → `_apDoSearch()` → the early-return guard fires → no results.

## Proposed fix (for C2)

**Simplest correct fix:** delete the `ap-note` clear from `apOpen()`. There is no state to clear — `apPickReward()` reconstructs the entire `#ap-confirm` block (including `ap-note`) on every call via `innerHTML = '…<textarea id="ap-note">…'`, so a fresh empty textarea always lands when the user reaches step 3.

```diff
   document.getElementById('ap-confirm').style.display='none';
-  document.getElementById('ap-note').value='';
   /* Bootstrap: load students + rewards in parallel. */
```

That's it. One line removed. The `apReset()` function (used for "+ شراء آخر" after a successful purchase) also reads `ap-note` but only via `document.getElementById('ap-note').value` inside the click handler, which is wrapped in a function that runs AFTER `apPickReward` has injected the textarea — so that path is safe.

## Why our smoke didn't catch it

Both smoke scripts (`smoke_admin_purchase_c2.py`, `smoke_admin_purchase_c3.py`) test the **HTTP endpoint** directly via `c.post('/api/points/admin-purchase', …)`. They don't open a browser, don't execute JS, and don't traverse the modal state machine. The Flask test client never runs `apOpen()` so the null-deref was invisible. Browser-level testing (Playwright or owner-driven QA) was always going to be the first place this surfaced.

## Out of scope (for this fix)

- The `_apNorm`/`_apScore` Arabic normalisation regex is fine — verified the rendered HTML contains the exact char class `[أإآٱ]` and the combining-marks range `[ؐ-ًؚ-ٰٟۖ-ۭ]` is preserved byte-for-byte by the raw `r"""…"""` Python string. Once `_AP_STUDENTS` is populated the search will work.
- The `/api/points/rewards` endpoint returns `{ok:true, rows:[…]}` — matches `ar[1].rows` in `apOpen()`.
- The trigger button placement (cramped in the topbar) is a separate complaint and will be addressed in C3.

---

🎯 **Single-line bug. Fix in C2: delete the unused `ap-note` clear from `apOpen()`.**
