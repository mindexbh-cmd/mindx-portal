"""C20 smoke - DELETE attachment with ownership check."""
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
    events_dept = dict(db.execute(
        "SELECT id FROM departments WHERE name_ar=?",
        ("قسم الفعاليات",)).fetchone())["id"]

login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C20 delete attach", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1
})
tid = rv.get_json()["id"]

# Admin uploads
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PNG_B64, "file_mime": "image/png",
                  "filename": "admin.png"})
admin_aid = rv.get_json()["id"]

# Raed uploads
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PNG_B64, "file_mime": "image/png",
                  "filename": "raed.png"})
raed_aid = rv.get_json()["id"]
print("[setup] tid=", tid, "admin_aid=", admin_aid, "raed_aid=", raed_aid)

# 1. Raed deletes own → 200
rv = c.delete("/api/tasks/" + str(tid) + "/attachments/" + str(raed_aid))
print("[1] raed deletes own ->", rv.status_code, rv.get_json())
assert rv.status_code == 200

# 2. Raed tries to delete admin's → 403
rv = c.delete("/api/tasks/" + str(tid) + "/attachments/" + str(admin_aid))
print("[2] raed deletes admin's ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 3. Admin deletes any → 200
c.get("/")
login("admin", "admin123")
rv = c.delete("/api/tasks/" + str(tid) + "/attachments/" + str(admin_aid))
print("[3] admin deletes ->", rv.status_code)
assert rv.status_code == 200

# 4. Non-existent → 404
rv = c.delete("/api/tasks/" + str(tid) + "/attachments/999999")
print("[4] bogus aid ->", rv.status_code)
assert rv.status_code == 404

# 5. Verify both gone
rv = c.get("/api/tasks/" + str(tid) + "/attachments")
print("[5] remaining:", len(rv.get_json()["attachments"]))
assert len(rv.get_json()["attachments"]) == 0

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.commit()

print("\nC20 smoke passed.")
