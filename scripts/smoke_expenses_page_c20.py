"""C20 smoke - /expenses route + role-aware template."""
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
rv = c.get("/expenses")
print("[1] unauth ->", rv.status_code)
assert rv.status_code == 302

# 2. teacher1 -> 403 polite page
login("teacher1", "tea123")
rv = c.get("/expenses")
body = rv.get_data(as_text=True)
print("[2] teacher1 ->", rv.status_code, "len=", len(body))
print("    has lock?", "&#x1F512;" in body)
print("    has admin-only text?", "&#x644;&#x644;&#x645;&#x62F;&#x64A;&#x631;" in body)
assert rv.status_code == 403
assert "&#x1F512;" in body

# 3. Admin -> 200 admin layout
c.get("/")
login("admin", "admin123")
rv = c.get("/expenses")
body = rv.get_data(as_text=True)
print("[3] admin ->", rv.status_code, "len=", len(body))
print("    has admin pill?", "EXP_IS_ADMIN = true" in body)
print("    has dashboard fetch?", "/api/expenses/dashboard" in body)
print("    has donut?", "exp-donut" in body)
print("    has filter bar?", "f-from" in body)
assert rv.status_code == 200
assert "EXP_IS_ADMIN = true" in body
assert "/api/expenses/dashboard" in body

# 4. raed -> 200 raed layout
c.get("/")
login("980909805", "raed123")
rv = c.get("/expenses")
body = rv.get_data(as_text=True)
print("[4] raed ->", rv.status_code, "len=", len(body))
print("    has raed pill?", "raed-pill" in body)
print("    has my-summary fetch?", "/api/expenses/my-summary" in body)
print("    has admin dashboard fetch?", "/api/expenses/dashboard" in body)
print("    is admin?", "EXP_IS_ADMIN = true" in body)
assert rv.status_code == 200
assert "/api/expenses/my-summary" in body
assert "/api/expenses/dashboard" not in body  # raed should NOT see admin dashboard
assert "EXP_IS_ADMIN = false" in body

# 5. Regression: legacy routes intact (re-login as admin first)
c.get("/")
login("admin", "admin123")
for path in ["/parent", "/dashboard", "/database", "/groups",
             "/attendance"]:
    rv = c.get(path)
    print("[5] " + path + " ->", rv.status_code)
    assert rv.status_code in (200, 302, 308), path

print("\nAll C20 smoke checks passed.")
