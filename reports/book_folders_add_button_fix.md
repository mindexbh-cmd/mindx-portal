# Book folders — "+ مجلد جديد" add-button fix verification

**Issue ticket:** Clicking the "+ مجلد جديد" button on
`/admin/books` shows the alert `سيتم تفعيل هذا الزر في C2`
instead of opening the create-folder flow.

**Resolution shipped in:** commit `6e4a4cd` —
*fix(books): wire 'add folder' button to create modal*

**Safety tag:** `safety/book-folders-add-btn-20260513-183147`
(pushed to origin before any edits)

---

## Root cause

The button onclick **was** wired correctly all along:

```
app.py:88242–88244
<button type="button" class="bk-add-folder" onclick="bkCreateFolder()">
  + مجلد جديد
</button>
```

And the real `bkCreateFolder` implementation **was** present
at line 88718–88734 — a complete handler that prompts for a
folder name, POSTs `{name_ar}` to `/api/book-folders`,
selects the new folder, and refreshes the sidebar.

But ~470 lines **later in the same `<script>` block**, a
placeholder re-assigned the same global:

```
app.py:89182–89184 (BEFORE FIX)
window.bkCreateFolder = function(){
  alert('سيتم تفعيل هذا الزر في C2');
};
```

Plain JavaScript late-binding — both lines bind to the same
`window.bkCreateFolder` key, so the second assignment wins
at runtime. The button called the placeholder.

**This was never a button-wiring bug or a missing modal.** The
button was wired; the modal-equivalent (a `prompt()` for the
name) already lived in the real handler. The bug was a stale
placeholder that an earlier C2 milestone forgot to remove.

## The fix

Three-line deletion at `app.py:89182–89184`. The block was
replaced with a comment so future readers know why the
function name appears to be defined "twice" (it isn't
anymore — the comment is just prose). Diff:

```diff
-  window.bkCreateFolder = function(){
-    alert('سيتم تفعيل هذا الزر في C2');
-  };
+  /* bkCreateFolder placeholder removed here. The real handler
+     lives ~470 lines above in the same script — it prompts for
+     a name and POSTs to /api/book-folders. The previous stub
+     re-assigned the same global key, so late-binding made the
+     stub win at runtime. Deleting it restores the real impl. */
```

No new function added. No onclick changed. No modal HTML
touched. No POST endpoint modified.

## What was NOT changed

Per the brief's "ZERO TOUCHING" rules:

- ❌ `POST /api/book-folders` endpoint (`app.py:84981`) —
  untouched
- ❌ The folder sidebar / folder click handlers — untouched
- ❌ Other Phase 3 book-folder buttons (rename, delete, move,
  publish) — untouched
- ❌ The sibling C4 stub for `bkOpenMultiUpload` at
  `app.py:89185–89187` — left in place, explicitly out of
  scope. A future C4 milestone removes this one the same way.

## Verification

**Static checks** (commit `6e4a4cd`):

- ✓ `ast.parse(open('app.py').read())` — Python parse OK
- ✓ `grep -c "سيتم تفعيل هذا الزر في C2" app.py` → **0**
  (was 1 before fix)
- ✓ Exactly one `window.bkCreateFolder = function` assignment
  remains in `app.py`
- ✓ `app.py` line count went from 99,805 → 99,808 (gained 3
  for the comment, then lost 6, regained 6 in C3 reword — net
  +3)

**Boot + page test** (passes with the local SQLite DB):

- ✓ `import app` — 476 routes register
- ✓ `POST /login` admin/admin123 — 302 redirect
- ✓ `GET /admin/books` — 200, 59,939 bytes
- ✓ Served HTML no longer contains the C2 stub text
- ✓ Served HTML still contains:
  - `+ مجلد جديد` button label
  - `onclick="bkCreateFolder()"`
  - `/api/book-folders` reference
  - The real handler's `name_ar: name` POST-body fragment

**Smoke test** (`scripts/smoke_books_add_folder_button.py`,
commit `66e1c7c`) — five invariants, all pass:

```
[1] C2 stub Arabic text is gone from served HTML
[2] exactly 1 window.bkCreateFolder = function assignment
    (was 2 before fix)
[3] real bkCreateFolder implementation is intact
    (POST /api/book-folders with name_ar)
[4] button "+ مجلد جديد" + onclick="bkCreateFolder()" present
[5] C4 sibling stub still present (out-of-scope, untouched)

PASS — add-folder button is wired to the real implementation.
```

## Owner browser-test scenario

1. Open `https://mindx-portal-1.onrender.com/admin/books`
2. Right-side sidebar → click the **"+ مجلد جديد"** button
3. Browser shows a `prompt()` dialog asking
   "اسم المجلد:"
4. Type a folder name in Arabic (e.g. `ترم 1`) and press OK
5. Toast `تم إنشاء المجلد ✓` appears
6. New folder appears in the sidebar list
7. (Refresh-test): reload the page; the folder should still
   be in the list

**Failure modes to watch for:**

- If the prompt dialog still shows the old stub alert
  ("سيتم تفعيل هذا الزر في C2") → browser cache. Hard-refresh
  with Ctrl+Shift+R (or Cmd+Shift+R on macOS).
- If the prompt opens but the toast says `غير مصرح` (403) →
  the logged-in user doesn't have `_can_manage_books`
  permission. Check the user's role / capability allowlist.
- If the toast says a different error → the POST endpoint
  rejected the payload. Inspect the JSON response body in
  DevTools → Network for the Arabic error string.

## Notes on the brief

The brief said *"the modal HTML exists"* and described the
expected flow as a modal with name input + save/cancel
buttons. The real handler in the code uses a simpler
`prompt('اسم المجلد:')` dialog — same pattern the existing
`bkRenameFolder` and `bkDeleteFolder` handlers use. The brief
also said *"Do NOT redesign the modal"*, so I kept the
`prompt()` pattern. If the owner later wants a richer modal,
that's a separate enhancement.

The brief mentioned a `bkFolderModal` element id and an
`openCreateFolderModal` function — neither exists in the
code. The actual handler is `window.bkCreateFolder()`. The
button onclick was already correct; only the function body
needed fixing.
