# Chunked upload — SSL SYSCALL EOF on finalize

**Symptom:** v2.9.5 chunked upload, batch of 4 files. 3 small files
(10–15 MB) finalized fine. One 25 MB file with a ~120-char Arabic
title failed with `psycopg2.OperationalError: SSL SYSCALL error: EOF
detected`. Chunks all uploaded successfully — the failure was at the
**finalize** step.

**No code changes made.** This is an investigation report only.

---

## 1. Finalize pipeline — what actually happens

`POST /api/books/upload/finalize` (`app.py:86171`):

1. Auth check (`_can_manage_books`).
2. Load `upload_sessions` row by `(id, user_id)` — line 86192.
3. Verify all `total_chunks` indexes are present in `received_chunks`
   (otherwise 409 with `missing_chunks`).
4. Resolve session dir under `/var/data/chunks/<upload_id>`.
5. **Reassemble in memory** (lines 86217–86230):
   ```python
   buf = BytesIO()
   for i in range(total_chunks):
       with open(<sdir>/<i>.bin, "rb") as fh:
           buf.write(fh.read())
   raw = buf.getvalue()
   ```
   For a 25 MB file: 5 chunks × ~5 MB → one 25 MB `bytes` object pinned
   on the heap (the `BytesIO` + `getvalue()` produces a second copy →
   ~50 MB transient).
6. Magic-byte sniff via `_books_v2_multi_detect_mime(raw)`.
7. **Single INSERT** (lines 86253–86261):
   ```sql
   INSERT INTO books_v2(title, description, file_path,
                        file_size_bytes, can_download,
                        uploaded_by_username, uploaded_by_name,
                        uploaded_at, is_deleted,
                        cloudinary_url, cloudinary_public_id,
                        file_data, folder_id)
   VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP,0,?,?,?,?)
   ```
   `?,?` translated to `%s,%s` by `_PgConnection`, **plus a
   `RETURNING id` appended automatically**. `raw` (25 MB) goes to
   `file_data` (BYTEA). `title` is the 120-char Arabic string.
8. On success: cleanup chunks dir, delete `upload_sessions` row,
   audit-log, return `{ok:true, book_id, size_bytes, mime}`.
9. **On any exception** (line 86270):
   ```python
   except Exception as ex:
       return jsonify({"ok": False, "error": str(ex)}), 500
   ```
   Raw `str(ex)` leaks to user. **No `traceback.format_exc()`, no
   `app.logger.exception`, no retry.** That's why the user saw
   `SSL SYSCALL error: EOF detected` verbatim — it's the psycopg2
   `OperationalError` message.

## 2. Relevant schema

**`books_v2`** (`app.py:1408`, plus migration `books_v2_file_data_v1`
at `app.py:7484`):

| Column                | Type                  | Constraint |
| --------------------- | --------------------- | ---------- |
| `id`                  | INTEGER PRIMARY KEY   | autoincr   |
| `title`               | TEXT                  | NOT NULL   |
| `description`         | TEXT                  | —          |
| `file_path`           | TEXT                  | NOT NULL   |
| `file_size_bytes`     | INTEGER               | default 0  |
| `can_download`        | INTEGER               | default 1  |
| `uploaded_by_username`| TEXT                  | —          |
| `uploaded_by_name`    | TEXT                  | —          |
| `uploaded_at`         | DATETIME              | default CURRENT_TIMESTAMP |
| `is_deleted`          | INTEGER               | default 0  |
| `cloudinary_url`      | TEXT                  | —          |
| `cloudinary_public_id`| TEXT                  | —          |
| `file_data`           | **BYTEA**             | nullable   |
| `folder_id`           | INTEGER               | nullable   |

No UNIQUE constraints other than the `id` primary key. **`title TEXT`
in Postgres → unlimited length**, so a 120-char Arabic title is fine.
Encoding is UTF-8 throughout (psycopg2 default + Flask).

**`upload_sessions`** (`app.py:1461`):

