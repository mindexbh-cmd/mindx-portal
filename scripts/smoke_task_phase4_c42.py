"""C42 smoke - request-time hook + throttle."""
import os, sys, io, datetime as dt
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

cleanup_rid = None
cleanup_tids = []

# Setup: create a daily template with last_gen = 5 days ago
with A.app.app_context():
    db = A.get_db()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]
    five_days_ago = (dt.date.today() - dt.timedelta(days=5)).isoformat()
    cur = db.execute(
        "INSERT INTO recurring_tasks("
        "template_title, department_id, priority, assigned_to_username, "
        "estimated_hours, frequency, last_generated_date, "
        "created_by_username, is_active) "
        "VALUES(?,?,?,?,?,?,?,?,1)",
        ("C42 daily hook test", events_dept, "normal", "admin",
         1.0, "daily", five_days_ago, "admin"))
    cleanup_rid = cur.lastrowid or dict(db.execute(
        "SELECT id FROM recurring_tasks WHERE template_title=?",
        ("C42 daily hook test",)).fetchone())["id"]
    db.commit()
print("[setup] rid=", cleanup_rid)

# Force-reset the throttle so we start from a clean state
A._LAST_RECURRING_CHECK = None

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

login("admin", "admin123")

# Test 1: first visit to /tasks fires the scheduler
rv = c.get("/tasks")
print("[1] /tasks ->", rv.status_code,
      "_LAST_RECURRING_CHECK set?", A._LAST_RECURRING_CHECK is not None)
assert rv.status_code == 200
assert A._LAST_RECURRING_CHECK is not None

# Verify the scheduler actually generated tasks
with A.app.app_context():
    db = A.get_db()
    rows = db.execute(
        "SELECT id, due_date FROM tasks WHERE recurring_id=? ORDER BY id",
        (cleanup_rid,)).fetchall()
    cleanup_tids = [dict(r)["id"] for r in rows]
print("[1a] tasks generated:", len(cleanup_tids), "(expected 2 for 5-day-old daily)")
assert len(cleanup_tids) == 2

# Test 2: capture the check time, visit again → throttle should hold
saved_check = A._LAST_RECURRING_CHECK
rv = c.get("/tasks")
print("[2] /tasks again ->", rv.status_code,
      "_LAST_RECURRING_CHECK changed?", A._LAST_RECURRING_CHECK != saved_check)
assert rv.status_code == 200
# Within 1 hour the throttle should NOT re-fire (timestamp unchanged
# because the function returned early)
assert A._LAST_RECURRING_CHECK == saved_check, (
    "throttle didn't hold — scheduler re-ran within 1 hour")

# Test 3: visiting /dashboard, /tasks/dashboard/personal, /tasks/recurring
# also respect the throttle (no extra runs)
prev = A._LAST_RECURRING_CHECK
for path in ['/dashboard', '/tasks/dashboard/personal', '/tasks/recurring']:
    rv = c.get(path)
    print(f"[3] {path} -> {rv.status_code}")
    assert rv.status_code == 200
assert A._LAST_RECURRING_CHECK == prev, "throttle leaked across routes"

# Test 4: manually reset throttle → next visit fires again
A._LAST_RECURRING_CHECK = None
rv = c.get("/tasks")
print("[4] after throttle-reset, /tasks ->", rv.status_code,
      "fires again:", A._LAST_RECURRING_CHECK is not None)
assert A._LAST_RECURRING_CHECK is not None
# Second run is idempotent — no NEW tasks should appear
with A.app.app_context():
    db = A.get_db()
    new_count = int(dict(db.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE recurring_id=?",
        (cleanup_rid,)).fetchone())["c"])
print(f"[4a] task count after second hook fire: {new_count} (expected 2 — idempotent)")
assert new_count == 2

# Test 5: silent failure mode — break the scheduler temporarily
A._LAST_RECURRING_CHECK = None
import unittest.mock as _mock
def _broken(*a, **kw): raise RuntimeError("intentional smoke crash")
saved = A._generate_due_recurring_tasks
A._generate_due_recurring_tasks = _broken
try:
    rv = c.get("/tasks")
    print("[5] /tasks with broken scheduler ->", rv.status_code,
          "(should still be 200)")
    assert rv.status_code == 200
finally:
    A._generate_due_recurring_tasks = saved

# Test 6: regression — all 8 routes still respond
A._LAST_RECURRING_CHECK = None
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[6] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for tid in cleanup_tids:
        db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE recurring_id=?", (cleanup_rid,))
    db.execute("DELETE FROM recurring_tasks WHERE id=?", (cleanup_rid,))
    db.commit()

print("\nC42 smoke passed.")
