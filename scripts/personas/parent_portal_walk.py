"""Pre-deploy persona walk for /portal/parent student-card layout fix."""
from __future__ import annotations
import os, sys, json, io, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir))
from auto_test import BrowserSession

BASE = "http://127.0.0.1:5000"
REPORT = {"personas": {}}


def has_text(page, needle):
    try:
        return page.evaluate("(n) => document.body.innerText.includes(n)", needle)
    except Exception:
        return False


def visible(page, selector):
    try:
        return page.evaluate(
            f"() => {{const e=document.querySelector({selector!r}); if(!e) return false; const r=e.getBoundingClientRect(); const s=getComputedStyle(e); return r.width>0 && r.height>0 && s.display!=='none' && s.visibility!=='hidden';}}"
        )
    except Exception:
        return False


def settle(page, ms=1500):
    try:
        page.wait_for_load_state("domcontentloaded")
    except Exception:
        pass
    time.sleep(ms/1000.0)


def run_student():
    out = {"name": "student_test", "checks": {}, "console": [], "subpages": {}}
    with BrowserSession(base_url=BASE, headless=True) as s:
        s.login_as("student")
        settle(s.page)
        s.navigate("/portal/parent")
        settle(s.page, 2500)  # give phLookup() time to populate
        out["url"] = s.page.url
        out["screenshots"] = [s.screenshot("student_portal_parent")]

        text_checks = {
            "header_student_card": has_text(s.page, "STUDENT CARD") or has_text(s.page, "بطاقة طالب"),
            "year_2025_2026": has_text(s.page, "2025-2026"),
            "pid_value": has_text(s.page, "TEST-STUDENT-0001"),
            "label_student_name": has_text(s.page, "اسم الطالب"),
            "label_group": has_text(s.page, "المجموعة"),
            "label_level": has_text(s.page, "المستوى"),
            "label_class": has_text(s.page, "الصف"),
            "label_teacher": has_text(s.page, "المعلمة"),
            "label_status": has_text(s.page, "الحالة"),
            "tab_attendance": has_text(s.page, "الحضور"),
            "tab_payments": has_text(s.page, "المدفوعات"),
            "tab_curriculum": has_text(s.page, "المناهج"),
            "tab_evaluations": has_text(s.page, "التقييمات"),
            "tab_points": has_text(s.page, "النقاط"),
        }
        out["checks"].update(text_checks)

        lookup_visible = visible(s.page, "#lookup-card")
        lookup_text_visible = has_text(s.page, "أدخل الرقم الشخصي")
        out["checks"]["lookup_card_hidden"] = not lookup_visible
        out["checks"]["lookup_text_absent"] = not lookup_text_visible
        out["lookup_visible_raw"] = lookup_visible
        out["lookup_text_visible_raw"] = lookup_text_visible
        out["test_student_present"] = has_text(s.page, "Test Student")
        out["student_name_snippet"] = s.page.evaluate(
            r"""() => {const m=document.body.innerText.match(/اسم الطالب[\s\S]{0,80}/); return m? m[0] : null;}"""
        )

        out["tab_inventory"] = s.page.evaluate(
            r"""() => Array.from(document.querySelectorAll('a')).filter(a => /parent-hub/.test(a.getAttribute('href')||'')).map(a => ({href: a.getAttribute('href'), text: (a.innerText||'').trim().slice(0,40)}))"""
        )

        tab_targets = [
            ("attendance", "/portal/parent-hub/attendance"),
            ("payments", "/portal/parent-hub/payments"),
            ("curriculum", "/portal/parent-hub/curriculum"),
            ("evaluations", "/portal/parent-hub/evaluations"),
            ("points", "/portal/parent-hub/points"),
        ]
        for key, expected in tab_targets:
            sub = {"expected": expected}
            resp = s.navigate(expected)
            settle(s.page)
            try:
                sub["status"] = resp.status if resp else None
            except Exception:
                sub["status"] = None
            sub["landed_url"] = s.page.url
            sub["landed_directly"] = expected in s.page.url
            sub["screenshot"] = s.screenshot(f"student_subpage_{key}")
            out["subpages"][key] = sub
            s.navigate("/portal/parent")
            settle(s.page)

        out["console"] = list(s.get_console_errors())
        out["no_5xx"] = s.check_no_500()
        out["failing"] = s.failing_responses()
    return out


def run_role(role, landing_path, label, markers):
    out = {"name": role, "label": label, "checks": {}, "console": [], "markers_found": []}
    with BrowserSession(base_url=BASE, headless=True) as s:
        s.login_as(role)
        settle(s.page)
        # Capture immediate post-login URL
        out["post_login_url"] = s.page.url
        s.navigate(landing_path)
        settle(s.page, 2000)
        out["url"] = s.page.url
        out["title"] = s.page.title()
        out["screenshot"] = s.screenshot(f"{role}_landing")
        for m in markers:
            if has_text(s.page, m):
                out["markers_found"].append(m)
        out["checks"]["landed_on_target"] = landing_path in s.page.url
        out["checks"]["has_any_marker"] = len(out["markers_found"]) > 0
        if role == "parent":
            out["checks"]["NOT_student_card_view"] = not has_text(s.page, "STUDENT CARD")
        out["console"] = list(s.get_console_errors())
        out["no_5xx"] = s.check_no_500()
        out["failing"] = [r for r in s.failing_responses() if r.get("status", 0) >= 500]
    return out


def main():
    REPORT["personas"]["student_test"] = run_student()
    REPORT["personas"]["parent_test"]  = run_role(
        "parent", "/portal/parent", "parent (V1)",
        markers=["أولياء", "أبنائي", "ولي الأمر", "أبناء", "التقدم", "الرسم البياني", "آخر", "STUDENT CARD"]
    )
    REPORT["personas"]["admin_test"]   = run_role(
        "admin", "/dashboard", "admin",
        markers=["لوحة", "قاعدة البيانات", "الإحصائيات", "Dashboard", "المجموعات", "الحضور"]
    )
    REPORT["personas"]["teacher_test"] = run_role(
        "teacher", "/teacher/hub", "teacher",
        markers=["المعلم", "الحضور", "المجموعات", "النقاط", "تسجيل الدرس", "teacher"]
    )
    out_path = os.path.join(os.path.dirname(__file__), "report.json")
    with io.open(out_path, "w", encoding="utf-8") as f:
        json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
    print("WROTE", out_path)


if __name__ == "__main__":
    main()
