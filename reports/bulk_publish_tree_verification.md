# Bulk-publish tree — verification (v2.9.7)

## What shipped

A new top-level button on `/admin/books` (next to the dashboard
back-link) opens a modal that lets an admin publish any subset of
the library — folders + standalone books — to any subset of the
school groups in one action. Semantics are strictly additive: an
existing `(book, group)` membership is never removed.

## Architecture (one-paragraph)

- **`POST /api/books/bulk-publish`** — body `{book_ids:[], group_ids:[]}`.
  Whitelists both id sets, loops `INSERT OR IGNORE INTO
  books_v2_groups(book_id, group_id) VALUES(?,?)` over the cross
  product, returns `{ok, books_count, groups_count, links_created,
  links_already_existed, total_attempted, invalid_book_ids,
  invalid_group_ids}`. `_pg_translate` rewrites `INSERT OR IGNORE`
  to `ON CONFLICT DO NOTHING` on Postgres.
- **`GET /api/books/all-with-folders`** — one round trip for the
  modal: `{folders:[{id,name,book_count,books:[{id,title,file_size_bytes}]}],
  standalone_books:[...], all_groups:[{id,name}], total_books}`.
- **UI** — collapsible folder cards with per-folder select-all,
  global "select-all" for books and groups, live count badges,
  preview pill that gates the submit button.

## Browser test plan (run on prod once `v2.9.7` is live)

1. **Open** `/admin/books` as admin user.
2. **See** the new "📚 نشر جماعي" button in the top bar next to
   "رجوع للداشبورد".
3. **Click** it → modal opens, shows "جاري التحميل..." briefly,
   then the tree appears with every folder pre-expanded and
   every book pre-checked. The header pill counts show e.g.
   `0/N` for groups and `N/N` for books.
4. **Click** a folder header (not its checkbox) — folder
   collapses; click again — expands. Indicator chevron flips
   ▼/◀.
5. **Uncheck** the per-folder "select all" — every book in that
   folder unchecks; folder header count shows `0/M`. Global
   "select all" books goes to indeterminate (filled square).
6. **Re-check** the per-folder select-all — only that folder's
   books recheck. Other folders untouched.
7. **Uncheck** one specific book inside a folder. Folder count
   shows `M-1/M`; global count shows `(N-1)/N`; preview shows
   "سيتم إضافة N-1 كتاب إلى 0 مجموعة" in red (empty state). The
   "📚 نشر" button stays disabled.
8. **Check** 2 groups → preview flips green: "سيتم إضافة N-1
   كتاب إلى 2 مجموعة". Submit button enables.
9. **Click** "📚 نشر" → submit shows "⏳ جاري النشر..." then
   succeeds with a toast like "تم النشر — K ربط جديد، L كان
   موجوداً". Modal closes.
10. **Open** any book affected by the bulk publish and verify
    via its single-book edit modal that the 2 new groups appear
    alongside any pre-existing memberships (additive — nothing
    was removed).
11. **Open** the modal again and submit the SAME book+group pair
    a second time → toast shows `links_created=0`,
    `links_already_existed=N*M` (idempotent on re-submit).

## Regression checks (already covered by `scripts/smoke_bulk_publish_tree.py`)

- The legacy folder-level "📤 نشر للمجموعات" button still
  appears in folder headers (it still works the way it did —
  replacement semantics on the folder publish set).
- Single-book group editing (`POST /api/books/<bid>/groups`)
  untouched.
- Folder publish PUT (`PUT /api/book-folders/<fid>/groups`)
  untouched.
- No duplicate `window.<handler>` assignments — the C4 late-binding
  bug class is asserted away.

## Permission gate

Both new endpoints check `_has_books_full_access(user)` — same as
the existing single-book group endpoint. No new role grants needed.

## Audit trail

Every successful bulk-publish writes one row to the audit log under
`books_v2.bulk_publish` with the validated book/group id sets and
the `links_created` / `total_attempted` counts.
