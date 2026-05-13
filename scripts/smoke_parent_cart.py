"""Smoke test — Parent shop cart system (v2.9.9 Phase B).

Invariants:
  [1]  cart_items table is created at boot (visible in sqlite_master
       on the local SQLite path).
  [2]  All 5 cart endpoints registered with the expected methods.
  [3]  Cart modal markup present in PARENT_HTML
       (ppCartBack / ppCartBody / ppCartFoot / pp-cart-checkout).
  [4]  Floating cart button (#ppCartFab) + badge (#ppCartBadge)
       present.
  [5]  Renderer emits a per-tile qty selector + add-to-cart wiring
       (.pp-tile-qty-row class + ppTileAddToCart call) on AVAILABLE
       tiles.
  [6]  All six generic-name aliases defined exactly once:
       addToCart, openCart, closeCart, updateQuantity,
       removeFromCart, checkout.
  [7]  app.py parses + imports cleanly with the new code in place.
  [8]  Existing /api/parent/store/request endpoint still registered
       (regression guard — must NOT have been touched).
  [9]  Upsert pattern: add-to-cart uses UPDATE-then-INSERT (the
       project's cross-DB equivalent of ON CONFLICT … DO UPDATE).
  [10] Checkout endpoint re-validates total ≤ balance server-side
       AND writes redemptions rows with status='pending' so points
       debit per _pts_balance semantics.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as fh:
    SRC = fh.read()

# ── 7
import app  # noqa: E402,F401
print("[7] app.py imports without raising")

# ── 1: cart_items table exists in live SQLite
import sqlite3
db_path = getattr(app, "DB_PATH", "mindx.db")
con = sqlite3.connect(db_path)
try:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='cart_items'").fetchall()
finally:
    con.close()
assert rows, "cart_items table missing from live SQLite at " + db_path
print("[1] cart_items table exists in live DB")

# ── 2: all 5 endpoints registered
expected_routes = {
    ("/api/parent/cart/add", "POST"),
    ("/api/parent/cart", "GET"),
    ("/api/parent/cart/<int:cid>/quantity", "PUT"),
    ("/api/parent/cart/<int:cid>", "DELETE"),
    ("/api/parent/cart/checkout", "POST"),
}
live_pairs = set()
for r in app.app.url_map.iter_rules():
    methods = r.methods - {"OPTIONS", "HEAD"}
    for m in methods:
        live_pairs.add((r.rule, m))
missing = expected_routes - live_pairs
assert not missing, "cart endpoints missing: " + str(missing)
print("[2] All 5 cart endpoints registered:")
for (rule, m) in sorted(expected_routes):
    print("    " + m + " " + rule)

# ── 3: cart modal markup
required_modal = [
    'id="ppCartBack"',
    'id="ppCartBody"',
    'id="ppCartFoot"',
    'class="pp-cart-close"',
    'pp-cart-checkout',
]
missing = [m for m in required_modal if m not in SRC]
assert not missing, "cart modal markup missing: " + str(missing)
print("[3] Cart modal HTML present")

# ── 4: floating button + badge
assert 'id="ppCartFab"' in SRC, "floating cart button missing"
assert 'id="ppCartBadge"' in SRC, "cart badge missing"
print("[4] Floating cart button + badge present")

# ── 5: per-tile qty selector + add-to-cart wiring in renderer
fmt_idx = SRC.index("function _ppFormatStoreCard")
fmt_body = SRC[fmt_idx:fmt_idx + 4000]
assert "pp-tile-qty-row" in fmt_body, (
    "renderer missing per-tile qty selector (.pp-tile-qty-row)")
assert "ppTileAddToCart" in fmt_body, (
    "renderer doesn't wire ppTileAddToCart on prize tiles")
print("[5] Renderer emits qty selector + ppTileAddToCart on tiles")

# ── 6: generic-name aliases defined exactly once
required_aliases = ["addToCart", "openCart", "closeCart",
                    "updateQuantity", "removeFromCart", "checkout"]
for name in required_aliases:
    pat = re.compile(r"window\." + re.escape(name)
                     + r"\s*=\s*function")
    matches = pat.findall(SRC)
    assert len(matches) == 1, (
        "window." + name + " defined " + str(len(matches))
        + " times (expected 1)")
print("[6] All 6 generic-name aliases defined exactly once: "
      + ", ".join(required_aliases))

# ── 8: legacy /api/parent/store/request still registered (no regression)
legacy = ("/api/parent/store/request", "POST")
assert legacy in live_pairs, (
    "legacy /api/parent/store/request endpoint missing — Phase A "
    "regression")
print("[8] Legacy /api/parent/store/request endpoint untouched")

# ── 9: upsert pattern in api_parent_cart_add
add_idx = SRC.index("def api_parent_cart_add")
add_body = SRC[add_idx:add_idx + 4000]
assert ("UPDATE cart_items SET quantity = quantity + ?" in add_body
        and "INSERT INTO cart_items" in add_body), (
    "api_parent_cart_add should upsert via UPDATE-then-INSERT — "
    "pattern not found")
print("[9] api_parent_cart_add uses UPDATE-then-INSERT upsert "
      "(cross-DB equivalent of ON CONFLICT DO UPDATE)")

# ── 10: checkout re-validates server-side AND writes status='pending'
chk_idx = SRC.index("def api_parent_cart_checkout")
chk_body = SRC[chk_idx:chk_idx + 4000]
assert "_pts_balance(db, sid)" in chk_body, (
    "checkout doesn't re-fetch live balance via _pts_balance")
assert "summary[\"total\"] > balance" in chk_body, (
    "checkout missing total-vs-balance guard")
assert '"pending"' in chk_body or "'pending'" in chk_body, (
    "checkout must write status='pending' so points debit per "
    "_pts_balance semantics")
print("[10] Checkout re-validates server-side AND writes "
      "status='pending' (debits per _pts_balance)")

print("")
print("All 10 invariants passed.")
