# Book-Folders Phase 1 — Schema Verification

**Date:** 2026-05-13
**Safety tag:** `safety/book-folders-phase1-20260512-201849`
**Phase commits:** C1 → C5 (this report = C6)

## Commit log

```
<this report>  docs: Phase 1 schema verification
adee82d        test(books): smoke for Phase 1 schema (C5)
c8d6d19        feat(books): _can_manage_books permission helper (C4)
7d4bb3e        feat(books): books_v2.folder_id for folder membership (C3)
8788d3c        feat(books): book_folder_groups for folder-level publishing (C2)
1fb145a        feat(books): book_folders table for content organization (C1)
a95465a        (v2.6 — base)
```

## What shipped

### New tables (2)

#### `book_folders`

```sql
CREATE TABLE IF NOT EXISTS book_folders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name_ar TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_by INTEGER,             -- users.id of creator
    created_by_username TEXT,       -- denormalised for audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    notes TEXT
)
```

Indexes:
- `idx_book_folders_active` on `(is_active, sort_order)` — listing
- `idx_book_folders_name` on `(name_ar)` — uniqueness lookup (Phase 2 API)

No DB-level `UNIQUE` constraint on `name_ar` — uniqueness will be enforced at the API layer scoped to `is_active=1` rows (so "delete + rename to old name" works).

#### `book_folder_groups`

```sql
CREATE TABLE IF NOT EXISTS book_folder_groups(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    folder_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    assigned_by INTEGER,
    assigned_by_username TEXT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(folder_id, group_id)
)
```

Indexes:
- `idx_book_folder_groups_folder` on `(folder_id)`
- `idx_book_folder_groups_group` on `(group_id)`
- (plus the auto-index backing `UNIQUE`)

### New column (1)

`books_v2.folder_id INTEGER` (nullable, default NULL). Idempotent migration `books_v2_folder_id_v1` in the else-branch ALTER block. All existing rows default to `NULL` ⇒ "book lives at root" semantics.

Index: `idx_books_v2_folder` on `(folder_id)`.

### New permission helper (1)

```python
_BOOK_FOLDER_MANAGER_USERNAMES = {
    "010307885",   # أحمد إبراهيم
    "980909805",   # رائد
}

def _can_manage_books(user):
    """admin role OR allowlist."""
```

Mirrors the v2.3 `_can_manage_points` pattern. ahmed_younis (021005931) qualifies via the `role == "admin"` short-circuit and isn't in the literal set.

### Table-audit registration

`book_folders` + `book_folder_groups` added to `_TBL_AUDIT_FEATURE` so the boot warning is gone. Both labeled in Arabic under "مكتبة المناهج" (the existing books-system audit group).

## Migration verification

```
schema_migrations (relevant tags):
  books_v2_schema           (existing, untouched)
  books_v2_cloudinary_v1    (existing, untouched)
  books_v2_file_data_v1     (existing, untouched)
  books_v2_folder_id_v1     ← NEW (this phase)
```

All idempotent — re-running boot any number of times produces no change to existing rows. CREATE TABLE IF NOT EXISTS for `book_folders` + `book_folder_groups` is naturally idempotent; CREATE INDEX IF NOT EXISTS likewise.

## Smoke results (C5)

12 test groups, all green:

| # | check | result |
|---|---|---|
| 1 | `book_folders` 8 columns + types | ✅ |
| 1a | column type assertions per column | ✅ |
| 2 | `book_folders` 2 indexes | ✅ |
| 3 | `book_folder_groups` 6 columns | ✅ |
| 3a | UNIQUE(folder_id, group_id) actually rejects duplicate | ✅ |
| 4 | `book_folder_groups` 2 indexes + auto-index | ✅ |
| 5 | `books_v2.folder_id` column INTEGER nullable | ✅ |
| 5a | every existing books_v2 row has `folder_id IS NULL` | ✅ |
| 5b | `idx_books_v2_folder` index present | ✅ |
| 6 | INSERT folder + correct defaults | ✅ |
| 7 | Two folders with the same name allowed at DB level | ✅ |
| 8 | Publish folder→group INSERT works | ✅ |
| 9 | Duplicate publish blocked by UNIQUE | ✅ |
| 10 | Existing student-view SQL returns same row count | ✅ |
| 11 | `_can_manage_books` 9-case truth table | ✅ |
| 12 | 9-route admin regression (all 200) | ✅ |

