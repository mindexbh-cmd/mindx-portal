---
description: List recent safety/* tags and roll the branch back to one (interactive)
---

Inspect recent safety tags and offer to roll back. **This is destructive — confirm twice.**

1. **List the last 10 safety tags** sorted newest-first:
   ```bash
   git for-each-ref --sort=-creatordate --format='%(refname:short) %(creatordate:iso) %(subject)' refs/tags/safety/ | head -10
   ```

2. **For each tag, show what would be lost** (`git log <tag>..HEAD --oneline`). One line per commit between the tag and current HEAD.

3. **Ask the user which tag to roll back to.** Do NOT pick one automatically.

4. **Once the user picks**, confirm AGAIN by showing:
   - The exact commands you'll run
   - The list of commits that will be discarded
   
   Wait for explicit "yes go" before proceeding.

5. **Execute the rollback:**
   ```bash
   git reset --hard <chosen_tag>
   # If user wants to push the rollback to prod:
   git push --force-with-lease origin main
   ```
   The `git push --force-with-lease origin main` line is currently in the project's `permissions.deny` list — if it's blocked, surface that to the user and let them handle it manually rather than try to bypass.

6. **Verify.** After the rollback:
   - `git log --oneline -5` — confirm HEAD matches the tag
   - If a push happened, wait 60 s then hit `/api/health` to confirm prod came back

Never use `git reset --hard origin/main` to roll back; it doesn't account for unpushed commits and is in the deny list anyway.
