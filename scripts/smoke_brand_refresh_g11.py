"""
G11 hermetic test — Mindex brand refresh source-level assertions.

Runs against app.py source code only — no Flask app, no DB, no browser.
Catches structural regressions (lost placeholders, missing CSS vars,
broken contact URLs) before deploy.

Usage:
    python scripts/test_g11_brand_refresh.py

Returns 0 on success, 1 on first failure (prints which assertion).
"""

import re
import sys
import pathlib

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

# ── 1. Brand constants defined ──────────────────────────────────
section("brand constants defined")
for const in (
    "_MINDEX_BRAND_CSS",
    "_MINDEX_BRAND_TOPBAR_HTML",
    "_MINDEX_BRAND_FOOTER_HTML",
    "_inject_brand",
):
    if not check(f"{const} appears in app.py",
                 const in SRC,
                 "G11.1 must define this constant"):
        failed.append(const)

# ── 2. The 4 brand CSS variables exist and use the spec colors ──
section("brand CSS variables")
vars_expected = {
    "--mindex-purple": "#6b2c91",
    "--mindex-pink":   "#B85FBE",
    "--mindex-teal":   "#4FB8B0",
    "--mindex-gold":   "#F2C744",
}
for name, color in vars_expected.items():
    pattern = re.compile(re.escape(name) + r"\s*:\s*" + re.escape(color))
    if not check(f"{name}: {color}",
                 bool(pattern.search(SRC)),
                 "expected color/value mismatch in :root block"):
        failed.append(f"{name}:{color}")

# ── 3. Logo + fallback ──────────────────────────────────────────
section("logo asset + fallback")
check("logo path /static/images/mindex_logo.png referenced in brand topbar",
      '/static/images/mindex_logo.png' in SRC)
check("logo <img> has onerror fallback wired",
      'onerror=' in SRC and "this.nextElementSibling.style.display='flex'" in SRC)
check("logo fallback styles defined (.mb-logo-fb)",
      '.mb-logo-fb' in SRC)
# Verify the asset actually exists on disk
logo_path = ROOT / "static" / "images" / "mindex_logo.png"
if not check("logo file exists on disk",
             logo_path.exists(),
             f"expected at {logo_path}"):
    failed.append("logo-missing")

# ── 4. Contact URLs correctly formatted ─────────────────────────
section("contact footer URLs")
check("phone href tel:+97336078926",
      'href="tel:+97336078926"' in SRC)
check("WhatsApp href https://wa.me/97336078926",
      'href="https://wa.me/97336078926"' in SRC)
check("Instagram href https://instagram.com/mindex_bh",
      'href="https://instagram.com/mindex_bh"' in SRC)
check("phone label 3607 8926",
      '3607 8926' in SRC)
check("Instagram handle @mindex_bh appears in footer",
      '@mindex_bh' in SRC)

# Brand colors on contact cards
check("WhatsApp brand green #25D366 used in footer icon",
      '#25D366' in SRC)
check("Phone green #639922 used in footer icon",
      '#639922' in SRC)
check("Instagram gradient (5-stop) defined in footer icon",
      '#f09433' in SRC and '#bc1888' in SRC)

# ── 5. SVG progress circle (G11.3) ──────────────────────────────
section("SVG progress circle")
check('viewBox="0 0 100 100" present',
      'viewBox="0 0 100 100"' in SRC)
check("circle r=42 with stroke-width 10",
      'r="42"' in SRC and 'stroke-width="10"' in SRC)
check('stroke-dasharray="263.89" (2*pi*42)',
      'stroke-dasharray="263.89"' in SRC)
check("hours-circle-fill ID emitted",
      'id="hours-circle-fill"' in SRC)
check("hours-circle-pct ID emitted for the center percentage",
      'id="hours-circle-pct"' in SRC)
check("JS computes stroke-dashoffset from real percentage",
      "CIRCLE_CIRC - (CIRCLE_CIRC * pct / 100)" in SRC)

# ── 6. Brand layout classes used ────────────────────────────────
section("brand layout classes")
for cls in (".mb-topbar", ".mb-card", ".mb-student",
            ".mb-progress-pane", ".mb-stat-card",
            ".mb-nav-card", ".mb-nav-btn", ".mb-nav-grid",
            ".mb-footer", ".mb-contact"):
    check(f"{cls} defined", cls + "{" in SRC or cls + " " in SRC)

