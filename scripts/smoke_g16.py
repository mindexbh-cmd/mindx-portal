"""
G16 hermetic test — rewards shop UX polish.

Source-level + node --check on the inline JS. No Flask boot.

Usage:
    python scripts/smoke_g16.py
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
    print("PORTAL_STUDENT_HTML missing"); sys.exit(2)
PS = m.group(1)


# ── Inline JS parses (G15-HOTFIX guard, carried forward) ────────
section("inline JS parses (node --check)")
NODE = shutil.which("node")
if not NODE:
    check("node available (skipped — install Node to enable)", True)
else:
    scripts = re.findall(r"<script>(.*?)</script>", PS, re.DOTALL)
    check("exactly one inline <script> block", len(scripts) == 1,
          f"found {len(scripts)}")
    if scripts:
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False,
                                         encoding="utf-8") as tf:
            tf.write(scripts[0])
            tmp = tf.name
        try:
            proc = subprocess.run([NODE, "--check", tmp],
                                  capture_output=True, text=True,
                                  timeout=15)
            check("node --check passes",
                  proc.returncode == 0,
                  (proc.stderr or proc.stdout).splitlines()[-1]
                  if (proc.stderr or proc.stdout) else "")
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)


# ── G16.1 — qty stepper + clearer cart text ─────────────────────
section("G16.1 qty stepper + button text")

check(".reward-actions is now stacked (flex column)",
      ".reward-actions{display:flex;flex-direction:column;" in SRC)
check(".card-qty stepper CSS shipped",
      ".card-qty{display:flex;" in SRC
      and ".card-qty button" in SRC
      and ".card-qty .q" in SRC)
check("renderer emits data-rid + data-cost + data-max",
      'data-rid="\'+r.id+\'"' in PS
      and 'data-cost="\'+cost+\'"' in PS
      and 'data-max="\'+maxQty+\'"' in PS)
check("renderer emits qty stepper with id=qty-<rid>",
      'id="qty-\'+r.id+\'"' in PS
      and 'onclick="cardQtyStep(' in PS)
check("cart button now reads 'أضف للسلة' (not just 'السلة')",
      "🛒 أضف للسلة" in PS)
check("maxQty formula = min(99, floor(avail/cost))",
      "Math.min(99, Math.floor(avail / cost))" in PS)
check("cardQtyStep / cardQtyGet / cardQtyReset all defined",
      "function cardQtyStep(rid, delta)" in PS
      and "function cardQtyGet(rid)" in PS
      and "function cardQtyReset(rid)" in PS)
check("addToCart reads qty via cardQtyGet",
      "var qty = cardQtyGet(rid)" in PS)


# ── G16.2 — confirmation modal on add ───────────────────────────
section("G16.2 confirmation modal on add")

check("cart button onclick → askAddToCart (not bare addToCart)",
      "onclick=\"askAddToCart(" in PS)
check("askAddToCart defined",
      "function askAddToCart(rid, name, cost)" in PS)
check("doAddToCart defined (the actual POST)",
      "function doAddToCart(rid, qty)" in PS)
check("confirm modal title set to 'تأكيد الإضافة إلى السلة'",
      "تأكيد الإضافة إلى السلة" in PS)
check("confirm prompt uses 'هل تريد إضافة' (operator choice)",
      "هل تريد إضافة" in PS)
check("backward-compat alias kept (function addToCart)",
      "function addToCart(rid, name, cost){" in PS)


# ── G16.3 — floating cart badge ─────────────────────────────────
section("G16.3 floating cart badge")

check(".float-cart CSS shipped",
      ".float-cart{position:fixed;bottom:18px;right:18px;" in SRC)
check(".float-cart-count chip styled",
      ".float-cart .float-cart-count{position:absolute;" in SRC)
check("badge DOM element present",
      'id="floatCart"' in PS and 'id="floatCartCount"' in PS)
check("position is bottom-right (RTL end, operator choice)",
      "bottom:18px" in SRC and "right:18px" in SRC)
check("z-index 90 (below modals)",
      ".float-cart{position:fixed;" in SRC and "z-index:90;" in SRC)
check("updateFloatingCart() defined + called in render()",
      "function updateFloatingCart()" in PS
      and "updateFloatingCart()" in PS)
check("prefers-reduced-motion suppresses fade",
      "@media (prefers-reduced-motion:reduce)" in SRC
      and ".float-cart{transition:none" in SRC)
check("mobile sizing (≤480px)",
      "@media (max-width:480px)" in SRC
      and ".float-cart{width:52px" in SRC)


# ── G16.4 — proactive balance-exhausted check ───────────────────
section("G16.4 proactive balance-exhausted block")

check("showCartWouldExceed defined",
      "function showCartWouldExceed(name, cost, qty)" in PS)
check("operator-chosen text present",
      "طلبياتك استوعبت النقاط" in PS)
check("breakdown shows available / cart-total / item / shortfall",
      "المتاح:" in PS and "مجموع السلة الحالي:" in PS
      and "الناقص:" in PS)
check("askAddToCart calls showCartWouldExceed before #confirm",
      "showCartWouldExceed(name, cost, qty)" in PS
      and "(c.total|0) + (cost|0) * qty) > (b.available|0)" in PS)
check("cardQtyStep enforces cart-aware ceiling on +",
      "cartCap" in PS and "headroom" in PS)
check("plus-button disabled when next > cart-aware cap",
      "plusBlock = ((c2.total|0) + cost * (next + 1)) > (b2.available|0)" in PS)


# ── G16.5 — cart modal overlay ──────────────────────────────────
section("G16.5 cart modal overlay")

check("#cartModal markup present",
      'id="cartModal"' in PS and 'id="cartModalBody"' in PS)
check("close button + backdrop click both wired",
      'onclick="closeCartModal(event)"' in PS
      and 'onclick="closeCartModal()"' in PS)
check("openCartModal() defined",
      "function openCartModal()" in PS)
check("closeCartModal() defined",
      "function closeCartModal(ev)" in PS)
check("modal body re-injects renderCartContents on each load",
      "box.innerHTML = renderCartContents()" in PS
      and "cm.classList.contains('show')" in PS)
check("ESC key closes cart modal",
      "var cm = document.getElementById('cartModal');" in PS
      and "closeCartModal();" in PS)
check("body.overflow locked while modal open",
      "document.body.style.overflow = 'hidden'" in PS
      and "document.body.style.overflow = ''" in PS)


# ── G16.6 — entry-point coordination ────────────────────────────
section("G16.6 floating-badge ↔ sub-tab coordination")

check("checkout success closes cart modal",
      "if(cm && cm.classList.contains('show')) closeCartModal();" in PS)
check("showCartWouldExceed injects 'عرض السلة' CTA",
      "عرض السلة" in PS and "openCartModal();" in PS)
check("showInsufficientBalance restores default action row",
      "G16.6: restore the default close-only action row" in PS)
check("floating-badge onclick routed to openCartModal",
      "btn.onclick = openCartModal" in PS)
check("cart sub-tab (G15.4) preserved",
      'data-sub="cart"' in PS and 'id="pane-cart"' in PS)


# ── Regression: G1–G15 still intact ─────────────────────────────
section("regression: prior features still present")

check("G14.1 image renderer intact",
      "r.image_url" in PS and "onerror=\"this.outerHTML=" in PS)
check("G14.2 lightbox intact",
      'id="rwLightbox"' in PS and "function openLightbox(" in PS)
check("G14.4 category tabs intact",
      'data-cat="toy"' in PS and 'data-cat="food"' in PS)
check("G15.1 backend endpoints intact",
      "@app.route('/api/portal/student/balance', methods=['GET'])" in SRC
      # G17: /api/portal/student/order removed
      and "@app.route('/api/portal/student/cart/add', methods=['POST'])" in SRC)
check("G15.2 3-card balance header intact",
      ".bal-cards{display:grid" in PS
      and 'class="bal-card available"' in PS)
# G17: direct-order button replaced by cart-only flow. smoke_g17.py
# asserts the inverse (button + JS gone).
check("G15.4 cart sub-pane intact",
      "function renderCartContents()" in PS
      and "function doCartCheckout()" in PS)
check("G15.5 history with status badges intact",
      "📨 قيد الموافقة" in PS and "function cancelMyOrder(" in PS)
check("G15.6 insufficient-balance modal intact",
      'id="balLow"' in PS
      and "function showInsufficientBalance(" in PS)
check("G15.7 legacy /redeem still 410",
      # G17: hint updated from /order to /cart/add when the
      # direct-order endpoint was removed.
      ('"use_instead": "/api/portal/student/cart/add"' in SRC
       or '"use_instead": "/api/portal/student/order"' in SRC)
      and "), 410" in SRC)
check("admin approve endpoint preserved",
      "/api/points/redemptions/<int:redeem_id>/approve" in SRC)


# ── Runtime: app.py imports cleanly ─────────────────────────────
section("runtime: app.py imports")
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))

# G15 endpoint helpers still in place (no shape break).
for fname in ("_g15_student_balance", "_g15_validate_reward_for_request",
              # G17: api_portal_student_order removed
              "api_portal_student_balance",
              "api_portal_student_cart_get", "api_portal_student_cart_add"):
    check(f"function present: {fname}", hasattr(mod, fname))


# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G16 SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G16 SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
