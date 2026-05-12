"""C12 smoke - GET /api/tasks with role-based filtering."""
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

# Seed student + a handful of tasks
task_ids = []
with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("smoke_student", A.hp("stu123"), "student", "طالب اختبار"))
    db.commit()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]
    admin_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("الإدارة",)).fetchone())["id"]

# Seed via the API to exercise the full POST path
login("admin", "admin123")
for desc, body in [
    ("admin → raed urgent",
     {"title": "C12 admin→raed urgent", "department_id": events_dept,
      "priority": "urgent", "assigned_to_username": "980909805",
      "due_date": "2026-06-01", "estimated_hours": 2}),
    ("admin → admin normal",
     {"title": "C12 admin self normal", "department_id": admin_dept,
      "priority": "normal", "assigned_to_username": "admin",
      "due_date": "2026-06-15", "estimated_hours": 1}),
    ("admin → teacher1 low",
     {"title": "C12 admin→teacher1 low", "department_id": admin_dept,
      "priority": "low", "assigned_to_username": "teacher1",
      "due_date": "2026-06-30", "estimated_hours": 1}),
]:
    rv = c.post("/api/tasks", json=body)
    j = rv.get_json()
    task_ids.append(j["id"])
    print("[setup]", desc, "id=", j["id"])

# Also have raed create one
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks", json={
    "title": "C12 raed-created self",
    "department_id": events_dept, "priority": "critical",
    "assigned_to_username": "980909805",
    "due_date": "2026-05-25", "estimated_hours": 1
})
j = rv.get_json()
task_ids.append(j["id"])
print("[setup] raed-created id=", j["id"])

# 1. Unauth -> 302
c.get("/")
rv = c.get("/api/tasks")
print("[1] unauth ->", rv.status_code)
assert rv.status_code == 302

# 2. student -> 403
login("smoke_student", "stu123")
rv = c.get("/api/tasks")
print("[2] student ->", rv.status_code)
assert rv.status_code == 403

# 3. admin sees all
c.get("/")
login("admin", "admin123")
rv = c.get("/api/tasks")
j = rv.get_json()
print("[3] admin sees all -> total=", j["total"], "len(tasks)=", len(j["tasks"]))
assert rv.status_code == 200
# Our 4 task ids should be present
admin_visible = {t["id"] for t in j["tasks"]}
assert all(tid in admin_visible for tid in task_ids), f"missing: {set(task_ids) - admin_visible}"

# 4. admin filter assigned_to=raed
rv = c.get("/api/tasks?assigned_to=980909805")
j = rv.get_json()
print("[4] admin assigned_to=raed -> total=", j["total"])
# Should only contain raed-assigned tasks
for t in j["tasks"]:
    assert t["assigned_to_username"] == "980909805"

# 5. raed sees only his own (assigned OR created)
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/tasks")
j = rv.get_json()
print("[5] raed total=", j["total"])
for t in j["tasks"]:
    assert (t["assigned_to_username"] == "980909805"
            or t["created_by_username"] == "980909805"), \
        f"raed saw foreign task: {t}"
# Should NOT see teacher1's task
teacher_task_id = [tid for tid in task_ids if tid][2]  # 3rd one is teacher1's
seen_ids = {t["id"] for t in j["tasks"]}
assert teacher_task_id not in seen_ids, "raed saw teacher1's task!"

# 6. raed tries to filter assigned_to=admin -> silently ignored
rv = c.get("/api/tasks?assigned_to=admin")
j = rv.get_json()
print("[6] raed tries assigned_to=admin -> total=", j["total"])
# Should still only contain his own
for t in j["tasks"]:
    assert (t["assigned_to_username"] == "980909805"
            or t["created_by_username"] == "980909805"), \
        f"raed probed admin tasks: {t}"

# 7. priority filter
c.get("/")
login("admin", "admin123")
rv = c.get("/api/tasks?priority=urgent")
j = rv.get_json()
print("[7] admin priority=urgent -> total=", j["total"])
for t in j["tasks"]:
    assert t["priority"] == "urgent"

# 8. q LIKE search
rv = c.get("/api/tasks?q=C12 admin")
j = rv.get_json()
print("[8] q='C12 admin' -> total=", j["total"])
assert all("c12 admin" in t["title"].lower() for t in j["tasks"])

# 9. limit
rv = c.get("/api/tasks?limit=2")
j = rv.get_json()
print("[9] limit=2 -> len(tasks)=", len(j["tasks"]), "total=", j["total"])
assert len(j["tasks"]) <= 2

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for tid in task_ids:
        db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC12 smoke passed.")
