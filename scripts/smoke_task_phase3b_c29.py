"""C29 smoke - /tasks list page role-aware."""
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

# 1. Unauth -> 302
rv = c.get("/tasks")
print("[1] unauth ->", rv.status_code)
assert rv.status_code == 302

# 2. student -> 403 polite page
login("smoke_student", "s123")
rv = c.get("/tasks")
print("[2] student ->", rv.status_code)
assert rv.status_code == 403
assert "&#x1F512;" in rv.get_data(as_text=True)

# 3. admin -> 200 with admin flag true
c.get("/")
login("admin", "admin123")
rv = c.get("/tasks")
body = rv.get_data(as_text=True)
print("[3] admin /tasks len=", len(body))
assert rv.status_code == 200
checks = [
    ("admin flag", "T_IS_ADMIN = true" in body),
    ("placeholder swapped", "IS_ADMIN_PLACEHOLDER" not in body),
    ("filter bar", 'id="f-status"' in body),
    ("dept filter", 'id="f-dept"' in body),
    ("admin-only assignee filter", 'admin-only' in body),
    ("add button", 'task-add-btn' in body),
    ("tasks table tbody", 'id="tasks-tbody"' in body),
    ("departments fetch", '/api/departments' in body),
    ("tasks fetch", '/api/tasks?' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 4. raed -> 200, admin flag false
c.get("/")
login("980909805", "raed123")
rv = c.get("/tasks")
body_r = rv.get_data(as_text=True)
print("[4] raed /tasks ->", rv.status_code, "len=", len(body_r))
assert rv.status_code == 200
assert "T_IS_ADMIN = false" in body_r
assert "IS_ADMIN_PLACEHOLDER" not in body_r

# 5. Regression
c.get("/")
login("admin", "admin123")
for p in ["/parent","/points/manage","/dashboard","/expenses","/assets"]:
    rv = c.get(p)
    print("[reg]", p, "->", rv.status_code)
    assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC29 smoke passed.")
