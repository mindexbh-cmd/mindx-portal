"""G4.2 — verify /api/attendance/summary reads attendance.class_duration
and aggregates per-session MAX for group totals.

Hermetic Flask test client against a tmp SQLite DB. Three scenarios
cover the impact surfaces called out in discovery:

  S1 — Aligned row: attendance.class_duration matches what session_durations
       would have said. Expected: numbers unchanged from legacy behaviour.

  S2 — Orphan no-SD row: attendance.class_duration='60.0' but no
       session_durations row exists. Legacy code would have returned 0
       for this session; new code must return 60.

  S3 — Pencil-edited row: attendance.class_duration='100' diverges from
       session_durations.duration_minutes=90 for the same (group, date).
       Legacy code returned 90; new code must return 100 in the student's
       hours_total_min.

Plus a MAX-aggregation check:

  S4 — Two students on the same (group, date), one pencil-edited to 100,
       the other on the auto-meta default 60. Group total_minutes for
       that session must be MAX(100, 60) = 100, not 80 (avg) or 60
       (mode) or order-dependent.
"""
import os
import sys
import sqlite3
import tempfile
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DB = os.path.join(tempfile.gettempdir(), "mindx_g4_smoke.db")

if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["DB_PATH"] = TMP_DB
os.environ["DATABASE_URL"] = ""
os.environ.setdefault("SECRET_KEY", "test-secret-g4")
sys.path.insert(0, REPO)
import app as appmod  # noqa: E402


def _seed():
    db = sqlite3.connect(TMP_DB)
    db.execute(
        "INSERT INTO users(username, password, role) VALUES(?, ?, ?)",
        ("g4admin", appmod.hp("G4pwd!"), "admin"),
    )
    db.execute(
        "INSERT INTO student_groups(group_name, session_minutes_normal) "
        "VALUES(?, ?)",
        ("G_G4", "60"),
    )

    # S1 aligned: SD=60, att.class_duration=60, status=حاضر
    db.execute(
        "INSERT INTO attendance(group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type) "
        "VALUES(?,?,?,?,?,?)",
        ("G_G4", "2026-05-01", "Alice", "حاضر", "60", "حضوري"),
    )
    db.execute(
        "INSERT INTO session_durations(group_name, session_date, "
        "                              duration_minutes, session_type) "
        "VALUES(?,?,?,?)",
        ("G_G4", "2026-05-01", 60, "حضور"),
    )

    # S2 orphan: NO SD row, att.class_duration='60.0', status=حاضر
    db.execute(
        "INSERT INTO attendance(group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type) "
        "VALUES(?,?,?,?,?,?)",
        ("G_G4", "2026-05-08", "Bob", "حاضر", "60.0", "حضوري"),
    )
    # deliberately no session_durations row for 2026-05-08

    # S3 pencil-edit: SD=90 BUT att.class_duration=100, status=حاضر
    db.execute(
        "INSERT INTO attendance(group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type) "
        "VALUES(?,?,?,?,?,?)",
        ("G_G4", "2026-05-15", "Carol", "حاضر", "100", "حضوري"),
    )
    db.execute(
        "INSERT INTO session_durations(group_name, session_date, "
        "                              duration_minutes, session_type) "
        "VALUES(?,?,?,?)",
        ("G_G4", "2026-05-15", 90, "حضور"),
    )

    # S4 MAX-aggregation: two students same session, one pencil-edited
    db.execute(
        "INSERT INTO attendance(group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type) "
        "VALUES(?,?,?,?,?,?)",
        ("G_G4", "2026-05-22", "Dave", "حاضر", "100", "حضوري"),
    )
    db.execute(
        "INSERT INTO attendance(group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type) "
        "VALUES(?,?,?,?,?,?)",
        ("G_G4", "2026-05-22", "Eve",  "حاضر", "60",  "حضوري"),
    )

    db.commit()
    db.close()


def _client():
    c = appmod.app.test_client()
    r = c.post("/login", data={"username": "g4admin", "password": "G4pwd!"})
    assert r.status_code in (200, 302), "login failed: " + str(r.status_code)
    return c


def _student_row(rows, name):
    for r in rows:
        if (r.get("student_name") or "").strip() == name:
            return r
    return None


