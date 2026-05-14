"""Smoke test — TWA assetlinks endpoint (v3.3-twa-ready).

Invariants:
  [1]  GET /.well-known/assetlinks.json returns 200 with
       Content-Type: application/json.
  [2]  With TWA_SHA256_FINGERPRINT unset, returns [] (empty array).
  [3]  With a single fingerprint, returns a statement using the
       default package 'com.mindex.portal' and the fingerprint in
       sha256_cert_fingerprints.
  [4]  With comma-separated fingerprints, returns one statement
       with ALL fingerprints listed (key rotation support).
  [5]  With TWA_PACKAGE_NAME set, overrides the default package.
  [6]  Stray whitespace + trailing comma in env var is tolerated
       (no spurious empty fingerprint entries).
  [7]  Response headers include Cache-Control + Content-Type.
  [8]  Parent flow + /points/manage + manifest + sw.js all still
       work (regression guard).
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

# Clean env around our env-var tests
for k in ("TWA_SHA256_FINGERPRINT", "TWA_PACKAGE_NAME"):
    os.environ.pop(k, None)

import app  # noqa: E402

# ── [1] route registered + returns 200 with JSON content-type
with app.app.test_client() as c:
    rv = c.get("/.well-known/assetlinks.json")
assert rv.status_code == 200, "status=" + str(rv.status_code)
ct = rv.headers.get("Content-Type", "")
assert "application/json" in ct, "wrong CT: " + ct
print("[1] GET /.well-known/assetlinks.json -> 200 application/json")

# ── [2] env unset → []
data = json.loads(rv.get_data(as_text=True))
assert data == [], "expected [] when env unset, got: " + repr(data)
print("[2] Unset env -> [] (empty array)")

# ── [3] single fingerprint
TEST_FP = ("AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89:"
           "AB:CD:EF:01:23:45:67:89:AB:CD:EF:01:23:45:67:89")
os.environ["TWA_SHA256_FINGERPRINT"] = TEST_FP
with app.app.test_client() as c:
    rv = c.get("/.well-known/assetlinks.json")
data = json.loads(rv.get_data(as_text=True))
assert isinstance(data, list) and len(data) == 1
stmt = data[0]
assert "delegate_permission/common.handle_all_urls" in stmt["relation"]
assert stmt["target"]["namespace"] == "android_app"
assert stmt["target"]["package_name"] == "com.mindex.portal"
assert stmt["target"]["sha256_cert_fingerprints"] == [TEST_FP]
print("[3] Single fingerprint -> statement with default package "
      "com.mindex.portal")

# ── [4] comma-separated fingerprints (key rotation)
FP2 = ("11:22:33:44:55:66:77:88:11:22:33:44:55:66:77:88:"
       "11:22:33:44:55:66:77:88:11:22:33:44:55:66:77:88")
os.environ["TWA_SHA256_FINGERPRINT"] = TEST_FP + "," + FP2
with app.app.test_client() as c:
    rv = c.get("/.well-known/assetlinks.json")
data = json.loads(rv.get_data(as_text=True))
assert (data[0]["target"]["sha256_cert_fingerprints"]
        == [TEST_FP, FP2])
print("[4] Comma-separated fingerprints -> both listed in one statement")

# ── [5] custom package name
os.environ["TWA_PACKAGE_NAME"] = "com.mindex.portal.staging"
os.environ["TWA_SHA256_FINGERPRINT"] = TEST_FP
with app.app.test_client() as c:
    rv = c.get("/.well-known/assetlinks.json")
data = json.loads(rv.get_data(as_text=True))
assert data[0]["target"]["package_name"] == "com.mindex.portal.staging"
print("[5] TWA_PACKAGE_NAME env overrides default")

# ── [6] tolerate stray whitespace / trailing commas
os.environ["TWA_PACKAGE_NAME"] = "com.mindex.portal"
os.environ["TWA_SHA256_FINGERPRINT"] = "  " + TEST_FP + " ,, ," + FP2 + ",  "
with app.app.test_client() as c:
    rv = c.get("/.well-known/assetlinks.json")
data = json.loads(rv.get_data(as_text=True))
fps = data[0]["target"]["sha256_cert_fingerprints"]
assert fps == [TEST_FP, FP2], "got: " + repr(fps)
print("[6] Whitespace + trailing/repeated commas tolerated")

# ── [7] Cache-Control header
assert "max-age" in (rv.headers.get("Cache-Control") or "")
print("[7] Cache-Control header set")

# Clean env
for k in ("TWA_SHA256_FINGERPRINT", "TWA_PACKAGE_NAME"):
    os.environ.pop(k, None)

# ── [8] Regression — parent flow + /points/manage + manifest + sw.js
with app.app.test_client() as c:
    rv = c.get("/parent/legacy?pid=200603680")
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    for n in ("ppBootAutoLookup", "function _ppRender",
              "function _ppFormatStoreCard",
              "navigator.serviceWorker.register"):
        assert n in html, "regression: " + n
    with c.session_transaction() as s:
        s["user"] = {"id": 1, "username": "admin", "role": "admin"}
    rv = c.get("/points/manage")
    assert rv.status_code == 200
    rv = c.get("/manifest.json")
    assert rv.status_code == 200
    rv = c.get("/sw.js")
    assert rv.status_code == 200
print("[8] Parent flow + /points/manage + manifest + sw.js all "
      "still respond 200")

print("")
print("All 8 invariants passed.")
