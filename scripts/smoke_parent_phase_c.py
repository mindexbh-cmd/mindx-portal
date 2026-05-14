"""Smoke test — Parent shop Phase C (v2.9.10-safe).

Invariants:
  [1]  Navigation regression test: /parent/legacy renders 200 with
       the boot-path functions still present.
  [2]  POST /api/parent/order/cancel endpoint registered.
  [3]  #orderConfirmBack modal markup present.
  [4]  #cancelOrderConfirmBack modal markup present.
  [5]  window.orderConfirmShow defined exactly once.
  [6]  window.cancelOrderShow defined exactly once.
  [7]  injectCancelButtons defined inside the IIFE.
  [8]  injectCartButtons builds a qty selector (cart-qty-selector
       class + _buildQtySelector helper).
  [9]  setupCheckoutConfirm defined (cart-checkout intercept).
  [10] _ppFormatStoreCard untouched (label + no v2.9.9-era leaks).
  [11] _ppRender untouched (function declaration still present).
  [12] loadStoreMenu untouched (function declaration still present).
  [13] Brace balance in the rendered <script> block.
  [14] No duplicate window.* assignments for the new handlers.
  [15] Existing cart functionality intact (cart endpoints + IIFE +
       legacy parent-store endpoint still registered).
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as fh:
    SRC = fh.read()

import app  # noqa: E402

# ── [1] Navigation regression test
with app.app.test_client() as c:
    rv = c.get("/parent/legacy?pid=200603680")
assert rv.status_code == 200, "status=" + str(rv.status_code)
html = rv.get_data(as_text=True)
for needle in ("pp-pid", "ppBootAutoLookup", "ppSectionOnlyView",
               "function _ppRender", "function loadStoreMenu",
               "function _ppFormatStoreCard", "requestStoreItem"):
    assert needle in html, "boot path missing: " + needle
print("[1] /parent/legacy -> 200 + boot-path invariants intact")

# ── [2] Cancel endpoint registered
live = set()
for r in app.app.url_map.iter_rules():
    for m in (r.methods - {"OPTIONS", "HEAD"}):
        live.add((r.rule, m))
assert ("/api/parent/order/cancel", "POST") in live, (
    "POST /api/parent/order/cancel missing")
print("[2] POST /api/parent/order/cancel registered")

# ── [3] orderConfirmBack modal markup
assert 'id="orderConfirmBack"' in html, "orderConfirmBack missing"
assert "orderConfirmBody" in html and "orderConfirmGo" in html
print("[3] orderConfirmBack modal markup present")

# ── [4] cancelOrderConfirmBack modal markup
assert 'id="cancelOrderConfirmBack"' in html, (
    "cancelOrderConfirmBack missing")
assert "cancelOrderGo" in html
print("[4] cancelOrderConfirmBack modal markup present")

# ── [5] window.orderConfirmShow defined exactly once
n = len(re.findall(r"window\.orderConfirmShow\s*=\s*function", html))
assert n == 1, "orderConfirmShow defined " + str(n) + " times"
print("[5] window.orderConfirmShow defined exactly once")

# ── [6] window.cancelOrderShow defined exactly once
n = len(re.findall(r"window\.cancelOrderShow\s*=\s*function", html))
assert n == 1, "cancelOrderShow defined " + str(n) + " times"
print("[6] window.cancelOrderShow defined exactly once")

# ── [7] injectCancelButtons inside IIFE
assert "function injectCancelButtons" in html, (
    "injectCancelButtons missing")
print("[7] injectCancelButtons defined in cart IIFE")

# ── [8] qty selector helpers + class
assert "function _buildQtySelector" in html
assert "cart-qty-selector" in html
assert "cart-qty-num-input" in html
print("[8] qty selector (_buildQtySelector + cart-qty-* classes) "
      "present")

# ── [9] setupCheckoutConfirm
assert "function setupCheckoutConfirm" in html
assert "data-confirm-wired" in html  # idempotency sentinel
print("[9] setupCheckoutConfirm + idempotency sentinel present")

# ── [10] _ppFormatStoreCard untouched
assert "'اطلب الآن'" in html, "_ppFormatStoreCard label gone"
assert "var actionHtml" not in html, (
    "v2.9.9-era _ppFormatStoreCard rewrite leaked in")
assert "data-reward-id" not in html, (
    "data-reward-id leaked in — violates zero-touching")
assert "data-redemption-id" not in html, (
    "data-redemption-id leaked in")
assert "ppTileAddToCart" not in html, (
    "v2.9.9-era ppTileAddToCart wiring leaked in")
print("[10] _ppFormatStoreCard untouched (no v2.9.9 leaks)")

# ── [11] _ppRender untouched
assert "function _ppRender" in html
print("[11] _ppRender declaration present")

# ── [12] loadStoreMenu untouched
assert "function loadStoreMenu" in html
print("[12] loadStoreMenu declaration present")

# ── [13] Brace balance
m = re.search(r"<script>(.*?)</script>", html, re.S)
js = m.group(1)
ob, cb = js.count("{"), js.count("}")
assert ob == cb, "brace mismatch: " + str(ob) + "/" + str(cb)
print("[13] JS braces balanced: " + str(ob) + "/" + str(cb))

# ── [14] No duplicate window.* for Phase C handlers
for name in ("orderConfirmShow", "orderConfirmClose",
             "orderConfirmProceed",
             "cancelOrderShow", "cancelOrderClose",
             "cancelOrderProceed"):
    c2 = len(re.findall(r"window\." + name + r"\s*=\s*function",
                        html))
    assert c2 == 1, "window." + name + " defined " + str(c2) + " times"
print("[14] All 6 Phase C window handlers defined exactly once")

# ── [15] Existing functionality intact
for rule in (("/api/parent/cart/add", "POST"),
             ("/api/parent/cart", "GET"),
             ("/api/parent/cart/<int:cid>/quantity", "PUT"),
             ("/api/parent/cart/<int:cid>", "DELETE"),
             ("/api/parent/cart/checkout", "POST"),
             ("/api/parent/store/request", "POST")):
    assert rule in live, "endpoint gone: " + str(rule)
print("[15] Cart endpoints + legacy parent-store endpoint intact")

# ── [16] Phase C.1 direct-order confirmation interceptor
#        (v2.9.10.1-safe): injectOrderConfirmInterceptor +
#        showDirectOrderConfirm helpers exist, original
#        requestStoreItem is still defined (we wrap it, never
#        replace it), and the IIFE-private _confirmMode flag is
#        present (no dynamic window.* reassignment).
assert "function injectOrderConfirmInterceptor" in html, (
    "injectOrderConfirmInterceptor missing")
assert "function showDirectOrderConfirm" in html, (
    "showDirectOrderConfirm missing")
assert "function requestStoreItem" in html, (
    "legacy requestStoreItem definition gone — we should wrap "
    "it, not delete it")
assert "_confirmMode" in html and "_directRewardId" in html, (
    "_confirmMode / _directRewardId state vars missing — "
    "branching pattern absent")
assert "data-direct-confirm-wired" in html, (
    "interceptor idempotency sentinel missing")
print("[16] Direct-order confirm interceptor wired + original "
      "requestStoreItem preserved")

print("")
print("All 16 invariants passed.")
