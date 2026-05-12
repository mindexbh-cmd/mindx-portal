"""C43 smoke - admin manual-trigger endpoint + button visibility."""
import os, sys, io, datetime as dt
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

cleanup_rid = None

# Setup: create a daily template with last_gen = 3 days ago so the
# manual trigger has something to generate.
with A.app.app_context():
    db = A.get_db()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]
    three_days_ago = (dt.date.today() - dt.timedelta(days=3)).isoformat()
    cur = db.execute(
        "INSERT INTO recurring_tasks("
        "template_title, department_id, priority, assigned_to_username, "
        "estimated_hours, frequency, last_generated_date, "
        "created_by_username, is_active) "
        "VALUES(?,?,?,?,?,?,?,?,1)",
        ("C43 manual-trigger test", events_dept, "normal", "admin",
         1.0, "daily", three_days_ago, "admin"))
    cleanup_rid = cur.lastrowid or dict(db.execute(
        "SELECT id FROM recurring_tasks WHERE template_title=?",
        ("C43 manual-trigger test",)).fetchone())["id"]
    db.commit()
print("[setup] rid=", cleanup_rid)

# Force-reset the throttle so we start from a clean state
A._LAST_RECURRING_CHECK = None

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ── Test 1: teacher1 (non-admin) -> 403 ──
sc = login("teacher1", "tea123")
print("[1pre] teacher1 login status=", sc)
rv = c.post("/api/recurring-tasks/run-scheduler")
print("[1] teacher1 POST -> status=", rv.status_code,
      "json=", rv.get_json())
assert rv.status_code == 403, f"expected 403, got {rv.status_code}"

# ── Test 2: admin -> 200 + generated count ──
login("admin", "admin123")
# Reset throttle (it may have been set by the /tasks visits in other tests
# or by a hooked route)
A._LAST_RECURRING_CHECK = None
rv = c.post("/api/recurring-tasks/run-scheduler")
j = rv.get_json()
print("[2] admin POST -> status=", rv.status_code, "json=", j)
assert rv.status_code == 200, f"expected 200, got {rv.status_code}"
assert j["ok"] is True
assert "generated" in j
assert isinstance(j["generated"], int)
# We seeded a template with last_gen 3 days ago, so the 2-day backlog
# policy means yesterday + today = 2 new tasks for THIS template.
template_details = [d for d in j["details"]
                    if d.get("template_id") == cleanup_rid]
print(f"[2a] details for our template: {len(template_details)} entries")
assert len(template_details) == 2, (
    f"expected 2 tasks for our 3-day-old template, got {len(template_details)}")

# ── Test 3: throttle bypass — endpoint MUST always fire,
# regardless of _LAST_RECURRING_CHECK ──
# (the endpoint resets the throttle itself; we test it ignores a fresh check)
A._LAST_RECURRING_CHECK = dt.datetime.now()  # pretend just-ran
rv = c.post("/api/recurring-tasks/run-scheduler")
j = rv.get_json()
print("[3] admin POST again (throttle bypassed) -> status=", rv.status_code,
      "generated=", j.get("generated"))
assert rv.status_code == 200
# Should be 0 — idempotent, no NEW tasks left to generate
assert j["generated"] == 0, (
    f"second call should be idempotent (0 new), got {j['generated']}")

# ── Test 4: button visible in HTML for admin / hidden for raed ──
login("admin", "admin123")
rv = c.get("/tasks/recurring")
print("[4] admin /tasks/recurring -> status=", rv.status_code)
assert rv.status_code == 200
html = rv.get_data(as_text=True)
assert 'r-run-now-btn' in html, "button id missing from page"
# R_IS_ADMIN must be true for admin
assert 'R_IS_ADMIN=true' in html.replace(' ', '') or \
       'R_IS_ADMIN = true' in html, "R_IS_ADMIN flag not set for admin"
print("[4a] R_IS_ADMIN=true present ✓")

login("teacher1", "tea123")
rv = c.get("/tasks/recurring")
print("[4b] teacher1 /tasks/recurring -> status=", rv.status_code)
assert rv.status_code == 200
html2 = rv.get_data(as_text=True)
# Button markup is in the template regardless, but the JS reveal block
# is guarded by R_IS_ADMIN. For teacher1 R_IS_ADMIN should be false.
assert 'R_IS_ADMIN=false' in html2.replace(' ', '') or \
       'R_IS_ADMIN = false' in html2, (
       "R_IS_ADMIN flag not false for teacher1")
print("[4c] R_IS_ADMIN=false for teacher1 ✓")

# ── Test 5: regression — 8 routes still 200 ──
login("admin", "admin123")
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[5] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Cleanup ──
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM tasks WHERE recurring_id=?", (cleanup_rid,))
    db.execute("DELETE FROM recurring_tasks WHERE id=?", (cleanup_rid,))
    db.commit()

print("\nC43 smoke passed.")
