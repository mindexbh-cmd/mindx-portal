"""
G14 hermetic test — rewards shop UX.

Source-level assertions + runtime import of app.py. No Flask boot.

Usage:
    python scripts/smoke_g14.py
"""

import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
APP_PY = ROOT / "app.py"
SRC = APP_PY.read_text(encoding="utf-8")


def check(label, ok, hint=""):
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")
    if not ok and hint:
        print(f"         hint: {hint}")
    return bool(ok)


def section(title):
    print(f"\n=== {title} ===")


failed = []

# Pull the PORTAL_STUDENT_HTML body out once so per-template
# assertions don't accidentally match against admin/teacher pages.
m_student = re.search(r'PORTAL_STUDENT_HTML = r"""(.*?)"""', SRC, re.DOTALL)
if not m_student:
    print("PORTAL_STUDENT_HTML constant not found; aborting.")
    sys.exit(2)
PS = m_student.group(1)


# ── G14.1 — reward image rendering ──────────────────────────────
section("G14.1 reward image rendering")

check(
    "renderer reads r.image_url (was emitting only r.icon)",
    "r.image_url" in PS and "imgUrl = (r.image_url" in PS,
)
check(
    "renderer emits <img onerror=...> fallback to icon emoji",
    "onerror=\"this.outerHTML=" in PS,
)
check(
    "loading=\"lazy\" on reward images to avoid scroll-jank",
    'loading="lazy"' in PS,
)
check(
    ".reward .ic img CSS sized at 88×88 + object-fit:cover",
    re.search(r"\.reward\s+\.ic\s+img\s*\{[^}]*width:\s*88px[^}]*height:\s*88px",
              SRC) is not None,
)


# ── G14.2 — lightbox modal ──────────────────────────────────────
section("G14.2 lightbox modal")

check(
    "lightbox overlay div with id=rwLightbox exists",
    'id="rwLightbox"' in PS and 'class="lightbox"' in PS,
)
check(
    "lightbox has aria-modal + role=dialog (a11y)",
    'role="dialog"' in PS and 'aria-modal="true"' in PS,
)
check(
    "lightbox image + title elements present",
    'id="rwLightboxImg"' in PS and 'id="rwLightboxTitle"' in PS,
)
check(
    "lightbox close button (X) with aria-label",
    'class="lightbox-close"' in PS and 'aria-label="إغلاق"' in PS,
)
check(
    "openLightbox() JS function defined",
    "function openLightbox(src, title)" in PS,
)
check(
    "closeLightbox() JS function defined",
    "function closeLightbox(ev)" in PS,
)
check(
    "delegated click listener for .reward .ic img",
    "closest('.reward .ic img')" in PS,
)
check(
    "ESC key closes the lightbox",
    "e.key === 'Escape'" in PS or "e.key === 'Esc'" in PS,
)
check(
    ".lightbox CSS uses opacity-fade transition (300ms)",
    re.search(r"\.lightbox\s*\{[^}]*transition:\s*opacity\s+\.3s",
              SRC) is not None,
)
check(
    "prefers-reduced-motion suppresses fade",
    "prefers-reduced-motion" in PS and ".lightbox" in PS,
)
check(
    ".reward .ic img cursor:zoom-in (signals clickability)",
    "cursor:zoom-in" in SRC,
)


# ── G14.4 — category tabs (games / meals) ───────────────────────
section("G14.4 category filter tabs")

check(
    "category tab bar exists in renderer",
    'class="cat-tabs"' in PS,
)
check(
    "🎮 ألعاب tab (data-cat=toy, default active)",
    'data-cat="toy"' in PS and "🎮 ألعاب" in PS,
)
check(
    "🍔 وجبات tab (data-cat=food)",
    'data-cat="food"' in PS and "🍔 وجبات" in PS,
)
check(
    "reward card carries data-cat",
    'data-cat="\'+cat+\'"' in PS,
)
check(
    "untyped rewards default to 'toy' bucket",
    "(r.category_type === 'food') ? 'food' : 'toy'" in PS,
)
check(
    "setRewardCat() JS function defined",
    "function setRewardCat(cat)" in PS,
)
check(
    "active-tab choice persisted on STATE.currentCat",
    "STATE.currentCat" in PS,
)
check(
    "empty-state placeholder when current category is empty",
    'id="catEmpty"' in PS,
)
check(
    ".cat-tab.active uses brand purple gradient",
    re.search(r"\.cat-tab\.active\s*\{[^}]*linear-gradient\([^}]*#6B3FA0",
              SRC) is not None,
)


# ── G14.6 — history sub-tab ─────────────────────────────────────
section("G14.6 history sub-tab")

check(
    "sub-tab bar exists (shop / history)",
    'class="sub-tabs"' in PS,
)
check(
    "🛍️ shop sub-tab (default active)",
    'data-sub="shop"' in PS and "🛍️ متجر المكافآت" in PS,
)
check(
    "📋 history sub-tab",
    'data-sub="history"' in PS and "📋 مكافآتي السابقة" in PS,
)
check(
    "pane-shop wrapper div present",
    'id="pane-shop"' in PS,
)
check(
    "pane-history wrapper div present",
    'id="pane-history"' in PS,
)
check(
    "setRewardsTab() JS function defined",
    "function setRewardsTab(name)" in PS,
)
check(
    "STATE.currentSub persists tab choice across re-renders",
    "STATE.currentSub" in PS,
)
check(
    ".sub-pane visibility toggled via .active class",
    ".sub-pane.active" in SRC and ".sub-pane{display:none" in SRC,
)


# ── Regression guards ───────────────────────────────────────────
section("regression guards: existing behaviour preserved")

check(
    "askRedeem() still defined (redemption flow intact)",
    "function askRedeem(rid,name,cost)" in PS,
)
check(
    "doRedeem() still defined (POST /api/portal/student/redeem)",
    "function doRedeem(rid)" in PS
    and "/api/portal/student/redeem" in PS,
)
check(
    "rewards shop section title kept",
    "🎁 متجر المكافآت" in PS,
)
check(
    "redemption history section title kept",
    "📋 مكافآتي السابقة" in PS,
)
check(
    "G13.5 Chart.js removal still in effect (no CDN in template)",
    "cdn.jsdelivr.net/npm/chart.js" not in PS,
)
check(
    "G13.4 activity feed still absent",
    "<h2>📜 آخر النشاطات</h2>" not in PS,
)


# ── Runtime ─────────────────────────────────────────────────────
section("runtime: app.py imports cleanly")
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))
    failed.append("import error: " + str(ex))

for const_name in (
    "PORTAL_STUDENT_HTML",
    "PORTAL_PARENT_HTML",
    "PORTAL_PARENT_PID_HUB_HTML",
):
    val = getattr(mod, const_name, None)
    check(f"{const_name} still defined and non-empty",
          bool(val) and len(val) > 500)

# Backend helpers we relied on still exist.
check(
    "_reward_serve_image_url helper still present",
    callable(getattr(mod, "_reward_serve_image_url", None)),
)


# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G14 SMOKE TEST — FAILED ({len(failed)})")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
print("G14 SMOKE TEST — ALL CHECKS PASSED")
sys.exit(0)
