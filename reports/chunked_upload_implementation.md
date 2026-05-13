# Chunked upload with resume — verification (v2.9.5)

**Goal:** replace the single-request `/api/books/upload-multi`
(which silently fails on slow uplinks against the 300 s gunicorn
ceiling) with a three-phase chunked pipeline that survives both
gunicorn timeouts and browser disconnects.

The legacy `/api/books/upload-multi` endpoint stays mounted as a
fallback — only the modal driver was migrated.

## Commits (all on `main`)

| # | Commit | What it added |
|---|---|---|
| C1 | (read-only investigation — no commit) | confirmed gunicorn 300 s ceiling + single-fetch shape |
| C2 | `b903863` | server endpoints: init / chunk / finalize / status + `upload_sessions` table |
| C3 | `d246444` | boot-time sweep of expired sessions + orphan chunk dirs |
| C4 | `ca0ec76` | `ChunkedUploader` JS class with per-chunk retry + resume |
| C5 | `8c41d59` | per-file progress bars + Arabic status pills in modal |
| C6 | `6ea82bd` | resume banner on modal open (`bkUpRenderResumeBanner`) |
| C7 | `db098a1` | `bkUpSubmit` drives `ChunkedUploader` sequentially |
| C8 | `f935624` | `scripts/smoke_chunked_upload.py` — 8 invariants |
| C9 | this report | verification + browser test scenarios |

**Safety tag:** `safety/chunked-upload-20260513-214051` —
pushed before any edit. Roll-back command:
```
git reset --hard safety/chunked-upload-20260513-214051
```

## Architecture

```
   ┌───────────────────────────────────────────────────────────┐
   │  Browser (bk-up-modal)                                    │
   │                                                           │
   │  bkUpSubmit()                                             │
   │    └─ uploadOne(idx)                                      │
   │         └─ new ChunkedUploader(file, {...}).start()       │
   │                ├─ _tryResume()  ──── GET /status ─────►   │
   │                ├─ _init()       ──── POST /init   ────►   │
   │                ├─ _sendChunk(0..N) × N (5 MB each)        │
   │                │     POST /chunk  with FormData(chunk)    │
   │                │     ↑ per-chunk retry (1s, 2s, 3s)       │
   │                └─ _finalize()    ── POST /finalize ────►  │
   └───────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌───────────────────────────────────────────────────────────┐
   │  Flask + gunicorn (--timeout 300)                         │
   │                                                           │
   │  /api/books/upload/init                                   │
   │     • validates filename + size + chunk count             │
   │     • INSERT upload_sessions{user_id, total_size, ...}    │
   │     • returns {upload_id, chunk_size}                     │
   │                                                           │
   │  /api/books/upload/chunk                                  │
   │     • verifies session ownership + not expired            │
   │     • writes /var/data/chunks/<upload_id>/<idx>.bin       │
   │       atomically (temp + os.replace)                      │
   │     • UPDATE upload_sessions.received_chunks JSON         │
   │     • returns {received_count, missing_chunks}            │
   │                                                           │
   │  /api/books/upload/finalize                               │
   │     • verifies all chunks received                        │
   │     • reassembles into BytesIO (ordered 0..N)             │
   │     • magic-byte sniff for MIME                           │
   │     • INSERT books_v2 row with file_data=BYTEA            │
   │     • inherit_folder_groups: copies folder→groups         │
   │     • rmtree(<upload_id>) + DELETE upload_sessions row    │
   │     • returns {ok, book_id, inherited_groups}             │
   │                                                           │
   │  /api/books/upload/status                                 │
   │     • returns {received_chunks: [...], expires_at}        │
   │     • used by client to resume after disconnect           │
   └───────────────────────────────────────────────────────────┘
                                │
                                ▼
   ┌───────────────────────────────────────────────────────────┐
   │  Persistent disk: /var/data/chunks/<upload_id>/<n>.bin    │
   │  (falls back to ./data/chunks/ if /var/data not writable) │
   └───────────────────────────────────────────────────────────┘
```

## Why this works

