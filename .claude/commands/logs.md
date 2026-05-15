---
description: Pull recent Render production logs filtered by keyword. Usage. /logs <keyword>
argument-hint: <keyword>
---

Pull the last hour of production logs filtered by a keyword.

Keyword: `$ARGUMENTS` (if empty, pull all logs from the last hour without filtering)

1. Verify the three Render env vars are set: `RENDER_API_KEY`, `RENDER_SERVICE_ID`, `RENDER_OWNER_ID`. If any are missing, tell the user where to set them and show the dashboard URL fallback — don't try to proceed.

2. Run:
   ```bash
   python scripts/get_logs.py --since 1h --keyword "$ARGUMENTS"
   ```

3. Show the last **50 matching lines** with timestamps. If there are more than 50, mention the total match count and tell the user to refine the keyword or run the script directly with `--limit` for the full set.

4. **Highlight errors/warnings.** Scan the output for lines containing any of:
   - `ERROR`, `CRITICAL`, `FATAL`
   - `Traceback`, `Exception:`, `psycopg2.errors`
   - `[books-v2] ⚠`, `orphan`, `OOM`
   - HTTP status `5xx`
   
   Prefix highlighted lines with `>>` in your report.

5. **Offer deploy-watcher.** If any errors found, ask the user whether to:
   - Tail more logs (`/logs <keyword> --since 6h`)
   - Roll back to the last safety tag (`/rollback`)
   - Investigate a specific endpoint (`/sql ...`)
