"""C1 smoke - GET /api/users/assignable endpoint."""
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

# ── Test 1: admin GET → 200, returns list ──
login("admin", "admin123")
rv = c.get("/api/users/assignable")
print("[1] admin GET ->", rv.status_code)
assert rv.status_code == 200
j = rv.get_json()
assert j.get("ok") is True
users = j.get("users") or []
total = j.get("total") or 0
assert isinstance(users, list)
assert total == len(users)
assert total >= 1, f"expected at least 1 assignable user, got {total}"
print(f"[1a] total assignable users: {total}")

# Verify shape on every row
required_keys = {"username", "display_name", "role"}
for u in users:
    assert required_keys.issubset(set(u.keys())), (
        f"row missing keys: {required_keys - set(u.keys())}")
    assert u["username"], "blank username"
    assert u["display_name"], "blank display_name (should fallback to username)"
print("[1b] all rows have username + display_name + role")

# Verify admin is present (we know admin has the flag from init_db)
admin_row = [u for u in users if u["username"] == "admin"]
assert len(admin_row) == 1, "admin row missing from list"
print(f"[1c] admin row present: display_name={admin_row[0]['display_name']!r}")

# ── Test 2: teacher GET → 200 (same data, role doesn't matter for read) ──
login("teacher1", "tea123")
rv = c.get("/api/users/assignable")
print("[2] teacher1 GET ->", rv.status_code)
assert rv.status_code == 200
j2 = rv.get_json()
assert j2.get("ok") is True
# Should see the same rows
assert j2.get("total") == total

# ── Test 3: sort order is alphabetical ASC by display_name ──
display_names = [u["display_name"] for u in users]
# casefold + lowercase for NOCASE-equivalent comparison
sorted_names = sorted(display_names, key=lambda s: s.casefold())
assert display_names == sorted_names, (
    f"order not alphabetical: got {display_names[:5]}, "
    f"expected {sorted_names[:5]}")
print(f"[3] sort order verified (first 3: {display_names[:3]})")

# ── Test 4: deactivated user (can_be_assigned_tasks=0) excluded ──
login("admin", "admin123")
test_username = "smoke_c1_test_user"
with A.app.app_context():
    db = A.get_db()
    # Cleanup any leftover row from a prior run
    db.execute("DELETE FROM users WHERE username=?", (test_username,))
    db.execute(
        "INSERT INTO users(username, password, role, name, "
        "can_be_assigned_tasks) VALUES(?,?,?,?,0)",
        (test_username, "x", "admin", "Test User", ))
    db.commit()
try:
    rv = c.get("/api/users/assignable")
    j3 = rv.get_json()
    excluded = all(u["username"] != test_username for u in j3.get("users", []))
    print(f"[4] user with can_be_assigned_tasks=0 excluded? {excluded}")
    assert excluded

    # Flip flag → should appear
    with A.app.app_context():
        db = A.get_db()
        db.execute("UPDATE users SET can_be_assigned_tasks=1 WHERE username=?",
                   (test_username,))
        db.commit()
    rv = c.get("/api/users/assignable")
    j4 = rv.get_json()
    included = any(u["username"] == test_username for u in j4.get("users", []))
    print(f"[4a] same user with can_be_assigned_tasks=1 included? {included}")
    assert included
finally:
    # Cleanup
    with A.app.app_context():
        db = A.get_db()
        db.execute("DELETE FROM users WHERE username=?", (test_username,))
        db.commit()

# ── Test 5: 8-route regression ──
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[5] {p} -> {rv.status_code}")
    assert rv.status_code == 200

print("\nC1 smoke passed.")
