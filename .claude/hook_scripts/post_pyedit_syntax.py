"""PostToolUse hook for Edit/Write — warn on .py syntax breaks.

Runs `ast.parse` on the edited file if it's a .py. Returns a
`systemMessage` (never blocks — block would be useless after the
write has already happened). The point is to surface the break
immediately so the assistant fixes it in the next turn instead of
chasing a later error.
"""
from __future__ import annotations
import ast
import json
import sys


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        print("{}")
        return 0

    ti = data.get("tool_input") or {}
    tr = data.get("tool_response") or {}
    path = (ti.get("file_path") or tr.get("filePath") or "").strip()
    if not path.endswith(".py"):
        print("{}")
        return 0

    try:
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
    except Exception:
        # File missing or unreadable — silent (probably a delete or
        # a path Claude can't see from the hook's CWD).
        print("{}")
        return 0

    try:
        ast.parse(source)
        print("{}")
        return 0
    except SyntaxError as e:
        print(json.dumps({
            "systemMessage":
                f"py syntax: {path}:{e.lineno}: {e.msg} "
                "(fix before next edit)"
        }))
        return 0


if __name__ == "__main__":
    sys.exit(main())
