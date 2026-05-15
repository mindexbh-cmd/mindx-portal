---
description: Multi-viewport screenshot capture of a page. Usage. /screenshots <path>
argument-hint: <path>
---

Capture a page at three viewports (360, 768, 1280) using Playwright + the admin_test user.

Page path: `$ARGUMENTS` (e.g. `/dashboard`, `/points/board`, `/portal/parent-hub`)

If `$ARGUMENTS` is empty, ask for the path and stop.

1. **Verify the dev server is up** on port 5000 (same probe as `/test`). If not, ask the user to start it.

2. **Write a one-off Playwright script** under `scripts/_tmp_screenshots.py` (gitignored; ephemeral). It must:
   - Import `BrowserSession` from `scripts/auto_test.py`
   - For each viewport size `[(360, 800), (768, 1024), (1280, 800)]`:
     - Launch a new context with `viewport={"width": w, "height": h}`
     - Use the existing `BrowserSession.login_as("admin")` to authenticate
     - Navigate to `$ARGUMENTS`
     - Screenshot to `docs/screenshots/<slug>-<width>px-<ts>.png` (`<slug>` = `$ARGUMENTS` with `/` replaced by `_`)
   - Print each screenshot path

3. **Run:** `python scripts/_tmp_screenshots.py`

4. **Delete the temp script** after the run.

5. **Report.** Three screenshot paths, one per viewport, plus any console errors or 5xx flagged by the session.

`docs/screenshots/` is committed (it's not in the gitignored `scripts/screenshots/` path), so if these are reference shots for a doc, that's fine. If they're throwaway, the user can delete them manually.
