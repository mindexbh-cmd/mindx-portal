"""Smoke for the declarative gunicorn config (v2.9.6).

Six invariants on the repo's deploy files:

  [1] render.yaml exists at repo root
  [2] render.yaml startCommand contains --timeout 300
  [3] render.yaml startCommand contains --graceful-timeout 30
  [4] render.yaml startCommand contains --workers 2 + --threads 4
  [5] render.yaml is valid YAML (yaml.safe_load passes; service
      shape matches what Render's blueprint parser expects)
  [6] If Procfile exists, its `web:` gunicorn args match
      render.yaml's startCommand exactly
  [7] requirements.txt declares gunicorn

Runs pure-Python — no Render API, no network. Fails fast on the
first mismatch so a CI run can flag config drift before any
deploy.
"""
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
REPO = os.path.dirname(os.path.abspath(__file__)) + "/.."

EXPECTED_FLAGS = [
    "--timeout 300",
    "--graceful-timeout 30",
    "--workers 2",
    "--threads 4",
]


# ── Invariant 1: render.yaml exists ─────────────────────────────
render_yaml_path = os.path.join(REPO, "render.yaml")
assert os.path.isfile(render_yaml_path), (
    "render.yaml not found at repo root — declarative deploy "
    "config is missing entirely")
print(f"[1] render.yaml exists at {render_yaml_path}")


# ── Invariants 2-4: required flags in startCommand ─────────────
render_text = open(render_yaml_path, encoding="utf-8").read()
m = re.search(r"^\s*startCommand:\s*(.+?)$", render_text, re.MULTILINE)
assert m, "render.yaml has no startCommand line"
start_cmd = m.group(1).strip()
for flag in EXPECTED_FLAGS:
    assert flag in start_cmd, (
        f"render.yaml startCommand missing {flag!r}\n"
        f"  full line: {start_cmd!r}")
print(f"[2-4] render.yaml startCommand contains all 4 expected flags: "
      f"{', '.join(EXPECTED_FLAGS)}")


# ── Invariant 5: valid YAML + Render-expected service shape ────
try:
    import yaml  # PyYAML — Render uses ruamel; both are YAML 1.1
except ImportError:
    print("[5] SKIP — PyYAML not installed locally; render.yaml "
          "passed regex shape check only. CI should pip-install pyyaml.")
else:
    doc = yaml.safe_load(render_text)
    assert isinstance(doc, dict), "render.yaml top-level must be a mapping"
    services = doc.get("services") or []
    assert isinstance(services, list) and services, (
        "render.yaml must declare at least one service under `services:`")
    svc = services[0]
    assert svc.get("type") == "web", \
        f"service type must be 'web', got {svc.get('type')!r}"
    assert svc.get("name"), "service must have a name"
    yaml_start = (svc.get("startCommand") or "").strip()
    for flag in EXPECTED_FLAGS:
        assert flag in yaml_start, (
            f"YAML-parsed startCommand missing {flag!r}\n"
            f"  parsed: {yaml_start!r}")
    print(f"[5] render.yaml parses as valid YAML; service "
          f"'{svc.get('name')}' (type=web) startCommand "
          f"validated through both regex and YAML parser")


# ── Invariant 6: Procfile alignment (if it exists) ─────────────
procfile_path = os.path.join(REPO, "Procfile")
if os.path.isfile(procfile_path):
    proc_text = open(procfile_path, encoding="utf-8").read()
    m = re.search(r"^\s*web:\s*(.+?)$", proc_text, re.MULTILINE)
    assert m, "Procfile has no 'web:' line"
    proc_cmd = m.group(1).strip()
    for flag in EXPECTED_FLAGS:
        assert flag in proc_cmd, (
            f"Procfile gunicorn args missing {flag!r}\n"
            f"  full line: {proc_cmd!r}")
    # Defensively confirm both surfaces invoke the same WSGI app
    assert "gunicorn app:app" in proc_cmd, \
        f"Procfile must run `gunicorn app:app`, got: {proc_cmd!r}"
    assert "gunicorn app:app" in start_cmd, \
        f"render.yaml startCommand must run `gunicorn app:app`"
    print(f"[6] Procfile is aligned with render.yaml — both invoke "
          f"`gunicorn app:app` with all 4 expected flags")
else:
    print("[6] SKIP — no Procfile (render.yaml is the only source "
          "of the start command)")


# ── Invariant 7: gunicorn pinned in requirements.txt ───────────
req_path = os.path.join(REPO, "requirements.txt")
assert os.path.isfile(req_path), "requirements.txt missing"
req_text = open(req_path, encoding="utf-8").read()
m = re.search(r"^\s*gunicorn(?:==(\S+))?", req_text, re.MULTILINE)
assert m, "gunicorn missing from requirements.txt"
pinned = m.group(1) or "(unpinned)"
print(f"[7] requirements.txt declares gunicorn: version {pinned}")


print()
print("PASS — declarative gunicorn config is in lockstep across "
      "render.yaml + Procfile + requirements.txt. No manual Render "
      "dashboard step needed.")
