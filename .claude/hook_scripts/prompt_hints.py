"""UserPromptSubmit hook — gentle keyword reminders + secret detection.

Looks at the user's prompt. If it mentions:
  - "deploy" without invoking /deploy → remind about the slash command
  - "test"/"tests" without /test → remind about it
  - "logs" without /logs → remind
  - looks like an API token (rnd_/ghp_/sk-) → loud warning about
    rotating credentials post-conversation

Returned via `hookSpecificOutput.additionalContext` so the assistant
sees the hint but the user's terminal isn't cluttered.
"""
from __future__ import annotations
import json
import re
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return 0

    prompt = data.get("prompt") or ""
    pl = prompt.lower()

    hints: list[str] = []

    if "deploy" in pl and "/deploy" not in pl:
        hints.append(
            "Tip: `/deploy <slug>` runs the safe-deploy pipeline "
            "(safety tag → push → poll /api/health → smoke e2e → "
            "auto-rollback).")

    if ("test" in pl or "tests" in pl) and "/test" not in pl:
        hints.append(
            "Tip: `/test` runs the full e2e suite against the local "
            "dev server.")

    if ("log " in pl or "logs " in pl) and "/logs" not in pl:
        hints.append(
            "Tip: `/logs <keyword>` pulls the last hour of Render "
            "logs filtered.")

    # Secret scan on the raw prompt (case-sensitive).
    if re.search(r"(rnd_|ghp_|sk-)[A-Za-z0-9_\-]{20,}", prompt):
        hints.append(
            "WARNING: your message contains what looks like an API "
            "token. The assistant will avoid logging or committing "
            "it, but you should rotate the credential after this "
            "conversation since the transcript persists.")

    if hints:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext":
                    "[prompt hints]\n- " + "\n- ".join(hints),
            }
        }))
    else:
        print("{}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
