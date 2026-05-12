"""C24 smoke - GET /api/tasks/dashboard/personal."""
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
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("smoke_student", A.hp("s123"), "student", "طالب"))
    db.commit()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

# Setup: admin creates 3 tasks for raed (one completed+evaluated)
login("admin", "admin123")
task_ids = []
for body in [
    {"title": "C24 new task", "department_id": events_dept,
     "priority": "normal", "assigned_to_username": "980909805",
     "due_date": "2026-06-15", "estimated_hours": 1},
    {"title": "C24 to complete", "department_id": events_dept,
     "priority": "urgent", "assigned_to_username": "980909805",
     "due_date": "2026-12-31", "estimated_hours": 2},
    {"title": "C24 overdue", "department_id": events_dept,
     "priority": "low", "assigned_to_username": "980909805",
     "due_date": "2026-05-12", "estimated_hours": 1},  # today
]:
    rv = c.post("/api/tasks", json=body)
    task_ids.append(rv.get_json()["id"])

# Complete + evaluate the 2nd one (raed gets points)
c.get("/")
login("980909805", "raed123")
c.post("/api/tasks/" + str(task_ids[1]) + "/status", json={"status": "in_progress"})
c.post("/api/tasks/" + str(task_ids[1]) + "/status", json={"status": "completed"})

c.get("/")
login("admin", "admin123")
c.post("/api/tasks/" + str(task_ids[1]) + "/evaluate",
       json={"rating_stars": 5, "strength_badges": ["speed", "quality"]})

print("[setup] tasks:", task_ids)

# 1. raed personal dashboard
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/tasks/dashboard/personal")
j = rv.get_json()
print("[1] raed dashboard ->", rv.status_code)
print("    user:", j["user"])
print("    summary:", j["summary"])
print("    points:", j["my_points"])
print("    badges:", j["my_strength_badges"])
print("    current_tasks count:", len(j["current_tasks"]))
print("    recent_completed count:", len(j["recent_completed"]))

assert rv.status_code == 200
assert j["user"]["username"] == "980909805"
# By-status: should reflect raed's tasks (3 raed tasks: 1 new, 1 completed,
# 1 today-due-still-new = 2 new + 1 completed = 3 total minimum from seeds)
assert j["summary"]["by_status"]["completed"] >= 1
# Points should reflect at least 70 (5*10 + urgent 10 + ontime 10)
assert j["my_points"]["total"] >= 70
# Strength badges: speed=1, quality=1
assert j["my_strength_badges"]["speed"] >= 1
assert j["my_strength_badges"]["quality"] >= 1
# Current tasks include new + in_progress
for t in j["current_tasks"]:
    assert t["status"] in ("new", "in_progress")

# 2. admin personal dashboard
c.get("/")
login("admin", "admin123")
rv = c.get("/api/tasks/dashboard/personal")
j = rv.get_json()
print("[2] admin dashboard ->", rv.status_code)
print("    total_my_tasks:", j["summary"]["total_my_tasks"])
assert rv.status_code == 200
# Admin created all 3 tasks → admin's "my tasks" = 3+ (creator visibility)
assert j["summary"]["total_my_tasks"] >= 3

# 3. student → 403
c.get("/")
login("smoke_student", "s123")
rv = c.get("/api/tasks/dashboard/personal")
print("[3] student ->", rv.status_code)
assert rv.status_code == 403

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for tid in task_ids:
        db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
        db.execute("DELETE FROM task_evaluations WHERE task_id=?", (tid,))
        db.execute("DELETE FROM employee_points WHERE task_id=?", (tid,))
        db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC24 smoke passed.")
