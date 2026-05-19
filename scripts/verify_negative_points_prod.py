"""Production probe for negative-points-no-session-deduct.

Runs the screenshot-equivalent scenario end-to-end against the
live deployment:

  1. login as admin
  2. pick a real group + student with active points activity
  3. read baseline session balance
  4. award -1 → assert remaining unchanged
  5. award +5 → assert remaining drops by 5
  6. UNDO both grants (clean up) so the prod DB is untouched

Run:
  python scripts/verify_negative_points_prod.py
  python scripts/verify_negative_points_prod.py --group "مجموعة 10"
  python scripts/verify_negative_points_prod.py --base http://localhost:5000
"""
from __future__ import annotations
import argparse
import sys

try:
    import requests
except Exception:
    print("requests not installed — pip install requests", file=sys.stderr)
    sys.exit(2)

DEFAULT_BASE = "https://mindx-portal-1.onrender.com"


def _login(base, username, password):
    s = requests.Session()
    s.headers.update({"User-Agent": "verify_negative_points_prod"})
    r = s.post(base + "/login",
               data={"username": username, "password": password},
               allow_redirects=False, timeout=30)
    if r.status_code not in (302, 303):
        return None, f"login HTTP {r.status_code}"
    return s, None


def _pick_group(sess, base, override=None):
    """If --group is given use it; otherwise pick the first visible
    group with at least one student via /api/points/groups."""
    if override:
        return override
    r = sess.get(base + "/api/points/groups", timeout=30)
    if r.status_code != 200:
        return None
    j = r.json() or {}
    # Endpoint returns {"groups": [{name, ...}], "names": [...]}
    names = j.get("names") or []
    if not names:
        groups = j.get("groups") or []
        names = [g.get("name") or g.get("group_name") for g in groups]
        names = [n for n in names if n]
    if not names:
        return None
    for cand in ("مجموعة 10", "Group 10"):
        if cand in names:
            return cand
    return names[0]


def _first_student_in_group(sess, base, group):
    r = sess.get(base + "/api/points/group", params={"group": group},
                 timeout=30)
    if r.status_code != 200:
        return None
    j = r.json() or {}
    students = j.get("students") or []
    if not students:
        return None
    return students[0].get("id")


def _budget(sess, base, group):
    r = sess.get(base + "/api/points/session-budget",
                 params={"group": group}, timeout=30)
    j = r.json() or {}
    return (j.get("used"), j.get("budget"), j.get("remaining"))


def _pick_behavior(sess, base, want_value):
    r = sess.get(base + "/api/points/behaviors", timeout=30)
    j = r.json() or {}
    # Endpoint returns {"rows": [...]}; older versions may return
    # {"behaviors": [...]}. Accept both.
    behaviors = j.get("rows") or j.get("behaviors") or []
    # Exact-value match first, then a positive fallback for override.
    for b in behaviors:
        if b.get("is_active") and int(b.get("points_value") or 0) == want_value:
            return b.get("id"), None
    for b in behaviors:
        if b.get("is_active") and int(b.get("points_value") or 0) > 0:
            return b.get("id"), want_value  # use as override
    return None, None


def _grant(sess, base, sid, amt, group):
    bid, override = _pick_behavior(sess, base, amt)
    if not bid:
        return None, "no behavior available"
    body = {"student_ids": [sid], "behavior_id": bid, "group_name": group}
    if override is not None:
        body["points_override"] = override
    r = sess.post(base + "/api/points/grant", json=body, timeout=30)
    j = r.json() or {}
    if not j.get("ok"):
        return None, j.get("error")
    eid = ((j.get("results") or [{}])[0] or {}).get("event_id")
    return eid, None


def _undo(sess, base, eid):
    r = sess.delete(base + f"/api/points/grant/{eid}", timeout=30)
    return (r.json() or {}).get("ok", False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--username", default="admin")
    ap.add_argument("--password", default="admin123")
    ap.add_argument("--group", default=None)
    args = ap.parse_args()
    base = args.base.rstrip("/")

    print(f"=== verifying {base} ====================================")
    try:
        v = requests.get(base + "/version", timeout=20).json()
        print(f"  /version sha={v.get('sha')}")
    except Exception as ex:
        print(f"  /version failed: {ex}")
        return 1

    sess, err = _login(base, args.username, args.password)
    if not sess:
        print(f"  LOGIN FAILED: {err}")
        return 1

    group = _pick_group(sess, base, args.group)
    if not group:
        print("  could not resolve a group to test against")
        return 1
    sid = _first_student_in_group(sess, base, group)
    if not sid:
        print(f"  group {group!r} has no students")
        return 1
    print(f"  group={group!r}  student_id={sid}")

    used0, budget0, rem0 = _budget(sess, base, group)
    print(f"  baseline: used={used0} budget={budget0} remaining={rem0}")
    if rem0 is None:
        print("  could not read baseline budget")
        return 1

    # Award -1 — remaining must be unchanged.
    print("\n  step 1 — award -1 ...")
    eid_neg, err = _grant(sess, base, sid, -1, group)
    if err:
        print(f"  FAIL — -1 grant error: {err}")
        return 1
    u, b, rem_after_neg = _budget(sess, base, group)
    delta_neg = rem_after_neg - rem0
    print(f"    after -1: used={u} remaining={rem_after_neg} "
          f"(Δremaining={delta_neg:+})")
    ok_neg = (delta_neg == 0)
    print(f"    {'OK' if ok_neg else 'FAIL'} — remaining unchanged after -1")

    # Award +5 — remaining must drop by 5.
    print("\n  step 2 — award +5 ...")
    eid_pos, err = _grant(sess, base, sid, 5, group)
    if err:
        print(f"  FAIL — +5 grant error: {err}")
        _undo(sess, base, eid_neg)
        return 1
    u, b, rem_after_pos = _budget(sess, base, group)
    delta_pos = rem_after_pos - rem_after_neg
    print(f"    after +5: used={u} remaining={rem_after_pos} "
          f"(Δremaining={delta_pos:+})")
    ok_pos = (delta_pos == -5)
    print(f"    {'OK' if ok_pos else 'FAIL'} — remaining dropped by exactly 5")

    # Cleanup — undo both grants so prod state is restored.
    print("\n  cleanup — undoing both grants ...")
    _undo(sess, base, eid_pos)
    _undo(sess, base, eid_neg)
    u, b, rem_final = _budget(sess, base, group)
    print(f"    final: used={u} remaining={rem_final} "
          f"(Δfrom baseline={rem_final - rem0:+})")

    if ok_neg and ok_pos and rem_final == rem0:
        print("\nALL OK — prod confirms: -1 doesn't touch the balance, "
              "+5 deducts exactly 5, undo restores baseline cleanly.")
        return 0
    print("\nSOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
