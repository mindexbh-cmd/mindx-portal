"""C7 smoke - history tab UI."""
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

# Tab button
assert "showTab('history')" in html
assert "سجل العمليات" in html
print("[1] history tab button + Arabic label present")

# showTab dispatcher
assert "history:loadHistory" in html
print("[2] showTab → loadHistory wired")

# JS helpers
for fn in ['function loadHistory()', 'function histApply()',
           'function _histBuildURL()', 'function _histFetch()',
           'function histPage', 'function histUndeliver',
           'function histExportCSV()', 'function _histStatusLabel',
           'function _histSourceLabel']:
    assert fn in html, f"missing: {fn}"
print("[3] all 9 history JS helpers present")

# Filter controls
for needle in ['id="hf-name"', 'id="hf-status"', 'id="hf-source"',
              'id="hf-from"', 'id="hf-to"']:
    assert needle in html, f"missing filter control: {needle}"
print("[4] filter controls present (name + status + source + 2 dates)")

# CSV export button
assert "📥 CSV" in html or 'histExportCSV' in html
print("[5] CSV export button wired")

# Inline rejection-reason styling for rejected rows
assert "سبب الرفض" in html
print("[6] rejection-reason inline display present")

# Undeliver button uses the C4 endpoint
assert "/api/points/redemptions/'" in html
assert "'/undeliver'" in html
print("[7] undeliver action wired to /undeliver endpoint")

# 8-route regression
for p in ['/parent','/dashboard','/tasks','/tasks/recurring',
          '/expenses','/assets','/points/manage','/database']:
    rv = c.get(p)
    print(f"[8] {p} -> {rv.status_code}")
    assert rv.status_code == 200

# Other tabs still work — C6 functions still intact
assert "function loadPendingDelivery()" in html
print("[9] C6 pending-delivery tab functions still intact")

print("\nC7 history-tab smoke passed.")