def main() -> int:
    _seed()
    c = _client()
    failures: list[str] = []

    # ── view=group — covers all 4 scenarios for the single group ──
    r = c.get("/api/attendance/summary?view=group&group=G_G4")
    if r.status_code != 200:
        failures.append("view=group HTTP " + str(r.status_code))
        d = {}
    else:
        d = r.get_json() or {}

    students = d.get("students", [])
    alice = _student_row(students, "Alice")
    bob   = _student_row(students, "Bob")
    carol = _student_row(students, "Carol")
    dave  = _student_row(students, "Dave")
    eve   = _student_row(students, "Eve")

    if not alice or alice.get("hours_total_min") != 60:
        failures.append("S1 (aligned): Alice hours_total_min expected 60, got "
                        + str(alice and alice.get("hours_total_min")))
    if not bob or bob.get("hours_total_min") != 60:
        failures.append("S2 (orphan no-SD): Bob hours_total_min expected 60 "
                        "(post-G4 — was 0 before), got "
                        + str(bob and bob.get("hours_total_min")))
    if not carol or carol.get("hours_total_min") != 100:
        failures.append("S3 (pencil-edit): Carol hours_total_min expected 100 "
                        "(post-G4 — was 90 before), got "
                        + str(carol and carol.get("hours_total_min")))
    if not dave or dave.get("hours_total_min") != 100:
        failures.append("S4 (per-row Dave): expected 100, got "
                        + str(dave and dave.get("hours_total_min")))
    if not eve or eve.get("hours_total_min") != 60:
        failures.append("S4 (per-row Eve): expected 60, got "
                        + str(eve and eve.get("hours_total_min")))

    # Group total_minutes:
    #   S1 session: MAX(60) = 60
    #   S2 session: MAX(60) = 60
    #   S3 session: MAX(100) = 100
    #   S4 session: MAX(100, 60) = 100
    # Total = 60+60+100+100 = 320
    if d.get("total_minutes") != 320:
        failures.append("group total_minutes expected 320 (MAX-aggregation), "
                        "got " + str(d.get("total_minutes")))

    # ── view=groups (multi-group container, single G_G4 selected) ──
    r = c.get("/api/attendance/summary?view=groups&g=G_G4")
    if r.status_code != 200:
        failures.append("view=groups HTTP " + str(r.status_code))
    else:
        d2 = r.get_json() or {}
        if d2.get("total_minutes") != 320:
            failures.append("groups total_minutes expected 320, got "
                            + str(d2.get("total_minutes")))

    # ── view=all (global) ──
    r = c.get("/api/attendance/summary?view=all")
    if r.status_code != 200:
        failures.append("view=all HTTP " + str(r.status_code))
    else:
        d3 = r.get_json() or {}
        if d3.get("total_minutes") != 320:
            failures.append("all total_minutes expected 320, got "
                            + str(d3.get("total_minutes")))

    # ── view=student (search for Carol — confirms pencil edit propagation) ──
    r = c.get("/api/attendance/summary?view=student&q=Carol")
    if r.status_code != 200:
        failures.append("view=student HTTP " + str(r.status_code))
    else:
        d4 = r.get_json() or {}
        matches = d4.get("matches", [])
        if not matches:
            failures.append("view=student: no matches for Carol")
        elif matches[0].get("hours_total_min") != 100:
            failures.append("view=student: Carol hours_total_min expected 100, "
                            "got " + str(matches[0].get("hours_total_min")))

    # ── view=all_groups (per-group rollup) ──
    r = c.get("/api/attendance/summary?view=all_groups")
    if r.status_code != 200:
        failures.append("view=all_groups HTTP " + str(r.status_code))
    else:
        d5 = r.get_json() or {}
        groups = d5.get("groups", [])
        g4 = next((g for g in groups if g.get("group_name") == "G_G4"), None)
        if not g4:
            failures.append("view=all_groups: G_G4 missing")
        elif g4.get("total_minutes") != 320:
            failures.append("view=all_groups G_G4 total_minutes expected 320, "
                            "got " + str(g4.get("total_minutes")))

    if failures:
        print("[G4] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[G4] PASS — summary endpoint reads attendance.class_duration, "
          "orphan rows count, pencil edits flow through, group totals "
          "use per-session MAX. All 5 views consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
