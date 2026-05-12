"""C10 smoke - GET /api/departments."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Ensure student exists for the permission denial test
with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("smoke_student", A.hp("stu123"), "student", "طالب اختبار"))
    db.commit()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# 1. Unauth -> 302
rv = c.get("/api/departments")
print("[1] unauth ->", rv.status_code)
assert rv.status_code == 302

# 2. student -> 403
login("smoke_student", "stu123")
rv = c.get("/api/departments")
print("[2] student ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 3. admin -> 200, 9 rows
c.get("/")
login("admin", "admin123")
rv = c.get("/api/departments")
j = rv.get_json() or {}
print("[3] admin ->", rv.status_code, "depts:", len(j.get("departments") or []))
assert rv.status_code == 200
deps = j.get("departments") or []
assert len(deps) == 9
# Each row has id/name_ar/icon/color
for d in deps:
    assert "id" in d and "name_ar" in d and "icon" in d and "color" in d
print("    first:", deps[0])

# 4. raed -> 200, 9 rows
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/departments")
j = rv.get_json() or {}
print("[4] raed ->", rv.status_code, "depts:", len(j.get("departments") or []))
assert rv.status_code == 200
assert len(j.get("departments") or []) == 9

# 5. teacher1 -> 200
c.get("/")
login("teacher1", "tea123")
rv = c.get("/api/departments")
j = rv.get_json() or {}
print("[5] teacher1 ->", rv.status_code, "depts:", len(j.get("departments") or []))
assert rv.status_code == 200
assert len(j.get("departments") or []) == 9

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC10 smoke passed.")
