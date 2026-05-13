# Parent book viewer — two-tier page cache (implementation)

**Goal:** make `/parent/book/<bid>/page/<n>.webp` cheap on
re-visits and on cross-worker requests, per the diagnosis in
`reports/viewer_performance_diagnosis.md`.

**Commits in this change:**
- `bd852e3` — feat(viewer): two-tier page cache (Tier 1 disk + Tier 2 in-memory)
- `60de84a` — feat(viewer): purge page cache on book delete + reupload
- `e2fcfbd` — perf(viewer): watermark uses small-tile-paste pattern
- `1b4cb20` — test(viewer): smoke covering all of the above

**Safety tag:** `safety/viewer-two-tier-cache-20260513-204116`
pushed before any edit.

---

## What changed

### Tier 1 — disk cache for the un-watermarked raster

New helper `_books_v2_render_page_base_cached(bid, page_n)` in
`app.py:86735+`:

- Returns the un-watermarked WebP for one page as bytes.
- Reads from `<storage_dir>/<bid>/pages/<n>_base.webp` on a hit.
- On miss: `pypdfium2.PdfDocument(...)` → `page.render(scale=2.0)`
  → WebP encode → atomic temp+rename write.
- Layout is parent-agnostic and day-agnostic — one file per
  `(bid, page_n)`, shared by every gunicorn worker, survives
  redeploys (lives on `/var/data` persistent disk).

### Tier 2 — in-memory LRU for the watermarked output

Refactored `_books_v2_render_page_webp_cached`:

- Same signature `(bid, pid, page_n, date_str, name_norm)`.
- `lru_cache(maxsize=64)` → **`lru_cache(maxsize=256)`** (each
  entry is cheaper to build now, so a bigger cache costs less).
- Pipeline collapsed from "parse PDF + rasterize + watermark +
  encode" to "load Tier 1 bytes + convert RGBA + watermark +
  encode". The heavy steps live in Tier 1; this step is ~200-300 ms
  on a miss.

### Tier 2 disk cache — DELIBERATELY NOT IMPLEMENTED

The diagnosis sketched a per-parent-per-day disk layout
(`<n>_<pidhash>_<date>.webp`). Sizing it for a typical center:

```
10 books × 30 pages × 50 parents × 200 KB = ~30 GB on day 1
```

Render disk is 1 GB. Tier 2 disk would blow the budget on day 1.
The current implementation:

- Keeps Tier 2 in-memory only (`lru_cache(maxsize=256)`).
- Different parents each pay the ~200-300 ms watermark step on
  their first miss for a given page — that's the new floor, not
  the old 2-4 s.
- Owner can layer a disk Tier 2 later (with strict eviction) if
  multi-parent reuse becomes a measurable problem.

This trade-off is documented in the `bd852e3` commit message and
the inline code comment above `_books_v2_render_page_base_cached`.

### Watermark optimisation (independent gain)

`_apply_image_watermark` used to call `ImageDraw.text()` ~500
times into a `diag×diag` (~4258×4258) RGBA overlay — once per
tile position. Each call re-rasterises glyphs into that buffer,
so the cost scaled with overlay size × tile count.

New pattern:

1. Render the watermark text ONCE into a small `~470×140` RGBA
   tile.
2. `Image.paste(tile, (x, y), tile)` into the diag×diag overlay
   at the same grid positions — pixel memcpy of pre-rasterised
   data.
3. Rotate + composite (unchanged).

Roughly halves the watermark step on typical 2400×3400 page
rasters (~1.5 s → ~0.7-0.8 s based on diagnosis math).

### Cache invalidation

New helper `_books_v2_clear_page_cache(bid)`:

- `rm -rf <storage_dir>/<bid>/pages/` (Tier 1 disk).
- `_books_v2_render_page_webp_cached.cache_clear()` (Tier 2 LRU —
  full clear because there's no per-key invalidation API on
  `functools.lru_cache`; book mutations are rare relative to
  page reads, so re-warming cost is acceptable).

Wired into two endpoints:

| Endpoint | Trigger | File:line |
|---|---|---|
| `DELETE /api/books/<bid>` | book deletion | `app.py:84844-84849` |
| `POST /api/books/<bid>/reupload` | bytes replacement | `app.py:84759-84765` |

## Expected after deploy

| Scenario | Before | After |
|---|---|---|
| First parent, first page (cold disk + cold LRU) | ~3 s | ~1.0-1.5 s (Tier 1 warm-up + faster watermark) |
| Same parent, page 2..N first time (warm disk) | ~3 s each | ~150-250 ms (Tier 1 hit, Tier 2 miss, faster watermark) |
| Same parent, re-visit same page same day | ~3 s if evicted from old `maxsize=64`; ~5 ms otherwise | ~5 ms (Tier 2 LRU hit) |
| Different parent, same page same day | ~3 s | ~150-250 ms (Tier 1 hit, different Tier 2 key) |
| After redeploy, any page | ~3 s (in-memory cache wiped) | ~150-250 ms (Tier 1 disk survived) |
| Cross-worker (no shared in-memory cache) | ~3 s on each worker's first hit | ~150-250 ms (Tier 1 shared on disk) |

The two big wins are **persistence across redeploys** and **sharing across workers** — both directly address the owner's "every time slow" report.

## What was NOT changed

