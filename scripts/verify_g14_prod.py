"""G14 prod verification — rewards shop UX.

Uses plain `requests.Session()` to keep the session cookie alive across
requests (headless Chromium has a recurring cookie-drop quirk on this
codebase — see BUGS_LOG 2026-05-21). Logs in as student_test, then
fetches the points page HTML and the rewards API, and asserts the four
G14 surfaces are live.

Usage:
    python scripts/verify_g14_prod.py --base https://mindx-portal-1.onrender.com
"""
import argparse
import sys

import requests


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://mindx-portal-1.onrender.com")
    args = ap.parse_args()

    BASE = args.base.rstrip("/")
    failed = []

    def check(label, ok, hint=""):
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}")
        if not ok:
            failed.append(label + (f" -- {hint}" if hint else ""))

    print(f"\n=== G14 verification against {BASE} ===\n")

    sess = requests.Session()
    sess.headers.update({"User-Agent": "g14-verify/1.0"})

    # 1. Login as student_test.
    r = sess.post(
        BASE + "/login",
        data={"username": "student_test", "password": "TestStudent2026!"},
        allow_redirects=True,
        timeout=30,
    )
    check(f"student_test login (final status={r.status_code}, "
          f"url={r.url})",
          r.status_code == 200 and "/login" not in r.url
          and "تسجيل الدخول" not in r.text[:500])

    # 2. Fetch the points-tab standalone page.
    r = sess.get(BASE + "/portal/parent-hub/points", timeout=30)
    html = r.text
    print(f"    (points page status={r.status_code}, "
          f"html_len={len(html)})")
    check("points page reachable as logged-in student",
          r.status_code == 200 and len(html) > 5000,
          f"status={r.status_code} len={len(html)}")

    # 3. Source-level assertions on the rendered HTML.
    print("\n[G14.1] reward image rendering")
    check("renderer reads r.image_url",
          "r.image_url" in html)
    check("onerror fallback to icon emoji",
          "onerror=\"this.outerHTML=" in html)
    check(".reward .ic img CSS shipped (zoom-in cursor)",
          "cursor:zoom-in" in html)

    print("\n[G14.2] lightbox modal")
    check("lightbox overlay (#rwLightbox) in DOM",
          'id="rwLightbox"' in html)
    check("openLightbox + closeLightbox JS shipped",
          "function openLightbox(src, title)" in html
          and "function closeLightbox" in html)
    check("ESC key handler shipped",
          "e.key === 'Escape'" in html or "e.key === 'Esc'" in html)
    check("delegated click listener on .reward .ic img",
          "closest('.reward .ic img')" in html)

    print("\n[G14.4] category tabs")
    check("🎮 ألعاب tab rendered (data-cat=toy)",
          'data-cat="toy"' in html and "🎮 ألعاب" in html)
    check("🍔 وجبات tab rendered (data-cat=food)",
          'data-cat="food"' in html and "🍔 وجبات" in html)
    check("setRewardCat function shipped",
          "function setRewardCat(cat)" in html)

    print("\n[G14.6] history sub-tab")
    check("🛍️ shop sub-tab rendered",
          'data-sub="shop"' in html and "🛍️ متجر المكافآت" in html)
    check("📋 history sub-tab rendered",
          'data-sub="history"' in html and "📋 مكافآتي السابقة" in html)
    check("pane-shop + pane-history wrappers in DOM",
          'id="pane-shop"' in html and 'id="pane-history"' in html)
    check("setRewardsTab function shipped",
          "function setRewardsTab(name)" in html)

    # 4. Backend data probe.
    print("\n[backend] reward data flow")
    r = sess.get(BASE + "/api/points/rewards", timeout=30)
    try:
        data = r.json()
    except Exception:
        data = {}
    rows = data.get("rows", [])
    with_img = [x for x in rows if (x.get("image_url") or "")]
    food = [x for x in rows if x.get("category_type") == "food"]
    toy = [x for x in rows if x.get("category_type") == "toy"]
    untyped = [x for x in rows if not (x.get("category_type") or "")]
    print(f"    (api status={r.status_code}, {len(rows)} rows, "
          f"{len(with_img)} with images, {len(toy)} toy, {len(food)} food, "
          f"{len(untyped)} untyped)")
    check("API returns >= 1 reward with image_url",
          r.status_code == 200 and len(rows) > 0 and len(with_img) > 0)
    check("API rewards bucket into toy + food + untyped",
          len(toy) > 0 or len(food) > 0)

    # 5. The dynamic image endpoint actually serves bytes.
    if with_img:
        # Pick the first reward with an image and probe the served bytes.
        sample = with_img[0]
        img_url = (sample.get("image_url") or "").strip()
        if not img_url.startswith("http"):
            img_url = BASE + img_url
        r = requests.get(img_url, timeout=30)
        ct = r.headers.get("Content-Type", "")
        print(f"    (image probe url={img_url}, status={r.status_code}, "
              f"ct={ct!r}, len={len(r.content)})")
        check(f"reward image #{sample.get('id')} serves bytes",
              r.status_code == 200
              and r.headers.get("Content-Type", "").startswith("image/")
              and len(r.content) > 500)

    # 6. Regression: admin reward management endpoint still works.
    print("\n[regression] admin still works")
    sess2 = requests.Session()
    sess2.post(
        BASE + "/login",
        data={"username": "admin_test", "password": "TestAdmin2026!"},
        allow_redirects=True,
        timeout=30,
    )
    r = sess2.get(BASE + "/api/points/rewards", timeout=30)
    try:
        admin_data = r.json()
    except Exception:
        admin_data = {}
    check(f"admin can list rewards (status={r.status_code})",
          r.status_code == 200 and admin_data.get("ok"))

    print("\n" + "=" * 60)
    if failed:
        print(f"G14 PROD VERIFY — FAILED ({len(failed)})")
        for f in failed:
            print(f"  - {f}")
        return 1
    print("G14 PROD VERIFY — ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
