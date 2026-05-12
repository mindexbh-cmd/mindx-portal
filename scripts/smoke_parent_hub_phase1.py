"""Parent-Hub Phase 1 C6 smoke - public PID hub landing.

Verifies the new /parent → 5-card hub landing without breaking the
legacy /parent flow. Checks:

  • GET /parent             returns 200 + hub markup (lookup-card +
                            hub-content + 5 CARD_DEFS entries +
                            /parent/legacy anchored links)
  • GET /parent/legacy      returns 200 + contains all 5 anchor IDs
                            (section-payment, section-attendance,
                             section-points, section-evaluations,
                             section-books)
  • POST  /api/parent/hub-stats with a real student PID returns
        {ok:true, student:{name, ...}, stats:{payment, attendance,
         points, evaluations, books}}
  • GET   /api/parent/hub-stats?pid=invalid returns ok=false (404
        or 200 with error message; either is acceptable as long as
        the wrapper sets ok=false)
  • Mobile breakpoint (`@media (max-width:600px)`) present in hub CSS
"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Setup: create a smoke student with a known PID
SMOKE_PID = "SMOKE_HUB_P1"
cleanup_student_ids = []

with A.app.app_context():
    db = A.get_db()
    # Idempotent: remove any leftover from a prior failed run
    db.execute("DELETE FROM students WHERE personal_id=?", (SMOKE_PID,))
    db.commit()
    db.execute(
        "INSERT INTO students(student_name, personal_id, "
        "group_name_student, class_name) VALUES(?, ?, ?, ?)",
        ("Smoke Hub Student", SMOKE_PID, "smoke hub grp", "Year 3"))
    r = db.execute("SELECT id FROM students WHERE personal_id=? "
                   "ORDER BY id DESC LIMIT 1",
                   (SMOKE_PID,)).fetchone()
    sid = int(dict(r)["id"]); cleanup_student_ids.append(sid)
    db.commit()
    print(f"[setup] smoke student id={sid} pid={SMOKE_PID}")

c = A.app.test_client()

# Test 1: /parent renders hub
rv = c.get("/parent")
print(f"[1] GET /parent -> {rv.status_code}")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
assert "lookup-card" in html, "missing lookup-card scaffold"
assert "hub-content" in html, "missing hub-content slot"
assert "phLookup" in html, "missing phLookup JS function"
assert "/api/parent/hub-stats" in html, "hub does not call hub-stats endpoint"
for key in ("section-payment", "section-attendance", "section-points",
            "section-evaluations", "section-books"):
    assert key in html, f"hub HTML missing card anchor {key!r}"
print("[1a] hub markup + 5 card anchors + endpoint reference present")

# Mobile breakpoint
assert "max-width:600px" in html, "missing 600px breakpoint"
assert "max-width:380px" in html, "missing 380px narrow breakpoint"
assert "hover:none" in html, "missing touch-device hover override"
print("[1b] responsive breakpoints (600/380/hover:none) present")

# Test 2: /parent/legacy renders the old PARENT_HTML with all 5 anchors
rv = c.get("/parent/legacy")
print(f"[2] GET /parent/legacy -> {rv.status_code}")
assert rv.status_code == 200
legacy = rv.get_data(as_text=True)
for anchor in ("section-payment", "section-attendance", "section-points",
               "section-evaluations", "section-books"):
    assert f'id="{anchor}"' in legacy, \
        f"legacy page missing anchor id={anchor!r}"
# Legacy IDs must still exist (JS references them)
for legacy_id in ("ppStoreCard", "pp-evals-card", "pp-books-card"):
    assert f'id="{legacy_id}"' in legacy, \
        f"legacy page missing original id={legacy_id!r} (JS will break)"
print("[2a] legacy page has all 5 anchors + 3 original IDs preserved")

# Test 3: hub-stats endpoint with a valid PID
rv = c.get(f"/api/parent/hub-stats?pid={SMOKE_PID}")
print(f"[3] GET /api/parent/hub-stats?pid={SMOKE_PID} -> {rv.status_code}")
assert rv.status_code == 200
j = rv.get_json()
assert j and j.get("ok"), f"expected ok=true, got {j!r}"
s = j.get("student") or {}
assert s.get("name"), "student.name missing"
assert s.get("personal_id") == SMOKE_PID
stats = j.get("stats") or {}
for k in ("payment", "attendance", "points", "evaluations", "books"):
    assert k in stats, f"stats missing key {k!r}"
print(f"[3a] response shape OK: student.name={s.get('name')!r} "
      f"stats keys={list(stats.keys())}")

# Test 4: hub-stats with invalid PID
rv = c.get("/api/parent/hub-stats?pid=DEFINITELY_NOT_A_REAL_PID_9999")
print(f"[4] invalid pid -> {rv.status_code}")
j = rv.get_json()
assert j is not None
# Accept either 404 with ok:false OR 200 with ok:false
assert j.get("ok") is False, \
    f"expected ok=false for bogus PID, got {j!r}"
print(f"[4a] bogus pid correctly rejected with ok=false")

# Test 5: hub-stats with empty PID
rv = c.get("/api/parent/hub-stats?pid=")
print(f"[5] empty pid -> {rv.status_code}")
j = rv.get_json()
assert j is not None
assert j.get("ok") is False
print(f"[5a] empty pid correctly rejected")

# Test 6: anchored link from hub points at /parent/legacy
assert "/parent/legacy?pid=" in html, \
    "hub cards should link to /parent/legacy?pid=…#anchor"
print("[6] hub cards anchored to /parent/legacy with PID query")

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for s_id in cleanup_student_ids:
        db.execute("DELETE FROM students WHERE id=?", (s_id,))
    db.commit()
print(f"[cleanup] removed {len(cleanup_student_ids)} smoke student")

print("\nParent-Hub Phase 1 smoke passed.")
