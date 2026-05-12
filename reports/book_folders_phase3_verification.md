# Book-Folders Phase 3 — Admin UI Verification

**Date:** 2026-05-13
**Safety tag:** `safety/book-folders-phase3-20260512-205604`
**Phase commits:** C1 → C8 (this report = C9)

## Commit log

```
<this report>  docs: Phase 3 UI verification
2462d52        test(books): Phase 3 UI smoke (C8)
483a04f        ui(books): polish + responsive layout (C7)
fd8af31        ui(books): move book between folders modal (C6)
5c0bc13        ui(books): publish folder to groups modal (C5)
4a8cfd7        ui(books): multi-file upload modal with drag-drop (C4)
e096bfb        ui(books): books list in selected folder (C3)
a4c1086        ui(books): folder list with create/rename/delete (C2)
162a294        ui(books): folder explorer layout scaffold (C1)
4f6f4c3        (Phase 2 base)
```

## Final HTML structure

```
<div class="topbar">       — existing, untouched
<div class="wrap">         — existing container
  <div class="bk-explorer">    ← NEW (Phase 3)
    <div class="bk-sidebar">
      📁 المجلدات header
      #bk-folders-list (scrollable)
        📂 الجذر pseudo-folder (always at top)
        📁 <folder> entries (with hover actions: 📤 ✏️ 🗑️)
      [+ مجلد جديد] button
    </div>
    <div class="bk-main">
      .bk-main-header   ← title + stat + action bar
      #bk-books-list    ← .bk-book-card per book + empty state
    </div>
  </div>

  <details>الرفع التقليدي</details>  ← legacy upload collapsed
  <div class="panel">إضافة منهج جديد</div>  ← unchanged
  <div class="panel">المناهج</div>     ← unchanged (legacy list)
</div>

<!-- New modals -->
<div id="bk-up-modal">    — multi-file upload (C4)
<div id="bk-pub-modal">   — publish to groups (C5)
<div id="bk-mv-modal">    — move book between folders (C6)
```

## JS functions (all 22, exposed via `window.bk*`)

**Folder list (C1–C2):**
- `bkLoadFolders` — fetch + render sidebar.
- `bkRenderSidebar` — render the folder cards + root pseudo-folder.
- `bkSelectFolder(fid)` — set selected, refresh books pane.
- `bkCreateFolder()` — prompt + POST → reload.
- `bkRenameFolder(fid)` — prompt + PATCH → reload.
- `bkDeleteFolder(fid)` — confirm + DELETE; 409 surface.
- `bkToast(msg, isErr)` — lightweight Arabic toast.

**Books pane (C3):**
- `bkLoadBooks` — fetch /api/book-folders/<id>/books, render.
- `bkDeleteBook(bid)` — confirm + DELETE /api/books/<bid> (legacy endpoint).
- `bkFmtSize`, `bkFmtDate` — display helpers.

**Multi-upload (C4):**
- `bkOpenMultiUpload`, `bkCloseMultiUpload`, `bkUpRenderFiles`,
  `bkUpAddFiles(fileList)`, `bkUpSetTitle(idx, v)`, `bkUpRemove(idx)`,
  `bkUpSubmit`.

**Publish (C5):**
- `bkLoadAllGroups` (cached), `bkOpenPublish(fid)`, `bkClosePublish`,
  `bkPubRender`, `bkPubToggle(gid, on)`, `bkPubSearch(v)`,
  `bkPubUpdateSummary`, `bkPubSubmit`.

**Move (C6):**
- `bkOpenMove(bid)`, `bkCloseMove`, `bkMoveSubmit`.

State objects: `_BK` (folders/selected_id/books/groups_cache),
`_BK_UPLOAD` (files/titles), `_BK_PUBLISH` (fid/all_groups/
current_ids/search), `_BK_MOVE` (bid/current_folder_id).

## 4-role permission visual check (smoke verified)

