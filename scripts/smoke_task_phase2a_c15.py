"""C15 smoke - POST /api/tasks/<id>/status state machine."""
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

# Admin creates task assigned to raed
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C15 lifecycle", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 2
})
tid = rv.get_json()["id"]
print("[setup] tid=", tid)

# 1. raed (assignee) new → in_progress
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "in_progress"})
j = rv.get_json()
print("[1] new→in_progress (assignee) ->", rv.status_code,
      "from/to:", j.get("transition"),
      "started_at:", j.get("task",{}).get("started_at"))
assert rv.status_code == 200
assert j["task"]["status"] == "in_progress"
assert j["task"]["started_at"] is not None

# 2. raed in_progress → completed
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "completed"})
j = rv.get_json()
print("[2] in_progress→completed ->", rv.status_code,
      "completed_at:", j.get("task",{}).get("completed_at"))
assert rv.status_code == 200
assert j["task"]["completed_at"] is not None

# 3. raed completed→in_progress (REOPEN) → 403
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "in_progress"})
print("[3] raed reopens ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 4. admin reopens → 200
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "in_progress"})
j = rv.get_json()
print("[4] admin reopens ->", rv.status_code,
      "completed_at after reopen (should be None):",
      j.get("task",{}).get("completed_at"))
assert rv.status_code == 200
assert j["task"]["completed_at"] is None

# 5. Admin reverts in_progress → new
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "new"})
j = rv.get_json()
print("[5] in_progress→new (revert) ->", rv.status_code,
      "started_at (should be None):", j.get("task",{}).get("started_at"))
assert rv.status_code == 200
assert j["task"]["started_at"] is None

# 6. Same status (already new) → 400
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "new"})
print("[6] same status ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 7. Invalid status string → 400
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "done"})
print("[7] invalid status ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 8. Not-allowed transition: new → completed (no skip) → 400
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "completed"})
print("[8] new→completed (skip) ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 9. Admin cancels → 200
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "cancelled"})
j = rv.get_json()
print("[9] new→cancelled ->", rv.status_code,
      "status:", j["task"]["status"])
assert rv.status_code == 200

# 10. raed tries uncancel → 403
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "new"})
print("[10] raed uncancels ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 11. cancelled → completed (not allowed) → 400 (admin tries)
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "completed"})
print("[11] cancelled→completed ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 12. admin uncancels → 200
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "new"})
print("[12] admin uncancels ->", rv.status_code)
assert rv.status_code == 200

# 13. Creator (non-assignee) can cancel
# Create new task assigned to teacher1, with admin as creator
rv = c.post("/api/tasks", json={
    "title": "C15 creator cancel test", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "teacher1",
    "due_date": "2026-06-01", "estimated_hours": 1
})
ctid = rv.get_json()["id"]
# raed is neither — should fail
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks/" + str(ctid) + "/status",
            json={"status": "cancelled"})
print("[13a] stranger cancels ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# Test that the creator (admin) cancels a task assigned to others
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks/" + str(ctid) + "/status",
            json={"status": "cancelled"})
print("[13b] creator/admin cancels ->", rv.status_code)
assert rv.status_code == 200

# 14. Bogus tid → 404
rv = c.post("/api/tasks/999999/status",
            json={"status": "in_progress"})
print("[14] bogus tid ->", rv.status_code)
assert rv.status_code == 404

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM tasks WHERE id IN(?,?)", (tid, ctid))
    db.commit()

print("\nC15 smoke passed.")
