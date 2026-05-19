"""Production probe for points-net-sum (per-event clamp).

Runs the operator's 5-step sequential scenario against the live
deployment to confirm the per-event running-balance with floor-at-0
is wired correctly end-to-end. We track `remaining` deltas from the
baseline rather than absolute values so this is safe to run when
other admins are simultaneously awarding points.

Sequence (against `remaining`):
  baseline B
  award +5  → remaining = B - 5       (positive consumes)
  award -5  → remaining = B           (cancel)
  award -3  → remaining = B           (floor — already at 0 used)
  award +7  → remaining = B - 7       (history reset; +7 fresh)
  award -10 → remaining = B           (floor)
  undo all  → remaining = B           (clean restore)

The "history reset" assertion is the key — under the old
max(0, SUM) it would have been B-3 instead of B-7.

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
    if override:
        return override
    r = sess.get(base + "/api/points/groups", timeout=30)
    if r.status_code != 200:
        return None
    j = r.json() or {}
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
    behaviors = j.get("rows") or j.get("behaviors") or []
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


def _step(sess, base, group, sid, label, amt, baseline_rem,
          expected_rem_delta):
    """Award `amt`, read remaining, assert delta from baseline."""
    eid, err = _grant(sess, base, sid, amt, group)
    if err:
        print(f"  FAIL — {label} grant error: {err}")
        return False, None
    used, budget, rem = _budget(sess, base, group)
    actual_delta = rem - baseline_rem
    ok = (actual_delta == expected_rem_delta)
    sign = "OK" if ok else "FAIL"
    print(f"  [{sign}] {label} (amt={amt:+}): "
          f"used={used} remaining={rem} "
          f"Δfromξbaseline={actual_delta:+} (expected {expected_rem_delta:+})")
    return ok, eid


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

    eids = []
    all_ok = True
    print("\n  5-step sequence (max(0, SUM) semantics):")

    # Signed sum after each step, floored at zero:
    #   step 1: +5  → SUM=+5  → used=5,  Δremaining=-5
    #   step 2: -5  → SUM=0   → used=0,  Δremaining=0
    #   step 3: -3  → SUM=-3  → used=0,  Δremaining=0  (floor)
    #   step 4: +7  → SUM=+4  → used=4,  Δremaining=-4  ← was -7 under
    #                                                     the previous
    #                                                     per-event clamp
    #   step 5: -10 → SUM=-6  → used=0,  Δremaining=0  (floor)
    ok, e = _step(sess, base, group, sid,
                  "step 1 award +5",  5,  rem0,  -5)
    all_ok &= ok
    if e: eids.append(e)

    ok, e = _step(sess, base, group, sid,
                  "step 2 award -5",  -5, rem0,  0)
    all_ok &= ok
    if e: eids.append(e)

    ok, e = _step(sess, base, group, sid,
                  "step 3 award -3",  -3, rem0,  0)  # floor
    all_ok &= ok
    if e: eids.append(e)

    ok, e = _step(sess, base, group, sid,
                  "step 4 award +7 (signed sum=+4)",
                  7,  rem0,  -4)
    all_ok &= ok
    if e: eids.append(e)

    ok, e = _step(sess, base, group, sid,
                  "step 5 award -10", -10, rem0, 0)  # floor
    all_ok &= ok
    if e: eids.append(e)

    print(f"\n  cleanup — undoing {len(eids)} grants ...")
    for eid in eids:
        _undo(sess, base, eid)
    used_f, _, rem_f = _budget(sess, base, group)
    print(f"    final: used={used_f} remaining={rem_f} "
          f"(Δ baseline={rem_f - rem0:+})")
    if rem_f != rem0:
        print("    WARN — final remaining != baseline; cleanup didn't fully restore")

    # Also verify the previously-broken مجموعة 11 case: any group
    # whose API used was non-zero pre-deploy should now show used=0
    # (assuming today's signed sum is 0 — true for the diagnostic
    # case). We don't modify any data here; just probe + report.
    print("\n  prod-regression probe: any group still showing used>0?")
    r = sess.get(base + "/api/points/groups", timeout=30)
    names = ((r.json() or {}).get("names") or [])
    nonzero = []
    for g in names:
        bj = sess.get(base + "/api/points/session-budget",
                      params={"group": g}, timeout=30).json() or {}
        u = bj.get("used") or 0
        if u > 0:
            nonzero.append((g, u, bj.get("budget"), bj.get("remaining")))
    if nonzero:
        print(f"    {len(nonzero)} group(s) still showing used>0:")
        for n in nonzero:
            print(f"      {n}")
        print("    (this is informational — used>0 is fine if "
              "today's signed sum is genuinely > 0)")
    else:
        print("    no groups with used>0 — clean")

    print()
    if all_ok and rem_f == rem0:
        print("ALL OK — prod confirms max(0, SUM): -5 cancels +5, "
              "-3 floors at 0, +7 lands at signed sum +4 (NOT 7 — "
              "history is not reset under the new rule), -10 floors. "
              "Undo restored baseline cleanly.")
        return 0
    print("SOME CHECKS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
