"""Verify the 5 action tabs on /portal/parent after the attendance-message
column fix. Walks Mohammed (student persona) through each tab."""
from __future__ import annotations
import os, sys, json, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from auto_test import BrowserSession

TABS = [
    ("attendance",  "/portal/parent-hub/attendance"),
    ("payments",    "/portal/parent-hub/payments"),
    ("curriculum",  "/portal/parent-hub/curriculum"),
    ("evaluations", "/portal/parent-hub/evaluations"),
    ("points",      "/portal/parent-hub/points"),
]

def real_login(s, username, password):
    s.navigate("/")
    s.page.fill('input[name=username]', username)
    s.page.fill('input[name=password]', password)
    s.page.click('button[type=submit]')
    s.page.wait_for_load_state('networkidle', timeout=10000)

def main():
    results = []
    with BrowserSession(base_url="http://127.0.0.1:5000", headless=True) as s:
        real_login(s, "student_test", "TestStudent2026!")
        s.navigate("/portal/parent")
        try: s.page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        landing_url = s.page.url
        body_text = s.page.evaluate("() => document.body.innerText")
        s.screenshot("parent_hub_landing")
        # 5 action tabs visible?
        labels = ["الحضور", "المدفوعات", "المناهج", "التقييمات", "النقاط"]
        missing = [w for w in labels if w not in body_text]
        results.append({
            "step": "landing /portal/parent",
            "url": landing_url,
            "redirected_to_login": "/login" in landing_url,
            "redirected_to_root": landing_url.rstrip("/") == "http://127.0.0.1:5000",
            "body_chars": len(body_text),
            "missing_action_labels": missing,
            "card_marker": ("بطاقة" in body_text) or ("Test Student" in body_text),
        })

        for slug, path in TABS:
            before_n = len(s.responses)
            before_errs = len(s.console_errors)
            s.navigate(path)
            try: s.page.wait_for_load_state("networkidle", timeout=10000)
            except Exception: pass
            time.sleep(0.4)
            tab_url = s.page.url
            doc_status = None
            for r in s.responses[before_n:]:
                if path in r["url"] and r["method"] == "GET" and "/api/" not in r["url"]:
                    doc_status = r["status"]
                    break
            api_problems = [
                r for r in s.responses[before_n:]
                if r["status"] >= 400 and ("/api/" in r["url"])
            ]
            five_hundreds = [r for r in api_problems if r["status"] >= 500]
            body_text = s.page.evaluate("() => document.body.innerText")
            error_markers = ["خطأ في الاتصال", "فشل التحميل", "حدث خطأ", "Internal Server Error"]
            visible_errors = [m for m in error_markers if m in body_text]
            attendance_stats = None
            if slug == "attendance":
                attendance_stats = s.page.evaluate(
                    """() => {
                        const txt = document.body.innerText;
                        return {
                            has_present_label:  /حاضر|الحضور/.test(txt),
                            has_absent_label:   /غائب|غياب/.test(txt),
                            has_late_label:     /متأخر|تأخير/.test(txt),
                            has_percent_label:  /نسبة|%/.test(txt),
                        };
                    }"""
                )
            points_store = None
            if slug == "points":
                points_store = any(w in body_text for w in ["متجر", "مكافآت", "مكافأة", "جائزة"])
            s.screenshot(f"parent_hub_{slug}")
            results.append({
                "step": f"tab {slug}",
                "path": path,
                "url": tab_url,
                "doc_status": doc_status,
                "redirected_to_login": "/login" in tab_url,
                "redirected_to_root": tab_url.rstrip("/") == "http://127.0.0.1:5000",
                "api_problems": [
                    {"status": r["status"], "url": r["url"]} for r in api_problems
                ],
                "five_hundreds_count": len(five_hundreds),
                "visible_error_markers": visible_errors,
                "body_chars": len(body_text),
                "console_errors": s.console_errors[before_errs:],
                "attendance_stats": attendance_stats,
                "points_store_marker": points_store,
            })
    print(json.dumps(results, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
