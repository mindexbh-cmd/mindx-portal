---
description: Snapshot the production DB to backups/ with integrity verification
---

Take a timestamped backup of the production Postgres DB.

1. **Verify the target is prod.** Inspect `$DATABASE_URL`. It must contain `oregon-postgres.render.com` (or whatever the current Render Postgres host is — currently `dpg-d7jl937lk1mc73aaal40-a.oregon-postgres.render.com`). If `DATABASE_URL` is unset OR points at localhost, abort with a clear "I refuse to back up a local DB to the prod backups folder — set DATABASE_URL first" message.

2. **Take the snapshot.**
   ```bash
   DATABASE_URL=$DATABASE_URL python scripts/db_backup.py
   ```
   The script produces `backups/mindx-<ts>.sql` for Postgres or `.db` for SQLite.

3. **Verify integrity.**
   - For `.sql` (Postgres dump): grep for the trailing `-- PostgreSQL database dump complete` marker, plus check the file size is non-trivial (> 100 KB for a populated DB).
   - For `.db` (SQLite): open it via `python scripts/db_query.py --tables` with `DB_PATH=<backup>` to confirm tables are present.

4. **Report.** Path to the backup file, byte size, and a one-line "verified ok" or "verification FAILED" verdict.

Backups are gitignored (`backups/` in `.gitignore`) — they won't get committed.
