"""C23 smoke - asset modal + dispose sub-dialog + E2E."""
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

# 1. Admin /assets page has modal markup
login("admin", "admin123")
rv = c.get("/assets")
body = rv.get_data(as_text=True)
print("[1] admin /assets len=", len(body))
checks = [
    ("modal markup", 'id="ast-modal"' in body),
    ("category pills", 'ast-cat-pills' in body),
    ("condition pills", 'ast-cond-pills' in body),
    ("image upload", 'ast-file' in body),
    ("save btn", 'ast-save-btn' in body),
    ("dispose btn", 'ast-dispose-btn' in body),
    ("dispose dialog", 'ast-disp-dialog' in body),
    ("detail modal", 'ast-detail-modal' in body),
    ("linked expense select", 'ast-linked-expense' in body),
    ("useful life", 'ast-useful-life' in body),
    ("admin flag", 'AST_IS_ADMIN = true' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 2. Raed page has modal but admin flag false
c.get("/")
login("980909805", "raed123")
rv = c.get("/assets")
body_r = rv.get_data(as_text=True)
print("[2] raed /assets ->", rv.status_code, "len=", len(body_r))
assert 'id="ast-modal"' in body_r
assert 'AST_IS_ADMIN = false' in body_r
assert 'ast-dispose-btn' in body_r  # element present but JS hides for non-admin
print("    - raed flag false ✓")

# 3. E2E: POST asset with image, PATCH, fetch image
c.get("/")
login("admin", "admin123")
rv = c.post("/api/assets", json={
    "name_ar": "حاسوب C23 smoke",
    "category": "electronics",
    "condition": "good",
    "purchase_price": 250,
    "vendor_name": "Test",
    "purchase_date": "2026-01-15",
    "location": "مكتب",
    "image_b64": PNG_B64
})
data = rv.get_json() or {}
print("[3] POST asset ->", rv.status_code, data)
assert rv.status_code == 200
aid = data["id"]

# 3a. Detail
rv = c.get("/api/assets/" + str(aid))
row = (rv.get_json() or {}).get("row") or {}
print("[3a] detail name=", row.get("name_ar"), "has_image=", row.get("has_image"))
assert row.get("has_image") is True

# 3b. Image stream
rv = c.get("/api/assets/" + str(aid) + "/image")
print("[3b] image ->", rv.status_code, "len=", len(rv.data))
assert rv.status_code == 200

# 3c. PATCH condition
rv = c.patch("/api/assets/" + str(aid),
             json={"condition": "needs_maintenance"})
print("[3c] PATCH cond ->", rv.status_code, rv.get_json())
assert rv.status_code == 200

# 3d. Admin dispose
rv = c.post("/api/assets/" + str(aid) + "/dispose",
            json={"reason": "اختبار smoke"})
print("[3d] dispose ->", rv.status_code, rv.get_json())
assert rv.status_code == 200

# 3e. Disposed asset hidden from default ?active=1
rv = c.get("/api/assets")
rows = (rv.get_json() or {}).get("rows", [])
visible = any(r["id"] == aid for r in rows)
print("[3e] disposed in active list?", visible)
assert not visible

# 3f. Visible with ?active=0
rv = c.get("/api/assets?active=0")
rows = (rv.get_json() or {}).get("rows", [])
visible = any(r["id"] == aid for r in rows)
print("[3f] disposed in all list?", visible)
assert visible

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM assets WHERE id=?", (aid,))
    db.commit()
print("\nAll C23 smoke checks passed.")
