"""C17 smoke - DELETE comment with strict ownership."""
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

login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C17 delete comment test", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1
})
tid = rv.get_json()["id"]

# Admin posts a comment
rv = c.post("/api/tasks/" + str(tid) + "/comments",
            json={"content": "admin comment"})
admin_cid = rv.get_json()["id"]

# Raed posts a comment
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks/" + str(tid) + "/comments",
            json={"content": "raed comment"})
raed_cid = rv.get_json()["id"]

print("[setup] tid=", tid, "admin_cid=", admin_cid, "raed_cid=", raed_cid)

# 1. Raed deletes raed's own → 200
rv = c.delete("/api/tasks/" + str(tid) + "/comments/" + str(raed_cid))
print("[1] raed deletes own ->", rv.status_code, rv.get_json())
assert rv.status_code == 200

# 2. Raed tries to delete admin's → 403
rv = c.delete("/api/tasks/" + str(tid) + "/comments/" + str(admin_cid))
print("[2] raed deletes admin's ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 3. Admin deletes any (admin's own) → 200
c.get("/")
login("admin", "admin123")
rv = c.delete("/api/tasks/" + str(tid) + "/comments/" + str(admin_cid))
print("[3] admin deletes ->", rv.status_code)
assert rv.status_code == 200

# 4. Delete non-existent comment → 404
rv = c.delete("/api/tasks/" + str(tid) + "/comments/999999")
print("[4] bogus cid ->", rv.status_code)
assert rv.status_code == 404

# 5. Verify both comments are gone
rv = c.get("/api/tasks/" + str(tid) + "/comments")
print("[5] remaining comments:", len(rv.get_json()["comments"]))
assert len(rv.get_json()["comments"]) == 0

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.commit()

print("\nC17 smoke passed.")
