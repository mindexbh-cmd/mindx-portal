"""C19 smoke - attachment download + metadata listing."""
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
    "title": "C19 download test", "department_id": events_dept,
    "priority": "normal", "assigned_to_username": "980909805",
    "due_date": "2026-06-01", "estimated_hours": 1
})
tid = rv.get_json()["id"]

# Upload PNG + PDF
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PNG_B64, "file_mime": "image/png",
                  "filename": "shot.png"})
png_aid = rv.get_json()["id"]
rv = c.post("/api/tasks/" + str(tid) + "/attachments",
            json={"file_b64": PDF_B64,
                  "file_mime": "application/pdf",
                  "filename": "report.pdf"})
pdf_aid = rv.get_json()["id"]
print("[setup] tid=", tid, "png_aid=", png_aid, "pdf_aid=", pdf_aid)

# 1. GET list — metadata only, no file_bytes
rv = c.get("/api/tasks/" + str(tid) + "/attachments")
j = rv.get_json()
print("[1] GET list ->", rv.status_code, "count=", len(j.get("attachments") or []))
assert rv.status_code == 200
assert len(j["attachments"]) == 2
for a in j["attachments"]:
    assert "file_bytes" not in a
    assert "file_size" in a

# 2. admin downloads PNG → 200 image/png
rv = c.get("/api/tasks/" + str(tid) + "/attachments/" + str(png_aid))
print("[2] admin PNG download ->", rv.status_code,
      "ct:", rv.headers.get("Content-Type"),
      "disp:", rv.headers.get("Content-Disposition"),
      "len:", len(rv.data))
assert rv.status_code == 200
assert "image/png" in rv.headers.get("Content-Type", "")
assert rv.headers.get("Content-Disposition", "").startswith("inline")
assert rv.data == PNG

# 3. admin downloads PDF → 200 application/pdf with attachment disposition
rv = c.get("/api/tasks/" + str(tid) + "/attachments/" + str(pdf_aid))
print("[3] admin PDF download ->", rv.status_code,
      "ct:", rv.headers.get("Content-Type"),
      "disp:", rv.headers.get("Content-Disposition"))
assert rv.status_code == 200
assert "application/pdf" in rv.headers.get("Content-Type", "")
assert rv.headers.get("Content-Disposition", "").startswith("attachment")

# 4. raed (assignee) can download
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/tasks/" + str(tid) + "/attachments/" + str(png_aid))
print("[4] raed download ->", rv.status_code)
assert rv.status_code == 200

# 5. student → 403
c.get("/")
login("smoke_student", "s123")
rv = c.get("/api/tasks/" + str(tid) + "/attachments/" + str(png_aid))
print("[5] student download ->", rv.status_code)
assert rv.status_code == 403

# 6. Stranger (teacher1) → 403
c.get("/")
login("teacher1", "tea123")
rv = c.get("/api/tasks/" + str(tid) + "/attachments/" + str(png_aid))
print("[6] stranger download ->", rv.status_code)
assert rv.status_code == 403

# 7. Bogus attachment id → 404
c.get("/")
login("admin", "admin123")
rv = c.get("/api/tasks/" + str(tid) + "/attachments/999999")
print("[7] bogus aid ->", rv.status_code)
assert rv.status_code == 404

# 8. Wrong task id (real attachment, wrong tid) → 404
rv = c.get("/api/tasks/" + str(tid + 999) + "/attachments/" + str(png_aid))
print("[8] wrong tid ->", rv.status_code)
assert rv.status_code == 404

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM task_notifications WHERE task_id=?", (tid,))
    db.execute("DELETE FROM task_attachments WHERE task_id=?", (tid,))
    db.execute("DELETE FROM tasks WHERE id=?", (tid,))
    db.execute("DELETE FROM users WHERE username=?", ("smoke_student",))
    db.commit()

print("\nC19 smoke passed.")