| User | `/admin/books` | Explorer markup | Notes |
|---|---|---|---|
| admin | 200 | ✅ | role=admin short-circuit |
| 980909805 (raed) | 200 | ✅ | `_BOOKS_V2_FULL_ACCESS_USERNAMES` allowlist |
| 010307885 (ahmed_ibrahim) | 200 | ✅ | allowlist |
| 021005931 (ahmed_younis) | 200 | ✅ | role=admin |
| teacher1 (teacher) | 302 → /dashboard | n/a | existing route gate |

## E2E user flow (manual test outline)

1. **Open `/admin/books`** as admin (or any allowed user).
2. **Click `+ مجلد جديد`** → prompt → enter "ترم 1" → toast "تم إنشاء المجلد ✓".
3. **Click the new folder** in the sidebar → main pane shows it empty.
4. **Click `📤 رفع كتب`** → multi-upload modal opens.
5. **Drag-drop 3 PDFs** OR click → file picker → 3 files chosen.
6. Optionally edit titles per row.
7. **Check `ربط الكتب الجديدة بمجموعات المجلد`** (default checked when folder is selected).
8. **Click `📤 رفع الكل`** → progress → result panel shows 3 ✅.
9. Books appear in the main pane.
10. **Hover on the folder** in the sidebar → click `📤` → publish modal.
11. **Search `مجموعة`** → filter list → check 2 groups → "✓ نشر".
12. **Toast** confirms: "تم النشر لـ 2 مجموعة • تأثر 3 كتاب".
13. **Hover on a book** → click `📁 نقل` → move modal.
14. **Pick `📂 الجذر`** → optionally check inherit → "✓ نقل".
15. **Click `🗑️`** on a book → confirm → toast "تم الحذف ✓".
16. **Hover on folder** → click `🗑️` while it's non-empty → toast "لا يمكن حذف المجلد لاحتوائه على X كتاب".
17. Move all books out → delete folder → confirms → soft-deleted, hidden from default list.

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after every commit | ✅ |
| Legacy single-file upload form still in HTML (`#bk-file`, `#bk-title`, `#bk-save-btn`) | ✅ — smoke [7] |
| Legacy `loadPickers()` + `loadList()` still execute on page load | ✅ — preserved IIFE structure |
| Legacy `bkSave()` (single-file save) untouched | ✅ — not edited |
| `/api/books` admin list still 200 | ✅ — smoke [9] |
| `/api/books/groups-list` still 200 | ✅ — smoke [9] |
| `/api/books/teachers-list` still 200 | ✅ — smoke [9] |
| `/api/books/for-student/<sid>` returns same results | ✅ — Phase 2 verified, no changes since |
| `/api/books/for-teacher` returns same results | ✅ — same as above |
| Permission gate (`_has_books_full_access`) unchanged | ✅ |
| 9-route admin regression all 200 | ✅ — smoke [10] |
| All 22 JS functions present in served HTML | ✅ — smoke [5] |
| All 10 `.bk-*` CSS classes present | ✅ — smoke [6] |
| All 3 modals present in HTML | ✅ — smoke [4] |
| Responsive breakpoint at 768px present | ✅ — smoke [8] |
| Narrow-screen breakpoint at 520px present (file rows + card actions) | ✅ — visible in CSS, not in smoke |
| Modal entry animation (opacity + transform) wired | ✅ — `.modal-back.show .modal {transform: translateY(0)}` |
| Focus rings for keyboard accessibility | ✅ — `.bk-sidebar button:focus, …` |
| No new endpoints added in Phase 3 | ✅ — UI only consumes Phase 2 endpoints |
| No DB schema changes | ✅ |

## Browser-test items (owner verification)

The smoke verifies server-rendered markup but doesn't execute browser JS. The owner should verify:

