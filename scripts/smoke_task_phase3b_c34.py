"""C34 smoke - team motivational dashboard page."""
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
rv = c.get("/tasks/dashboard/team")
print("[1] student ->", rv.status_code)
assert rv.status_code == 403

# 2. admin → 200
c.get("/")
login("admin", "admin123")
rv = c.get("/tasks/dashboard/team")
body = rv.get_data(as_text=True)
print("[2] admin ->", rv.status_code, "len=", len(body))
checks = [
    ("2 stat cards", body.count('class="stat ') >= 2),
    ("podium container", 'id="t-podium"' in body),
    ("motivation card", 'class="motivation-card"' in body),
    ("team total stat", 'id="t-team-total"' in body),
    ("in-progress stat", 'id="t-team-in-progress"' in body),
    ("message holder", 'id="t-message"' in body),
    ("team fetch", '/api/tasks/dashboard/team' in body),
    ("NO bottom_performers payload", 'bottom_performers' not in body.lower()),
    ("NO failure_rate payload", 'failure_rate' not in body.lower()),
    ("NO overdue payload", '"overdue"' not in body.lower()),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 3. raed → 200
c.get("/")
login("980909805", "raed123")
rv = c.get("/tasks/dashboard/team")
print("[3] raed ->", rv.status_code)
assert rv.status_code == 200

# 4. teacher1 → 200
c.get("/")
login("teacher1", "tea123")
rv = c.get("/tasks/dashboard/team")
print("[4] teacher1 ->", rv.status_code)
assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC34 smoke passed.")