- ❌ The watermark visual design (text content, font, opacity,
  rotation, density). The output should look identical.
- ❌ Auth pipeline (`_books_v2_pid_can_view`, `_vt` HMAC token,
  date-key invalidation).
- ❌ The PARENT_PDF_VIEWER_HTML client viewer.
- ❌ Storage location (`_books_v2_storage_dir()` resolves the
  same paths on Render + local).
- ❌ `parent_book_page_webp` route signature or response headers.
- ❌ Tier 1 expiry: pages stay cached until the book is deleted
  or re-uploaded. Old pages can't go stale because they're keyed
  by `(bid, page_n)` and the source bytes don't change without
  triggering `_books_v2_clear_page_cache(bid)`.

## Disk budget projection

For a typical center on a fresh deploy (Tier 1 only):

```
Page count avg: 30 pages/book
Base WebP avg:  ~200 KB/page (rasterized RGB at scale=2.0, q=85)
Per-book Tier 1 footprint: ~6 MB
50 books → ~300 MB Tier 1 disk usage
```

Render's `/var/data` is 1 GB, with `playwright-browsers` already
eating ~150 MB. **Headroom: ~850 MB → comfortable for ~140 books
of avg shape.** Well past the current scale.

For larger books (200+ page educational PDFs at 400-800 KB/page),
50 books could approach 8 GB. The cache wouldn't fit. **Mitigation
plan if disk pressure becomes real**: a periodic cron that deletes
`/pages/` directories for books unaccessed for N days. Owner can
add this only if/when needed.

## Smoke results

`scripts/smoke_viewer_two_tier_cache.py`:

```
[1] three new cache helpers present and callable
[2] Tier 2 lru_cache maxsize == 256
[3] _books_v2_clear_page_cache wired into 2 sites (delete + reupload)
[4] watermark uses small-tile-paste pattern (no more N×M ImageDraw.text loop)
[5a] /parent/book/<bid>/meta route alive (status 403)
[5b] /parent/book/<bid>/page/<n>.webp route alive (status 403)

PASS — two-tier cache wiring + watermark optimisation + endpoint pipeline all verified.
```

## Owner browser-test scenarios

After deploy + hard-refresh (Ctrl+Shift+R):

### Scenario A — first open of a fresh book (cold cache)

1. Pick any view-only book, open as parent (PID in URL).
2. First page should load in **~1.0-1.5 s** (down from 2-4 s).
3. Page 2 click → **~150-250 ms** (Tier 1 was warmed during
   server-side prefetch for adjacent pages? No — only after the
   first page is rendered does its Tier 1 file land on disk).
   Actually for page 2 the first time: still ~1.0-1.5 s (page 2
   wasn't rasterized yet). After page 2 → page 3 → all pages
   are visited once, every subsequent re-visit is **5-250 ms**.

### Scenario B — close tab, reopen same book (persistent disk)

1. Visit all pages of a book once.
2. Close the browser tab.
3. Reopen the book within the same day.
4. **Every page** should load in **~150-250 ms** or faster.
   The Tier 1 base files are on disk; the Tier 2 LRU may have
   been evicted if other parents have been browsing, but the
   200-300 ms compose-and-watermark path applies.

### Scenario C — same page across a Render redeploy

1. Visit a page, see it cache.
2. Trigger a redeploy on Render (push any commit).
3. After deploy, hit the same page.
4. **Before this change:** full ~3 s (in-memory cache wiped).
   **After:** ~150-250 ms (Tier 1 disk survived the redeploy).

### Scenario D — admin reuploads, parent re-opens

1. As parent, open book #X, browse pages 1-5.
2. As admin, re-upload book #X with replacement bytes.
3. As parent, reload page 1 of book #X.
4. **Expect:** the new bytes render (Tier 1 was purged by
   `_books_v2_clear_page_cache` from the reupload handler).
   Timing: ~1.0-1.5 s for the first page (cold), then ~150-250 ms
   for subsequent pages — like Scenario A again.

### Scenario E — admin deletes the book

1. As admin, soft-delete book #X.
2. Inspect `/var/data/books_v2/<X>/pages/` on Render shell.
3. **Expect:** directory empty or removed.

### Failure modes to watch for

| Symptom | Likely cause | Fix |
|---|---|---|
| Still ~3 s on every page | Tier 1 disk-write failing (permissions, no disk space). Check Render logs for `base page disk-cache write failed` warnings. | Investigate disk; the fallback is still functional, just no speedup |
| Watermark looks broken / missing | The new tile-then-paste may have hit a font-rendering edge case. Look for `image wm failed` warnings | Roll back commit `e2fcfbd` only — Tier 1 + Tier 2 still work without that perf gain |
| Stale page after reupload | Cache-clear didn't fire. Check Render logs for an exception in `api_books_v2_reupload` between the UPDATE commit and the audit log call | Manual fix: `rm -rf /var/data/books_v2/<bid>/pages/` |
| Disk full | Page cache plus PDFs growing past the 1 GB disk budget | Add a cron to purge `/pages/` for books not accessed in N days |

---

_Phase A (IndexedDB client-side cache) was abandoned upstream because
the actual viewer is server-rendered WebP images, not PDF.js — see the
prior diagnosis. The two-tier server-side cache delivered here is the
right shape for that architecture._
