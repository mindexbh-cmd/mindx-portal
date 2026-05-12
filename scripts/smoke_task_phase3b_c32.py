"""C32 smoke - evaluate task modal."""
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

# Setup: completed task
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C32 eval test", "department_id": events_dept,
    "priority": "urgent", "assigned_to_username": "980909805",
    "due_date": "2026-12-31", "estimated_hours": 1
})
tid = rv.get_json()["id"]
c.get("/")
login("980909805", "raed123")
c.post("/api/tasks/" + str(tid) + "/status", json={"status": "in_progress"})
c.post("/api/tasks/" + str(tid) + "/status", json={"status": "completed"})

# 1. Admin detail page contains eval modal markup
c.get("/")
login("admin", "admin123")
rv = c.get("/tasks/" + str(tid))
body = rv.get_data(as_text=True)
print("[1] admin detail w/ eval modal len=", len(body))
checks = [
    ("eval modal markup", 'id="eval-modal"' in body),
    ("star picker", 'id="eval-stars"' in body),
    ("badge grid", 'id="eval-badges"' in body),
    ("comment input", 'id="eval-comment"' in body),
    ("points preview", 'id="eval-pts-total"' in body),
    ("save btn", 'id="eval-save-btn"' in body),
    ("openEvaluate fn", "window.taskOpenEvaluate" in body),
    ("admin-only guard", "if (typeof T_IS_ADMIN === 'undefined' || !T_IS_ADMIN) return" in body),
    ("eval modal CSS", '.strength-pill' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 2. Raed detail page — modal markup is present, but IIFE guard returns early
c.get("/")
login("980909805", "raed123")
rv = c.get("/tasks/" + str(tid))
body_r = rv.get_data(as_text=True)
print("[2] raed detail ->", rv.status_code, "len=", len(body_r))
assert rv.status_code == 200
# Markup is in the HTML; the IIFE guard prevents JS wire-up on raed's
# side. window.taskOpenEvaluate is not defined for non-admin.
assert 'id="eval-modal"' in body_r
assert "T_IS_ADMIN = false" in body_r

# 3. E2E: admin evaluates via the same body shape modal sends
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks/" + str(tid) + "/evaluate",
            json={"rating_stars": 4,
                  "strength_badges": ["speed", "quality"],
                  "admin_comment": "أداء ممتاز"})
j = rv.get_json()
print("[3] eval POST shape ->", rv.status_code,
      "points:", j.get("points_awarded"))
assert rv.status_code == 200
assert j["points_awarded"] == 60  # 4*10 + 10 urgent + 10 on-time

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM task_evaluations WHERE task_id=?", (tid,))
    db.execute("DELETE FROM employee_points WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.commit()

print("\nC32 smoke passed.")
