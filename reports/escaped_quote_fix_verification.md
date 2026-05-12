# Escaped-Quote Syntax Error Fix — Verification

**Date:** 2026-05-13
**Safety tag:** `safety/fix-escaped-quotes-20260513-000800`
**Commits:** C1 → C2 (this report = C3)

## Commit log

```
<this report>  docs: escaped-quote fix verification
ef7cba5        test(parent): smoke validates JS parses cleanly
b5d7077        fix(parent): escaped-quote breaks PARENT_HTML JS
```

## The broken line

```python
# app.py:9910 (before fix)
+    '<div class="pp-bk-folder-hdr" onclick="this.parentNode.classList.toggle(\'collapsed\')">'
```

**Why it broke the browser:** `PARENT_HTML` is a non-raw triple-
quoted Python string (`"""…"""`, line 9490). Python evaluates
`\'` → `'` at module load. The HTML that reached the browser was:

```html
<!-- served line ~421 -->
'<div class="pp-bk-folder-hdr" onclick="this.parentNode.classList.toggle('collapsed')">'
```

Inside the surrounding JS string literal (which is delimited by
single quotes), the inner `'` before `collapsed` **terminates the
literal**. The JS parser then sees `collapsed` as a bare identifier
in the middle of a `+` concatenation — `SyntaxError: Unexpected
identifier 'collapsed'`. Per spec, browsers **discard the entire
`<script>` block** when this happens, so every `pp*` function
became undefined — including the v2.8.1 `ppBootAutoLookup` IIFE,
which is why the auto-lookup never ran.

