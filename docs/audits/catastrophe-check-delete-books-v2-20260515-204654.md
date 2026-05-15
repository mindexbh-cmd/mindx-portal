# Catastrophe-prevention report — "delete the books_v2 table"

**Timestamp:** 2026-05-15 20:46:54 UTC
**Slug:** delete-books-v2
**Reviewer:** catastrophe-prevention-agent (DEMO)

---

## ❌ VERDICT: REJECT — DO NOT proceed

**Categories flagged:** 1 (data loss) + 2 (breaking changes). Both are hard blockers.

---

## Phase 1 — Scan

Proposed change: **drop the `books_v2` table**.

Surface area:
- `books_v2` is a **user-data table**. Currently holds every uploaded book in the library (per CLAUDE.md "Tables" section + `init_db()` at app.py:1477).
- Sibling tables `books_v2_groups`, `books_v2_teachers`, `book_folders` reference `books_v2.id` via foreign-key-like usage.
- `346` literal references to `books_v2` in `app.py` (grep count).

Applicable categories: **1 (data loss)** and **2 (breaking changes)**.

---

## Phase 2 — Deep check

### Category 1 — Data loss (HARD VIOLATION)

- `DROP TABLE books_v2` would irreversibly delete every uploaded book row + its metadata (title, file_hash, folder_id, uploader, timestamps, …).
- The PDF binaries live on the persistent disk at `/var/data/books_v2/<sha256>.pdf` — those remain, but become orphaned and unreachable without the DB rows that index them.
- The sibling tables `books_v2_groups` and `books_v2_teachers` carry the assignment rules (who can see which book). They'd also need dropping, compounding the data loss.
- CLAUDE.md "Data safety" rule, verbatim: **"NEVER use `DROP TABLE` on any user-data table in `app.py`. Every deployment must leave existing rows 100% intact."**

**Verdict: REJECT on Category 1 alone.** No safety tag, no backup, no rollback plan exists in the proposed change.

### Category 2 — Breaking changes (HARD VIOLATION)

`grep -c "books_v2" app.py` → **346 occurrences**. Every one of them is a callsite that would 500 immediately after a DROP:

- Routes: `/api/books`, `/portal/parent-hub/books`, `/admin/books`, `/api/book-folders`, the curriculum-library viewer, etc.
- Templates: `PORTAL_PARENT_HUB_HTML` card "كتب المنهج", the books library page.
- Migrations: the `books_v2_*` migration tags would still try to ALTER a non-existent table on every cold start.

Every parent, teacher, and admin who opens the books surface would see a 5xx. This is the single largest dependency surface in the codebase after `students` and `attendance`.

**Verdict: REJECT on Category 2.** No replacement designed, no deprecation period, no documentation of the breaking change.

### Categories 3, 4, 5 — N/A

Not applicable to this proposed change (no auth/perf/UX surface changes directly proposed). But Category 5 would surface a downstream UX disaster if the change shipped — the books card would just fail.

---

## Always-on scan results

| Check | Result |
|---|---|
| Secret scan | clean |
| `@login_required` count | 366 (baseline preserved) |
| `/api/health` | green (last deploy) |
| `/login` | 200 |
| `/portal/parent-hub` anonymous | 302 → /login (correct) |
| Test users intact | yes (4 `*_test` accounts) |
| Render Starter sanity | nothing in this change touches infra |

---

## Required to unblock

1. **Drop the request entirely** — `books_v2` is load-bearing. There's no safe path to delete it.
2. **OR, if the goal is to migrate to a new schema**, follow the **Expand-Migrate-Contract** pattern (CLAUDE.md ADR-007):
   - **Expand**: add the new table `books_v3` alongside `books_v2`, mirror writes from new code paths.
   - **Migrate**: dual-write for one deploy cycle. Add a migration that copies rows. Update reads to prefer the new table with the old one as fallback.
   - **Contract**: only after every callsite is migrated AND the metric "reads from books_v2" is zero for ≥ 1 week, can `books_v2` be retired. The retirement itself uses a soft-flag, not a DROP — leave the table empty but extant for one more release cycle as a safety net.
3. **OR, if the goal is to hide / hard-disable the books feature**, set the route handlers to return 410 Gone or hide the UI surface via a feature flag — keep the table.

## Suggested alternative

Run `Agent({subagent_type: "database-architect-agent", prompt: "Plan the books_v2 retirement using Expand-Migrate-Contract. Discovery only — produce docs/migrations/books-v2-retirement-discovery.md and STOP for approval."})` before any code change.

## Operator override (last resort)

To bypass this REJECT, the operator must:
1. Acknowledge the specific risks in this report.
2. Include the literal tag `override:catastrophe:books_v2_drop` in the eventual commit message.
3. The override + reason will be logged to `docs/memory/REJECTED_CHANGES.md` for posterity.

The Bash hook (`.claude/hook_scripts/catastrophe_block.py`) will block any `DROP TABLE books_v2` command until the override is in place.

---

**Logged to:** `docs/memory/CATASTROPHE_LOG.md` (REJECT row) + `docs/memory/REJECTED_CHANGES.md` (full breakdown).