| Column            | Type            | Constraint |
| ----------------- | --------------- | ---------- |
| `id`              | TEXT            | PRIMARY KEY |
| `user_id`         | INTEGER         | NOT NULL   |
| `filename`        | TEXT            | NOT NULL   |
| `total_size`      | INTEGER         | NOT NULL   |
| `total_chunks`    | INTEGER         | NOT NULL   |
| `received_chunks` | TEXT            | default `'[]'` |
| `title`           | TEXT            | NOT NULL   |
| `folder_id`       | INTEGER         | —          |
| `created_at`      | DATETIME        | default CURRENT_TIMESTAMP |
| `expires_at`      | DATETIME        | NOT NULL   |

Init endpoint (`app.py:86023`) caps `title` at 200 chars — the
120-char title passed validation. Filename inserted as `filename[:300]`.
**Arabic comma U+060C, dash, all UTF-8 round-trip safely through
TEXT columns** — that is not the cause.

## 3. Ranked root-cause hypotheses

### H1 — Postgres server killed the connection mid-INSERT (most likely)

`SSL SYSCALL error: EOF detected` is psycopg2's message when the
TCP socket to Postgres is closed by the **server side** while a query
is in flight. On Render's managed Postgres, the common triggers are:

- **Statement timeout** — the 25 MB BYTEA payload + the auto-appended
  `RETURNING id` round-trip can take several seconds. If the cluster
  has a `statement_timeout` set (Render's default is generous but
  not unlimited), a slow insert can exceed it. Smaller 10–15 MB
  inserts complete inside the window; 25 MB doesn't.
- **OOM kill on the Postgres backend** — psycopg2 sends BYTEA in
  the extended protocol with binary framing; Postgres allocates
  work_mem-style buffers for the value. On Render Starter
  Postgres (limited RAM), a 25 MB BYTEA arriving after the
  server has been serving the same web worker for the prior three
  uploads can push the backend over its limit. The kernel kills
  the backend → SSL EOF on the client.
- **idle_in_transaction_session_timeout** — less likely because
  `_PgConnection.autocommit = True` (line 173), but the BYTEA copy
  inside the cursor still counts as "in-progress".

This hypothesis explains everything observed: the three small files
fit comfortably under whatever the threshold is; the 25 MB file
crosses it.

### H2 — Per-request connection establishment timing out at the wrong moment

`get_db()` opens a fresh `_PgConnection` per Flask request and
closes on teardown. For the 4th upload, all chunk requests (6 of
them for a 25 MB / 5 MB file) each opened+closed a connection. By
finalize time, the underlying TLS handshake to Render Postgres can
fail intermittently and surface as `SSL SYSCALL error: EOF`. Less
likely than H1, but worth excluding by adding diagnostic logging.

### H3 — Cumulative web-worker memory pressure

Each finalize on the gunicorn worker leaves: a `BytesIO`, a `raw`
bytes copy, the psycopg2 parameter buffer, and the cursor's result
row. Python doesn't return memory to the OS aggressively. After
three back-to-back 10–15 MB uploads, the worker's RSS could be
60–80 MB above baseline. The 4th file pushes the worker close to
or over the Render Starter web service's memory cap, triggering
OOM kill during the INSERT. The client sees the connection drop.

This is a less likely explanation than H1 because Render usually
restarts the worker (which would surface as a 502, not an SSL EOF
in the response body), but cannot be ruled out without inspecting
Render's "Metrics" panel for the upload timestamp.

### H4 — Title encoding / length (ruled out)

The title and filename are stored as TEXT in both `upload_sessions`
and `books_v2`, no length cap on the column side. The init
endpoint enforces a 200-char title cap; this file's 120 chars
passed. The Arabic comma U+060C, dashes, and spaces are valid UTF-8
codepoints with no special handling required by psycopg2 or
Postgres. **This is not the cause.**

### H5 — RETURNING id rewrite breaking the insert (ruled out)

