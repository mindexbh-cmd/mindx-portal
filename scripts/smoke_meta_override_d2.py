"""D2 — verify the override-clear fix lands in both lifecycle hooks.

The clears are unconditional statements inside well-known function
bodies in ATTENDANCE_HTML. We assert structural placement:

  1. checkAndLoad must clear _attMetaOverride alongside _attMetaCache,
     before the Promise.all that fires the per-date refetch.
  2. saveAllAttendance must clear _attMetaOverride in the SUCCESS
     branch (after the success toast, before checkAndLoad), and NOT
     in the failure branch (which preserves user-in-progress state).

The check operates on the ATTENDANCE_HTML constant from app.py so it
needs no running server, no DB, and no browser — fast and hermetic.
"""
from __future__ import annotations
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PY = os.path.join(REPO, "app.py")


def _read_function_body(src: str, name: str) -> str:
    """Return the textual body of `function <name>(...) { ... }` using
    a naive brace counter. Sufficient for app.py's inline scripts —
    string literals containing unbalanced braces don't exist in these
    functions. Returns '' when the function is not found."""
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", src)
    if not m:
        return ""
    i = m.end() - 1  # position of the opening brace
    depth = 0
    for j in range(i, len(src)):
        ch = src[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
    return ""


def main() -> int:
    failures: list[str] = []
    with open(APP_PY, encoding="utf-8") as f:
        src = f.read()

    chk = _read_function_body(src, "checkAndLoad")
    if not chk:
        failures.append("checkAndLoad not found in app.py")
    else:
        # 1a. Both clears present
        if "_attMetaCache = {}" not in chk:
            failures.append("checkAndLoad: _attMetaCache = {} missing")
        if "_attMetaOverride = {}" not in chk:
            failures.append("checkAndLoad: _attMetaOverride = {} missing")
        # 1b. Clears come before the Promise.all
        promise_idx = chk.find("Promise.all")
        override_idx = chk.find("_attMetaOverride = {}")
        if -1 not in (promise_idx, override_idx) and override_idx > promise_idx:
            failures.append(
                "checkAndLoad: _attMetaOverride clear is AFTER Promise.all — "
                "it must run synchronously at the top of the function"
            )

    sav = _read_function_body(src, "saveAllAttendance")
    if not sav:
        failures.append("saveAllAttendance not found in app.py")
    else:
        # 2a. Clear is present somewhere
        if "_attMetaOverride = {}" not in sav:
            failures.append(
                "saveAllAttendance: _attMetaOverride = {} missing — the "
                "success-path clear is not in place"
            )
        # 2b. Clear is in the LIVE success branch. saveAllAttendance
        # contains both a legacy `function finish()` (dead — overwritten
        # later in the same function) and an override `finish = function()`
        # assignment that's the live success path. The clear belongs in
        # the override. We anchor on the LAST occurrences of the success
        # toast colour and the checkAndLoad reload so we're looking at
        # the override block.
        toast_idx = sav.rfind("'#00897B'")
        clear_idx = sav.rfind("_attMetaOverride = {}")
        reload_idx = sav.rfind("checkAndLoad(group, date)")
        if -1 in (toast_idx, clear_idx, reload_idx):
            failures.append(
                "saveAllAttendance: one of (success toast, override clear, "
                "checkAndLoad reload) is missing — cannot validate placement"
            )
        elif not (toast_idx < clear_idx < reload_idx):
            failures.append(
                "saveAllAttendance: override clear is not between success "
                "toast and checkAndLoad reload — placement regression "
                "(toast=" + str(toast_idx) + " clear=" + str(clear_idx)
                + " reload=" + str(reload_idx) + ")"
            )
        # 2c. Clear is NOT in the failure branch. The failure branch is
        # marked by the failure toast colour '#e53935' followed by a
        # `return;`. We assert no override-clear sits between them.
        fail_toast = sav.find("'#e53935'")
        if fail_toast != -1:
            fail_return = sav.find("return", fail_toast)
            if fail_return != -1:
                fail_block = sav[fail_toast:fail_return]
                if "_attMetaOverride = {}" in fail_block:
                    failures.append(
                        "saveAllAttendance: override clear leaked into the "
                        "failure branch — would lose user's in-progress "
                        "edits on save errors"
                    )

    if failures:
        print("[D2] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[D2] PASS — checkAndLoad clears _attMetaOverride alongside the "
          "cache, and saveAllAttendance clears it only on the success path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
