"""Phase 2a full E2E — admin lifecycle + raed scoping + student lockout."""
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

# Setup
with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("e2e_student", A.hp("s123"), "student", "طالب"))
    db.commit()

print("════════════ SCENARIO A: ADMIN ════════════")
login("admin", "admin123")

# 1. GET /api/departments
rv = c.get("/api/departments")
j = rv.get_json() or {}
print("[A1] /api/departments ->", rv.status_code,
      "count=", len(j.get("departments") or []))
assert rv.status_code == 200
events_id = next(d["id"] for d in j["departments"]
                 if d["name_ar"] == "قسم الفعاليات")

# 2. POST /api/tasks (assign to raed, dept=الفعاليات, priority=urgent)
rv = c.post("/api/tasks", json={
    "title": "E2E تنظيف القاعة 2",
    "description": "قبل فعالية الأسبوع",
    "department_id": events_id,
    "priority": "urgent",
    "assigned_to_username": "980909805",
    "due_date": "2026-06-01",
    "estimated_hours": 2.5,
    "tags": ["فعالية", "تنظيف"]
})
j = rv.get_json()
tid = j["id"]
print("[A2] POST /api/tasks ->", rv.status_code, "id=", tid,
      "task title:", j["task"]["title"])
assert rv.status_code == 200
assert j["task"]["status"] == "new"
assert j["task"]["dept_name_ar"] == "قسم الفعاليات"

# 3. GET /api/tasks → see it
rv = c.get("/api/tasks")
j = rv.get_json()
print("[A3] GET /api/tasks ->", rv.status_code, "total=", j["total"])
assert any(t["id"] == tid for t in j["tasks"])

# 4. GET /api/tasks/<id> → full detail
rv = c.get("/api/tasks/" + str(tid))
j = rv.get_json()
print("[A4] GET /api/tasks/<id> ->", rv.status_code,
      "tags:", j["task"]["tags"],
      "is_overdue:", j["task"]["is_overdue"])
assert rv.status_code == 200

# 5. PATCH /api/tasks/<id> change priority to normal
rv = c.patch("/api/tasks/" + str(tid), json={"priority": "normal"})
j = rv.get_json()
print("[A5] PATCH priority ->", rv.status_code,
      "new priority:", j["task"]["priority"])
assert j["task"]["priority"] == "normal"

# 6. POST /api/tasks/<id>/status new → in_progress
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "in_progress"})
j = rv.get_json()
print("[A6] new→in_progress ->", rv.status_code,
      "started_at:", j["task"]["started_at"])
assert j["task"]["started_at"] is not None

# 7. in_progress → completed
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "completed"})
j = rv.get_json()
print("[A7] in_progress→completed ->", rv.status_code,
      "completed_at:", j["task"]["completed_at"])
assert j["task"]["completed_at"] is not None

print()
print("════════════ SCENARIO B: RAED ════════════")
c.get("/")
login("980909805", "raed123")

# 8. GET /api/tasks (raed sees only own)
rv = c.get("/api/tasks")
j = rv.get_json()
print("[B8] raed GET /api/tasks ->", rv.status_code, "total=", j["total"])
# Confirm raed sees the e2e task (he's assignee)
raed_visible_ids = {t["id"] for t in j["tasks"]}
assert tid in raed_visible_ids

# 9. raed GET detail of his task
rv = c.get("/api/tasks/" + str(tid))
print("[B9] raed GET /api/tasks/<id> ->", rv.status_code)
assert rv.status_code == 200

# 10. raed tries to PATCH assigned_to → 403
rv = c.patch("/api/tasks/" + str(tid),
             json={"assigned_to_username": "admin"})
print("[B10] raed PATCH assigned_to ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 11. raed tries to view non-existent task → 404
rv = c.get("/api/tasks/99999")
print("[B11] raed bogus task ->", rv.status_code)
assert rv.status_code == 404

# Create a stranger's task to test cross-visibility
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "E2E stranger task",
    "department_id": events_id,
    "priority": "low",
    "assigned_to_username": "teacher1",
    "due_date": "2026-06-15",
    "estimated_hours": 1
})
stranger_tid = rv.get_json()["id"]
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/tasks/" + str(stranger_tid))
print("[B12] raed views stranger task ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

print()
print("════════════ SCENARIO C: STUDENT ════════════")
c.get("/")
login("e2e_student", "s123")

# 13-17. All endpoints → 403
for path, method, body in [
    ("/api/departments", "GET", None),
    ("/api/tasks", "GET", None),
    ("/api/tasks", "POST", {"title": "x", "department_id": 1,
                              "priority": "normal",
                              "assigned_to_username": "e2e_student",
                              "due_date": "2026-06-01",
                              "estimated_hours": 1}),
    ("/api/tasks/" + str(tid), "GET", None),
    ("/api/tasks/" + str(tid), "PATCH", {"title": "x"}),
    ("/api/tasks/" + str(tid) + "/status", "POST", {"status": "cancelled"}),
]:
    if method == "GET":     rv = c.get(path)
    elif method == "POST":  rv = c.post(path, json=body or {})
    elif method == "PATCH": rv = c.patch(path, json=body or {})
    print("[C]", method, path, "->", rv.status_code)
    assert rv.status_code == 403, (method, path, rv.status_code)

print()
print("════════════ SCENARIO D: REGRESSION ════════════")
c.get("/")
login("admin", "admin123")
for p in ["/parent","/points/manage","/dashboard","/expenses","/assets","/database","/groups","/attendance"]:
    rv = c.get(p)
    print("[D]", p, "->", rv.status_code)
    assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM tasks WHERE id IN(?,?)", (tid, stranger_tid))
    db.execute("DELETE FROM users WHERE username=?", ("e2e_student",))
    db.commit()

print("\nALL Phase 2a E2E SCENARIOS PASSED.")
