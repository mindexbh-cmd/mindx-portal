# Financial System — Phase 1 Schema Verification

**Date:** 2026-05-12
**Safety tag:** `safety/financial-system-phase1-20260512-062303`
**Phase 1 HEAD:** `b71ee21 migration: add indexes + register financial tables in audit classification`

## Commit Log

```
b71ee21  migration: add indexes + register financial tables in audit classification
fd43d6e  migration: create expense_store_link table
5fe6e21  migration: create assets table
6ad6c88  migration: create expenses table
65a73fe  migration: seed default expense categories
e6ac0a2  migration: create expense_categories table
```

6 commits shipped. C7 (this report) is the 7th. The spec listed indexes and audit registration as separate steps; bundled into C6 since both are mechanical "register the new tables" housekeeping that finalize the schema for Phase 1.

## New Tables (column dumps verified via `PRAGMA table_info` locally + production `/api/admin/table-audit`)

### 1. `expense_categories`

```sql
id          INTEGER PRIMARY KEY AUTOINCREMENT
name_ar     TEXT NOT NULL
icon        TEXT DEFAULT ''
color       TEXT DEFAULT '#6B3FA0'
is_active   INTEGER DEFAULT 1
sort_order  INTEGER DEFAULT 0
created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
```

### 2. `expenses`

```sql
id                      INTEGER PRIMARY KEY AUTOINCREMENT
category_id             INTEGER REFERENCES expense_categories(id)
amount                  NUMERIC(10,3)
description             TEXT NOT NULL
vendor_name             TEXT DEFAULT ''
payment_method          TEXT DEFAULT 'cash'
expense_date            DATE NOT NULL
receipt_bytes           BYTEA
receipt_mime            TEXT DEFAULT ''
receipt_filename        TEXT DEFAULT ''
notes                   TEXT DEFAULT ''
created_by_username     TEXT NOT NULL
created_at              DATETIME DEFAULT CURRENT_TIMESTAMP
updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP
```

### 3. `assets`

```sql
id                      INTEGER PRIMARY KEY AUTOINCREMENT
name_ar                 TEXT NOT NULL
category                TEXT DEFAULT ''
serial_number           TEXT DEFAULT ''
image_bytes             BYTEA
image_mime              TEXT DEFAULT ''
location                TEXT DEFAULT ''
condition               TEXT DEFAULT 'good'
responsible_person      TEXT DEFAULT ''
purchase_date           DATE
purchase_price          NUMERIC(10,3) DEFAULT 0
vendor_name             TEXT DEFAULT ''
linked_expense_id       INTEGER REFERENCES expenses(id) ON DELETE SET NULL
useful_life_years       INTEGER DEFAULT 5
last_maintenance_date   DATE
maintenance_notes       TEXT DEFAULT ''
next_maintenance_date   DATE
is_disposed             INTEGER DEFAULT 0
disposed_at             DATETIME
disposal_reason         TEXT DEFAULT ''
created_by_username     TEXT NOT NULL
created_at              DATETIME DEFAULT CURRENT_TIMESTAMP
updated_at              DATETIME DEFAULT CURRENT_TIMESTAMP
```

### 4. `expense_store_link`

```sql
id          INTEGER PRIMARY KEY AUTOINCREMENT
expense_id  INTEGER REFERENCES expenses(id) ON DELETE CASCADE
reward_id   INTEGER REFERENCES rewards(id)
quantity    INTEGER NOT NULL
unit_cost   NUMERIC(10,3) NOT NULL
created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
```

## Seeded Default Categories (verified live on prod: 8 rows in `expense_categories`)

| id | sort | name_ar | icon | color |
|---|---|---|---|---|
| 1 | 0 | تشغيلي (إيجار/كهرباء/إنترنت) | 🏢 | #1976D2 |
| 2 | 1 | رواتب وأجور | 💵 | #388E3C |
| 3 | 2 | مشتريات للمتجر (مأكولات/ألعاب) | 🛍️ | #F57C00 |
| 4 | 3 | مستلزمات تعليمية | 📚 | #7B1FA2 |
| 5 | 4 | صيانة وتصليح | 🔧 | #FF5722 |
| 6 | 5 | تسويق وإعلان | 📣 | #C2185B |
| 7 | 6 | فعاليات ورحلات | 🎉 | #00838F |
| 8 | 7 | أخرى | 📌 | #616161 |

Seed is tag-gated by `financial_phase1_categories_seed_v1` in `schema_migrations` (also guarded by an existence check per row — defensive against partial failures).

## Indexes Created

| Index | Table | Columns |
|---|---|---|
| `idx_expenses_date` | expenses | `expense_date DESC` |
| `idx_expenses_category` | expenses | `category_id` |
| `idx_expenses_creator` | expenses | `created_by_username` |
| `idx_assets_category` | assets | `category` |
| `idx_assets_condition` | assets | `condition` |
| `idx_assets_disposed` | assets | `is_disposed` |
| `idx_esl_expense` | expense_store_link | `expense_id` |
| `idx_esl_reward` | expense_store_link | `reward_id` |

