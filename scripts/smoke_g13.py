"""
G13 hermetic test — UX cleanups (forced pw, level row, parent sections).

Runs source-level assertions on app.py plus a runtime import so any
syntax / template-render regression surfaces immediately. No Flask boot
needed.

Usage:
    python scripts/smoke_g13.py
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


# ── G13.1 — forced password change bypass ───────────────────────
section("G13.1 forced-password-change redirect removed")

# Zero remaining `if int(user.get("must_change_pw") or 0):` guards.
guard_re = re.compile(
    r'if int\(user\.get\("must_change_pw"\) or 0\):\s*\n\s*return redirect',
)
n_guards = len(guard_re.findall(SRC))
if not check("zero remaining redirect guards (was 9)", n_guards == 0,
             f"found {n_guards} — should be 0"):
    failed.append("guards remain")

# Zero remaining `must_change and role in (...): redirect` from the
# /login dispatch.
if not check(
    "/login no longer redirects to change-password",
    "redirect(\"/portal/change-password\")" not in SRC,
    "the post-auth dispatch must not bounce non-admin to change-password",
):
    failed.append("login still redirects")

# /portal/change-password gated to admin.
gate_pat = re.compile(
    r"def portal_change_pw_page\(\):.*?role != \"admin\"",
    re.DOTALL,
)
if not check("/portal/change-password gated to admin-only",
             bool(gate_pat.search(SRC))):
    failed.append("portal_change_pw_page not gated")

api_gate_pat = re.compile(
    r"def api_portal_change_pw\(\):.*?role != \"admin\"",
    re.DOTALL,
)
if not check("/api/portal/change-password gated to admin-only",
             bool(api_gate_pat.search(SRC))):
    failed.append("api_portal_change_pw not gated")

# No code path sets must_change_pw=1 anymore.
n_set_one = len(re.findall(r"must_change_pw\s*=\s*1", SRC))
if not check("no must_change_pw=1 setters remain (was 4)",
             n_set_one == 0, f"found {n_set_one}"):
    failed.append("must_change_pw=1 setters remain")

# Admin password reset endpoint preserved (admin still resets others).
if not check(
    "admin parent password reset endpoint preserved",
    "/api/admin/parents/<int:pid>/reset-password" in SRC
    or "@app.route('/api/admin/parents/<int:pid>/reset-password'" in SRC,
    "must keep admin's ability to reset other users' passwords",
):
    failed.append("admin reset endpoint missing")


# ── G13.2 — level row hidden ────────────────────────────────────
section("G13.2 level row hidden in PORTAL_PARENT_PID_HUB_HTML")

# The row should now carry display:none.
level_row_pat = re.compile(
    r'<div class="mb-stu-row"[^>]*display:none[^>]*>\s*'
    r'<span class="mb-stu-row-lbl">المستوى:'
)
if not check("المستوى row carries display:none",
             bool(level_row_pat.search(SRC))):
    failed.append("level row not hidden")

# The card-level binding survives (JS still safe to call).
if not check("id=\"card-level\" element kept (binding survives)",
             'id="card-level"' in SRC):
    failed.append("card-level id removed")
if not check("getElementById('card-level') binding preserved",
             "getElementById('card-level')" in SRC):
    failed.append("card-level binding removed")


# ── G13.3 — weekly summary section removed ──────────────────────
section("G13.3 weekly summary section removed from PORTAL_STUDENT_HTML")

if not check(
    "no rendered '📅 ملخص هذا الأسبوع' h2",
    "<h2>📅 ملخص هذا الأسبوع</h2>" not in SRC,
):
    failed.append("weekly summary still rendered")
if not check(
    "no weeklySumm.positive_count + .negative_count consumer",
    "weeklySumm.positive_count + weeklySumm.negative_count" not in SRC,
):
    failed.append("weeklySumm consumer remains")
if not check(
    "wcell pos/neg/net stat tiles gone",
    "'<div class=\"wcell pos\"><span class=\"ic\">⭐</span>" not in SRC,
):
    failed.append("wcell rendering remains")


# ── G13.4 — activity feed removed (both templates) ──────────────
section("G13.4 activity feed removed from both parent surfaces")

if not check(
    "PORTAL_STUDENT_HTML: no '📜 آخر النشاطات' h2",
    "<h2>📜 آخر النشاطات</h2>" not in SRC,
):
    failed.append("student activity feed still rendered")
if not check(
    "PORTAL_PARENT_HTML: no '📝 آخر النشاطات (آخر 20 حدث)' card",
    "📝 آخر النشاطات (آخر 20 حدث)" not in SRC,
):
    failed.append("parent activity feed still rendered")

# Admin-side dashboard activity feed MUST remain untouched.
if not check(
    "admin dashboard 'آخر النشاطات' preserved",
    "/api/dashboard/recent-activity" in SRC
    and "md-activity-list" in SRC,
    "G13 must NOT touch admin pages",
):
    failed.append("admin dashboard feed clobbered")


# ── G13.5 — 8-week chart + Chart.js gone ────────────────────────
section("G13.5 8-week chart + Chart.js dependency dropped")

if not check(
    "PORTAL_STUDENT_HTML: no '📈 تطوري خلال 8 أسابيع' section",
    "<h2>📈 تطوري خلال 8 أسابيع</h2>" not in SRC,
):
    failed.append("student 8-week chart remains")
if not check(
    "PORTAL_PARENT_HTML: no 'التقدم خلال آخر 8 أسابيع' card",
    "📈 التقدم خلال آخر 8 أسابيع" not in SRC,
):
    failed.append("parent 8-week chart remains")
if not check(
    "drawChart() removed from PORTAL_STUDENT_HTML",
    "function drawChart(weekly){" not in SRC,
):
    failed.append("drawChart still defined")
if not check(
    "drawCharts(i,c) removed from PORTAL_PARENT_HTML",
    "function drawCharts(i,c){" not in SRC,
):
    failed.append("drawCharts still defined")
if not check(
    "weeklyChart canvas removed",
    'id="weeklyChart"' not in SRC,
):
    failed.append("weeklyChart canvas remains")

# Chart.js CDN script should be gone from both templates. Other
# admin/teacher pages may still ship Chart.js — that's fine.
m_student = re.search(
    r'PORTAL_STUDENT_HTML = r"""(.*?)"""', SRC, re.DOTALL,
)
m_parent = re.search(
    r'PORTAL_PARENT_HTML = r"""(.*?)"""', SRC, re.DOTALL,
)
if not check("PORTAL_STUDENT_HTML matched", bool(m_student)):
    failed.append("PORTAL_STUDENT_HTML not found")
elif not check(
    "PORTAL_STUDENT_HTML: no chart.umd.min.js <script>",
    "cdn.jsdelivr.net/npm/chart.js" not in m_student.group(1),
):
    failed.append("student Chart.js CDN remains")
if not check("PORTAL_PARENT_HTML matched", bool(m_parent)):
    failed.append("PORTAL_PARENT_HTML not found")
elif not check(
    "PORTAL_PARENT_HTML: no chart.umd.min.js <script>",
    "cdn.jsdelivr.net/npm/chart.js" not in m_parent.group(1),
):
    failed.append("parent Chart.js CDN remains")


# ── G11 / G12 preservation ──────────────────────────────────────
section("G11 brand + G12 tabs regression guard")

# G11 brand still active.
if not check(
    "PORTAL_PARENT_PID_HUB_HTML x-build still g11-brand-refresh",
    'x-build" content="g11-brand-refresh"' in SRC,
):
    failed.append("brand build marker missing")

# G12 tab infrastructure preserved.
for marker, label in [
    ("function phActivateTab", "G12 phActivateTab"),
    ("function phReexecuteScripts", "G12 phReexecuteScripts"),
    ("var TAB_URLS = {", "G12 TAB_URLS"),
    ('id="ph-tab-pane"', "G12 tab pane"),
    ('id="card-name"', "PID_HUB card-name binding"),
    ('id="card-group"', "PID_HUB card-group binding"),
    ('id="card-teacher"', "PID_HUB card-teacher binding"),
]:
    if not check(f"{label} preserved", marker in SRC):
        failed.append(f"{label} broken")


# ── Runtime import check ────────────────────────────────────────
section("runtime: importing app.py exercises template constants")
spec = importlib.util.spec_from_file_location("app_for_test", APP_PY)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    check("app module imports cleanly", True)
except Exception as ex:
    check("app module imports cleanly", False, str(ex))
    failed.append("import error: " + str(ex))

# Sanity: every template constant we touched still exists.
for const_name in (
    "PORTAL_STUDENT_HTML",
    "PORTAL_PARENT_HTML",
    "PORTAL_PARENT_PID_HUB_HTML",
    "PORTAL_CHANGE_PW_HTML",
):
    val = getattr(mod, const_name, None)
    if not check(f"{const_name} still defined and non-empty",
                 bool(val) and len(val) > 500):
        failed.append(f"{const_name} broken")

# _render_subpage_inner (G12) still produces a non-empty payload for
# PORTAL_STUDENT_HTML — the most-touched template this round.
try:
    inner = mod._render_subpage_inner(mod.PORTAL_STUDENT_HTML)
    check("PORTAL_STUDENT_HTML still renders via _render_subpage_inner",
          len(inner) > 1000 and "<!DOCTYPE" not in inner)
except Exception as ex:
    check("PORTAL_STUDENT_HTML still renders via _render_subpage_inner",
          False, str(ex))
    failed.append("_render_subpage_inner broke: " + str(ex))


# ── Summary ─────────────────────────────────────────────────────
print("\n" + "=" * 60)
if failed:
    print(f"G13 SMOKE TEST — FAILED ({len(failed)} issues)")
    for f in failed:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("G13 SMOKE TEST — ALL CHECKS PASSED")
    sys.exit(0)
