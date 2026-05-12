"""Phase 3b full E2E — exercises every new page + sidebar gating."""
import os, sys, io, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082")
PNG_B64 = base64.b64encode(PNG).decode()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("e2e_student", A.hp("s123"), "student", "طالب"))
    db.commit()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

print("════════ A: ADMIN ════════")
login("admin", "admin123")

# 1. Sidebar: dashboard contains 4 task links + tasks data attr
rv = c.get("/dashboard")
body = rv.get_data(as_text=True)
print("[A1] /dashboard ->", rv.status_code, "len=", len(body))
assert rv.status_code == 200
# Sidebar markers
assert 'href="/tasks"' in body
assert 'href="/tasks/dashboard/personal"' in body
assert 'href="/tasks/dashboard/team"' in body
assert 'href="/tasks/dashboard/admin"' in body
assert 'mx-tasks-link' in body
assert 'allowTasks = "1"' in body
print("[A1] sidebar markers ✓ + allowTasks=1")

# 2. All 4 task pages return 200
for url, title in [
    ("/tasks", "list page"),
    ("/tasks/dashboard/personal", "personal dashboard"),
    ("/tasks/dashboard/team", "team dashboard"),
    ("/tasks/dashboard/admin", "admin dashboard"),
]:
    rv = c.get(url)
    print("[A2]", title, "->", rv.status_code)
    assert rv.status_code == 200

# 3. Create + view + status flow via API (mirrors UI)
rv = c.post("/api/tasks", json={
    "title": "E2E phase 3b task",
    "department_id": events_dept,
    "priority": "urgent",
    "assigned_to_username": "980909805",
    "due_date": "2026-12-31",
    "estimated_hours": 2,
    "tags": ["E2E", "phase3b"]
})
tid = rv.get_json()["id"]
print("[A3] task created id=", tid)
rv = c.get("/tasks/" + str(tid))
print("[A4] /tasks/<id> ->", rv.status_code, "len=", len(rv.get_data(as_text=True)))
assert rv.status_code == 200

# 4. Raed advances + completes; admin evaluates
c.get("/")
login("980909805", "raed123")
c.post("/api/tasks/" + str(tid) + "/status", json={"status": "in_progress"})
c.post("/api/tasks/" + str(tid) + "/status", json={"status": "completed"})
# Raed views detail
rv = c.get("/tasks/" + str(tid))
print("[A5] raed detail ->", rv.status_code)
assert rv.status_code == 200

c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks/" + str(tid) + "/evaluate",
            json={"rating_stars": 4, "strength_badges": ["speed"]})
print("[A6] evaluate ->", rv.status_code, "points:", rv.get_json()["points_awarded"])

print()
print("════════ B: RAED ════════")
c.get("/")
login("980909805", "raed123")
# Sidebar shows task section (allowTasks=1 via Phase 1 backfill)
rv = c.get("/dashboard")
body_r = rv.get_data(as_text=True)
print("[B1] raed /dashboard allowTasks=1?",
      'allowTasks = "1"' in body_r)
assert 'allowTasks = "1"' in body_r
# Raed cannot access admin dashboard page
rv = c.get("/tasks/dashboard/admin")
print("[B2] raed admin dashboard ->", rv.status_code)
assert rv.status_code == 403
# Raed can access list, detail, personal, team
for url in ["/tasks", "/tasks/" + str(tid),
            "/tasks/dashboard/personal", "/tasks/dashboard/team"]:
    rv = c.get(url)
    print("[B3]", url, "->", rv.status_code)
    assert rv.status_code == 200

print()
print("════════ C: STUDENT ════════")
c.get("/")
login("e2e_student", "s123")
# Sidebar shows allowTasks=0
rv = c.get("/dashboard")
print("[C1] student /dashboard ->", rv.status_code)
# Student gets redirected from /dashboard to /portal/parent-hub
assert rv.status_code == 302
# Student → 403 on every task page
for url in ["/tasks", "/tasks/" + str(tid),
            "/tasks/dashboard/personal", "/tasks/dashboard/team",
            "/tasks/dashboard/admin"]:
    rv = c.get(url)
    print("[C2]", url, "->", rv.status_code)
    assert rv.status_code == 403

print()
print("════════ D: REGRESSION ════════")
c.get("/")
login("admin", "admin123")
for p in ["/parent","/points/manage","/dashboard","/expenses","/assets",
          "/database","/groups","/attendance",
          "/api/departments","/api/tasks",
          "/api/expenses/categories",
          "/api/expenses/dashboard","/api/assets"]:
    rv = c.get(p)
    print("[D]", p, "->", rv.status_code)
    assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM task_evaluations WHERE task_id=?", (tid,))
    db.execute("DELETE FROM employee_points WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("e2e_student",))
    db.commit()

print("\nALL Phase 3b E2E SCENARIOS PASSED.")
