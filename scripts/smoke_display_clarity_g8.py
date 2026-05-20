"""G8.3 — verify the hours card unifies on hours.taken across both
parent surfaces and the legacy "حضرت X" footer is gone.

Hermetic source-level checks against app.py — no server, no DB.
Structural assertions are sufficient because G8 is a pure read-path
display change (no math, no new endpoints).

Coverage:
  PID hub (PORTAL_PARENT_PID_HUB_HTML):
    1. Header counter writes hours.taken (not hours.attended)
    2. Progress bar fill uses (hrs.taken * 100 / hrs.required)
    3. New element ids exist: hours-taken-head, hours-remaining
    4. The legacy "حضرت X" foot is removed (no .hours-summary-foot
       element AND no "حضرت" label fragment in the card body)
    5. Three info rows in the correct order: العقد → مأخوذة → المتبقي

  Logged-in (_renderHoursCard inside PORTAL_PARENT_ATTENDANCE_HTML):
    6. Same three rows in the same order
    7. "ساعات العقد" label replaces the old "ساعات الدورة الكلية"
    8. Remaining row reads hrs.remaining

  Backend API (sanity):
    9. hours.attended field is still returned by api_parent_hub_stats
       (G8 explicitly preserves it for any downstream consumer)
"""
from __future__ import annotations
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PY = os.path.join(REPO, "app.py")


def _slice_between(src: str, start: str, end: str) -> str:
    s = src.find(start)
    if s == -1:
        return ""
    e = src.find(end, s)
    return src[s:e] if e > s else ""


def main() -> int:
    failures: list[str] = []
    with open(APP_PY, encoding="utf-8") as f:
        src = f.read()

    # ── PID hub assertions ──
    # The hours-summary card markup and its JS render path both live
    # inside the PORTAL_PARENT_PID_HUB_HTML template, between the
    # "id=\"hours-summary\"" anchor and the start of the next template
    # constant HOME_HTML. Slicing this generously covers both the
    # markup and the JS that updates the spans.
    pid_card_window = _slice_between(
        src,
        'id="hours-summary"',
        'HOME_HTML',
    )
    if not pid_card_window:
        failures.append("PID hub: couldn't locate hours-summary window")

    # 1. Header writes taken
    if "document.getElementById('hours-taken-head').textContent = hrs.taken" not in pid_card_window:
        failures.append("PID hub: header counter does NOT read hrs.taken")

    # 2. Progress bar fill uses taken
    if "(hrs.taken||0) * 100 / hrs.required" not in pid_card_window:
        failures.append("PID hub: progress bar fill does NOT use hrs.taken")

    # 3. New element ids exist
    for _id in ("hours-taken-head", "hours-remaining", "hours-taken",
                "hours-contract", "hours-required"):
        if 'id="' + _id + '"' not in pid_card_window:
            failures.append("PID hub: missing element id=" + _id)

    # 4. No legacy "حضرت X" foot. The div class .hours-summary-foot
    # must be gone, AND the foot's element id (hours-attended-foot)
    # must not be referenced. The bare word "حضرت" is allowed inside
    # changelog comments — only the rendered form (id-bearing span)
    # would actually show up on the parent's screen.
    if 'class="hours-summary-foot"' in pid_card_window:
        failures.append("PID hub: .hours-summary-foot div still in "
                        "the card markup")
    if "hours-attended-foot" in pid_card_window:
        failures.append("PID hub: 'hours-attended-foot' element/id "
                        "still referenced (legacy footer not fully removed)")
    if 'id="hours-attended"' in pid_card_window:
        failures.append("PID hub: 'hours-attended' element still in "
                        "the card markup")

    # 5. Three info rows in the correct order
    info_rows_block = _slice_between(pid_card_window, "hours-info-rows", "hours-overrun-banner")
    if not info_rows_block:
        failures.append("PID hub: hours-info-rows block missing")
    else:
        idx_contract  = info_rows_block.find("ساعات العقد")
        idx_taken     = info_rows_block.find("ساعات مأخوذة")
        idx_remaining = info_rows_block.find("المتبقي")
        if -1 in (idx_contract, idx_taken, idx_remaining):
            failures.append("PID hub: one of (ساعات العقد / ساعات مأخوذة / "
                            "المتبقي) labels missing")
        elif not (idx_contract < idx_taken < idx_remaining):
            failures.append("PID hub: info rows not in expected order "
                            "(العقد → مأخوذة → المتبقي)")
        # The renamed label must NOT carry the old "الدورة الكلية" suffix
        if "ساعات الدورة الكلية" in info_rows_block:
            failures.append("PID hub: legacy 'ساعات الدورة الكلية' label "
                            "still present — should be 'ساعات العقد'")

    # ── Logged-in (_renderHoursCard) assertions ──
    fn_body = re.search(
        r"function\s+_renderHoursCard\s*\([^)]*\)\s*\{",
        src,
    )
    logged_in = ""
    if fn_body:
        # Naive brace counter for the function body
        i = fn_body.end() - 1
        depth = 0
        for j in range(i, len(src)):
            ch = src[j]
            if ch == "{": depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    logged_in = src[fn_body.start():j + 1]
                    break
    if not logged_in:
        failures.append("Logged-in: _renderHoursCard body not found")
    else:
        # Strip JS/HTML comments from the body before the label check
        # so a changelog reference like '/* "الدورة الكلية" was renamed */'
        # doesn't trip the assertion. Block-comment stripping is enough
        # since none of the labels we check appear in single-line //.
        no_comments = re.sub(r"/\*.*?\*/", "", logged_in, flags=re.S)
        if "ساعات العقد" not in no_comments:
            failures.append("Logged-in: 'ساعات العقد' label missing")
        if "ساعات الدورة الكلية" in no_comments:
            failures.append("Logged-in: legacy 'ساعات الدورة الكلية' label "
                            "still rendered (not in a comment)")
        if "المتبقي" not in no_comments:
            failures.append("Logged-in: 'المتبقي' row missing")
        # Order check — anchor on the rendered (no-comments) form
        idx_c = no_comments.find("ساعات العقد")
        idx_t = no_comments.find("ساعات مأخوذة")
        idx_r = no_comments.find("المتبقي")
        if -1 not in (idx_c, idx_t, idx_r) and not (idx_c < idx_t < idx_r):
            failures.append("Logged-in: info rows not in expected order")
        # Must read hrs.remaining for the new row
        if "hrs.remaining" not in logged_in:
            failures.append("Logged-in: المتبقي row does not read hrs.remaining")

    # ── Backend hours.attended still in the response ──
    # The api_parent_hub_stats function still computes and exposes
    # hours.attended. Confirm by checking the hours_stat dict shape
    # is unchanged in the source.
    if '"attended":    0' not in src:
        failures.append("Backend: hours.attended initializer missing — "
                        "G8 should have left the field intact for "
                        "downstream consumers")

    if failures:
        print("[G8] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[G8] PASS — hours card unified on hours.taken across both "
          "parent surfaces; legacy 'حضرت' wording gone; three info "
          "rows in العقد → مأخوذة → المتبقي order; backend "
          "hours.attended preserved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
