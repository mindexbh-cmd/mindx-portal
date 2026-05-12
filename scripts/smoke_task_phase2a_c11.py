"""C11 smoke - POST /api/tasks with full validation + RBAC."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Seed student
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

# Get dept id (الفعاليات = events dept seeded at sort_order=6, id=6)
with A.app.app_context():
    db = A.get_db()
    events_dept_id = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?", ("قسم الفعاليات",)
        ).fetchone())["id"]
print("[setup] events_dept_id =", events_dept_id)

task_ids = []

# 1. Unauth -> 302
rv = c.post("/api/tasks", json={})
print("[1] unauth ->", rv.status_code)
assert rv.status_code == 302

# 2. student -> 403
login("smoke_student", "stu123")
rv = c.post("/api/tasks", json={"title": "x", "department_id": events_dept_id,
                                  "priority": "normal",
                                  "assigned_to_username": "smoke_student",
                                  "due_date": "2026-06-01", "estimated_hours": 2})
print("[2] student ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 3. admin happy path: assign to raed
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "تنظيف القاعة 2", "department_id": events_dept_id,
    "priority": "urgent",
    "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 2.5,
    "tags": ["طارئ", "أسبوعي"],
    "description": "تنظيف شامل قبل الفعالية"
})
j = rv.get_json()
print("[3] admin happy ->", rv.status_code, "id=", j.get("id"),
      "linked task title:", (j.get("task") or {}).get("title"))
assert rv.status_code == 200
assert j.get("task", {}).get("tags") == ["طارئ", "أسبوعي"]
assert j.get("task", {}).get("dept_name_ar") == "قسم الفعاليات"
task_ids.append(j["id"])

# 4. admin tries to assign to non-assignable user (student) -> 400
rv = c.post("/api/tasks", json={
    "title": "بدون صلاحية", "department_id": events_dept_id,
    "priority": "normal",
    "assigned_to_username": "smoke_student",
    "due_date": "2026-06-01", "estimated_hours": 1
})
print("[4] admin→student ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 5. raed self-assigns -> 200
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks", json={
    "title": "مهمة شخصية لرائد", "department_id": events_dept_id,
    "priority": "normal",
    "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1.5
})
j = rv.get_json()
print("[5] raed self ->", rv.status_code, "id=", j.get("id"))
assert rv.status_code == 200
task_ids.append(j["id"])

# 6. raed tries to assign to admin -> 403
rv = c.post("/api/tasks", json={
    "title": "محاولة إسناد للمدير", "department_id": events_dept_id,
    "priority": "normal",
    "assigned_to_username": "admin",
    "due_date": "2026-06-01", "estimated_hours": 1
})
print("[6] raed→admin ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 7. missing due_date -> 400
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "بدون تاريخ", "department_id": events_dept_id,
    "priority": "normal", "assigned_to_username": "980909805",
    "estimated_hours": 2
})
print("[7] missing due_date ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 8. past due_date -> 400
rv = c.post("/api/tasks", json={
    "title": "تاريخ ماضي", "department_id": events_dept_id,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2024-01-01", "estimated_hours": 2
})
print("[8] past due_date ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 9. invalid priority -> 400
rv = c.post("/api/tasks", json={
    "title": "أولوية خاطئة", "department_id": events_dept_id,
    "priority": "super_critical", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 2
})
print("[9] invalid priority ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 10. non-existent department_id -> 400
rv = c.post("/api/tasks", json={
    "title": "قسم خاطئ", "department_id": 999,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 2
})
print("[10] bogus dept ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 11. estimated_hours = 0 -> 400
rv = c.post("/api/tasks", json={
    "title": "صفر ساعات", "department_id": events_dept_id,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 0
})
print("[11] hours=0 ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 12. tags: too many (11) -> 400
rv = c.post("/api/tasks", json={
    "title": "وسوم كثيرة", "department_id": events_dept_id,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1,
    "tags": ["t"+str(i) for i in range(11)]
})
print("[12] 11 tags ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 13. title too long (>200) -> 400
rv = c.post("/api/tasks", json={
    "title": "x"*201, "department_id": events_dept_id,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1
})
print("[13] title>200 ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for tid in task_ids:
        db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC11 smoke passed.")
