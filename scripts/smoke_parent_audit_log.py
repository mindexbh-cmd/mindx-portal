"""Smoke test — Parent activity audit log (v2.9.11-safe).

Invariants:
  [1]  App imports cleanly.
  [2]  Parent flow regression test: /parent/legacy renders 200 with
       every boot-path function still present + every Phase B/C
       cart/cancel/confirmation marker intact.
  [3]  GET /api/admin/parent-audit-log endpoint registered.
  [4]  /points/manage page renders 200 for an admin session AND
       contains the new audit-log section markup
       (#palSection, #palBody, #palPrev, #palNext, ACTION_LABEL map).
  [5]  All 6 new _audit() calls present in the source
       ('parent.cart_add', 'parent.cart_update', 'parent.cart_remove',
        'parent.cart_checkout', 'parent.direct_order',
        'admin.redeem_approve').
  [6]  The 2 pre-existing audit actions still present
       ('redemptions.cancel_by_parent', 'redemptions.reject').
  [7]  Endpoint returns the {ok, items, total, page, per_page, pages}
       envelope when called with admin session.
  [8]  Endpoint requires admin gate (unauthenticated request is
       redirected or denied — NOT 200).
  [9]  No `parent_audit_log` table was created (we deliberately
       reused the existing audit_log table; a separate table
       would mean schema duplication).
  [10] _ppFormatStoreCard, _ppRender, loadStoreMenu untouched
       (zero-touching guard).
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as fh:
    SRC = fh.read()

# ── [1] App imports
import app  # noqa: E402,F401
print("[1] app.py imports cleanly")

# ── [2] Parent flow regression test
with app.app.test_client() as c:
    rv = c.get("/parent/legacy?pid=200603680")
assert rv.status_code == 200, "/parent/legacy status=" + str(rv.status_code)
html = rv.get_data(as_text=True)
for needle in ("pp-pid", "ppBootAutoLookup", "ppSectionOnlyView",
               "function _ppRender", "function loadStoreMenu",
               "function _ppFormatStoreCard",
               "function requestStoreItem",
               "injectCartButtons", "injectCancelButtons",
               "injectOrderConfirmInterceptor",
               "window.cartModalOpen", "window.cartAdd",
               "window.orderConfirmShow", "window.cancelOrderShow"):
    assert needle in html, "parent flow regression — missing: " + needle
print("[2] Parent flow boot path + Phase B/C wiring all intact")

# ── [3] New admin endpoint registered
live = set()
for r in app.app.url_map.iter_rules():
    for m in (r.methods - {"OPTIONS", "HEAD"}):
        live.add((r.rule, m))
assert ("/api/admin/parent-audit-log", "GET") in live, (
    "GET /api/admin/parent-audit-log missing from Flask url_map")
print("[3] GET /api/admin/parent-audit-log registered")

# ── [4] Admin /points/manage renders + contains audit section
with app.app.test_client() as c:
    with c.session_transaction() as s:
        s["user"] = {"id": 1, "username": "admin", "role": "admin"}
    rv = c.get("/points/manage")
assert rv.status_code == 200, "/points/manage status=" + str(rv.status_code)
hpm = rv.get_data(as_text=True)
for needle in ('id="palSection"', 'id="palBody"',
               'id="palPrev"', 'id="palNext"',
               "ACTION_LABEL", "parent-audit-log",
               "سجل نشاط أولياء الأمور"):
    assert needle in hpm, "/points/manage missing: " + needle
print("[4] /points/manage renders + contains audit-log section")

# ── [5] All 6 new _audit actions present in source
for action in ("parent.cart_add", "parent.cart_update",
               "parent.cart_remove", "parent.cart_checkout",
               "parent.direct_order", "admin.redeem_approve"):
    assert '"' + action + '"' in SRC, (
        "_audit call missing for action: " + action)
print("[5] All 6 new _audit() actions present in source")

# ── [6] Pre-existing audit actions still present
for action in ("redemptions.cancel_by_parent", "redemptions.reject"):
    assert '"' + action + '"' in SRC, (
        "pre-existing audit action removed: " + action)
print("[6] Pre-existing audit actions still present")

# ── [7] Endpoint response envelope
import json as _j
with app.app.test_client() as c:
    with c.session_transaction() as s:
        s["user"] = {"id": 1, "username": "admin", "role": "admin"}
    rv = c.get("/api/admin/parent-audit-log?page=1&per_page=5")
assert rv.status_code == 200, "endpoint status=" + str(rv.status_code)
d = _j.loads(rv.get_data(as_text=True))
assert d.get("ok") is True
for k in ("items", "total", "page", "per_page", "pages"):
    assert k in d, "response missing key: " + k
print("[7] Endpoint returns {ok,items,total,page,per_page,pages} envelope")

# ── [8] Unauthenticated request is denied
with app.app.test_client() as c:
    rv = c.get("/api/admin/parent-audit-log")
assert rv.status_code != 200, (
    "endpoint must require admin gate — unauthenticated got 200")
print("[8] Endpoint requires admin gate (unauth status=" + str(rv.status_code) + ")")

# ── [9] No parent_audit_log table created
assert "CREATE TABLE IF NOT EXISTS parent_audit_log" not in SRC, (
    "a separate parent_audit_log table was created — Phase C "
    "explicitly chose to reuse the existing audit_log table; "
    "duplicate infrastructure breaks the rule")
print("[9] No duplicate parent_audit_log table created (reuse path honored)")

# ── [10] Zero-touching guard for the renderer + boot
assert "'اطلب الآن'" in html, "_ppFormatStoreCard label changed"
assert "data-reward-id" not in html, (
    "data-reward-id leaked in — violates zero-touching")
assert "var actionHtml" not in html, (
    "v2.9.9-era _ppFormatStoreCard rewrite leaked in")
print("[10] _ppFormatStoreCard / _ppRender / loadStoreMenu untouched")

print("")
print("All 10 invariants passed.")
