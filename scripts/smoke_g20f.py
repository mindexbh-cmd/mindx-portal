"""
G20f hermetic test — stock-restore + out-of-stock UX hint.

Asserts:
  - G20f.2: DELETE /api/admin/redemptions/<id> restores stock when
            the deleted row was in 'pending' or 'delivered' status.
            Same restore pattern as the existing /cancel endpoint.
  - G20f.3: PORTAL_STUDENT_HTML renderer adds .out-of-stock class
            + 'نفد المخزون' hint when stock=0, distinct from
            .unaffordable.

Plus node --check on inline JS (G15-HOTFIX guard).

Usage:
    python scripts/smoke_g20f.py
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


def extract(name):
    m = re.search(r'^' + name + r' = r?"""(.*?)"""',
                  SRC, re.DOTALL | re.MULTILINE)
    return m.group(1) if m else ""


PS = extract("PORTAL_STUDENT_HTML")


# ── G20f.2 — DELETE endpoint stock-restore ─────────────────────
section("G20f.2 DELETE endpoint auto-restores stock")

check("DELETE /api/admin/redemptions/<id> route registered",
      "@app.route('/api/admin/redemptions/<int:redeem_id>', methods=['DELETE'])" in SRC)
check("handler computes was_committed for pending/delivered",
      'was_committed = (snapshot.get("status") in ("pending", "delivered"))' in SRC)
check("handler bumps rewards.stock+1 conditionally",
      "UPDATE rewards SET stock=stock+1" in SRC
      and "AND stock>=0" in SRC)
check("stock-restore guarded on was_committed AND reward_id",
      "if was_committed and reward_id:" in SRC)
check("response includes stock_restored flag",
      '"stock_restored": stock_restored' in SRC)
check("audit log snapshot carries _stock_restored",
      '"_stock_restored": stock_restored' in SRC)


# ── G20f.3 — out-of-stock visual + hint ────────────────────────
section("G20f.3 distinct out-of-stock visual")

check(".reward.out-of-stock CSS shipped",
      ".reward.out-of-stock{opacity:0.55;}" in SRC)
check(".reward.out-of-stock image gets 75% grayscale",
      "grayscale(75%)" in SRC)
check(".stock-hint base CSS shipped",
      ".reward .stock-hint{display:none" in SRC
      and ".reward.out-of-stock .stock-hint{display:block" in SRC)
check("renderer applies .out-of-stock when !inStock",
      "(!inStock) ? ' out-of-stock'" in SRC)
check("out-of-stock takes precedence over unaffordable",
      "(!inStock) ? ' out-of-stock' : (canAfford ? '' : ' unaffordable')" in SRC)
check("renderer emits 'نفد المخزون' hint markup",
      "⚠ نفد المخزون" in PS
      and 'class="stock-hint"' in PS)
check("'نقاطك غير كافية' hint still rendered (regression check)",
      "⚠ نقاطك غير كافية" in PS
      and 'class="afford-hint"' in PS)


# ── Regression: prior G20a/b/d surfaces preserved ──────────────
section("regression: prior surfaces preserved")

check("G20a.1 read-only book viewer link still wired",
      "/parent/book/' + e.id + '/viewer?pid='" in SRC)
check("G20a.2 pending callout still in shop renderer",
      "طلبك قيد المراجعة من الإدارة" in PS)
check("G20a.2 rejected callout still in shop renderer",
      "تم رفض طلبك" in PS)
check("G20a.3 eval iframe wrapper still in route",
      'class="eval-frame"' in SRC)
check("G20b.1 .unaffordable shading still in place",
      ".reward.unaffordable{opacity:0.55;}" in SRC)
check("G20d.1 headline = total − committed still in place",
      "(b.total - b.committed)" in PS)
check("G20d.4 delivery checkbox still in place",
      'class="pd-cb"' in SRC)
check("G20e DELETE endpoint still registered",
      "def api_admin_redemption_hard_delete" in SRC)
check("/cancel endpoint stock-restore unchanged",
      'UPDATE rewards SET stock=stock+1 WHERE id=? AND stock>=0' in SRC)


# ── Inline JS parses ───────────────────────────────────────────
section("node --check on inline JS")
NODE = shutil.which("node")
if NODE:
    scripts = re.findall(r"<script>(.*?)</script>", PS, re.DOTALL)
    if scripts:
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
            check("PORTAL_STUDENT_HTML inline JS parses",
                  proc.returncode == 0,
                  (proc.stderr or proc.stdout).splitlines()[-1]
                  if (proc.stderr or proc.stdout) else "")
        finally:
            pathlib.Path(tmp).unlink(missing_ok=True)
else:
    check("node available (skipped)", True)


# ── Runtime ────────────────────────────────────────────────────
section("runtime: app.py imports + routes")
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))

try:
    rules = [str(r) for r in mod.app.url_map.iter_rules()]
    check("DELETE /api/admin/redemptions/<int:redeem_id> still registered",
          "/api/admin/redemptions/<int:redeem_id>" in rules)
    check("POST /api/points/redemptions/<int:redeem_id>/cancel still alive",
          "/api/points/redemptions/<int:redeem_id>/cancel" in rules)
except Exception as ex:
    check("flask url_map probe", False, str(ex))


# ── Summary ────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G20f SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G20f SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
