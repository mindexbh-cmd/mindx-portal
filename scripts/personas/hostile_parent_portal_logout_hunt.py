# -*- coding: utf-8 -*-
import os, sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import os, sys, json
HERE = r"C:/Users/polyt/Documents/mindex-projects/mindx-portal/scripts"
sys.path.insert(0, HERE)
from auto_test import BrowserSession

BASE = "http://127.0.0.1:5000"

JS_ENUM = r"""
() => {
  const out = [];
  document.querySelectorAll("a, button, [onclick], [role=button]").forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return;
    const cs = getComputedStyle(el);
    out.push({
      tag: el.tagName,
      text: ((el.innerText || el.textContent || "") + "").trim().slice(0, 120),
      href: el.getAttribute("href") || null,
      onclick: el.getAttribute("onclick") || null,
      cursor: cs.cursor,
      x: Math.round(rect.x + rect.width / 2),
      y: Math.round(rect.y + rect.height / 2),
      w: Math.round(rect.width),
      h: Math.round(rect.height),
      id: el.id || null,
      cls: (el.className && el.className.toString) ? el.className.toString() : null
    });
  });
  const meta = document.querySelector("meta[http-equiv=refresh]");
  if (meta) out.push({_meta_refresh: meta.getAttribute("content")});
  return out;
}
"""


def real_login(s, u, p):
    s.navigate("/")
    s.page.fill("input[name=username]", u)
    s.page.fill("input[name=password]", p)
    with s.page.expect_navigation(wait_until="domcontentloaded"):
        s.page.click("button[type=submit]")
    if s.page.url.rstrip("/").endswith("/login"):
        raise RuntimeError("login fail url=" + s.page.url)
    return s.page.url


def classify(item):
    href = (item.get("href") or "").strip()
    oc = (item.get("onclick") or "").strip().lower()
    if href in ("/login", "/logout", "/api/logout"):
        return ("BAD:" + href.lstrip("/"), href)
    if href.startswith("javascript:"):
        return ("js_only", href)
    if "logout(" in oc:
        return ("BAD:onclick_logout", oc)
    if "location" in oc and "login" in oc:
        return ("BAD:onclick_login_redirect", oc)
    if "session.clear" in oc:
        return ("BAD:onclick_session_clear", oc)
    if href.startswith("/portal/parent-hub"):
        return ("sub_page", href)
    if href == "/portal/parent":
        return ("parent_hub", href)
    if href == "":
        return ("no_dest", "")
    return ("other", href)


def follow_link(s, href):
    """Probe a destination WITHOUT clobbering the test session.

    The session cookie is bound to the BrowserContext, and s.page.request
    re-uses that context, so a GET to /logout via s.page.request.get
    would actually log us out. We avoid that by skipping any href in
    SESSION_KILLERS and returning a synthetic "would clear session"
    response. For non-killer hrefs, fire a HEAD instead of GET so we
    learn the status code without executing the handler body."""
    if not href or href.startswith(("javascript:", "#", "mailto:", "tel:")):
        return None
    SESSION_KILLERS = ("/logout", "/api/logout")
    if href in SESSION_KILLERS:
        return {"note": "session_killer_skipped", "expected": "302 -> /login"}
    try:
        url = BASE + href if href.startswith("/") else href
        # Use HEAD to avoid running side-effect handlers. Falls back to GET
        # if the server doesn't support HEAD (404 / 405).
        r = s.page.request.head(url, max_redirects=0)
        if r.status in (404, 405):
            r = s.page.request.get(url, max_redirects=0)
        return {"status": r.status, "loc": r.headers.get("location")}
    except Exception as e:
        return {"err": str(e)}

print("part1 ok")


