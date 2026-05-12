"""C22 smoke - /assets route + grid."""
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

# 1. Unauth -> 302
rv = c.get("/assets")
print("[1] unauth ->", rv.status_code)
assert rv.status_code == 302

# 2. teacher1 -> 403
login("teacher1", "tea123")
rv = c.get("/assets")
print("[2] teacher1 ->", rv.status_code)
assert rv.status_code == 403

# 3. Admin -> 200, IS_ADMIN flag = true, total card structure present
c.get("/")
login("admin", "admin123")
rv = c.get("/assets")
body = rv.get_data(as_text=True)
print("[3] admin /assets len=", len(body))
checks = [
    ("admin flag injected", "AST_IS_ADMIN = true" in body),
    ("category chips", 'data-cat="electronics"' in body),
    ("condition chips", 'data-cond="needs_maintenance"' in body),
    ("show-disposed toggle", 'show-disposed' in body),
    ("asset-grid container", 'id="asset-grid"' in body),
    ("total card markup", 'id="total-card"' in body),
    ("add btn", 'asset-add-btn' in body),
    ("placeholder swapped", "IS_ADMIN_PLACEHOLDER" not in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 4. Raed -> 200, IS_ADMIN flag = false
c.get("/")
login("980909805", "raed123")
rv = c.get("/assets")
body_r = rv.get_data(as_text=True)
print("[4] raed /assets len=", len(body_r))
assert "AST_IS_ADMIN = false" in body_r
assert "IS_ADMIN_PLACEHOLDER" not in body_r
print("    - raed flag false ✓")

# 5. Seed an asset, verify grid endpoint matches
c.get("/")
login("admin", "admin123")
rv = c.post("/api/assets", json={"name_ar": "كرسي اختبار",
                                   "category": "furniture",
                                   "condition": "good",
                                   "purchase_price": 25,
                                   "location": "مكتب"})
aid = (rv.get_json() or {}).get("id")
print("[5] seed asset ->", rv.status_code, "id=", aid)

# 6. Verify GET /api/assets returns it for raed too (institute-wide)
c.get("/")
login("980909805", "raed123")
rv = c.get("/api/assets")
rows = (rv.get_json() or {}).get("rows", [])
print("[6] raed sees admin's asset?",
      any(r["id"] == aid for r in rows))
assert any(r["id"] == aid for r in rows)

# 7. Regression: legacy pages
c.get("/")
login("admin", "admin123")
for p in ["/parent", "/dashboard", "/expenses"]:
    rv = c.get(p)
    print("[7] " + p + " ->", rv.status_code)
    assert rv.status_code == 200

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM assets WHERE id=?", (aid,))
    db.commit()
print("\nAll C22 smoke checks passed.")
