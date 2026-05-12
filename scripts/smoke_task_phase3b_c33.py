"""C33 smoke - personal dashboard page."""
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

# 1. student → 403
login("smoke_student", "s123")
rv = c.get("/tasks/dashboard/personal")
print("[1] student ->", rv.status_code)
assert rv.status_code == 403

# 2. admin → 200 with all page markers
c.get("/")
login("admin", "admin123")
rv = c.get("/tasks/dashboard/personal")
body = rv.get_data(as_text=True)
print("[2] admin ->", rv.status_code, "len=", len(body))
checks = [
    ("4 stat cards", body.count('class="stat ') >= 4),
    ("total stat", 'id="d-total"' in body),
    ("in-progress stat", 'id="d-in-progress"' in body),
    ("overdue stat", 'id="d-overdue"' in body),
    ("completed stat", 'id="d-completed"' in body),
    ("points panel", 'id="d-pts-total"' in body),
    ("badges grid", 'id="d-badges"' in body),
    ("current tasks table", 'id="d-current-table"' in body),
    ("recent table", 'id="d-recent-table"' in body),
    ("dashboard fetch", '/api/tasks/dashboard/personal' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label
assert rv.status_code == 200

# 3. raed → 200
c.get("/")
login("980909805", "raed123")
rv = c.get("/tasks/dashboard/personal")
print("[3] raed ->", rv.status_code)
assert rv.status_code == 200

# 4. /tasks list still works
rv = c.get("/tasks")
print("[4] /tasks list ->", rv.status_code)
assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC33 smoke passed.")
