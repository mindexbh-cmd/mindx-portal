"""Production smoke for session_durations bulk-fill.

READ-ONLY: only exercises /bulk-preview (which performs no writes)
and verifies the markup is served on /dashboard.

Specifically NOT exercised on prod:
  /bulk-fill — would actually write to prod's session_durations.
              Operator should do the manual test from the UI.

Run: python scripts/verify_session_durations_bulk_prod.py
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

    # 1. Modal markup on dashboard.
    r = s.get(base + "/dashboard", timeout=30)
    html = r.text
    for marker in ('id="sd-bulk-toggle"',
                   'id="sd-bulk-panel"',
                   'id="sd-bulk-from"',
                   'id="sd-bulk-to"',
                   'id="sd-bulk-dur"',
                   'id="sd-bulk-type"',
                   'id="sd-bulk-preview-btn"',
                   'id="sd-bulk-apply-btn"',
                   '🚀 تعبئة سريعة بالجملة',
                   'sdBulkPreview',
                   'sdBulkApply',
                   '/api/session-durations/bulk-preview',
                   '/api/session-durations/bulk-fill'):
        check(f"dashboard HTML carries {marker!r}", marker in html)

    # 2. Preview endpoint with a tiny date range (read-only). Use
    # a 1-day range so the universe is small even if prod has lots
    # of attendance data.
    r = s.post(base + "/api/session-durations/bulk-preview",
               json={"group_names": "all",
                     "date_from": "2026-05-19",
                     "date_to":   "2026-05-19",
                     "duration_minutes": 60,
                     "lesson_type": ""},
               timeout=30)
    check("preview HTTP 200", r.status_code == 200, f"got {r.status_code}")
    j = r.json() or {}
    check("preview ok=True", j.get("ok") is True)
    check("preview returns 'total' field",
          isinstance(j.get("total"), int),
          f"got total={j.get('total')!r}")
    check("preview returns 'by_group' array",
          isinstance(j.get("by_group"), list))
    check("preview returns date_from/date_to echo",
          j.get("date_from") == "2026-05-19" and j.get("date_to") == "2026-05-19")
    check("preview returns overwrite=false echo",
          j.get("overwrite") is False)
    if isinstance(j.get("total"), int):
        print(f"    (informational: prod has {j.get('total')} (group, date) "
              f"pairs on 2026-05-19 across {len(j.get('by_group') or [])} group(s))")

    # 3. Validation: empty group_names list returns 400.
    r = s.post(base + "/api/session-durations/bulk-preview",
               json={"group_names": [], "date_from": "2026-05-19",
                     "date_to": "2026-05-19", "duration_minutes": 60},
               timeout=30)
    check("empty group_names → HTTP 400", r.status_code == 400)

    print()
    if ok:
        print("ALL OK — bulk-fill endpoints + UI live on prod.")
        print(f"\nOperator test URL: {base}/dashboard")
        print("Click the '⏱ مدة الحصص' card → '🚀 تعبئة سريعة بالجملة' "
              "toggle to expand the panel.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
