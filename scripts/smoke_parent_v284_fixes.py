"""v2.8.4 smoke — 3 owner-reported fixes on the parent hub.

[1] ppStoreCard hidden on non-points sections — verifies the
    pp-section-only-hide <style> rule is emitted by the IIFE
    (injected with !important to survive loadStoreMenu race).

[2] Back-button preserves PID — verifies the IIFE constructs
    href from window.location.search.

[3] Hub topbar no longer contains the 'للموقع الرئيسي' link.

[4] Hub auto-rehydrates from ?pid= so the back nav returns to
    a populated hub.

[5] Existing parent smokes still green (no regression).
"""
import os, sys, io, re, subprocess, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()

# Test 1: legacy page contains the injectHideRules logic + IDs
rv = c.get("/parent/legacy")
print(f"[1] GET /parent/legacy -> {rv.status_code}")
assert rv.status_code == 200
html = rv.get_data(as_text=True)
for snip in [
    "injectHideRules",
    "pp-section-only-hide",
    "display:none !important",
    "'pp-evals-card'",
    "'pp-books-card'",
    "'ppStoreCard'",
    "'section-evaluations'",
    "'section-books'",
    "'section-points'",
]:
    assert snip in html, f"injectHideRules wiring missing: {snip!r}"
print("[1a] injectHideRules wired with all 3 explicit cards + sections")

# Test 2: back button reads ?pid from window.location.search
for snip in [
    "URLSearchParams(window.location.search)",
    ".get('pid')",
    "/parent?pid=",
    "encodeURIComponent(backPid)",
]:
    assert snip in html, f"back-button PID logic missing: {snip!r}"
print("[2a] back button preserves PID via URLSearchParams")

# Test 3: hub no longer contains the topbar link
rv = c.get("/parent")
assert rv.status_code == 200
hub = rv.get_data(as_text=True)
assert "للموقع الرئيسي" not in hub, \
    "topbar link 'للموقع الرئيسي' should have been removed"
assert "<a href=\"/\">" not in hub, \
    "topbar still has <a href=\"/\"> tag"
print("[3a] hub topbar link removed")
# Topbar h1 still present
assert "🏠 منصة ولي الأمر — مايندكس" in hub
print("[3b] hub topbar h1 preserved")

# Test 4: hub auto-rehydrates from ?pid=
for snip in [
    "phBootFromUrl",
    "URLSearchParams(window.location.search)",
    "urlPid",
    "phLookup();",
]:
    assert snip in hub, f"hub rehydrate logic missing: {snip!r}"
print("[4a] hub phBootFromUrl IIFE wired")

# Test 5: PARENT_HTML script still parses cleanly via node
script_re = re.compile(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>",
                       re.IGNORECASE)
for label, response_html in [("PARENT_HTML", html), ("HUB_HTML", hub)]:
    m = script_re.search(response_html)
    assert m, f"no <script> in {label}"
    body = m.group(1)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js",
                                     delete=False,
                                     encoding="utf-8") as fp:
        fp.write(body); fp.flush(); path = fp.name
    try:
        rv2 = subprocess.run(
            ["node", "-e",
             "try{ new Function(require('fs').readFileSync("
             f"'{path.replace(chr(92), '/')}','utf8')); "
             "console.log('OK'); }catch(e){"
             "console.log('ERR:'+e.message); process.exit(1);}"],
            capture_output=True, text=True, timeout=30)
        out = (rv2.stdout or "").strip() + (rv2.stderr or "").strip()
        assert rv2.returncode == 0 and "OK" in out, \
            f"{label} <script> failed to parse: {out}"
    finally:
        try: os.unlink(path)
        except: pass
    print(f"[5] {label} <script> parses cleanly")

# Test 6: existing wiring still intact (regression guard)
for snip in ["ppBootAutoLookup", "ppToggleFolder",
             "ppSectionOnlyView"]:
    assert snip in html, f"prior IIFE lost: {snip!r}"
print("[6] all 3 prior IIFEs preserved (no regression)")

# Test 7: back button href falls back to /parent when no PID
# (verified by the ternary in the source — fallback path exists)
assert re.search(r"a\.href\s*=\s*backPid\s*\?", html), \
    "missing back-button ternary"
assert "'/parent?pid='" in html, "missing PID-preserving branch"
assert "/parent';" in html, "missing /parent fallback"
print("[7] back button falls back to /parent when no PID present")

print("\nv2.8.4 fixes smoke passed.")
