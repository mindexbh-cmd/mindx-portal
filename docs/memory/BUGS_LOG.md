# BUGS_LOG.md

Every notable bug encountered on the mindex-portal codebase, with root cause + fix + prevention. Maintained by `memory-keeper-agent`. Sourced from `fix:` commits and post-mortem conversations.

Total `fix:` commits (raw count): 149 as of 2026-05-15.

Format:
```
### YYYY-MM-DD: <bug title> [scope]
- **Symptom**: what users saw
- **Root cause**: actual bug
- **Fix**: what was changed
- **Prevention**: rule / test / guardrail added
- **Commit**: <hash>
```

---

## 2026-05 (recent — full detail)

### 2026-05-16: Testing the wrong flow — logged-in curl instead of the anonymous WhatsApp PID flow [testing discipline]
- **Symptom**: In the prior 2026-05-15 parent-routes session (ADR-014 / commits `31499e9` + `3712968`), Claude validated the unified-login redirects with logged-in `curl` requests against `/parent`. The validation looked green. Operators using the actual parent flow — receive WhatsApp link → land on `/parent?pid=...` anonymously → expect the PID-hub student card → tap into payments/evaluations — hit two real regressions that the curl-based test never exercised: (a) the student card was missing the "اسم الطالب" name row in `PORTAL_PARENT_PID_HUB_HTML`, and (b) `/parent/legacy?pid=<X>` flashed the anonymous CPR prompt UI for ~200 ms before the deep-link auto-lookup populated, looking broken to parents.
- **Root cause**: Test methodology mismatch. Claude assumed "if the redirect logic works for an authenticated session, it works in general" and shaped the verification around that assumption. Real parents are anonymous on first WhatsApp click, and the PID-hub deep-link path was outside the tested surface. Two issues that would have been obvious in a single manual browser walk-through (anonymous, with `?pid=` in the URL) went out the door.
- **Fix**: Commit `6a94497` — added `<div id="card-name">` row with "اسم الطالب" label to the PID-hub student card; added an inline `<script>` in `<head>` of `PARENT_HTML` that detects `?pid=` and adds `.has-deeplink-pid` to `<body>`, with matching CSS hiding `.pp-hero` + `#pp-lookup-card` so the prompt is suppressed instantly. (Both fixes are now mostly moot at the routing layer after commit `3ad90c1` retired the public PID flow per ADR-017, but they remain valuable for the one-release-cycle revert safety net.)
- **Prevention**: **Testing-discipline rule** — when the operator says "parents are seeing X" or describes a flow in their own words, test the EXACT flow they describe, not a logged-in approximation that's convenient to script. Specifically:
  1. WhatsApp deep-link flows must be tested anonymously with the query string actually carried (e.g. `?pid=<X>`), not as authenticated sessions.
  2. Curl is fine for redirect status codes but cannot detect UI flashes, missing labels, or above-the-fold content gaps — a Playwright walk-through of the same URL with the same auth state catches what curl misses.
  3. `real-user-tester-agent` persona scripts must include at least one anonymous-WhatsApp-deep-link persona, not just authenticated personas.
  4. The verification template for any future parent/student-facing surface change should explicitly enumerate auth states (`{anonymous, role=parent, role=student, role=admin}`) × entry URLs, and the deploy verification must hit each cell that the change touches.
- **Commit**: `6a94497` (fix), `3ad90c1` (subsequent consolidation per ADR-017 which moots the public PID flow entirely)

### 2026-05-15: `_pg_pool` NameError silently killed orphan-loss alarm [safety]
- **Symptom**: Boot logs never printed the books_v2 storage check. Data-loss surfaces were invisible.
- **Root cause**: `_books_v2_orphan_probe()` referenced `_pg_pool` which doesn't exist in this codebase. Wrapped in `try/except Exception` so the NameError was swallowed.
- **Fix**: Open a private `psycopg2.connect(DATABASE_URL)` like `_new_connection()` does; close in `finally`. Also added `/api/health{,/deep}` so deploy gating doesn't depend on boot logs.
- **Prevention**: ADR-005 + database-architect-agent's gotcha list. Hook for `app.py` syntax check on commit (precommit_check.py).
- **Commit**: f7e62c9

### 2026-05-14: White-square push notification badge
- **Symptom**: Push notifications showed a white square instead of the app icon on Android.
- **Root cause**: Badge image wasn't monochrome; Android needs a monochrome white-on-transparent silhouette.
- **Fix**: Generated monochrome badge PNG; also raised urgency on time-sensitive payloads.
- **Commit**: (fix(push): monochrome badge + stronger urgent)

### 2026-05-14: Push SyntaxError on history-table ternary
- **Symptom**: JS ReferenceError thrown on the admin push-history page, breaking the rest of the script.
- **Root cause**: A nested ternary that didn't parse cleanly inside the inline `<script>` block (the JS-escape conversion mangled `:` inside `${...}`).
- **Fix**: Refactored the ternary to an if/else.
- **Prevention**: Don't use nested ternaries inside template literals that are also Python-escaped.
- **Commit**: (fix(push): SyntaxError on history-table ternary line 2218)

### 2026-05-14: Parent shop cart debiting points immediately
- **Symptom**: Parents added items to cart and points were instantly deducted, even before checkout.
- **Root cause**: The cart-add endpoint was also calling the redemption-create logic.
- **Fix**: Cart now writes `requested` rows that don't affect balance until admin approves.
- **Prevention**: Tests would have caught this — added to e2e wishlist.
- **Commit**: (fix(parent-shop): cart checkout no longer debits immediately)

