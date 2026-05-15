---
description: Run the full e2e test suite against the local dev server
---

Verify the local dev server is reachable, then run the e2e suite.

1. Check whether something is listening on port 5000:
   ```bash
   python -c "import socket; s=socket.socket(); s.settimeout(1);
   exit(0 if s.connect_ex(('127.0.0.1',5000))==0 else 1)"
   ```
   If nothing is listening, tell the user to start the server with `python app.py` in another terminal, then stop. Do NOT auto-start the server — the user should own the server's lifecycle.

2. If port 5000 is up, run:
   ```bash
   python scripts/run_e2e.py
   ```

3. Parse the output and report:
   - Pass/fail counts
   - Failing tests (if any) with their screenshot paths
   - Any 5xx responses or console errors flagged in the runner output

Keep the report concise — one line per test, plus a summary footer. If a test failed, surface its screenshot path so the user can click straight to it.
