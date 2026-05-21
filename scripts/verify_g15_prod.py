"""G15 prod verification — student approval workflow.

Uses requests.Session() (sidesteps the headless-Chromium cookie-drop
quirk first seen in G13). Logs in as student_test, exercises:
  - GET  /api/portal/student/balance
  - POST /api/portal/student/order — G17: confirms 404 (endpoint removed)
  - POST /api/portal/student/cart/add
  - GET  /api/portal/student/cart
  - PUT  /api/portal/student/cart/<cid>/quantity
  - DELETE /api/portal/student/cart/<cid>
  - POST /api/portal/student/cart/checkout (insufficient)
  - POST /api/portal/student/redemptions/<id>/cancel (404 path)
  - POST /api/portal/student/redeem (legacy 410)
  - GET  /portal/parent-hub/points (HTML markup check)
  - GET  /api/portal/student/redemptions (includes rejection_reason)

Also confirms admin side unchanged:
  - GET /api/points/history?source=student_portal (filter works)
  - GET /api/points/redemptions (admin still lists rows)

Usage:
    python scripts/verify_g15_prod.py --base https://mindx-portal-1.onrender.com
"""
import argparse
import sys

import requests


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://mindx-portal-1.onrender.com")
    args = ap.parse_args()

    BASE = args.base.rstrip("/")
    failed = []

    def check(label, ok, hint=""):
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}")
        if not ok:
            failed.append(label + (f" -- {hint}" if hint else ""))

    print(f"\n=== G15 verification against {BASE} ===\n")

    # 1. Login as student_test.
    s = requests.Session()
    s.headers.update({"User-Agent": "g15-verify/1.0"})
    r = s.post(
        BASE + "/login",
        data={"username": "student_test", "password": "TestStudent2026!"},
        allow_redirects=True, timeout=30,
    )
    check(f"student_test login (status={r.status_code}, url={r.url})",
          r.status_code == 200 and "/login" not in r.url)

    # 2. Balance endpoint shape.
    print("\n[G15.1 + G15.2] balance endpoint")
    r = s.get(BASE + "/api/portal/student/balance", timeout=30)
    bal = r.json() if r.status_code == 200 else {}
    print(f"    (status={r.status_code}, body={bal})")
    check("/balance returns 4-key dict",
          r.status_code == 200 and bal.get("ok")
          and {"total", "committed", "reserved", "available"}.issubset(bal.keys()))
    check("available = total - committed - reserved",
          (bal.get("ok") and
           bal["available"] == bal["total"] - bal["committed"] - bal["reserved"]))

    # 3. G17: /api/portal/student/order REMOVED. Confirm Flask
    # returns 404 (no route registered).
    print("\n[G17] /order endpoint removed")
    r = s.post(BASE + "/api/portal/student/order", json={}, timeout=30)
    check(f"/order returns 404 (was 400/404 before G17) ({r.status_code})",
          r.status_code == 404)
    rwj = s.get(BASE + "/api/points/rewards", timeout=30).json()
    real_rid = (rwj.get("rows") or [{}])[0].get("id", 0)

    # 4. Cart endpoints.
    print("\n[G15.4] cart endpoints round-trip")
    # Add → list → update qty → remove.
    if real_rid:
        r = s.post(BASE + "/api/portal/student/cart/add",
                   json={"reward_id": real_rid, "quantity": 1}, timeout=30)
        added = r.json() if r.status_code == 200 else {}
        check(f"cart/add → 200 (items_count={added.get('items_count')})",
              r.status_code == 200 and added.get("ok"))
        r = s.get(BASE + "/api/portal/student/cart", timeout=30)
        cart = r.json() if r.status_code == 200 else {}
        items = cart.get("items") or []
        check(f"cart/get → {len(items)} item(s)",
              r.status_code == 200 and cart.get("ok") and len(items) >= 1)
        if items:
            cid = items[0].get("cart_id")
            r = s.put(BASE + f"/api/portal/student/cart/{cid}/quantity",
                      json={"quantity": 3}, timeout=30)
            check(f"cart qty update → {r.json().get('total')} total",
                  r.status_code == 200 and r.json().get("ok"))
            r = s.delete(BASE + f"/api/portal/student/cart/{cid}", timeout=30)
            check("cart row delete → 200",
                  r.status_code == 200 and r.json().get("ok"))
        # Cart checkout — empty cart → 400.
        r = s.post(BASE + "/api/portal/student/cart/checkout",
                   json={}, timeout=30)
        j = r.json() if r.status_code == 400 else {}
        check(f"cart checkout on empty → 400 ({r.status_code})",
              r.status_code == 400
              and "السلة فارغة" == (j.get("error") or ""))

    # 5. Cancel endpoint — 404 path (no row).
    print("\n[G15.5] cancel endpoint")
    r = s.post(BASE + "/api/portal/student/redemptions/999999/cancel",
               json={}, timeout=30)
    j = r.json() if r.status_code == 404 else {}
    check(f"cancel missing rid → 404 ({r.status_code})",
          r.status_code == 404
          and "الطلب غير موجود" == (j.get("error") or ""))

    # 6. Legacy redeem → 410.
    print("\n[G15.7] legacy /redeem deprecated")
    if real_rid:
        r = s.post(BASE + "/api/portal/student/redeem",
                   json={"reward_id": real_rid}, timeout=30)
        check(f"legacy /redeem returns 410 ({r.status_code})",
              r.status_code == 410
              and "use_instead" in r.text)

    # 7. Points-page HTML — source-grep the deployed body.
    print("\n[G15.x] points page HTML markup")
    r = s.get(BASE + "/portal/parent-hub/points", timeout=30)
    html = r.text if r.status_code == 200 else ""
    print(f"    (status={r.status_code}, html_len={len(html)})")
    check("/portal/parent-hub/points → 200",
          r.status_code == 200 and len(html) > 5000)
    check("3-card balance markup deployed",
          ".bal-cards{display:grid" in html
          and 'class="bal-card available"' in html)
    # G17: direct-order button removed. Cart is the sole purchase
    # path now. G16's "أضف للسلة" label is what the renderer ships.
    check("Cart-only reward card deployed",
          "🛒 أضف للسلة" in html
          and "⚡ طلب مباشر" not in html
          and 'class="reward-actions"' in html)
    check("Cart sub-pane deployed",
          'id="pane-cart"' in html and 'data-sub="cart"' in html)
    check("History 'طلباتي' sub-pane deployed",
          "<h2>📋 طلباتي</h2>" in html
          and "📨 قيد الموافقة" in html)
    check("Insufficient-balance modal deployed",
          'id="balLow"' in html
          and "function showInsufficientBalance(" in html)

    # 8. /redemptions returns rejection_reason field.
    r = s.get(BASE + "/api/portal/student/redemptions", timeout=30)
    rj = r.json() if r.status_code == 200 else {}
    sample = (rj.get("rows") or [{}])[0] if rj.get("rows") else {}
    check("/redemptions includes rejection_reason field",
          rj.get("ok") and (
              "rejection_reason" in sample or len(rj.get("rows") or []) == 0))

    # 9. Admin still works — source filter, redemptions list.
    print("\n[regression] admin side intact")
    a = requests.Session()
    a.headers.update({"User-Agent": "g15-verify/1.0"})
    a.post(BASE + "/login",
           data={"username": "admin_test", "password": "TestAdmin2026!"},
           timeout=30)
    r = a.get(BASE + "/api/points/history?source=student_portal&limit=10",
              timeout=30)
    aj = r.json() if r.status_code == 200 else {}
    print(f"    student_portal-filtered history → "
          f"status={r.status_code}, rows={len(aj.get('rows') or [])}")
    check("admin history filter accepts source=student_portal",
          r.status_code == 200 and aj.get("ok"))
    r = a.get(BASE + "/api/points/redemptions", timeout=30)
    check(f"admin /redemptions list still works ({r.status_code})",
          r.status_code == 200 and r.json().get("ok"))

    print("\n" + "=" * 60)
    if failed:
        print(f"G15 PROD VERIFY — FAILED ({len(failed)})")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("G15 PROD VERIFY — ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