| Failure mode (was) | Old behavior | New behavior |
|---|---|---|
| 150 MB file on 3 Mbps uplink | ~400 s upload, gunicorn kills at 300 s → 502 | each 5 MB chunk needs ~13 s, well inside 300 s; total takes the same wall-clock time but never trips the ceiling |
| Wi-Fi drops mid-upload | start over, lose all progress | open modal again → banner shows "📁 يوجد رفع غير مكتمل: <filename> (45% مرفوع) [استئناف] [إلغاء]". Re-pick same file → `_tryResume` populates `receivedChunks`, only missing chunks re-uploaded |
| Browser tab closed | session + chunks orphaned forever | C3 boot sweep + per-finalize sweep + 1-hour TTL → cleaned up automatically |
| Single chunk transmission glitch | whole upload fails | C4 retry loop: 3 attempts at 1s/2s/3s backoff per chunk; user sees nothing |

## Configuration knobs

All server-side, all in `app.py`:

| Constant | Value | Why |
|---|---|---|
| `_CHUNKED_CHUNK_SIZE` | 5 MB | sweet spot for 13 s/chunk on 3 Mbps uplink |
| `_CHUNKED_CHUNK_HARD_CAP` | 6 MB | server-side hard reject; matches `multipart/form-data` overhead headroom |
| `_CHUNKED_MAX_TOTAL_BYTES` | 150 MB | mirrors `_BOOKS_V2_MULTI_MAX_BYTES`; can't allow a chunked upload to exceed the single-shot limit |
| `_CHUNKED_MAX_CHUNKS` | 30 | 30 × 5 MB = 150 MB exactly; prevents pathological "1-byte chunk × 1M times" |
| `_CHUNKED_SESSION_TTL_SEC` | 3600 (1 hour) | a 150 MB upload on 3 Mbps takes ~400 s; 1 hour covers retries, disconnect grace, and a moderate user pause |

## Owner browser-test scenarios

Hard-refresh `/admin/books` after deploy (Ctrl+Shift+R) — service
worker may keep the old JS otherwise.

### A — Happy path, single small file (~10 MB)

1. `/admin/books` → pick or create a folder.
2. "+ ارفع أول كتاب" → modal opens, banner is hidden.
3. Drop a ~10 MB PDF.
4. Click "📤 رفع الكل".
5. **Expect:** progress pill cycles
   `🔧 جاري التحضير...` → `⬆️ يرفع...` →
   `🧩 يجمع الأجزاء...` → `✅ تم`.
   Bar fills 0 → 100 %. Result panel shows
   "تم رفع 1 ملف بنجاح • فشل 0" with green `✅ <title>`.
   The book appears in the folder.

### B — Happy path, single large file (~140 MB)

1. Same flow, ~140 MB PDF.
2. **Expect:** progress takes ~5 min on a 25 Mbps uplink;
   bar advances smoothly across all chunks. Final outcome
   identical to scenario A.
   The book appears with the right size.

### C — Disconnect mid-upload + resume

1. Pick a ~50 MB file, start upload.
2. After ~40 % progress, kill the Wi-Fi (or open DevTools →
   Network → "Offline").
3. **Expect:** the progress pill flips to `❌ فشل`, the result
   panel shows "تم رفع 0 ملف بنجاح • فشل 1" with the error
   message ("Failed to fetch" or similar).
4. Restore the network. Close the modal. Re-open it via
   "📤 رفع كتب".
5. **Expect:** yellow banner appears at the top of the modal:
   "📁 يوجد رفع غير مكتمل: <filename> (≈40% مرفوع)
   [استئناف] [إلغاء]".
6. Click "استئناف" → toast says "اختاري نفس الملف لاستئناف الرفع".
7. Drop the SAME file again (same name + size + lastModified
   are what the resume key uses).
8. **Expect:** the upload skips already-uploaded chunks
   (pill flashes `↩️ استئناف...`) and continues from ~40 %.

### D — Three files at once, all small