## Regression checklist

| Check | Result |
|---|---|
| `python -c "import app"` clean after every commit | ✅ |
| Existing `books_v2` table untouched (column additive only) | ✅ |
| Existing `books_v2_groups` table untouched | ✅ |
| Existing `books_v2_teachers` table untouched | ✅ |
| `/api/books` returns same rows | ✅ |
| `/api/books/for-student/<sid>` SQL unchanged | ✅ — smoke [10] |
| `/admin/books` page still loads | ✅ — smoke [12] |
| Upload endpoint untouched | ✅ |
| Group-assignment endpoints untouched | ✅ |
| Teacher-assignment endpoints untouched | ✅ |
| All existing books have `folder_id IS NULL` (visibility preserved) | ✅ |
| No new DB constraint affects existing rows | ✅ |
| Idempotent migrations — re-boot is a no-op | ✅ |
| Migration tag `books_v2_folder_id_v1` persisted | ✅ |
| Boot-time table audit no longer warns about the new tables | ✅ |

## Files touched

- `app.py`
  - C1 (lines 1437-1466 init_db + 7305-7323 migration branch): `book_folders` table + 2 indexes.
  - C2 (lines 1467-1488 init_db + 7327-7348 migration branch): `book_folder_groups` table + 2 indexes + auto-UNIQUE-index.
  - C3 (lines 1416-1427 init_db + 7440-7470 migration branch + `idx_books_v2_folder`): `books_v2.folder_id` column + idempotent ALTER tag.
  - C4 (lines 34998-35038): `_BOOK_FOLDER_MANAGER_USERNAMES` set + `_can_manage_books` helper; also adds 2 rows to `_TBL_AUDIT_FEATURE` (line 45041).
- `scripts/smoke_book_folders_schema.py` — 12-step smoke.
- `reports/book_folders_phase1_verification.md` (this file).

## Rollback

`safety/book-folders-phase1-20260512-201849` is the commit immediately before C1. To revert the entire Phase 1:

```bash
git revert --no-edit adee82d c8d6d19 7d4bb3e 8788d3c 1fb145a
git push origin main
```

Notes on revert behavior:
- Reverting drops the new code paths but does **NOT** drop the new tables / column from any DB that already booted with them. That's intentional — orphaned schema is harmless (no code references it after revert) and avoiding `DROP TABLE` keeps the data-safety rule from CLAUDE.md.
- The `books_v2_folder_id_v1` migration tag stays in `schema_migrations`. A forward-roll would skip the ALTER (column already exists) — no harm.
- If the owner wants the schema gone too, that's a separate explicit DROP TABLE migration the owner has to approve.

## Ready for Phase 2

Phase 1 is **schema-only** — no user-visible changes, no endpoint changes, no UI changes. Existing book features behave identically. The new schema is now available for Phase 2 to build the API endpoints on top of:

- `GET /api/folders` — list all folders (with active/inactive filter)
- `POST /api/folders` — create a folder (admin gate via `_can_manage_books`)
- `PATCH /api/folders/<id>` — rename / reorder / activate-deactivate
- `DELETE /api/folders/<id>` — soft-delete (refuses if it contains books)
- `POST /api/folders/<id>/publish` — set group assignments (replaces + propagates to `books_v2_groups`)
- `GET /api/folders/<id>/books` — books in folder
- `PATCH /api/books/<bid>/move` — move book between folders
- (modified) `POST /api/books/upload` — accept optional `folder_id`

Estimated: 4-5 commits, ~50 minutes — per the Phase 0 plan.

---

🎯 **Phase 1 complete. 2 new tables, 1 new column, 1 new permission helper, 0 regressions. 12-step smoke green. Ready for Phase 2.**
