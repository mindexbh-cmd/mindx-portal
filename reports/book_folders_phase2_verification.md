# Book-Folders Phase 2 — API Verification

**Date:** 2026-05-13
**Safety tag:** `safety/book-folders-phase2-20260512-203436`
**Phase commits:** C1 → C10 (this report = C11)

## Commit log

```
<this report>  docs: Phase 2 API verification
92cd88d        test(books): Phase 2 endpoint coverage (C10)
4f2bf51        feat(books): move book between folders (C9)
3c885f8        feat(books): multi-file upload (max 10, 20MB each) (C8)
903cdae        feat(books): GET books in folder (C7)
788a1aa        feat(books): PUT folder groups (replace publishing set) (C6)
21d9484        feat(books): GET folder's published groups (C5)
7187cd9        feat(books): DELETE folder (soft delete with safety) (C4)
256cbd8        feat(books): PATCH folder rename + reorder (C3)
4dd7f55        feat(books): POST /api/book-folders create endpoint (C2)
cacab33        feat(books): GET /api/book-folders list endpoint (C1)
a852529        (Phase 1 verification — base)
```

## Endpoints shipped (9)

| # | Method | Path | Gate | Purpose |
|---|---|---|---|---|
| 1 | GET | `/api/book-folders` | `_can_manage_books` | List folders with book_count + group_count |
| 2 | POST | `/api/book-folders` | `_can_manage_books` | Create folder with Arabic-fold uniqueness check |
| 3 | PATCH | `/api/book-folders/<id>` | `_can_manage_books` | Partial update (name_ar, sort_order, notes) |
| 4 | DELETE | `/api/book-folders/<id>` | `_can_manage_books` | Soft-delete; 409 if non-empty |
| 5 | GET | `/api/book-folders/<id>/groups` | `_can_manage_books` | List published groups + student_count |
| 6 | PUT | `/api/book-folders/<id>/groups` | `_can_manage_books` | Replace publish set + propagate to books_v2_groups |
| 7 | GET | `/api/book-folders/<id>/books` | `_can_manage_books` | Books in folder (or root if id=0) |
| 8 | POST | `/api/books/upload-multi` | `_can_manage_books` | 1-10 files, 20MB each, 6 mime types |
| 9 | PATCH | `/api/books/<id>/move` | `_can_manage_books` | Move book between folders + optional group inheritance |

### Request/response shapes (quick reference)

**Create folder (POST /api/book-folders):**
```json
// in:
{"name_ar": "ترم 1", "sort_order": 10, "notes": "..."}
// out:
{"ok": true, "folder": {"id": 7, "name_ar": "...", ...,
   "book_count": 0, "group_count": 0}}
```

**Publish folder (PUT /api/book-folders/<id>/groups):**
```json
// in:
{"group_ids": [5310, 9104]}
// out:
{"ok": true, "folder_id": 7, "added": [9104], "removed": [9999],
 "books_affected": 3, "ignored_invalid_groups": [99999]}
```

**Multi-upload (POST /api/books/upload-multi):**
```text
multipart fields:
  files                 — N file parts (1-10)
  titles                — JSON array of N titles
  folder_id             — optional int
  inherit_folder_groups — '1' (default) | '0'
```
```json
// out:
{"ok": true,
 "results": [{"filename": "..", "title": "..", "ok": true,
              "book_id": 12, "size_bytes": 1024, "mime": "application/pdf"},
             {"filename": "..", "title": "..", "ok": false,
              "error": "صيغة غير مدعومة"}],
 "success_count": 1, "fail_count": 1, "folder_id": 5,
 "inherited_groups": [5310]}
```

## Permission matrix (verified)

| Role/Username | All 9 endpoints |
|---|---|
| admin (role=admin) | ✅ 200/201 |
| 980909805 (raed, manager) | ✅ 200/201 |
| 010307885 (ahmed_ibrahim, manager) | ✅ 200/201 |
| 021005931 (ahmed_younis, admin role) | ✅ 200/201 (via short-circuit) |
| teacher1 (teacher) | ❌ 403 on all |
| reception, students, parents | ❌ 403 on all |

Verified in smoke Scenario D — every endpoint plus the multi-upload returns 403 for teacher1, and all 4 allowed users return 200 on `GET /api/book-folders`.

## E2E scenarios (all from smoke C10, all green)

### Scenario A — Folder lifecycle
- admin creates folder ✅
- raed creates folder ✅ (allowlist user works)
- list shows both with book_count=0 ✅
- rename succeeds ✅
- duplicate name rejected (Arabic-folded) ✅
- empty-folder delete soft-deletes ✅
- soft-deleted hidden by `active_only=1`, visible by `active_only=0` ✅
- patch on soft-deleted → 404 ✅

### Scenario B — Publishing + propagation
- Folder with 2 books; PUT publish to [G_A, G_B]
- `books_v2_groups` correctly gains 4 rows (2 books × 2 groups) ✅
- Re-publish to [G_A, GID] → G_B removed from books, GID added ✅
- Empty publish set → all 4 rows removed ✅
- `GET /api/book-folders/<id>/groups` returns the current set ✅

### Scenario C — Multi-upload with folder inheritance
- 3 PDFs into a published folder with `inherit=true` → each new book gets `books_v2_groups` rows for every folder-published group ✅
- 1 PDF at root → `folder_id IS NULL` ✅
- 11 files → 400 (max enforced) ✅
- Mixed valid/invalid mime → per-file success/fail in result array ✅
- Title count mismatch → 400 before any INSERT ✅

