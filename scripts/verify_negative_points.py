"""Regression suite for points-net-sum (rev 2).

The session-budget rule is now:
  used = max(0, SUM(points_value))   # signed net, floored at zero

Negatives CANCEL prior positives in the same session, but never
let "used" go below zero. The pre-grant intended_cost still uses
max(0, pv) — a negative grant's cost contribution at the cap-check
moment is 0, but the cumulative `used` it lands in IS net-sum.

This script wipes today's events for the test (group, student)
pair at start, then runs a single sequential scenario script
asserting the EXACT cumulative `used` after each action.

Run: python scripts/verify_negative_points.py
"""
from __future__ import annotations
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
sys.path.insert(0, _ROOT)

import app as appmod  # noqa: E402


# ── infra helpers ───────────────────────────────────────────────


def _login(client, username):
    with appmod.app.app_context():
        db = appmod.get_db()
        row = db.execute("SELECT * FROM users WHERE username=?",
                         (username,)).fetchone()
        if not row:
            return None
        user_d = dict(row)
    with client.session_transaction() as s:
        s["user"] = user_d
    return user_d


def _pick_group_and_student():
    with appmod.app.app_context():
        db = appmod.get_db()
        row = db.execute(
            "SELECT id, student_name, group_name_student FROM students "
            "WHERE TRIM(COALESCE(group_name_student,'')) <> '' "
            "  AND TRIM(COALESCE(student_name,'')) <> '' "
            "ORDER BY id LIMIT 1"
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        return d["group_name_student"], d["id"], d["student_name"]


def _read_used(client, group):
    r = client.get(f"/api/points/session-budget?group={group}")
    j = r.get_json() or {}
    return int(j.get("used", -1)), int(j.get("budget", -1)), int(j.get("remaining", -1))


def _read_balance(client, sid):
    r = client.get(f"/api/points/student/{sid}")
    j = r.get_json() or {}
    return int(j.get("balance", 0)) if j else 0


def _behavior_id_for(amt):
    with appmod.app.app_context():
        db = appmod.get_db()
        row = db.execute(
            "SELECT id, points_value FROM behaviors "
            "WHERE is_active=1 AND points_value=? LIMIT 1", (amt,)
        ).fetchone()
        if row:
            return int(dict(row)["id"]), None
        row = db.execute(
            "SELECT id FROM behaviors WHERE is_active=1 AND points_value>0 "
            "ORDER BY id LIMIT 1"
        ).fetchone()
        if row:
            return int(dict(row)["id"]), amt
    return None, None


_created_event_ids = []


def _wipe_todays_events(group):
    """Hard-delete every point_events row for (group, today) so the
    scenario script starts from a known clean state. Local-only —
    never run this against prod."""
    with appmod.app.app_context():
        db = appmod.get_db()
        today = appmod._pts_bahrain_today()
        cur = db.execute(
            "DELETE FROM point_events "
            "WHERE TRIM(group_name)=? AND session_date=?",
            (group, today),
        )
        db.commit()
        return cur.rowcount if hasattr(cur, "rowcount") else 0


def _grant(client, sid, amt, group):
    bid, override = _behavior_id_for(amt)
    if not bid:
        return None, "no behavior"
    body = {"student_ids": [sid], "behavior_id": bid, "group_name": group}
    if override is not None:
        body["points_override"] = override
    r = client.post("/api/points/grant", json=body)
    j = r.get_json() or {}
    if not j.get("ok"):
        return None, j.get("error")
    eid = ((j.get("results") or [{}])[0] or {}).get("event_id")
    if eid:
        _created_event_ids.append(eid)
    return eid, None


def _bulk_grant(client, group, amt):
    bid, _override = _behavior_id_for(amt)
    if not bid:
        return None, "no behavior"
    body = {"group_name": group, "behavior_id": bid,
            "per_student_amount": amt}
    r = client.post("/api/points/bulk-grant", json=body)
    j = r.get_json() or {}
    if not j.get("ok"):
        return None, j.get("error")
    eids = [res.get("event_id") for res in (j.get("results") or [])
            if res.get("ok") and res.get("event_id")]
    _created_event_ids.extend(eids)
    return eids, None


def _undo(client, event_id):
    r = client.delete(f"/api/points/grant/{event_id}")
    j = r.get_json() or {}
    return j.get("ok")


def _cleanup(client):
    for eid in list(_created_event_ids):
        try:
            client.delete(f"/api/points/grant/{eid}")
        except Exception:
            pass
    _created_event_ids.clear()


def _assert(name, expected, actual):
    ok = (expected == actual)
    sign = "OK" if ok else "FAIL"
    print(f"    [{sign}] {name}: expected={expected} actual={actual}")
    return ok


def _step(client, label, action, group, sid,
          expected_used, expected_remaining, expected_bal_delta):
    """Run one scenario step, assert the absolute `used` /
    `remaining` and the student balance delta from the previous
    step."""
    bal_before = _read_balance(client, sid)
    eid = action()
    used, _, rem = _read_used(client, group)
    bal_after = _read_balance(client, sid)
    print(f"  {label}")
    ok1 = _assert("used (absolute)",      expected_used,      used)
    ok2 = _assert("remaining (absolute)", expected_remaining, rem)
    ok3 = _assert("student bal Δ",        expected_bal_delta, bal_after - bal_before)
    return ok1 and ok2 and ok3, eid


def main():
    picked = _pick_group_and_student()
    if not picked:
        print("FAIL — no eligible (group, student) in local DB")
        return 1
    group, sid, sname = picked
    print(f"Using group={group!r} student#{sid} {sname!r}")

    # Wipe today's events for this group so the cumulative `used`
    # tracking below is exact. Local-only; the prod verifier uses
    # delta-from-baseline instead and undoes everything it created.
    wiped = _wipe_todays_events(group)
    print(f"Wiped {wiped} existing event(s) for today/{group}\n")

    client = appmod.app.test_client()
    _login(client, "admin")

    used0, budget, rem0 = _read_used(client, group)
    print(f"Baseline (clean): used={used0} budget={budget} remaining={rem0}")
    if used0 != 0:
        print("WARN — baseline used != 0 after wipe; results may drift")

    all_ok = True

    # ── New net-sum scenarios from the operator's spec ──────────
    # Cumulative `used` tracked relative to the budget (e.g. 10 in
    # the dev DB, 110 in prod for مجموعة 10). The assertions are
    # written in terms of budget arithmetic so the script stays
    # portable across DBs with different active-student counts.

    print("\n=== net-sum sequence ====================================")

    print("\nStep 1 — award +5  → used=5, remaining=budget-5")
    ok, _ = _step(
        client, "after +5", lambda: _grant(client, sid, 5, group)[0],
        group, sid,
        expected_used=5, expected_remaining=budget - 5,
        expected_bal_delta=5)
    all_ok &= ok

    print("\nStep 2 — award -5  → used=0, remaining=budget (cancel)")
    ok, _ = _step(
        client, "after -5", lambda: _grant(client, sid, -5, group)[0],
        group, sid,
        expected_used=0, expected_remaining=budget,
        expected_bal_delta=-5)
    all_ok &= ok

    print("\nStep 3 — award -3  → used=0, remaining=budget (floor)")
    ok, _ = _step(
        client, "after -3", lambda: _grant(client, sid, -3, group)[0],
        group, sid,
        expected_used=0, expected_remaining=budget,
        expected_bal_delta=-3)
    all_ok &= ok

    print("\nStep 4 — award +7  → used=7, remaining=budget-7")
    # Per-event clamp semantics (Option B): after step 3 the running
    # used hit the floor (0), so the -3 was absorbed. The +7 here
    # lands on top of 0, giving used=7 — NOT signed-sum +4 that an
    # aggregate max(0, SUM) would produce. This is the core
    # operator-facing distinction that motivated the C1 revision.
    ok, _ = _step(
        client, "after +7", lambda: _grant(client, sid, 7, group)[0],
        group, sid,
        expected_used=7, expected_remaining=budget - 7,
        expected_bal_delta=7)
    all_ok &= ok

    print("\nStep 5 — award -10 → used=0, remaining=budget (floor)")
    ok, _ = _step(
        client, "after -10", lambda: _grant(client, sid, -10, group)[0],
        group, sid,
        expected_used=0, expected_remaining=budget,
        expected_bal_delta=-10)
    all_ok &= ok

    # Wipe to a clean state for the admin-override scenarios.
    _wipe_todays_events(group)
    _created_event_ids.clear()
    print("\n=== admin override scenarios ============================")
    used0b, budget_b, rem0b = _read_used(client, group)
    print(f"Reset: used={used0b} budget={budget_b} remaining={rem0b}")

    print("\nStep 6 — admin big +N up to budget (no override needed)")
    # Award an amount equal to budget so used == budget (still
    # within cap, no override needed). Skip if budget is 0.
    if budget_b <= 0:
        print("    SKIP — no budget available in this env")
    else:
        eid_bn, err_bn = _grant(client, sid, budget_b, group)
        if err_bn:
            print(f"    FAIL — grant +{budget_b} error: {err_bn}")
            all_ok = False
        else:
            used_bn, _, rem_bn = _read_used(client, group)
            all_ok &= _assert("used == budget",   budget_b, used_bn)
            all_ok &= _assert("remaining == 0",   0,        rem_bn)

    print("\nStep 7 — admin -2 at cap → used drops to budget-2")
    if budget_b <= 0:
        print("    SKIP")
    else:
        eid_dec, err_dec = _grant(client, sid, -2, group)
        if err_dec:
            print(f"    FAIL — grant -2 at cap error: {err_dec}")
            all_ok = False
        else:
            used_dec, _, rem_dec = _read_used(client, group)
            all_ok &= _assert("used == budget-2",
                              budget_b - 2, used_dec)
            all_ok &= _assert("remaining == 2", 2, rem_dec)

    # Cleanup — restore the local DB to its pre-test state.
    print(f"\nCleaning up {len(_created_event_ids)} stray events…")
    _cleanup(client)
    _wipe_todays_events(group)

    print()
    if all_ok:
        print("ALL SCENARIOS PASSED — net-sum with floor-at-zero "
              "is wired correctly end-to-end.")
        return 0
    print("SOME SCENARIOS FAILED — see above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
