# Plan — friendly "book file missing" page

## Problem

When a `books_v2` row has no usable bytes on disk (no `file_data` blob, no
Cloudinary URL, no valid `file_path`), both view/download endpoints return:

```json
{"book_id":53,"error":"الملف مفقود على القرص …","missing_file":true,"ok":false}
```

Parents clicking the book card hit this URL directly via `<a href>`, so the
browser renders the raw JSON. The UX is broken for parents and admins alike.

Two call sites both return that JSON with HTTP 410:

- `app.py:89199` — `_books_v2_send_file` (logged-in `/api/books/<bid>/view`
  + `/api/books/<bid>/download`).
- `app.py:89370` — `_books_v2_send_file_public` (public parent portal
  `/parent/book/<bid>/view` + `/parent/book/<bid>/download`).

## Approach

Add a single helper, `_books_v2_missing_file_response(bid, *, pid)`, that
picks the response shape based on what the caller wants:

- If the request looks like a browser navigation (HTML in `Accept`, not
  `Accept: application/json` only, no `X-Requested-With: XMLHttpRequest`) →
  render a Mindex-branded Arabic HTML page (`MISSING_FILE_PAGE_HTML`).
- Otherwise → keep the existing JSON envelope unchanged.

The HTML page:

- RTL, `lang="ar"`, mobile-responsive, mirrors the parent-hub purple
  gradient + white card style used by `PORTAL_PARENT_HUB_HTML` and
  `PARENT_PDF_VIEWER_HTML`.
- Big lock + warning emoji "illustration", H1 "عذراً، هذا المنهج غير متاح
  حالياً", subtext "الإدارة على علم بالمشكلة وستحلّها قريباً", primary
  button "العودة للقائمة" pointing back to:
    - `/parent?pid=<pid>` when `pid` was supplied (public path).
    - `/portal/parent-hub/curriculum` for logged-in parents/students.
    - `/admin/books` for admins/uploaders.
- Quiet secondary line with the book id so support can match it to a row.
- One short stderr log line per hit so recurring orphans surface in the
  Render log alongside the boot-probe diagnostics.

Status code stays **410 Gone** either way — clients (and any future APK
consumer) keep the same machine-readable signal.

## Constraints honoured

- No DB schema change.
- No change to `books_v2` lookup / priority-order logic.
- API JSON envelope intact for non-HTML consumers.
- Working books unaffected — helper is only reached on the existing 410
  branch.

## Files touched

- `app.py` — add `MISSING_FILE_PAGE_HTML` template constant, add
  `_books_v2_missing_file_response`, replace the two `jsonify(... 410)`
  return sites.

No JS or settings changes.

## Out of scope

- Auto-deploy via "safe_deploy" (no such skill in this environment).
- Specialist sub-agent reviews (the named agents do not exist here).
- Browser screenshots (no headless browser available in this session).
