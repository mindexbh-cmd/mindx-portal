# Book folders — all remaining Phase-3 stubs wired

**Issue ticket:** After v2.9.1 fixed the "+ مجلد جديد" (C2)
stub, the owner found that clicking "+ ارفع أول كتاب" on
`/admin/books` still alerted `سيتم تفعيل هذا الزر في C4`.
Pattern confirmed: multiple Phase-3 buttons had been left as
placeholders. This change finds them all and wires them up.

**Resolution shipped in:**
- commit `743920a` — *fix(books): wire 'ارفع أول كتاب' / 'رفع كتب' to real handler*
- commit `a2a5083` — *test(books): all stubs gone from admin books*

**Safety tag:** `safety/book-folders-all-stubs-20260513-192817`
(pushed to origin before any edits).

---

## Comprehensive sweep

The investigation looked for every form of "placeholder
button" pattern in `ADMIN_BOOKS_HTML` (lines 88300–89500):

| Pattern | Hits | Action |
|---|---|---|
| `alert('سيتم تفعيل هذا الزر …')` | **1** | Fixed (this commit) |
| TODO / FIXME / "coming soon" / "قريباً" comments | 0 | — |
| `window.bk*` late-binding duplicates | **1** (`bkOpenMultiUpload`) | Fixed (this commit) |
| Other `alert(…)` calls | All real (error toasts, confirm dialogs) | — |

Total stubs in `ADMIN_BOOKS_HTML` after this change: **0**.

## Stub list (1 stub → 1 fix)

### Stub 1: `bkOpenMultiUpload` — C4 placeholder

- **Was:** `app.py:89187–89189`
  ```js
  window.bkOpenMultiUpload = function(){
    alert('سيتم تفعيل هذا الزر في C4');
  };
  ```
- **Calling buttons** (all three rendered correctly all along):
  - `app.py:88253` — `<button onclick="bkOpenMultiUpload()">📤 رفع كتب</button>` (toolbar)
  - `app.py:88907` — `'📤 رفع كتب'` (main-header, rendered dynamically inside `actsHtml`)
  - `app.py:88942` — `'+ ارفع أول كتاب'` (empty-state when a folder has no books)
- **Real handler** (already present, just shadowed by the stub):
  - `app.py:89053–89069` — sets the selected-folder context, hides the "inherit folder groups" checkbox at the root level, clears the file inputs, calls `bkUpRenderFiles()`, opens `bk-up-modal`.
- **Modal it opens:** `app.py:89197` (`<div class="modal-back" id="bk-up-modal">`).
- **API it reaches:** `POST /api/books/upload-multi` — defined at `app.py:85607`.
- **Bug class:** JS late-binding. Both lines bind to the same global key in the SAME `<script>` block (opens 88384, closes 89194). The second assignment wins at runtime, so the user saw the C4 alert instead of the upload modal.
- **Fix:** delete the 3-line stub. The real implementation at line 89053 takes effect. Same exact technique as the v2.9.1 fix for `bkCreateFolder`.

### Side observation: this is the same bug class as v2.9.1

The C2 stub for `bkCreateFolder` (v2.9.1) and the C4 stub for
`bkOpenMultiUpload` (this fix) are structurally identical:

- Real implementation written in full earlier in the script.
- A "see Phase N for activation" placeholder reassigned the
  same global key later in the same script.
- Both went unnoticed because the button-wiring `onclick=`
  was correct; only the function body got swapped.

The smoke test (commit `a2a5083`) now guards against this
class of bug — it asserts that NO `window.bk*` function name
appears twice in the served `<script>`. Any future C-phase
that adds a new stub-then-overwrite pair will be caught.

## What was NOT changed

Per the brief's "ZERO TOUCHING" rules:

- ❌ `POST /api/books/upload-multi` endpoint — untouched.
- ❌ `bk-up-modal` HTML — untouched.
- ❌ The folder sidebar + folder click handlers — untouched.
- ❌ The C2 fix from v2.9.1 (`bkCreateFolder`) — untouched.
- ❌ The 28 other `window.bk*` handlers (rename, delete,
  publish, move, edit, etc.) — untouched, all single-assignment.