1. Drop three ~5 MB files into the modal.
2. Set distinct titles, click "📤 رفع الكل".
3. **Expect:** files upload **sequentially**, one at a time
   (not in parallel — by design, to keep gunicorn workers
   free for other tenants). Each row's pill + bar updates
   independently. Result panel lists three ✅ rows.

### E — One file too large

1. Try to drop a ~200 MB file.
2. **Expect:** the file is rejected client-side **before**
   any chunk is sent — toast "<filename>" يتجاوز 150 ميغا.
   No `/api/books/upload/init` request fires.

### F — Cancel mid-upload + dismiss

1. Start a ~50 MB upload, let it reach ~30 %.
2. Close the modal (clicks "إلغاء" on the modal acts row).
3. Re-open it.
4. **Expect:** resume banner appears with that file's
   filename + ~30 %.
5. Click "إلغاء" on the banner.
6. **Expect:** banner disappears, localStorage entry is
   gone, the server session keeps existing until the
   1-hour TTL sweep (this is intentional — we don't want
   to delete server state from a UI action; the sweep is
   the safety net).

## Failure modes to watch for

| Symptom | Likely cause | Fix |
|---|---|---|
| `/api/books/upload/init` returns 500 with "/var/data unwritable" | persistent disk not mounted | Render dashboard → disk attached at /var/data |
| `/api/books/upload/chunk` returns 413 with "حجم الجزء يتجاوز 6 ميغا" | client posted a chunk larger than the hard cap | only happens if someone bypasses ChunkedUploader; the bundled client never does |
| Resume banner shows phantom entry | server session expired (>1 h) but localStorage didn't sync | banner's status fetch returns `{ok:false}` → entry pruned silently on next render |
| Progress bar jumps to 100 % immediately and then "fails" | `_init` rejected the file (size > 150 MB / bad chunk count); error caught by `onError` so the bar fills but the pill flips to ❌ | check `bk-up-result` panel for the Arabic error string |
| Two tabs uploading the same file → only one wins | `_resumeKey` is name+size+lastModified, so both tabs share state | won't break anything — the server just rejects whichever tries to write a chunk to a closed session; the user sees ❌ in the loser tab |

## What was NOT changed

Per the brief's "DO NOT" rules:

- ❌ `/api/books/upload` (single-shot, used by the legacy edit flow) — untouched.
- ❌ `/api/books/upload-multi` route — still mounted as a fallback; only the modal handler stopped calling it.
- ❌ `_BOOKS_V2_MAX_BYTES` / `_BOOKS_V2_MULTI_MAX_BYTES` — both still 150 MB (set in v2.9.4).
- ❌ Cloudinary path — no chunked uploads go through Cloudinary; they all land in BYTEA `books_v2.file_data` exactly like the single-shot path.
- ❌ Auth helpers (`_can_manage_books`, `_books_v2_pid_can_view`).
- ❌ Render's gunicorn `--timeout 300` — still 300 s; chunked uploads make this irrelevant for the upload itself, but it's still load-bearing for finalize's reassemble step.

## Smoke verification (`scripts/smoke_chunked_upload.py`)

```
[1] all 4 chunked-upload endpoints wired:
    /api/books/upload/init, /chunk, /finalize, /status
[2] all 5 chunked-upload constants at expected values
[3] upload_sessions table present with all 10 expected columns
[4] upload_sessions registered in _TBL_AUDIT_FEATURE:
    ('جلسات الرفع المُجزَّأ', 'مكتبة المناهج')
[5] ChunkedUploader class + all 5 prototype methods in served HTML
[6] per-file progress UI elements + mutators present (8 markers)
[7] resume-detection elements + Arabic banner copy present (7 markers)
[8] bkUpSubmit drives ChunkedUploader sequentially (4 markers);
    legacy /upload-multi route intact as fallback

PASS — chunked upload (v2.9.5) is wired end-to-end.
```

---

_Tagged as **v2.9.5**. Roll-back command if anything misbehaves
in production:_

```
git reset --hard safety/chunked-upload-20260513-214051
git push --force-with-lease origin main  # ⚠ owner-only
```
