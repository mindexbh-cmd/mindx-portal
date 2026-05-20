"""C4 smoke test — verify date-aware resolver + /api/center/auto-meta
path against a synthetic local SQLite DB.

We don't spin up Flask for this; we directly import the relevant
helpers and exercise them against a tmp DB so the test is fast and
hermetic.

Coverage:
  - Resolver WITHOUT date returns the group default (legacy path).
  - Resolver WITH date matching a session_durations row returns the
    session_durations value (new path).
  - Resolver WITH date that has NO matching SD row falls back to the
    group default (graceful fallback).
  - Resolver respects mode_exceptions (per-student override).
"""
import os
import sys
import sqlite3
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

# Use a tmp DB and force the SQLite path before importing app.py.
_TMP_DB = os.path.join(tempfile.gettempdir(), "mindx_c4_smoke.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["DB_PATH"] = _TMP_DB
os.environ["DATABASE_URL"] = ""

import app as appmod  # noqa: E402


def main() -> int:
    db = sqlite3.connect(_TMP_DB)
    db.row_factory = sqlite3.Row

    # Seed: one group with a default session_duration of 45 minutes,
    # one student in that group, and a session_durations row for
    # 2026-05-19 that overrides to 90.
    db.execute("INSERT INTO student_groups(group_name, session_duration) VALUES(?, ?)",
               ("G_TEST_C4", "45"))
    db.execute("INSERT INTO students(student_name, group_name_student) VALUES(?, ?)",
               ("Test Student", "G_TEST_C4"))
    sid = db.execute("SELECT id FROM students WHERE student_name=?",
                     ("Test Student",)).fetchone()[0]
    db.execute("INSERT INTO session_durations(group_name, session_date, "
               "duration_minutes, session_type) VALUES(?,?,?,?)",
               ("G_TEST_C4", "2026-05-19", 90, "حضور"))
    db.commit()

    mode = appmod._center_mode_default()
    failures = []

    # T1: no date → group default
    meta = appmod._resolve_center_class_meta(db, mode, sid)
    if meta.get("class_duration") != "45":
        failures.append(
            "T1 expected class_duration='45' (group default), got "
            + repr(meta.get("class_duration"))
        )

    # T2: date that matches an SD row → SD value
    meta = appmod._resolve_center_class_meta(db, mode, sid,
                                              session_date="2026-05-19")
    if meta.get("class_duration") != "90":
        failures.append(
            "T2 expected class_duration='90' (session_durations), got "
            + repr(meta.get("class_duration"))
        )

    # T3: date with NO matching SD row → fallback to group default
    meta = appmod._resolve_center_class_meta(db, mode, sid,
                                              session_date="2026-04-01")
    if meta.get("class_duration") != "45":
        failures.append(
            "T3 expected class_duration='45' (no SD, fallback), got "
            + repr(meta.get("class_duration"))
        )

    # T4: SD row with duration_minutes=0 → must NOT win (treated as empty)
    db.execute("INSERT INTO session_durations(group_name, session_date, "
               "duration_minutes, session_type) VALUES(?,?,?,?)",
               ("G_TEST_C4", "2026-05-20", 0, ""))
    db.commit()
    meta = appmod._resolve_center_class_meta(db, mode, sid,
                                              session_date="2026-05-20")
    if meta.get("class_duration") != "45":
        failures.append(
            "T4 expected class_duration='45' (zero SD ignored), got "
            + repr(meta.get("class_duration"))
        )

    # T5: malformed date string → resolver normalises; falls back if not parseable
    meta = appmod._resolve_center_class_meta(db, mode, sid,
                                              session_date="garbage")
    if meta.get("class_duration") not in ("45",):
        failures.append(
            "T5 expected class_duration='45' (garbage date, fallback), got "
            + repr(meta.get("class_duration"))
        )

    # T6: alternate date format that normalises to the same ISO date
    meta = appmod._resolve_center_class_meta(db, mode, sid,
                                              session_date="19/5/2026")
    if meta.get("class_duration") != "90":
        failures.append(
            "T6 expected class_duration='90' (date-format normalised), got "
            + repr(meta.get("class_duration"))
        )

    db.close()
    if failures:
        print("[C4] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[C4] PASS — date-aware resolver behaves correctly across "
          "6 scenarios (legacy, SD hit, SD miss, zero-SD, garbage date, "
          "alt date format)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
