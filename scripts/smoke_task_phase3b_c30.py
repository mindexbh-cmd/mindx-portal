"""C30 smoke - task add/edit modal + E2E POST flow."""
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

# 1. Admin /tasks contains modal markup
login("admin", "admin123")
rv = c.get("/tasks")
body = rv.get_data(as_text=True)
print("[1] admin /tasks len=", len(body))
checks = [
    ("modal markup", 'id="task-modal"' in body),
    ("title input", 'id="task-title"' in body),
    ("dept select", 'id="task-dept"' in body),
    ("assignee input", 'id="task-assignee"' in body),
    ("priority pills", 'id="task-pri-pills"' in body),
    ("due date", 'id="task-due"' in body),
    ("hours input", 'id="task-hours"' in body),
    ("tags input", 'id="task-tags"' in body),
    ("save btn", 'id="task-save-btn"' in body),
    ("admin assignee logic", "if (!T_IS_ADMIN)" in body),
    ("taskOpenAdd fn", "window.taskOpenAdd" in body),
    ("taskOpenEdit fn", "window.taskOpenEdit" in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 2. Raed /tasks has modal too
c.get("/")
login("980909805", "raed123")
rv = c.get("/tasks")
body_r = rv.get_data(as_text=True)
print("[2] raed /tasks len=", len(body_r))
assert 'id="task-modal"' in body_r
assert "T_IS_ADMIN = false" in body_r

# 3. E2E: admin POSTs a new task via the same body shape modal would send
c.get("/")
login("admin", "admin123")
with A.app.app_context():
    db = A.get_db()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

rv = c.post("/api/tasks", json={
    "title": "C30 modal smoke",
    "description": "via modal shape",
    "department_id": events_dept,
    "assigned_to_username": "980909805",
    "priority": "urgent",
    "due_date": "2026-06-15",
    "estimated_hours": 2.5,
    "tags": ["test", "modal"]
})
j = rv.get_json()
tid = j["id"]
print("[3] modal POST shape ->", rv.status_code, "id=", tid,
      "tags:", j["task"]["tags"])
assert rv.status_code == 200
assert j["task"]["tags"] == ["test", "modal"]

# 4. PATCH (edit flow)
rv = c.patch("/api/tasks/" + str(tid), json={"priority": "normal"})
print("[4] PATCH priority ->", rv.status_code,
      "new pri:", rv.get_json()["task"]["priority"])
assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.commit()

print("\nC30 smoke passed.")
