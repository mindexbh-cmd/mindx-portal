"""
G17 hermetic test — direct-order surface fully removed.

Asserts the deletions stuck (button, JS, route, endpoint) AND the
cart flow survived. Plus node --check on the inline JS (G15-HOTFIX
guard) and the runtime check that Flask has 0 routes matching the
removed path.

Usage:
    python scripts/smoke_g17.py
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


# ── G17.1: frontend removal ─────────────────────────────────────
section("G17.1 frontend direct-order surface GONE")

# Operator-visible text gone (substring matching is fine — this
# string can only appear in user-facing UI strings).
check("PORTAL_STUDENT_HTML: no '⚡ طلب مباشر' user-visible text",
      "⚡ طلب مباشر" not in PS)

# Function definitions gone. Use the exact `function NAME(` shape
# so the removal-explanation comment (which mentions the names in
# prose) doesn't false-positive.
check("askDirectOrder function NOT defined",
      "function askDirectOrder(" not in PS)
check("doDirectOrder function NOT defined",
      "function doDirectOrder(" not in PS)

# Button class name gone from any actual markup. CSS rule comments
# may still reference 'btn-order' in removal-explanation text — that
# doesn't render. Check for the actual class usage.
check("PORTAL_STUDENT_HTML: no class=\"btn btn-order\" anywhere",
      'class="btn btn-order"' not in PS)
check("PORTAL_STUDENT_HTML: no fetch to /api/portal/student/order",
      "/api/portal/student/order'," not in PS
      and "/api/portal/student/order\"" not in PS)
check("canOrder local var gone from renderer",
      "var canOrder" not in PS)

# .btn-order CSS rules deleted (only the removal-explanation comment
# may mention the name in prose).
check(".btn-order CSS rules removed",
      ".btn-order{background:" not in SRC
      and ".btn-order:hover" not in SRC
      and ".btn-cart:disabled,.btn-order:disabled" not in SRC)

# .btn-row CSS for the reward grid removed (was a 2-col layout for
# the two-button row that no longer exists).
check(".reward-actions .btn-row CSS removed",
      ".reward-actions .btn-row{display:grid" not in SRC)


# ── G17.2: backend removal ──────────────────────────────────────
section("G17.2 backend endpoint /api/portal/student/order GONE")

check("@app.route('/api/portal/student/order'…) gone",
      "@app.route('/api/portal/student/order'" not in SRC)
check("def api_portal_student_order gone",
      "def api_portal_student_order(" not in SRC)
check("legacy /redeem 410 alias updated to /cart/add",
      '"use_instead": "/api/portal/student/cart/add"' in SRC
      and '"use_instead": "/api/portal/student/order"' not in SRC)


# ── Cart flow PRESERVED ─────────────────────────────────────────
section("cart flow (G15.4 + G16) preserved")

for sig in [
    "@app.route('/api/portal/student/balance', methods=['GET'])",
    "@app.route('/api/portal/student/cart', methods=['GET'])",
    "@app.route('/api/portal/student/cart/add', methods=['POST'])",
    "@app.route('/api/portal/student/cart/<int:cid>/quantity', methods=['PUT'])",
    "@app.route('/api/portal/student/cart/<int:cid>', methods=['DELETE'])",
    "@app.route('/api/portal/student/cart/checkout', methods=['POST'])",
    "@app.route('/api/portal/student/redemptions/<int:rid>/cancel', methods=['POST'])",
]:
    check("preserved: " + sig.split("'")[1], sig in SRC)

# Cart-side JS functions preserved
for fn in [
    "function askAddToCart(rid, name, cost)",
    "function doAddToCart(rid, qty)",
    "function renderCartContents()",
    "function cartChangeQty(cid, qty)",
    "function cartRemove(cid)",
    "function doCartCheckout()",
    "function openCartModal()",
    "function closeCartModal(ev)",
    "function updateFloatingCart()",
    "function showCartWouldExceed(name, cost, qty)",
    "function showInsufficientBalance(available, needed)",
]:
    check("JS preserved: " + fn.split("(")[0].replace("function ", ""),
          fn in PS)


# ── Cart button is the SOLE purchase button ─────────────────────
section("renderer emits a single cart button per card")

# The cart button must still exist.
check("renderer still emits 'btn btn-cart' button",
      'class="btn btn-cart"' in PS)
check("cart button text: '🛒 أضف للسلة'",
      "🛒 أضف للسلة" in PS)
check("cart button onclick → askAddToCart",
      'onclick="askAddToCart(' in PS)

# Qty stepper still present (G16.1).
check("qty stepper .card-qty still in CSS",
      ".card-qty{display:flex" in SRC)
check("renderer still emits id=qty-<rid>",
      'id="qty-\'+r.id+\'"' in PS)


# ── Runtime: Flask url_map ──────────────────────────────────────
section("runtime: Flask URL map sanity")
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))

# Confirm Flask has 0 routes matching the removed path.
try:
    rules = list(mod.app.url_map.iter_rules())
    order_routes = [str(r) for r in rules
                    if "/api/portal/student/order" in str(r)]
    check(f"0 routes match /api/portal/student/order (got {len(order_routes)})",
          len(order_routes) == 0)
    cart_routes = [str(r) for r in rules
                   if "/api/portal/student/cart" in str(r)]
    check(f"≥5 /api/portal/student/cart routes still present (got {len(cart_routes)})",
          len(cart_routes) >= 5)
    bal_routes = [str(r) for r in rules
                  if str(r) == "/api/portal/student/balance"]
    check(f"/api/portal/student/balance still registered (got {len(bal_routes)})",
          len(bal_routes) == 1)
    cancel_routes = [str(r) for r in rules
                     if "/api/portal/student/redemptions" in str(r)
                     and "/cancel" in str(r)]
    check(f"cancel endpoint still registered (got {len(cancel_routes)})",
          len(cancel_routes) == 1)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# ── Admin-side student_portal references preserved ──────────────
section("admin UI student_portal references preserved")

# These all key on request_source='student_portal' which past rows
# (from the removed direct-order endpoint AND from cart-checkout)
# carry. They MUST stay.
check("_pdSourceBadge handles student_portal",
      "src === 'student_portal'" in SRC and "🎓 الطالب" in SRC)
check("_histSourceLabel handles student_portal",
      "if (src === 'student_portal')" in SRC)
check("admin history-tab dropdown lists student_portal",
      '<option value="student_portal">🎓 الطالب</option>' in SRC)
check("backend /api/points/history filter accepts student_portal",
      'source_f == "student_portal"' in SRC
      and "r.request_source = 'student_portal'" in SRC)


# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G17 SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G17 SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
