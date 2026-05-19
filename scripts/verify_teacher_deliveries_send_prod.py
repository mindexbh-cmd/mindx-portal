"""Prod smoke for the teacher-deliveries send fix.

Confirms /admin/teacher-deliveries serves the new sequential
modal markup + state-machine JS, and the buggy auto-loop pattern
is no longer in the response.

Run:
  python scripts/verify_teacher_deliveries_send_prod.py
"""
from __future__ import annotations
import argparse, re, sys, time

import requests

DEFAULT_BASE = "https://mindx-portal-1.onrender.com"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--username", default="admin")
    ap.add_argument("--password", default="admin123")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"=== verifying {base} ====================================")

    # Wait for /version to be parseable + report sha.
    sha = None
    for _ in range(6):
        try:
            v = requests.get(base + "/version", timeout=15).json()
            sha = v.get("sha")
            if sha: break
        except Exception:
            pass
        time.sleep(10)
    if not sha:
        print("  /version unreachable after retries"); return 1
    print(f"  /version sha={sha}")

    s = requests.Session()
    r = s.post(base + "/login",
               data={"username": args.username, "password": args.password},
               allow_redirects=False, timeout=30)
    if r.status_code not in (302, 303):
        print(f"  LOGIN FAILED status={r.status_code}"); return 1
    print(f"  logged in as {args.username!r}")

    r = s.get(base + "/admin/teacher-deliveries", timeout=30)
    if r.status_code != 200:
        print(f"  HTTP {r.status_code} on /admin/teacher-deliveries")
        return 1
    html = r.text
    print(f"  /admin/teacher-deliveries len={len(html)}")

    ok = True
    def check(label, pred, detail=""):
        nonlocal ok
        if not pred: ok = False
        print(f"  [{'OK' if pred else 'FAIL'}] {label}" +
              (f"  {detail}" if detail else ""))

    # New modal markers present
    for m in ('id="tm-send-open"',
              'id="tm-send-confirm"',
              'id="tm-send-skip"',
              'id="tm-send-pause"',
              'id="tm-send-finish"',
              'id="tm-send-progress-fill"',
              'id="tm-send-current-name"',
              'id="tm-send-blocked-hint"'):
        check(f"served HTML has {m}", m in html)

    # State machine functions present
    for fn in ('function tmRunSendSweep',
               'function tmsOpenCurrent',
               'function tmsConfirmCurrent',
               'function tmsSkipCurrent',
               'function tmsFinish',
               '/recipient/'):
        check(f"served JS has {fn!r}", fn in html)

    # Buggy patterns absent
    suspect = re.search(r"setTimeout\(\s*step\s*,", html)
    check("no 'setTimeout(step, …)' in served HTML",
          suspect is None,
          f"match: {suspect.group(0) if suspect else 'none'}")
    suspect2 = re.search(r"window\.open\([^)]*\)\s*;\s*opened\+\+", html)
    check("no 'window.open(...); opened++' in served HTML",
          suspect2 is None,
          f"match: {suspect2.group(0) if suspect2 else 'none'}")

    print()
    if ok:
        print("ALL OK — teacher-deliveries page now serves the "
              "sequential send flow on prod.")
        print(f"\nOperator test URL: {base}/admin/teacher-deliveries")
        print("Select a teacher → click موافقة وإرسال on a pending "
              "message → walk through the new modal step-by-step.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
