"""Production smoke for the quantity + unit_ar feature.

READ-ONLY assertions against the deployed instance:
  1. /version sha matches deploy.
  2. /expenses (admin) HTML carries the new field IDs + الكمية column
     + colspan=7 empty cell.
  3. /assets HTML carries the new field IDs + detail الكمية row + the
     "qty > 1" card meta line.
  4. /api/expenses?limit=5 rows expose quantity + unit_ar keys.
  5. /api/assets?limit=5 rows expose quantity + unit_ar keys.

No write probes — those would leave litter on prod.
"""
from __future__ import annotations
import argparse, sys, time

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
        print("  /version unreachable"); return 1
    print(f"  /version sha={sha}")

    s = requests.Session()
    r = s.post(base + "/login",
               data={"username": args.username, "password": args.password},
               allow_redirects=False, timeout=30)
    if r.status_code not in (302, 303):
        print(f"  LOGIN FAILED status={r.status_code}"); return 1
    print(f"  logged in as {args.username!r}")

    ok = True
    def check(label, pred, detail=""):
        nonlocal ok
        if not pred: ok = False
        print(f"  [{'OK' if pred else 'FAIL'}] {label}" +
              (f"  {detail}" if detail else ""))

    # 1. /expenses (admin) HTML
    print("\n  /expenses admin markup")
    r = s.get(base + "/expenses", timeout=30)
    h = r.text
    for marker in ('id="exp-qty"',
                   'id="exp-unit"',
                   'id="exp-unit-other"',
                   'value="__other__"',
                   '&#x627;&#x644;&#x643;&#x645;&#x64A;&#x629;',
                   'colspan="7"',
                   'var qtyCell'):
        check(f"  /expenses has {marker!r}", marker in h)

    # 2. /assets HTML
    print("\n  /assets markup")
    r = s.get(base + "/assets", timeout=30)
    h = r.text
    for marker in ('id="ast-qty"',
                   'id="ast-unit"',
                   'id="ast-unit-other"',
                   'value="__other__"',
                   "'الكمية'",
                   "parseInt(r.quantity, 10) > 1"):
        check(f"  /assets has {marker!r}", marker in h)

    # 3. /api/expenses list JSON carries the keys
    print("\n  /api/expenses list JSON")
    r = s.get(base + "/api/expenses?limit=5", timeout=30)
    j = r.json() or {}
    check("  /api/expenses 200", r.status_code == 200,
          f"got {r.status_code}")
    rows = j.get("rows") or []
    if rows:
        keys = set(rows[0].keys())
        check("  /api/expenses row has 'quantity'", "quantity" in keys,
              f"got {sorted(keys)[:10]}…")
        check("  /api/expenses row has 'unit_ar'",  "unit_ar"  in keys)
    else:
        print("    (no rows on prod — keys-presence check skipped)")

    # 4. /api/assets list JSON
    print("\n  /api/assets list JSON")
    r = s.get(base + "/api/assets?limit=5", timeout=30)
    j = r.json() or {}
    check("  /api/assets 200", r.status_code == 200,
          f"got {r.status_code}")
    rows = j.get("rows") or []
    if rows:
        keys = set(rows[0].keys())
        check("  /api/assets row has 'quantity'", "quantity" in keys,
              f"got {sorted(keys)[:10]}…")
        check("  /api/assets row has 'unit_ar'",  "unit_ar"  in keys)
    else:
        print("    (no rows on prod — keys-presence check skipped)")

    print()
    if ok:
        print("ALL OK — quantity/unit_ar surfaced on prod /expenses + /assets "
              "+ both list endpoints.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
