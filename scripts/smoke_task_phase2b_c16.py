"""C16 smoke - comments POST + GET + notification fan-out."""
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

# Admin creates task assigned to raed (admin=creator, raed=assignee)
login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C16 comment test", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 2
})
tid = rv.get_json()["id"]
print("[setup] tid=", tid)

# 1. admin posts comment → notification fan to raed
rv = c.post("/api/tasks/" + str(tid) + "/comments",
            json={"content": "تعليق من المدير"})
j = rv.get_json()
print("[1] admin comment ->", rv.status_code, "id=", j.get("id"))
assert rv.status_code == 200
admin_comment_id = j["id"]

# Verify notification created for raed (not for admin)
with A.app.app_context():
    db = A.get_db()
    notifs = db.execute(
        "SELECT recipient_username, notification_type "
        "FROM task_notifications WHERE task_id=?", (tid,)).fetchall()
    nrows = [dict(n) for n in notifs]
print("[1a] notifications after admin comment:", nrows)
assert any(n["recipient_username"] == "980909805"
           and n["notification_type"] == "comment" for n in nrows)
# No notification for admin (the commenter)
assert not any(n["recipient_username"] == "admin" for n in nrows)

# 2. raed posts comment → notification fan to admin
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks/" + str(tid) + "/comments",
            json={"content": "تعليق من رائد"})
j = rv.get_json()
print("[2] raed comment ->", rv.status_code, "id=", j.get("id"))
assert rv.status_code == 200

# Verify admin got a notification
with A.app.app_context():
    db = A.get_db()
    notifs = db.execute(
        "SELECT recipient_username, notification_type "
        "FROM task_notifications WHERE task_id=?", (tid,)).fetchall()
    nrows = [dict(n) for n in notifs]
print("[2a] notifications after raed comment:")
for n in nrows: print("    ", n)
assert any(n["recipient_username"] == "admin" for n in nrows)

# 3. GET comments returns 2 in ASC order
rv = c.get("/api/tasks/" + str(tid) + "/comments")
j = rv.get_json()
print("[3] GET comments ->", rv.status_code, "count=", len(j.get("comments") or []))
comms = j["comments"]
assert len(comms) == 2
assert comms[0]["author_username"] == "admin"  # admin commented first
assert comms[1]["author_username"] == "980909805"

# 4. student → 403
c.get("/")
login("smoke_student", "s123")
rv = c.post("/api/tasks/" + str(tid) + "/comments",
            json={"content": "محاولة"})
print("[4] student POST ->", rv.status_code)
assert rv.status_code == 403
rv = c.get("/api/tasks/" + str(tid) + "/comments")
print("[5] student GET ->", rv.status_code)
assert rv.status_code == 403

# 6. Stranger (teacher1, neither creator nor assignee) → 403
c.get("/")
login("teacher1", "tea123")
rv = c.post("/api/tasks/" + str(tid) + "/comments",
            json={"content": "نزول من الجيران"})
print("[6] stranger POST ->", rv.status_code)
assert rv.status_code == 403

# 7. Empty content → 400
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks/" + str(tid) + "/comments", json={"content": "   "})
print("[7] empty ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 8. Over 2000 chars → 400
rv = c.post("/api/tasks/" + str(tid) + "/comments",
            json={"content": "x"*2001})
print("[8] >2000 chars ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 9. Bogus task id → 404
rv = c.post("/api/tasks/999999/comments", json={"content": "x"})
print("[9] bogus tid ->", rv.status_code)
assert rv.status_code == 404

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM task_comments WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC16 smoke passed.")
