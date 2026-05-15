---
description: Safe deploy to production with auto-rollback. Usage. /deploy <feature-slug>
argument-hint: <feature-slug>
---

Deploy the current branch to production via `scripts/safe_deploy.py` with full pre-flight checks.

Feature slug: `$ARGUMENTS`

If `$ARGUMENTS` is empty, ask the user for a slug (e.g. `points-board-fixes`) and stop — don't deploy with a placeholder name.

1. **Working tree check.** Run `git status --porcelain`. If anything is uncommitted, abort and show what's dirty.

2. **Run e2e first.** Invoke the `/test` skill (or run `python scripts/run_e2e.py`). If anything fails, abort and surface the failing test. Don't continue.

3. **DB-change detection.** If `git diff origin/main..HEAD` contains any of these patterns, you MUST delegate a review to `data-protector-agent` before proceeding:
   - `ALTER TABLE`
   - `DROP TABLE`
   - `CREATE TABLE`
   - `DELETE FROM`
   - `UPDATE` that lacks a `WHERE`
   - `TRUNCATE`
   - `schema_migrations` insert
   
   If `data-protector-agent` rejects, abort. If it approves-with-conditions, surface the conditions to the user and ask before continuing.

4. **Run safe_deploy.** Execute:
   ```bash
   python scripts/safe_deploy.py --feature $ARGUMENTS
   ```
   This already tags `safety/pre-$ARGUMENTS-<timestamp>`, pushes, polls `/api/health` for up to 5 minutes, runs the smoke e2e against prod, and auto-rolls-back on red.

5. **Report.** Surface the script's exit code, the safety tag name, and the final `/api/health` status. If it rolled back, surface the failure reason from the script's logs.

Don't add features to `safe_deploy.py` from within this command — that script is the single source of truth for the deploy protocol.
