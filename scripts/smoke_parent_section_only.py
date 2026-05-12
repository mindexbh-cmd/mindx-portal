"""Section-only view smoke (v2.8.3).

Verifies the v2.8.3 ppSectionOnlyView IIFE in PARENT_HTML wires up
section isolation when /parent/legacy lands with a #section-*
hash. The actual hiding happens in the browser at runtime, so the
smoke validates:

  • The IIFE source is present in the served HTML.
  • The 5-entry whitelist (KNOWN map) covers all hub anchors.
  • The back-to-hub button construction exists.
  • All 5 anchor IDs the hub deep-links to are in the DOM
    (otherwise the IIFE has nothing to find).
  • The script body still parses cleanly via node (reuses the
    v2.8.2 validator pattern).

Browser-level DOM manipulation (display:none on the right cards)
can only be verified with Playwright — that's the owner's
manual test step.
"""
import os, sys, io, re, subprocess, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

c = A.app.test_client()

# Test 1: /parent/legacy served HTML contains the section-only IIFE
rv = c.get("/parent/legacy")
print(f"[1] GET /parent/legacy -> {rv.status_code}")
assert rv.status_code == 200
html = rv.get_data(as_text=True)

required_snippets = [
    "ppSectionOnlyView",
    "window.location.hash",
    "#section-",
    "section-payment",
    "section-attendance",
    "section-points",
    "section-evaluations",
    "section-books",
    "applySectionOnly",
    "addBackButton",
    "pp-back-btn",
    "/parent",
    "← العودة",
]
for snip in required_snippets:
    assert snip in html, f"section-only IIFE missing snippet {snip!r}"
print(f"[1a] section-only IIFE wired "
      f"({len(required_snippets)} critical snippets present)")

# Test 2: All 5 anchor IDs are in the DOM (section-only logic needs
# them to walk the pp-content children)
for anchor in ("section-payment", "section-attendance",
               "section-points", "section-evaluations",
               "section-books"):
    assert f'id="{anchor}"' in html, \
        f"anchor target #{anchor} missing from legacy page"
print("[2] all 5 anchor targets in DOM")

# Test 3: Confirm existing legacy DOM ids are still preserved
# (the section-only logic must not break the auto-lookup or the
# manual-entry flow)
for legacy_id in ("pp-pid", "pp-go", "pp-lookup-card", "pp-content",
                  "pp-evals-card", "pp-books-card", "ppStoreCard"):
    assert f'id="{legacy_id}"' in html, \
        f"legacy id {legacy_id!r} missing — JS will break"
print("[3] 7 legacy DOM ids preserved")

# Test 4: Both prior IIFEs still wired (auto-lookup + folder
# helper) — section-only is additive, not replacing
for snip in ["ppBootAutoLookup",      # v2.8.1 auto-lookup
             "ppToggleFolder",         # v2.8.2 folder helper
             "URLSearchParams",        # used by auto-lookup
             "_ppStudent",             # poll target
             ]:
    assert snip in html, f"prior wiring lost: {snip!r}"
print("[4] prior IIFEs (auto-lookup + folder helper) preserved")

# Test 5: Script body parses cleanly via node
script_re = re.compile(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>",
                       re.IGNORECASE)
m = script_re.search(html)
assert m, "no <script> block in legacy page"
body = m.group(1)
with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False,
                                 encoding="utf-8") as fp:
    fp.write(body); fp.flush(); path = fp.name
try:
    rv2 = subprocess.run(
        ["node", "-e",
         "try{ new Function(require('fs').readFileSync("
         f"'{path.replace(chr(92), '/')}','utf8')); console.log('OK');"
         "}catch(e){console.log('ERR:'+e.message); process.exit(1);}"],
        capture_output=True, text=True, timeout=30)
    out = (rv2.stdout or "").strip() + (rv2.stderr or "").strip()
    assert rv2.returncode == 0 and "OK" in out, \
        f"PARENT_HTML <script> failed to parse: {out}"
finally:
    try: os.unlink(path)
    except: pass
print("[5] PARENT_HTML <script> parses cleanly via node")

# Test 6: Direct visit (no hash, no pid) — the IIFE early-returns
# (verified by source inspection — the wiring is there, the
# behavior depends on hash being present at browser runtime)
assert "if (!hash || hash.indexOf(&#x27;#section-&#x27;) !== 0) return;" \
    in html or "if (!hash || hash.indexOf('#section-') !== 0) return;" \
    in html, "missing hash guard"
print("[6] hash guard (early-return when no #section-* hash) present")

# Test 7: Whitelist covers exactly 5 sections
known_block_re = re.compile(r"var KNOWN\s*=\s*\{([\s\S]*?)\};")
m = known_block_re.search(html)
assert m, "KNOWN whitelist not found"
known_block = m.group(1)
for sect in ["section-payment", "section-attendance",
             "section-points", "section-evaluations",
             "section-books"]:
    assert f"'{sect}'" in known_block, \
        f"whitelist missing {sect!r}"
print("[7] KNOWN whitelist covers all 5 hub-linkable sections")

# Test 8: The previous /parent hub HTML is untouched (no
# section-only leakage there)
rv = c.get("/parent")
assert rv.status_code == 200
hub = rv.get_data(as_text=True)
assert "ppSectionOnlyView" not in hub, \
    "section-only IIFE leaked into hub HTML"
print("[8] /parent hub untouched (no section-only leakage)")

print("\nParent section-only view smoke passed.")
