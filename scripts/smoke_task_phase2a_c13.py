"""C13 smoke - GET /api/tasks/<id> detail."""
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

# Seed student + 2 tasks (raed's own + admin's assigned-to-teacher)
with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("smoke_student", A.hp("stu123"), "student", "طالب"))
    db.commit()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C13 raed task", "department_id": events_dept,
    "priority": "urgent", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 2,
    "tags": ["test"], "description": "desc"
})
raed_tid = rv.get_json()["id"]
rv = c.post("/api/tasks", json={
    "title": "C13 teacher task", "department_id": events_dept,
    "priority": "low", "assigned_to_username": "teacher1",
    "due_date": "2026-06-15", "estimated_hours": 1
})
teacher_tid = rv.get_json()["id"]
print("[setup] raed_tid=", raed_tid, "teacher_tid=", teacher_tid)

# 1. admin sees any task → 200, full row
rv = c.get("/api/tasks/" + str(raed_tid))
j = rv.get_json()
print("[1] admin detail raed task ->", rv.status_code,
      "title:", j["task"]["title"], "tags:", j["task"]["tags"])
assert rv.status_code == 200
assert j["task"]["title"] == "C13 raed task"
assert j["task"]["tags"] == ["test"]
assert j["task"]["dept_name_ar"] == "قسم الفعاليات"

# 2. raed sees his own → 200
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/tasks/" + str(raed_tid))
print("[2] raed detail own ->", rv.status_code)
assert rv.status_code == 200

# 3. raed sees teacher's task → 403 (not his)
rv = c.get("/api/tasks/" + str(teacher_tid))
print("[3] raed detail teacher's ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 4. teacher1 sees own → 200
c.get("/")
login("teacher1", "tea123")
rv = c.get("/api/tasks/" + str(teacher_tid))
print("[4] teacher1 detail own ->", rv.status_code)
assert rv.status_code == 200

# 5. Non-existent task → 404
rv = c.get("/api/tasks/999999")
print("[5] bogus tid ->", rv.status_code, rv.get_json())
assert rv.status_code == 404

# 6. student -> 403
c.get("/")
login("smoke_student", "stu123")
rv = c.get("/api/tasks/" + str(raed_tid))
print("[6] student ->", rv.status_code)
assert rv.status_code == 403

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM tasks WHERE id IN(?,?)", (raed_tid, teacher_tid))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC13 smoke passed.")
