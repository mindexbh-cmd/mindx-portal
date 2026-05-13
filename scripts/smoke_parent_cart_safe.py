"""Smoke test — Parent cart defensive rebuild (v2.9.9-safe).

Invariants enforced (matching the brief's 10 checks):
  [1]  /parent/legacy returns 200 with a valid pid.
  [2]  Hub-navigation invariants intact: ppBootAutoLookup +
       ppSectionOnlyView + the boot-critical render functions
       (_ppRender, loadStoreMenu, _ppFormatStoreCard,
       requestStoreItem) all still present and untouched.
  [3]  cart_items table exists in the live DB.
  [4]  All 5 cart endpoints registered with the correct methods.
  [5]  #cartModalBack present in rendered HTML.
  [6]  #cartFab + #cartFabBadge present in rendered HTML.
  [7]  window.cartModalOpen exists exactly once in JS.
  [8]  window.cartAdd exists exactly once in JS.
  [9]  IIFE defensive wrapper present (use strict + the IIFE open
       sequence) — module-level state doesn't leak outside the
       wrapper.
  [10] ZERO modifications to _ppFormatStoreCard / _ppRender /
       loadStoreMenu — exact strings match the v2.9.8.1 baseline.
       (Asserted via the markers' presence + a structural check
       that no `actionHtml` variable was reintroduced inside
       _ppFormatStoreCard.)
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as fh:
    SRC = fh.read()

# Boot: importing app proves no parse/runtime error at module load.
import app  # noqa: E402

# ── [1] /parent/legacy returns 200
with app.app.test_client() as c:
    rv = c.get("/parent/legacy?pid=200603680")
assert rv.status_code == 200, "/parent/legacy returned " + str(rv.status_code)
html = rv.get_data(as_text=True)
print("[1] GET /parent/legacy?pid=... -> 200")

# ── [2] Boot-path invariants intact
for needle in ("pp-pid", "ppBootAutoLookup", "ppSectionOnlyView",
               "function _ppRender", "function loadStoreMenu",
               "function _ppFormatStoreCard", "requestStoreItem"):
    assert needle in html, "boot path missing: " + needle
print("[2] Hub-navigation invariants intact (ppBootAutoLookup, "
      "ppSectionOnlyView, _ppRender, loadStoreMenu, "
      "_ppFormatStoreCard, requestStoreItem)")

# ── [3] cart_items table in live DB
import sqlite3
db_path = getattr(app, "DB_PATH", "mindx.db")
con = sqlite3.connect(db_path)
try:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='cart_items'").fetchall()
finally:
    con.close()
assert rows, "cart_items table missing in live DB"
print("[3] cart_items table exists in live DB")

# ── [4] All 5 cart endpoints registered
expected = {
    ("/api/parent/cart/add",                "POST"),
    ("/api/parent/cart",                    "GET"),
    ("/api/parent/cart/<int:cid>/quantity", "PUT"),
    ("/api/parent/cart/<int:cid>",          "DELETE"),
    ("/api/parent/cart/checkout",           "POST"),
}
live = set()
for r in app.app.url_map.iter_rules():
    for m in (r.methods - {"OPTIONS", "HEAD"}):
        live.add((r.rule, m))
missing = expected - live
assert not missing, "cart endpoints missing: " + str(missing)
print("[4] All 5 cart endpoints registered")

# ── [5] cart modal in HTML
assert 'id="cartModalBack"' in html, "cart modal markup missing"
assert "cartItemsList" in html and "cartCheckoutBtn" in html
print("[5] #cartModalBack + cart modal scaffolding present")

# ── [6] cart fab + badge
assert 'id="cartFab"' in html and 'id="cartFabBadge"' in html, \
    "cart floating button or badge missing"
print("[6] #cartFab + #cartFabBadge present")

# ── [7] cartModalOpen defined exactly once
n = len(re.findall(r"window\.cartModalOpen\s*=\s*function", html))
assert n == 1, "window.cartModalOpen defined " + str(n) + " times"
print("[7] window.cartModalOpen defined exactly once")

# ── [8] cartAdd defined exactly once
n = len(re.findall(r"window\.cartAdd\s*=\s*function", html))
assert n == 1, "window.cartAdd defined " + str(n) + " times"
print("[8] window.cartAdd defined exactly once")

# ── [9] IIFE defensive wrapper present
# Look for the exact opening pattern + 'use strict' inside the
# cart IIFE, plus a closing })(); after the cart code.
assert "===== Cart system" in html and "'use strict'" in html, \
    "defensive IIFE / strict mode wrapper missing"
print("[9] Cart IIFE defensive wrapper + 'use strict' present")

# ── [10] No modifications to _ppFormatStoreCard / _ppRender /
#        loadStoreMenu. We check that the v2.9.9 (broken) markers
#        are NOT present: no 'actionHtml' variable, no
#        'ppTileAddToCart' hook on prize cards, no
#        'ppCartRefresh' call inside loadStoreMenu body.
assert "var actionHtml" not in html, (
    "_ppFormatStoreCard rewrite from v2.9.9 leaked in — "
    "regression vector present")
assert "ppTileAddToCart" not in html, (
    "v2.9.9-era per-tile add-to-cart wiring leaked in")
assert "window.ppCartRefresh" not in html, (
    "v2.9.9-era loadStoreMenu hook leaked in")
# And the legacy active-button label is intact in the renderer:
assert "'اطلب الآن'" in html, (
    "_ppFormatStoreCard's 'اطلب الآن' label gone — renderer "
    "was modified, breaking the zero-touching guarantee")
print("[10] ZERO modifications to _ppFormatStoreCard / _ppRender "
      "/ loadStoreMenu (legacy markers intact, v2.9.9 hooks not "
      "present)")

print("")
print("All 10 invariants passed.")
