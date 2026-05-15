# DATABASE_AUDIT.md

Read-only audit of the production Postgres `mindex_db_pw2a` performed on 2026-05-15 by `database-architect-agent`. **No changes were made.** The agent connected as the application user, ran only `SELECT`/`information_schema` queries, and produced this report. Every migration proposed below requires explicit human approval before any DDL is executed (per the agent's Phase-2 stop rule).

The numbers were captured by `SELECT COUNT(*) ...` because `pg_stat_user_tables.n_live_tup` was stale on several tables. Treat these as accurate within ±2 rows for low-write tables.

---

## 1. Inventory

### 1.1 Top tables by size (prod)

| Table | Rows | Total size |
|---|---:|---:|
| books_v2 | 10 | 67 MB |
| rewards | 58 | 10 MB |
| parent_receipts | 8 | 2.4 MB |
| attendance | 3618 | 1.1 MB |
| student_points_log | 1865 | 672 KB |
| audit_log | 562 | 224 KB |
| point_events | 624 | 184 KB |
| evaluations | 250 | 160 KB |
| settings | 100 | 80 KB |
| schema_migrations | 102 | 32 KB |

`books_v2` is dominated by BYTEA `file_data` blobs; row count is tiny. Everything else is well under 1 MB. The DB is small enough that any single migration can complete in seconds.

### 1.2 Schema-migrations integrity

102 migration tags persisted. The dual-path schema management (CLAUDE.md "Dual-path schema management") works on prod — tags persist correctly. No evidence of the `_NO_ID_COLUMN_TABLES` wrapper trap currently active.

### 1.3 Constraint inventory

- **Foreign keys: 39** across the schema. Concentrated in newer feature tables (`trips_*`, `ev_*`, `tasks_*`, `expense_*`, `student_achievements`, `student_points_log`).
- **Triggers: 0**. All cross-table mirroring is application-level (e.g. `taqseet ↔ student_payments`).
- **Tables without a primary key: 0**. Every table has a PK.
- **Unique constraints**: present where expected (`students.personal_id`, `users.username`, `settings(page,component)`, etc.).

### 1.4 Index inventory

Strong index coverage on the newer tables (every `idx_<table>_<col>` follows a consistent naming scheme). **Older core tables are under-indexed** — see Section 6.

---

## 2. Naming issues

### 2.1 Cryptic auto-generated column names (HIGH)

The `students` table contains six columns whose names came from the "تعديل الجدول" modal's `col_<timestamp>` generator OR an ASCII-folder that stripped Arabic to empty strings. **All are populated with real data:**

| Column | Populated rows | Likely intent |
|---|---:|---|
| `col_7572024368` | 322 / 327 (99%) | unknown — needs business-analyst lookup |
| `col_7572590762` | 168 / 327 (51%) | unknown |
| `____2026` | 66 / 327 (20%) | Arabic name stripped to empty + `2026` suffix |
| `____2026_2` | 125 / 327 (38%) | duplicate of above, second column |
| `_____2026` | 167 / 327 (51%) | five-underscore variant |
| `_2026` | 69 / 327 (21%) | one-underscore variant |

These break the CLAUDE.md "Display labels" rule indirectly (users see the labels via `column_labels`, but every developer and every query writer hits these awful identifiers). Rename via Expand-Migrate-Contract — see Section 7.

### 2.2 Arabic identifiers in `taqseet` (MEDIUM)

`taqseet` has 30 Arabic column names: `طريقة_التقسيط`, `مبلغ_الدورة`, `عدد_الاقساط`, `القسط_1` … `القسط_12`, `تاريخ_الاستحقاق_1` … `تاريخ_الاستحقاق_12`, `عدد_ساعات_الدراسة`, `تاريخ_بدء_الدورة`, `تاريخ_انتهاء_الدورة`. These work but require double-quoting in every SQL string and are fragile across console encodings. Only 1 row in prod — small blast radius. Renaming is a clean opportunity.

### 2.3 Year-suffixed columns in `students` (LOW–MEDIUM)

Columns `old_new_2026`, `registration_term2_2026`, `level_reached_2026`, `suitable_level_2026`, `teacher_2026`. Year-stamping a column name means a schema migration every academic year. Move to a normalised `student_year_attributes` child table.

### 2.4 Inconsistent date columns

| Table | Column | Storage |
|---|---|---|
| `attendance` | `attendance_date` | TEXT, ISO YYYY-MM-DD (per `_att_normalize_date`) |
| `evaluations` | `form_fill_date` | TEXT, but contains `46079` (an unconverted Excel serial!) |
| `lessons_log` | `lesson_date` | TEXT, ISO |
| `point_events` | `session_date` | TEXT |
| `payment_log` | `created_at` | TIMESTAMP |
| `student_points_log` | `awarded_at` | TIMESTAMP |

Half use TEXT, half use TIMESTAMP. TEXT-as-date is a Postgres footgun (sort-by-string fails for non-zero-padded dates). Treat as MEDIUM — the `_att_normalize_date` helper hides the worst of it but new code keeps copying the TEXT pattern.

### 2.5 Inconsistent naming patterns

- `users.linked_student_id` (int FK-style) vs `users.linked_parent_for` (text matching `students.personal_id`). Two different join styles in one table.
- `attendance.personal_id` (added recently) coexists with `attendance.student_name` (free text from older imports). Maintained as a SYNC pair but never enforced.
- `student_groups.session_minutes_normal` (TEXT, e.g. "60") next to `student_groups.total_required_hours` (TEXT) — both numeric concepts stored as TEXT.

### 2.6 Reserved-word usage

No reserved-word collisions detected at quick scan. `level` is reserved-ish but only appears as `levels` (table) and `level_course` / `level_reached_2026` (columns); none cause issues.

---

## 3. Schema smells

### 3.1 Missing NOT NULL constraints (HIGH)

Core columns whose nullability is `YES` but logically should be NOT NULL:

| Table | Column | NULL rows on prod |
|---|---|---:|
| `students` | `personal_id` | **156 / 327 (48%)** |
| `students` | `student_name` | 0 |
| `users` | `username` | 0 |
| `users` | `role` | 0 |
| `attendance` | `personal_id` | **169 / 3618** (4.7%, legacy rows pre-migration) |
| `attendance` | `attendance_date` | 0 |
| `attendance` | `status` | 0 |
| `attendance` | `student_name` | 0 |

The 156-NULL `students.personal_id` rows are the biggest data-quality issue in the DB. Half the student records lack a CPR-style ID, even though the column has a UNIQUE constraint. Likely cause: imports from older Excel sources where personal_id wasn't a required field. Several reports under `reports/*.md` reference this pattern.

### 3.2 Missing foreign keys (HIGH)

39 FKs exist but **NONE on the core tables**. The orphan-risk surface:

| From | To (logical) | Enforced? | Orphans found |
|---|---|---|---:|
| `attendance.personal_id` | `students.personal_id` | ❌ | 0 |
| `attendance.group_name` | `student_groups.group_name` | ❌ | 0 |
| `students.group_name_student` | `student_groups.group_name` | ❌ | 0 |
| `payment_log.personal_id` | `students.personal_id` | ❌ | 0 |
| `point_events.student_id` | `students.id` | ❌ | **8 orphans** |
| `student_payments.student_id` | `students.id` | ❌ | not checked |
| `taqseet_method` / `students.installment_type` | `taqseet.taqseet_method` | ❌ | not checked |
| `users.linked_student_id` | `students.id` | ❌ | not checked |
| `books_v2.folder_id` | `book_folders.id` | ❌ | not checked |
| `evaluations.student_id` | `students.id` | ❌ | not checked |

The 8 `point_events.student_id` orphans are real silent data corruption — points were granted to students who were subsequently deleted (or whose `id` rolled). The audit caught this only because we ran the join manually.

### 3.3 TEXT used where typed columns belong (MEDIUM)

Examples (not exhaustive):
- `student_groups.session_minutes_normal` — should be INTEGER
- `student_groups.total_required_hours` — should be NUMERIC
- `student_groups.hours_*` — should be NUMERIC
- `students.installment[1-5]` — should be NUMERIC (amount)
- `users.is_active`, `users.must_change_pw`, `users.can_be_assigned_tasks` — are INTEGER but should be BOOLEAN
- `users.linked_student_id` — INTEGER but default `0` instead of NULL (the FK-as-zero footgun)

The `0` default on `linked_student_id` means every non-linked user has `linked_student_id=0`. Any future FK would fail because there's no `students.id=0`. Migrate to NULL.

### 3.4 Unused / wasted indexes

`student_points_log.idx_points_event` — indexes `event_type` on a table that's unreferenced (Section 5). Drops naturally with the table.

`student_points_log.idx_points_source` is a PARTIAL UNIQUE INDEX (`WHERE is_deleted=0 AND event_source IS NOT NULL`) — well-designed but for a dead table.

### 3.5 Duplicate index near-misses

`achievements_key_key` (UNIQUE) and `idx_achievements_key` (non-UNIQUE) both index `key`. The non-unique one is redundant — Postgres will use the unique index. Drop `idx_achievements_key`. (Moot — table is dead, see Section 5.)

---

## 4. Data quality issues

### 4.1 Duplicates

- `students` duplicate `personal_id`: **0** (constraint holds)
- `users` duplicate `username`: **0** (constraint holds)
- `attendance` duplicate `(date, group, student)`: **0** at the LIMIT 10 sample

### 4.2 Format inconsistencies

- `attendance.attendance_date`: all 3618 rows pass the ISO-YYYY-MM-DD regex. The `att_normalize_v1` migration appears to have worked.
- `attendance.status`: 3 distinct values, all canonical Arabic — `حاضر` (2968), `غائب` (470), `متأخر` (180). Clean.
- `evaluations.form_fill_date` has at least one row with value `46079` (Excel serial date number, never converted). Stored as TEXT so the bug never surfaced as a type error — it just renders nonsense to the user.

### 4.3 Orphan rows (no FK enforcement)

- `point_events`: **8 rows** with `student_id` referencing a non-existent student row.
- All other join paths checked: 0 orphans.

### 4.4 NULL where data expected

- 156 students lack a `personal_id`. Reports under `reports/*.md` already track this.
- 169 attendance rows have NULL `personal_id` — these are pre-migration legacy rows; the recent migration backfilled most but not all.

---

## 5. Dead tables / columns

### 5.1 Truly dead tables (zero `app.py` references AND populated with stale data)

| Table | Rows | Earliest write | Latest write | Verdict |
|---|---:|---|---|---|
| `student_points_log` | 1865 | 2026-05-04 19:18:57 | 2026-05-04 19:19:06 | **9-second bulk seed, never read**. Confirmed legacy. |
| `student_achievements` | 225 | n/a | n/a | Schema present, code path removed. |
| `achievements` | 15 | n/a | n/a | Companion to above. |

Pattern: a points/achievements v1 was built, data was seeded, code was replaced (likely by the current `point_events` flow), and the tables were never cleaned up. Total stranded data: 2105 rows / ~750 KB.

### 5.2 Trip-family tables — empty AND unreferenced

`trips` (1 row, but the 1 row is meaningless without registrations), `trip_message_templates` (3 templates, never sent), `trip_payments`, `trip_registrations`, `trip_reminder_log`, `trip_day_attendance`, `trip_surveys`, `trip_tasks` — all have 0 references in app.py. The trips feature exists in schema but was never shipped to production users.

### 5.3 Other empty + unreferenced

| Table | Rows | Notes |
|---|---:|---|
| `tasks` / `task_*` family | 0 | Tasks feature scaffolded, never went live |
| `custom_table_*` (3 tables) | 0 | User-defined tables feature, never used in prod |
| `cart_items` | 0 | Cart not yet shipped |
| `assets` | 0 | Asset tracking scaffolded |
| `expense_categories` | 8 | Seed data but no actual expense records |
| `expense_store_link` | 0 | |
| `employee_points` | 0 | |
| `recurring_tasks` | 0 | |
| `point_notifications` | 0 | |
| `parent_message_reads` | 0 | Read-tracking exists but no reads recorded |
| `violations_settings` | 0 | |
| `mode_exceptions` | 0 | |
| `upload_sessions` | 0 | |
| `message_reminders` | 0 | |

These are mostly FEATURE-SCAFFOLD tables (created with `IF NOT EXISTS` migrations but never populated). Per CLAUDE.md "Table creation policy" they should appear as Category-D orphans in `/api/admin/table-audit`. Recommend running that audit and approving-keep the ones we want to retain as planned-future-feature.

### 5.4 Soft-deleted rows older than 6 months

22 `books_v2` rows are soft-deleted. Without checking the `deleted_at` column (not queried — agent kept the audit narrow), it's not clear how many are >6 months old. Likely ripe for hard-delete + file cleanup.

### 5.5 Always-NULL columns

Not exhaustively checked. The cryptic `students.col_*` columns ARE populated; they're badly named, not dead.

---

## 6. Performance concerns

### 6.1 Missing indexes on hot lookup paths (MEDIUM)

| Table | Missing index | Used by |
|---|---|---|
| `users` | `username` | `/login` lookup runs on every auth — currently a seq scan on 157 rows. Fine NOW; will hurt at 5K users. |
| `student_groups` | `group_name` | Joined to `attendance`, `students`, `point_events`, `lessons_log` constantly. 38 rows now; seq scans hide the issue. |
| `attendance` | `(group_name, attendance_date)` | Canonical query pattern from CLAUDE.md "Attendance data format". 3618 rows + growing; the `idx_attendance_personal_id` alone doesn't help here. |
| `students` | `personal_id` (covered by UNIQUE — fine) | n/a |
| `student_payments` | `student_id` (covered by UNIQUE with `inst_num` — fine for lookups by student) | n/a |

### 6.2 N+1 candidates

Not exhaustively measured. The `performance-watchdog` agent's spec lists the pattern to look for; flagging a separate audit pass.

### 6.3 BYTEA in hot SELECT *

`books_v2` is 67 MB total, dominated by `file_data` BYTEA. The CLAUDE.md notes already flag this — the orphan probe uses `COALESCE(LENGTH(file_data), 0) AS data_size` to avoid pulling bytes. Any `SELECT * FROM books_v2` would yank megabytes per query.

---

## 7. Migration candidates (sorted by risk × value)

Every item below requires **Phase 1 discovery → Phase 2 plan → human approval → Phase 3+ execution** per the database-architect-agent's standard workflow.

### 7.1 CRITICAL — point_events orphan cleanup
- **Current state**: 8 `point_events` rows reference non-existent `students.id`.
- **Target state**: 0 orphans + FK enforced.
- **Plan**:
  - Phase A (Expand): add FK `point_events.student_id → students(id) NOT VALID` (Postgres-only: `NOT VALID` lets existing orphans stay, future inserts validate).
  - Phase B (Migrate): triage the 8 orphans — either reassign to a "deleted student" sentinel row or hard-delete the orphan events; update any code path that creates `point_events` without a student check.
  - Phase C (Contract): `ALTER TABLE ... VALIDATE CONSTRAINT` to enforce on existing rows; remove the orphans permanently.
- **Estimated time**: 2 days (1 day Phase A + 1 day triage + monitoring).
- **Risk**: LOW. Eight rows, no user impact.

### 7.2 HIGH — rename cryptic `students.col_*` and `____2026` columns
- **Current state**: 6 columns with auto-generated or mojibake names, 99%/51%/20%/38%/51%/21% populated.
- **Target state**: 6 columns with meaningful ASCII snake_case names AND Arabic labels in `column_labels`.
- **Plan**: per column, Expand → Migrate → Contract (3 deploys × 6 columns = 18 deploys, batched 2-3 per week).
- **Estimated time**: 4–6 weeks total (each column gets a 24-hour Phase A and a 48-hour Phase B observation window; columns can overlap their phases).
- **Risk**: HIGH if done sloppily — 99% population means losing the column breaks ~all students. Must keep both columns in sync during Phase B.
- **Prereq**: `business-analyst-agent` must identify the original intent of each column (the data values themselves should hint — `col_7572024368` populated for 322/327 rows is almost certainly a required attribute that got renamed away from its label).

### 7.3 HIGH — drop dead `student_points_log` / `student_achievements` / `achievements` family
- **Current state**: 2105 rows of orphan data, 0 code references.
- **Target state**: tables removed; data archived to a backup snapshot.
- **Plan**: Phase A (Expand): no-op (tables already unread). Phase B (Migrate): no-op. Phase C (Contract): `db_backup.py` snapshot → `DROP TABLE` (gated through `data-protector-agent`, recorded in the audit log).
- **Estimated time**: 1 day. Effectively just the safety procedure.
- **Risk**: LOW provided the grep confirms zero references and the backup is taken.

### 7.4 HIGH — backfill missing `students.personal_id`
- **Current state**: 156 of 327 students lack `personal_id`.
- **Target state**: every student has a personal_id; column made NOT NULL.
- **Plan**: NOT a pure database migration — this is a data-cleanup project that needs the office staff to look up the missing CPRs. Outside the agent's autonomous scope. Phase A: add a temporary `personal_id_missing` flag for reporting. Phase B: manual cleanup by staff. Phase C: NOT NULL enforce.
- **Estimated time**: 2–8 weeks calendar (depends on staff availability).
- **Risk**: MEDIUM — until cleanup is done, any future code that assumes `personal_id IS NOT NULL` will silently miss half the students.

### 7.5 MEDIUM — index attendance(group_name, attendance_date)
- **Current state**: seq scan on 3618 rows for the canonical query pattern.
- **Target state**: composite index.
- **Plan**: Phase A (Expand): `CREATE INDEX CONCURRENTLY idx_attendance_group_date ON attendance(group_name, attendance_date)`. Phase B: n/a. Phase C: n/a (just a new index).
- **Estimated time**: 1 hour including review.
- **Risk**: LOW. `CONCURRENTLY` builds without locking.

### 7.6 MEDIUM — index users(username)
- **Current state**: seq scan on 157 rows on every login.
- **Target state**: `CREATE INDEX idx_users_username ON users(username)`.
- **Risk**: LOW.

### 7.7 MEDIUM — fix `evaluations.form_fill_date` Excel-serial garbage
- **Current state**: at least one row stores `46079` (Excel serial) instead of an ISO date.
- **Target state**: every `form_fill_date` is ISO YYYY-MM-DD, with a check constraint or normaliser at write time.
- **Plan**: identify all malformed rows (`SELECT * FROM evaluations WHERE form_fill_date !~ '^\d{4}-\d{2}-\d{2}$'`), convert in-place via Excel epoch math, then add a write-time validator to the `/api/evaluations` endpoint.
- **Estimated time**: 1 day.
- **Risk**: LOW.

### 7.8 MEDIUM — add FKs to the 9 core join paths
- **Current state**: 0 FKs on `attendance`, `students.group_name_student`, `payment_log`, `student_payments`, `evaluations`, `books_v2`, etc.
- **Plan**: per join, `NOT VALID` → validate later. Same shape as 7.1 but eight more.
- **Estimated time**: 2 weeks across all 9 joins, staggered.
- **Risk**: LOW per individual FK; bundle two-three per deploy to stay sane.

### 7.9 LOW — drop empty + unreferenced feature-scaffold tables
- **Trip family** (8 tables), **task family** (5 tables), **cart_items**, **assets**, **employee_points**, **recurring_tasks**, **point_notifications**, **mode_exceptions**, **upload_sessions**, **message_reminders**, **expense_store_link**, **violations_settings**.
- **Plan**: gather business sign-off (some are deliberately-planned-future), drop the rest. Coordinate with `business-analyst-agent` per CLAUDE.md "Table creation policy."
- **Risk**: LOW if dropped after grep confirms unused.

### 7.10 LOW — normalize year-stamped columns in `students`
- **Current state**: `*_2026` columns will need to be renamed every year.
- **Plan**: extract to `student_year_attributes(student_id, year, attribute_key, value)`.
- **Estimated time**: 2–3 weeks.
- **Risk**: MEDIUM — touches every student-form code path.

---

## 8. Code-to-DB map

Top tables mapped to the routes/blobs that read or write them. Counts are whole-word matches in `app.py`. Lines are the LARGEST cluster of references (most-touched call site).

| Table | Refs | Primary call sites |
|---|---:|---|
| students | many | `_students_live_columns`, `/api/students` POST/PUT/PATCH, `srOpenAddStudent`/`_srRenderCard` flows |
| student_groups | many | `_groups_days_column`, `/api/groups/*` |
| attendance | many | `/api/attendance/*`, `att_normalize_v1` migration |
| users | many | `/login`, `_login_*`, permissions endpoints |
| books_v2 | many | `/api/books/*`, `_books_v2_orphan_probe`, `_books_v2_storage_dir` |
| point_events | 60+ | `/api/points/*` |
| settings | many | `get_setting()`, `/api/settings`, `/settings` page |
| schema_migrations | tag handling | migration block in `init_db()` else-branch |
| taqseet | many | payment/installment logic |
| evaluations | many | `/api/evaluations/*`, `evaluations_v2` migration |
| lessons_log | ~30 | `/api/lessons/*`, `_lessons_*` helpers |
| parent_messages | ~30 | `/portal/parent-hub/messages`, `parent_messages_v1` |
| curriculum_files / curriculum_assignments / curriculum_access_log | many | `/api/curriculum/*`, `curriculum_v1` |
| **student_points_log** | **0** | **NONE — dead** |
| **achievements** | **0** | **NONE — dead** |
| **student_achievements** | **0** | **NONE — dead** |
| **trip_* family** | **0** | **NONE — never shipped** |

For the dead/unshipped tables, see Sections 5 and 7.

---

## End of audit

Verdict summary:

- **3 dead tables** (`student_points_log`, `student_achievements`, `achievements`) with 2105 rows of stranded data — recommend Phase 7.3.
- **8 silent orphan rows** in `point_events` — recommend Phase 7.1.
- **156 students missing personal_id** — recommend Phase 7.4 (not autonomous; needs staff).
- **6 cryptic `students` column names** with real data behind them — recommend Phase 7.2.
- **At least 1 evaluations row with unconverted Excel serial date (`46079`)** — recommend Phase 7.7.
- **2 missing hot-path indexes** (`attendance(group_name, attendance_date)`, `users(username)`) — recommend 7.5, 7.6.
- **9 missing FKs on core join paths** — recommend Phase 7.8 staggered.
- **~15 empty feature-scaffold tables** — recommend Phase 7.9 with business sign-off.

**Next step (per the agent's stop rule): human approval on which of these to plan first.** The agent will not produce migration plan documents or execute any DDL until explicitly told which item(s) to pursue.
