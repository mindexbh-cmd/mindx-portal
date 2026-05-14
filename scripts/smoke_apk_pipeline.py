"""Smoke test — APK CI pipeline (v3.4-apk-pipeline).

This is a STATIC smoke (no `act` / no actual workflow run). It
validates the three checked-in artifacts that the workflow
depends on:

  [1]  twa-manifest.json parses + has Bubblewrap-required fields
       (packageId, host, name, themeColor, startUrl, signingKey,
        iconUrl, maskableIconUrl, webManifestUrl).
  [2]  packageId matches the canonical com.mindex.portal that
       /.well-known/assetlinks.json defaults to.
  [3]  Icon URLs in twa-manifest.json point at real /static/icons/
       files that the Flask static handler can serve.
  [4]  .github/workflows/build-apk.yml is valid YAML.
  [5]  Workflow references all 4 required secrets (sets of
       env: blocks must be a superset).
  [6]  Workflow has the fail-fast secret-check step (the docs
       depend on this for the helpful error message).
  [7]  Workflow's path filter includes twa-manifest.json so a
       config change actually triggers a rebuild.
  [8]  docs/APK_BUILD.md exists and references all 4 secret names
       so the owner-facing instructions stay in sync with the
       workflow.
  [9]  App still imports + /parent/legacy renders (regression
       guard — pipeline changes shouldn't touch the runtime).
"""
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

TWA = os.path.join(ROOT, "twa-manifest.json")
WF  = os.path.join(ROOT, ".github", "workflows", "build-apk.yml")
DOC = os.path.join(ROOT, "docs", "APK_BUILD.md")

# ── [1] twa-manifest.json fields
with open(TWA, "r", encoding="utf-8") as fh:
    twa = json.load(fh)
required = ("packageId", "host", "name", "themeColor", "startUrl",
            "signingKey", "iconUrl", "maskableIconUrl",
            "webManifestUrl")
for k in required:
    assert k in twa, "twa-manifest missing field: " + k
print("[1] twa-manifest.json has all required Bubblewrap fields")

# ── [2] packageId canonical match
assert twa["packageId"] == "com.mindex.portal", (
    "packageId mismatch: " + twa["packageId"])
print("[2] packageId == com.mindex.portal "
      "(matches assetlinks.json default)")

# ── [3] Icon URLs point at real /static/icons/ files
for key in ("iconUrl", "maskableIconUrl", "monochromeIconUrl"):
    url = twa.get(key, "")
    if not url: continue
    # Pull the path component
    m = re.search(r"(/static/icons/[^?#]+)", url)
    assert m, key + " doesn't reference /static/icons/: " + url
    path = os.path.join(ROOT, m.group(1).lstrip("/"))
    assert os.path.isfile(path), (
        "icon file missing on disk: " + path)
print("[3] iconUrl / maskableIconUrl / monochromeIconUrl all "
      "resolve to real /static/icons/ files")

# ── [4] Workflow YAML parses
import yaml
with open(WF, "r", encoding="utf-8") as fh:
    wf_yaml = fh.read()
wf = yaml.safe_load(wf_yaml)
assert wf and "jobs" in wf, "workflow YAML didn't parse"
print("[4] .github/workflows/build-apk.yml is valid YAML")

# ── [5] All 4 secrets referenced
needed_secrets = ("ANDROID_KEYSTORE_BASE64",
                  "ANDROID_KEYSTORE_PASSWORD",
                  "ANDROID_KEY_ALIAS",
                  "ANDROID_KEY_PASSWORD")
for sec in needed_secrets:
    assert "secrets." + sec in wf_yaml, (
        "workflow doesn't reference secret: " + sec)
print("[5] Workflow references all 4 ANDROID_* secrets")

# ── [6] Fail-fast secret-check step present
assert "Fail fast if signing secrets are missing" in wf_yaml, (
    "fail-fast secret-check step missing")
assert "Missing required GitHub Actions secrets" in wf_yaml
print("[6] Fail-fast secret-check step present")

# ── [7] Path filter includes twa-manifest.json
build = wf.get("jobs", {}).get("build", {})
# `on:` parses to True in some PyYAML versions (it's a YAML
# boolean-y key). Pull from raw source.
assert "twa-manifest.json" in wf_yaml, (
    "twa-manifest.json missing from workflow paths filter")
assert "static/icons/**" in wf_yaml, (
    "static/icons/** missing from paths filter")
print("[7] Push trigger paths filter covers manifest + icons")

# ── [8] Docs reference every secret name + the trigger steps
with open(DOC, "r", encoding="utf-8") as fh:
    docs = fh.read()
for sec in needed_secrets:
    assert sec in docs, "docs missing secret name: " + sec
for marker in ("keytool -genkeypair", "ToBase64String",
               "Run workflow", "TWA_SHA256_FINGERPRINT",
               "Render"):
    assert marker in docs, "docs missing instruction marker: " + marker
print("[8] docs/APK_BUILD.md references all 4 secrets + key "
      "instruction markers")

# ── [9] App regression — pipeline changes shouldn't touch runtime
import app  # noqa: E402
with app.app.test_client() as c:
    rv = c.get("/parent/legacy?pid=200603680")
assert rv.status_code == 200, "regression: /parent/legacy " + str(rv.status_code)
html = rv.get_data(as_text=True)
for n in ("ppBootAutoLookup", "function _ppRender",
          "function _ppFormatStoreCard",
          "navigator.serviceWorker.register"):
    assert n in html, "regression: " + n
# Plus assetlinks endpoint still works
with app.app.test_client() as c:
    rv = c.get("/.well-known/assetlinks.json")
assert rv.status_code == 200
print("[9] App + parent boot + assetlinks endpoint all intact")

print("")
print("All 9 invariants passed.")