### 2026-05-13: Books library buttons not wired
- **Symptom**: "Add folder" and "ارفع أول كتاب" buttons did nothing.
- **Root cause**: New buttons in HTML, no JS handlers attached.
- **Fix**: Wired both to the existing modal-open handlers.
- **Commit**: (fix(books): wire 'ارفع أول كتاب' / 'رفع كتب' to real handler; fix(books): wire 'add folder' button to create modal)

### 2026-05-13: Chunked-upload SSL EOF on finalize
- **Symptom**: Large book uploads completed all chunks then failed at finalize with SSL EOF on Render.
- **Root cause**: psycopg2 connection idle-timed out during the long BYTEA-assembly step.
- **Fix**: Switched chunked uploads to write to disk instead of BYTEA; logged traceback and retry on SSL EOF.
- **Prevention**: Don't store >50 MB in BYTEA on Postgres over a 300 s gunicorn timeout.
- **Commit**: (fix(books): store chunked uploads on disk instead of BYTEA; fix(books): log traceback and retry on SSL EOF in chunked finalize)

### 2026-05-12: Parent portal failing on Unicode bidi marks in personal_id
- **Symptom**: ~10% of parents' login attempts silently returned "no student found" even when the PID was correct.
- **Root cause**: WhatsApp / iOS sometimes inserts invisible LRM/RLM/PDI characters when users paste an ID. The lookup compared exact-string and missed.
- **Fix**: Strip Unicode bidi marks from the PID at parse time.
- **Prevention**: Always normalise user-supplied IDs before exact match.
- **Commit**: (fix(parent-portal): tolerate Unicode bidi marks in personal_id lookups)

### 2026-05-12: parent-viewer HMAC token separator collision
- **Symptom**: ~10% of generated PDF-viewer tokens rejected as invalid.
- **Root cause**: Token used `:` as the separator; some base64-encoded payloads contained `:` legitimately.
- **Fix**: Switched separator to a character that doesn't appear in base64.
- **Commit**: (fix(parent-viewer): HMAC token separator collision)

### 2026-05-12: Postgres `lastrowid` returns wrong value in parent-store request
- **Symptom**: After cart checkout, the wrong order ID was returned to the parent.
- **Root cause**: SQLite's `lastrowid` doesn't map cleanly to Postgres; the wrapper's auto-`RETURNING id` was the right path but the call wasn't using it.
- **Fix**: Use `RETURNING id` explicitly via the wrapper.
- **Commit**: (fix(store): Postgres-safe lastrowid in parent_store_request)

### 2026-05-12: Rewards stale `image_url` when bytes missing
- **Symptom**: Some reward tiles showed broken-image icons after the admin re-uploaded an image.
- **Root cause**: Old `image_url` cached even after `image_bytes` was replaced; the booleans weren't distinguished cleanly.
- **Fix**: `_reward_serve_image_url` distinguishes empty boolean from None; stale URLs cleared.
- **Commit**: (fix: distinguish empty boolean from None in _reward_serve_image_url; fix: clear stale image_url for rewards with missing image_bytes)

## 2026-05 (earlier highlights — abbreviated)

- Push admin-send endpoint visibility and history (May 14)
- Push smart-timing permission prompt (May 14)
- TWA Bubblewrap version pinning saga (May 14–15) — culminated in 1.23.0 pinned, prior 1.19.0 didn't exist on npm
- Parent shop prize tile heights (May 14)
- Parent-shop "اطلب الآن" disable when points insufficient (May 14)
- Books orphan probe BYTEA-only recognition (May 13)
- Parent legacy auto-lookup from `?pid` query (May 12)
- Parent escaped-quote breaks PARENT_HTML JS (May 12)
- Points admin-purchase student search returning empty (May 12)
- Points allowlist swap to numeric usernames (May 12)
- Payment portal soft message when warning is set (May 11)
- Payment `missing_installment_type` surfaced instead of silent zeros (May 11)

## 2026-04 (early — summary)

- April was bug-finding and stabilization phase. Notable patterns:
  - Multiple "field undefined" JS errors as new fields were added to API responses but old clients didn't have fallbacks (driven into a discipline: always default-fallback in JS).
  - Many Excel-import field-mapping mismatches.
  - Group filter UX iteration (multiple commits "Fix group filter to show actual student groups from DB").
  - Custom-table modal column drift (lead to ADR-010 Sync Rule).

## Recurring bug categories (lessons learned)

1. **Postgres vs SQLite type strictness** (~15 commits). SQLite silently coerces; PG throws. Examples: `COALESCE(<ts_col>, '')`, `WHERE ts_col = ''`, inserting `''` into typed columns. → CLAUDE.md "Database type notes" now has this codified.
2. **Arabic encoding in source** (~10 commits). Raw Arabic mangled on round-trip. → ADR-002 + the entity/JS-escape convention.
3. **Inline JS template literal interpolation collisions** (~8 commits). Python `{}` substitution + JS `${}` template literals + Arabic entities = subtle escape bugs. → No simple rule; always test the rendered page.
4. **Schema drift between init_db and else-branch** (~6 commits). Forgot to add a column to one branch. → ADR-004 + database-architect-agent enforcing E-M-C.
5. **Excel imports breaking when columns renamed** (~10 commits). → Universal `/api/import` endpoint + `IMPORT_TABLE_KEYS` natural-key declaration.
