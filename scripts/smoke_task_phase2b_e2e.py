"""Phase 2b full E2E — recurring + task + attachment + comment +
lifecycle + evaluate + amend + dashboards + notifications."""
import os, sys, io, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE426082")
PNG_B64 = base64.b64encode(PNG).decode()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("e2e_student", A.hp("s123"), "student", "طالب"))
    db.commit()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

cleanup_tasks = []
cleanup_recurring = []

print("════════════ SCENARIO A: ADMIN BOOTSTRAP ════════════")
login("admin", "admin123")

# 1. Admin creates a daily recurring template assigned to raed
rv = c.post("/api/recurring-tasks", json={
    "template_title": "E2E daily backup check",
    "department_id": events_dept, "priority": "normal",
    "assigned_to_username": "980909805",
    "estimated_hours": 0.5, "frequency": "daily"
})
j = rv.get_json()
recurring_id = j["id"]
cleanup_recurring.append(recurring_id)
print("[A1] POST /api/recurring-tasks ->", rv.status_code,
      "id=", recurring_id, "title:",
      j["template"]["template_title"])
assert rv.status_code == 200

# 2. Admin manually creates a one-off task
rv = c.post("/api/tasks", json={
    "title": "E2E تجهيز قاعة الفعالية",
    "department_id": events_dept, "priority": "urgent",
    "assigned_to_username": "980909805",
    "due_date": "2026-12-31", "estimated_hours": 2.5,
    "tags": ["فعالية", "تجهيز"]
})
j = rv.get_json()
tid = j["id"]
cleanup_tasks.append(tid)
print("[A2] POST /api/tasks ->", rv.status_code, "id=", tid)
assert rv.status_code == 200

# 3. Admin uploads PNG attachment
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PNG_B64, "file_mime": "image/png",
                  "filename": "venue.png"})
j = rv.get_json()
attach_id = j["id"]
print("[A3] POST attachment ->", rv.status_code, "aid=", attach_id,
      "size=", j["attachment"]["file_size"])
assert rv.status_code == 200

print()
print("════════════ SCENARIO B: RAED INTERACTS ════════════")
c.get("/")
login("980909805", "raed123")

# 4. Raed sees a notification (from admin's attachment upload)
rv = c.get("/api/notifications/unread-count")
unread_before = rv.get_json()["count"]
print("[B4] raed unread-count before comment:", unread_before)

# 5. Raed comments
rv = c.post("/api/tasks/" + str(tid) + "/comments",
            json={"content": "تم البدء بالتجهيزات"})
j = rv.get_json()
comment_id = j["id"]
print("[B5] POST comment ->", rv.status_code, "cid=", comment_id)
assert rv.status_code == 200

# 6. Raed transitions new → in_progress → completed
rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "in_progress"})
print("[B6a] new→in_progress ->", rv.status_code,
      "started_at:", rv.get_json()["task"]["started_at"])
assert rv.status_code == 200

rv = c.post("/api/tasks/" + str(tid) + "/status",
            json={"status": "completed"})
print("[B6b] in_progress→completed ->", rv.status_code,
      "completed_at:", rv.get_json()["task"]["completed_at"])
assert rv.status_code == 200

print()
print("════════════ SCENARIO C: ADMIN EVALUATES ════════════")
c.get("/")
login("admin", "admin123")

# 7. Admin evaluates: 5 stars + 2 badges
rv = c.post("/api/tasks/" + str(tid) + "/evaluate",
            json={"rating_stars": 5,
                  "strength_badges": ["speed", "quality"],
                  "admin_comment": "تنفيذ ممتاز"})
j = rv.get_json()
print("[C7] evaluate ->", rv.status_code,
      "points:", j["points_awarded"])
# 5 stars * 10 + urgent 10 + on-time 10 = 70
assert rv.status_code == 200
assert j["points_awarded"] == 70

# 8. Verify employee_points correct
with A.app.app_context():
    db = A.get_db()
    pts = db.execute(
        "SELECT employee_username, points FROM employee_points "
        "WHERE task_id=?", (tid,)).fetchall()
    pts_rows = [dict(p) for p in pts]
print("[C8] employee_points:", pts_rows)
assert len(pts_rows) == 1
assert pts_rows[0]["points"] == 70
assert pts_rows[0]["employee_username"] == "980909805"

# 9. Admin amends to 4 stars → delta -10
rv = c.patch("/api/tasks/" + str(tid) + "/evaluation",
             json={"rating_stars": 4})
