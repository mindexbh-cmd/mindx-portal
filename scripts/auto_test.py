"""Browser test helpers built on Playwright (sync API).

This module is a *library*; import it from e2e runners. The convention
is one BrowserSession per test scenario:

    from scripts.auto_test import BrowserSession
    with BrowserSession(base_url="http://localhost:5000") as s:
        s.login_as("admin")
        s.navigate("/dashboard")
        s.screenshot("dashboard")
        assert s.check_no_500()
        assert s.get_console_errors() == []

The session captures every HTTP response so check_no_500() can fail
fast on a server error even if the UI doesn't surface it visibly.
Screenshots land in scripts/screenshots/<name>-<timestamp>.png.

Test credentials are sourced from scripts/seed_test_users.py — run
that first, otherwise login_as() will fail.
"""
from __future__ import annotations
import os
import time
from contextlib import contextmanager
from typing import List, Optional


# Mirrors scripts/seed_test_users.py. Keep these in lockstep.
TEST_CREDENTIALS = {
    "admin":   ("admin_test",   "TestAdmin2026!"),
    "teacher": ("teacher_test", "TestTeacher2026!"),
    "student": ("student_test", "TestStudent2026!"),
    "parent":  ("parent_test",  "TestParent2026!"),
}


SCREENSHOT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "screenshots")


def _ensure_screenshot_dir() -> str:
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    return SCREENSHOT_DIR


class BrowserSession:
    def __init__(self, base_url: str = "http://localhost:5000",
                 headless: bool = True, slow_mo: int = 0):
        from playwright.sync_api import sync_playwright  # type: ignore
        self.base_url = base_url.rstrip("/")
        self._pw_cm = sync_playwright()
        self._pw = None
        self._browser = None
        self._context = None
        self.page = None
        self.headless = headless
        self.slow_mo = slow_mo
        self.responses: List[dict] = []
        self.console_errors: List[str] = []

    def __enter__(self):
        self._pw = self._pw_cm.__enter__()
        self._browser = self._pw.chromium.launch(
            headless=self.headless, slow_mo=self.slow_mo)
        self._context = self._browser.new_context()
        self.page = self._context.new_page()
        # Capture every response so check_no_500() can see the whole
        # picture, not just the last nav.
        def _on_response(resp):
            try:
                self.responses.append({
                    "status": resp.status,
                    "url": resp.url,
                    "method": resp.request.method,
                })
            except Exception:
                pass
        def _on_console(msg):
            try:
                if msg.type == "error":
                    self.console_errors.append(msg.text)
            except Exception:
                pass
        self.page.on("response", _on_response)
        self.page.on("console", _on_console)
        self.page.on("pageerror", lambda exc:
                     self.console_errors.append("pageerror: " + str(exc)))
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
        finally:
            self._pw_cm.__exit__(exc_type, exc, tb)

    # ── Core actions ─────────────────────────────────────────────────
    def navigate(self, path: str, wait_until: str = "domcontentloaded"):
        url = path if path.startswith("http") else (self.base_url + path)
        return self.page.goto(url, wait_until=wait_until)

    def login_as(self, role: str):
        """Log in via the standard /login form using the test creds.

        role must be one of admin / teacher / student / parent.
        Raises RuntimeError if the post-login URL is still /login
        (the login form re-renders on bad creds — easy way to detect
        a seed problem)."""
        if role not in TEST_CREDENTIALS:
            raise ValueError(f"unknown test role: {role!r}")
        username, password = TEST_CREDENTIALS[role]
        self.navigate("/")
        # The login form posts to /login with form fields named
        # username / password. We submit via form-post instead of
        # clicking so we don't depend on the button's selector text
        # (Arabic, HTML-entity-encoded).
        self.page.evaluate(
            """([u, p]) => {
                const f = document.createElement('form');
                f.method = 'POST'; f.action = '/login';
                for (const [k, v] of [['username', u], ['password', p]]) {
                    const i = document.createElement('input');
                    i.name = k; i.value = v; f.appendChild(i);
                }
                document.body.appendChild(f); f.submit();
            }""", [username, password])
        # Wait for the post-login navigation to settle.
        self.page.wait_for_load_state("domcontentloaded")
        if self.page.url.rstrip("/").endswith("/login"):
            raise RuntimeError(
                f"login failed for role={role} -- still on /login "
                f"(check seed_test_users.py was run; current url={self.page.url})")

    def click_button(self, selector: str, timeout_ms: int = 5000):
        self.page.click(selector, timeout=timeout_ms)

    def fill(self, selector: str, value: str, timeout_ms: int = 5000):
        self.page.fill(selector, value, timeout=timeout_ms)

    def screenshot(self, name: str) -> str:
        d = _ensure_screenshot_dir()
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = os.path.join(d, f"{name}-{ts}.png")
        self.page.screenshot(path=path, full_page=True)
        return path

    # ── Assertions ───────────────────────────────────────────────────
    def get_console_errors(self) -> List[str]:
        return list(self.console_errors)

    def check_no_500(self) -> bool:
        """Return True when no response in the session was a 5xx."""
        return not any(r["status"] >= 500 for r in self.responses)

    def failing_responses(self) -> List[dict]:
        """All non-2xx/3xx responses captured so far — useful for
        debugging when check_no_500 fails."""
        return [r for r in self.responses if r["status"] >= 400]


@contextmanager
def open_session(*args, **kwargs):
    """Convenience wrapper so callers can write:
        with open_session(headless=False) as s: ..."""
    with BrowserSession(*args, **kwargs) as s:
        yield s
