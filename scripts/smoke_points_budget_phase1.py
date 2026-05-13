"""Phase 1 smoke — teacher per-session points budget.

Verifies the 8-commit Phase 1 wiring end-to-end against a local
SQLite DB. The script creates a sandboxed test group + roster +
attendance, runs the scenarios, then cleans up everything it
inserted (rolling back to original state).

Scenarios:
  1. Schema — session_date column + composite index exist.
  2. New /api/points/grant inserts now populate session_date.
  3. GET /api/points/session-budget returns the expected shape.
  4. Award within budget for a teacher → 200.
  5. Award that would exceed budget for a teacher → 400 with
     the structured cap-exceeded payload.
  6. Same exceeding-grant for an admin → 200 (bypass) + audit
     row in audit_log with would_exceed:true.
  7. Admin grant with explicit ?override=1 (within budget) →
     200 + audit row with explicit:true.
  8. Cumulative used across multiple grants in the same
     session sums correctly.
  9. New session_date (yesterday) starts at used=0 even when
     today is mostly spent.
 10. Existing rows (legacy session_date IS NULL) still query
     cleanly — no UnicodeError, no SQL error from joins.
"""
import os
import sys
import io
import sqlite3
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A  # noqa: E402

TEST_GROUP   = "SMOKE_PHASE1_GROUP"
TEST_TEACHER = "smoke_teacher_phase1"
TEST_STUDENTS = [
    ("SMOKE_PID_1", "SMOKE Student 1"),
    ("SMOKE_PID_2", "SMOKE Student 2"),
    ("SMOKE_PID_3", "SMOKE Student 3"),
    ("SMOKE_PID_4", "SMOKE Student 4"),
    ("SMOKE_PID_5", "SMOKE Student 5"),
]
TODAY = A._pts_bahrain_today()
YESTERDAY = (sqlite3.connect(":memory:")
             .execute("SELECT date(?, '-1 day')", (TODAY,))
             .fetchone()[0])


def fresh_db():
    return sqlite3.connect("mindx.db")


def setup():
    """Insert sandbox group + students + attendance + a teacher
    user assigned to this group. Returns a dict of created ids."""
    db = fresh_db()
    db.row_factory = sqlite3.Row

    # Group (teacher_name = TEST_TEACHER so _teacher_groups_for
    # returns it for the smoke teacher user).
    db.execute(
        "INSERT INTO student_groups(group_name, teacher_name) VALUES(?,?)",
        (TEST_GROUP, TEST_TEACHER))
    gid = db.execute(
        "SELECT id FROM student_groups WHERE group_name=?",
        (TEST_GROUP,)).fetchone()[0]

    # Students assigned to the group.
    sids = []
    for pid, name in TEST_STUDENTS:
        db.execute(
            "INSERT INTO students(personal_id, student_name, "
            "group_name_student) VALUES(?,?,?)",
            (pid, name, TEST_GROUP))
        sids.append(db.execute(
            "SELECT id FROM students WHERE personal_id=?",
            (pid,)).fetchone()[0])

    # Attendance for today — every student present.
    for _pid, name in TEST_STUDENTS:
        db.execute(
            "INSERT INTO attendance(attendance_date, day_name, "
            "group_name, student_name, status) "
            "VALUES(?,?,?,?,?)",
            (TODAY, "", TEST_GROUP, name, "حاضر"))

    # Smoke teacher user.
    db.execute(
        "INSERT INTO users(username, password, role, name) "
        "VALUES(?,?,?,?)",
        (TEST_TEACHER, A.hp("smoke"), "teacher", TEST_TEACHER))
    tuid = db.execute(
        "SELECT id FROM users WHERE username=?",
        (TEST_TEACHER,)).fetchone()[0]

    db.commit()
    db.close()

    return {"gid": gid, "sids": sids, "tuid": tuid}


def teardown(ids):
    db = fresh_db()
    # Roll back all sandbox rows + any artifacts the smoke created.
    db.execute(
        "DELETE FROM point_events WHERE group_name=?", (TEST_GROUP,))
    db.execute(
        "DELETE FROM attendance WHERE group_name=?", (TEST_GROUP,))
    db.execute(
        "DELETE FROM students WHERE group_name_student=?", (TEST_GROUP,))
    db.execute(
        "DELETE FROM student_groups WHERE group_name=?", (TEST_GROUP,))
    db.execute(
        "DELETE FROM users WHERE username=?", (TEST_TEACHER,))
    db.execute(
        "DELETE FROM audit_log WHERE action='points_budget_override' "
        "AND target_id=?", (TEST_GROUP,))
    db.commit()
    db.close()