def run():
    report = {"persona": "student_test", "viewports": {}, "issues": []}
    for vp_name, vp in (("desktop", {"width":1280,"height":900}), ("mobile_360", {"width":360,"height":740})):
        sec = {"pages": {}}
        with BrowserSession(base_url=BASE, headless=True) as s:
            s.page.set_viewport_size(vp)
            sec["url_after_login"] = real_login(s, "student_test", "TestStudent2026!")
            print("[" + vp_name + "] post-login:", sec["url_after_login"])
            dialogs = []
            def _ond(d):
                dialogs.append({"t": d.type, "m": d.message})
                d.dismiss()
            s.page.on("dialog", _ond)

            PAGES = [
                ("/portal/parent",                "main_hub_card"),
                ("/portal/parent-hub",            "parent_hub_landing"),
                ("/portal/parent-hub/attendance", "attendance"),
                ("/portal/parent-hub/payments",   "payments"),
                ("/portal/parent-hub/curriculum", "curriculum"),
                ("/portal/parent-hub/evaluations","evaluations"),
                ("/portal/parent-hub/points",     "points"),
                ("/portal/parent-hub/messages",   "messages"),
            ]
            for path, label in PAGES:
                resp = s.page.goto(BASE + path, wait_until="domcontentloaded")
                final = s.page.url
                if final.rstrip("/").endswith("/login") or final == BASE + "/":
                    sec["pages"][label] = {"FATAL_redirect_to": final, "status": resp.status if resp else None}
                    report["issues"].append("[" + vp_name + "] " + path + " -> " + final)
                    continue
                s.page.wait_for_timeout(900)
                s.screenshot("hostile_" + vp_name + "_" + label)
                elems = s.page.evaluate(JS_ENUM)
                classified = []
                for it in elems:
                    if "_meta_refresh" in it:
                        report["issues"].append("[" + vp_name + "] " + label + " meta-refresh: " + str(it["_meta_refresh"]))
                        continue
                    k, t = classify(it)
                    rec = dict(it); rec["classification"]=k; rec["target"]=t
                    if k.startswith("BAD"):
                        rec["server_response"] = follow_link(s, it.get("href"))
                    classified.append(rec)
                sec["pages"][label] = {
                    "url": final,
                    "click_count": len(classified),
                    "destructive": [c for c in classified if c["classification"].startswith("BAD")],
                    "all": classified,
                }

            s.page.goto(BASE + "/portal/parent", wait_until="domcontentloaded")
            s.page.wait_for_timeout(1200)
            tab_results = []
            try:
                n = s.page.locator(".action-tab").count()
            except Exception:
                n = 0
            print("[" + vp_name + "] action_tab count =", n)
            for i in range(n):
                s.page.goto(BASE + "/portal/parent", wait_until="domcontentloaded")
                s.page.wait_for_timeout(1000)
                tab = s.page.locator(".action-tab").nth(i)
                txt = (tab.inner_text() or "").strip()
                href = tab.get_attribute("href") or ""
                try:
                    with s.page.expect_navigation(wait_until="domcontentloaded", timeout=5000):
                        tab.click()
                except Exception as e:
                    tab_results.append({"i":i,"label":txt,"href":href,"click_err":str(e),"final":s.page.url,"BAD":False})
                    continue
                final = s.page.url
                bad = final.rstrip("/").endswith("/login") or final == BASE + "/"
                tab_results.append({"i":i,"label":txt,"href":href,"final":final,"BAD":bad})
                if bad:
                    report["issues"].append("[" + vp_name + "] tab " + str(i) + " text=" + repr(txt) + " -> " + final)
            sec["action_tab_clicks"] = tab_results
            sec["seen_dialogs"] = dialogs
            sec["failing_non_api"] = [r for r in s.responses if r["status"] >= 400 and "/api/" not in r["url"]][:30]
            sec["console_errors"] = s.get_console_errors()
        report["viewports"][vp_name] = sec

    out = r"C:/Users/polyt/Documents/mindex-projects/mindx-portal/scripts/personas/hostile_parent_portal_report.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("=== REPORT ===")
    print(out)
    print("Issues:")
    for x in report["issues"]:
        print("  *", x)
    if not report["issues"]:
        print("  (none)")
    for vp_name in ("desktop", "mobile_360"):
        if vp_name not in report["viewports"]:
            continue
        print("--- Destructive per page [" + vp_name + "] ---")
        for label, data in report["viewports"][vp_name]["pages"].items():
            d = data.get("destructive") or []
            print("  " + label + ": " + str(len(d)) + " destructive / " + str(data.get("click_count")) + " total")
            for x in d:
                print("    [" + x["classification"] + "] text=" + str(x["text"][:60]) + " href=" + str(x["href"]) + " pos=(" + str(x["x"]) + "," + str(x["y"]) + ") resp=" + str(x.get("server_response")))


if __name__ == "__main__":
    run()