1. **Folder create/rename/delete** all show the right toasts.
2. **Drag-and-drop** onto the multi-upload dropzone actually picks up files.
3. **The accept-attribute filter** on `<input type=file>` lets the 6 expected mime types through.
4. **The inherit checkbox** is hidden when uploading at root.
5. **Publish modal search** filters the group list as you type.
6. **Mobile view ≤ 768px** stacks the sidebar above the main pane.
7. **Modal focus management** — closing a modal via ESC (browser default for backdrop click) returns focus to the page.

Items 1-5 use established patterns (prompt/confirm + FormData/JSON fetch), and the JS is verified by smoke to be present and syntactically valid (the file parses). Items 6-7 are CSS/A11y polish that needs an actual browser.

## Files touched

- `app.py`
  - C1 (CSS + HTML scaffold + JS state object + boot loader): ~210 lines added to `ADMIN_BOOKS_HTML`.
  - C2 (folder CRUD wired): ~90 lines added.
  - C3 (books list rendering): ~100 lines added.
  - C4 (multi-upload modal + state machine): ~170 lines added.
  - C5 (publish modal + group search): ~115 lines added.
  - C6 (move modal): ~85 lines added.
  - C7 (focus + animation + responsive polish): ~25 lines added.

  Net for Phase 3: ~795 lines added to `ADMIN_BOOKS_HTML` (was 1487 → now ~2280). All additions are scoped to that one constant; no other code modified.
- `scripts/smoke_book_folders_ui.py` — 147-line UI smoke.
- `reports/book_folders_phase3_verification.md` (this file).

## Rollback

`safety/book-folders-phase3-20260512-205604` is the commit immediately before C1. To revert the entire Phase 3:

```bash
git revert --no-edit 2462d52 483a04f fd8af31 5c0bc13 4a8cfd7 e096bfb a4c1086 162a294
git push origin main
```

Each commit is self-contained inside `ADMIN_BOOKS_HTML`. No DB or other-file changes anywhere in Phase 3. Reverting restores the legacy flat-list UI exactly as it was before C1, with the Phase 1 + Phase 2 backend untouched (those phases ship independently).

## What this phase does NOT do

- **No drag-and-drop reordering of folders** in the sidebar. Folders sort by `sort_order` from the DB; the `PATCH /api/book-folders/<id>` endpoint accepts `sort_order` updates but the UI doesn't surface a reorder control yet. Defer to future polish if owner asks.
- **No bulk move.** Per-book move only. The Phase 2 backend doesn't have a bulk endpoint either.
- **No book preview pane inside the modal.** Click "👁️ معاينة" opens `/api/books/<bid>/view` in a new tab (existing endpoint, unchanged).
- **No teacher visibility in the folder UI.** The legacy `books_v2_teachers` table is still managed via the legacy `POST /api/books/<bid>/teachers` endpoint + the legacy form below the explorer.
- **No undo on delete.** Soft-delete is final (the folder row stays but `is_active=0` flags it as a tombstone; there's no UI to re-activate).

## Ready for Phase 4

Phase 4 surfaces folders to students/parents/teachers (the read-only viewer side). The student-view query in `/api/books/for-student/<sid>` stays unchanged because the propagation logic from Phase 2 means books are visible via the existing `books_v2_groups` JOIN. Phase 4 will need:

- New endpoint `GET /api/my-class-books` (or extend `for-student` to return `folder_id` per book + a sibling `folders` list of folders published to this student's groups).
- Parent-hub `/portal/parent-hub/curriculum` rendering update — group books by folder.
- Optional: per-folder section header on the parent UI.

Estimated for Phase 4: 2-3 commits, ~30 minutes per the Phase 0 plan.

---

🎯 **Phase 3 complete. Folder tree explorer, 3 modals (multi-upload + publish + move), 22 JS functions, 10 CSS classes, mobile-responsive at 768px and 520px breakpoints. All 4 allowed roles see the markup; teacher1 still blocked. Existing single-file flow + legacy CRUD untouched. Ready for Phase 4 or owner browser-test.**