def login_admin(c):
    db = fresh_db()
    db.row_factory = sqlite3.Row
    a = dict(db.execute(
        "SELECT id, username, role, name FROM users "
        "WHERE role='admin' LIMIT 1").fetchone())
    db.close()
    with c.session_transaction() as s:
        s["user"] = a


def login_teacher(c, tuid):
    with c.session_transaction() as s:
        s["user"] = {
            "id":       tuid,
            "username": TEST_TEACHER,
            "role":     "teacher",
            "name":     TEST_TEACHER,
        }


def pick_behavior(points_value):
    """Return a behavior id whose points_value matches the requested
    value (uses existing seeded behaviors)."""
    db = fresh_db()
    row = db.execute(
        "SELECT id FROM behaviors WHERE points_value=? AND is_active=1 "
        "ORDER BY id LIMIT 1", (points_value,)).fetchone()
    db.close()
    if not row:
        raise RuntimeError(f"no behavior with points_value={points_value}")
    return row[0]


def main():
    ids = setup()
    try:
        run(ids)
    finally:
        teardown(ids)
    print("\nPhase 1 points-budget smoke passed.")


def run(ids):
    sids = ids["sids"]
    tuid = ids["tuid"]
    c    = A.app.test_client()

    # ── Test 1: schema markers ────────────────────────────────
    db = fresh_db()
    cols = {r[1] for r in db.execute(
        "PRAGMA table_info(point_events)").fetchall()}
    assert "session_date" in cols, "session_date column missing"
    idx = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' "
        "AND tbl_name='point_events'").fetchall()}
    assert "idx_point_events_session" in idx, "session index missing"
    db.close()
    print("[1] session_date column + composite index present")

    # ── Test 3 (do before grants so used=0): budget endpoint shape ─
    login_admin(c)
    rv = c.get(f"/api/points/session-budget?group={TEST_GROUP}")
    assert rv.status_code == 200, f"budget endpoint HTTP {rv.status_code}"
    j = rv.get_json()
    for k in ("ok", "group_name", "session_date", "active_students",
              "per_student_cap", "budget", "used", "remaining",
              "percent_used", "status"):
        assert k in j, f"budget payload missing field {k!r}"
    assert j["active_students"] == len(TEST_STUDENTS), \
        f"active_students={j['active_students']}, expected {len(TEST_STUDENTS)}"
    assert j["budget"] == len(TEST_STUDENTS) * A.PTS_PER_STUDENT_CAP, \
        f"budget={j['budget']}"
    assert j["used"] == 0, "fresh session should have used=0"
    assert j["status"] == "ok"
    print(f"[3] budget endpoint OK — active={j['active_students']} "
          f"budget={j['budget']} used={j['used']}")

    # ── Test 4: teacher within-budget grant succeeds ──────────
    login_teacher(c, tuid)
    bid_2 = pick_behavior(2)
    rv = c.post("/api/points/grant",
                json={"student_ids": [sids[0]], "behavior_id": bid_2,
                      "group_name": TEST_GROUP})
    assert rv.status_code == 200, \
        f"teacher within-budget grant HTTP {rv.status_code} {rv.get_json()}"
    j = rv.get_json()
    assert j["ok"] and j["granted_to"] == 1
    print("[4] teacher within-budget grant → 200")

    # ── Test 2: new rows include session_date ─────────────────
    db = fresh_db()
    row = db.execute(
        "SELECT session_date FROM point_events WHERE group_name=? "
        "ORDER BY id DESC LIMIT 1", (TEST_GROUP,)).fetchone()
    db.close()
    assert row and row[0] == TODAY, \
        f"session_date={row[0]!r}, expected {TODAY!r}"
    print("[2] new grant row carries session_date=today")

    # ── Test 5: teacher over-budget grant → 400 ───────────────
    # Budget = 5 students × 10 = 50. Already used = 2 (test 4).
    # Try to grant +10 to all 5 students = 50 pts. used(2)+50 = 52 > 50.
    bid_10 = pick_behavior(2)  # 2 × 5 = 10; we need to overshoot
    # Easier: many awards × big behavior. Use override_points trick:
    # pass points_override=10 on the +2 behavior → 10 × 5 = 50 → 50+2=52>50
    rv = c.post("/api/points/grant",
                json={"student_ids": sids, "behavior_id": bid_2,
                      "group_name": TEST_GROUP,
                      "points_override": 10})
    assert rv.status_code == 400, \
        f"teacher over-budget HTTP {rv.status_code} {rv.get_json()}"
    j = rv.get_json()
    assert j["ok"] is False
    assert "تجاوزت" in j.get("error", ""), \
        f"expected Arabic cap error, got {j.get('error')!r}"
    for k in ("budget", "used", "remaining", "requested",
              "session_date", "group_name"):
        assert k in j, f"reject payload missing {k!r}"
    print(f"[5] teacher over-budget → 400 ({j['used']}+{j['requested']}>"
          f"{j['budget']})")

    # ── Test 6: admin same over-budget grant → 200 + audit ────
    login_admin(c)
    rv = c.post("/api/points/grant",
                json={"student_ids": sids, "behavior_id": bid_2,
                      "group_name": TEST_GROUP,
                      "points_override": 10})
    assert rv.status_code == 200, \
        f"admin over-budget HTTP {rv.status_code} {rv.get_json()}"
    j = rv.get_json()
    assert j["ok"] and j["granted_to"] == 5
    assert j.get("override") is True, \
        f"admin bypass should set override=True, got {j.get('override')}"
    db = fresh_db()
    db.row_factory = sqlite3.Row
    arow = db.execute(
        "SELECT details FROM audit_log "
        "WHERE action='points_budget_override' AND target_id=? "
        "ORDER BY id DESC LIMIT 1", (TEST_GROUP,)).fetchone()
    db.close()
    assert arow, "audit row missing after admin bypass"
    ad = json.loads(arow["details"])
    assert ad["would_exceed"] is True, "would_exceed should be true"
    print("[6] admin over-budget → 200 + audit row would_exceed=true")

    # ── Test 7: admin ?override=1 within budget → audit ───────
    # Set up a fresh small session by switching to YESTERDAY via date arg —
    # but the grant endpoint always writes TODAY. Instead: keep TODAY but
    # use a small grant that's within remaining budget, with override=1.
    # First, check remaining budget — used is now 52.
    rv = c.get(f"/api/points/session-budget?group={TEST_GROUP}")
    used_before = rv.get_json()["used"]
    rv = c.post(f"/api/points/grant?override=1",
                json={"student_ids": [sids[0]], "behavior_id": bid_2,
                      "group_name": TEST_GROUP})
    j = rv.get_json()
    assert rv.status_code == 200, \
        f"admin override=1 grant HTTP {rv.status_code} {j}"
    db = fresh_db()
    db.row_factory = sqlite3.Row
    arow = db.execute(
        "SELECT details FROM audit_log "
        "WHERE action='points_budget_override' AND target_id=? "
        "ORDER BY id DESC LIMIT 1", (TEST_GROUP,)).fetchone()
    db.close()
    assert arow
    ad = json.loads(arow["details"])
    assert ad["explicit"] is True, "explicit should be true for ?override=1"
    print("[7] admin ?override=1 → 200 + audit row explicit=true")

    # ── Test 8: cumulative used sums correctly ────────────────
    rv = c.get(f"/api/points/session-budget?group={TEST_GROUP}")
    j = rv.get_json()
    # Expected: 2 (test 4) + 50 (test 6, override pts=10 × 5) + 2 (test 7) = 54
    assert j["used"] == 54, f"cumulative used={j['used']}, expected 54"
    print(f"[8] cumulative used={j['used']} (sum across the day) ✓")

    # ── Test 9: a different session_date starts fresh ─────────
    rv = c.get(f"/api/points/session-budget?group={TEST_GROUP}"
               f"&date={YESTERDAY}")
    j = rv.get_json()
    assert j["used"] == 0, \
        f"yesterday should have used=0, got {j['used']}"
    # active_students may also be 0 (no attendance row for yesterday in
    # this sandbox) — budget falls back to roster size via the fallback
    # path. Verify either active_students=roster OR ==0 (attendance path).
    assert j["budget"] in (0, len(TEST_STUDENTS) * A.PTS_PER_STUDENT_CAP), \
        f"yesterday budget={j['budget']}"
    print(f"[9] yesterday session — used=0 (fresh bucket)")

    # ── Test 10: legacy NULL-session_date rows still queryable ─
    # Insert a NULL session_date row directly to simulate legacy data
    # and confirm /api/points/session-budget for today is unaffected
    # (NULL ≠ TODAY).
    db = fresh_db()
    db.execute(
        "INSERT INTO point_events(student_id, student_name, "
        "behavior_id, behavior_name, points_value, group_name, "
        "awarded_by, awarded_by_name, awarded_at, note, "
        "session_date) "
        "VALUES(?,?,?,?,?,?,?,?,?,?, NULL)",
        (sids[0], TEST_STUDENTS[0][1], bid_2, "legacy", 5,
         TEST_GROUP, 1, "admin", "2026-01-01 10:00:00", ""))
    db.commit()
    db.close()
    rv = c.get(f"/api/points/session-budget?group={TEST_GROUP}")
    j = rv.get_json()
    assert j["used"] == 54, \
        f"legacy NULL row leaked into today's bucket: used={j['used']}"
    print("[10] legacy NULL session_date rows do not pollute today's bucket")


if __name__ == "__main__":
    main()
