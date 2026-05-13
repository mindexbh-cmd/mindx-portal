# 150 MB book-upload limit — verification

**Goal:** raise the per-file limit on `/admin/books` from
20/50 MB to a uniform 150 MB, with gunicorn timeout bumped
to absorb the longer upload duration.

**Commits in this change** (all on `main`):

- `e0602be` — feat(books): raise per-file upload limit to 150 MB (server)
- `44a78dd` — feat(books-ui): client validation + Arabic hints for 150 MB
- `2427422` — ops: raise gunicorn timeout 120s → 300s for large uploads
- `4433aea` — test(books): 150 MB limit smoke

**Safety tag:** `safety/book-size-150mb-20260513-205852`
pushed before any edit.

---

## What changed

### Server (commit `e0602be`)

| Where | Before | After |
|---|---|---|
| `app.py:84257` `_BOOKS_V2_MAX_BYTES` | `50 * 1024 * 1024` | `150 * 1024 * 1024` |
| `app.py:85593` `_BOOKS_V2_MULTI_MAX_BYTES` | `20 * 1024 * 1024` | `150 * 1024 * 1024` |
| `app.py:84623` error string (single upload) | `"حجم الملف يتجاوز 50 ميجا"` | `"حجم الملف يتجاوز 150 ميغا"` |
| `app.py:84742` error string (reupload) | `"حجم الملف يتجاوز 50 ميجا"` | `"حجم الملف يتجاوز 150 ميغا"` |
| `app.py:85742` error string (multi-upload) | `"حجم الملف يتجاوز 20 ميجا"` | `"حجم الملف يتجاوز 150 ميغا"` |

Both runtime constants now resolve to **157,286,400 bytes** (150 MB).

### Client / UI (commit `44a78dd`)

| Where | Before | After |
|---|---|---|
| `app.py:88615` `bkSave` JS check | `50*1024*1024` + `"50 ميجا"` toast | `150*1024*1024` + `"150 ميغا"` toast |
| `app.py:88762` `bkDoReupload` JS check | `50*1024*1024` + `"50 ميجا"` toast | `150*1024*1024` + `"150 ميغا"` toast |
| `app.py:89275` `bkUpAddFiles` `MAX` | `20 * 1024 * 1024` | `150 * 1024 * 1024` |
| `app.py:89282` `bkUpAddFiles` per-file toast | `"يتجاوز 20 ميجا"` | `"يتجاوز 150 ميغا"` |
| `app.py:88437` single-upload label | `"(حد أقصى 50 ميجا)"` | `"(حد أقصى 150 ميغا)"` |
| `app.py:88535` single-reupload label | `"(حد أقصى 50 ميجا)"` | `"(حد أقصى 150 ميغا)"` |
| `app.py:89379` multi-upload drop-zone hint | `"الحد الأقصى 20 ميجا لكل ملف"` | `"الحد الأقصى 150 ميغا لكل ملف"` |

### Transliteration note

The owner's brief specified `"150 ميغا"` with **غ**. The existing
codebase used `"ميجا"` with **ج**. All eleven books-area strings
updated in this change use **غ**, so the books admin surface is
now internally consistent. Other features that still say `"ميجا"`
are out of scope and unchanged.

### Deploy config (commit `2427422`)

| File | Before | After |
|---|---|---|
| `Procfile:1` | `--timeout 120` | `--timeout 300` |
| `render.yaml:25` (startCommand) | `--timeout 120` | `--timeout 300` |
| `render.yaml:20-24` (comment) | rationale was Drive-import 30-90s | rewritten to include 150 MB upload rationale |

`--graceful-timeout 30` unchanged.

### ⚠️ Render dashboard step required

Per `CLAUDE.md`: `render.yaml` does **not** auto-apply to existing
services. After this change deploys, the owner must:

1. Open https://dashboard.render.com → `mindx-portal-1` service
2. **Settings → Build & Deploy → Start Command**
3. Paste:
   ```
   gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300 --graceful-timeout 30
   ```
4. **Save Changes**
5. **Manual Deploy** → "Clear build cache & deploy" (or just trigger a redeploy)

Without this step, the deployed gunicorn keeps the old 120s
timeout regardless of what `render.yaml` says, and 150 MB
uploads on slow connections will still 502.

## Why the timeout bump matters

A 150 MB upload time depends on the parent's upstream bandwidth:

| Upstream | 150 MB upload time | 120s ceiling | 300s ceiling |
|---|---|---|---|
| 50 Mbps (office fibre) | ~24 s | ✓ | ✓ |
| 25 Mbps (home fibre, Bahrain typical) | ~48 s | ✓ | ✓ |
| 10 Mbps (mobile decent) | ~120 s | **at the limit** | ✓ |
| 5 Mbps (slower mobile) | ~240 s | **502** | ✓ |
| 3 Mbps (3G fallback) | ~400 s | **502** | **at the limit** |

300 s comfortably covers everything except sub-3-Mbps connections.

## What was NOT changed

Per the brief's "ZERO TOUCHING" rules:

- ❌ BYTEA storage pattern — `books_v2.file_data` still holds the
  bytes; no switch to filesystem or cloud.
- ❌ Auth / permission helpers (`_has_books_full_access`,
  `_books_v2_pid_can_view`).
- ❌ Upload flow itself (file validation, magic-byte PDF check,
  the actual INSERT/UPDATE).
- ❌ The two-tier page cache shipped earlier today.
- ❌ Flask `MAX_CONTENT_LENGTH` — still unset (Flask layer
  remains unlimited; the upload endpoints enforce per-file).
- ❌ Postgres / Render plan tier — the diagnosis flagged that
  a 150 MB ceiling × 50 books could approach 7.5 GB; the
  owner has confirmed they're comfortable with that growth.

## Smoke verification (commit `4433aea`)

```
[1] _BOOKS_V2_MAX_BYTES == 157,286,400 bytes (= 150 MB)
[2] _BOOKS_V2_MULTI_MAX_BYTES == 157,286,400 bytes (= 150 MB)
[3] all 6 expected 150 MB markers in served HTML
[4] no leftover '20 ميجا' / '50 ميجا' / 20|50 MB JS literals
[5] gunicorn --timeout = 300 in BOTH Procfile and render.yaml,
    no stale --timeout 120
[6] all 3 upload endpoints still wired (/upload, /upload-multi,
    /<bid>/reupload)

PASS — 150 MB limit landed cleanly across server + client + UI +
deploy config.
```

## Owner browser-test scenarios

After deploy + the manual Render dashboard step + hard-refresh
(Ctrl+Shift+R):

### A — ~100 MB single-upload should succeed

1. `/admin/books` → "إضافة منهج جديد" panel.
2. Pick a ~100 MB PDF file.
3. Form label reads "📤 ملف PDF (حد أقصى 150 ميغا)" — confirms
   the new UI rendered.
4. Fill title, group, etc., click "💾 حفظ الكتاب".
5. **Expect:** upload completes (takes ~30 s – 3 min depending on
   the parent's upstream), toast "تم الرفع ✓", book appears in
   the list below.

### B — ~140 MB single-upload should succeed

1. Same flow, ~140 MB file.
2. **Expect:** same outcome.

### C — ~160 MB single-upload should be rejected client-side

1. Same flow, ~160 MB file.
2. **Expect:** immediately after selecting the file or pressing
   save, toast "حجم الملف يتجاوز 150 ميغا" appears. No upload
   begins. Server never receives the request.

### D — Multi-upload ~100 MB each should succeed

1. Pick a folder (or create one), click "+ ارفع أول كتاب".
2. Drop 3 × ~100 MB files into the drop zone.
3. Drop-zone hint reads "الحد الأقصى 150 ميغا لكل ملف، حد أقصى
   10 ملفات".
4. **Expect:** all three accepted client-side, batch upload
   proceeds, each file gets a "✓" in the results panel.

### E — Multi-upload ~160 MB rejected client-side

1. Same flow, one ~160 MB file in the drop.
2. **Expect:** toast `"<filename>" يتجاوز 150 ميغا`. That single
   file is skipped from the batch; others (if any) still
   queued.

### Failure modes to watch for

| Symptom | Likely cause | Fix |
|---|---|---|
| Upload hangs past ~2 min then 502 | Render didn't pick up the new --timeout 300 (the dashboard step was skipped) | Apply the Settings → Start Command change manually per §Render dashboard above |
| Toast still says "50 ميجا" or "20 ميجا" | Browser cache | Hard-refresh (Ctrl+Shift+R) |
| 413 with "150 ميغا" message even for small file | One of the constants regressed | Check `python -c "import app; print(app._BOOKS_V2_MAX_BYTES)"` in Render shell |
| Disk-full errors during upload | Render Postgres plan headroom + the BYTEA write | Owner needs to verify current Render Postgres plan capacity (see `book_size_limits_diagnosis.md` §7) |

---

_Tagged as **v2.9.4**. The smoke test (`scripts/smoke_books_150mb_limit.py`) is part of the change so the limit can't regress unnoticed._
