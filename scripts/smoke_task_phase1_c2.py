"""C2 smoke - users ALTER + assignable backfill."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

with A.app.app_context():
    db = A.get_db()
    cols = [r[1] for r in db.execute("PRAGMA table_info(users)").fetchall()]
    print("[1] users cols:", cols)
    assert "primary_department_id" in cols
    assert "can_be_assigned_tasks" in cols

    # Tag persisted
    t = db.execute("SELECT 1 FROM schema_migrations WHERE tag=?",
                   ("task_phase1_users_assignable_backfill_v1",)).fetchone()
    print("[2] tag persisted:", t is not None)
    assert t is not None

    # Backfill: admin/manager/teacher/staff → 1
    rows = db.execute(
        "SELECT username, role, COALESCE(can_be_assigned_tasks,0) AS cba "
        "FROM users ORDER BY role, username").fetchall()
    by_role_yes = {}
    by_role_no = {}
    for r in rows:
        d = dict(r)
        role = (d.get("role") or "").lower()
        bucket = by_role_yes if d.get("cba") == 1 else by_role_no
        bucket.setdefault(role, []).append(d.get("username"))
    print("[3] users with assignable=1, grouped by role:")
    for k, vs in sorted(by_role_yes.items()):
        print("   ", k, "->", vs)
    print("[4] users with assignable=0, grouped by role:")
    for k, vs in sorted(by_role_no.items()):
        print("   ", k, "->", vs)

    # Verify the rule: admin/manager/teacher/staff must be =1
    for r in rows:
        d = dict(r)
        role = (d.get("role") or "").lower()
        if role in ("admin", "manager", "teacher", "staff"):
            assert d.get("cba") == 1, f"{d['username']} ({role}) should be assignable"
        elif role in ("student", "parent"):
            assert d.get("cba") == 0, f"{d['username']} ({role}) must NOT be assignable"

# Regression
c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code
login("admin", "admin123")
for p in ["/parent", "/points/manage", "/dashboard", "/expenses",
          "/assets", "/database"]:
    rv = c.get(p)
    print("[reg] " + p + " ->", rv.status_code)
    assert rv.status_code == 200, p

print("\nC2 smoke passed.")
