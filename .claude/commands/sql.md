---
description: Run a read-only SELECT against prod or local DB. Usage. /sql <query>
argument-hint: <query>
---

Execute a read-only SQL query through `scripts/db_query.py`.

Query: `$ARGUMENTS`

1. **Refuse writes.** Before passing the query to the script, check that its first non-whitespace token (case-insensitive) is one of `SELECT`, `EXPLAIN`, `PRAGMA`, `WITH`. If not, refuse with:
   > Only SELECT/EXPLAIN/PRAGMA/WITH allowed. For writes, use the agent pipeline (which routes through data-protector-agent).
   
   Do NOT pass `--force-write` to the script under any circumstances inside this command.

2. **Target.** If `DATABASE_URL` is set in the environment, the script auto-targets prod Postgres. Otherwise it falls back to local SQLite at `DB_PATH`. State which one before running.

3. **Run:**
   ```bash
   python scripts/db_query.py "$ARGUMENTS"
   ```
   The script formats as aligned columns by default. The Bash output gets piped back to you.

4. **Format for the user.**
   - If the result fits in ~30 rows, show inline.
   - If larger, show the first 20 rows + the total count, and offer:
     > `Result has <n> rows. Re-run with --csv to export, or refine your query.`

5. **No analytic queries against giant tables.** If the query mentions a known-large table (`attendance`, `student_points_log`, `audit_log`, `books_v2`) without a `WHERE` clause limiting the scan, warn the user before running.
