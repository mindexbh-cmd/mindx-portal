"""Regression check that ADMIN_TEACHER_DELIVERIES_HTML carries
the new sequential send flow and no longer carries the buggy
auto-loop pattern.

Pure template-content assertion — exercises no live endpoint
(the server-side /recipient/<rid>/mark-sent + /finalize are
already covered by verify_pm_send_flow.py).

Run: python scripts/verify_teacher_deliveries_send.py
"""
from __future__ import annotations
import os, re, sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))
import app as appmod  # noqa: E402

_results = []


def _check(label, ok, detail=""):
    _results.append((label, ok, detail))
    print(f"  [{'OK' if ok else 'FAIL'}] {label}" +
          (f"  {detail}" if detail else ""))


def main():
    html = appmod.ADMIN_TEACHER_DELIVERIES_HTML

    # ── Markup: new button ids present ──────────────────────────
    print("Markup: new modal buttons present")
    for marker in ('id="tm-send-open"',
                   'id="tm-send-confirm"',
                   'id="tm-send-skip"',
                   'id="tm-send-pause"',
                   'id="tm-send-finish"',
                   'id="tm-send-final-summary"',
                   'id="tm-send-final-text"',
                   'id="tm-send-progress-fill"',
                   'id="tm-send-current-name"',
                   'id="tm-send-current-phone"',
                   'id="tm-send-current-text"',
                   'id="tm-send-blocked-hint"',
                   'id="tm-send-blocked-link"',
                   'id="tm-send-count-sent"',
                   'id="tm-send-count-skipped"',
                   'id="tm-send-count-remaining"'):
        _check(f"has {marker}", marker in html)

    # ── JS: state machine functions present ─────────────────────
    print("\nJS: state machine functions present")
    for fn in ('function tmRunSendSweep',
               'function tmsRenderCurrent',
               'function tmsOpenCurrent',
               'function tmsConfirmCurrent',
               'function tmsSkipCurrent',
               'function tmsRenderDone',
               'function tmsFinish',
               'function tmsPause',
               '/recipient/'):
        _check(f"JS contains {fn!r}", fn in html)

    # ── JS: buggy patterns are GONE ─────────────────────────────
    print("\nJS: buggy patterns removed")
    suspect_step = re.search(r"setTimeout\(\s*step\s*,", html)
    _check("no 'setTimeout(step, …)' loop",
           suspect_step is None,
           f"match: {suspect_step.group(0) if suspect_step else 'none'}")
    suspect_opened = re.search(
        r"window\.open\([^)]*\)\s*;\s*opened\+\+", html)
    _check("no 'window.open(...); opened++' incrementer",
           suspect_opened is None,
           f"match: {suspect_opened.group(0) if suspect_opened else 'none'}")
    # And the old auto-finalize-at-end pattern that lied about counts.
    suspect_autofinal = re.search(
        r"tmSendModalDone\([^\)]+\)\s*;\s*\/\/[^\n]*?Auto-finalize", html)
    _check("no 'Auto-finalize' comment block",
           "Auto-finalize" not in html,
           "marker still present" if "Auto-finalize" in html else "")

    # ── /send-request flow and /send-to-parent stay untouched ───
    print("\nUntouched (other correct flows still intact)")
    _check("/send-request flow still calls window.open inside fetch.then",
           "/send-request" in html and
           "popup = window.open('about:blank'" in html)
    _check("/send-to-parent (eval) flow still present",
           "/send-to-parent" in html)

    # ── Entry point preserved ───────────────────────────────────
    print("\nEntry point preserved")
    _check("tmApproveAndSend still wired",
           "function tmApproveAndSend" in html)
    _check("tmApproveAndSend still calls tmRunSendSweep",
           "tmRunSendSweep(msgId" in html)

    print()
    fails = [r for r in _results if not r[1]]
    print(f"{len(_results) - len(fails)}/{len(_results)} checks passed.")
    if fails:
        print("FAILED:")
        for f in fails:
            print(f"  - {f[0]}  {f[2]}")
        return 1
    print("ALL OK — teacher-deliveries page now uses the sequential "
          "send flow + the buggy auto-loop is gone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
