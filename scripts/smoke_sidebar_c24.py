"""C24 smoke - sidebar nav links visible to admin + raed only."""
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

EXP_HREF  = 'href="/expenses"'
AST_HREF  = 'href="/assets"'
EXP_LINK_CLASS = 'mx-expenses-link'

# 1. Admin /dashboard contains both links + flag = "1"
login("admin", "admin123")
rv = c.get("/dashboard")
body = rv.get_data(as_text=True)
print("[1] admin /dashboard len=", len(body))
checks = [
    ("expenses link href", EXP_HREF in body),
    ("assets link href", AST_HREF in body),
    ("link class", EXP_LINK_CLASS in body),
    ("flag set to 1", 'allowExpenses = "1"' in body),
    ("placeholder swapped", 'EXPENSES_ACCESS_PLACEHOLDER' not in body),
    ("CSS rule present", 'data-allow-expenses="1"' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# 2. Raed /dashboard: links visible (flag=1)
c.get("/")
login("980909805", "raed123")
rv = c.get("/dashboard")
body_r = rv.get_data(as_text=True)
print("[2] raed /dashboard ->", rv.status_code, "len=", len(body_r))
assert rv.status_code == 200
print("    - expenses link present?", EXP_HREF in body_r)
print("    - assets link present?", AST_HREF in body_r)
print("    - allowExpenses flag value:",
      '"1"' if 'allowExpenses = "1"' in body_r else '"0"')
assert EXP_HREF in body_r
assert AST_HREF in body_r
assert 'allowExpenses = "1"' in body_r

# 3. teacher1: links technically in markup (CSS hides them), flag=0
c.get("/")
login("teacher1", "tea123")
rv = c.get("/dashboard")
# teacher1 redirects via /dashboard -> /teacher/hub
print("[3] teacher1 /dashboard ->", rv.status_code)
# That's a redirect — teachers don't see HOME_HTML at all, so the
# sidebar question is moot for them. Verify they get redirected.
assert rv.status_code == 302

# 4. manager-role user (mock by inserting one) — links should be hidden
with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("smoke_mgr", A.hp("mgr123"), "manager", "مدير اختبار"))
    db.commit()
c.get("/")
login("smoke_mgr", "mgr123")
rv = c.get("/dashboard")
body_m = rv.get_data(as_text=True)
print("[4] manager /dashboard ->", rv.status_code, "len=", len(body_m))
assert rv.status_code == 200
# Manager doesn't get expenses access (only admin + raed username)
assert 'allowExpenses = "0"' in body_m
print("    - manager has flag=0 ✓")
# Markup is still present (CSS hides), so the links should exist
# in source but won't render due to the body[data-allow-expenses]
# rule. Confirm they're in the HTML.
print("    - links in markup?", EXP_HREF in body_m and AST_HREF in body_m)
print("    - CSS rule present?", 'mx-expenses-link' in body_m)
print("    - body has data-allow-expenses=0?",
      'allowExpenses = "0"' in body_m)

# 5. Regression: existing nav items + routes still work
c.get("/")
login("admin", "admin123")
for p in ["/dashboard", "/parent", "/groups", "/attendance", "/database",
          "/expenses", "/assets"]:
    rv = c.get(p)
    print("[5] " + p + " ->", rv.status_code)
    assert rv.status_code == 200, p

# Cleanup mock manager
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM users WHERE username='smoke_mgr'")
    db.commit()

print("\nAll C24 smoke checks passed.")