`_PgConnection.execute` auto-appends `RETURNING id` to every
INSERT (`app.py:199–200`). `books_v2` has an `id` column, so the
rewrite is correct here. Even if it were wrong, the failure mode
would be a Postgres error message ("column id does not exist"), not
an SSL EOF. **Ruled out.**

### H6 — Magic-byte detector consuming too much memory (ruled out)

`_books_v2_multi_detect_mime(raw)` just inspects the first ~16
bytes of `raw`. No buffer copy beyond the slice. Not the cause.

## 4. Why other 3 succeeded; why this one failed

Three smaller files (10–15 MB each) finished their finalize INSERT
in a window the server was happy with — small enough BYTEA payload
that statement_timeout / memory budget was never threatened. The 4th
file at 25 MB is **~2× the largest of the three**. The wire-protocol
cost of a BYTEA in extended-query mode is roughly linear in payload
size; Postgres-side allocation is roughly 1.5–2× the binary value.
At 25 MB the budget is exceeded and the backend either times out or
gets killed → SSL EOF on the client.

The Arabic title is a red herring — TEXT length is unconstrained
and UTF-8 round-trips cleanly. **The file size is the variable that
changed**, not the title or the language.

## 5. Recommended fix (no code written yet)

In priority order:

**Fix 1 — add diagnostic logging to finalize.** Replace `str(ex)` at
`app.py:86270` with a `traceback.format_exc()` capture written to
`app.logger.exception(...)`, plus a generic user-facing message
("تعذّر حفظ الكتاب — حاول مرة أخرى"). This alone will tell us in the
next failure whether it's `OperationalError`, `OperationalError:
SSL SYSCALL`, or something else, plus where in the call stack it
fired.

**Fix 2 — retry-with-fresh-connection on `psycopg2.OperationalError`.**
Catch the exception type explicitly, close the dead connection, open
a new one via `_new_connection()`, and re-run the INSERT once. The
chunks are still on disk; `raw` is still in memory. This is cheap and
robust against transient SSL/network failures.

**Fix 3 — stream the BYTEA to avoid a single jumbo INSERT.** Either:
- Use Postgres large objects (`lo_import` + `lo_get`) so the
  protocol streams in 8 KB pages instead of one big parameter. Heavier
  refactor.
- Or revert to file-system storage: write `raw` to
  `/var/data/books_v2/<bid>_<safe>.pdf` and store only the path in
  `books_v2.file_path`. The `file_data` BYTEA column was added in
  `books_v2_file_data_v1` migration, so both paths already exist in
  code; switching new uploads back to file-path is the smallest
  surface-area change.

Fix 1 is non-controversial and should land first. Fix 2 is the
right next step if Fix 1's logs confirm `OperationalError`. Fix 3
is the long-term solve and should be opened as a separate ticket —
storing 25–150 MB blobs in a managed Postgres on the Starter plan is
on the steep part of the cost/reliability curve regardless of how
clever the INSERT is.

## 6. Workaround for the owner right now

**Yes — try one of these in order:**

1. **Refresh the page, then upload only the failed file alone.**
   This eliminates the cumulative-worker-memory hypothesis (H3) and
   gives the 25 MB file a clean web-worker + DB-backend with no prior
   load. Most likely to succeed.
2. If that still fails: **upload it via the legacy single-shot
   `/api/books/upload` endpoint** (still mounted at `app.py:84685`).
   The single-shot path uses the same final INSERT but skips the
   chunk reassembly, so memory pressure inside the worker is
   slightly lower. If it succeeds there but not via chunked, that's
   evidence pointing at H3.
3. If both fail: **shorten the title to something brief** like
   "بحوث في علم الأصول - ج4" and rename. This isn't because the
   title is the cause (it isn't), but because it cleanly rules out
   any latent encoding regression on the chunk-store path. If a
   short-title upload also fails, the title is conclusively
   exonerated and we're left with the size hypothesis (H1).

The title is **not** the bug; the 25 MB BYTEA insert against the
managed Postgres is. The workaround exists only because retrying
the same file under a less-loaded worker should succeed without
any code change.

---

**Awaiting owner approval before any code change.**
