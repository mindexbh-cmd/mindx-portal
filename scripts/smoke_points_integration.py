"""Phase 1 + 2 + 3 integration smoke.

End-to-end happy path + key error paths against a sandboxed
group. Covers the cap, the per-student counter, the absent
block, the undo, the stats endpoint, and the bulk-grant — in
the same sequence a teacher would experience them.

The smoke creates its own fixtures (group, 5 students,
attendance, teacher user) and tears them down on exit — safe
to re-run.

Run:   python scripts/smoke_points_integration.py
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

TEST_GROUP   = "SMOKE_INT_GROUP"
TEST_TEACHER = "smoke_int_teacher"
TEST_STUDENTS = [
    ("SMOKE_INT_PID_1", "SMOKE Int Student 1"),
    ("SMOKE_INT_PID_2", "SMOKE Int Student 2"),
    ("SMOKE_INT_PID_3", "SMOKE Int Student 3"),
    ("SMOKE_INT_PID_4", "SMOKE Int Student 4"),
    ("SMOKE_INT_PID_5", "SMOKE Int Student 5"),
]
TODAY = A._pts_bahrain_today()


def fresh_db():
    return sqlite3.connect("mindx.db")


def setup():
    db = fresh_db()
    db.row_factory = sqlite3.Row
    db.execute(
        "INSERT INTO student_groups(group_name, teacher_name) VALUES(?,?)",
        (TEST_GROUP, TEST_TEACHER))
    gid = db.execute(
        "SELECT id FROM student_groups WHERE group_name=?",
        (TEST_GROUP,)).fetchone()[0]
    sids = []
    for pid, name in TEST_STUDENTS:
        db.execute(
            "INSERT INTO students(personal_id, student_name, "
            "group_name_student) VALUES(?,?,?)", (pid, name, TEST_GROUP))
        sids.append(db.execute(
            "SELECT id FROM students WHERE personal_id=?",
            (pid,)).fetchone()[0])
    # All present today.
    for _pid, name in TEST_STUDENTS:
        db.execute(
            "INSERT INTO attendance(attendance_date, day_name, "
            "group_name, student_name, status) VALUES(?,?,?,?,?)",
            (TODAY, "", TEST_GROUP, name, "حاضر"))
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


def teardown():
    db = fresh_db()
    db.execute("DELETE FROM point_events WHERE group_name=?", (TEST_GROUP,))
    db.execute("DELETE FROM attendance   WHERE group_name=?", (TEST_GROUP,))
    db.execute("DELETE FROM students     WHERE group_name_student=?",
               (TEST_GROUP,))
    db.execute("DELETE FROM student_groups WHERE group_name=?", (TEST_GROUP,))
    db.execute("DELETE FROM users        WHERE username=?", (TEST_TEACHER,))
    db.execute("DELETE FROM audit_log    WHERE target_id=? "
               "AND action IN ('points_budget_override','points_event_undo')",
               (TEST_GROUP,))
    db.commit()
    db.close()


def login_admin(c):
    db = fresh_db(); db.row_factory = sqlite3.Row
    a = dict(db.execute(
        "SELECT id, username, role, name FROM users "
        "WHERE role='admin' LIMIT 1").fetchone())
    db.close()
    with c.session_transaction() as s:
        s["user"] = a


def login_teacher(c, tuid):
    with c.session_transaction() as s:
        s["user"] = {"id": tuid, "username": TEST_TEACHER,
                     "role": "teacher", "name": TEST_TEACHER}


def pick_behavior(points_value):
    db = fresh_db()
    row = db.execute(
        "SELECT id FROM behaviors WHERE points_value=? AND is_active=1 "
        "ORDER BY id LIMIT 1", (points_value,)).fetchone()
    db.close()
    if not row:
        raise RuntimeError(f"no behavior with points_value={points_value}")
    return row[0]


def run():
    ids   = setup()
    sids  = ids["sids"]
    tuid  = ids["tuid"]
    c     = A.app.test_client()
    bid_2 = pick_behavior(2)

    # 1 — Phase 1: schema + budget endpoint
    login_admin(c)
    rv = c.get(f"/api/points/session-budget?group={TEST_GROUP}")
    assert rv.status_code == 200
    j = rv.get_json()
    assert j["active_students"] == 5
    assert j["budget"] == 50
    assert j["used"] == 0
    print("[1] Phase 1 — budget endpoint: active=5 budget=50 used=0")

    # 2 — Phase 1: teacher within budget
    login_teacher(c, tuid)
    rv = c.post("/api/points/grant",
                json={"student_ids":[sids[0]], "behavior_id":bid_2,
                      "group_name": TEST_GROUP})
    assert rv.status_code == 200
    print("[2] Phase 1 — teacher within-budget grant → 200")

    # 3 — Phase 1: teacher over-budget → 400
    rv = c.post("/api/points/grant",
                json={"student_ids": sids, "behavior_id": bid_2,
                      "group_name": TEST_GROUP,
                      "points_override": 10})
    assert rv.status_code == 400
    print("[3] Phase 1 — teacher over-budget → 400")

    # 4 — Phase 1: admin over-budget → 200 (bypass) + audit
    login_admin(c)
    rv = c.post("/api/points/grant",
                json={"student_ids": sids, "behavior_id": bid_2,
                      "group_name": TEST_GROUP,
                      "points_override": 10})
    assert rv.status_code == 200
    db = fresh_db(); db.row_factory = sqlite3.Row
    arow = db.execute(
        "SELECT details FROM audit_log "
        "WHERE action='points_budget_override' AND target_id=? "
        "ORDER BY id DESC LIMIT 1", (TEST_GROUP,)).fetchone()
    db.close()
    assert arow and json.loads(arow["details"])["would_exceed"] is True
    print("[4] Phase 1 — admin over-budget → 200 + audit would_exceed=true")

    # 5 — Phase 2: per-student counter via session-events
    rv = c.get(f"/api/points/session-events?group={TEST_GROUP}")
    assert rv.status_code == 200
    j = rv.get_json()
    assert sids[0] in [int(k) for k in j["by_student"].keys()]
    assert j["attendance_by_name"], "attendance_by_name should be populated"
    print(f"[5] Phase 2 — session-events: by_student has "
          f"{len(j['by_student'])} entries, attendance keys: "
          f"{len(j['attendance_by_name'])}")

    # 6 — Phase 2: absent block
    db = fresh_db()
    db.execute("UPDATE attendance SET status='غائب' "
               "WHERE group_name=? AND student_name=? "
               "AND attendance_date=?",
               (TEST_GROUP, TEST_STUDENTS[2][1], TODAY))
    db.commit(); db.close()
    rv = c.post("/api/points/grant",
                json={"student_ids":[sids[2]], "behavior_id":bid_2,
                      "group_name": TEST_GROUP})
    assert rv.status_code == 400
    j = rv.get_json()
    assert "غائب" in j.get("error", "") or "absent" in str(j).lower()
    print("[6] Phase 2 — absent student → 400 with structured payload")

    # 7 — Phase 2: undo last award (use a fresh within-budget grant)
    login_teacher(c, tuid)
    # First need to make a new grant — but budget is already at 52.
    # Login as admin to bypass for this test event.
    login_admin(c)
    rv = c.post("/api/points/grant",
                json={"student_ids":[sids[0]], "behavior_id":bid_2,
                      "group_name": TEST_GROUP})
    new_eid = rv.get_json()["results"][0]["event_id"]
    rv = c.delete(f"/api/points/grant/{new_eid}")
    assert rv.status_code == 200
    rv = c.delete(f"/api/points/grant/{new_eid}")
    assert rv.status_code == 404  # already gone
    print("[7] Phase 2 — undo: DELETE→200, re-DELETE→404")

    # 8 — Phase 3: stats endpoint returns valid data
    rv = c.get(f"/api/points/session-stats?group={TEST_GROUP}")
    assert rv.status_code == 200
    j = rv.get_json()
    for k in ("budget", "used", "remaining", "percent_used",
              "active_students", "awarded_count", "skipped_count",
              "top_students", "by_behavior", "undo_count"):
        assert k in j, f"stats payload missing {k!r}"
    assert isinstance(j["top_students"], list)
    assert isinstance(j["by_behavior"], list)
    assert j["undo_count"] >= 1, "C7 above wrote one undo audit row"
    print(f"[8] Phase 3 — stats: top={len(j['top_students'])} "
          f"behaviors={len(j['by_behavior'])} undo={j['undo_count']}")

    # 9 — Phase 3: bulk-grant respects budget (teacher path)
    # Reset some budget: delete everything in this session so the
    # bulk path has a clean slate.
    db = fresh_db()
    db.execute("DELETE FROM point_events WHERE group_name=? "
               "AND session_date=?", (TEST_GROUP, TODAY))
    db.commit(); db.close()
    # Also flip the absent student back to present for fairness.
    db = fresh_db()
    db.execute("UPDATE attendance SET status='حاضر' "
               "WHERE group_name=? AND student_name=? "
               "AND attendance_date=?",
               (TEST_GROUP, TEST_STUDENTS[2][1], TODAY))
    db.commit(); db.close()
    login_teacher(c, tuid)
    rv = c.post("/api/points/bulk-grant",
                json={"group_name": TEST_GROUP, "behavior_id": bid_2,
                      "per_student_amount": 2})
    assert rv.status_code == 200
    j = rv.get_json()
    assert j["granted_to"] == 5
    print(f"[9] Phase 3 — bulk-grant within budget: granted_to={j['granted_to']}")

    # 10 — Phase 3: bulk-grant over budget → 400 for teacher
    rv = c.post("/api/points/bulk-grant",
                json={"group_name": TEST_GROUP, "behavior_id": bid_2,
                      "per_student_amount": 10})
    assert rv.status_code == 400
    print("[10] Phase 3 — bulk-grant over budget → 400 (teacher)")

    # 11 — Phase 3: bulk-grant skips absent
    db = fresh_db()
    db.execute("UPDATE attendance SET status='غائب' "
               "WHERE group_name=? AND student_name=? "
               "AND attendance_date=?",
               (TEST_GROUP, TEST_STUDENTS[4][1], TODAY))
    db.commit(); db.close()
    # Clear and try +1 — that's 4 students × 1 = 4. Budget = 4 active × 10 = 40.
    db = fresh_db()
    db.execute("DELETE FROM point_events WHERE group_name=? "
               "AND session_date=?", (TEST_GROUP, TODAY))
    db.commit(); db.close()
    rv = c.post("/api/points/bulk-grant",
                json={"group_name": TEST_GROUP, "behavior_id": bid_2,
                      "per_student_amount": 1})
    assert rv.status_code == 200
    j = rv.get_json()
    assert j["granted_to"] == 4, f"expected 4 granted, got {j['granted_to']}"
    assert len(j["skipped_absent"]) == 1
    assert j["skipped_absent"][0]["name"] == TEST_STUDENTS[4][1]
    print(f"[11] Phase 3 — bulk-grant absent skip: granted_to=4 "
          f"skipped_absent=1 ({j['skipped_absent'][0]['name']})")

    # 12 — UI sanity: /points/board still renders for this group.
    rv = c.get(f"/points/board/{TEST_GROUP}")
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    for marker in ("pb-budget", "pb-bar-fill", "stats-back",
                   "dist-back", "function refreshBoardState",
                   "function openStatsModal", "function openDistModal"):
        assert marker in html, f"UI marker missing: {marker}"
    print("[12] UI — /points/board renders + all Phase 1/2/3 markers present")

    print("\nFull Phase 1+2+3 integration smoke passed.")


def main():
    try:
        run()
    finally:
        teardown()


if __name__ == "__main__":
    main()
