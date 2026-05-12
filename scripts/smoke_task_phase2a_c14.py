"""C14 smoke - PATCH /api/tasks/<id> with immutability + role rules."""
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
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]
    admin_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("الإدارة",)).fetchone())["id"]

# Admin creates a task assigned to raed (so admin=creator, raed=assignee)
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C14 admin-created", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-15", "estimated_hours": 2
})
admin_tid = rv.get_json()["id"]
print("[setup] admin_tid=", admin_tid)

# Raed creates own task (raed is both creator + assignee)
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks", json={
    "title": "C14 raed-self", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-15", "estimated_hours": 2
})
raed_tid = rv.get_json()["id"]
print("[setup] raed_tid=", raed_tid)

# 1. admin edits any field on admin-created task → 200
c.get("/")
login("admin", "admin123")
rv = c.patch("/api/tasks/" + str(admin_tid),
             json={"title": "C14 admin-updated", "priority": "urgent"})
print("[1] admin updates own task ->", rv.status_code, rv.get_json().get("task", {}).get("title"))
assert rv.status_code == 200

# 2. admin tries to PATCH immutable field (status) → 400
rv = c.patch("/api/tasks/" + str(admin_tid),
             json={"status": "completed"})
print("[2] PATCH status ->", rv.status_code, rv.get_json())
assert rv.status_code == 400
assert "غير قابلة للتعديل" in rv.get_json().get("error", "")

# 3. admin PATCH created_at → 400
rv = c.patch("/api/tasks/" + str(admin_tid),
             json={"created_at": "2020-01-01"})
print("[3] PATCH created_at ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 4. admin reassigns to teacher1 → 200
rv = c.patch("/api/tasks/" + str(admin_tid),
             json={"assigned_to_username": "teacher1"})
print("[4] admin reassigns ->", rv.status_code)
assert rv.status_code == 200
# Now teacher1 is assignee; raed is no longer
rv = c.get("/api/tasks/" + str(admin_tid))
assert rv.get_json()["task"]["assigned_to_username"] == "teacher1"

# Re-assign back to raed for subsequent tests
rv = c.patch("/api/tasks/" + str(admin_tid),
             json={"assigned_to_username": "980909805"})
assert rv.status_code == 200

# 5. raed (assignee, NOT creator) tries to edit title → 403
c.get("/")
login("980909805", "raed123")
rv = c.patch("/api/tasks/" + str(admin_tid),
             json={"title": "محاولة تعديل عنوان"})
print("[5] assignee edits title ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 6. raed (assignee) edits actual_hours → 200
rv = c.patch("/api/tasks/" + str(admin_tid),
             json={"actual_hours": 1.75})
print("[6] assignee edits actual_hours ->", rv.status_code, rv.get_json().get("task", {}).get("actual_hours"))
assert rv.status_code == 200

# 7. raed tries to reassign to admin → 403
rv = c.patch("/api/tasks/" + str(admin_tid),
             json={"assigned_to_username": "admin"})
print("[7] non-admin reassign ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 8. raed edits OWN task title (he is creator AND assignee) → 200
rv = c.patch("/api/tasks/" + str(raed_tid),
             json={"title": "C14 raed updated own"})
print("[8] raed edits own task title ->", rv.status_code)
assert rv.status_code == 200

# 9. teacher1 (not creator, not assignee, not admin) tries → 403
c.get("/")
login("teacher1", "tea123")
rv = c.patch("/api/tasks/" + str(raed_tid),
             json={"title": "نزول من الجيران"})
print("[9] stranger edits ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 10. PATCH with invalid priority → 400
c.get("/")
login("admin", "admin123")
rv = c.patch("/api/tasks/" + str(admin_tid),
             json={"priority": "supreme"})
print("[10] invalid priority ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 11. Empty PATCH body → 400
rv = c.patch("/api/tasks/" + str(admin_tid), json={})
print("[11] empty body ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 12. PATCH non-existent task → 404
rv = c.patch("/api/tasks/999999", json={"title": "x"})
print("[12] bogus tid ->", rv.status_code)
assert rv.status_code == 404

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM tasks WHERE id IN(?,?)", (admin_tid, raed_tid))
    db.commit()

print("\nC14 smoke passed.")
