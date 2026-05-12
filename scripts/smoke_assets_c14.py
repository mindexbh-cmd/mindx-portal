"""Phase 2 C14 smoke test - assets CRUD bundle."""
import os, sys, json, base64, hashlib, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

import app as A

# Tiny valid PNG (1x1 transparent)
PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000A49444154789C6300010000000500010D0A2DB40000000049454E44AE4260"
    "82")
PNG_B64 = base64.b64encode(PNG).decode()

c = A.app.test_client()

def login(username, password):
    rv = c.post("/login", data={"username": username, "password": password},
                follow_redirects=False)
    return rv.status_code

# 1. Unauth check
rv = c.get("/api/assets")
print("[1] unauth GET list ->", rv.status_code,
      "(login redirect expected: 302/401)")

# 2. Login as admin
sc = login("admin", "admin123")
print("[2] admin login ->", sc)

# 3. Admin POST create
body = {"name_ar": "حاسوب مكتب", "category": "electronics",
        "condition": "good", "purchase_price": 250, "vendor_name": "متجر س",
        "image_b64": PNG_B64}
rv = c.post("/api/assets", json=body)
data = rv.get_json() or {}
print("[3] admin POST ->", rv.status_code, data)
aid = data.get("id")
assert rv.status_code == 200 and aid, "POST failed"

# 4. GET list
rv = c.get("/api/assets")
data = rv.get_json() or {}
print("[4] admin GET list ->", rv.status_code,
      "rows=", len(data.get("rows", [])),
      "has_image?", any(r.get("has_image") for r in data.get("rows", [])))

# 5. GET detail
rv = c.get("/api/assets/" + str(aid))
data = rv.get_json() or {}
print("[5] admin GET detail ->", rv.status_code,
      "name=", (data.get("row") or {}).get("name_ar"),
      "image_url=", (data.get("row") or {}).get("image_url"))

# 6. GET image
rv = c.get("/api/assets/" + str(aid) + "/image")
print("[6] admin GET image ->", rv.status_code,
      "ct=", rv.headers.get("Content-Type"),
      "len=", len(rv.data))
assert rv.status_code == 200 and rv.data == PNG

# 7. PATCH update
rv = c.patch("/api/assets/" + str(aid),
             json={"condition": "needs_maintenance",
                   "maintenance_notes": "بحاجة لإصلاح"})
print("[7] admin PATCH ->", rv.status_code, rv.get_json())

rv = c.get("/api/assets/" + str(aid))
row = (rv.get_json() or {}).get("row") or {}
assert row.get("condition") == "needs_maintenance", row
print("[7a] PATCH applied -> condition=", row.get("condition"))

# 8. Logout, log in as random non-admin user (teacher1)
c.get("/")  # clears session
sc = login("teacher1", "tea123")
print("[8] teacher1 login ->", sc)

rv = c.get("/api/assets")
print("[8a] teacher1 GET list ->", rv.status_code, rv.get_json())

rv = c.post("/api/assets", json={"name_ar": "أداة"})
print("[8b] teacher1 POST ->", rv.status_code, rv.get_json())

# 9. Logout, log in as raed (980909805) - has access; needs to exist
c.get("/")
# Ensure raed exists
with A.app.app_context():
    db = A.get_db()
    row = db.execute("SELECT id FROM users WHERE username=?",
                     ("980909805",)).fetchone()
    if not row:
        db.execute("INSERT INTO users(username, password, role, name) "
                   "VALUES(?, ?, ?, ?)",
                   ("980909805", A.hp("raed123"), "manager", "رائد"))
        db.commit()
        print("[9-prep] inserted raed user")

sc = login("980909805", "raed123")
print("[9] raed login ->", sc)

# 9a. raed POST own asset
rv = c.post("/api/assets",
            json={"name_ar": "كرسي إداري", "category": "furniture",
                  "purchase_price": 35})
print("[9a] raed POST ->", rv.status_code, rv.get_json())
raed_aid = (rv.get_json() or {}).get("id")

# 9b. raed sees ALL assets (institute-wide)
rv = c.get("/api/assets")
rows = (rv.get_json() or {}).get("rows", [])
print("[9b] raed GET list ->", rv.status_code, "rows=", len(rows),
      "owners=", sorted({r.get("created_by_username") for r in rows}))
assert len(rows) >= 2, "raed should see admin's asset too"

# 9c. raed PATCHes own asset OK
rv = c.patch("/api/assets/" + str(raed_aid),
             json={"location": "غرفة الإدارة"})
print("[9c] raed PATCH own ->", rv.status_code, rv.get_json())

# 9d. raed PATCHes admin's asset -> 403
rv = c.patch("/api/assets/" + str(aid),
             json={"location": "محاولة تعديل"})
print("[9d] raed PATCH admin's ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 10. Bad image bytes
c.get("/")
login("admin", "admin123")
bad = base64.b64encode(b"NOT_AN_IMAGE_BYTES_AT_ALL_xx_xx").decode()
rv = c.post("/api/assets", json={"name_ar": "x", "image_b64": bad})
print("[10] bad magic ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 11. Empty name
rv = c.post("/api/assets", json={"name_ar": ""})
print("[11] empty name ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 12. Bogus id
rv = c.get("/api/assets/999999")
print("[12] bogus id ->", rv.status_code, rv.get_json())

# 13. Bogus image
rv = c.get("/api/assets/999999/image")
print("[13] bogus img ->", rv.status_code, rv.get_json())

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM assets WHERE name_ar IN(?,?)",
               ("حاسوب مكتب", "كرسي إداري"))
    db.commit()
print("\nAll smoke checks passed.")
