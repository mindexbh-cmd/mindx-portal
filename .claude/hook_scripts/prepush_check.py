"""PreToolUse hook for git push — warn (never block).

Surfaces:
  - non-main branch push
  - dirty working tree
  - no recent test run (if .last-test-pass marker is missing or > 1h old)

Returns a `systemMessage` rather than a deny verdict. The deploy
protocol (scripts/safe_deploy.py + the /deploy slash command) is the
real gate; this hook is just a heads-up so the operator isn't surprised.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return 0

    cmd = (data.get("tool_input", {}) or {}).get("command", "") or ""
    if "git push" not in cmd:
        print("{}")
        return 0

    warnings: list[str] = []

    # Branch
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if branch != "main":
            warnings.append(f"branch={branch} (not main)")
    except Exception:
        pass

    # Dirty tree
    try:
        dirty = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8").strip()
        if dirty:
            n = len(dirty.splitlines())
            warnings.append(f"working tree dirty ({n} entries)")
    except Exception:
        pass

    # Test recency — operator-set sentinel file
    marker = os.path.join(".claude", ".last-test-pass")
    if not os.path.exists(marker):
        warnings.append("no recent test pass recorded "
                        "(run /test to set the marker)")
    else:
        age = time.time() - os.path.getmtime(marker)
        if age > 3600:
            warnings.append(
                f"last test pass was {int(age/60)} min ago "
                "(consider /test)")

    if warnings:
        print(json.dumps({
            "systemMessage":
                "git push pre-flight: " + "; ".join(warnings)
                + ". Proceeding — this hook is informational only "
                "(/deploy uses scripts/safe_deploy.py for the real "
                "auto-rollback gate)."
        }))
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
