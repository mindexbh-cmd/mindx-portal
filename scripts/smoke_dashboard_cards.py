"""Smoke - 2 new dashboard cards visible to admin + raed, hidden to others."""
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

# Markers we expect in the HOME_HTML response
HREF_EXP = 'href="/expenses"'
HREF_AST = 'href="/assets"'
CLASS_EXP = 'mx-expenses-link'
ALLOW_1 = 'allowExpenses = "1"'
ALLOW_0 = 'allowExpenses = "0"'

# Admin
login("admin", "admin123")
rv = c.get("/dashboard")
body = rv.get_data(as_text=True)
print("[1] admin /dashboard ->", rv.status_code, "len=", len(body))
# Count anchors with each href — should be 2 each (sidebar + new card)
exp_count = body.count(HREF_EXP)
ast_count = body.count(HREF_AST)
expclass_count = body.count(CLASS_EXP)
print("    href=/expenses count:", exp_count)
print("    href=/assets count:  ", ast_count)
print("    mx-expenses-link count:", expclass_count)
print("    allowExpenses flag = 1?", ALLOW_1 in body)
assert rv.status_code == 200
# Sidebar already had 1 of each (+1 CSS rule for mx-expenses-link).
# New cards add 1 more of each href + 2 more class occurrences.
# So expected: hrefs=2, mx-expenses-link >= 4 (2 sidebar + 2 new + 1 CSS rule)
assert exp_count == 2, "admin should see expenses link twice (sidebar + card)"
assert ast_count == 2, "admin should see assets link twice (sidebar + card)"
assert ALLOW_1 in body

# Raed
c.get("/")
login("980909805", "raed123")
rv = c.get("/dashboard")
body_r = rv.get_data(as_text=True)
print("[2] raed /dashboard ->", rv.status_code, "len=", len(body_r))
print("    href=/expenses count:", body_r.count(HREF_EXP))
print("    href=/assets count:  ", body_r.count(HREF_AST))
print("    allowExpenses=1?", ALLOW_1 in body_r)
assert rv.status_code == 200
assert body_r.count(HREF_EXP) == 2
assert body_r.count(HREF_AST) == 2
assert ALLOW_1 in body_r  # raed has expenses access

# Reception (mock - if not in allowlist, allowExpenses="0")
with A.app.app_context():
    db = A.get_db()
    db.execute("INSERT OR IGNORE INTO users(username, password, role, name) "
               "VALUES(?, ?, ?, ?)",
               ("smoke_recep", A.hp("rec123"), "reception", "استقبال"))
    db.commit()
c.get("/")
login("smoke_recep", "rec123")
rv = c.get("/dashboard")
body_rec = rv.get_data(as_text=True)
print("[3] reception /dashboard ->", rv.status_code, "len=", len(body_rec))
print("    allowExpenses=0?", ALLOW_0 in body_rec)
print("    markup still present (CSS hides)?",
      body_rec.count(HREF_EXP) == 2 and body_rec.count(HREF_AST) == 2)
assert rv.status_code == 200
assert ALLOW_0 in body_rec
# Markup is in the HTML (CSS rule hides it) — defense in depth means
# the cards aren't physically removed, just visually hidden.
assert body_rec.count(HREF_EXP) == 2
assert body_rec.count(HREF_AST) == 2

# Teacher1 → /dashboard redirects to /teacher/hub
c.get("/")
login("teacher1", "tea123")
rv = c.get("/dashboard")
print("[4] teacher1 /dashboard ->", rv.status_code)
assert rv.status_code == 302  # redirect, not in HOME_HTML at all

# Regression: existing cards still present (count them)
c.get("/")
login("admin", "admin123")
rv = c.get("/dashboard")
body = rv.get_data(as_text=True)
# Count dh-action-card occurrences (was 18, should now be 20 with the 2 new cards)
nbr = body.count('class="dh-action-card')
print("[5] dh-action-card total count:", nbr, "(expected: 20 = 18 existing + 2 new)")
assert nbr == 20

# Verify specific neighbors still present
checks_existing = [
    ("books card", 'href="/admin/books"' in body),
    ("receipts card", 'href="/admin/receipts"' in body),
    ("permissions card", 'href="/admin/permissions"' in body),
    ("database card", 'href="/database"' in body),
    ("attendance card", 'href="/attendance"' in body),
    ("teacher-deliveries card", 'href="/admin/teacher-deliveries"' in body),
]
print("[6] existing-card spot checks:")
for label, ok in checks_existing:
    print("    -", label, "->", ok)
    assert ok, label

# Cleanup mock reception user
with A.app.app_context():
    db = A.get_db()
    db.execute("DELETE FROM users WHERE username='smoke_recep'")
    db.commit()

print("\nAll dashboard-card smoke checks passed.")