j = rv.get_json()
print("[C9] amend 5→4 ->", rv.status_code,
      "delta:", j["delta"],
      "new_total:", j["new_total_points"])
assert j["delta"] == -10
assert j["new_total_points"] == 60

# Verify audit trail has 2 rows now
with A.app.app_context():
    db = A.get_db()
    pts = db.execute(
        "SELECT points FROM employee_points WHERE task_id=? ORDER BY id",
        (tid,)).fetchall()
    points_list = [dict(p)["points"] for p in pts]
print("[C9a] audit points trail:", points_list)
assert points_list == [70, -10]
assert sum(points_list) == 60

print()
print("════════════ SCENARIO D: NOTIFICATIONS ════════════")
# Raed should have 2 notifications:
#   - attachment upload (admin uploaded → raed notified)
#   - evaluation (admin evaluated → raed notified)
# Admin should have 1:
#   - comment (raed commented → admin notified)
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/notifications")
raed_notifs = rv.get_json()["notifications"]
print("[D] raed notifications:")
for n in raed_notifs:
    print("    -", n["notification_type"], "/", n["message"])
assert any(n["notification_type"] == "completed"
           and "5 نجوم" in n["message"] for n in raed_notifs)
assert any("مرفق جديد" in n["message"] for n in raed_notifs)

c.get("/")
login("admin", "admin123")
rv = c.get("/api/notifications")
admin_notifs = rv.get_json()["notifications"]
print("[D] admin notifications:")
for n in admin_notifs:
    if n["task_id"] == tid:
        print("    -", n["notification_type"], "/", n["message"])
admin_comment_notif = [n for n in admin_notifs
                        if n["task_id"] == tid
                        and "تعليق" in n["message"]]
assert admin_comment_notif

print()
print("════════════ SCENARIO E: DASHBOARDS ════════════")

# Admin dashboard
rv = c.get("/api/tasks/dashboard/admin")
j = rv.get_json()
print("[E-admin] overview:", j["overview"])
raed_emp = next((e for e in j["by_employee"]
                 if e["username"] == "980909805"), None)
print("[E-admin] raed entry: completed=", raed_emp["completed"],
      "avg_rating=", raed_emp["avg_rating"],
      "total_points=", raed_emp["total_points"],
      "on_time_rate=", raed_emp["on_time_rate"])
assert raed_emp["avg_rating"] == 4.0   # after amendment
assert raed_emp["total_points"] >= 60

# Personal dashboard for raed
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/tasks/dashboard/personal")
j = rv.get_json()
print("[E-raed] points total:", j["my_points"]["total"],
      "completed count:", j["summary"]["by_status"]["completed"])
assert j["my_points"]["total"] >= 60

# Team dashboard (everyone)
rv = c.get("/api/tasks/dashboard/team")
j = rv.get_json()
print("[E-team] team_total:", j["team_total_tasks"],
      "top:", j["top_performers"])
assert j["team_total_tasks"] >= 1

print()
print("════════════ SCENARIO F: REGRESSION ════════════")
c.get("/")
login("admin", "admin123")
for p in ["/parent","/points/manage","/dashboard","/expenses","/assets",
          "/database","/groups","/attendance",
          "/api/departments","/api/tasks"]:
    rv = c.get(p)
    print("[F]", p, "->", rv.status_code)
    assert rv.status_code == 200

# Phase 2a endpoints still respond
rv = c.get("/api/tasks/" + str(tid))
print("[F-2a] GET /api/tasks/<id> ->", rv.status_code)
assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    for x in cleanup_tasks:
        db.execute("DELETE FROM task_notifications WHERE task_id=?", (x,))
        db.execute("DELETE FROM task_evaluations WHERE task_id=?", (x,))
        db.execute("DELETE FROM employee_points WHERE task_id=?", (x,))
        db.execute("DELETE FROM task_comments WHERE task_id=?", (x,))
        db.execute("DELETE FROM task_attachments WHERE task_id=?", (x,))
        db.execute("DELETE FROM tasks WHERE id=?", (x,))
    for x in cleanup_recurring:
        db.execute("DELETE FROM recurring_tasks WHERE id=?", (x,))
    db.execute("DELETE FROM users WHERE username=?", ("e2e_student",))
    db.commit()

print("\nALL Phase 2b E2E SCENARIOS PASSED.")
