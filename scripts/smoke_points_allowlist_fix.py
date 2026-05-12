"""Smoke - POINTS_MANAGER_USERNAMES now uses numeric login IDs."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# ── Test 1: set contents match production reality ──
expected = {"010307885", "980909805"}
got = A.POINTS_MANAGER_USERNAMES
print(f"[1] POINTS_MANAGER_USERNAMES = {sorted(got)}")
assert got == expected, f"expected {expected}, got {got}"
# Legacy literal strings are gone
assert "raed" not in got
assert "ahmed_ibrahim" not in got
print("[1a] legacy literal strings 'raed'/'ahmed_ibrahim' no longer in set")

# ── Test 2: helper grants access to the two numeric IDs ──
# Note: _can_manage_points reads role from the user dict; manager users
# are NOT admin by role, so they only pass via the allowlist.
r = A._can_manage_points({"username": "010307885", "role": "manager"})
print(f"[2a] _can_manage_points(010307885, manager) -> {r}")
assert r is True

r = A._can_manage_points({"username": "980909805", "role": "manager"})
print(f"[2b] _can_manage_points(980909805, manager) -> {r}")
assert r is True

# ── Test 3: legacy literal usernames no longer grant access ──
r = A._can_manage_points({"username": "raed", "role": "manager"})
print(f"[3a] _can_manage_points(raed, manager) -> {r} (should False)")
assert r is False
r = A._can_manage_points({"username": "ahmed_ibrahim", "role": "manager"})
print(f"[3b] _can_manage_points(ahmed_ibrahim, manager) -> {r} (False)")
assert r is False

# ── Test 4: admin role passes regardless of allowlist ──
# ahmed_younis on prod is username '021005931' with role='admin', so
# his role short-circuits to True. This is the audit's main finding.
r = A._can_manage_points({"username": "021005931", "role": "admin"})
print(f"[4] _can_manage_points(021005931, admin) -> {r} (admin role)")
assert r is True

# Hypothetical literal 'admin' username with role='admin'
r = A._can_manage_points({"username": "admin", "role": "admin"})
print(f"[4a] _can_manage_points(admin, admin) -> {r}")
assert r is True

# ── Test 5: teachers + students + random non-allowlist users blocked ──
for u in [
    {"username": "040507718", "role": "teacher"},  # زهراء
    {"username": "960302557", "role": "teacher"},  # كوثر
    {"username": "teacher1",  "role": "teacher"},
    {"username": "reception", "role": "reception"},
    {"username": "anyone",    "role": "student"},
]:
    r = A._can_manage_points(u)
    print(f"[5] _can_manage_points({u['username']}, {u['role']}) -> {r}")
    assert r is False

# ── Test 6: _pts_user_role spoofing still works for the new IDs ──
# The C1 commit modified _pts_user_role to return "admin" for allowlist
# usernames. After today's fix, that spoofing must follow the new IDs.
r = A._pts_user_role({"username": "010307885", "role": "manager"})
print(f"[6a] _pts_user_role(010307885) -> {r!r}")
assert r == "admin", f"expected 'admin' (spoofed), got {r!r}"

r = A._pts_user_role({"username": "980909805", "role": "manager"})
print(f"[6b] _pts_user_role(980909805) -> {r!r}")
assert r == "admin"

# Legacy literals no longer get the spoof
r = A._pts_user_role({"username": "raed", "role": "manager"})
print(f"[6c] _pts_user_role(raed, manager) -> {r!r}")
assert r == "manager", f"legacy literal should no longer spoof, got {r!r}"

# ── Test 7: full route smoke — provision the prod-style user locally
#    then login and verify /points/manage returns 200 ──
SMOKE_USERS = [
    ("010307885", "ah_ib_smoke_pw", "أحمد إبراهيم", "manager"),
    ("980909805", "raed_smoke_pw",  "رائد",          "manager"),
]
with A.app.app_context():
    db = A.get_db()
    # The local DB already has these usernames from the seed mirror —
    # set known passwords so we can login.
    for uname, pw, name, role in SMOKE_USERS:
        existing = db.execute("SELECT id FROM users WHERE username=?",
                              (uname,)).fetchone()
        if existing:
            db.execute(
                "UPDATE users SET password=?, role=?, is_active=1, "
                "can_be_assigned_tasks=1 WHERE username=?",
                (A.hp(pw), role, uname))
        else:
            db.execute(
                "INSERT INTO users(username, password, role, name, "
                "is_active, can_be_assigned_tasks) "
                "VALUES(?,?,?,?,1,1)",
                (uname, A.hp(pw), role, name))
    db.commit()

c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code

# ahmed_ibrahim (010307885) → /points/manage
sc = login("010307885", "ah_ib_smoke_pw")
print(f"[7a] login 010307885 status={sc}")
rv = c.get("/points/manage", follow_redirects=False)
print(f"[7b] /points/manage -> {rv.status_code}")
assert rv.status_code == 200, (
    f"010307885 should access /points/manage, got {rv.status_code}")

# raed (980909805) → /points/manage
sc = login("980909805", "raed_smoke_pw")
rv = c.get("/points/manage", follow_redirects=False)
print(f"[7c] 980909805 /points/manage -> {rv.status_code}")
assert rv.status_code == 200

# ── Test 8: dashboard exposes data-can-manage-points=1 for both ──
rv = c.get("/dashboard")
html = rv.get_data(as_text=True)
assert 'dataset.canManagePoints = "1"' in html, (
    "980909805 dashboard missing data-can-manage-points=1")
print("[8] 980909805 dashboard exposes data-can-manage-points=1")

# Switch to ahmed_ibrahim and check the same
login("010307885", "ah_ib_smoke_pw")
rv = c.get("/dashboard")
html = rv.get_data(as_text=True)
assert 'dataset.canManagePoints = "1"' in html, (
    "010307885 dashboard missing data-can-manage-points=1")
print("[8a] 010307885 dashboard exposes data-can-manage-points=1")

# ── Test 9: admin regression ──
login("admin", "admin123")
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[9] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# Cleanup — restore the two users' role + password as they were
# (these are seed users in the local DB; we override password only)
with A.app.app_context():
    db = A.get_db()
    # Revert passwords to something obviously-test-only so re-runs work
    for uname, _, name, role in SMOKE_USERS:
        db.execute(
            "UPDATE users SET role=? WHERE username=?",
            (role, uname))
    db.commit()

print("\nAllowlist-fix smoke passed.")
