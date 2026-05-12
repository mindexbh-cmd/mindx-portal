"""C22 smoke - GET + PATCH evaluation with delta audit trail."""
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

# Setup: complete + evaluate task with 4 stars (urgent + on-time → 60 pts)
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C22 amend test", "department_id": events_dept,
    "priority": "urgent", "assigned_to_username": "980909805",
    "due_date": "2026-12-31", "estimated_hours": 1
})
tid = rv.get_json()["id"]

c.get("/")
login("980909805", "raed123")
c.post("/api/tasks/" + str(tid) + "/status", json={"status": "in_progress"})
c.post("/api/tasks/" + str(tid) + "/status", json={"status": "completed"})

c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks/" + str(tid) + "/evaluate",
            json={"rating_stars": 4, "strength_badges": ["speed"]})
initial_pts = rv.get_json()["points_awarded"]
print("[setup] tid=", tid, "initial points (4 stars urgent ontime):", initial_pts)
assert initial_pts == 60  # 4*10 + 10 + 10

# 1. GET evaluation by admin → 200
rv = c.get("/api/tasks/" + str(tid) + "/evaluation")
j = rv.get_json()
print("[1] admin GET ->", rv.status_code, "stars:", j["evaluation"]["rating_stars"])
assert rv.status_code == 200
assert j["evaluation"]["strength_badges"] == ["speed"]

# 2. GET by raed (assignee) → 200
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/tasks/" + str(tid) + "/evaluation")
print("[2] raed GET ->", rv.status_code)
assert rv.status_code == 200

# 3. raed tries to PATCH → 403
rv = c.patch("/api/tasks/" + str(tid) + "/evaluation",
             json={"rating_stars": 5})
print("[3] raed PATCH ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 4. admin amends 4→5 → delta +10 (new total 70)
c.get("/")
login("admin", "admin123")
rv = c.patch("/api/tasks/" + str(tid) + "/evaluation",
             json={"rating_stars": 5})
j = rv.get_json()
print("[4] admin amends 4→5 ->", rv.status_code,
      "new_total_points:", j["new_total_points"],
      "delta:", j["delta"])
assert rv.status_code == 200
assert j["new_total_points"] == 70
assert j["delta"] == 10

# Verify employee_points has 2 rows: original 60 + delta 10
with A.app.app_context():
    db = A.get_db()
    rows = db.execute(
        "SELECT points, reason FROM employee_points "
        "WHERE task_id=? ORDER BY id ASC", (tid,)).fetchall()
    rs = [dict(r) for r in rows]
print("[5] audit trail:")
for r in rs: print("   ", r)
assert len(rs) == 2
assert rs[0]["points"] == 60
assert rs[1]["points"] == 10
assert "تعديل تقييم" in rs[1]["reason"]

# 6. Amend 5→3 → delta = (3*10 + 10 + 10) - 70 = 50 - 70 = -20
rv = c.patch("/api/tasks/" + str(tid) + "/evaluation",
             json={"rating_stars": 3})
j = rv.get_json()
print("[6] amend 5→3 ->", rv.status_code,
      "new_total_points:", j["new_total_points"],
      "delta:", j["delta"])
assert j["new_total_points"] == 50
assert j["delta"] == -20

with A.app.app_context():
    db = A.get_db()
    rows = db.execute(
        "SELECT points FROM employee_points "
        "WHERE task_id=? ORDER BY id ASC", (tid,)).fetchall()
    total = sum(dict(r)["points"] for r in rows)
print("[7] sum of employee_points (should be 50):", total)
assert total == 50

# 8. GET on non-evaluated task → 404
rv = c.post("/api/tasks", json={
    "title": "C22 unevaluated", "department_id": events_dept,
    "priority": "low", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1
})
ue_tid = rv.get_json()["id"]
rv = c.get("/api/tasks/" + str(ue_tid) + "/evaluation")
print("[8] unevaluated task ->", rv.status_code, rv.get_json())
assert rv.status_code == 404

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for x in [tid, ue_tid]:
        db.execute("DELETE FROM task_notifications WHERE task_id=?", (x,))
        db.execute("DELETE FROM task_evaluations WHERE task_id=?", (x,))
        db.execute("DELETE FROM employee_points WHERE task_id=?", (x,))
        db.execute("DELETE FROM tasks WHERE id=?", (x,))
    db.commit()

print("\nC22 smoke passed.")
