"""Smoke test — Web Push foundation (v3.1-push-foundation).

Invariants (per the Phase 2 brief):
  [1]  GET /api/push/vapid-public-key returns 200 with the
       expected envelope.
  [2]  POST /api/push/subscribe is registered.
  [3]  POST /api/push/unsubscribe is registered.
  [4]  push_subscriptions table exists in the live DB.
  [5]  /sw.js contains the push event handler.
  [6]  /sw.js contains the notificationclick handler.
  [7]  Permission-prompt UI present in main HTML
       (#mxPushBanner + _mxPushSubscribeFlow + mx_push_dismissed_until).
  [8]  pywebpush + py-vapid + cryptography pinned in
       requirements.txt.
  [9]  render.yaml declares VAPID_PUBLIC_KEY + VAPID_PRIVATE_KEY
       (both sync:false) + VAPID_CLAIM_SUB.
  [10] PARENT_HTML boot regression (the regression we've already
       chased + fixed twice): all Phase B/C cart wiring intact,
       _ppFormatStoreCard untouched, install banner intact.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as fh:
    SRC = fh.read()
with open(os.path.join(ROOT, "requirements.txt"),
          "r", encoding="utf-8") as fh:
    REQ = fh.read()
with open(os.path.join(ROOT, "render.yaml"),
          "r", encoding="utf-8") as fh:
    YML = fh.read()

import app  # noqa: E402

# ── [1] vapid-public-key
with app.app.test_client() as c:
    rv = c.get("/api/push/vapid-public-key")
assert rv.status_code == 200
import json as _j
d = _j.loads(rv.get_data(as_text=True))
assert "ok" in d and "public_key" in d and "enabled" in d, (
    "response envelope missing ok/public_key/enabled")
print("[1] GET /api/push/vapid-public-key -> 200, "
      "enabled=" + str(d.get("enabled")))

# ── [2] + [3] subscribe/unsubscribe registered
live = set()
for r in app.app.url_map.iter_rules():
    for m in (r.methods - {"OPTIONS", "HEAD"}):
        live.add((r.rule, m))
for rule in (("/api/push/subscribe", "POST"),
             ("/api/push/unsubscribe", "POST")):
    assert rule in live, "endpoint missing: " + str(rule)
print("[2] POST /api/push/subscribe registered")
print("[3] POST /api/push/unsubscribe registered")

# ── [4] push_subscriptions table
import sqlite3
db_path = getattr(app, "DB_PATH", "mindx.db")
con = sqlite3.connect(db_path)
try:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='push_subscriptions'").fetchall()
finally:
    con.close()
assert rows, "push_subscriptions table missing from live DB"
print("[4] push_subscriptions table exists in live DB")

# ── [5] + [6] SW push + notificationclick handlers
with app.app.test_client() as c:
    rv = c.get("/sw.js")
assert rv.status_code == 200
sw = rv.get_data(as_text=True)
assert "addEventListener('push'" in sw, (
    "/sw.js missing push handler")
assert "requireInteraction" in sw and "vibrate" in sw, (
    "/sw.js push handler missing requireInteraction/vibrate")
assert "addEventListener('notificationclick'" in sw, (
    "/sw.js missing notificationclick handler")
print("[5] /sw.js has push handler (with requireInteraction+vibrate)")
print("[6] /sw.js has notificationclick handler")

# ── [7] Permission-prompt UI in main HTML
# Note: the banner element itself is created at runtime (after the
# 30s/login-success trigger fires), so the static HTML only carries
# the #mxPushBanner CSS selector + the JS that builds + shows it.
with app.app.test_client() as c:
    rv = c.get("/parent/legacy?pid=200603680")
html = rv.get_data(as_text=True)
for needle in ("#mxPushBanner", "_mxPushSubscribeFlow",
               "mx_push_dismissed_until", "mx-login-success",
               "Notification.requestPermission",
               "_mxPushEnsureBanner"):
    assert needle in html, "push prompt UI missing: " + needle
print("[7] Permission-prompt UI + smart-timing IIFE present "
      "(CSS + builder + 30s/login triggers)")

# ── [8] requirements.txt deps
for dep in ("pywebpush==2.0.0", "py-vapid==1.9.0", "cryptography"):
    assert dep in REQ, "requirements.txt missing: " + dep
print("[8] pywebpush + py-vapid + cryptography pinned")

# ── [9] render.yaml VAPID entries
for needle in ("VAPID_PUBLIC_KEY", "VAPID_PRIVATE_KEY",
               "VAPID_CLAIM_SUB", "sync: false"):
    assert needle in YML, "render.yaml missing: " + needle
print("[9] render.yaml declares VAPID_PUBLIC_KEY / PRIVATE / "
      "CLAIM_SUB (sync:false on secrets)")

# ── [10] Parent boot regression
for n in ("ppBootAutoLookup", "ppSectionOnlyView",
          "function _ppRender", "function loadStoreMenu",
          "function _ppFormatStoreCard",
          "function requestStoreItem",
          "injectCartButtons", "injectCancelButtons",
          "injectOrderConfirmInterceptor",
          # PWA install banner from Phase 1 still alive
          "mxPwaBanner", "navigator.serviceWorker.register"):
    assert n in html, "boot/regression marker missing: " + n
assert "'اطلب الآن'" in html, "_ppFormatStoreCard label changed"
assert "var actionHtml" not in html, (
    "v2.9.9-era _ppFormatStoreCard rewrite leaked back in")
print("[10] Parent boot + Phase B/C wiring + PWA install banner "
      "all intact")

print("")
print("All 10 invariants passed.")