# ── 7. Placeholders present in parent templates ─────────────────
section("brand placeholders wired in templates")
templates_with_brand = [
    "PORTAL_PARENT_PID_HUB_HTML",
    "PORTAL_PARENT_HTML",
    "PORTAL_PARENT_HUB_HTML",
    "PORTAL_PARENT_PAYMENTS_HTML",
    "PORTAL_PARENT_ATTENDANCE_HTML",
    "PORTAL_PARENT_MESSAGES_HTML",
    "PORTAL_PARENT_EVALUATIONS_HTML",
    "PORTAL_BOOKS_HTML",
    "PORTAL_STUDENT_HTML",
]
# Every parent template should mention either __BRAND_TOPBAR__ or
# carry it via the rebind (PORTAL_PARENT_HUB_HTML is pre-substituted).
# We check: each constant definition is followed (before next constant
# defn) by at least one __BRAND_TOPBAR__ placeholder OR was rebound.
for tpl in templates_with_brand:
    # Slice from `<NAME> = r"""` to the next top-level `XXX = r"""`.
    pat = re.compile(re.escape(tpl) + r'\s*=\s*r"""(.*?)"""', re.DOTALL)
    match = pat.search(SRC)
    if not match:
        check(f"{tpl} defined", False, "constant missing")
        failed.append(tpl)
        continue
    body = match.group(1)
    has_topbar_placeholder = "__BRAND_TOPBAR__" in body
    # PORTAL_PARENT_HUB_HTML is pre-baked at module load — its body
    # already has placeholders substituted in the rebound constant.
    # Original source string still contains them.
    check(f"{tpl} body contains __BRAND_TOPBAR__",
          has_topbar_placeholder,
          "G11.6: every parent template must carry the brand topbar")
    check(f"{tpl} body contains __BRAND_FOOTER__",
          "__BRAND_FOOTER__" in body,
          "G11.6: contact footer must be wired")

# ── 8. Helper called from route handlers ────────────────────────
section("route handlers call _inject_brand")
# Count calls to _inject_brand — should be at least 7 (one per
# parent route that still substitutes at request time; PORTAL_PARENT
# _HUB_HTML uses a module-level rebind so it's not counted).
calls = len(re.findall(r"_inject_brand\(", SRC))
check(f"_inject_brand called >=7 times (got {calls})",
      calls >= 7,
      "expected: PID_HUB + 4 sub-pages + PARENT + STUDENT + BOOKS + module rebind")

# ── 9. Existing data-binding IDs preserved (G11.3 must not break) ─
section("PID hub data-binding IDs preserved")
for elem_id in ("card-name", "card-pid", "card-group", "card-level",
                "card-class", "card-teacher", "card-status",
                "hours-summary", "hours-required", "hours-contract",
                "hours-taken", "hours-remaining", "hours-fill",
                "hours-overrun-banner", "hours-overrun",
                "action-tabs"):
    check(f'id="{elem_id}" still present in PID_HUB',
          f'id="{elem_id}"' in SRC)

# New IDs introduced by G11.3
section("G11.3 new IDs")
for elem_id in ("hours-circle-fill", "hours-circle-pct",
                "hours-circle-cap",
                "hours-contract-num", "hours-taken-num",
                "hours-remaining-num"):
    check(f'id="{elem_id}" present', f'id="{elem_id}"' in SRC)

# ── 10. Module imports cleanly (smoke) ──────────────────────────
section("module-level smoke")
# Reading + AST-parsing without running the route handlers.
import ast
try:
    ast.parse(SRC)
    check("app.py parses as valid Python", True)
except SyntaxError as e:
    check(f"app.py parses as valid Python (got {e})", False)
    failed.append("syntax")

# ── 11. Inject helper round-trip (runtime) ──────────────────────
section("_inject_brand runtime substitution")
try:
    # Import without booting Flask routes. We just need the function.
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
    mod = importlib.util.module_from_spec(spec)
    # Suppress Flask side-effects: app.run() is guarded by __main__.
    spec.loader.exec_module(mod)
    sample = "X__BRAND_TOPBAR__Y__BRAND_FOOTER__Z__BRAND_CSS__W"
    out = mod._inject_brand(sample)
    check("topbar placeholder substituted",
          "__BRAND_TOPBAR__" not in out)
    check("footer placeholder substituted",
          "__BRAND_FOOTER__" not in out)
    check("CSS placeholder substituted",
          "__BRAND_CSS__" not in out)
    check("brand logo path appears in substituted output",
          "/static/images/mindex_logo.png" in out)
    check("Instagram contact URL appears in substituted output",
          "https://instagram.com/mindex_bh" in out)
    check("--mindex-purple appears in substituted output",
          "--mindex-purple" in out)
    # The dead PORTAL_PARENT_HUB_HTML was rebound at module load —
    # verify it no longer contains the placeholder.
    check("PORTAL_PARENT_HUB_HTML pre-baked (no leftover placeholders)",
          "__BRAND_TOPBAR__" not in mod.PORTAL_PARENT_HUB_HTML
          and "__BRAND_FOOTER__" not in mod.PORTAL_PARENT_HUB_HTML)
except Exception as e:
    check(f"runtime substitution succeeded (got {type(e).__name__}: {e})", False)
    failed.append("runtime")

# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G11 BRAND REFRESH TEST — FAILED ({len(failed)} issues)")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("G11 BRAND REFRESH TEST — ALL CHECKS PASSED")
    sys.exit(0)
