"""C3 smoke - admin-purchase trigger moved to hero panel."""
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

# ── Test 1: hero panel rendered for admin ──
login("admin", "admin123")
rv = c.get("/points/manage")
assert rv.status_code == 200
html = rv.get_data(as_text=True)

assert 'id="ap-hero"' in html, "hero panel ID missing"
assert 'فتح النموذج' in html, "hero button label missing"
assert 'شراء مكافأة نيابة عن طالب' in html, "hero title missing"
print("[1] admin sees hero panel + 'فتح النموذج' button + descriptor")

# Hero appears BEFORE the tabs in document order
i_hero = html.find('id="ap-hero"')
i_tabs = html.find('class="tabs"')
assert i_hero > 0 and i_tabs > 0
assert i_hero < i_tabs, "hero panel should sit ABOVE the tabs strip"
print(f"[1a] hero (offset {i_hero}) is above tabs (offset {i_tabs}) ✓")

# ── Test 2: old cramped topbar button is gone ──
# The previous render had a <button onclick="apOpen()"> inside the
# .topbar div — verify it's no longer present in the topbar block
i_topbar = html.find('class="topbar"')
i_topbar_end = html.find('</div>', i_topbar)
topbar_block = html[i_topbar:i_topbar_end]
# Either no button in topbar at all, OR a button without apOpen
assert '<button' not in topbar_block or 'apOpen' not in topbar_block, \
    "old topbar button still present"
print("[2] old topbar button is gone ✓")

# ── Test 3: the modal markup is still present + apOpen function exists ──
assert 'id="ap-modal"' in html
assert 'function apOpen()' in html
print("[3] modal markup + apOpen function still present")

# ── Test 4: button inside hero correctly wires to apOpen() ──
# Slice from id="ap-hero" to the next top-level <div opening that
# follows (or 600 chars, whichever first — generous to span the
# whole panel including the button).
hero_block = html[i_hero:i_hero + 1200]
assert 'onclick="apOpen()"' in hero_block, "hero button doesn't wire to apOpen"
assert 'فتح النموذج' in hero_block
print("[4] hero button calls apOpen() ✓")

# ── Test 5: 980909805 (allowlist user) also sees the hero ──
with A.app.app_context():
    db = A.get_db()
    existing = db.execute("SELECT id FROM users WHERE username=?",
                          ("980909805",)).fetchone()
    if existing:
        db.execute(
            "UPDATE users SET password=?, role='manager', is_active=1 "
            "WHERE username=?", (A.hp("raed_pw"), "980909805"))
    else:
        db.execute(
            "INSERT INTO users(username, password, role, name, is_active, "
            "can_be_assigned_tasks) VALUES(?,?,?,?,1,1)",
            ("980909805", A.hp("raed_pw"), "manager", "رائد"))
    db.commit()
login("980909805", "raed_pw")
rv = c.get("/points/manage")
print(f"[5] 980909805 /points/manage -> {rv.status_code}")
assert rv.status_code == 200
assert 'id="ap-hero"' in rv.get_data(as_text=True)

# ── Test 6: teacher1 still blocked from the page ──
login("teacher1", "tea123")
rv = c.get("/points/manage", follow_redirects=False)
print(f"[6] teacher1 /points/manage -> {rv.status_code}")
assert rv.status_code == 302

# ── Test 7: search-fix from C2 still intact ──
login("admin", "admin123")
html2 = c.get("/points/manage").get_data(as_text=True)
i_open = html2.find('function apOpen()')
i_next = html2.find('function apClose()', i_open)
apopen_body = html2[i_open:i_next]
assert "document.getElementById('ap-note').value=''" not in apopen_body, \
    "the C2 fix has regressed"
print("[7] C2 search fix still intact ✓")

# ── Test 8: 8-route regression ──
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[8] {p} -> {rv.status_code}")
    assert rv.status_code == 200

print("\nC3 hero-panel smoke passed.")
