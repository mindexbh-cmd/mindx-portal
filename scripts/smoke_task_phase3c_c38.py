"""C38 smoke - /tasks/recurring page."""
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
rv = c.get("/tasks/recurring")
print("[1] student ->", rv.status_code)
assert rv.status_code == 403

# 2. admin → 200 with full markup
c.get("/")
login("admin", "admin123")
rv = c.get("/tasks/recurring")
body = rv.get_data(as_text=True)
print("[2] admin ->", rv.status_code, "len=", len(body))
checks = [
    ("table", 'id="r-table"' in body),
    ("tbody", 'id="r-tbody"' in body),
    ("show-inactive toggle", 'id="r-show-inactive"' in body),
    ("add btn", 'id="r-add-btn"' in body),
    ("recurring fetch", '/api/recurring-tasks' in body),
    ("delete fn", "window._recurDelete" in body),
    ("admin flag", "R_IS_ADMIN = true" in body),
    ("placeholder swapped", "IS_ADMIN_PLACEHOLDER" not in body),
    ("freq pills CSS", '.freq-daily' in body and '.freq-weekly' in body
                        and '.freq-monthly' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 3. raed → 200, admin flag false
c.get("/")
login("980909805", "raed123")
rv = c.get("/tasks/recurring")
body_r = rv.get_data(as_text=True)
print("[3] raed ->", rv.status_code, "len=", len(body_r))
assert rv.status_code == 200
assert "R_IS_ADMIN = false" in body_r

# 4. /tasks list still works
rv = c.get("/tasks")
print("[4] /tasks list ->", rv.status_code)
assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC38 smoke passed.")
