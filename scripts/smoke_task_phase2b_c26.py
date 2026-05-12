"""C26 smoke - admin full performance dashboard."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

with A.app.app_context():
    db = A.get_db()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

# Setup: a few tasks across users + an evaluation
login("admin", "admin123")
ids = []
for body in [
    {"title": "C26 raed", "department_id": events_dept,
     "priority": "urgent", "assigned_to_username": "980909805",
     "due_date": "2026-12-31", "estimated_hours": 2},
    {"title": "C26 teacher", "department_id": events_dept,
     "priority": "normal", "assigned_to_username": "teacher1",
     "due_date": "2026-12-31", "estimated_hours": 1},
]:
    rv = c.post("/api/tasks", json=body)
    ids.append(rv.get_json()["id"])

# Mark both completed + evaluate one
with A.app.app_context():
    db = A.get_db()
    for tid in ids:
        db.execute("UPDATE tasks SET status='completed', "
                   "started_at=CURRENT_TIMESTAMP, "
                   "completed_at=CURRENT_TIMESTAMP WHERE id=?", (tid,))
    db.commit()
c.post("/api/tasks/" + str(ids[0]) + "/evaluate",
       json={"rating_stars": 5, "strength_badges": ["speed"]})
print("[setup] ids:", ids)

# 1. raed → 403
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/tasks/dashboard/admin")
print("[1] raed admin dashboard ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 2. admin → 200 with full shape
c.get("/")
login("admin", "admin123")
rv = c.get("/api/tasks/dashboard/admin")
j = rv.get_json()
print("[2] admin admin dashboard ->", rv.status_code)
print("    period:", j.get("period"))
ov = j.get("overview", {})
print("    overview keys:", sorted(ov.keys()))
print("    overview totals:", ov)
assert rv.status_code == 200
# Required overview keys
for k in ("total_tasks","completed","in_progress","cancelled",
          "overdue","avg_completion_days","avg_rating"):
    assert k in ov

# by_employee
emps = j.get("by_employee", [])
print("    by_employee count:", len(emps))
raed_emp = next((e for e in emps if e["username"] == "980909805"), None)
print("    raed entry:", raed_emp)
assert raed_emp is not None
assert raed_emp["completed"] >= 1
assert raed_emp["avg_rating"] == 5.0
assert raed_emp["total_points"] >= 70
assert raed_emp["strength_badges"]["speed"] >= 1

# by_department
deps = j.get("by_department", [])
print("    by_department count:", len(deps))
assert len(deps) == 9  # all active depts
events_row = next(d for d in deps if d["name_ar"] == "قسم الفعاليات")
print("    events dept:", events_row)
assert events_row["total_tasks"] >= 2

# by_priority
bp = j.get("by_priority", {})
print("    by_priority:", bp)
for k in ("critical","urgent","normal","low"):
    assert k in bp

# trends
trends = j.get("trends", {}).get("last_30_days", [])
print("    trends.last_30_days count:", len(trends))
assert len(trends) == 30
for t in trends[-3:]:
    assert "date" in t and "created" in t and "completed" in t

# 3. teacher1 → 403 (non-admin)
c.get("/")
login("teacher1", "tea123")
rv = c.get("/api/tasks/dashboard/admin")
print("[3] teacher1 ->", rv.status_code)
assert rv.status_code == 403

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for tid in ids:
        db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
        db.execute("DELETE FROM task_evaluations WHERE task_id=?", (tid,))
        db.execute("DELETE FROM employee_points WHERE task_id=?", (tid,))
        db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.commit()

print("\nC26 smoke passed.")
