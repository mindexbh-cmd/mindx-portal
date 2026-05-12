"""C18 smoke - salary category restricted for raed."""
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

# Find the salary category id
with A.app.app_context():
    db = A.get_db()
    salary = db.execute(
        "SELECT id FROM expense_categories WHERE name_ar=?",
        ("رواتب وأجور",)).fetchone()
    salary_id = dict(salary)["id"] if salary else None
    op = db.execute(
        "SELECT id FROM expense_categories WHERE name_ar=?",
        ("تشغيلي (إيجار/كهرباء/إنترنت)",)).fetchone()
    op_id = dict(op)["id"] if op else None
print("[setup] salary cat id=", salary_id, "operational cat id=", op_id)

# raed POST salary -> 403
login("980909805", "raed123")
rv = c.post("/api/expenses",
            json={"category_id": salary_id, "amount": 500,
                  "description": "محاولة راتب",
                  "expense_date": "2026-05-12"})
print("[1] raed POST salary ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# raed POST operational -> 200
rv = c.post("/api/expenses",
            json={"category_id": op_id, "amount": 50,
                  "description": "كهرباء",
                  "expense_date": "2026-05-12"})
print("[2] raed POST operational ->", rv.status_code, rv.get_json())
assert rv.status_code == 200
raed_eid = (rv.get_json() or {}).get("id")

# raed tries to reclassify his expense → salary - 403
rv = c.patch("/api/expenses/" + str(raed_eid),
             json={"category_id": salary_id})
print("[3] raed PATCH to salary ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# admin POST salary -> 200
c.get("/")
login("admin", "admin123")
rv = c.post("/api/expenses",
            json={"category_id": salary_id, "amount": 800,
                  "description": "راتب مايو",
                  "expense_date": "2026-05-12"})
print("[4] admin POST salary ->", rv.status_code, rv.get_json())
assert rv.status_code == 200
admin_eid = (rv.get_json() or {}).get("id")

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM expenses WHERE id IN(?,?)", (raed_eid, admin_eid))
    db.commit()
print("\nAll C18 smoke checks passed.")
