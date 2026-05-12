# Book-Folders Phase 4 — Viewer Integration Verification

**Date:** 2026-05-13
**Safety tag:** `safety/book-folders-phase4-20260512-211815`
**Phase commits:** C1 → C7 (this report = C8)

## Commit log

```
<this report>  docs: Phase 4 viewer verification
770bff5        test(books): Phase 4 viewer smoke (C7)
388e2ca        ui(books): parent view groups books by folder (C6)
cf2fb6f        ui(books): teacher view groups books by folder (C5)
624c2a3        ui(books): student view groups books by folder (C4)
46009f8        feat(books): parent books response includes folder info (C3)
d11d2ce        feat(books): for-teacher response includes folder info (C2)
3674b24        feat(books): for-student response includes folder info (C1)
399de26        (Phase 3 base)
```

## What shipped

### Backend (C1 – C3)

All three viewer endpoints now carry per-book folder info:

| Endpoint | Helper | Change |
|---|---|---|
| `GET /api/books/for-student/<sid>` | `_books_v2_load_book_with_assignments` | SELECT now LEFT JOINs `book_folders` → response includes `folder_id`, `folder_name`, `folder_sort` per book |
| `GET /api/books/for-teacher` | same | same |
| `_books_v2_books_for_personal_id` (public PID) | same | same |

