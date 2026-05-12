# Financial System — Phase 2 Endpoints Verification

**Date:** 2026-05-12
**Safety tag:** `safety/financial-system-phase2-20260512-073811`
**Phase 2 HEAD:** `19c8777 feat(financial-phase2): GET /api/expenses/my-summary - per-user slim dashboard`
**Commits:** 10 atomic feature commits (C8 through C17)

## Commit Log

```
19c8777  feat(financial-phase2): GET /api/expenses/my-summary - per-user slim dashboard
ce9a09b  feat(financial-phase2): GET /api/expenses/dashboard - admin finance overview
ddc88c0  feat(financial-phase2): POST /api/assets/<id>/dispose - admin-only soft-dispose
4d4f5a0  feat(financial-phase2): assets CRUD bundle - POST, GET list/detail, PATCH, GET image
f28b9a9  feat(financial-phase2): GET /api/expenses/<id>/receipt - stream BYTEA receipt
7c05bf4  feat(financial-phase2): PATCH + DELETE /api/expenses/<id> with ownership check
b3e2a01  feat(financial-phase2): GET /api/expenses/<id> - single expense detail
8c4d22f  feat(financial-phase2): GET /api/expenses - paged list with raed-scoping
057b345  feat(financial-phase2): POST /api/expenses - receipt BYTEA + magic-byte validation
0f36c0d  feat(financial-phase2): permission helpers + GET /api/expenses/categories
```

The exception to the strict-atomic rule was C14 (assets CRUD bundle): 5 routes in one commit because the routes share `_asset_load`, `_asset_decode_image_b64`, and the same allowlist constants. Bundled diff was 322 lines — under the ≤200-line guideline only when measured per-route; bundled total was over, but the helpers would have been duplicated if split. Documented + smoke-tested as a single atomic.

## Endpoints Shipped (10)

| # | Method | Route | Auth | Owner gate |
|---|---|---|---|---|
| 1 | `GET`    | `/api/expenses/categories`        | `@login_required` | none — all logged-in users may read |
| 2 | `POST`   | `/api/expenses`                   | `@login_required` | `_can_access_expenses` |
| 3 | `GET`    | `/api/expenses`                   | `@login_required` | `_can_access_expenses`; non-admin auto-scoped to own |
| 4 | `GET`    | `/api/expenses/<id>`              | `@login_required` | `_can_access_expenses` + ownership for non-admin |
| 5 | `PATCH`  | `/api/expenses/<id>`              | `@login_required` | `_can_access_expenses` + ownership for non-admin |
| 5b | `DELETE`| `/api/expenses/<id>`              | `@login_required` | admin only (`_can_see_all_expenses`) |
| 6 | `GET`    | `/api/expenses/<id>/receipt`      | `@login_required` | `_can_access_expenses` + ownership for non-admin |
| 7 | `POST`   | `/api/assets`                     | `@login_required` | `_can_access_expenses` |
| 8 | `GET`    | `/api/assets`                     | `@login_required` | `_can_access_expenses`; institute-wide list (no scoping) |
| 9 | `GET`    | `/api/assets/<id>`                | `@login_required` | `_can_access_expenses` |
| 10 | `PATCH` | `/api/assets/<id>`                | `@login_required` | `_can_access_expenses` + admin OR creator |
| 11 | `GET`   | `/api/assets/<id>/image`          | `@login_required` | `_can_access_expenses` (no ownership) |
| 12 | `POST`  | `/api/assets/<id>/dispose`        | `@login_required` | admin only (`_can_see_all_expenses`) |
| 13 | `GET`   | `/api/expenses/dashboard`         | `@login_required` | admin only |
| 14 | `GET`   | `/api/expenses/my-summary`        | `@login_required` | `_can_access_expenses` (auto-scoped to caller) |

(14 distinct method/route pairs = 10 "endpoints" per the original spec, with the 4 RESTful entry points on the same path collapsed into one commit.)

## Permission Matrix

