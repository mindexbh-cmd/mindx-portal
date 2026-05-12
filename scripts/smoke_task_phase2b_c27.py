"""C27 smoke - notifications endpoints (3)."""
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
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("smoke_student", A.hp("s123"), "student", "طالب"))
    db.commit()
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

# Setup: admin creates task assigned to raed, then both comment
# → notifications fan to each side
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C27 notif task", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1
})
tid = rv.get_json()["id"]
c.post("/api/tasks/" + str(tid) + "/comments",
       json={"content": "admin comment 1"})
c.post("/api/tasks/" + str(tid) + "/comments",
       json={"content": "admin comment 2"})

c.get("/")
login("980909805", "raed123")
c.post("/api/tasks/" + str(tid) + "/comments",
       json={"content": "raed comment"})
print("[setup] tid=", tid)

# 1. raed unread-count → 2 (from admin's 2 comments)
rv = c.get("/api/notifications/unread-count")
j = rv.get_json()
print("[1] raed unread-count ->", rv.status_code, "count=", j.get("count"))
assert rv.status_code == 200
assert j["count"] == 2

# 2. raed GET list → 2 notifications with task_title joined
rv = c.get("/api/notifications")
j = rv.get_json()
print("[2] raed GET ->", rv.status_code, "count=", len(j.get("notifications") or []))
notifs = j["notifications"]
assert len(notifs) == 2
for n in notifs:
    assert n["recipient_username"] == "980909805"
    assert n["task_title"] == "C27 notif task"
    assert n["is_read"] == 0

# 3. Mark first as read
first_nid = notifs[0]["id"]
rv = c.post("/api/notifications/" + str(first_nid) + "/read")
print("[3] mark read ->", rv.status_code, rv.get_json())
assert rv.status_code == 200

# 4. Unread-count is now 1
rv = c.get("/api/notifications/unread-count")
print("[4] unread-count after read ->", rv.status_code,
      "count=", rv.get_json().get("count"))
assert rv.get_json()["count"] == 1

# 5. ?unread_only=1 returns only the still-unread
rv = c.get("/api/notifications?unread_only=1")
print("[5] unread_only ->", rv.status_code,
      "count=", len(rv.get_json()["notifications"]))
assert len(rv.get_json()["notifications"]) == 1

# 6. raed tries to mark admin's notification as read → 403
# admin has 1 notification (from raed's comment)
c.get("/")
login("admin", "admin123")
rv = c.get("/api/notifications")
admin_notifs = rv.get_json()["notifications"]
admin_n = next((n for n in admin_notifs if n["task_id"] == tid), None)
admin_nid = admin_n["id"] if admin_n else None
print("[setup-admin-notif] id=", admin_nid)
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/notifications/" + str(admin_nid) + "/read")
print("[6] raed marks admin's ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 7. Mark non-existent → 404
rv = c.post("/api/notifications/999999/read")
print("[7] bogus nid ->", rv.status_code)
assert rv.status_code == 404

# 8. student → 403 on all
c.get("/")
login("smoke_student", "s123")
rv = c.get("/api/notifications")
print("[8a] student GET ->", rv.status_code)
assert rv.status_code == 403
rv = c.get("/api/notifications/unread-count")
print("[8b] student count ->", rv.status_code)
assert rv.status_code == 403

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM task_comments WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC27 smoke passed.")
