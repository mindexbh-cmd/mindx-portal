# v2.8.5 — `/parent/evaluations/view` back button preserves PID

## Symptom

Owner reported: tapping **رجوع** on the monthly evaluations page
(`/parent/evaluations/view?pid=<X>`) returned the parent to the
**empty** PID lookup form at `/parent`, forcing them to retype
the same PID they were just viewing.

Same class of regression as the v2.8.4 fix (commit `198216b`),
but on a different page — that fix touched `PARENT_HTML` and
the hub; the evaluations page (`PARENT_EVALUATIONS_HTML`) was
not in scope at the time.

## Root cause

`PARENT_EVALUATIONS_HTML` (`app.py` line 85404) shipped a static
back anchor:

```html
<a class="pe-back" href="/parent">← رجوع</a>
```

The `?pid=` query was never threaded through, so navigation
landed on the lookup form. The hub's `phBootFromUrl` IIFE (from
v2.8.4) already auto-rehydrates from `?pid=`, so the back link
just needed to send them there.

## Fix

Two minimal edits inside `PARENT_EVALUATIONS_HTML`:

### 1. Add an id to the back anchor (line 85524)

```diff
-  <a class="pe-back" href="/parent">← رجوع</a>
+  <a class="pe-back" id="pe-back-link" href="/parent">← رجوع</a>
```

### 2. Thread server-injected PID into the href (line ~85536, inside the existing IIFE)

```diff
 (function(){
   var PID = __PID_JSON__;
+  /* v2.8.5 — back button preserves PID so the parent returns to
+     the populated hub instead of the empty PID lookup form. The
+     hub's phBootFromUrl IIFE reads ?pid= and auto-rehydrates. */
+  try {
+    var _peBack = document.getElementById('pe-back-link');
+    if (_peBack && PID) {
+      _peBack.href = '/parent?pid=' + encodeURIComponent(PID);
+    }
+  } catch(_) {}
   var AXES = [
```

Total: **10 lines added, 1 deleted** in `app.py`.

The static `href="/parent"` is retained as the no-JS fallback —
if a browser had JS disabled the parent would still land on the
hub, just without auto-rehydration (this matches the v2.8.4
behavior).

## What was NOT touched

- `parent_evaluations_page()` Flask route — unchanged. PID
  validation (`_eval_pid_resolve_student`) still 403s bogus PIDs.
- `/parent/evaluations` JSON endpoint — unchanged.
- Empty-state HTML (`pe-empty-card`) — unchanged.
- Any evaluation data fetching / rendering — unchanged.

## E2E scenario (owner browser test)

1. Open `/parent`.
2. Enter a known PID → hub renders with the student's cards.
3. Click **التقييمات** card → land on
   `/parent/evaluations/view?pid=<PID>`.
4. Click **← رجوع**.
5. ✅ Land on `/parent?pid=<PID>` — hub auto-rehydrates via
   `phBootFromUrl`, the same populated hub appears, **no PID
   re-entry required**.

## Smoke (`scripts/smoke_parent_evaluations_back.py`)

```
[1] GET /parent/evaluations/view?pid=200603680 -> 200
[2] back anchor carries id='pe-back-link'
[3] back-link href is rewritten to /parent?pid=<encoded PID>
[4] static href fallback (/parent) preserved for no-JS path
[5] GET /parent/evaluations/view?pid=<bogus> -> 403
[6] template shell (loader + content slot + PID var) intact

v2.8.5 evaluations back-button smoke passed.
```

The smoke pulls a real `personal_id` from local `mindx.db` so
the validator passes without hardcoding a PID.

## Safety

- Safety tag created pre-change:
  `safety/evaluations-back-button-20260513-135448`.
- Three atomic commits on `main`:
  - `f1657d6` fix(parent): evaluations back button preserves PID
  - `a73be07` test(parent): evaluations back button smoke
  - (this commit) docs: evaluations back button verification
- App boots; Python syntax check (`ast.parse`) clean; smoke
  green; `/parent/evaluations/view` still renders 200 for a
  valid PID and 403 for a bogus one.
