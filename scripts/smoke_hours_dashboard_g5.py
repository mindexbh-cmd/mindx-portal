"""G5.4 — verify /api/parent/hub-stats returns the new hours dashboard
shape across the 4 operator scenarios.

Each scenario seeds a self-contained student + group + attendance
rows, then calls /api/parent/hub-stats?pid=<pid> via the Flask test
client and asserts the response fields. PID auth is public so no
session needed.

Scenarios:
  S1 — under-target: required=40, taken=25 (5 present × 5h each, 0 absent)
       → remaining=15, no overrun, absence_dates=[]
  S2 — overrun: required=20, taken=35 (5 present × 7h each, 0 absent)
       → remaining=0, overrun_min=900 (15h*60), absence_dates=[]
  S3 — mixed with absences: required=40, taken=30 (3 present × 6h + 2 absent × 6h)
       → remaining=10, no overrun, absence_dates has 2 ISO dates ordered oldest first
  S4 — both required fields empty (and zero):
       → required=null, remaining=0, overrun_min=0, taken still computed
"""
import os
import sys
import sqlite3
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DB = os.path.join(tempfile.gettempdir(), "mindx_g5_smoke.db")

if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["DB_PATH"] = TMP_DB
os.environ["DATABASE_URL"] = ""
os.environ.setdefault("SECRET_KEY", "test-secret-g5")
sys.path.insert(0, REPO)
import app as appmod  # noqa: E402


def _seed():
    db = sqlite3.connect(TMP_DB)
    # Each student gets their own group so required-hours and
    # attendance rollups stay scoped.
    db.executemany(
        "INSERT INTO student_groups(group_name, total_required_hours, "
        "                           hours_all_online) VALUES(?,?,?)",
        [
            ("G_S1", "40", "30"),  # total_required_hours wins
            ("G_S2", "20", "99"),  # total_required_hours wins
            ("G_S3", "40", "10"),  # total_required_hours wins
            ("G_S4", "",   ""),    # both empty → required = None
        ],
    )
    db.executemany(
        "INSERT INTO students(id, student_name, personal_id, "
        "                     group_name_student) VALUES(?,?,?,?)",
        [
            (9701, "G5 Alice", "G5-S1", "G_S1"),
            (9702, "G5 Bob",   "G5-S2", "G_S2"),
            (9703, "G5 Carol", "G5-S3", "G_S3"),
            (9704, "G5 Dave",  "G5-S4", "G_S4"),
        ],
    )
    # S1: 5 present rows × 300 min = 1500 min = 25 hours
    for i, d in enumerate(["2026-02-02", "2026-02-09", "2026-02-16",
                            "2026-02-23", "2026-03-02"]):
        db.execute(
            "INSERT INTO attendance(group_name, attendance_date, "
            "                       student_name, status, class_duration) "
            "VALUES(?,?,?,?,?)",
            ("G_S1", d, "G5 Alice", "حاضر", "300"),
        )
    # S2: 5 present rows × 420 min = 2100 min = 35 hours (overrun by 15)
    for i, d in enumerate(["2026-02-03", "2026-02-10", "2026-02-17",
                            "2026-02-24", "2026-03-03"]):
        db.execute(
            "INSERT INTO attendance(group_name, attendance_date, "
            "                       student_name, status, class_duration) "
            "VALUES(?,?,?,?,?)",
            ("G_S2", d, "G5 Bob", "حاضر", "420"),
        )
    # S3: 3 present + 2 absent, each 360 min = 6 hours. taken=30, attended=18.
    # Absence dates intentionally out-of-order to verify the sort.
    db.executemany(
        "INSERT INTO attendance(group_name, attendance_date, "
        "                       student_name, status, class_duration) "
        "VALUES(?,?,?,?,?)",
        [
            ("G_S3", "2026-02-04", "G5 Carol", "حاضر", "360"),
            ("G_S3", "2026-03-04", "G5 Carol", "غائب", "360"),
            ("G_S3", "2026-02-11", "G5 Carol", "حاضر", "360"),
            ("G_S3", "2026-02-18", "G5 Carol", "غائب", "360"),
            ("G_S3", "2026-02-25", "G5 Carol", "حاضر", "360"),
        ],
    )
    # S4: 2 present rows × 600 min = 20 hours. No required.
    db.executemany(
        "INSERT INTO attendance(group_name, attendance_date, "
        "                       student_name, status, class_duration) "
        "VALUES(?,?,?,?,?)",
        [
            ("G_S4", "2026-02-05", "G5 Dave", "حاضر", "600"),
            ("G_S4", "2026-02-12", "G5 Dave", "حاضر", "600"),
        ],
    )
    db.commit()
    db.close()


