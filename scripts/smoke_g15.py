"""
G15 hermetic test — student approval workflow.

Source-level assertions + runtime import of app.py + endpoint
registration check. No Flask boot.

Usage:
    python scripts/smoke_g15.py
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

# Pull PORTAL_STUDENT_HTML body so per-template assertions don't
# accidentally match against admin/teacher pages.
m_student = re.search(r'PORTAL_STUDENT_HTML = r"""(.*?)"""', SRC, re.DOTALL)
if not m_student:
    print("PORTAL_STUDENT_HTML constant not found; aborting.")
    sys.exit(2)
PS = m_student.group(1)


# ── PORTAL_STUDENT_HTML inline JS must PARSE ────────────────────
# (Added in G15-HOTFIX: the original G15.4 ternary had `+ ? + :`
# inside an open paren — a syntax error that prevented load() from
# ever running. Smoke tests grep'd for string presence but didn't
# parse the script, so the bug shipped to prod. node --check is the
# minimum guardrail.)
section("inline JS parses (node --check)")
NODE = shutil.which("node")
if not NODE:
    check("node available for syntax check (skipped — node not on PATH)",
          True, "install Node to enable this guard")
else:
    scripts = re.findall(r"<script>(.*?)</script>", PS, re.DOTALL)
    check("PORTAL_STUDENT_HTML has exactly one inline <script>",
          len(scripts) == 1, f"found {len(scripts)}")
    if scripts:
        with tempfile.NamedTemporaryFile(
            "w", suffix=".js", delete=False, encoding="utf-8") as tf:
            tf.write(scripts[0])
            tmp = tf.name
        try:
            proc = subprocess.run(
                [NODE, "--check", tmp],
                capture_output=True, text=True, timeout=15,
            )
            check("node --check on inline JS",
                  proc.returncode == 0,
                  (proc.stderr or proc.stdout).splitlines()[-1]
                  if (proc.stderr or proc.stdout) else "")
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)


# ── G15.1 — backend endpoints ───────────────────────────────────
section("G15.1 backend endpoints registered")

for sig in [
    "@app.route('/api/portal/student/balance', methods=['GET'])",
    "@app.route('/api/portal/student/order', methods=['POST'])",
    "@app.route('/api/portal/student/cart', methods=['GET'])",
    "@app.route('/api/portal/student/cart/add', methods=['POST'])",
    "@app.route('/api/portal/student/cart/<int:cid>/quantity', methods=['PUT'])",
    "@app.route('/api/portal/student/cart/<int:cid>', methods=['DELETE'])",
    "@app.route('/api/portal/student/cart/checkout', methods=['POST'])",
    "@app.route('/api/portal/student/redemptions/<int:rid>/cancel', methods=['POST'])",
]:
    check("route registered: " + sig.split("'")[1], sig in SRC)

for helper in [
    "def _g15_student_balance(db, sid):",
    "def _g15_validate_reward_for_request(db, rid):",
]:
    check("helper defined: " + helper, helper in SRC)

# Balance must NOT modify _pts_balance (it's a separate computed view).
# The exclusion list is split across two Python string concatenation
# lines in the source — match flexibly with a regex.
_PTS_EXCL = re.search(
    r"status NOT IN[\s\"']+\(\s*'cancelled'\s*,\s*'requested'\s*,\s*'rejected'\s*\)",
    SRC,
)
check(
    "G15 does NOT change _pts_balance semantics",
    SRC.count("def _pts_balance(db, sid):") == 1
    and _PTS_EXCL is not None,
)


# ── G15.2 — 3-card balance header ───────────────────────────────
section("G15.2 3-card balance header")

check("bal-cards CSS class shipped",
      ".bal-cards{display:grid" in PS
      and ".bal-card.total" in PS
      and ".bal-card.reserved" in PS
      and ".bal-card.available" in PS)
check("renderer fetches /api/portal/student/balance",
      "/api/portal/student/balance" in PS)
check("renderer emits 3-card grid",
      'class="bal-card total"' in PS
      and 'class="bal-card reserved"' in PS
      and 'class="bal-card available"' in PS)
check("animates Available (balAvail)",
      "countUp('balAvail'" in PS)
check("Arabic labels (الإجمالي / قيد الحجز / المتاح)",
      "إجمالي النقاط" in PS
      and "قيد الحجز" in PS
      and "المتاح" in PS)


# ── G15.3 — two-button reward card ──────────────────────────────
section("G15.3 two-button reward card")

check("renderer emits reward-actions wrapper",
      'class="reward-actions"' in PS)
check("🛒 cart button calls addToCart",
      "🛒 السلة" in PS and 'class="btn btn-cart"' in PS
      and "onclick=\"addToCart(" in PS)
check("⚡ order button calls askDirectOrder",
      "⚡ طلب مباشر" in PS and 'class="btn btn-order"' in PS
      and "onclick=\"askDirectOrder(" in PS)
check("addToCart() function defined",
      "function addToCart(rid, name, cost)" in PS)
check("askDirectOrder() function defined",
      "function askDirectOrder(rid,name,cost)" in PS)
check("doDirectOrder() POSTs to /api/portal/student/order",
      "fetch('/api/portal/student/order'" in PS)
check("can-afford uses Available (not legacy bal)",
      "var avail = b.available" in PS
      and "canAfford = avail >= cost" in PS)


# ── G15.4 — cart UI ─────────────────────────────────────────────
section("G15.4 cart sub-pane")

check("cart sub-tab rendered with badge",
      'data-sub="cart"' in PS and "🛒 السلة" in PS
      and 'id="cartBadge"' in PS)
check("pane-cart wrapper present",
      'id="pane-cart"' in PS)
check("setRewardsTab accepts 'cart'",
      "name !== 'cart' && name !== 'history'" in PS)
check("renderCartContents() defined",
      "function renderCartContents()" in PS)
check("cartChangeQty calls PUT /quantity",
      "function cartChangeQty(cid, qty)" in PS
      and "/api/portal/student/cart/'+cid+'/quantity" in PS)
check("cartRemove calls DELETE",
      "function cartRemove(cid)" in PS
      and "DELETE" in PS)
check("doCartCheckout POSTs to /cart/checkout",
      "function doCartCheckout()" in PS
      and "/api/portal/student/cart/checkout" in PS)
check("post-checkout jumps to history sub-tab",
      "STATE.currentSub = 'history'" in PS)


# ── G15.5 — order history with status + cancel ──────────────────
section("G15.5 history with status badges + cancel")

check("history h2 renamed to 'طلباتي'",
      "<h2>📋 طلباتي</h2>" in PS)
check("5 status keys mapped",
      "requested:" in PS and "pending:" in PS and "delivered:" in PS
      and "cancelled:" in PS and "rejected:" in PS)
check("📨 / ⏳ / ✅ / ❌ / ⛔ icons present",
      "📨 قيد الموافقة" in PS and "⏳ تمت الموافقة" in PS
      and "✅ تم التسليم" in PS and "❌ ملغي" in PS
      and "⛔ مرفوض" in PS)
check("cancel button rendered for requested rows only",
      "canCancel = (st === 'requested')" in PS
      and "cancelMyOrder(" in PS)
check("rejection_reason shown inline",
      "rejection_reason" in PS and "hist-reject-reason" in PS)
check("/redemptions endpoint returns rejection_reason",
      "COALESCE(rejection_reason,'') AS rejection_reason" in SRC)
check("cancelMyOrder POSTs to /redemptions/<rid>/cancel",
      "/api/portal/student/redemptions/'+rid+'/cancel" in PS)


# ── G15.6 — insufficient-balance modal ──────────────────────────
section("G15.6 insufficient-balance modal")

check("#balLow modal in DOM",
      'id="balLow"' in PS and 'id="balLowBody"' in PS)
check("showInsufficientBalance() defined",
      "function showInsufficientBalance(available, needed)" in PS)
check("direct-order error path wires modal",
      "d.error === 'insufficient available balance'" in PS)
check("cart-checkout error path wires modal",
      "showInsufficientBalance(d.available|0, d.cart_total|0)" in PS)
check("modal lists requested rows from STATE.redemptions",
      "(STATE.redemptions || []).filter" in PS
      and "'requested'" in PS)


# ── G15.7 — legacy endpoint deprecated ──────────────────────────
section("G15.7 legacy /api/portal/student/redeem → 410")

check("endpoint returns 410",
      'def api_portal_student_redeem()' in SRC
      and '"use_instead": "/api/portal/student/order"' in SRC
      and '), 410' in SRC)
check("no askRedeem/doRedeem in PORTAL_STUDENT_HTML anymore",
      "function askRedeem(" not in PS
      and "function doRedeem(" not in PS)
check("no caller of /api/portal/student/redeem in PORTAL_STUDENT_HTML",
      "/api/portal/student/redeem'," not in PS)


# ── G15.8 — admin source badge ──────────────────────────────────
section("G15.8 admin source badge for student_portal")

check("_pdSourceBadge has student_portal branch",
      "src === 'student_portal'" in SRC
      and "🎓 الطالب" in SRC)
check("_histSourceLabel has student_portal branch",
      "if (src === 'student_portal')" in SRC)
check("history-tab dropdown lists student_portal option",
      '<option value="student_portal">🎓 الطالب</option>' in SRC)
check("backend /api/points/history filter handles student_portal",
      'source_f == "student_portal"' in SRC
      and "r.request_source = 'student_portal'" in SRC)
check("parent_cart folded into parent bucket",
      "'parent_pid','parent_login','parent_cart'" in SRC)


# ── Regression: G1–G14 still standing ───────────────────────────
section("regression: prior features still present")

check("G14.1 reward image renderer intact",
      "r.image_url" in PS and "onerror=\"this.outerHTML=" in PS)
check("G14.2 lightbox intact",
      'id="rwLightbox"' in PS and "function openLightbox(" in PS)
check("G14.4 category tabs intact",
      'data-cat="toy"' in PS and 'data-cat="food"' in PS
      and "function setRewardCat(cat)" in PS)
check("G14.6 sub-tab scaffolding intact",
      "function setRewardsTab(name)" in PS
      and 'id="pane-shop"' in PS)
check("G13.4 activity feed still absent",
      "<h2>📜 آخر النشاطات</h2>" not in PS)
check("G13.5 Chart.js removal still in effect",
      "cdn.jsdelivr.net/npm/chart.js" not in PS)
check("admin parent reset-password endpoint preserved",
      "/api/admin/parents/<int:pid>/reset-password" in SRC)
check("admin approve endpoint preserved",
      "/api/points/redemptions/<int:redeem_id>/approve" in SRC)
check("admin deliver endpoint preserved",
      "/api/points/redemptions/<int:redeem_id>/deliver" in SRC)


# ── Runtime import + helper smoke ───────────────────────────────
section("runtime: app.py imports cleanly + helpers work")

spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))
    failed.append("import error: " + str(ex))

for fname in (
    "_g15_student_balance", "_g15_validate_reward_for_request",
    "api_portal_student_balance", "api_portal_student_order",
    "api_portal_student_cart_get", "api_portal_student_cart_add",
    "api_portal_student_cart_set_qty", "api_portal_student_cart_remove",
    "api_portal_student_cart_checkout",
    "api_portal_student_redemption_cancel",
):
    check(f"function present: {fname}", hasattr(mod, fname))

# Exercise the balance helper against the local DB.
try:
    with mod.app.app_context():
        db = mod.get_db()
        out = mod._g15_student_balance(db, 1)
        keys_ok = set(out.keys()) == {"total", "committed", "reserved", "available"}
        check(f"_g15_student_balance(sid=1) returns 4-key dict {out}", keys_ok)
        check("available = total - committed - reserved",
              out["available"] == out["total"] - out["committed"] - out["reserved"])
except Exception as ex:
    check("balance helper runtime", False, str(ex))
    failed.append("runtime balance error: " + str(ex))


# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G15 SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G15 SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
