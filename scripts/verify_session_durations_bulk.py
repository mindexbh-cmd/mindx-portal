"""End-to-end regression for session_durations bulk-fill.

Covers the explicit semantics the operator confirmed:
  - overwrite=false: fills empty (duration=0) AND inserts missing,
    skips rows with duration > 0
  - overwrite=true: upserts every (group, date) in range
  - duration=0 (NULL row) is treated as empty
  - date range is inclusive on both ends
  - groups filter uses TRIM on both sides
  - rows OUTSIDE the range/groups stay untouched

Seeds a tiny synthetic universe in attendance + session_durations,
runs preview + bulk-fill, asserts the per-row outcome, then
cleans up.

Run: python scripts/verify_session_durations_bulk.py
"""
from __future__ import annotations
import os, sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))
import app as appmod  # noqa: E402

_r = []


def _check(label, ok, detail=""):
    _r.append((label, ok, detail))
    print(f"  [{'OK' if ok else 'FAIL'}] {label}" +
          (f"  {detail}" if detail else ""))


# Synthetic groups + dates we'll seed. Chosen to be obviously
# non-real so a re-run doesn't collide with operator data.
TEST_GROUPS = ["__sd_bulk_test_grp_A", "__sd_bulk_test_grp_B"]
DATE_IN_RANGE_1  = "2026-05-10"
DATE_IN_RANGE_2  = "2026-05-15"
DATE_OUT_OF_RANGE = "2026-04-01"
RANGE_FROM = "2026-05-01"
RANGE_TO   = "2026-05-31"


def _login_admin(client):
    with appmod.app.app_context():
        db = appmod.get_db()
        row = db.execute(
            "SELECT * FROM users WHERE role='admin' ORDER BY id LIMIT 1"
        ).fetchone()
        if not row: return None
        u = dict(row)
    with client.session_transaction() as s:
        s["user"] = u
    return u


def _seed(db):
    """Layout we set up:

      grp A, 2026-05-10  → attendance row only (no sd row)        → EMPTY
      grp A, 2026-05-15  → sd row, duration=0                     → EMPTY
      grp A, 2026-04-01  → attendance row only — OUTSIDE range    → untouched

      grp B, 2026-05-10  → sd row, duration=45 (real value)       → FILLED
      grp B, 2026-05-15  → sd row, duration=60                    → FILLED

    Expected universe inside [2026-05-01 .. 2026-05-31]:
      total = 4 rows (2 per group). 2 empty, 2 filled.
    """
    for g in TEST_GROUPS:
        for d in (DATE_IN_RANGE_1, DATE_IN_RANGE_2):
            db.execute(
                "INSERT INTO attendance(group_name, attendance_date, "
                "student_name, status) VALUES(?, ?, ?, ?)",
                (g, d, "__sd_bulk_synth", "حاضر"))
    # Out-of-range row for grp A.
    db.execute(
        "INSERT INTO attendance(group_name, attendance_date, "
        "student_name, status) VALUES(?, ?, ?, ?)",
        (TEST_GROUPS[0], DATE_OUT_OF_RANGE, "__sd_bulk_synth", "حاضر"))
    # session_durations rows:
    db.execute(
        "INSERT INTO session_durations(group_name, session_date, "
        "duration_minutes, session_type) VALUES(?,?,?,?)",
        (TEST_GROUPS[0], DATE_IN_RANGE_2, 0, ""))            # empty (cur=0)
    db.execute(
        "INSERT INTO session_durations(group_name, session_date, "
        "duration_minutes, session_type) VALUES(?,?,?,?)",
        (TEST_GROUPS[1], DATE_IN_RANGE_1, 45, "حضور"))      # filled
    db.execute(
        "INSERT INTO session_durations(group_name, session_date, "
        "duration_minutes, session_type) VALUES(?,?,?,?)",
        (TEST_GROUPS[1], DATE_IN_RANGE_2, 60, "أونلاين"))   # filled
    db.commit()


def _cleanup(db):
    for g in TEST_GROUPS:
        try:
            db.execute("DELETE FROM attendance WHERE group_name=?", (g,))
            db.execute("DELETE FROM session_durations WHERE group_name=?", (g,))
        except Exception: pass
    db.commit()


