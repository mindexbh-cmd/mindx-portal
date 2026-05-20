"""G9.3 — verify stats.attendance_breakdown across 4 scenarios.

Flask test client against a tmp SQLite. Each scenario uses a fresh
student so counts don't leak between cases.

Scenarios:
  S1 — 8 present + 1 late + 1 absent (10 total) →
       counts: 8/1/1, total=10
       percentages: 80/10/10, total=90
  S2 — 0 sessions → all counts and percentages = 0
       (UI surfaces "لا توجد حصص" empty-state from this signal)
  S3 — 0 present + 0 late + 5 absent (5 total) →
       counts: 0/0/5, percentages: 0/0/100, total=0
  S4 — 1 present + 1 late + 1 absent (3 total; raw 33.33% each) →
       rounded raw: 33/33/33 = 99; the largest-bucket adjustment
       nudges +1 to present (ties favour present > late > absent),
       final: 34/33/33 = 100. attendance_pct_total = 34+33 = 67.
"""
import os
import sys
import sqlite3
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DB = os.path.join(tempfile.gettempdir(), "mindx_g9_smoke.db")

if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["DB_PATH"] = TMP_DB
os.environ["DATABASE_URL"] = ""
os.environ.setdefault("SECRET_KEY", "test-secret-g9")
sys.path.insert(0, REPO)
import app as appmod  # noqa: E402


def _seed():
    db = sqlite3.connect(TMP_DB)
    db.execute(
        "INSERT INTO student_groups(group_name, total_required_hours, hours_all_online) "
        "VALUES(?,?,?)", ("G9_G", "0", "0"),
    )
    db.executemany(
        "INSERT INTO students(student_name, personal_id, group_name_student, contract_hours) "
        "VALUES(?,?,?,?)",
        [
            ("G9 Alice", "G9-S1", "G9_G", 28),  # S1 — mixed 8/1/1
            ("G9 Bob",   "G9-S2", "G9_G", 28),  # S2 — no rows
            ("G9 Carol", "G9-S3", "G9_G", 28),  # S3 — all absent
            ("G9 Dave",  "G9-S4", "G9_G", 28),  # S4 — 1/1/1
        ],
    )
    rows = []
    # S1: 8 present + 1 late + 1 absent
    for i in range(8):
        rows.append(("G9_G", "2026-02-%02d" % (i + 1), "G9 Alice", "حاضر", "60"))
    rows.append(("G9_G", "2026-02-09", "G9 Alice", "متأخر", "60"))
    rows.append(("G9_G", "2026-02-10", "G9 Alice", "غائب",  "60"))
    # S2: nothing
    # S3: 5 absent
    for i in range(5):
        rows.append(("G9_G", "2026-03-%02d" % (i + 1), "G9 Carol", "غائب", "60"))
    # S4: 1 present + 1 late + 1 absent
    rows.append(("G9_G", "2026-04-01", "G9 Dave", "حاضر", "60"))
    rows.append(("G9_G", "2026-04-02", "G9 Dave", "متأخر", "60"))
    rows.append(("G9_G", "2026-04-03", "G9 Dave", "غائب",  "60"))
    db.executemany(
        "INSERT INTO attendance(group_name, attendance_date, "
        "                       student_name, status, class_duration) "
        "VALUES(?,?,?,?,?)",
        rows,
    )
    db.commit()
    db.close()


def main() -> int:
    _seed()
    c = appmod.app.test_client()
    failures: list[str] = []

    def _hit(pid):
        r = c.get("/api/parent/hub-stats?pid=" + pid)
        try:
            return r.status_code, r.get_json() or {}
        except Exception:
            return r.status_code, {}

    def _bd(payload):
        return (payload.get("stats") or {}).get("attendance_breakdown") or {}

    # ── S1 — 8 present + 1 late + 1 absent
    sc, d = _hit("G9-S1")
    bd = _bd(d)
    expect = {
        "sessions_present_count": 8,
        "sessions_late_count":    1,
        "sessions_absent_count":  1,
        "sessions_total_count":   10,
        "attendance_pct_present": 80,
        "attendance_pct_late":    10,
        "attendance_pct_absent":  10,
        "attendance_pct_total":   90,
    }
    for k, v in expect.items():
        if bd.get(k) != v:
            failures.append("S1." + k + " expected " + str(v) + ", got " + str(bd.get(k)))

    # ── S2 — 0 sessions
    sc, d = _hit("G9-S2")
    bd = _bd(d)
    for k in expect.keys():
        if bd.get(k) != 0:
            failures.append("S2." + k + " expected 0, got " + str(bd.get(k)))

    # ── S3 — 100% absent
    sc, d = _hit("G9-S3")
    bd = _bd(d)
    expect_s3 = {
        "sessions_present_count": 0,
        "sessions_late_count":    0,
        "sessions_absent_count":  5,
        "sessions_total_count":   5,
        "attendance_pct_present": 0,
        "attendance_pct_late":    0,
        "attendance_pct_absent":  100,
        "attendance_pct_total":   0,
    }
    for k, v in expect_s3.items():
        if bd.get(k) != v:
            failures.append("S3." + k + " expected " + str(v) + ", got " + str(bd.get(k)))

    # ── S4 — rounding drift 33/33/33 → 34/33/33 (present gets the +1)
    sc, d = _hit("G9-S4")
    bd = _bd(d)
    # Counts
    if bd.get("sessions_present_count") != 1:
        failures.append("S4.sessions_present_count expected 1, got "
                        + str(bd.get("sessions_present_count")))
    if bd.get("sessions_late_count") != 1:
        failures.append("S4.sessions_late_count expected 1")
    if bd.get("sessions_absent_count") != 1:
        failures.append("S4.sessions_absent_count expected 1")
    if bd.get("sessions_total_count") != 3:
        failures.append("S4.sessions_total_count expected 3")
    # Percentages — present gets the +1 nudge
    if bd.get("attendance_pct_present") != 34:
        failures.append("S4.attendance_pct_present expected 34 (rounded "
                        "33+1 nudge), got " + str(bd.get("attendance_pct_present")))
    if bd.get("attendance_pct_late") != 33:
        failures.append("S4.attendance_pct_late expected 33, got "
                        + str(bd.get("attendance_pct_late")))
    if bd.get("attendance_pct_absent") != 33:
        failures.append("S4.attendance_pct_absent expected 33, got "
                        + str(bd.get("attendance_pct_absent")))
    # Sum must equal 100
    total_pct = (bd.get("attendance_pct_present", 0)
                 + bd.get("attendance_pct_late", 0)
                 + bd.get("attendance_pct_absent", 0))
    if total_pct != 100:
        failures.append("S4 percentages sum expected 100, got " + str(total_pct))
    # attendance_pct_total = present + late = 34 + 33 = 67
    if bd.get("attendance_pct_total") != 67:
        failures.append("S4.attendance_pct_total expected 67 (34+33), got "
                        + str(bd.get("attendance_pct_total")))

    if failures:
        print("[G9] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[G9] PASS — attendance_breakdown handles mixed / empty / "
          "all-absent / rounding-drift correctly; percentages always "
          "sum to 100 when sessions exist.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
