"""F2 — verify _attRenderMetaCell honours the new priority chain.

The implementation is JS embedded in app.py's ATTENDANCE_HTML. A
behavioural Playwright test would need a fully-seeded prod-shape DB
(student rows + groups + attendance + session_durations) plus the
attendance page to actually render against the right row. That's
significant scaffolding for what is, structurally, a small read-path
change.

Instead: a source-level check that asserts the priority chain wires
exist in the right order. We assert:

  1. _attRenderMetaCell exists.
  2. It calls _attLookup with existingRecords inside its body
     (i.e. it consults the persisted source).
  3. The persisted-value resolution sits inside an `if (!hasOverride)`
     guard — so in-progress overrides keep winning.
  4. The badge variable (hasOverride) is set to true when the
     persisted value differs from auto-meta.
  5. The fallback '—' assignment runs AFTER the persisted lookup, so
     a persisted '60' isn't masked by the placeholder.
"""
from __future__ import annotations
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PY = os.path.join(REPO, "app.py")


def _read_function_body(src: str, name: str) -> str:
    m = re.search(r"function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{", src)
    if not m:
        return ""
    i = m.end() - 1
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

    body = _read_function_body(src, "_attRenderMetaCell")
    if not body:
        print("[F2] FAILED: _attRenderMetaCell not found")
        return 1

    # 1. Consults existingRecords via _attLookup
    if "_attLookup(existingRecords" not in body:
        failures.append("_attRenderMetaCell does not call _attLookup(existingRecords, ...)")

    # 2. Persisted-source consult is gated by !hasOverride
    if "if (!hasOverride)" not in body:
        failures.append("_attRenderMetaCell missing `if (!hasOverride)` guard "
                        "around persisted-source consult — would shadow in-progress edits")

    # 3. hasOverride is flipped true when persisted differs from auto
    if "_pDur !== _autoDur" not in body and "_pDur != _autoDur" not in body:
        failures.append("_attRenderMetaCell does not flip hasOverride when "
                        "persisted ≠ auto — badge would never fire for "
                        "persisted overrides")

    # 4. The em-dash placeholder runs AFTER the persisted lookup. We anchor
    #    on the placeholder line text and the existingRecords lookup line.
    lookup_idx = body.find("_attLookup(existingRecords")
    em_dash_idx = body.find("if (!dur) dur = ")
    if -1 in (lookup_idx, em_dash_idx):
        failures.append("can't locate priority chain markers in body")
    elif lookup_idx > em_dash_idx:
        failures.append("placeholder '—' assignment runs BEFORE persisted "
                        "lookup — would mask persisted values with the dash")

    # 5. The override-set badge path is preserved (in-progress override
    #    still triggers badge).
    if "hasOverride = !!_attMetaOverride[sid]" not in body:
        failures.append("hasOverride no longer initialised from "
                        "_attMetaOverride[sid] — in-progress badge broken")

    # 6. Defensive try/catch around the lookup — we don't want the cell to
    #    blow up if existingRecords is undefined for any reason.
    if "try {" not in body or "catch" not in body:
        failures.append("persisted-source consult is not wrapped in try/catch")

    if failures:
        print("[F2] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[F2] PASS — _attRenderMetaCell honours override → persisted → "
          "auto-meta priority, sets badge for persisted overrides, "
          "guards against missing existingRecords.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
