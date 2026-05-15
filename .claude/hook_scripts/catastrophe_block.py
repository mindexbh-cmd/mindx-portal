"""PreToolUse hook — blocks the most dangerous Bash patterns until /check approves.

Reads the tool-call JSON on stdin. If the command isn't a Bash invocation
matching the catastrophe pattern set, exits 0 with empty JSON (no-op).
Otherwise emits a deny verdict pointing the operator at `/check`.

Override: include the literal string `override:catastrophe:` in the command
itself (e.g. inside a comment) to bypass — gives a single deliberate path
out for the operator when they're sure.

Categories blocked here are the SUBSET of catastrophe-prevention checks
that are realistic to detect from a Bash command string alone. The full
catastrophe agent runs via /check for everything else.
"""
from __future__ import annotations
import json
import re
import sys


# Patterns that always warrant a stop-and-check. Designed to err on
# the side of false positives — the operator can paste an override
# tag to proceed if they're certain.
DANGEROUS_PATTERNS = [
    # Category 1 — data loss
    (r"\bDROP\s+TABLE\b",
     "Category 1 (data loss): DROP TABLE — confirms catastrophe-prevention check"),
    (r"\bTRUNCATE\b",
     "Category 1 (data loss): TRUNCATE — confirms catastrophe-prevention check"),
    (r"\bDELETE\s+FROM\s+\w+(?:\s+WHERE\b)?",
     None),  # special-cased below — only block DELETE without WHERE
    (r"\bALTER\s+(?:TABLE\s+\w+\s+)?(?:ALTER|MODIFY|RENAME)\s+COLUMN\b",
     "Category 1 (data loss): ALTER COLUMN type/rename — use Expand-Migrate-Contract"),

    # Filesystem catastrophes
    (r"\brm\s+-rf\s+(?:/|~|\$HOME|\.|\*|app\.py|app/|docs/|scripts/)",
     "Filesystem catastrophe: rm -rf on sensitive paths"),

    # Git catastrophes — match `--force` as a STANDALONE flag (followed by
    # whitespace or end-of-string), so `--force-with-lease` is allowed.
    (r"\bgit\s+push\s+.*--force(?:\s|$)",
     "Git catastrophe: push --force without --force-with-lease"),
    (r"\bgit\s+reset\s+--hard\s+origin/(main|master)\b",
     "Git catastrophe: reset --hard origin/main wipes local work"),
    (r"\bgit\s+filter-(repo|branch)\b",
     "Git catastrophe: history rewriting"),

    # Cloud / DB direct catastrophes
    (r"\bdropdb\b",
     "Category 1: dropdb"),
    (r"\bpg_(?:dump|restore).*--clean\b",
     "Category 1: pg_restore --clean drops objects first"),
]

OVERRIDE_TAG = "override:catastrophe:"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return 0

    cmd = (data.get("tool_input", {}) or {}).get("command", "") or ""
    if not cmd:
        print("{}")
        return 0

    # Operator opt-out: explicit override tag in the command itself.
    if OVERRIDE_TAG in cmd:
        print("{}")
        return 0

    issues: list[str] = []
    for pat, msg in DANGEROUS_PATTERNS:
        m = re.search(pat, cmd, flags=re.IGNORECASE)
        if not m:
            continue
        # Special case: DELETE FROM is fine if it has a WHERE clause.
        if pat == r"\bDELETE\s+FROM\s+\w+(?:\s+WHERE\b)?":
            # Re-check: does the same statement carry a WHERE?
            if re.search(r"\bDELETE\s+FROM\s+\w+\s+WHERE\b", cmd, re.IGNORECASE):
                continue
            issues.append(
                "Category 1 (data loss): DELETE FROM without WHERE")
            continue
        if msg:
            issues.append(msg)

    if not issues:
        print("{}")
        return 0

    reason = (
        "catastrophe-prevention hook: "
        + "; ".join(issues)
        + f". Run `/check <what you intend to do>` first and review the "
          f"verdict, OR include the literal `{OVERRIDE_TAG}<reason>` in "
          f"your command to bypass (logged to docs/memory/REJECTED_CHANGES.md). "
          f"Hook source: .claude/hook_scripts/catastrophe_block.py"
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
