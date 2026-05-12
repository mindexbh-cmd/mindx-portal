"""C21 smoke - expense modal HTML + E2E POST flow."""
import os, sys, io, base64
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D49484452000000010000000108060000001F15C489"
    "0000000A49444154789C6300010000000500010D0A2DB400000000IEND".replace("IEND","49454E44") + "AE426082")
PNG_B64 = base64.b64encode(PNG).decode()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# 1. Admin /expenses includes modal markup
login("admin", "admin123")
rv = c.get("/expenses")
body = rv.get_data(as_text=True)
print("[1] admin /expenses len=", len(body))
checks = [
    ("modal markup", 'id="exp-modal"' in body),
    ("category pills", 'exp-cat-pills' in body),
    ("amount input", 'exp-amount' in body),
    ("file input", 'exp-file' in body),
    ("save btn", 'exp-save-btn' in body),
    ("lightbox", 'exp-lightbox' in body),
    ("store-link conditional", 'exp-store-link' in body),
    ("ensureCats fn", '_ensureCats' in body),
    ("admin flag true", 'EXP_IS_ADMIN = true' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 2. Raed /expenses includes modal but flagged non-admin
c.get("/")
login("980909805", "raed123")
rv = c.get("/expenses")
body_r = rv.get_data(as_text=True)
print("[2] raed /expenses len=", len(body_r))
assert 'id="exp-modal"' in body_r
assert 'EXP_IS_ADMIN = false' in body_r
# The raed-side JS still pulls all categories; the pill renderer filters
# "رواتب وأجور" out at render time. Verify that filter is present.
assert "رواتب وأجور" in body_r and "indexOf('رواتب وأجور')" in body_r
print("    - non-admin flag ✓")
print("    - salary-filter present in JS ✓")

# 3. E2E: admin POST a new expense via the modal's same body shape
c.get("/")
login("admin", "admin123")
rv = c.post("/api/expenses", json={
    "category_id": 1,
    "amount": 25.500,
    "description": "C21 modal smoke test",
    "vendor_name": "Test Vendor",
    "payment_method": "cash",
    "expense_date": "2026-05-12",
    "notes": "smoke",
    "receipt_b64": PNG_B64,
    "receipt_filename": "rcpt.png"
})
data = rv.get_json() or {}
print("[3] modal POST ->", rv.status_code, data)
assert rv.status_code == 200
eid = data["id"]

# 4. GET expense detail
rv = c.get("/api/expenses/" + str(eid))
row = (rv.get_json() or {}).get("row") or {}
print("[4] detail ->", rv.status_code, "amount=", row.get("amount"),
      "has_receipt=", row.get("has_receipt"))
assert row.get("has_receipt") is True

# 5. GET receipt streams PNG bytes back
rv = c.get("/api/expenses/" + str(eid) + "/receipt")
print("[5] receipt ->", rv.status_code, rv.headers.get("Content-Type"),
      "len=", len(rv.data))
assert rv.status_code == 200
assert "image/png" in rv.headers.get("Content-Type", "")

# 6. PATCH amount
rv = c.patch("/api/expenses/" + str(eid),
             json={"amount": 30.250})
print("[6] PATCH amount ->", rv.status_code, rv.get_json())
assert rv.status_code == 200

# 7. DELETE
rv = c.delete("/api/expenses/" + str(eid))
print("[7] DELETE ->", rv.status_code, rv.get_json())
assert rv.status_code == 200

print("\nAll C21 smoke checks passed.")