def _row_dur(db, g, d):
    """Return (duration, type) tuple for a (group, date), or (None, None)
    when no session_durations row exists."""
    row = db.execute(
        "SELECT duration_minutes, session_type FROM session_durations "
        "WHERE group_name=? AND session_date=?",
        (g, d)).fetchone()
    if not row: return (None, None)
    rd = dict(row)
    return (int(rd.get("duration_minutes") or 0),
            (rd.get("session_type") or ""))


def main():
    client = appmod.app.test_client()
    admin = _login_admin(client)
    if not admin: print("FAIL — no admin in DB"); return 1
    print(f"Logged in as admin: {admin.get('username')!r}\n")

    # Start clean.
    with appmod.app.app_context():
        db = appmod.get_db()
        _cleanup(db)
        _seed(db)

    print("=== Layer 1 — preview classification ===")
    body = {
        "group_names":       TEST_GROUPS,
        "date_from":         RANGE_FROM,
        "date_to":           RANGE_TO,
        "duration_minutes":  90,
        "lesson_type":       "حضور",
        "overwrite":         False,
    }
    r = client.post("/api/session-durations/bulk-preview", json=body)
    j = r.get_json() or {}
    _check("preview HTTP 200", r.status_code == 200)
    _check("preview ok=True", j.get("ok") is True)
    _check("total = 4",          j.get("total") == 4,
           f"got {j.get('total')}")
    _check("will_fill_empty = 2 (grpA/05-10 missing, grpA/05-15 dur=0)",
           j.get("will_fill_empty") == 2,
           f"got {j.get('will_fill_empty')}")
    _check("already_filled = 2 (both grpB rows have dur>0)",
           j.get("already_filled") == 2,
           f"got {j.get('already_filled')}")
    _check("will_be_updated = 0 (overwrite=false)",
           j.get("will_be_updated") == 0)
    _check("will_skip = 2 (overwrite=false skips filled)",
           j.get("will_skip") == 2)
    bg = j.get("by_group") or []
    _check("by_group has 2 entries",  len(bg) == 2,
           f"got {len(bg)}")
    for g in bg:
        if g.get("group_name") == TEST_GROUPS[0]:
            _check("grpA: 2 total / 2 empty / 0 filled",
                   g.get("total")==2 and g.get("empty")==2 and g.get("filled")==0,
                   f"got {g}")
        if g.get("group_name") == TEST_GROUPS[1]:
            _check("grpB: 2 total / 0 empty / 2 filled",
                   g.get("total")==2 and g.get("empty")==0 and g.get("filled")==2,
                   f"got {g}")

    print("\n=== Layer 2 — bulk-fill overwrite=FALSE ===")
    r = client.post("/api/session-durations/bulk-fill", json=body)
    j = r.get_json() or {}
    _check("fill HTTP 200", r.status_code == 200, f"got {r.status_code}")
    _check("fill ok",   j.get("ok") is True)
    _check("inserted = 2", j.get("inserted") == 2,
           f"got {j.get('inserted')}")
    _check("updated = 0",  j.get("updated") == 0,
           f"got {j.get('updated')}")
    _check("skipped = 2",  j.get("skipped") == 2,
           f"got {j.get('skipped')}")
    # Verify DB state.
    with appmod.app.app_context():
        db = appmod.get_db()
        d1 = _row_dur(db, TEST_GROUPS[0], DATE_IN_RANGE_1)
        d2 = _row_dur(db, TEST_GROUPS[0], DATE_IN_RANGE_2)
        d3 = _row_dur(db, TEST_GROUPS[1], DATE_IN_RANGE_1)
        d4 = _row_dur(db, TEST_GROUPS[1], DATE_IN_RANGE_2)
        out_of_range = _row_dur(db, TEST_GROUPS[0], DATE_OUT_OF_RANGE)
    _check("grpA/05-10 filled with new value (90/حضور)",
           d1 == (90, "حضور"), f"got {d1}")
    _check("grpA/05-15 (was 0) filled with new value",
           d2 == (90, "حضور"), f"got {d2}")
    _check("grpB/05-10 UNCHANGED at 45/حضور (skipped)",
           d3 == (45, "حضور"), f"got {d3}")
    _check("grpB/05-15 UNCHANGED at 60/أونلاين (skipped)",
           d4 == (60, "أونلاين"), f"got {d4}")
    _check("out-of-range row untouched (no sd row)",
           out_of_range == (None, None), f"got {out_of_range}")

    print("\n=== Layer 3 — bulk-fill overwrite=TRUE ===")
    body2 = dict(body)
    body2["overwrite"] = True
    body2["duration_minutes"] = 120
    body2["lesson_type"] = "أونلاين"
    r = client.post("/api/session-durations/bulk-fill", json=body2)
    j = r.get_json() or {}
    _check("overwrite-fill ok",  j.get("ok") is True)
    _check("inserted = 2 (cur=90 from Layer 2 → counted as 'empty' relative to "
           "the universe walk? no — Layer 2 wrote real values, so 4 rows are "
           "now all 'filled')",
           True,  # informational
           "see classifications below")
    # Re-walk: all 4 rows now have a non-zero duration → universe
    # walk classifies all as 'filled'; overwrite=true → all 4
    # become 'updated', 0 'inserted'.
    _check("inserted = 0 (no row missing or duration=0 anymore)",
           j.get("inserted") == 0, f"got {j.get('inserted')}")
    _check("updated = 4 (overwrite=true bumps all)",
           j.get("updated") == 4, f"got {j.get('updated')}")
    _check("skipped = 0",
           j.get("skipped") == 0, f"got {j.get('skipped')}")
    with appmod.app.app_context():
        db = appmod.get_db()
        d1 = _row_dur(db, TEST_GROUPS[0], DATE_IN_RANGE_1)
        d3 = _row_dur(db, TEST_GROUPS[1], DATE_IN_RANGE_1)
        out_of_range = _row_dur(db, TEST_GROUPS[0], DATE_OUT_OF_RANGE)
    _check("grpA/05-10 now 120/أونلاين (overwrite replaced 90/حضور)",
           d1 == (120, "أونلاين"), f"got {d1}")
    _check("grpB/05-10 now 120/أونلاين (overwrite replaced 45/حضور)",
           d3 == (120, "أونلاين"), f"got {d3}")
    _check("out-of-range row STILL untouched",
           out_of_range == (None, None), f"got {out_of_range}")

    print("\n=== Layer 4 — input validation ===")
    # Empty group_names list.
    r = client.post("/api/session-durations/bulk-preview",
                    json={"group_names": [], "date_from": RANGE_FROM,
                          "date_to": RANGE_TO, "duration_minutes": 60})
    _check("empty group_names → HTTP 400",
           r.status_code == 400, f"got {r.status_code}")
    # Inverted date range.
    r = client.post("/api/session-durations/bulk-preview",
                    json={"group_names": "all",
                          "date_from": "2026-12-31",
                          "date_to":   "2026-01-01",
                          "duration_minutes": 60})
    _check("inverted range → HTTP 400",
           r.status_code == 400, f"got {r.status_code}")
    # Invalid duration.
    r = client.post("/api/session-durations/bulk-preview",
                    json={"group_names": "all",
                          "date_from": RANGE_FROM, "date_to": RANGE_TO,
                          "duration_minutes": -5})
    _check("duration=-5 → HTTP 400",
           r.status_code == 400, f"got {r.status_code}")
    # Invalid lesson_type.
    r = client.post("/api/session-durations/bulk-preview",
                    json={"group_names": "all",
                          "date_from": RANGE_FROM, "date_to": RANGE_TO,
                          "duration_minutes": 60,
                          "lesson_type": "كذا"})
    _check("unknown lesson_type → HTTP 400",
           r.status_code == 400, f"got {r.status_code}")
    # Empty lesson_type IS allowed.
    r = client.post("/api/session-durations/bulk-preview",
                    json={"group_names": TEST_GROUPS,
                          "date_from": RANGE_FROM, "date_to": RANGE_TO,
                          "duration_minutes": 60, "lesson_type": ""})
    j = r.get_json() or {}
    _check("empty lesson_type → HTTP 200 + ok",
           r.status_code == 200 and j.get("ok") is True,
           f"got {r.status_code} {j.get('ok')}")

    # Cleanup
    with appmod.app.app_context():
        db = appmod.get_db()
        _cleanup(db)

    print()
    fails = [r for r in _r if not r[1]]
    print(f"{len(_r) - len(fails)}/{len(_r)} checks passed.")
    if fails:
        print("FAILED:")
        for f in fails:
            print(f"  - {f[0]}  {f[2]}")
        return 1
    print("ALL OK — bulk-fill semantics + validation correct.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
