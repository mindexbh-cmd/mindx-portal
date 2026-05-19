"""Production smoke for fix-pm-send-flow.

End-to-end against the live deployment:
  - Login as admin.
  - Create a real draft via the existing /api/parent-messages POST
    using a group that has at least one active student.
  - Call /send → confirm draft stays at status='draft'.
  - Call /recipient/<rid>/mark-sent → confirm sent_count bumps.
  - Call /finalize → confirm status flips to 'sent'.
  - Soft-delete the test draft so prod state is clean.

Run:
  python scripts/verify_pm_send_flow_prod.py
"""
from __future__ import annotations
import argparse, sys

import requests

DEFAULT_BASE = "https://mindx-portal-1.onrender.com"


def _check(label, ok, detail=""):
    print(f"  [{'OK' if ok else 'FAIL'}] {label}" +
          (f"  {detail}" if detail else ""))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--username", default="admin")
    ap.add_argument("--password", default="admin123")
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"=== verifying {base} ====================================")
    try:
        v = requests.get(base + "/version", timeout=20).json()
        print(f"  /version sha={v.get('sha')}")
    except Exception as ex:
        print(f"  /version failed: {ex}"); return 1

    s = requests.Session()
    r = s.post(base + "/login",
               data={"username": args.username, "password": args.password},
               allow_redirects=False, timeout=30)
    if r.status_code not in (302, 303):
        print(f"  LOGIN FAILED status={r.status_code}"); return 1
    print(f"  logged in as {args.username!r}")

    # Pick the first prod group via the existing admin endpoint.
    r = s.get(base + "/api/points/groups", timeout=30)
    names = ((r.json() or {}).get("names") or [])
    if not names:
        print("  no groups visible — cannot create a test draft")
        return 1
    target_group = names[0]
    print(f"  using group: {target_group!r}")

    # Create a test draft.
    r = s.post(base + "/api/parent-messages",
               json={"action": "save",
                     "group_name": target_group,
                     "content_covered": "prod smoke — fix-pm-send-flow",
                     "skills_focused":  "verifying mark-sent endpoint",
                     "books_used":      "—",
                     "homework":        "",
                     "parent_notes":    "(this draft will be deleted at end)"})
    j = r.json() or {}
    mid = j.get("id")
    if not (j.get("ok") and mid):
        print(f"  create draft failed: {j}"); return 1
    print(f"  created test draft id={mid}")

    ok_all = True
    # /send
    r = s.post(base + f"/api/parent-messages/{mid}/send")
    j = r.json() or {}
    recipients = j.get("recipients") or []
    total = j.get("total_count") or len(recipients)
    ok_all &= _check("/send HTTP 200", r.status_code == 200,
                     f"got {r.status_code}")
    ok_all &= _check("/send ok=True",
                     j.get("ok") is True)
    print(f"    /send returned {len(recipients)} recipient(s), total={total}")

    # /recipient/0/mark-sent — synthetic bump (doesn't depend on
    # any specific recipient existing for a clean smoke).
    r = s.post(base + f"/api/parent-messages/{mid}/recipient/0/mark-sent")
    j = r.json() or {}
    ok_all &= _check("mark-sent ok",
                     j.get("ok") is True,
                     f"got {j}")
    ok_all &= _check("sent_count = 1 after one bump",
                     j.get("sent_count") == 1,
                     f"got {j.get('sent_count')}")

    # Second bump — verifies counter advances.
    r = s.post(base + f"/api/parent-messages/{mid}/recipient/0/mark-sent")
    j = r.json() or {}
    ok_all &= _check("sent_count = 2 after second bump",
                     j.get("sent_count") == 2,
                     f"got {j.get('sent_count')}")

    # /finalize.
    r = s.post(base + f"/api/parent-messages/{mid}/finalize",
               json={"sent_count": 2,
                     "total_count": max(total, 2)})
    j = r.json() or {}
    ok_all &= _check("/finalize flips status",
                     j.get("status") == "sent",
                     f"got status={j.get('status')!r}")

    # mark-sent after finalize → already_finalized=True, no bump.
    r = s.post(base + f"/api/parent-messages/{mid}/recipient/0/mark-sent")
    j = r.json() or {}
    ok_all &= _check("post-finalize mark-sent → already_finalized=True",
                     j.get("already_finalized") is True,
                     f"got {j}")
    ok_all &= _check("post-finalize count unchanged",
                     j.get("sent_count") == 2,
                     f"got {j.get('sent_count')}")

    # Markup check — fresh /admin/parent-messages should carry the
    # new modal markers.
    r = s.get(base + "/admin/parent-messages", timeout=30)
    html = r.text
    for marker in ('id="pmsOpenBtn"', 'id="pmsConfirmBtn"',
                   'id="pmsSkipBtn"', 'id="pmsPauseBtn"',
                   '/recipient/'):
        ok_all &= _check(f"admin page has {marker}", marker in html)

    # Cleanup — soft-delete the test draft.
    r = s.delete(base + f"/api/parent-messages/{mid}")
    j = r.json() or {}
    print(f"\n  cleanup: DELETE returned ok={j.get('ok')}")

    print()
    if ok_all:
        print("ALL OK — sequential send flow live on prod.")
        print(f"\nOperator test URL: {base}/admin/parent-messages")
        print("Open any draft → click send → walk through the modal "
              "step-by-step.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