def main() -> int:
    _seed()
    c = appmod.app.test_client()
    failures: list[str] = []

    def _hit(pid):
        r = c.get("/api/parent/hub-stats?pid=" + pid)
        return r.status_code, r.get_json() or {}

    # ── S1 — under-target
    sc, d = _hit("G5-S1")
    hrs = (d.get("stats") or {}).get("hours") or {}
    if sc != 200 or not d.get("ok"):
        failures.append("S1 HTTP/ok: " + str(sc) + " " + str(d))
    if hrs.get("required") != 40:
        failures.append("S1 required expected 40, got " + repr(hrs.get("required")))
    if hrs.get("taken") != 25:
        failures.append("S1 taken expected 25, got " + repr(hrs.get("taken")))
    if hrs.get("remaining") != 15:
        failures.append("S1 remaining expected 15, got " + repr(hrs.get("remaining")))
    if hrs.get("overrun_min") != 0:
        failures.append("S1 overrun_min expected 0, got " + repr(hrs.get("overrun_min")))
    if d.get("absence_dates") != []:
        failures.append("S1 absence_dates expected [], got " + repr(d.get("absence_dates")))

    # ── S2 — overrun by 15h
    sc, d = _hit("G5-S2")
    hrs = (d.get("stats") or {}).get("hours") or {}
    if hrs.get("required") != 20:
        failures.append("S2 required expected 20, got " + repr(hrs.get("required")))
    if hrs.get("taken") != 35:
        failures.append("S2 taken expected 35, got " + repr(hrs.get("taken")))
    if hrs.get("remaining") != 0:
        failures.append("S2 remaining expected 0, got " + repr(hrs.get("remaining")))
    # 35h taken - 20h required = 15h overrun = 900 min
    if hrs.get("overrun_min") != 900:
        failures.append("S2 overrun_min expected 900, got " + repr(hrs.get("overrun_min")))

    # ── S3 — mixed with absences
    sc, d = _hit("G5-S3")
    hrs = (d.get("stats") or {}).get("hours") or {}
    if hrs.get("required") != 40:
        failures.append("S3 required expected 40, got " + repr(hrs.get("required")))
    # taken = 5 × 360 min = 1800 min = 30 hours
    if hrs.get("taken") != 30:
        failures.append("S3 taken expected 30, got " + repr(hrs.get("taken")))
    if hrs.get("attended") != 18:
        failures.append("S3 attended expected 18 (only present), got "
                        + repr(hrs.get("attended")))
    if hrs.get("remaining") != 10:
        failures.append("S3 remaining expected 10, got " + repr(hrs.get("remaining")))
    if hrs.get("overrun_min") != 0:
        failures.append("S3 overrun_min expected 0, got " + repr(hrs.get("overrun_min")))
    # absence_dates must be ordered oldest first
    expected_abs = ["2026-02-18", "2026-03-04"]
    if d.get("absence_dates") != expected_abs:
        failures.append("S3 absence_dates expected " + repr(expected_abs)
                        + " (sorted), got " + repr(d.get("absence_dates")))

    # ── S4 — required null
    sc, d = _hit("G5-S4")
    hrs = (d.get("stats") or {}).get("hours") or {}
    if hrs.get("required") is not None:
        failures.append("S4 required expected None, got " + repr(hrs.get("required")))
    if hrs.get("taken") != 20:
        failures.append("S4 taken expected 20, got " + repr(hrs.get("taken")))
    if hrs.get("remaining") != 0:
        failures.append("S4 remaining expected 0, got " + repr(hrs.get("remaining")))
    if hrs.get("overrun_min") != 0:
        failures.append("S4 overrun_min expected 0, got " + repr(hrs.get("overrun_min")))

    # ── Existing fields not broken
    sc, d = _hit("G5-S1")
    hrs = (d.get("stats") or {}).get("hours") or {}
    if hrs.get("attended") != 25:
        failures.append("Compat: S1 hours.attended expected 25, got "
                        + repr(hrs.get("attended")))

    if failures:
        print("[G5] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[G5] PASS — under-target, overrun, with-absences, "
          "null-required all behave correctly; attended/taken/required/"
          "remaining/overrun_min/absence_dates all match spec.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
