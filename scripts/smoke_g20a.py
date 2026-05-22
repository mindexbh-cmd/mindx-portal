"""
G20a hermetic test — parent-tab regression restoration.

Asserts the 3 restorations stuck:
  - G20a.1: PORTAL_BOOKS_HTML renderer routes can_download=false to
            /parent/book/<id>/viewer (operator's per-page WebP
            read-only viewer with NO PDF download).
  - G20a.2: PORTAL_STUDENT_HTML emits pending + rejected callouts at
            the top of #pane-shop (the OLD front-of-shop status
            notifications restored from pre-3ad90c1).
  - G20a.3: /portal/parent-hub/evaluations route returns an iframe
            embedding /parent/evaluations/view (OLD rich layout).

Plus node --check on all inline JS blocks (G15-HOTFIX guard).

Usage:
    python scripts/smoke_g20a.py
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


def extract_template(name):
    m = re.search(r'^' + name + r' = r?"""(.*?)"""',
                  SRC, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


BK = extract_template("PORTAL_BOOKS_HTML")
PS = extract_template("PORTAL_STUDENT_HTML")


# ── G20a.1 — books read-only viewer link restored ──────────────
section("G20a.1 read-only book viewer link")

check("PORTAL_BOOKS_HTML extracted (non-empty)", bool(BK))
check("renderer captures personal_id from /meta",
      "d.student.personal_id" in BK
      and "var pid =" in BK
      and "var pidEnc = encodeURIComponent(pid)" in BK)
check("renderCard uses conditional viewHref",
      "var viewHref = e.can_download" in BK)
check("can_download=false routes to /parent/book/<id>/viewer",
      "/parent/book/' + e.id + '/viewer?pid='" in BK)
check("can_download=true keeps /api/books/<id>/view",
      "/api/books/' + e.id + '/view'" in BK)
check("download button still gated on can_download",
      "e.can_download" in BK and "/download" in BK and "⬇ تحميل" in BK)
check("🔒 read-only label still rendered",
      "🔒 للقراءة فقط" in BK)


# ── G20a.2 — points shop callouts restored ─────────────────────
section("G20a.2 points shop pending/rejected callouts")

check("PORTAL_STUDENT_HTML extracted", bool(PS))
check(".pp-pending-card CSS shipped",
      ".pp-pending-card{background:#e3f2fd;" in SRC)
check(".pp-rejected-card CSS shipped",
      ".pp-rejected-card{background:#fff3e0;" in SRC)
check(".pp-rejected-card .reason styling present",
      ".pp-rejected-card .reason{" in SRC)
check("renderer filters STATE.redemptions for pending",
      "_ppPending = (STATE.redemptions || []).filter" in PS
      and "'requested'" in PS)
check("renderer filters STATE.redemptions for rejected",
      "_ppRejected = (STATE.redemptions || []).filter" in PS
      and "'rejected'" in PS)
check("rejected slice capped at 5",
      ".slice(0, 5)" in PS or "slice(0,5)" in PS)
check("pending card title 'طلبك قيد المراجعة من الإدارة'",
      "طلبك قيد المراجعة من الإدارة" in PS)
check("rejected card title 'تم رفض طلبك'",
      "تم رفض طلبك" in PS)
check("rejection_reason label 'سبب الرفض'",
      "سبب الرفض" in PS)
check("rejection_reason fallback '(لم يُذكر سبب)'",
      "(لم يُذكر سبب)" in PS)
check("callouts injected BEFORE the rewards-grid empty-state",
      PS.find("_ppPending") < PS.find('STATE.rewards.length'))


# ── G20a.3 — evaluations iframe wrapper ────────────────────────
section("G20a.3 evaluations tab → iframe wrapper")

check("portal_parent_hub_evaluations_page resolves session sid",
      "_resolve_session_student_id(user)" in SRC
      and "def portal_parent_hub_evaluations_page" in SRC)
check("route reads students.personal_id for the pid",
      "SELECT personal_id FROM students WHERE id=?" in SRC)
check("iframe_url = /parent/evaluations/view?pid=...",
      '"/parent/evaluations/view?pid="' in SRC)
check("?inner=1 returns iframe HTML markup",
      "iframe class=\"eval-frame\"" in SRC
      or "<iframe class=\"eval-frame\"" in SRC)
check("standalone visit redirects to old rich page",
      # G20a originally redirected to iframe_url. G20m.2 split the
      # URLs so the iframe still uses iframe_url (carrying embed=1)
      # but the standalone redirect uses standalone_url (no embed=1)
      # so the legacy back-button stays visible on mobile full-page
      # navigation.
      "return redirect(standalone_url)" in SRC)
check(".eval-frame CSS sizes to viewport",
      ".eval-frame{width:100%" in SRC
      and "height:calc(100vh - 220px)" in SRC)
check("backend /parent/evaluations/view route still defined",
      "@app.route('/parent/evaluations/view'" in SRC)
check("backend /parent/evaluations JSON API still defined",
      "@app.route('/parent/evaluations'," in SRC)


# ── Regression: prior surfaces untouched ───────────────────────
section("regression: G12-G19 surfaces preserved")

check("G12 phActivateTab intact",
      "function phActivateTab" in SRC)
check("G12 ?inner=1 mode on payments route",
      "request.args.get('inner') == '1'" in SRC
      and "PORTAL_PARENT_PAYMENTS_HTML" in SRC)
check("G14.4 category tabs in shop intact",
      'data-cat="toy"' in PS and 'data-cat="food"' in PS)
check("G15.1 backend endpoints intact",
      "@app.route('/api/portal/student/balance', methods=['GET'])" in SRC
      and "@app.route('/api/portal/student/cart/add', methods=['POST'])" in SRC)
check("G15.4 cart sub-pane intact",
      'id="pane-cart"' in PS and "function doCartCheckout()" in PS)
check("G15.5 history sub-pane intact",
      "<h2>📋 طلباتي</h2>" in PS)
check("G15.7 legacy /redeem still 410",
      "), 410" in SRC and "endpoint deprecated" in SRC)
check("G16.3 floating cart badge intact",
      'id="floatCart"' in PS and "function updateFloatingCart()" in PS)
check("G16.5 cart modal intact",
      'id="cartModal"' in PS)
check("G17 direct-order removal still in effect",
      "⚡ طلب مباشر" not in PS
      and "@app.route('/api/portal/student/order'" not in SRC)
check("G19.2 single-number balance still in effect",
      'class="pts" id="balCount"' in PS
      and "class=\"bal-card" not in PS)


# ── node --check on PORTAL_STUDENT_HTML and PORTAL_BOOKS_HTML ──
section("node --check on inline JS")
NODE = shutil.which("node")
if NODE:
    for name, body in (("PORTAL_STUDENT_HTML", PS),
                       ("PORTAL_BOOKS_HTML", BK)):
        scripts = re.findall(r"<script>(.*?)</script>", body, re.DOTALL)
        if not scripts:
            check(f"{name}: any inline <script>?", False)
            continue
        biggest = max(scripts, key=len)
        with tempfile.NamedTemporaryFile("w", suffix=".js",
                                         delete=False,
                                         encoding="utf-8") as tf:
            tf.write(biggest)
            tmp = tf.name
        try:
            proc = subprocess.run([NODE, "--check", tmp],
                                  capture_output=True, text=True,
                                  timeout=15)
            check(f"{name} inline JS parses",
                  proc.returncode == 0,
                  (proc.stderr or proc.stdout).splitlines()[-1]
                  if (proc.stderr or proc.stdout) else "")
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)
else:
    check("node available (skipped)", True)


# ── Runtime ────────────────────────────────────────────────────
section("runtime: app.py imports")
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))

# Backend routes still wired in url_map.
try:
    rules = [str(r) for r in mod.app.url_map.iter_rules()]
    for route in [
        "/portal/parent-hub/evaluations",
        "/portal/parent-hub/curriculum",
        "/portal/parent-hub/points",
        "/parent/evaluations/view",
        "/parent/book/<int:bid>/viewer",
        "/parent/book/<int:bid>/page/<int:n>.webp",
        "/api/portal/student/balance",
        "/api/portal/student/cart/checkout",
    ]:
        check(f"route still registered: {route}", route in rules)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G20a SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G20a SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
