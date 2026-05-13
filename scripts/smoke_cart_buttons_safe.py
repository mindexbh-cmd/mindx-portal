"""Smoke test — Per-tile "أضف للسلة" buttons (v2.9.9.1-safe).

Builds on top of the v2.9.9-safe rebuild. This smoke specifically
asserts:

  [1]  /parent/legacy renders 200 with a valid pid.
  [2]  Hub-navigation invariants intact: ppBootAutoLookup,
       ppSectionOnlyView, _ppRender, loadStoreMenu,
       _ppFormatStoreCard, requestStoreItem.
  [3]  The renderer was NOT modified — the original 'اطلب الآن'
       label string is still in the source, no 'data-reward-id'
       attribute was added to .pp-store-card, no v2.9.9-era
       ppTileAddToCart wiring leaked back in, no 'var actionHtml'
       rewrite present.
  [4]  injectCartButtons + setupCartButtonObserver defined inside
       the cart IIFE.
  [5]  MutationObserver pattern used (defensive — no render hook).
  [6]  Regex extraction pattern present
       (requestStoreItem\((\d+)\)).
  [7]  Click handlers attached via addEventListener (NOT inline
       onclick on the injected button — defence against quote-
       escaping bugs).
  [8]  All 5 cart endpoints still registered.
  [9]  window.cartAdd reachable from outside the IIFE.
  [10] JS brace count balanced in the rendered HTML.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as fh:
    SRC = fh.read()

import app  # noqa: E402

# ── [1] /parent/legacy renders
with app.app.test_client() as c:
    rv = c.get("/parent/legacy?pid=200603680")
assert rv.status_code == 200, "status=" + str(rv.status_code)
html = rv.get_data(as_text=True)
print("[1] GET /parent/legacy?pid=... -> 200")

# ── [2] Boot invariants
for needle in ("pp-pid", "ppBootAutoLookup", "ppSectionOnlyView",
               "function _ppRender", "function loadStoreMenu",
               "function _ppFormatStoreCard", "requestStoreItem"):
    assert needle in html, "boot missing: " + needle
print("[2] Hub-navigation invariants intact")

# ── [3] Renderer untouched
assert "'اطلب الآن'" in html, (
    "'اطلب الآن' label gone — renderer was modified")
assert "data-reward-id" not in html, (
    "data-reward-id attribute leaked in — violates zero-touching")
assert "ppTileAddToCart" not in html, (
    "v2.9.9-era per-tile wiring leaked in")
assert "var actionHtml" not in html, (
    "v2.9.9-era _ppFormatStoreCard rewrite leaked in")
print("[3] _ppFormatStoreCard untouched (no v2.9.9 regression vectors)")

# ── [4] New observer code inside the IIFE
assert "function injectCartButtons" in html, (
    "injectCartButtons missing from cart IIFE")
assert "function setupCartButtonObserver" in html, (
    "setupCartButtonObserver missing from cart IIFE")
print("[4] injectCartButtons + setupCartButtonObserver defined")

# ── [5] MutationObserver pattern
assert "MutationObserver" in html, "MutationObserver pattern absent"
assert "childList: true" in html and "subtree: true" in html, (
    "observer options missing — won't catch re-renders")
print("[5] MutationObserver with childList+subtree present")

# ── [6] Regex extraction
assert re.search(r"requestStoreItem\\\\\(\\\\d\+\\\\\)", html) \
    or "requestStoreItem\\\\(" in html \
    or "/requestStoreItem\\((\\d+)\\)/" in html.replace("\\\\", "\\"), \
    "regex extraction pattern not found"
print("[6] requestStoreItem regex extraction pattern present")

# ── [7] addEventListener, NO inline onclick on the injected button
# The injected DOM button is created via document.createElement,
# wired via btn.addEventListener('click', ...). We assert that the
# IIFE contains "addEventListener('click'" near the injection code.
inj_start = SRC.index("function injectCartButtons")
inj_block = SRC[inj_start:inj_start + 3000]
assert "addEventListener('click'" in inj_block, (
    "injected button missing addEventListener click wiring")
# And that we DIDN'T fall back to inline onclick='cartAdd(…)'
assert ".onclick = " not in inj_block, (
    "injected button uses .onclick= instead of addEventListener")
print("[7] Injected button uses addEventListener (no inline onclick)")

# ── [8] All 5 cart endpoints still registered
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
assert not (expected - live), "endpoints lost: " + str(expected - live)
print("[8] All 5 cart endpoints still registered")

# ── [9] window.cartAdd reachable
n = len(re.findall(r"window\.cartAdd\s*=\s*function", html))
assert n == 1, "window.cartAdd defined " + str(n) + " times"
print("[9] window.cartAdd defined exactly once")

# ── [10] Brace balance
m = re.search(r"<script>(.*?)</script>", html, re.S)
js = m.group(1)
ob, cb = js.count("{"), js.count("}")
assert ob == cb, "brace mismatch: " + str(ob) + "/" + str(cb)
print("[10] JS braces balanced: " + str(ob) + "/" + str(cb))

print("")
print("All 10 invariants passed.")
