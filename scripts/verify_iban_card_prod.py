"""Prod-side fetch of /parent/legacy to confirm the IBAN card is
in the deployed markup, in the correct position (between the
installment picker and the receipt-upload section).

Uses a real student session — defaults to the seeded student_test
(plain password = TestStudent2026!). If your prod doesn't carry
that seed, override via --username/--password.
"""
from __future__ import annotations
import argparse, sys

import requests

DEFAULT_BASE = "https://mindx-portal-1.onrender.com"
IBAN = "BH30BIBB00100002994768"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--username", default="student_test")
    ap.add_argument("--password", default="TestStudent2026!")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"=== verifying {base} ====================================")
    try:
        v = requests.get(base + "/version", timeout=20).json()
        print(f"  /version sha={v.get('sha')}")
    except Exception as ex:
        print(f"  /version failed: {ex}")
        return 1

    s = requests.Session()
    r = s.post(base + "/login",
               data={"username": args.username, "password": args.password},
               allow_redirects=False, timeout=30)
    if r.status_code not in (302, 303):
        print(f"  LOGIN FAILED status={r.status_code}")
        return 1
    print(f"  logged in as {args.username!r}")

    r = s.get(base + "/parent/legacy",
              allow_redirects=False, timeout=30)
    if r.status_code != 200:
        print(f"  FAIL — /parent/legacy → HTTP {r.status_code}")
        return 1
    html = r.text

    ok = True
    def check(label, pred):
        nonlocal ok
        if not pred: ok = False
        print(f"  [{'OK' if pred else 'FAIL'}] {label}")

    check("IBAN value in markup",             IBAN in html)
    check("#pp-iban-card element present",    'id="pp-iban-card"' in html)
    check("copy button id #pp-iban-copy-btn", 'id="pp-iban-copy-btn"' in html)
    check("data-iban attribute",              f'data-iban="{IBAN}"' in html)
    check("button label '📋 نسخ'",            "📋 نسخ" in html)
    check("'✓ تم النسخ' in JS",              "✓ تم النسخ" in html)
    check("clipboard API path",               "navigator.clipboard.writeText" in html)
    check("execCommand fallback",             "document.execCommand('copy')" in html)
    check(".pp-iban-num CSS rule",            '.pp-iban-num' in html)

    iban_idx   = html.find('id="pp-iban-card"')
    pick_idx   = html.find('id="pp-pick-card"')
    upload_idx = html.find('id="pp-upload-card"')
    check("IBAN card AFTER #pp-pick-card",
          0 <= pick_idx < iban_idx)
    check("IBAN card BEFORE #pp-upload-card",
          0 <= iban_idx < upload_idx)

    print()
    if ok:
        print("ALL OK — prod serves the IBAN card on /parent/legacy "
              "in the correct position.")
        print(f"Operator can test live at: {base}/parent/legacy")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
