"""C37 smoke - notifications bell in dashboard."""
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

# Admin dashboard should contain the new bell markup
login("admin", "admin123")
rv = c.get("/dashboard")
body = rv.get_data(as_text=True)
print("[1] admin /dashboard len=", len(body))
checks = [
    ("bell wrap", 'id="tn-wrap"' in body),
    ("bell button", 'id="tn-bell"' in body),
    ("badge", 'id="tn-badge"' in body),
    ("dropdown", 'id="tn-dropdown"' in body),
    ("list container", 'id="tn-list"' in body),
    ("mark-all button", 'id="tn-mark-all"' in body),
    ("footer link", 'href="/tasks"' in body),
    ("CSS for dropdown", '.tn-dropdown' in body),
    ("unread-count fetch", '/api/notifications/unread-count' in body),
    ("list fetch", '/api/notifications?limit=20' in body),
    ("mark-read endpoint", '/api/notifications/' in body and '/read' in body),
    ("60s polling interval", '60000' in body),
    ("existing teacher-delivery bell preserved",
        'id="md-tb-bell"' in body and 'md-tb-bell-badge' in body),
]
for label, ok in checks:
    print("    -", label, "->", ok)
    assert ok, label

# Verify allowTasks flag is set (for the JS short-circuit guard)
assert 'allowTasks = "1"' in body
print("    - allowTasks=1 ✓")

# E2E: existing notifications endpoints still work
rv = c.get("/api/notifications/unread-count")
print("[2] /api/notifications/unread-count ->", rv.status_code,
      rv.get_json())
assert rv.status_code == 200
assert "count" in (rv.get_json() or {})

rv = c.get("/api/notifications")
print("[3] /api/notifications ->", rv.status_code,
      "count:", len((rv.get_json() or {}).get("notifications") or []))
assert rv.status_code == 200

# Regression: legacy routes still work
for p in ["/parent", "/points/manage", "/expenses", "/assets",
          "/tasks", "/tasks/dashboard/personal", "/tasks/dashboard/team",
          "/tasks/dashboard/admin"]:
    rv = c.get(p)
    print("[reg]", p, "->", rv.status_code)
    assert rv.status_code == 200, p

print("\nC37 smoke passed.")
