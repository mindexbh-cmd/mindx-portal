"""C2 smoke - /tasks modal: assignee free-text → dropdown."""
import os, sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ── Test 1: /tasks markup has <select id="task-assignee"> ──
login("admin", "admin123")
rv = c.get("/tasks")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
assert '<select id="task-assignee">' in html, "select markup missing"
# Old free-text input shape removed
assert 'list="task-assignee-list"' not in html, "old datalist still wired"
assert '<datalist id="task-assignee-list">' not in html, "old datalist still in body"
# Placeholder option present
assert '— اختر الموظف —' in html or 'اختر الموظف' in html, (
    "placeholder option missing")
print("[1] /tasks markup: <select id=task-assignee> + no datalist remnants")

# JS helpers wired
assert '/api/users/assignable' in html, "endpoint URL not referenced in JS"
assert '_ensureAssignees' in html, "_ensureAssignees helper missing"
assert '_renderAssignees' in html, "_renderAssignees helper missing"
print("[1a] _ensureAssignees + _renderAssignees + endpoint URL present")

# ── Test 2: full task-create round trip via the existing endpoint ──
import sqlite3
created_tid = None
with A.app.app_context():
    db = A.get_db()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

# admin POST /api/tasks with assigned_to_username='teacher1'
body = {
    "title": "C2 smoke task",
    "description": "Created via dropdown-swap smoke",
    "department_id": events_dept,
    "assigned_to_username": "teacher1",
    "priority": "normal",
    "due_date": "2026-05-20",
    "estimated_hours": 1.0
}
rv = c.post("/api/tasks", headers={"Content-Type": "application/json"},
            data=json.dumps(body))
j = rv.get_json()
print("[2] POST /api/tasks ->", rv.status_code, j)
assert rv.status_code == 200 and j["ok"] is True
created_tid = j.get("task_id") or j.get("id") or (j.get("task") or {}).get("id")
assert created_tid, f"no task id in response: {j}"
print(f"[2a] task created: id={created_tid}")

# ── Test 3: GET back, assignee is teacher1 ──
rv = c.get(f"/api/tasks/{created_tid}")
j2 = rv.get_json()
assert j2["ok"] is True
assert j2["task"]["assigned_to_username"] == "teacher1"
print(f"[3] task assignee in DB: teacher1 ✓")

# ── Test 4: PATCH to admin via the same endpoint (admin can reassign) ──
rv = c.patch(f"/api/tasks/{created_tid}",
             headers={"Content-Type": "application/json"},
             data=json.dumps({"assigned_to_username": "admin"}))
print(f"[4] PATCH reassign -> {rv.status_code}")
assert rv.status_code == 200
rv = c.get(f"/api/tasks/{created_tid}")
assert rv.get_json()["task"]["assigned_to_username"] == "admin"
print("[4a] reassign verified in DB")

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM tasks WHERE id=?", (created_tid,))
    db.commit()

# ── Test 5: 8-route regression ──
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[5] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# ── Test 6: teacher can still load /tasks (modal HTML present for them) ──
login("teacher1", "tea123")
rv = c.get("/tasks")
assert rv.status_code == 200
html2 = rv.get_data(as_text=True)
assert '<select id="task-assignee">' in html2
print("[6] teacher1 /tasks: dropdown markup served")

print("\nC2 smoke passed.")
