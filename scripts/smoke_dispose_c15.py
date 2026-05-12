"""Phase 2 C15 smoke - POST /api/assets/<id>/dispose."""
import os, sys, io, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()

def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# Admin creates an asset to dispose
login("admin", "admin123")
rv = c.post("/api/assets", json={"name_ar": "كرسي قديم",
                                  "category": "furniture"})
aid = (rv.get_json() or {}).get("id")
print("[setup] admin POST ->", rv.status_code, "id=", aid)

# 1. No reason → 400
rv = c.post("/api/assets/" + str(aid) + "/dispose", json={})
print("[1] no reason ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# 2. Bogus id → 404
rv = c.post("/api/assets/99999/dispose", json={"reason": "x"})
print("[2] bogus id ->", rv.status_code, rv.get_json())
assert rv.status_code == 404

# 3. raed (non-admin) cannot dispose
c.get("/")
login("980909805", "raed123")
rv = c.post("/api/assets/" + str(aid) + "/dispose",
            json={"reason": "محاولة"})
print("[3] raed dispose ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 4. teacher1 (no expense access at all) → 403
c.get("/")
login("teacher1", "tea123")
rv = c.post("/api/assets/" + str(aid) + "/dispose",
            json={"reason": "محاولة"})
print("[4] teacher1 dispose ->", rv.status_code, rv.get_json())
assert rv.status_code == 403

# 5. Admin dispose OK
c.get("/")
login("admin", "admin123")
rv = c.post("/api/assets/" + str(aid) + "/dispose",
            json={"reason": "تم البيع للموظف"})
print("[5] admin dispose ->", rv.status_code, rv.get_json())
assert rv.status_code == 200

# 5a. Detail shows is_disposed=1 + reason
rv = c.get("/api/assets/" + str(aid))
row = (rv.get_json() or {}).get("row") or {}
print("[5a] disposed=", row.get("is_disposed"),
      "at=", row.get("disposed_at"),
      "reason=", row.get("disposal_reason"))
assert int(row.get("is_disposed") or 0) == 1

# 5b. Default list (?active=1) hides it
rv = c.get("/api/assets")
rows = (rv.get_json() or {}).get("rows", [])
disposed_visible = any(r["id"] == aid for r in rows)
print("[5b] in active list?", disposed_visible)
assert not disposed_visible

# 5c. Explicit ?active=0 shows it
rv = c.get("/api/assets?active=0")
rows = (rv.get_json() or {}).get("rows", [])
visible = any(r["id"] == aid for r in rows)
print("[5c] in all-list?", visible)
assert visible

# 6. Double-dispose blocked
rv = c.post("/api/assets/" + str(aid) + "/dispose",
            json={"reason": "مرة أخرى"})
print("[6] double dispose ->", rv.status_code, rv.get_json())
assert rv.status_code == 400

# Cleanup
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM assets WHERE id=?", (aid,))
    db.commit()

print("\nAll C15 smoke checks passed.")
