"""Smoke test — Admin push send panel (v3.2-push-send, Phase 3A).

Invariants:
  [1]  notifications table exists in live DB.
  [2]  POST /api/admin/push/send registered.
  [3]  GET  /api/admin/push/history registered.
  [4]  GET  /api/admin/push-subscriptions-count still registered
       (Phase 3A doesn't regress v3.1.2 visibility endpoints).
  [5]  pywebpush importable.
  [6]  Send panel UI present on /points/manage (#psSection,
       psSend, psUpdateTargetUI, psLoadHistory, target inputs).
  [7]  Send panel does NOT interfere with the existing pal-*
       audit log section.
  [8]  Send endpoint rejects with 400 on missing title.
  [9]  Send endpoint rejects with 400 on invalid target_type.
  [10] Parent flow + cart + Phase B/C wiring intact.
  [11] Push subscribe/unsubscribe + VAPID endpoints still alive
       (v3.1 + v3.1.1 + v3.1.2 layers all preserved).
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as fh:
    SRC = fh.read()

import app  # noqa: E402

# ── [1] notifications table
import sqlite3
db_path = getattr(app, "DB", "mindex.db")
con = sqlite3.connect(db_path)
try:
    rows = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name='notifications'").fetchall()
finally:
    con.close()
assert rows, "notifications table missing from live DB"
print("[1] notifications table exists in live DB")

# ── [2..4] / [11] endpoints registered
live = set()
for r in app.app.url_map.iter_rules():
    for m in (r.methods - {"OPTIONS", "HEAD"}):
        live.add((r.rule, m))
for rule in (("/api/admin/push/send", "POST"),
             ("/api/admin/push/history", "GET"),
             ("/api/admin/push-subscriptions-count", "GET"),
             ("/api/push/subscribe", "POST"),
             ("/api/push/unsubscribe", "POST"),
             ("/api/push/vapid-public-key", "GET")):
    assert rule in live, "endpoint missing: " + str(rule)
print("[2] POST /api/admin/push/send registered")
print("[3] GET  /api/admin/push/history registered")
print("[4] GET  /api/admin/push-subscriptions-count still registered")
print("[11] Phase 2 push endpoints (subscribe/unsubscribe/"
      "vapid-public-key) still registered")

# ── [5] pywebpush importable
try:
    from pywebpush import webpush, WebPushException  # noqa: F401
    print("[5] pywebpush + WebPushException importable")
except ImportError:
    raise AssertionError(
        "pywebpush not installed — Render build should have "
        "picked it up from requirements.txt")

# ── [6] Send panel UI
with app.app.test_client() as c:
    with c.session_transaction() as s:
        s["user"] = {"id": 1, "username": "admin", "role": "admin"}
    rv = c.get("/points/manage")
assert rv.status_code == 200
hpm = rv.get_data(as_text=True)
for needle in ('id="psSection"', 'id="psTitle"', 'id="psBody"',
               'id="psUrgent"', 'id="psTargetType"',
               'id="psTargetRole"', 'id="psTargetGroup"',
               'id="psTargetPid"', 'id="psHistoryBody"',
               "window.psSend", "window.psUpdateTargetUI",
               "/api/admin/push/send", "/api/admin/push/history"):
    assert needle in hpm, "send panel UI missing: " + needle
print("[6] Send panel UI present on /points/manage")

# ── [7] No interference with audit log
for needle in ('id="palSection"', 'id="palBody"', "ACTION_LABEL",
               "/api/admin/parent-audit-log"):
    assert needle in hpm, "audit log section regressed: " + needle
print("[7] Existing pal-* audit log section still rendered intact")

# ── [8] Send rejects missing title
with app.app.test_client() as c:
    with c.session_transaction() as s:
        s["user"] = {"id": 1, "username": "admin", "role": "admin"}
    rv = c.post("/api/admin/push/send",
                json={"target_type": "all"})
assert rv.status_code == 400, "missing-title status=" + str(rv.status_code)
print("[8] POST /api/admin/push/send rejects 400 on missing title")

# ── [9] Send rejects bad target_type
with app.app.test_client() as c:
    with c.session_transaction() as s:
        s["user"] = {"id": 1, "username": "admin", "role": "admin"}
    rv = c.post("/api/admin/push/send",
                json={"title": "x", "target_type": "bogus"})
assert rv.status_code == 400, "bad-target status=" + str(rv.status_code)
print("[9] POST /api/admin/push/send rejects 400 on invalid target_type")

# ── [10] Parent flow regression
with app.app.test_client() as c:
    rv = c.get("/parent/legacy?pid=200603680")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
for n in ("pp-pid", "ppBootAutoLookup", "ppSectionOnlyView",
          "function _ppRender", "function loadStoreMenu",
          "function _ppFormatStoreCard", "function requestStoreItem",
          "injectCartButtons", "injectCancelButtons",
          "injectOrderConfirmInterceptor",
          "_mxPushAutoSubscribe", "navigator.serviceWorker.register"):
    assert n in html, "parent flow regression — missing: " + n
print("[10] Parent flow + Phase B/C + PWA + push auto-subscribe "
      "all intact")

print("")
print("All 11 invariants passed.")