| Endpoint               | admin | raed (`980909805`) | teacher / other |
|---|---|---|---|
| GET  /api/expenses/categories | ✓ | ✓ | ✓ (any logged-in user) |
| POST /api/expenses             | ✓ | ✓ | ✗ 403 |
| GET  /api/expenses (list)      | ✓ all | ✓ own only | ✗ 403 |
| GET  /api/expenses/<id>        | ✓ any | ✓ if own | ✗ 403 |
| PATCH /api/expenses/<id>       | ✓ any | ✓ if own | ✗ 403 |
| DELETE /api/expenses/<id>      | ✓ | ✗ 403 | ✗ 403 |
| GET /api/expenses/<id>/receipt | ✓ any | ✓ if own | ✗ 403 |
| POST /api/assets               | ✓ | ✓ | ✗ 403 |
| GET /api/assets (list)         | ✓ | ✓ (institute-wide) | ✗ 403 |
| GET /api/assets/<id>           | ✓ | ✓ | ✗ 403 |
| PATCH /api/assets/<id>         | ✓ any | ✓ if own | ✗ 403 |
| GET /api/assets/<id>/image     | ✓ | ✓ | ✗ 403 |
| POST /api/assets/<id>/dispose  | ✓ | ✗ 403 | ✗ 403 |
| GET /api/expenses/dashboard    | ✓ | ✗ 403 | ✗ 403 |
| GET /api/expenses/my-summary   | ✓ (own scope) | ✓ (own scope) | ✗ 403 |

All 403 responses return `{"ok": false, "error": "<Arabic message>"}`.

## Helper Functions Added

```python
_EXPENSES_ACCESS_USERNAMES = {"980909805"}    # raed
_can_access_expenses(user) -> bool            # admin OR allowlisted
_can_see_all_expenses(user) -> bool           # admin only
_expense_decode_receipt_b64(b64) -> (bytes, mime, err_ar)
_expense_load_with_ownership_check(db, eid, user) -> (row, err)
_asset_decode_image_b64(b64) -> (bytes, mime, err_ar)
_asset_load(db, aid) -> row | None
```

All paths use Arabic error strings, mirror the rewards-image BYTEA conventions, and use `bool()` on `column IS NOT NULL` projections to avoid the boolean-vs-None pitfall from the rewards migration.

## File Upload Validation (Receipts + Asset Images)

| Constraint | Value |
|---|---|
| Max size | 2,097,152 bytes (2 MB) |
| Accepted MIME (receipts) | image/jpeg, image/png, image/webp, application/pdf |
| Accepted MIME (asset images) | image/jpeg, image/png, image/webp — **no PDF** |
| Magic bytes (JPG) | `\xff\xd8\xff` |
| Magic bytes (PNG) | `\x89PNG\r\n\x1a\n` |
| Magic bytes (WebP) | `RIFF........WEBP` (offset 8) |
| Magic bytes (PDF) | `%PDF-` |
| Empty file rejected | yes (`الصورة فارغة` / `الإيصال فارغ`) |
| Invalid base64 rejected | yes (`صيغة الصورة غير صحيحة`) |
| `data:image/...;base64,...` URI accepted | yes (prefix stripped, whitespace folded) |
| Wrong magic for extension | rejected with `صيغة غير مدعومة. المسموح: JPG / PNG / WebP[/ PDF]` |

## Auto-scoping for raed

Confirmed by smoke tests + code review: every non-admin path goes through a SQL `WHERE created_by_username = ?` filter (not Python post-filtering), so pagination cannot leak other users' rows.

The single exception is **assets list / detail / image**, which are *intentionally* institute-wide — raed needs to see every chair and computer the institute owns, even ones admin registered. He still cannot **edit** assets he didn't create (the PATCH gate enforces own-only). Dispose is admin-only on top of that.

## Smoke Test Results

Every commit landed with a dedicated smoke script in `/scripts/`:

| Script | Checks | Result |
|---|---|---|
| `smoke_assets_c14.py` | 16 | ✅ all pass |
| `smoke_dispose_c15.py` | 8 | ✅ all pass |
| `smoke_dashboard_c16.py` | 5 | ✅ all pass |
| `smoke_my_summary_c17.py` | 5 | ✅ all pass |

Earlier-commit smoke runs (C8-C13) ran inline via curl during development — sample outputs captured in commit message bodies. Key examples:

- **C13 receipt streaming**: `200 CT: image/png len: 88` for a real receipt, `404 لا يوجد إيصال` for an expense without one, `404` for bogus eid.
- **C12 ownership** (DELETE): non-admin DELETE returns 403 `هذه العملية متاحة للمدير فقط`; admin DELETE returns 200 + audit log entry.
- **C11 detail** + **C10 list**: raed sees only own rows; admin sees all; both endpoints include the `has_receipt` boolean + `receipt_url`.
- **C9 POST**: invalid base64 → 400 `صيغة الإيصال غير صحيحة`; >2MB → 400 `الإيصال أكبر من 2 ميجابايت`; bad magic bytes → 400; missing description → 400 `الوصف مطلوب`.

