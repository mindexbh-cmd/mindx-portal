"""C21 smoke - POST /api/tasks/<id>/evaluate with points calc."""
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

# Setup: admin creates urgent task → raed completes it (on time)
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C21 evaluate test", "department_id": events_dept,
    "priority": "urgent",       # +10 bonus
    "assigned_to_username": "980909805",
    "due_date": "2026-12-31",   # far future → completed on-time
    "estimated_hours": 2
})
tid = rv.get_json()["id"]

c.get("/")
login("980909805", "raed123")
c.post("/api/tasks/" + str(tid) + "/status",
       json={"status": "in_progress"})
c.post("/api/tasks/" + str(tid) + "/status",
       json={"status": "completed"})

# 1. raed tries to evaluate → 403 (admin-only)
rv = c.post("/api/tasks/" + str(tid) + "/evaluate",
            json={"rating_stars": 5})
print("[1] raed evaluates ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 2. admin evaluates with 5 stars + speed/quality badges → points = 5*10 + 10 (urgent) + 10 (ontime) = 70
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks/" + str(tid) + "/evaluate",
            json={"rating_stars": 5,
                  "strength_badges": ["speed", "quality"],
                  "admin_comment": "عمل ممتاز"})
j = rv.get_json()
print("[2] admin evaluates ->", rv.status_code,
      "points:", j.get("points_awarded"),
      "badges:", j.get("evaluation", {}).get("strength_badges"))
assert rv.status_code == 200
assert j["points_awarded"] == 70
assert j["evaluation"]["strength_badges"] == ["speed", "quality"]

# 3. Verify employee_points row for raed
with A.app.app_context():
    db = A.get_db()
    pts_row = db.execute(
        "SELECT employee_username, points FROM employee_points "
        "WHERE task_id=?", (tid,)).fetchall()
    pts_rows = [dict(r) for r in pts_row]
print("[3] employee_points rows:", pts_rows)
assert len(pts_rows) == 1
assert pts_rows[0]["employee_username"] == "980909805"
assert pts_rows[0]["points"] == 70

# 4. Verify notification for raed
with A.app.app_context():
    db = A.get_db()
    nrows = db.execute(
        "SELECT recipient_username, notification_type, message "
        "FROM task_notifications WHERE task_id=? "
        "AND notification_type='completed'",
        (tid,)).fetchall()
    nrows = [dict(n) for n in nrows]
print("[4] eval notification:", nrows)
assert any(n["recipient_username"] == "980909805"
           and "5 نجوم" in n["message"] for n in nrows)

# 5. Re-evaluating → 400 (already evaluated)
rv = c.post("/api/tasks/" + str(tid) + "/evaluate",
            json={"rating_stars": 3})
print("[5] re-evaluate ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 6. Invalid stars (6) → 400
rv = c.post("/api/tasks/" + str(tid) + "/evaluate",
            json={"rating_stars": 6})
print("[6] stars=6 ->", rv.status_code)
assert rv.status_code == 400

# 7. Invalid stars (0) → 400 — needs fresh task
rv = c.post("/api/tasks", json={
    "title": "C21 fresh", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1
})
fresh_tid = rv.get_json()["id"]
with A.app.app_context():
    db = A.get_db()
    db.execute("UPDATE tasks SET status='completed', completed_at=CURRENT_TIMESTAMP WHERE id=?", (fresh_tid,))
    db.commit()
rv = c.post("/api/tasks/" + str(fresh_tid) + "/evaluate",
            json={"rating_stars": 0})
print("[7] stars=0 ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 8. Invalid badge → 400
rv = c.post("/api/tasks/" + str(fresh_tid) + "/evaluate",
            json={"rating_stars": 3,
                  "strength_badges": ["speed", "BOGUS_BADGE"]})
print("[8] bad badge ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 9. Non-completed task → 400
rv = c.post("/api/tasks", json={
    "title": "C21 not-done", "department_id": events_dept,
    "priority": "low", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1
})
nodone_tid = rv.get_json()["id"]
rv = c.post("/api/tasks/" + str(nodone_tid) + "/evaluate",
            json={"rating_stars": 4})
print("[9] non-completed eval ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for x in [tid, fresh_tid, nodone_tid]:
        db.execute("DELETE FROM task_notifications WHERE task_id=?", (x,))
        db.execute("DELETE FROM task_evaluations WHERE task_id=?", (x,))
        db.execute("DELETE FROM employee_points WHERE task_id=?", (x,))
        db.execute("DELETE FROM tasks WHERE id=?", (x,))
    db.commit()

print("\nC21 smoke passed.")
