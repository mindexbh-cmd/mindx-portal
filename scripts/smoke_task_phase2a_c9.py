"""C9 smoke - 4 task permission helpers."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Seed a student/parent user pair if missing (needed for permission tests
# below + C11/C12 smoke tests later in the phase)
with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("smoke_student", A.hp("stu123"), "student", "طالب اختبار"))
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("smoke_parent", A.hp("par123"), "parent", "ولي أمر اختبار"))
    db.commit()

with A.app.test_request_context():
    # _can_use_tasks
    print("[1] _can_use_tasks tests:")
    # None / empty
    assert A._can_use_tasks(None) is False
    assert A._can_use_tasks({}) is False
    print("    None / empty -> False ✓")
    # admin (was backfilled to can_be_assigned_tasks=1)
    assert A._can_use_tasks({"username": "admin", "role": "admin"}) is True
    print("    admin -> True ✓")
    # raed
    assert A._can_use_tasks({"username": "980909805", "role": "manager"}) is True
    print("    raed -> True ✓")
    # teacher
    assert A._can_use_tasks({"username": "teacher1", "role": "teacher"}) is True
    print("    teacher1 -> True ✓")
    # student (seeded, cba defaults to 0)
    assert A._can_use_tasks({"username": "smoke_student", "role": "student"}) is False
    print("    smoke_student -> False ✓")
    # parent
    assert A._can_use_tasks({"username": "smoke_parent", "role": "parent"}) is False
    print("    smoke_parent -> False ✓")
    # nonexistent user
    assert A._can_use_tasks({"username": "ghost", "role": "admin"}) is False
    print("    nonexistent -> False ✓")

    # _can_manage_all_tasks
    print("[2] _can_manage_all_tasks tests:")
    assert A._can_manage_all_tasks({"role": "admin"}) is True
    assert A._can_manage_all_tasks({"role": "manager"}) is False
    assert A._can_manage_all_tasks({"role": "teacher"}) is False
    assert A._can_manage_all_tasks(None) is False
    print("    admin->T, manager->F, teacher->F, None->F ✓")

    # _can_assign_to_others (alias for admin-only today)
    assert A._can_assign_to_others({"role": "admin"}) is True
    assert A._can_assign_to_others({"role": "manager"}) is False
    print("[3] _can_assign_to_others: admin->T, manager->F ✓")

    # _can_see_task
    print("[4] _can_see_task tests:")
    task_row = {"assigned_to_username": "raed",
                "created_by_username": "admin"}
    # admin sees any
    assert A._can_see_task({"username":"admin","role":"admin"}, task_row) is True
    # assignee sees own
    assert A._can_see_task({"username":"raed","role":"manager"}, task_row) is True
    # creator sees own
    assert A._can_see_task({"username":"admin","role":"admin"}, task_row) is True
    # third party
    assert A._can_see_task({"username":"someone_else","role":"teacher"}, task_row) is False
    # None
    assert A._can_see_task(None, task_row) is False
    print("    admin->T, assignee->T, creator->T, stranger->F, None->F ✓")

# Regression: existing routes
c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code
login("admin", "admin123")
for p in ["/parent", "/points/manage", "/dashboard", "/expenses",
          "/assets"]:
    rv = c.get(p)
    print("[reg]", p, "->", rv.status_code)
    assert rv.status_code == 200, p

# Sentinel comment present
import re
src = open(A.app.config.get("APP_PY_PATH","app.py")
           if "APP_PY_PATH" in A.app.config else "app.py",
           encoding="utf-8").read()
assert "TASK MANAGEMENT SYSTEM" in src
print("[5] sentinel block present in app.py ✓")

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM users WHERE username IN(?, ?)",
               ("smoke_student", "smoke_parent"))
    db.commit()

print("\nC9 smoke passed.")