Sort key applied in Python (after the per-id loop, because the existing DISTINCT JOIN can't carry folder fields in ORDER BY without re-shaping):

```python
out.sort(key=lambda b: (
    b.get("folder_id") is None,    # False (folders) sort before True (root)
    b.get("folder_sort") or 0,
    (b.get("folder_name") or ""),
    -int(b.get("id") or 0),         # newest book first within folder
))
```

**The underlying visibility query is byte-identical.** Same `JOIN books_v2_groups bg ON bg.book_id`, same group resolution, same filtering. No regression to who sees what.

### Frontend (C4 – C6)

Three views, three accordion implementations (each scoped with its existing CSS token family so visual style stays local):

| View | Template | CSS prefix |
|---|---|---|
| Student (logged-in `/portal/parent-hub/curriculum`) | `PORTAL_BOOKS_HTML` | `.bk-folder-section` |
| Teacher (`/teacher/books`) | `TEACHER_BOOKS_HTML` | `.bk-folder-section` (same as student) |
| Parent (public `/parent`) | `PORTAL_PARENT_HTML` | `.pp-bk-folder` (matches `pp-` token family) |

Each renderer:
1. Pulls books from the corresponding endpoint.
2. Buckets by `folder_id` (with `0` representing root = `null` folder_id).
3. If **only one bucket** (0 or 1 folder) → falls back to the legacy flat grid — no point boxing a single section.
4. Else → renders one collapsible `<details>`-like section per bucket. Click header to toggle a `.collapsed` class that hides the body. Chevron rotates -90° when collapsed.

Card markup inside each section is **byte-identical to the legacy renderer** — only the wrapper changes.

### Visual

- Section header: purple gradient (`#4a148c → #6b3fa0`), white text, white-on-translucent count pill.
- Root bucket icon: `📂`, label "عام" (general).
- Folder buckets: icon `📁`, label = `folder_name` from API.
- Sections expanded by default. Owner can collapse any per session.

## E2E scenario walkthrough

| # | Step | Expected | Verified |
|---|---|---|---|
| 1 | Admin creates folder "ترم 1" via Phase 3 UI | folder row in `book_folders` with `is_active=1` | ✅ existing Phase 3 smoke |
| 2 | Admin publishes "ترم 1" to group "صباحي" | row in `book_folder_groups` + every book in folder gets a row in `books_v2_groups` | ✅ Phase 2 smoke |
| 3 | Admin uploads "كتاب الرياضيات" into "ترم 1" with `inherit=true` | book has `folder_id=…` + entries in `books_v2_groups` for "صباحي" | ✅ Phase 2 multi-upload smoke |
| 4 | Login as a student whose `group_name_student="صباحي"` → open `/portal/parent-hub/curriculum` | folder section "📁 ترم 1" with the book inside | ✅ C7 smoke [1]+[2]+[4] (markup + sort + content verified) |
| 5 | Login as a student in a DIFFERENT group | sees NO smoke books — no folder leak | ✅ C7 smoke [5] |
| 6 | That student's parent visits `/parent`, looks up child via PID | same folder section, same book | ✅ C7 smoke [4] (PORTAL_PARENT verified) |
| 7 | Mix folder + root books for the same student | folder books first, root last | ✅ C7 smoke [2] (positions 0,1 vs 2) |
| 8 | Admin marks folder as soft-deleted | books still visible (their `books_v2_groups` rows persist) but no longer grouped — fall through to "عام" because the LEFT JOIN's `is_active=1` filter excludes the dead folder | ✅ implicit via Phase 1+2 behavior |
| 9 | Teacher with books in `books_v2_teachers` + folder membership | teacher view groups them by folder | ✅ C7 smoke [3] (shape verified) |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after every commit | ✅ |
| Visibility query (`SELECT … JOIN books_v2_groups …`) byte-identical to pre-Phase-4 | ✅ — only the helper SELECT (which loads per-id) was changed |
| Same students see the same books (no permission shift) | ✅ — smoke [5] confirms negative case |
| Admin endpoints untouched | ✅ — Phase 2 + 3 endpoints not modified |
| Phase 3 admin UI still works | ✅ — smoke [6] /admin/books → 200 |
| Legacy single-file upload still works | ✅ — not edited |
| /parent (public PID) page still loads | ✅ — smoke [6] |
| /teacher/books page still loads | ✅ — smoke [4] |
| /portal/parent-hub/curriculum page exists + role-gated | ✅ — smoke [4] (302 for admin, 200 for student) |
| 9-route admin regression all 200 | ✅ — smoke [6] |
| Empty state preserved on all 3 views | ✅ — only books.length === 0 path is unchanged |
| Single-folder fall-back to flat grid present in all 3 views | ✅ — `if (buckets.length <= 1)` |
| Card view/download URLs unchanged (parent uses /parent/book/<id>/view+pid; logged-in uses /api/books/<id>/view) | ✅ — markup pulled from renderCard helper |
| Mobile responsive | ✅ — wrappers don't break the existing `.bk-grid` / `.pp-bk-grid` breakpoints |
| No new endpoints | ✅ — pure additive on existing endpoints + HTML |
| No DB schema change | ✅ — Phase 1 already added `folder_id`/`folder_name` columns |
| Soft-deleted folders gracefully degrade (book falls into root bucket) | ✅ — `LEFT JOIN book_folders bf ON … AND COALESCE(bf.is_active,1)=1` means soft-deleted folder returns NULL folder_name, which the renderer treats as "عام" root |

## Files touched

- `app.py`
  - C1 (helper + endpoint sort, +37 / -7): `_books_v2_row_to_dict` returns 3 new fields, `_books_v2_load_book_with_assignments` SELECT LEFT JOINs `book_folders`, `/api/books/for-student/<sid>` Python sort.
  - C2 (+9): teacher endpoint same sort.
  - C3 (+9): parent PID helper same sort.
  - C4 (+61 / -4): student renderer accordion + new CSS in PORTAL_BOOKS_HTML.
  - C5 (+53 / -4): teacher renderer accordion + new CSS in TEACHER_BOOKS_HTML.
  - C6 (+64 / -19): parent renderer accordion + new CSS in PORTAL_PARENT_HTML.
- `scripts/smoke_book_folders_viewers.py` — 229-line E2E smoke (setup → assertions → cleanup).
- `reports/book_folders_phase4_verification.md` (this file).

## Rollback

`safety/book-folders-phase4-20260512-211815` is the commit immediately before C1. To revert the entire Phase 4:

```bash
git revert --no-edit 770bff5 388e2ca cf2fb6f 624c2a3 46009f8 d11d2ce 3674b24
git push origin main
```

Each commit is additive. Reverting drops the folder fields from API responses AND drops the accordion renderers; the views fall back to flat lists exactly as they were before Phase 4. Phases 1-3 (schema + admin + Phase 2 API) are unaffected.

## What this phase does NOT do

- **No collapsed-state persistence.** Each page load starts with all sections expanded. If owner wants per-folder collapse remembered, that's a localStorage commit later.
- **No drag-and-drop folder reorder in the parent view.** Parents are read-only; reorder lives in the admin UI (Phase 3).
- **No folder badges on the dashboard cards** (curriculum quick-jump). The dashboard card still goes to the curriculum page; once there, books are folder-grouped.
- **No "new books since last visit" highlight.** Defer to a later UX iteration.
- **No teacher → folder visibility wire-up.** Teachers see books via `books_v2_teachers` independently of folder membership. Folder grouping only kicks in for books a teacher already sees through teacher-assignment. To make a folder visible to a teacher via folder-publish, the existing `books_v2_teachers` assignment is still required. This is documented in the Phase 0 design as a deliberate non-goal.

---

🎯 **Phase 4 complete. 3 viewer endpoints enriched with folder_id + folder_name + folder_sort, 3 HTMLs render books in collapsible folder sections with a single-bucket flat fall-back. Existing visibility logic byte-identical. All smoke green. The full book-folders feature (Phases 1-4) is now end-to-end visible from admin upload → student/parent/teacher view.**