## Verification

**Static checks** (commit `743920a`):
- ✓ `ast.parse(open('app.py').read())` — Python parse OK
- ✓ `grep -c "سيتم تفعيل هذا الزر" app.py` → **0**
- ✓ `bkOpenMultiUpload` now has exactly one assignment
- ✓ `bkCreateFolder` still has exactly one assignment (v2.9.1 fix intact)

**Boot + page test:**
- ✓ `import app` — 476 routes register
- ✓ `POST /login` admin/admin123 → 302 redirect
- ✓ `GET /admin/books` → 200, 60,308 bytes
- ✓ Served HTML contains: `📤 رفع كتب`, `+ ارفع أول كتاب`, `onclick="bkOpenMultiUpload()"`, `id="bk-up-modal"`, `/api/books/upload-multi`
- ✓ Served HTML does NOT contain `سيتم تفعيل هذا الزر`

**Smoke test** (`scripts/smoke_books_all_stubs.py`, commit `a2a5083`):
```
[1] zero 'سيتم تفعيل هذا الزر' stub strings in served HTML
[2] no duplicate window.bk* assignments (29 unique handlers,
    all single-assignment)
[3a] C2 fix intact — '+ مجلد جديد' wired to bkCreateFolder
[3b] C4 fix intact — '📤 رفع كتب' + '+ ارفع أول كتاب' wired
     to bkOpenMultiUpload (opens bk-up-modal, posts to
     /api/books/upload-multi)
[4] all 24 onclick='bkXxx()' attributes resolve to defined
    handlers

PASS — all ADMIN_BOOKS_HTML stubs are gone and no
late-binding duplicates remain.
```

## Owner browser-test scenarios

After hard-refresh (Ctrl+Shift+R) of `/admin/books`:

### Scenario A — Add folder (regression test for v2.9.1)

1. Click **+ مجلد جديد** in the right sidebar
2. Browser shows `prompt('اسم المجلد:')`
3. Type a folder name in Arabic (e.g. `ترم 1`), press OK
4. Toast `تم إنشاء المجلد ✓` appears
5. New folder shows up in the sidebar list

### Scenario B — Multi-file upload from empty folder

1. Click the new folder you just created
2. Main pane shows the empty-state message + **+ ارفع أول كتاب** button
3. Click **+ ارفع أول كتاب**
4. The `📤 رفع كتب متعددة` modal opens, scoped to the folder
5. "المجلد:" line shows the folder name
6. Drag/drop or browse-select up to 10 PDFs/docs (each ≤20MB)
7. Each file gets an editable title row
8. Click submit → batch uploads via POST `/api/books/upload-multi`
9. Toast confirms; modal closes; books appear in the folder

### Scenario C — Multi-file upload from toolbar (alternate entry)

1. With any folder selected, click **📤 رفع كتب** in the main-header toolbar
2. Same upload modal opens; same flow as Scenario B

### Scenario D — Upload at root level

1. Click `الجذر` (root) in the sidebar
2. Click **📤 رفع كتب**
3. Modal opens with "المجلد: الجذر (بدون مجلد)" in the header
4. "inherit folder groups" checkbox is hidden (root has no folder groups to inherit)
5. Upload proceeds; books land at root level (no `folder_id`)

### Failure modes to watch for

| Symptom | Likely cause | Fix |
|---|---|---|
| Stub alert still shows | Browser cache | Hard-refresh (Ctrl+Shift+R / Cmd+Shift+R) |
| Modal opens but submit fails with `غير مصرح` (403) | Logged-in user lacks `_can_manage_books` | Check role / capability allowlist on the user |
| Modal opens but files won't upload | Disk / `/var/data/books_v2` permissions, OR mime not in the accepted list (`pdf, doc, docx, jpg, png, webp`) | Check Render logs |
| Modal opens at root level but groups input shows confusion | Inherit-folder-groups checkbox should be HIDDEN at root — UI bug only if it's visible | Inspect `#bk-up-inherit-row` style attribute |

---

_Tagged as **v2.9.2**. The smoke test guards against this bug class for any future C5/C6/… Phase work._
