# Catastrophe-prevention report — "add a footer with the centre slogan to /login"

**Timestamp:** 2026-05-15 20:46:54 UTC
**Slug:** add-footer-slogan
**Reviewer:** catastrophe-prevention-agent (DEMO)

---

## ✅ VERDICT: APPROVE — proceed safely

**Categories cleared:** 1, 2, 3, 4. **Category 5 has one soft note** (Arabic encoding rule).

---

## Phase 1 — Scan

Proposed change: **add a small footer at the bottom of `/login` with the text "Play · Enjoy · Learn"**.

Surface area:
- `LOGIN_HTML` constant in `app.py` (~line 9700).
- No new routes, no DB writes, no auth changes, no API consumers.
- The slogan already appears in the existing `.centre-slogan` div near the top of the form — adding it as a footer would be **duplicate-but-harmless**. Could also be a different microcopy.

Applicable categories: **5 only** (UX surface change, additive).

---

## Phase 2 — Deep check

### Category 1 — Data loss (N/A)

No DB writes. No DDL. No row mutations. ✅

### Category 2 — Breaking changes (N/A)

No route, function, ID, or class is removed or renamed. The change is **purely additive**: one new `<div class="footer">` element at the end of the form box. ✅

### Category 3 — Security (N/A)

The footer string is static content. No user input rendered. No auth surface touched. The Arabic-entity-encoding rule (CLAUDE.md "Working with Arabic text") prevents accidental mojibake on the Render round-trip — soft Category 5 note below.

### Category 4 — Performance (N/A)

A static `<div>` adds ~50 bytes to the HTML response. No queries, no JS, no fetches. Network impact: negligible. ✅

### Category 5 — UX (1 soft condition)

- ✅ Login flow not changed.
- ✅ Navigation not changed.
- ✅ Mobile viewport: the existing `.box` has `width:380px` and `padding:40px 36px`. A small footer line at the bottom fits without affecting the form. Verify at 360 px via `mobile-first-agent` after the change.
- ⚠️ **Soft condition**: if the footer text is Arabic, it MUST be entity-encoded per the LOGIN_HTML convention (`&#x627;&#x644;&#x645;...`). Raw Arabic in `app.py` gets mangled on Windows/Render round-trip (CLAUDE.md ADR-002). If it's the English slogan "Play · Enjoy · Learn", just use ASCII + the middle-dot `&middot;` entity as the existing `.centre-slogan` does.
- ✅ No destructive action introduced.
- ✅ No error message introduced.

---

## Always-on scan results

| Check | Result |
|---|---|
| Secret scan | clean |
| `@login_required` count | 366 (baseline preserved) |
| `/api/health` | green (last deploy) |
| `/login` | 200 |
| `/portal/parent-hub` anonymous | 302 → /login (correct) |
| Test users intact | yes (4 `*_test` accounts) |
| Render Starter sanity | not affected |

---

## Requirements met

- Change is purely additive.
- No user-data row at risk.
- No route or auth boundary touched.
- No performance impact.
- Existing mobile / Arabic / RTL conventions easy to follow.

## Verification plan (before commit)

1. `python -c "import ast; ast.parse(open('app.py', encoding='utf-8').read())"` — syntax sanity.
2. `python app.py` + `curl http://127.0.0.1:5000/login` — confirm the new footer renders.
3. Screenshot at 360 px viewport (`/screenshots /login`) — confirm no layout overflow.
4. If Arabic text: run `arabic-quality-agent` for the encoding + grammar check.

## Recommended follow-up

After the commit, run `/test` for the local e2e smoke (login test is in the 8/8 suite) — that's enough verification for a static-text change. Then `/deploy <slug>` ships it.

---

**Logged to:** `docs/memory/CATASTROPHE_LOG.md` (APPROVE row).
