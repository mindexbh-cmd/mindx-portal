"""PostToolUse hook for git commit — invoke memory-keeper for notable commits.

Fires after `git commit *` succeeds. Inspects the new HEAD's commit
message. If the subject line starts with `feat:` / `fix:` / `refactor:`
(with optional scope `feat(scope):`), surfaces a system message
pointing memory-keeper-agent at the commit so the next turn updates
the relevant log.

Does NOT block. Does NOT invoke any agent synchronously (the parent
turn is the right place for that). The hook's job is to flag —
the assistant decides whether to act.
"""
from __future__ import annotations
import json
import re
import subprocess
import sys


SUBJECT_RE = re.compile(r"^(feat|fix|refactor)(\([a-z0-9_-]+\))?\s*:\s*.+",
                        re.I)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return 0

    cmd = (data.get("tool_input", {}) or {}).get("command", "") or ""
    if "git commit" not in cmd:
        print("{}")
        return 0

    # Read the latest commit's subject.
    try:
        subject = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%s"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        sha = subprocess.check_output(
            ["git", "log", "-1", "--pretty=%h"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
    except Exception:
        print("{}")
        return 0

    if not SUBJECT_RE.match(subject):
        print("{}")
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext":
                f"[memory-keeper hint] Commit {sha} subject "
                f"'{subject[:80]}' qualifies for log update. Consider "
                "invoking memory-keeper-agent in passive-tracking mode "
                "to append to docs/memory/{CHANGE_LOG,BUGS_LOG,"
                "DECISIONS_LOG,DESIGN_LOG}.md as appropriate.",
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
