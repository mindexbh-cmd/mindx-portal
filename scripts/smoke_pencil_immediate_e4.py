"""E4 — verify the backend PUT validation guards added in E2 plus
the dynamic-update behaviour they sit on top of.

Hermetic — spins a Flask test client against a tmp SQLite DB so we
exercise the actual request pipeline (normalisation, validation,
dynamic UPDATE) without any browser or running server.

Coverage:
  T1 — Valid PUT writes class_duration + class_type, returns row
  T2 — Empty body for both fields clears them (override-cleared)
  T3 — Garbage class_duration ('abc') → 400
  T4 — class_duration=0 → 400 (below the 1-1440 range)
  T5 — class_duration=2000 → 400 (above range)
  T6 — class_duration=60.0 (float-text) coerces to "60"
  T7 — Invalid class_type → 400
  T8 — Status / contact_number on the same row are PRESERVED when
       the PUT body only carries class_duration/class_type.
  T9 — Auth required (no session → redirect)
"""
import os
import sys
import sqlite3
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP_DB = os.path.join(tempfile.gettempdir(), "mindx_e4_smoke.db")

if os.path.exists(TMP_DB):
    os.remove(TMP_DB)
os.environ["DB_PATH"] = TMP_DB
os.environ["DATABASE_URL"] = ""
os.environ.setdefault("SECRET_KEY", "test-secret-e4")

sys.path.insert(0, REPO)
import app as appmod  # noqa: E402


def _seed():
    db = sqlite3.connect(TMP_DB)
    # admin user
    db.execute(
        "INSERT INTO users(username, password, role) VALUES(?, ?, ?)",
        ("e4admin", appmod.hp("E4pwd!"), "admin"),
    )
    # one attendance row to mutate
    db.execute(
        "INSERT INTO attendance(id, group_name, attendance_date, student_name, "
        "                       status, class_duration, class_type, "
        "                       contact_number, message) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (9001, "G_E4", "2026-05-19", "Test Pencil", "حاضر", "60", "حضوري",
         "55555555", ""),
    )
    db.commit()
    db.close()


def _client():
    c = appmod.app.test_client()
    r = c.post("/login", data={"username": "e4admin", "password": "E4pwd!"})
    assert r.status_code in (200, 302), "login failed: " + str(r.status_code)
    return c


def _put(c, rid, body):
    r = c.put(
        "/api/attendance/" + str(rid),
        json=body,
    )
    try:
        data = r.get_json()
    except Exception:
        data = {}
    return r.status_code, (data or {})


def main() -> int:
    _seed()
    c = _client()
    failures = []

    # T1 — valid PUT writes both columns
    sc, d = _put(c, 9001, {"class_duration": "75", "class_type": "حضوري"})
    if sc != 200 or not d.get("ok"):
        failures.append("T1: PUT failed: " + str(sc) + " " + str(d))
    else:
        row = d.get("row", {})
        if row.get("class_duration") != "75":
            failures.append("T1: class_duration stored as " + repr(row.get("class_duration")))

    # T2 — empty body clears (sends "" for both)
    sc, d = _put(c, 9001, {"class_duration": "", "class_type": ""})
    if sc != 200 or not d.get("ok"):
        failures.append("T2: empty PUT failed: " + str(sc) + " " + str(d))
    else:
        row = d.get("row", {})
        if row.get("class_duration") not in ("", None):
            failures.append("T2: class_duration not cleared: " + repr(row.get("class_duration")))

    # T3 — garbage → 400
    sc, d = _put(c, 9001, {"class_duration": "abc"})
    if sc != 400:
        failures.append("T3: expected 400 for non-numeric, got " + str(sc))

    # T4 — 0 below range
    sc, d = _put(c, 9001, {"class_duration": "0"})
    if sc != 400:
        failures.append("T4: expected 400 for class_duration=0, got " + str(sc))

    # T5 — above range
    sc, d = _put(c, 9001, {"class_duration": "2000"})
    if sc != 400:
        failures.append("T5: expected 400 for class_duration=2000, got " + str(sc))

    # T6 — float-text coerces to int
    sc, d = _put(c, 9001, {"class_duration": "60.0"})
    if sc != 200:
        failures.append("T6: 60.0 should be accepted, got " + str(sc) + " " + str(d))
    elif d.get("row", {}).get("class_duration") != "60":
        failures.append("T6: 60.0 not coerced to '60': " + repr(d.get("row", {}).get("class_duration")))

    # T7 — invalid class_type
    sc, d = _put(c, 9001, {"class_type": "bogus"})
    if sc != 400:
        failures.append("T7: invalid class_type accepted: " + str(sc) + " " + str(d))

    # T8 — status / contact preserved when only sending duration+type
    # Reset to a known state first
    _put(c, 9001, {"class_duration": "90", "class_type": "أونلاين"})
    db = sqlite3.connect(TMP_DB)
    row = db.execute(
        "SELECT status, contact_number, class_duration, class_type "
        "FROM attendance WHERE id=9001"
    ).fetchone()
    db.close()
    if row[0] != "حاضر":
        failures.append("T8: status mutated to " + repr(row[0]))
    if row[1] != "55555555":
        failures.append("T8: contact_number mutated to " + repr(row[1]))
    if row[2] != "90":
        failures.append("T8: class_duration not stored: " + repr(row[2]))
    if row[3] != "أونلاين":
        failures.append("T8: class_type not stored: " + repr(row[3]))

    # T9 — auth required
    c2 = appmod.app.test_client()
    r = c2.put("/api/attendance/9001",
               json={"class_duration": "60"})
    # login_required returns a 302 redirect to /
    if r.status_code not in (302, 401, 403):
        failures.append("T9: unauthenticated PUT got " + str(r.status_code)
                        + " (expected 302/401/403)")

    if failures:
        print("[E4] FAILED:")
        for f in failures:
            print("  - " + f)
        return 1
    print("[E4] PASS — PUT validation matrix correct: "
          "valid writes, empty clears, garbage/0/2000 reject, "
          "60.0→60 coerces, invalid type rejects, sibling columns "
          "preserved, auth required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
