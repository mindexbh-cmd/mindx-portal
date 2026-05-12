"""C6 smoke - pending-delivery tab UI."""
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

login("admin", "admin123")
rv = c.get("/points/manage")
assert rv.status_code == 200
html = rv.get_data(as_text=True)

# Tab button present
assert "showTab('pending-delivery')" in html, "tab button not wired"
assert "في انتظار التسليم" in html, "Arabic label missing"
assert 'id="pd-badge"' in html, "badge element missing"
print("[1] tab button + Arabic label + badge present")

# showTab dispatcher knows the new key
assert "'pending-delivery':loadPendingDelivery" in html or \
       "'pending-delivery': loadPendingDelivery" in html, \
       "showTab dispatcher missing pending-delivery"
print("[2] showTab dispatcher wired to loadPendingDelivery")

# Helpers
for fn in ['function loadPendingDelivery()', 'function pdDeliver',
           'function _pdRefreshBadge', 'function _pdSourceBadge',
           'function _pdRelTime']:
    assert fn in html, f"missing helper: {fn}"
print("[3] all 5 JS helpers present")

# Endpoint URL referenced
assert '/api/points/history?status=pending' in html
assert "/deliver',\n" in html or "/deliver'," in html
print("[4] pending-history + deliver endpoint URLs referenced")

# Badge polling
assert 'setInterval(_pdRefreshBadge' in html
print("[5] badge poller scheduled")

# 8-route regression
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[6] {p} -> {rv.status_code}")
    assert rv.status_code == 200

print("\nC6 pending-delivery smoke passed.")
