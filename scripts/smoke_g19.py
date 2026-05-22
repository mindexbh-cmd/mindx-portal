"""
G19 hermetic test — balance display reverted to single number.

Source-level + node --check on the inline JS. Confirms:
- 3-card markup (G15.2) removed
- Original .pts + .ptslbl headline restored
- countUp targets #balCount and animates STATE.balance.available
- /api/portal/student/balance endpoint + STATE.balance still wired
  (cart flow + G15.6 + G16.4 keep gating on .available)
- G15–G18 cart / modal / floating-badge surfaces preserved

Usage:
    python scripts/smoke_g19.py
"""

import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PY = ROOT / "app.py"
SRC = APP_PY.read_text(encoding="utf-8")

failed = []


def check(label, ok, hint=""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok:
        if hint:
            print(f"         hint: {hint}")
        failed.append(label)
    return bool(ok)


def section(title):
    print(f"\n=== {title} ===")


m = re.search(r'PORTAL_STUDENT_HTML = r"""(.*?)"""', SRC, re.DOTALL)
if not m:
    print("PORTAL_STUDENT_HTML missing")
    sys.exit(2)
PS = m.group(1)


# ── Inline JS parses (G15-HOTFIX guard) ─────────────────────────
section("inline JS parses (node --check)")
NODE = shutil.which("node")
if NODE:
    scripts = re.findall(r"<script>(.*?)</script>", PS, re.DOTALL)
    check("exactly one inline <script>", len(scripts) == 1)
    if scripts:
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False,
                                         encoding="utf-8") as tf:
            tf.write(scripts[0])
            tmp = tf.name
        try:
            proc = subprocess.run([NODE, "--check", tmp],
                                  capture_output=True, text=True, timeout=15)
            check("node --check passes",
                  proc.returncode == 0,
                  (proc.stderr or proc.stdout).splitlines()[-1]
                  if (proc.stderr or proc.stdout) else "")
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)
else:
    check("node available (skipped)", True)


# ── G19.2: 3-card balance REMOVED ───────────────────────────────
section("G19.2 3-card balance markup removed")

# CSS deletions
check(".bal-cards CSS gone",
      ".bal-cards{display:grid" not in SRC)
check(".bal-card.total CSS gone",
      ".bal-card.total" not in SRC)
check(".bal-card.reserved CSS gone",
      ".bal-card.reserved" not in SRC)
check(".bal-card.available CSS gone",
      ".bal-card.available" not in SRC)

# DOM ids gone
check('id="balTotal" not emitted', 'id="balTotal"' not in PS)
check('id="balReserved" not emitted', 'id="balReserved"' not in PS)
check('id="balAvail" not emitted', 'id="balAvail"' not in PS)

# Renderer no longer emits the 3-card grid
check("renderer emits no class=\"bal-card …\"",
      'class="bal-card' not in PS)


# ── G19.2: single-number .pts hero restored ─────────────────────
section("G19.2 single-number .pts headline restored")

check(".pts CSS still in place (was never deleted)",
      ".hero .pts{font-size:4rem" in SRC)
check(".ptslbl CSS still in place",
      ".hero .ptslbl{" in SRC)
check("renderer emits <div class=\"pts\" id=\"balCount\">",
      'class="pts" id="balCount"' in PS)
check("renderer emits <div class=\"ptslbl\">نقطة",
      'class="ptslbl">نقطة' in PS)
check("countUp animates balCount",
      "countUp('balCount'" in PS)
# G20d.1: countUp now animates (total-committed), not .available.
# The named-var changed from `bavail` to `_headlineNum`. Both legacy
# names accepted here so the smoke suite stays stable across this
# semantics change.
check("countUp animates a balance number on #balCount",
      "countUp('balCount', _headlineNum," in PS
      or "countUp('balCount', bavail," in PS)


# ── STATE.balance + endpoint preserved ──────────────────────────
section("STATE.balance + /balance endpoint preserved")

check("/api/portal/student/balance endpoint still registered",
      "@app.route('/api/portal/student/balance', methods=['GET'])" in SRC)
check("def api_portal_student_balance still defined",
      "def api_portal_student_balance():" in SRC)
check("renderer still fetches /balance in load() Promise.all",
      "/api/portal/student/balance" in PS
      and "STATE.balance" in PS)
check("STATE.balance fallback shape preserved",
      "{total:bal, committed:0, reserved:0, available:bal}" in PS)
# G20d.1 retired this assertion: the headline now reads (b.total -
# b.committed) instead of b.available, per operator's clarified model
# (only approved/delivered should reduce the displayed number; pending
# requests shouldn't). The internal gates (cart-checkout backend,
# G16.4 proactive check, G20b.1 shading) still use b.available; only
# the headline consumer changed. smoke_g20d.py owns that assertion.
check("renderer reads a balance field for headline",
      "b.total" in PS and "b.committed" in PS)


# ── G15.6 / G16.4 still gate on STATE.balance.available ─────────
section("dependent surfaces still gate on available")

check("G15.6 showInsufficientBalance still defined",
      "function showInsufficientBalance(available, needed)" in PS)
check("G16.4 showCartWouldExceed still defined",
      "function showCartWouldExceed(name, cost, qty)" in PS)
check("G16.4 reads STATE.balance.available",
      "b.available|0" in PS)
check("G16.4 reads STATE.cart.total for cart-aware check",
      "(c.total|0) + (cost|0) * qty" in PS)


# ── Regression: G14–G18 surfaces preserved ──────────────────────
section("regression: prior surfaces still present")

check("G14.1 reward image renderer intact",
      "r.image_url" in PS and "onerror=\"this.outerHTML=" in PS)
check("G14.2 lightbox intact",
      'id="rwLightbox"' in PS)
check("G14.4 category tabs intact",
      'data-cat="toy"' in PS and 'data-cat="food"' in PS)
check("G14.6 sub-tab scaffolding intact",
      "function setRewardsTab(name)" in PS
      and 'id="pane-shop"' in PS and 'id="pane-history"' in PS)
check("G15.4 cart sub-tab + functions intact",
      'data-sub="cart"' in PS
      and "function renderCartContents()" in PS
      and "function doCartCheckout()" in PS)
check("G15.5 history badges + cancel intact",
      "📨 قيد الموافقة" in PS and "function cancelMyOrder(" in PS)
check("G15.6 #balLow modal intact",
      'id="balLow"' in PS)
check("G15.7 legacy /redeem still 410",
      "), 410" in SRC and "endpoint deprecated" in SRC)
check("G16.1 qty stepper intact",
      ".card-qty{display:flex" in SRC
      and "function cardQtyStep(rid, delta)" in PS)
check("G16.2 confirm modal on add intact",
      "function askAddToCart(rid, name, cost)" in PS
      and "function doAddToCart(rid, qty)" in PS)
check("G16.3 floating cart badge intact",
      'id="floatCart"' in PS and "function updateFloatingCart()" in PS)
check("G16.5 cart modal intact",
      'id="cartModal"' in PS and "function openCartModal()" in PS)
check("G17 direct-order removal still in effect",
      "⚡ طلب مباشر" not in PS
      and "function askDirectOrder(" not in PS
      and "@app.route('/api/portal/student/order'" not in SRC)


# ── Runtime ─────────────────────────────────────────────────────
section("runtime: app.py imports cleanly")
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))

# Balance endpoint still callable.
try:
    rules = list(mod.app.url_map.iter_rules())
    bal = [str(r) for r in rules
           if str(r) == "/api/portal/student/balance"]
    check(f"/balance still in url_map (got {len(bal)})", len(bal) == 1)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G19 SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G19 SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
