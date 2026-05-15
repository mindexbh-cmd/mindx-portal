# Rejected changes log

Append-only log of every REJECT verdict from `catastrophe-prevention-agent`. Full breakdown of the risks that were prevented — institutional memory of "what we almost shipped that would have hurt us."

## Format

Each entry is a sub-section under the date:

```
### YYYY-MM-DD HH:MM — <slug>

**Proposed change:** <what the operator asked to do>

**Verdict:** ❌ REJECT

**Categories flagged:**
- Category X (<name>): <specific risk + code reference>
- Category Y (<name>): <specific risk + code reference>

**Required remediation:**
- <item>
- <item>

**Suggested alternative:** <approach>

**Outcome:** <operator dropped change | applied remediation and re-ran | overrode with explicit tag>

**Audit file:** `docs/audits/catastrophe-check-<slug>-<ts>.md`
```

## Log

### 2026-05-15 20:46 — delete-books-v2 (DEMO)

**Proposed change:** delete the `books_v2` table.

**Verdict:** ❌ REJECT

**Categories flagged:**
- Category 1 (data loss): `DROP TABLE books_v2` violates CLAUDE.md "Data safety" rule. PDFs on `/var/data/books_v2/` would be orphaned. Sibling tables `books_v2_groups` / `books_v2_teachers` lose their FK target.
- Category 2 (breaking changes): `grep -c "books_v2" app.py` → **346 callsites**. Every books surface (parent-hub card, admin library, curriculum viewer, /api/books, /api/book-folders) would 500 immediately after a DROP.

**Required remediation:**
- Drop the request, OR follow the **Expand-Migrate-Contract** pattern (CLAUDE.md ADR-007).
- If the goal is to hide the books feature, set route handlers to 410 Gone or feature-flag the UI — keep the table.

**Suggested alternative:** invoke `database-architect-agent` for a books_v2 retirement plan (discovery → expand → migrate → contract). Never DROP — soft-disable instead.

**Outcome:** demo entry, no actual change made.

**Audit file:** `docs/audits/catastrophe-check-delete-books-v2-20260515-204654.md`

---

*Subsequent rejections will be logged here chronologically. Entries are append-only — never edit historical decisions.*
