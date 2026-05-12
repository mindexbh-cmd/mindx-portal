"""C31 smoke - /tasks/<tid> detail page."""
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

# Setup a task
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C31 detail page test",
    "department_id": events_dept, "priority": "urgent",
    "assigned_to_username": "980909805",
    "due_date": "2026-06-15", "estimated_hours": 2
})
tid = rv.get_json()["id"]
print("[setup] tid=", tid)

# 1. admin detail page
rv = c.get("/tasks/" + str(tid))
body = rv.get_data(as_text=True)
print("[1] admin /tasks/<tid> ->", rv.status_code, "len=", len(body))
checks = [
    ("admin flag", "T_IS_ADMIN = true" in body),
    ("TID injected", "TID = " + str(tid) in body),
    ("placeholders swapped", "IS_ADMIN_PLACEHOLDER" not in body
                              and "TID_PLACEHOLDER" not in body),
    ("description panel", 'id="t-desc"' in body),
    ("comments section", 'id="t-comments-list"' in body),
    ("comment form", 'id="t-comment-input"' in body),
    ("attachments section", 'id="t-attach-list"' in body),
    ("dropzone", 'id="t-drop"' in body),
    ("eval panel", 'id="t-eval-panel"' in body),
    ("actions box", 'id="t-actions"' in body),
    ("meta panel timeline", 't-ts-created' in body),
    ("modal (re-used)", 'id="task-modal"' in body),
    ("transition fn", '_transition' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 2. raed detail page (he's the assignee)
c.get("/")
login("980909805", "raed123")
rv = c.get("/tasks/" + str(tid))
body_r = rv.get_data(as_text=True)
print("[2] raed /tasks/<tid> ->", rv.status_code, "len=", len(body_r))
assert rv.status_code == 200
assert "T_IS_ADMIN = false" in body_r

# 3. student → 403 polite
c.get("/")
login("smoke_student", "s123")
rv = c.get("/tasks/" + str(tid))
print("[3] student ->", rv.status_code)
assert rv.status_code == 403

# 4. /tasks list still works
c.get("/")
login("admin", "admin123")
rv = c.get("/tasks")
print("[4] /tasks list still OK ->", rv.status_code)
assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM task_comments WHERE task_id=?", (tid,))
    db.execute("DELETE FROM task_attachments WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC31 smoke passed.")
