---
description: Run the quick + deep health probes against prod (or local) and format the result
---

Probe the app's health endpoints and surface a per-subsystem report.

1. **Target.** If the user supplied a URL after `/health`, use it. Otherwise default to prod: `https://mindx-portal-1.onrender.com`.

2. **Quick probe.**
   ```bash
   curl -s -m 10 <base>/api/health
   ```
   Expected: `{"ok": true, "checks": {"db": {...}, "disk": {...}}, "ts": ...}`. 503 = something is down.

3. **Deep probe.**
   ```bash
   curl -s -m 30 <base>/api/health/deep
   ```
   Returns row counts for every critical table + books storage status.

4. **Format the output.** Per-subsystem, one line each:
   - `db` (kind=pg/sqlite, ok/error)
   - `disk` (scratch write, ok/error)
   - For deep probe: `users`, `students`, `student_groups`, `attendance`, `lessons_log`, `books_v2`, `taqseet`, `student_payments` row counts + ok/error
   - `books_storage` (dir path + writable yes/no)

5. **Red-flag failures.**
   - Any subsystem with `ok=false` → print `🚨 <subsystem>: <error>` (use just text; no emoji-decorations in the report unless the user has emoji on)
   - 5xx response → loud failure banner
   - Slow response (> 5 s for quick, > 30 s for deep) → flag as performance concern even on success