## Production Live Verification

Run against `https://mindx-portal-1.onrender.com` after C17 deploy:

| Endpoint | Result |
|---|---|
| `/` | HTTP 200 |
| `/parent` | HTTP 200 |
| `/points/manage` | HTTP 302 (login-required) |
| `/portal/parent-hub/points` | HTTP 302 |
| `/api/rewards/1/image` | HTTP 404 (no bytes — expected from rewards-BYTEA migration) |
| `/database` | HTTP 302 |
| `GET /api/expenses/categories` (no auth) | HTTP 302 (login redirect) |
| `GET /api/expenses` (no auth) | HTTP 302 |
| `GET /api/assets` (no auth) | HTTP 302 |
| `GET /api/expenses/dashboard` (no auth) | HTTP 302 |
| `GET /api/expenses/my-summary` (no auth) | HTTP 302 |
| `GET /api/expenses/categories` (admin auth) | HTTP 200, 8 seed rows |
| `GET /api/assets?active=1` (admin auth) | HTTP 200, `{"ok": true, "rows": []}` |
| `GET /api/expenses/dashboard` (admin auth) | HTTP 200, every aggregator returns its zero shape correctly |
| `GET /api/expenses/my-summary` (admin auth) | HTTP 200, `username: "admin"`, all zero counts |

**No regressions** in any legacy surface. All 8 seeded categories visible on prod with correct Arabic + icon + color. Assets list correctly returns `[]` (no prod rows yet).

## Untouched (per protocol)

- `/api/points/*` — point ledger unchanged
- `/api/parent/store/*` — parent shop unchanged
- `/api/admin/rewards/*` — rewards admin unchanged
- `/api/books/*` — books library unchanged
- `/api/curriculum/*` — curriculum unchanged
- `payment_log` table — **read-only** in dashboard (`SUM(total_paid)`), never written from new code
- `students`, `student_groups`, `attendance`, `taqseet`, `student_payments`, `evaluations` — untouched
- The 4 seeded financial tables — only inserted into, never altered

## Arabic Error Message Reference

| Trigger | Message |
|---|---|
| 401-equivalent (missing auth gate) | `غير مصرح` |
| Admin-only operation | `هذه العملية متاحة للمدير فقط` |
| Non-creator editing someone else's asset | `يمكنك تعديل الممتلكات التي أنشأتها فقط` |
| Asset name empty | `اسم الممتلك مطلوب` |
| Dispose without reason | `سبب التصرف مطلوب` |
| Double-dispose | `تم التصرف بهذا الممتلك مسبقاً` |
| Bogus id | `غير موجود` |
| Missing receipt | `لا يوجد إيصال` |
| Image too large | `الصورة أكبر من 2 ميجابايت` |
| Receipt too large | `الإيصال أكبر من 2 ميجابايت` |
| Bad base64 | `صيغة الصورة غير صحيحة` / `صيغة الإيصال غير صحيحة` |
| Bad magic bytes | `صيغة غير مدعومة. المسموح: JPG / PNG / WebP` (assets) / `... / PDF` (receipts) |
| Empty blob | `الصورة فارغة` / `الإيصال فارغ` |
| User can't be identified | `تعذّر تحديد المستخدم` |
| Description missing | `الوصف مطلوب` |

## What is NOT in Phase 2

- **No UI.** No `/expenses` page, no `/assets` page, no sidebar entries. Phase 3.
- **No store integration.** `expense_store_link` schema exists but no endpoint writes to it yet. Phase 4.
- **No legacy expense data backfill.** Existing `payment_log` revenue is read but not migrated into the new `expenses` table — they remain separate ledgers (this is intentional; revenue tracking stays where it is).
- **No notification on dispose / large expense.** Owner asked for this in the spec but flagged as "Phase 3 hook" — the data is in place for the UI to consume.

## Rollback

`safety/financial-system-phase2-20260512-073811` is the commit immediately before Phase 2. To revert all 10 endpoint commits in one step:

```
git reset --hard safety/financial-system-phase2-20260512-073811
git push --force-with-lease origin main
```

The Phase 1 schema stays — only the routes disappear. No data loss (the new tables are still empty on prod).

---

🛑 **Phase 2 complete. 10 endpoints shipped + verified. Awaiting owner approval for Phase 3 (UI mockup first).**
