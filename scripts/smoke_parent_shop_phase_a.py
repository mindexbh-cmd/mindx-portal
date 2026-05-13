"""Smoke test — Parent shop Phase A (v2.9.8).

Invariants:
  [1] app.py imports without raising
  [2] GET /parent/legacy responds 200 (no pid, just the
      landing form — page must still render)
  [3] CSS: .pp-store-img img uses object-fit:contain (the C2 fix)
  [4] Modal HTML present (#prizeZoomBack, #prizeZoomImg,
      #prizeZoomTitle, button.prize-zoom-close)
  [5] window.openPrizeZoom and window.closePrizeZoom each defined
      exactly once in PARENT_HTML
  [6] Card renderer wires onclick="openPrizeZoom(this.src,...)"
      on every prize image
  [7] _ppFormatStoreCard still sets disabled=true when
      balance < cost (server-stays-source-of-truth regression
      guard) AND requestStoreItem has the new client-side guard
  [8] PARENT_HTML serves cleanly via the test client (200, has
      the section-points anchor)
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

with open(os.path.join(ROOT, "app.py"), "r", encoding="utf-8") as fh:
    SRC = fh.read()

# ── 1
import app  # noqa: E402,F401
print("[1] app.py imports without raising")

# ── 2 + 8: /parent/legacy renders
with app.app.test_client() as c:
    rv = c.get("/parent/legacy")
assert rv.status_code == 200, ("/parent/legacy returned "
                                + str(rv.status_code))
html = rv.get_data(as_text=True)
assert 'id="section-points"' in html, (
    "section-points anchor missing from rendered /parent/legacy")
print("[2] GET /parent/legacy -> 200")
print("[8] /parent/legacy HTML contains #section-points anchor")

# ── 3: object-fit:contain on prize images
assert re.search(r"\.pp-store-img\s+img\s*\{[^}]*object-fit:\s*contain",
                 SRC), (
    ".pp-store-img img CSS does not declare object-fit:contain")
print("[3] .pp-store-img img uses object-fit:contain")

# ── 4: zoom modal HTML
required_modal = [
    'id="prizeZoomBack"',
    'id="prizeZoomImg"',
    'id="prizeZoomTitle"',
    'class="prize-zoom-close"',
]
missing = [m for m in required_modal if m not in SRC]
assert not missing, "zoom modal markup missing: " + str(missing)
print("[4] prizeZoomBack modal HTML present")

# ── 5: openPrizeZoom + closePrizeZoom defined exactly once
for name in ("openPrizeZoom", "closePrizeZoom"):
    pat = re.compile(r"window\." + re.escape(name)
                     + r"\s*=\s*function")
    matches = pat.findall(SRC)
    assert len(matches) == 1, (
        "window." + name + " defined " + str(len(matches))
        + " times (expected 1)")
print("[5] window.openPrizeZoom + window.closePrizeZoom each "
      "defined exactly once")

# ── 6: onclick wires on the renderer's img tag
assert 'onclick="openPrizeZoom(this.src,' in SRC, (
    "prize image renderer doesn't emit "
    "onclick=\"openPrizeZoom(this.src,...)\"")
print("[6] _ppFormatStoreCard emits onclick=\"openPrizeZoom(...)\"")

# ── 7: card-render disabled-when-insufficient + new POST guard
assert "balance < cost" in SRC, (
    "renderer's 'balance < cost' disable branch removed — "
    "Phase A regression")
assert "نقاطك غير كافية" in SRC, (
    "Arabic insufficient-points message disappeared from source")
# The new requestStoreItem guard checks _ppStoreState.balance
rsi_idx = SRC.index("function requestStoreItem(rewardId)")
rsi_body = SRC[rsi_idx:rsi_idx + 2500]
assert "_ppStoreState" in rsi_body and "balance" in rsi_body, (
    "requestStoreItem missing client-side balance-vs-cost guard")
print("[7] Card renderer disables when balance < cost AND "
      "requestStoreItem has client-side guard")

print("")
print("All 8 invariants passed.")
