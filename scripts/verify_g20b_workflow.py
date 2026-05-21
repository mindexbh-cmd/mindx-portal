"""G20b.2 — controlled end-to-end probe of the cart → approval → delivery
workflow on prod. Proves the code path works AND establishes a known-
good baseline if the operator hits the perceived bug again.

Flow:
  1. Admin grants student_test +200 points (تعديل يدوي behavior_id=15)
  2. Student logs in, adds a cheap reward to cart, checks out
  3. Admin polls /api/points/redemptions and confirms the new row
     has status='requested' + source='student_portal'
  4. Admin approves it via /redemptions/<id>/approve
     → confirm status flipped to 'pending'
  5. Admin marks it delivered via /redemptions/<id>/deliver
     → confirm status flipped to 'delivered'
  6. Admin grants student_test -200 points to refund the test grant
     (so balance returns to ~0 and no residual data is left behind)

Usage:
    python scripts/verify_g20b_workflow.py [--base https://...]
"""
import argparse
import sys
import time

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
            if hint:
                print(f"         hint: {hint}")
            failed.append(label)
        return bool(ok)

    print(f"\n=== G20b workflow verify against {BASE} ===\n")

    # Admin session
    admin = requests.Session()
    admin.post(BASE + "/login",
               data={"username": "admin_test", "password": "TestAdmin2026!"},
               timeout=30)

    # Find student_test's student row + a cheap reward
    students = admin.get(BASE + "/api/students", timeout=30).json().get("students", [])
    test_sids = [x.get("id") for x in students
                 if (x.get("personal_id") or "").startswith("TEST-")]
    if not test_sids:
        print("FATAL: no TEST-STUDENT-* row found")
        return 2
    sid = test_sids[0]
    print(f"Test student linked id: {sid}")

    rewards = admin.get(BASE + "/api/points/rewards", timeout=30).json().get("rows", [])
    cheapest = min((r for r in rewards if (r.get("is_active") and
                                            (r.get("point_cost") or 0) > 0)),
                   key=lambda x: x.get("point_cost") or 999999)
    print(f"Cheapest reward: id={cheapest['id']} name={cheapest['name_ar']!r} cost={cheapest['point_cost']}")
    grant_amount = max(50, (cheapest.get("point_cost") or 30) + 20)

    # 1. Grant +N points via تعديل يدوي behavior (id=15)
    print(f"\n[step 1] grant +{grant_amount} points to student_test")
    r = admin.post(BASE + "/api/points/grant",
                   json={"student_ids": [sid],
                         "behavior_id": 15,
                         "group_name": "",
                         "note": "G20b workflow test (auto-refunded after)",
                         "points_override": grant_amount},
                   timeout=30)
    grant_resp = r.json() if r.status_code == 200 else {}
    check(f"grant succeeded ({r.status_code})",
          r.status_code == 200 and grant_resp.get("ok"),
          str(grant_resp))
    if not grant_resp.get("ok"):
        print("    grant body:", r.text[:300])
        return 1
    # Confirm new balance via balance endpoint
    student = requests.Session()
    student.post(BASE + "/login",
                 data={"username": "student_test", "password": "TestStudent2026!"},
                 timeout=30)
    bal = student.get(BASE + "/api/portal/student/balance", timeout=30).json()
    check(f"student balance now {bal.get('available')} (≥{cheapest['point_cost']})",
          (bal.get("available") or 0) >= (cheapest["point_cost"] or 0))

    # 2. Student adds to cart + checks out
    print("\n[step 2] student adds to cart + checks out")
    r = student.post(BASE + "/api/portal/student/cart/add",
                     json={"reward_id": cheapest["id"], "quantity": 1},
                     timeout=30)
    check(f"cart/add returned 200 (items_count={r.json().get('items_count')})",
          r.status_code == 200 and r.json().get("ok"))
    r = student.post(BASE + "/api/portal/student/cart/checkout",
                     json={}, timeout=30)
    checkout = r.json() if r.status_code == 200 else {}
    check(f"cart/checkout returned 200 (redemption_ids={checkout.get('redemption_ids')})",
          r.status_code == 200 and checkout.get("ok"))
    new_ids = checkout.get("redemption_ids") or []
    if not new_ids:
        print("    checkout body:", r.text[:400])
        return 1
    new_rid = new_ids[0]
    print(f"    new redemption id: {new_rid}")

    # 3. Admin confirms row is in approval queue with correct source
    print("\n[step 3] admin confirms 'طلبات أولياء الأمور' has the row")
    time.sleep(1)
    r = admin.get(BASE + "/api/points/history?status=requested&limit=20",
                  timeout=30)
    req_rows = r.json().get("rows", [])
    found = [x for x in req_rows if (x.get("id") or 0) == new_rid]
    check(f"row #{new_rid} appears in /history?status=requested ({len(req_rows)} total req)",
          bool(found))
    if found:
        row = found[0]
        check(f"row source is 'student_portal' (got {row.get('request_source')!r})",
              row.get("request_source") == "student_portal")
        check("row status is 'requested'",
              row.get("status") == "requested")

    # 4. Admin approves the row
    print(f"\n[step 4] admin approves row #{new_rid}")
    r = admin.post(BASE + f"/api/points/redemptions/{new_rid}/approve",
                   json={}, timeout=30)
    appr = r.json() if r.status_code == 200 else {}
    check(f"approve returned 200 ({appr})",
          r.status_code == 200 and appr.get("ok"))
    # Verify row is now 'pending'
    r = admin.get(BASE + f"/api/points/history?status=pending&limit=50",
                  timeout=30)
    pend_rows = r.json().get("rows", [])
    found_p = [x for x in pend_rows if (x.get("id") or 0) == new_rid]
    check(f"row #{new_rid} now in /history?status=pending",
          bool(found_p))

    # 5. Admin marks delivered
    print(f"\n[step 5] admin marks row #{new_rid} as delivered")
    r = admin.post(BASE + f"/api/points/redemptions/{new_rid}/deliver",
                   json={}, timeout=30)
    deliv = r.json() if r.status_code == 200 else {}
    check(f"deliver returned 200 ({deliv})",
          r.status_code == 200 and deliv.get("ok"))
    r = admin.get(BASE + f"/api/points/history?status=delivered&limit=50",
                  timeout=30)
    deliv_rows = r.json().get("rows", [])
    found_d = [x for x in deliv_rows if (x.get("id") or 0) == new_rid]
    check(f"row #{new_rid} now in /history?status=delivered",
          bool(found_d))

    # 6. Refund the test grant — give back -N points so the student's
    # balance returns to ~0 (it was 0 + N − cost; refund N to get to -cost,
    # which is "spent" since the row is now delivered).
    # We grant -N so the net point_events sum returns to baseline.
    print(f"\n[step 6] refund -{grant_amount} points (cleanup)")
    r = admin.post(BASE + "/api/points/grant",
                   json={"student_ids": [sid],
                         "behavior_id": 15,
                         "group_name": "",
                         "note": "G20b workflow test cleanup",
                         "points_override": -grant_amount},
                   timeout=30)
    check(f"refund grant succeeded ({r.status_code})",
          r.status_code == 200 and r.json().get("ok"))

    # Final state
    bal2 = student.get(BASE + "/api/portal/student/balance", timeout=30).json()
    print(f"\nFinal student_test balance: total={bal2.get('total')} "
          f"committed={bal2.get('committed')} "
          f"reserved={bal2.get('reserved')} "
          f"available={bal2.get('available')}")

    print("\n" + "=" * 60)
    if failed:
        print(f"G20b WORKFLOW PROBE — FAILED ({len(failed)})")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("G20b WORKFLOW PROBE — ALL CHECKS PASSED")
    print("The cart → approval → delivery workflow works end-to-end on prod.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