All `CREATE INDEX IF NOT EXISTS` — idempotent across boots.

## Confirmation: NO existing table modified

`git diff e6ac0a2~..b71ee21 -- app.py` shows **only insertions** to:
- `init_db()` (fresh-DB path) — appended 4 `CREATE TABLE IF NOT EXISTS` + 8 `CREATE INDEX IF NOT EXISTS` statements
- The always-runs migration block (existing-DB path) — same 4 tables + 8 indexes + the tag-gated seed INSERTs
- `_TBL_AUDIT_FEATURE` dict — 4 entries appended (so the table-audit UI puts our new tables in Category B with feature label "النظام المالي" instead of Category D "orphan")

No `ALTER TABLE`, no `DROP`, no `UPDATE` of existing rows. The existing `rewards.stock` column will be incremented in Phase 4 — but that's a Phase 4 change, gated on the `expense_store_link` row insertion happening in the same transaction.

## BYTEA Pattern Match Confirmation

Both `expenses.receipt_bytes` and `assets.image_bytes` use the identical BYTEA column type the existing system already proves works for binary blobs:

| Feature | Column | Stored via | Served via |
|---|---|---|---|
| books_v2 PDFs (pre-existing) | `books_v2.file_data` | base64 in JSON or multipart upload | `GET /api/books/<bid>/view` |
| Rewards images (Phase 2 done) | `rewards.image_bytes` | `image_b64` in JSON of POST/PATCH | `GET /api/rewards/<rid>/image` |
| **Expense receipts** (Phase 2 todo) | `expenses.receipt_bytes` | will mirror rewards: `receipt_b64` in JSON | will be `GET /api/expenses/<id>/receipt` |
| **Asset images** (Phase 2 todo) | `assets.image_bytes` | will mirror rewards | will be `GET /api/assets/<id>/image` |

## Production Health Check

Run live against `mindx-portal-1.onrender.com` AFTER all 6 commits deployed:

| Endpoint | Status |
|---|---|
| `/parent` | HTTP 200 |
| `/portal/parent-hub/points` (admin → 302 redirect by role) | HTTP 302 |
| `/points/manage` | HTTP 200 |
| `POST /api/parent/lookup` (JSON, real PID) | HTTP 200, full payload |
| `GET /api/parent/store/menu?pid=<real>` | HTTP 200 |
| `GET /api/rewards/1/image` (no bytes → 404, JSON error) | HTTP 404 |
| `GET /api/books/9/view` (302 to viewer per can_download=0) | HTTP 302 |
| `GET /api/admin/table-audit` (audit JSON) | HTTP 200 |

**No regressions.** The BYTEA serve route still works, the legacy shop still loads, parent lookup still works.

## Audit Verification (from prod `/api/admin/table-audit`)

```
assets              category=B  rows=0  feature='النظام المالي'
expense_categories  category=B  rows=8  feature='النظام المالي'
expense_store_link  category=B  rows=0  feature='النظام المالي'
expenses            category=B  rows=0  feature='النظام المالي'
```

All four tables surface as **Category B (feature tables)** with the correct Arabic feature label — they no longer appear as Category D orphan candidates. Counts:

```
A: 14   B: 35  ← was 31; +4 financial tables
C: 13   D: 12  ← orphan candidates dropped from 16 to 12
total: 74
```

## Schema Migrations Stamp

`schema_migrations.tag` includes:
- `financial_phase1_categories_seed_v1` (seeded the 8 default categories; one-shot tag-gated)

The CREATE TABLE statements themselves are not tag-gated because `IF NOT EXISTS` makes them naturally idempotent — that matches the precedent for tables added in `points_v1`, `evaluations_v2`, and other prior migrations.

## Rollback

`safety/financial-system-phase1-20260512-062303` is the commit immediately before Phase 1. To revert:

```
git reset --hard safety/financial-system-phase1-20260512-062303
git push --force-with-lease origin main
```

The 4 new tables become unreferenced on rollback. Since they're empty (other than the 8 seed rows), no data is at risk. The migration is **purely additive** — no existing column, row, or behaviour is touched.

## What is NOT in Phase 1

- **No endpoints.** `/api/expenses/*`, `/api/assets/*`, `/api/expenses/categories` — all Phase 2.
- **No UI.** No `/expenses` route, no `/assets` route, no admin pages, no sidebar links. All Phase 3.
- **No store integration.** The `expense_store_link` table exists but no code writes to it or reads from it yet. All Phase 4.
- **No role enforcement code yet.** `created_by_username` is on the schema but no endpoint checks it. The `_EXPENSES_ACCESS_USERNAMES = {"980909805"}` helper will land in Phase 2.

Phase 1 is purely the foundation. Nothing user-visible changes until Phase 2 ships endpoints.

---

🛑 **Phase 1 complete. Awaiting owner approval for Phase 2 (backend endpoints).**
