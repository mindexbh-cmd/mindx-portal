"""C25 smoke - team dashboard (motivational, top 3 only)."""
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

# Setup: complete tasks for multiple users this month
login("admin", "admin123")
created = []
# 3 completed for raed
for i in range(3):
    rv = c.post("/api/tasks", json={
        "title": f"C25 raed completed {i}", "department_id": events_dept,
        "priority": "normal", "assigned_to_username": "980909805",
        "due_date": "2026-12-31", "estimated_hours": 1
    })
    tid = rv.get_json()["id"]
    created.append(tid)
# 2 completed for teacher1
for i in range(2):
    rv = c.post("/api/tasks", json={
        "title": f"C25 teacher completed {i}", "department_id": events_dept,
        "priority": "normal", "assigned_to_username": "teacher1",
        "due_date": "2026-12-31", "estimated_hours": 1
    })
    tid = rv.get_json()["id"]
    created.append(tid)
# 1 completed for admin
rv = c.post("/api/tasks", json={
    "title": "C25 admin completed", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "admin",
    "due_date": "2026-12-31", "estimated_hours": 1
})
created.append(rv.get_json()["id"])

# Mark all as completed
with A.app.app_context():
    db = A.get_db()
    for tid in created:
        db.execute("UPDATE tasks SET status='completed', "
                   "completed_at=CURRENT_TIMESTAMP WHERE id=?", (tid,))
    db.commit()

# Also add 1 in_progress for the team_in_progress count
rv = c.post("/api/tasks", json={
    "title": "C25 in progress", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "teacher1",
    "due_date": "2026-12-31", "estimated_hours": 1
})
inprog_tid = rv.get_json()["id"]
with A.app.app_context():
    db = A.get_db()
    db.execute("UPDATE tasks SET status='in_progress', "
               "started_at=CURRENT_TIMESTAMP WHERE id=?", (inprog_tid,))
    db.commit()
print("[setup] created:", created, "in_progress:", inprog_tid)

# 1. raed gets team dashboard
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/tasks/dashboard/team")
j = rv.get_json()
print("[1] raed team dashboard ->", rv.status_code)
print("    period:", j.get("period"))
print("    team_total_tasks (this month):", j.get("team_total_tasks"))
print("    team_in_progress:", j.get("team_in_progress"))
print("    top_performers (max 3):")
for p in j.get("top_performers") or []:
    print("      -", p)
print("    motivational_message:", j.get("motivational_message"))
assert rv.status_code == 200
assert j["team_total_tasks"] >= 6
# Top 3 limited
assert len(j["top_performers"]) <= 3
# Order: raed (3) should be first
assert j["top_performers"][0]["username"] == "980909805"
assert j["top_performers"][0]["completed_count"] >= 3
# Message is one of the pool
assert j["motivational_message"] in (
    "معاً نبني مايندكس 💪",
    "كل مهمة منجزة خطوة نحو الأفضل 🌟",
    "فريق رائع، إنجازات أروع 🎉",
    "الجودة قبل الكمية، وأنتم تحققون الاثنين ✨",
    "شكراً لكل عضو في الفريق 🙏",
)
# No prohibited fields
forbidden = ("bottom_performers", "failure_rate", "overdue")
for k in forbidden:
    assert k not in j, f"forbidden field {k} present"
print("    no bottom_performers/failure_rate/overdue ✓")

# 2. teacher1 gets same shape
c.get("/")
login("teacher1", "tea123")
rv = c.get("/api/tasks/dashboard/team")
j = rv.get_json()
print("[2] teacher1 ->", rv.status_code, "team_total:", j.get("team_total_tasks"))
assert rv.status_code == 200
# Same shape
assert "top_performers" in j and "motivational_message" in j

# 3. admin gets same shape
c.get("/")
login("admin", "admin123")
rv = c.get("/api/tasks/dashboard/team")
print("[3] admin ->", rv.status_code)
assert rv.status_code == 200

# 4. student → 403
c.get("/")
login("smoke_student", "s123")
rv = c.get("/api/tasks/dashboard/team")
print("[4] student ->", rv.status_code)
assert rv.status_code == 403

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for tid in created + [inprog_tid]:
        db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC25 smoke passed.")
