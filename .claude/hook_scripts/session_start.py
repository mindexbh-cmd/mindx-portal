"""SessionStart hook — injects a brief status snapshot.

Surfaces:
  - git branch
  - uncommitted changes (`git status --short`, capped at 8 lines)
  - last 5 commits

Returned via `hookSpecificOutput.additionalContext` so the assistant
sees the snapshot at the top of the conversation context. Lightweight
— shells out only to git, no DB reads, no network.
"""
from __future__ import annotations
import json
import subprocess
import sys


def _git(args: list[str]) -> str:
    try:
        return subprocess.check_output(
            ["git"] + args, stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace").rstrip()
    except Exception:
        return ""


def main() -> int:
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or "(detached)"
    status_lines = _git(["status", "--short"]).splitlines()
    if len(status_lines) > 8:
        status_block = (
            "\n".join(status_lines[:8])
            + f"\n... ({len(status_lines) - 8} more)")
    else:
        status_block = "\n".join(status_lines) if status_lines else "(clean)"
    recent = _git(["log", "--oneline", "-5"]) or "(no commits)"

    # Pull a brief HANDOFF_COMPACT.md preview if present — gives the
    # session immediate project context without forcing the assistant
    # to read it itself.
    handoff_preview = ""
    try:
        with open("docs/memory/HANDOFF_COMPACT.md", encoding="utf-8") as fh:
            text = fh.read()
        # Trim the YAML/markdown header and grab the first ~600 chars
        # of body so the snapshot stays compact.
        body_start = text.find("## ")
        preview = text[body_start:body_start + 600] if body_start >= 0 else text[:600]
        handoff_preview = (
            "\n**HANDOFF_COMPACT.md preview** (full file at "
            "`docs/memory/HANDOFF_COMPACT.md`):\n"
            f"```\n{preview.rstrip()}\n…\n```\n"
        )
    except Exception:
        pass

    msg = (
        "## Session start snapshot\n\n"
        f"**Branch:** {branch}\n\n"
        f"**Working tree:**\n```\n{status_block}\n```\n\n"
        f"**Recent commits:**\n```\n{recent}\n```\n"
        + handoff_preview
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": msg,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
