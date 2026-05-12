"""C35 smoke - admin analytics dashboard page."""
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
rv = c.get("/tasks/dashboard/admin")
print("[1] student ->", rv.status_code)
assert rv.status_code == 403

# 2. raed (non-admin manager) → 403
c.get("/")
login("980909805", "raed123")
rv = c.get("/tasks/dashboard/admin")
print("[2] raed ->", rv.status_code)
assert rv.status_code == 403

# 3. teacher1 → 403
c.get("/")
login("teacher1", "tea123")
rv = c.get("/tasks/dashboard/admin")
print("[3] teacher1 ->", rv.status_code)
assert rv.status_code == 403

# 4. admin → 200
c.get("/")
login("admin", "admin123")
rv = c.get("/tasks/dashboard/admin")
body = rv.get_data(as_text=True)
print("[4] admin ->", rv.status_code, "len=", len(body))
checks = [
    ("overview stats", body.count('class="stat ') >= 6),
    ("employee table", 'id="a-emp-table"' in body),
    ("dept table", 'id="a-dept-table"' in body),
    ("priority table", 'id="a-pri-table"' in body),
    ("trend chart", 'id="a-trend"' in body),
    ("trend legend", 'trend-legend' in body),
    ("dashboard fetch", '/api/tasks/dashboard/admin' in body),
    ("403 guard text in page (for non-admin path)", "هذه اللوحة متاحة للمدير فقط" in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC35 smoke passed.")