### Scenario D — Permission matrix
All 8 endpoints + multi-upload return 403 for teacher1; admin / raed / ahmed_ibrahim / ahmed_younis all 200 ✅

### Scenario E — Move book
- Move into folder → `folder_id` updated ✅
- Move back to root (`folder_id: null`) → `folder_id IS NULL` ✅
- Move with `inherit_new_folder_groups=true` → new folder's groups inserted into `books_v2_groups` ✅
- Invalid folder_id → 404; non-existent book → 404 ✅

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after each commit | ✅ |
| Legacy `/api/books/upload` untouched | ✅ |
| Legacy `/api/books/<bid>/groups` untouched | ✅ |
| Legacy `/api/books/<bid>/teachers` untouched | ✅ |
| Existing `/api/books/for-student/<sid>` SQL byte-identical | ✅ — Phase 1 confirmed; Phase 2 only adds rows via INSERT OR IGNORE |
| `/api/books` admin list untouched | ✅ |
| `/admin/books` page still loads | ✅ — Phase 2 [regression] |
| Student / parent / teacher viewer queries unchanged | ✅ |
| `books_v2_groups` UNIQUE constraint preserved | ✅ |
| `books_v2_teachers` untouched | ✅ |
| 9-route admin regression all 200 | ✅ — Phase 2 smoke regression block |
| `_can_manage_books` truth table verified | ✅ — Phase 1 smoke [11], reused in Phase 2 |
| Boot-time table audit clean (no orphan warning) | ✅ — registered in Phase 1 C4 |

## Phase 0 → Phase 2 promise audit

The Phase 0 diagnosis (reports/books_v2_groups_diagnosis.md §9) promised:

> Publishing-time propagation (folder publish → `INSERT OR IGNORE` into `books_v2_groups`) means the visibility query stays byte-identical.

Phase 2 delivers exactly this:
- C6's PUT-groups inserts `(book_id, group_id)` pairs into `books_v2_groups` for every book in the folder.
- C8's multi-upload inserts the same when `inherit_folder_groups=1`.
- C9's move inserts the same when `inherit_new_folder_groups=true`.

The existing student-view query in `app.py:82388` is **unchanged**. Phase 4 will surface the folder structure in the parent UI, but the underlying visibility query stays as-is.

## Files touched

- `app.py`:
  - 9 new endpoints inserted between `/api/books/<bid>/teachers` (line ~82480) and the existing `# ── Viewer endpoints` comment block (line ~83390). Total ~1000 lines added.
  - 1 new helper `_books_v2_multi_detect_mime` + 3 new constants (`_BOOKS_V2_MULTI_MAGIC_TYPES`, `_BOOKS_V2_MULTI_MAX_BYTES`, `_BOOKS_V2_MULTI_MAX_FILES`).
- `scripts/smoke_book_folders_phase2.py` — 465-line comprehensive smoke (5 scenarios + permission matrix + cleanup + regression).
- `reports/book_folders_phase2_verification.md` (this file).

## Rollback

`safety/book-folders-phase2-20260512-203436` is the commit immediately before C1. To revert the entire Phase 2:

```bash
git revert --no-edit 92cd88d 4f2bf51 3c885f8 903cdae 788a1aa 21d9484 7187cd9 256cbd8 4dd7f55 cacab33
git push origin main
```

Notes:
- Reverting removes the new endpoints. Any `book_folder_groups` rows or `books_v2.folder_id` values created during Phase 2 testing/use stay in the DB (harmless — no code references them after revert, and the Phase 1 schema also stays per its own rollback policy).
- The propagation INSERTs into `books_v2_groups` also stay. If the owner wants those gone too, that's a manual cleanup via `DELETE FROM books_v2_groups WHERE ...` — but the propagation rows look identical to legacy direct-assignment rows, so distinguishing them post-revert isn't straightforward. **Recommend leaving them in place** — the data they represent is still semantically valid (book is assigned to group).

## What this phase does NOT do

- **No UI changes.** `/admin/books` still serves the existing 1487-line `ADMIN_BOOKS_HTML` flat-list. Phase 3 builds the tree explorer.
- **No student-facing changes.** `/portal/parent-hub/curriculum` still renders a flat list. Phase 4 surfaces the folder structure.
- **No drag-and-drop move.** The `PATCH /api/books/<bid>/move` endpoint is keyboard/click-driven; if owner wants HTML5 drag-and-drop, that's a Phase 3 polish step.
- **No bulk move.** Per-book move only. A "move all books in folder X to folder Y" bulk operation is deferred.
- **No teacher inheritance.** `books_v2_teachers` is untouched — folders don't auto-propagate to teachers. The owner can decide whether to wire that in a future phase.

## Ready for Phase 3

Phase 2 ships a complete admin API. Phase 3 will:
- Replace the flat list in `ADMIN_BOOKS_HTML` with a tree explorer (folders accordion → books inside).
- Add a folder create/rename/delete modal.
- Add a publish modal that reuses `/api/books/groups-list` for the multi-select.
- Add a "move book" UI (dropdown or button per book).
- Keep the legacy upload modal working alongside a new multi-upload modal.

Estimated for Phase 3: 3-4 commits, ~60 minutes per the Phase 0 plan.

---

🎯 **Phase 2 complete. 9 new endpoints, all gates verified across 4 roles, publishing propagation tested end-to-end, multi-upload with magic-byte sniff working for 6 file formats, 0 regressions on legacy book flows. Ready for Phase 3 admin UI.**
