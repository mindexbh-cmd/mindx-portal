"""G7.4 — verify hours.required now reads students.contract_hours and
the migration applies the 28-default backfill correctly.

Five scenarios:
  S1 — contract_hours=28, taken=29 (one 60-min overrun) →
       overrun_min=60 → UI ceil to "أخذ زيادة 1 ساعة"
  S2 — contract_hours=28, taken=20 → remaining=8, no overrun
  S3 — contract_hours=14 (split-group case), taken=14 → remaining=0,
       overrun_min=0 (exactly at quota)
  S4 — group columns NOT consulted: student's group has
       total_required_hours='99' and hours_all_online='42', but
       student's contract_hours=20 wins → required=20 (proves the
       resolver no longer touches student_groups)
  S5 — fresh-seed default: new student inserted with NO contract_hours
       in the body → DB default 28 fires → required=28 in hub-stats

The hermetic harness exercises the live api_parent_hub_stats endpoint
against a tmp SQLite DB so the result is what the parent actually
sees, not just SQL-level state.
"""
import os
import sys
import sqlite3
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DB = os.path.join(tempfile.gettempdir(), "mindx_g7_smoke.db")

if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["DB_PATH"] = TMP_DB
os.environ["DATABASE_URL"] = ""
os.environ.setdefault("SECRET_KEY", "test-secret-g7")
sys.path.insert(0, REPO)
import app as appmod  # noqa: E402


def _seed():
    db = sqlite3.connect(TMP_DB)
    # Confirm the migration ran (column exists with DEFAULT 28).
    cols = {r[1] for r in db.execute("PRAGMA table_info(students)").fetchall()}
    assert "contract_hours" in cols, "migration didn't add contract_hours"

    # Groups carry deliberately misleading group-level "hours" values
    # so S4 can prove the resolver no longer consults them.
    db.executemany(
        "INSERT INTO student_groups(group_name, total_required_hours, "
        "                           hours_all_online) VALUES(?,?,?)",
        [
            ("G7_G1", "0", "0"),
            ("G7_G2", "0", "0"),
            ("G7_G3", "0", "0"),
            ("G7_G4", "99", "42"),  # red herrings for S4
        ],
    )
    # S1-S4 students with explicit contract_hours.
    db.executemany(
        "INSERT INTO students(student_name, personal_id, "
        "                     group_name_student, contract_hours) "
        "VALUES(?,?,?,?)",
        [
            ("G7 Alice", "G7-S1", "G7_G1", 28),
            ("G7 Bob",   "G7-S2", "G7_G2", 28),
            ("G7 Carol", "G7-S3", "G7_G3", 14),
            ("G7 Dave",  "G7-S4", "G7_G4", 20),
        ],
    )
    # S5 — no contract_hours in the INSERT, so the column DEFAULT
    # 28 should fire. SQLite's PRAGMA default applies on row insert.
    db.execute(
        "INSERT INTO students(student_name, personal_id, "
        "                     group_name_student) "
        "VALUES(?,?,?)",
        ("G7 Eve", "G7-S5", "G7_G1"),
    )

    # Attendance loads:
    #   S1 — 29 hours present (one 60-min overrun against 28 contract)
    #   S2 — 20 hours present
    #   S3 — 14 hours present (exact-quota)
    #   S4 — 5 hours present (well under 20 contract, doesn't matter
    #        for the test — focus is on `required`)
    #   S5 — 0 attendance (fresh student); required should still be 28
    rows = []
    # S1: 29h = 1740 min → 29 × 60-min rows
    for i in range(29):
        rows.append(("G7_G1", "2026-0%d-%02d" % (2 + (i // 28), (i % 28) + 1),
                     "G7 Alice", "حاضر", "60"))
    # S2: 20h = 1200 min → 20 × 60-min rows
    for i in range(20):
        rows.append(("G7_G2", "2026-0%d-%02d" % (2 + (i // 28), (i % 28) + 1),
                     "G7 Bob", "حاضر", "60"))
    # S3: 14h
    for i in range(14):
        rows.append(("G7_G3", "2026-0%d-%02d" % (2 + (i // 28), (i % 28) + 1),
                     "G7 Carol", "حاضر", "60"))
    # S4: 5h
    for i in range(5):
        rows.append(("G7_G4", "2026-0%d-%02d" % (2 + (i // 28), (i % 28) + 1),
                     "G7 Dave", "حاضر", "60"))
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

    # ── S1 — contract_hours=28, taken=29 → overrun_min=60
    sc, d = _hit("G7-S1")
    h = (d.get("stats") or {}).get("hours") or {}
    if h.get("required") != 28:
        failures.append("S1 required expected 28, got " + repr(h.get("required")))
    if h.get("taken") != 29:
        failures.append("S1 taken expected 29, got " + repr(h.get("taken")))
    if h.get("remaining") != 0:
        failures.append("S1 remaining expected 0, got " + repr(h.get("remaining")))
    if h.get("overrun_min") != 60:
        failures.append("S1 overrun_min expected 60 (= 1h ceil), got "
                        + repr(h.get("overrun_min")))

    # ── S2 — contract=28, taken=20 → remaining=8
    sc, d = _hit("G7-S2")
    h = (d.get("stats") or {}).get("hours") or {}
    if h.get("required") != 28:
        failures.append("S2 required expected 28, got " + repr(h.get("required")))
    if h.get("taken") != 20:
        failures.append("S2 taken expected 20, got " + repr(h.get("taken")))
    if h.get("remaining") != 8:
        failures.append("S2 remaining expected 8, got " + repr(h.get("remaining")))
    if h.get("overrun_min") != 0:
        failures.append("S2 overrun_min expected 0, got " + repr(h.get("overrun_min")))

    # ── S3 — contract=14, taken=14 → exact quota
    sc, d = _hit("G7-S3")
    h = (d.get("stats") or {}).get("hours") or {}
    if h.get("required") != 14:
        failures.append("S3 required expected 14 (split-group case), got "
                        + repr(h.get("required")))
    if h.get("taken") != 14:
        failures.append("S3 taken expected 14, got " + repr(h.get("taken")))
    if h.get("remaining") != 0:
        failures.append("S3 remaining expected 0, got " + repr(h.get("remaining")))
    if h.get("overrun_min") != 0:
        failures.append("S3 overrun_min expected 0 (exact quota), got "
                        + repr(h.get("overrun_min")))

    # ── S4 — group columns NOT consulted. Group has total_required_hours=99
    # and hours_all_online=42; student's contract_hours=20 must win.
    sc, d = _hit("G7-S4")
    h = (d.get("stats") or {}).get("hours") or {}
    if h.get("required") != 20:
        failures.append("S4 required expected 20 (student wins over "
                        "group's 99/42 red herrings), got "
                        + repr(h.get("required")))

    # ── S5 — DEFAULT 28 fires on insert without explicit value
    sc, d = _hit("G7-S5")
    h = (d.get("stats") or {}).get("hours") or {}
    if h.get("required") != 28:
        failures.append("S5 required expected 28 (DB default), got "
                        + repr(h.get("required")))
    # And no attendance rows yet → taken=0
    if h.get("taken") != 0:
        failures.append("S5 taken expected 0, got " + repr(h.get("taken")))

    if failures:
        print("[G7] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[G7] PASS — contract_hours drives required across all 5 "
          "scenarios; group_groups.* fields no longer consulted; "
          "fresh students pick up DB DEFAULT 28.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