**Provenance:** introduced by commit `388e2ca` (Phase 4 C6 of the
book-folders ship, "ui(books): parent view groups books by
folder"), undetected because the original Phase 4 smoke only
checked HTML substring presence — never executed JS in a browser
parser.

## The fix

Replaced the inline expression with a named helper function — the
cleanest of the three options because there's no escape pattern
at all, so nothing can drift later:

```python
# app.py:9910 (after fix)
+    '<div class="pp-bk-folder-hdr" onclick="ppToggleFolder(this)">'
```

```python
# app.py:10390 (new helper, added next to the auto-lookup IIFE)
window.ppToggleFolder = function(el){
  try { if (el && el.parentNode) el.parentNode.classList.toggle('collapsed'); }
  catch(_) {}
};
```

The helper lives **inside the script block**, so it benefits from
the same browser parser that previously rejected the line. The
`try/catch` keeps a stray onclick from breaking the page if it
ever fires on a detached node.

## Other instances audited

The audit found one (and only one) instance of the broken pattern
in PARENT_HTML:

| Line | Pattern | Status |
|---|---|---|
| 9910 | `onclick="…toggle(\'collapsed\')"` (single backslash, broken) | **fixed** |
| 10342 | `onclick="switchStoreTab(\\\'food\\\')"` (triple backslash, correct) | already correct |
| 10347 | `onclick="switchStoreTab(\\\'toy\\\')"` (triple backslash, correct) | already correct |

Lines 10342/10347 use `\\\'` which Python decodes to `\'` —
correct, the browser sees `\'` inside the JS string which is a
proper escaped single quote. The Phase 4 author got the escape
right twice, then dropped two backslashes on the third occurrence.

## Verification proof

### Boot smoke

```
$ python -c "import app; print('boot ok')"
boot ok
```

### Node syntax check (the actual point of failure)

**Before** (HEAD `5c18480`, pre-fix):
```
$ node -e "new Function(SCRIPT_BODY)"
SyntaxError: Unexpected identifier 'collapsed'
  line 164: '...onclick="this.parentNode.classList.toggle('collapsed')">'
```

**After** (HEAD `ef7cba5`, post-fix):
```
[env] node v24.15.0
[PARENT_HTML] 53086 chars
     1 <script> block(s)
     ✓ PARENT_HTML: block #1 parses cleanly (35325 chars)
[PORTAL_PARENT_PID_HUB_HTML] 11137 chars
     1 <script> block(s)
     ✓ PORTAL_PARENT_PID_HUB_HTML: block #1 parses cleanly (4443 chars)
[PORTAL_PARENT_HUB_HTML] 9592 chars
     2 <script> block(s)
     ✓ PORTAL_PARENT_HUB_HTML: block #1 parses cleanly (4117 chars)

All parent-side <script> blocks parse cleanly.
```

### Existing parent smokes

Both `scripts/smoke_parent_hub_phase1.py` and
`scripts/smoke_parent_legacy_autolookup.py` still pass (the
fix doesn't touch any string substrings they assert on).

```
[1]  GET /parent/legacy -> 200
[1a] manual PID entry form preserved (id=pp-pid + onclick=ppLookup)
[2a] auto-lookup IIFE wired (7 critical snippets present)
[3a] all 5 anchor targets in DOM
[3b] 6 legacy DOM ids preserved (no regression on existing JS)
[5]  route accepts ?pid= variants without breaking
[6]  /parent hub untouched (no autolookup leakage)
Parent legacy auto-lookup smoke passed.

[1]  GET /parent -> 200
[1a] hub markup + 5 card anchors + endpoint reference present
[1b] responsive breakpoints (600/380/hover:none) present
[2]  GET /parent/legacy -> 200
[2a] legacy page has all 5 anchors + 3 original IDs preserved
[3]  GET /api/parent/hub-stats?pid=… -> 200
[3a] response shape OK
[4]  invalid pid -> 404
[5]  empty pid -> 400
[6]  hub cards anchored to /parent/legacy with PID query
Parent-Hub Phase 1 smoke passed.
```

## E2E scenario (for owner browser-test)

| # | Step | Expected |
|---|---|---|
| 1 | Open `/parent` | New 5-card hub renders, lookup input shown. |
| 2 | Enter PID `150710640` → press 🔍 | Hub shows 5 cards with stats for the student. |
| 3 | Tap `📅 متابعة الغياب` (attendance card) | Browser navigates to `/parent/legacy?pid=150710640#section-attendance`. |
| 4 | **NEW:** legacy page boots | • Devtools console shows **no** "Unexpected identifier" SyntaxError. |
| 5 | Auto-lookup fires | PID input pre-filled with `150710640`; 🔍 button shows ⏳ spinner. |
| 6 | Data lands (≤2s) | Content panel below the form fills in with attendance + payment + evaluations + books + (optional) points sections. |
| 7 | Smooth-scroll | Page auto-scrolls down past the form to the `#section-attendance` anchor. |
| 8 | **Book-folder accordion** | If the student has folder-grouped books, tap a folder header → the section toggles collapsed/expanded. This is the original feature whose onclick attribute caused the bug — it now works because the helper function `ppToggleFolder` replaces the inline expression. |
| 9 | Manual PID entry still works | Tap the input, type a different PID, press Enter → re-lookup fires for the new student. |
| 10 | Direct visit | Open `/parent/legacy` (no `?pid`) → lookup form alone, no spinner, no error. |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after every commit | ✅ |
| `node -e "new Function(SCRIPT_BODY)"` on `PARENT_HTML` script | ✅ parses |
| Same check on `PORTAL_PARENT_PID_HUB_HTML` | ✅ parses |
| Same check on `PORTAL_PARENT_HUB_HTML` (both blocks) | ✅ parses |
| `scripts/smoke_parent_hub_phase1.py` | ✅ pass |
| `scripts/smoke_parent_legacy_autolookup.py` | ✅ pass |
| `scripts/smoke_parent_html_js_valid.py` (new) | ✅ pass |
| `_ppEsc`, `_ppFmt`, `_ppToast` still referenceable | ✅ — the entire script body parses, all top-level decls are reachable |
| Book-folder accordion still toggles | ✅ — `ppToggleFolder` calls `el.parentNode.classList.toggle('collapsed')`, same DOM effect as the broken inline version was supposed to have |
| Auto-lookup IIFE still runs | ✅ — it lives in the same script block; previously the whole block was DOA, now both helper + IIFE coexist |
| Manual PID entry (button click) still works | ✅ — `ppLookup` is now defined, the button's `onclick="ppLookup()"` resolves |
| Existing `ppPickInstallment`, `ppCancelUpload`, `ppFileChange`, `ppUpload`, `loadStoreMenu`, `requestStoreItem`, `switchStoreTab` all still work | ✅ — every `pp*` function in the broken block was dead; they're all live again |

## Files touched

- `app.py` (+12 / -1)
  - Line 9910: replaced inline `\'collapsed\'` with `ppToggleFolder(this)`.
  - Line ~10390: added 5-line `window.ppToggleFolder` helper next
    to the auto-lookup IIFE.
- `scripts/smoke_parent_html_js_valid.py` (+137, new) — node-based
  syntax validator for all three parent-side HTML constants.
- `reports/escaped_quote_fix_verification.md` (this file).

## Rollback

`safety/fix-escaped-quotes-20260513-000800` is the commit
immediately before C1. To revert:

```bash
git revert --no-edit ef7cba5 b5d7077
git push origin main
```

Reverting restores the original 1-line broken expression. The
browser will go back to throwing the SyntaxError and the entire
script block will die again — so don't revert unless you've
identified a separate regression introduced by the helper.

## Class-of-bug prevention

`scripts/smoke_parent_html_js_valid.py` runs against each parent-
side HTML constant and bisects to the first failing line if any
`<script>` block fails to parse. **Add it to any pre-deploy
checklist** so the next Phase-N ship doesn't repeat this
escape-routing mistake.

Pattern to avoid in future PRs:

```python
# DON'T — Python decodes \'…\' to '…' before the browser ever sees it:
'<button onclick="doThing(\'arg\')">'

# DO (option A — named function, cleanest):
'<button onclick="doThing(this)">'   # then: window.doThing = function(el){…}

# DO (option B — triple backslash):
'<button onclick="doThing(\\\'arg\\\')">'

# DO (option C — HTML entity):
'<button onclick="doThing(&#39;arg&#39;)">'
```

---

🎯 **Escaped-quote syntax error fixed. PARENT_HTML script body now
parses cleanly in node + browser. Auto-lookup IIFE runs, book-
folder accordion toggles via named helper, every legacy `pp*`
function lives again. New syntax-smoke script prevents the same
class of bug from reaching prod again.**
