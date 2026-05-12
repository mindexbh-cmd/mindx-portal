"""C27 smoke - store-link UI markup + JS wiring verification."""
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

# Admin /expenses page has the store-link form markup
login("admin", "admin123")
rv = c.get("/expenses")
body = rv.get_data(as_text=True)
print("[1] admin /expenses len=", len(body))
checks = [
    ("store-link toggle markup", 'id="store-link-toggle"' in body),
    ("store-link form", 'id="store-link-form"' in body),
    ("reward select", 'id="store-link-reward"' in body),
    ("qty input", 'id="store-link-qty"' in body),
    ("preview container", 'id="store-link-previews"' in body),
    ("fetch /api/points/rewards", '/api/points/rewards' in body),
    ("preview pill CSS", '.preview-pill' in body),
    ("sl toggle CSS", '.sl-toggle' in body),
    ("body uses store_link in POST", 'body.store_link' in body),
    ("eligibility prefix check", "indexOf('مشتريات للمتجر')" in body),
    ("reward ensure fn", '_slEnsureRewards' in body),
    ("preview update fn", '_slUpdatePreviews' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# Raed page should ALSO have the store-link UI (raed can use it)
c.get("/")
login("980909805", "raed123")
rv = c.get("/expenses")
body_r = rv.get_data(as_text=True)
print("[2] raed /expenses len=", len(body_r))
assert 'id="store-link-toggle"' in body_r
assert '/api/points/rewards' in body_r
print("    - store-link UI present for raed ✓")

# Verify /api/points/rewards exists and admin auth gets it
c.get("/")
login("admin", "admin123")
rv = c.get("/api/points/rewards")
print("[3] /api/points/rewards ->", rv.status_code)
assert rv.status_code == 200
j = rv.get_json() or {}
rewards = j.get("rewards") or j.get("rows") or []
print("    - rewards count:", len(rewards))

print("\nAll C27 smoke checks passed.")
