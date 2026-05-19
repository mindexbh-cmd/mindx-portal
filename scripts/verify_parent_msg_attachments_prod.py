"""Production smoke check for parent_message_attachments.

Logs in as the seeded student/admin/teacher account, uploads a
1KB test PDF, GETs the public download URL, soft-deletes it,
and confirms the public URL then 404s. Never touches any real
parent message — leaves prod state byte-identical after the
soft-delete.

Run:
  python scripts/verify_parent_msg_attachments_prod.py
  python scripts/verify_parent_msg_attachments_prod.py --base http://localhost:5000
"""
from __future__ import annotations
import argparse, io, sys

import requests

DEFAULT_BASE = "https://mindx-portal-1.onrender.com"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--username", default="teacher_test")
    ap.add_argument("--password", default="TestTeacher2026!")
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
        print(f"  LOGIN FAILED status={r.status_code} body={r.text[:200]!r}")
        return 1
    print(f"  logged in as {args.username!r}")

    ok_all = True
    def check(label, pred, detail=""):
        nonlocal ok_all
        if not pred: ok_all = False
        print(f"  [{'OK' if pred else 'FAIL'}] {label}" +
              (f"  {detail}" if detail else ""))

    pdf = b"%PDF-1.4\n%test\n" + (b"\n" * 1000)
    files = {"file": ("prod_smoke.pdf", io.BytesIO(pdf), "application/pdf")}
    r = s.post(base + "/api/parent-messages/attachments",
               files=files, timeout=30)
    j = r.json() if r.headers.get("Content-Type","").startswith("application/json") else {}
    fid = (j or {}).get("file_id") or ""
    check("upload HTTP 200", r.status_code == 200, f"got {r.status_code}")
    check("file_id is 32-char hex",
          len(fid) == 32 and all(c in "0123456789abcdef" for c in fid),
          f"fid={fid!r}")
    url = (j or {}).get("url") or ""
    check("url is absolute",
          url.startswith("http"),
          f"url={url}")
    check("content_type=application/pdf",
          (j or {}).get("content_type") == "application/pdf")
    check("size matches input",
          int((j or {}).get("size", 0)) == len(pdf))

    if not fid:
        print("\nAborting — no file_id to follow with.")
        return 1

    # Public GET — fresh session (no cookies) to prove it's truly public.
    pub = requests.Session()
    r = pub.get(base + f"/files/parent-messages/{fid}", timeout=30)
    check("public GET HTTP 200", r.status_code == 200, f"got {r.status_code}")
    check("Content-Type=application/pdf",
          r.headers.get("Content-Type") == "application/pdf")
    check("body has %PDF- magic",
          r.content[:5] == b"%PDF-")
    check("body length matches",
          len(r.content) == len(pdf),
          f"got {len(r.content)} expected {len(pdf)}")

    # Bogus slug → 404.
    r = pub.get(base + "/files/parent-messages/" + ("0"*32), timeout=15)
    check("bogus file_id → 404", r.status_code == 404)

    # Soft-delete then re-GET → 404.
    r = s.delete(base + f"/api/parent-messages/attachments/{fid}",
                 timeout=30)
    check("DELETE returns ok",
          (r.json() or {}).get("ok"),
          f"got {r.json()}")
    r = pub.get(base + f"/files/parent-messages/{fid}", timeout=30)
    check("public GET after delete → 404",
          r.status_code == 404, f"got {r.status_code}")

    print()
    if ok_all:
        print("ALL OK — prod attachment pipeline works end-to-end.")
        print(f"\nOperator test URL: {base}/teacher/parent-messages")
        print("Login as any teacher → fill the form → use the new")
        print("📎 المرفقات picker → save the draft.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
