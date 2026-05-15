---
description: Multi-agent code/UX/perf/security audit aggregated to docs/audits/audit-<ts>.md
---

Run the five most-relevant review agents in parallel and aggregate their verdicts into a timestamped audit file.

1. **Capture context.** What's the scope?
   - If the user gave a scope hint after `/audit` (e.g. "the points page"), use it.
   - Otherwise, default to "the current branch's diff vs main."

2. **Invoke the team.** In a single message with parallel `Agent` calls (5 agents, independent concerns):
   - `data-protector-agent` — DB safety review
   - `performance-watchdog` — response time / memory / queries
   - `arabic-quality-agent` — grammar / terminology / RTL / labels
   - `ui-designer-agent` — palette / spacing / typography / hierarchy
   - `code-architect-agent` — function length / duplication / dead code / type hints

   Each prompt should brief the agent on the scope and request their standard output format.

3. **Aggregate.** Once all five return, write `docs/audits/audit-<YYYYMMDD-HHMMSS>.md` with:
   - Scope (what was reviewed)
   - One section per specialist, verbatim from their report
   - **Aggregated findings table** sorted by severity (critical / high / medium / low), de-duplicated across agents
   - **Top 5 actionable items** for the user

4. **Commit the audit doc** with a `docs(audit): ...` message. Do NOT auto-fix any of the findings — surfacing is the job; fixing is a follow-up the user decides on.

5. **Report.** Path to the audit file + the top 5 actionable items inline.
