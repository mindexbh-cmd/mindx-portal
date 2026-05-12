"""Legacy auto-lookup smoke (v2.8 hotfix).

Verifies that PARENT_HTML carries the ppBootAutoLookup IIFE so the
hub's /parent/legacy?pid=…#anchor deep-link flow no longer makes
parents re-enter their PID after they typed it into the hub.

Three scenarios:

[1] GET /parent/legacy             — manual PID input form rendered;
                                      auto-lookup wiring present but
                                      inert (no ?pid in URL).
[2] GET /parent/legacy?pid=<valid> — same HTML response (server-side
                                      is identical) but verify the
                                      JS reads URLSearchParams + calls
                                      ppLookup() + scrolls to hash.
[3] GET /parent/legacy?pid=<valid>#section-payment — same HTML; we
                                      can't browser-test the actual
                                      scroll but verify the anchor
                                      target (sibling <span> with
                                      id=section-payment) is in DOM.

Server side returns identical HTML regardless of ?pid — the new
logic runs client-side in the browser. So all three assertions are
made against the same response body.
"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()

# Scenario 1: no PID → lookup form rendered, wiring inert
rv = c.get("/parent/legacy")
print(f"[1] GET /parent/legacy -> {rv.status_code}")
assert rv.status_code == 200
html = rv.get_data(as_text=True)

# The manual PID input form must still be present
assert 'id="pp-pid"' in html, "manual PID input field missing"
assert 'id="pp-go"' in html, "manual lookup button missing"
assert 'onclick="ppLookup()"' in html, \
    "manual lookup onclick handler missing"
print("[1a] manual PID entry form preserved (id=pp-pid + onclick=ppLookup)")

# Scenario 2: auto-lookup IIFE must be wired in the served HTML
required_snippets = [
    "ppBootAutoLookup",
    "URLSearchParams",
    "params.get('pid')",
    "if (typeof ppLookup !== 'function') return;",
    "ppLookup();",
    "_ppStudent",
    "scrollIntoView",
]
for snip in required_snippets:
    assert snip in html, f"PARENT_HTML missing auto-lookup snippet {snip!r}"
print("[2a] auto-lookup IIFE wired (7 critical snippets present)")

# Scenario 3: anchor targets must be in DOM (so the smooth scroll
# from the IIFE has somewhere to land)
for anchor in ("section-payment", "section-attendance",
               "section-points", "section-evaluations",
               "section-books"):
    assert f'id="{anchor}"' in html, \
        f"anchor target #{anchor} missing from legacy page"
print("[3a] all 5 anchor targets in DOM")

# Scenario 4: original DOM ids preserved (existing JS relies on these)
for legacy_id in ("ppStoreCard", "pp-evals-card", "pp-books-card",
                  "pp-lookup-card", "pp-info-rows", "pp-go"):
    assert f'id="{legacy_id}"' in html, \
        f"legacy DOM id {legacy_id!r} missing — existing JS will break"
print("[3b] 6 legacy DOM ids preserved (no regression on existing JS)")

# Scenario 5: query-string variants don't break server response
# (server-side identical, but ensure the route handler doesn't
# choke on the extra query param)
for path in ["/parent/legacy?pid=150710640",
             "/parent/legacy?pid=150710640&foo=bar",
             "/parent/legacy?pid="]:
    rv = c.get(path)
    assert rv.status_code == 200, \
        f"unexpected status {rv.status_code} for {path}"
print("[5] route accepts ?pid= variants without breaking")

# Scenario 6: /parent (hub) still ships untouched
rv = c.get("/parent")
assert rv.status_code == 200
hub = rv.get_data(as_text=True)
assert "lookup-card" in hub
assert "ppBootAutoLookup" not in hub, \
    "hub HTML must NOT carry the legacy autolookup IIFE"
print("[6] /parent hub untouched (no autolookup leakage)")

print("\nParent legacy auto-lookup smoke passed.")
