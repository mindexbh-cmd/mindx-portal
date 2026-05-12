"""C18 smoke - BYTEA attachment upload + validation."""
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

# PDF magic + a tiny PDF body
PDF = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj<</Type/Catalog>>endobj\ntrailer<<>>"
PDF_B64 = base64.b64encode(PDF).decode()

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

login("admin", "admin123")
rv = c.post("/api/tasks", json={
    "title": "C18 attach test", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1
})
tid = rv.get_json()["id"]
print("[setup] tid=", tid)

attach_ids = []

# 1. admin uploads PNG → success, no file_bytes in response
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PNG_B64, "file_mime": "image/png",
                  "filename": "proof.png"})
j = rv.get_json()
print("[1] admin uploads PNG ->", rv.status_code, "attachment:", j.get("attachment"))
assert rv.status_code == 200
assert "file_bytes" not in j["attachment"]
assert j["attachment"]["file_mime"] == "image/png"
assert j["attachment"]["file_size"] == len(PNG)
attach_ids.append(j["id"])

# 2. raed uploads PDF → success
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PDF_B64,
                  "file_mime": "application/pdf",
                  "filename": "report.pdf"})
j = rv.get_json()
print("[2] raed uploads PDF ->", rv.status_code, "id=", j.get("id"))
assert rv.status_code == 200
attach_ids.append(j["id"])

# 3. student → 403
c.get("/")
login("smoke_student", "s123")
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PNG_B64, "file_mime": "image/png"})
print("[3] student ->", rv.status_code)
assert rv.status_code == 403

# 4. Stranger (teacher1) → 403
c.get("/")
login("teacher1", "tea123")
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PNG_B64, "file_mime": "image/png"})
print("[4] stranger ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 5. Bad MIME → 400
c.get("/")
login("admin", "admin123")
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PNG_B64,
                  "file_mime": "application/x-malware"})
print("[5] bad MIME ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 6. Magic byte mismatch (claim PDF, send PNG bytes) → 400
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PNG_B64,
                  "file_mime": "application/pdf"})
print("[6] magic mismatch ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 7. Oversized (6MB of zeros, base64 encoded) → 400
big = base64.b64encode(b"\x00" * (6 * 1024 * 1024)).decode()
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": big, "file_mime": "image/png"})
print("[7] oversized ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 8. Empty file → 400
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": "", "file_mime": "image/png"})
print("[8] empty ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 9. Bogus task id → 404
rv = c.post("/api/tasks/999999/attachments",
            json={"file_b64": PNG_B64, "file_mime": "image/png"})
print("[9] bogus tid ->", rv.status_code)
assert rv.status_code == 404

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM task_attachments WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC18 smoke passed.")
