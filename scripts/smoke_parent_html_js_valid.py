"""Validate that every <script> block in the parent-side HTML
constants parses cleanly as JavaScript.

Catches the class of bug where a Python non-raw triple-quoted
string decodes backslash escapes BEFORE serving (e.g. `\\'` becomes
`'`), leaving inner quotes inside a single-quoted JS string
literal — which causes the browser to throw a SyntaxError and
discard the ENTIRE <script> block, silently disabling every
function in it.

The smoke imports app.py and inspects each module-level constant
directly (no test client, no auth needed). Every <script>…</script>
block in each constant is fed into `node -e "new Function(<body>)"`
and any SyntaxError fails the smoke loudly.

Constants checked:
  • PARENT_HTML                  (legacy /parent/legacy flow)
  • PORTAL_PARENT_PID_HUB_HTML   (v2.8 public hub at /parent)
  • PORTAL_PARENT_HUB_HTML       (logged-in hub /portal/parent-hub)
"""
import os, sys, io, re, subprocess, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

# Ensure node is available
try:
    rv = subprocess.run(["node", "--version"], capture_output=True,
                        text=True, timeout=15)
    if rv.returncode != 0:
        print("FATAL: node returned non-zero:", rv.returncode)
        sys.exit(2)
    print(f"[env] node {rv.stdout.strip()}")
except FileNotFoundError:
    print("FATAL: node not on PATH — install node.js and re-run")
    sys.exit(2)

CONSTANTS = [
    "PARENT_HTML",
    "PORTAL_PARENT_PID_HUB_HTML",
    "PORTAL_PARENT_HUB_HTML",
]

SCRIPT_RE = re.compile(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>",
                       re.IGNORECASE)

failures = []

def _check(label, body, ctx):
    if not body.strip():
        return True
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js",
                                     delete=False,
                                     encoding="utf-8") as fp:
        fp.write(body); fp.flush(); path = fp.name
    try:
        rv = subprocess.run(
            ["node", "-e",
             "try { new Function(require('fs').readFileSync("
             f"'{path.replace(chr(92), '/')}','utf8')); "
             "console.log('OK'); } catch(e){ "
             "console.log('ERR:'+e.message); process.exit(1); }"],
            capture_output=True, text=True, timeout=30)
        out = (rv.stdout or "").strip() + (rv.stderr or "").strip()
        if rv.returncode == 0 and "OK" in out:
            print(f"     ✓ {ctx}: {label} parses cleanly "
                  f"({len(body)} chars)")
            return True
        msg = out.split("ERR:", 1)[1].strip() if "ERR:" in out else out
        # Bisect to find the first failing line
        lines = body.split("\n")
        bad_line = -1
        lo, hi = 1, len(lines)
        while lo < hi:
            mid = (lo + hi) // 2
            sub = "\n".join(lines[:mid])
            with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".js", delete=False,
                    encoding="utf-8") as fp2:
                fp2.write(sub); fp2.flush(); p2 = fp2.name
            rv2 = subprocess.run(
                ["node", "-e",
                 "try { new Function(require('fs').readFileSync("
                 f"'{p2.replace(chr(92), '/')}','utf8')); "
                 "} catch(e){ process.exit(1); }"],
                capture_output=True, timeout=15)
            try: os.unlink(p2)
            except: pass
            if rv2.returncode != 0:
                hi = mid
            else:
                lo = mid + 1
        bad_line = lo
        snippet = (lines[bad_line - 1] if bad_line - 1 < len(lines)
                   else "").strip()
        print(f"     ✗ {ctx}: {label} FAILED — {msg}")
        if bad_line > 0:
            print(f"       first bad line ≈ {bad_line}: "
                  f"{snippet[:160]}")
        failures.append({
            "ctx": ctx, "label": label, "error": msg,
            "bad_line": bad_line, "snippet": snippet[:200],
        })
        return False
    finally:
        try: os.unlink(path)
        except: pass

for cname in CONSTANTS:
    constant = getattr(A, cname, None)
    if constant is None:
        print(f"[{cname}] MISSING — not defined in app.py")
        failures.append({"ctx": cname, "label": "constant",
                         "error": "not defined"})
        continue
    print(f"[{cname}] {len(constant)} chars")
    blocks = SCRIPT_RE.findall(constant)
    print(f"     {len(blocks)} <script> block(s)")
    if not blocks:
        print("     ⚠ no <script> blocks — nothing to validate")
        continue
    for idx, body in enumerate(blocks, 1):
        _check(f"block #{idx}", body, cname)

print()
if failures:
    print(f"FAIL: {len(failures)} script block(s) have syntax errors:")
    for f in failures:
        print(f"  - {f['ctx']} {f['label']} line "
              f"~{f.get('bad_line', '?')}: {f['error']}")
        if f.get("snippet"):
            print(f"      → {f['snippet']}")
    sys.exit(1)

print("All parent-side <script> blocks parse cleanly.")
