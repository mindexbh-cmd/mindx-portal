"""PreToolUse hook for git commit — fails fast on broken syntax or secrets.

Reads the tool-call JSON on stdin. If the command isn't `git commit ...`,
exits 0 with empty JSON (no-op). Otherwise:
  1. If `app.py` is among the staged files, runs `ast.parse` on it.
  2. Greps the staged diff (`+` lines only) for narrow secret patterns:
     rnd_<20+>, ghp_<20+>, sk-<20+>. Also detects `password=` followed
     by a quoted literal.
  3. If anything fires, returns a deny verdict with the issue list.

Safe by design: narrow regex avoids false positives on legitimate
`password=` form fields, `name="password"` HTML attrs, etc.
"""
from __future__ import annotations
import ast
import json
import re
import subprocess
import sys


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

    issues: list[str] = []

    # 1) Syntax check on app.py if it's staged.
    try:
        staged = subprocess.check_output(
            ["git", "diff", "--cached", "--name-only"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace").split()
        if "app.py" in staged:
            try:
                ast.parse(open("app.py", encoding="utf-8").read())
            except SyntaxError as e:
                issues.append(
                    f"app.py syntax error at line {e.lineno}: {e.msg}")
    except Exception:
        pass

    # 2) Secret scan on ADDED lines of the staged diff only.
    try:
        diff = subprocess.check_output(
            ["git", "diff", "--cached", "-U0"],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace")
        # Restrict to added lines (start with + but not +++ file marker).
        secrets = re.findall(
            r"^\+(?!\+\+).*?((?:rnd_|ghp_|sk-)[A-Za-z0-9_\-]{20,})",
            diff, flags=re.M)
        if secrets:
            issues.append(
                "API token in staged diff: " +
                ", ".join(s[:12] + "..." for s in secrets[:3]))
        # Detect assignments where an identifier in the
        # password / passwd / api_key / token / secret family is
        # followed by = or : and a quoted string of 4+ chars.
        # Anchors on the IDENTIFIER side so HTML form attributes
        # whose VALUE is one of those words are not flagged.
        pw = re.findall(
            r"^\+(?!\+\+).*?\b(?:password|passwd|api_key|token|secret)"
            r"\s*[=:]\s*['\"]([^'\"]{4,})['\"]",
            diff, flags=re.M | re.I)
        if pw:
            issues.append(
                "Quoted secret literal in diff: " +
                ", ".join(p[:8] + "..." for p in pw[:3]))
    except Exception:
        pass

    if issues:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason":
                    "pre-commit hook: " + "; ".join(issues)
                    + " — fix and re-stage, or commit manually if it's a "
                    "false positive (this hook is in "
                    ".claude/hook_scripts/precommit_check.py)",
            }
        }))
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
