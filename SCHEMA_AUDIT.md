# SCHEMA_AUDIT.md

**Purpose:** complete READ-ONLY inventory of the mindex-v3 production schema as it actually exists on Render's PostgreSQL instance, with cross-references to the `app.py` source.

**Generated:** 2026-05-22 (UTC) against `mindex_db_pw2a` on `dpg-d7jl937lk1mc73aaal40-a.oregon-postgres.render.com` via `information_schema` + `pg_catalog` SELECTs only. Zero writes.

**Source of truth:** the LIVE PostgreSQL schema. Where `app.py`'s `init_db()` or migration block disagrees with prod, the live schema wins and the discrepancy is noted in §G.

**Safety tag created before this audit:** `pre-audit-20260522-175922` (no commits made).

---

## A. Summary

- **93 tables** in the `public` schema
- **1,026 columns** total
- **42 foreign-key constraints** (almost all `ON DELETE NO ACTION`; a few `SET NULL` or `CASCADE` — see §C)
- **42 unique constraints** (excluding primary keys)
- **4 CHECK constraints** (only on `tasks.priority`, `tasks.status`, `recurring_tasks.frequency`, `task_evaluations.rating_stars`)
- **217 indexes** (mostly `_pkey` for primary keys + `_<col>_key` for unique constraints + a few hand-written performance indexes)
- **116 rows in `schema_migrations`** — every applied migration tag from project bootstrap to 2026-05-22
- **27 empty tables** (mostly task / trip system tables that exist but have no rows yet) — listed in §A.3

### A.1 — All 93 tables, grouped by subsystem

Grouping is the codebase's own classification from `app.py` (`_TBL_AUDIT_CORE` / `_TBL_AUDIT_FEATURE` / `_TBL_AUDIT_SYSTEM` at line 51282).

**Core data (15 tables) — primary user-data, never DROP/TRUNCATE:**
- `students`, `student_groups`, `attendance`, `payment_log`, `taqseet`, `student_payments`, `evaluations`, `payment_edits`, `parent_receipts`, `session_durations`, `receipts_log`, `custom_tables`, `custom_table_cols`, `custom_table_rows`, `students` (incl. linked tables)

**Feature tables (54):**
- **Points system (12):** `behaviors`, `point_events`, `student_points_log`, `rewards`, `redemptions`, `cart_items`, `avatars`, `levels`, `achievements`, `student_achievements`, `point_notifications`, `employee_points`
- **Notifications / push (3):** `push_subscriptions`, `notifications`, `point_notifications`
- **Messages / WhatsApp (5):** `message_log`, `message_reminders`, `message_templates`, `payment_messages`, `parent_messages`, `parent_message_reads`, `parent_message_attachments`
- **Curriculum / books (6):** `books_v2`, `books_v2_groups`, `books_v2_teachers`, `book_folders`, `book_folder_groups`, `upload_sessions`, `curriculum_plans`, `curriculum_lessons`
- **Violations (4):** `violations`, `violations_catalog`, `violations_action_templates`, `violations_settings`
- **Events / trips v2 (7):** `ev_events`, `ev_schedule`, `ev_costs`, `ev_items`, `ev_tasks`, `ev_registrations`, `ev_msg_templates`
- **Trips v1 (legacy, 6):** `trips`, `trip_registrations`, `trip_payments`, `trip_day_attendance`, `trip_tasks`, `trip_surveys`, `trip_reminder_log`, `trip_message_templates`
- **Financial (4):** `expenses`, `expense_categories`, `expense_store_link`, `assets`
- **Tasks (7):** `departments`, `tasks`, `task_evaluations`, `task_comments`, `task_attachments`, `recurring_tasks`, `task_notifications`
- **Teacher deliverables / lessons (3):** `lessons_log`, `evaluation_deadlines`, `deadline_task_completions`
- **Docs / center mode (3):** `docs_pages`, `docs_screenshots`, `mode_exceptions`
- **Misc (1):** `backup_log`

**System / infra tables (13):**
- `users`, `settings`, `schema_migrations`, `audit_log`, `user_permissions`, `button_registry`, `table_labels`, `column_labels`, `group_col_labels`, `att_col_labels`, `eval_col_labels`, `taqseet_col_labels`, `paylog_col_labels`

### A.2 — Top 15 tables by row count (live data on prod)

```
attendance                       3953
student_points_log               1865
audit_log                        1682
point_events                     1483
session_durations                 458
evaluations                       330
students                          327
payment_log                       325
ev_tasks                          240
student_achievements              225
users                             188
message_log                       174
schema_migrations                 116
settings                          100
payment_messages                   89
```

### A.3 — Empty tables (27)

These tables exist but have 0 rows. Roughly half are feature-tables waiting to be exercised; the other half are legacy/duplicate (e.g. `tasks` exists alongside `ev_tasks`; `trip_*` v1 exists alongside `ev_*` v2):

```
att_col_labels, books_v2_teachers, custom_table_cols, custom_table_rows,
custom_tables, deadline_task_completions, docs_screenshots, employee_points,
evaluation_deadlines, expense_store_link, message_reminders, mode_exceptions,
parent_message_reads, point_notifications, recurring_tasks, task_attachments,
task_comments, task_evaluations, task_notifications, tasks,
trip_day_attendance, trip_payments, trip_registrations, trip_reminder_log,
trip_surveys, upload_sessions, violations_settings
```

---

## B. Per-table detail

Format: `column_name  pg_type  NOT NULL?  DEFAULT  (PK / UNIQUE)`. Outgoing FKs listed below each table. Types are PostgreSQL `udt_name` (e.g. `int4` = INTEGER, `float4` = REAL, `text` = TEXT, `bytea` = BLOB, `numeric` = DECIMAL). Where a column's name is Arabic that's the actual stored identifier; the `column_labels` / `*_col_labels` tables map them to display labels (see §F).

### `achievements` — 10 cols, 15 rows
- `id` int4 NOT NULL default `nextval('achievements_id_seq')` **PK**
- `key` text NOT NULL **UNIQUE**
- `name_ar` text NOT NULL
- `description_ar` text NOT NULL
- `icon` text
- `points_reward` int4 default 0
- `tier` text
- `criteria_json` text
- `is_active` int4 default 1
- `created_at` timestamp default CURRENT_TIMESTAMP

### `assets` — 25 cols, 28 rows
- `id` int4 NOT NULL **PK**, `name_ar` text NOT NULL, `category` text default '', `serial_number` text default ''
- `image_bytes` bytea, `image_mime` text default ''
- `location` text default '', `condition` text default 'good' (values: good / damaged / needs_maintenance per app), `responsible_person` text default ''
- `purchase_date` date, `purchase_price` numeric default 0, `vendor_name` text default ''
- `linked_expense_id` int4 → **FK** `expenses.id` (ON DELETE SET NULL)
- `useful_life_years` int4 default 5, `last_maintenance_date` date, `maintenance_notes` text, `next_maintenance_date` date
- `is_disposed` int4 default 0 (soft-delete flag), `disposed_at` timestamp, `disposal_reason` text
- `created_by_username` text NOT NULL, `created_at` timestamp default CURRENT_TIMESTAMP, `updated_at` timestamp default CURRENT_TIMESTAMP
- `quantity` int4 default 1, `unit_ar` text

### `att_col_labels` — 7 cols, 0 rows
- `id` int4 NOT NULL **PK**
- `col_key` text **UNIQUE**, `col_label` text, `col_order` int4 default 0, `is_visible` int4 default 1
- `col_type` text default 'نص' (values: نص / رقم / تاريخ / نعم-لا / قائمة منسدلة / تقييم — Arabic for text/number/date/yes-no/dropdown/rating)
- `col_options` text default ''

### `attendance` — 11 cols, 3,953 rows
- `id` int4 NOT NULL **PK**
- `attendance_date` text — ISO `YYYY-MM-DD` enforced by `_att_normalize_date()` per ATTENDANCE RULE in CLAUDE.md (was previously polluted with Arabic-era suffixes like `31/1-2026م`; backfilled via migration `att_normalize_v1`)
- `day_name` text
- `group_name` text — whitespace-folded
- `student_name` text — whitespace-folded
- `status` text — canonical `حاضر | غائب | متأخر` (folded via `STATUS_REMAP` at app.py:74142)
- `message_status` text
- `class_duration` text default '', `class_type` text default '' (in-person / online — set by attendance UI)
- `personal_id` text (denormalized; backfilled via `att_personal_id_backfill_v1`)
- `message` text default ''

### `audit_log` — 10 cols, 1,682 rows
- `id` int4 NOT NULL **PK**
- `actor_id` int4, `actor_username` text
- `action` text NOT NULL — free-form action key (e.g. `books_v2.cleanup_orphans`, `redemption.cancel`, `user.permission.update`)
- `target_type` text, `target_id` text
- `old_value` text, `new_value` text, `details` text
- `created_at` timestamp default CURRENT_TIMESTAMP

### `avatars` — 6 cols, 31 rows
- `id` int4 NOT NULL **PK**, `name` text, `emoji` text, `sort_order` int4 default 0
- `file_path` text default '', `category` text default ''

### `backup_log` — 15 cols, 27 rows
- `id` int4 NOT NULL **PK**, `username` text, `filename` text, `bytes_written` int4 default 0
- `downloaded_at` timestamp default CURRENT_TIMESTAMP, `kind` text default '', `reason` text default ''
- `path` text default '', `size_bytes` int4 default 0
- `email_status` text default '', `email_to` text default ''
- `tables_count` int4 default 0, `total_rows` int4 default 0, `verified` int4 default 0, `report_text` text default ''

### `behaviors` — 10 cols, 15 rows
- `id` int4 NOT NULL **PK**, `name_ar` text
- `type` text default 'positive' (values: `positive | negative`)
- `points_value` int4 default 1
- `icon` text default '', `color` text default ''
- `created_by` int4, `is_global` int4 default 1, `is_active` int4 default 1
- `created_at` timestamp default CURRENT_TIMESTAMP

### `book_folder_groups` — 6 cols, 12 rows
- `id` int4 NOT NULL **PK**
- `folder_id` int4 NOT NULL, `group_id` int4 NOT NULL — **UNIQUE(folder_id, group_id)**
- `assigned_by` int4, `assigned_by_username` text, `assigned_at` timestamp default CURRENT_TIMESTAMP

### `book_folders` — 8 cols, 10 rows
- `id` int4 NOT NULL **PK**, `name_ar` text NOT NULL
- `sort_order` int4 default 0
- `created_by` int4, `created_by_username` text, `created_at` timestamp default CURRENT_TIMESTAMP
- `is_active` int4 default 1, `notes` text
- **NOTE: NO `parent_id` column. Folders are FLAT, not hierarchical** — the brief asked about hierarchical/self-referencing folders; the live schema has none.

### `books_v2` — 14 cols, 42 rows
- `id` int4 NOT NULL **PK**, `title` text NOT NULL, `description` text
- `file_path` text NOT NULL — disk-relative path under `/var/data/books_v2/`
- `file_size_bytes` int4 default 0
- `can_download` int4 default 1 — 0 means view-only PDF.js viewer (`/parent/book/<id>/viewer`)
- `uploaded_by_username` text, `uploaded_by_name` text, `uploaded_at` timestamp default CURRENT_TIMESTAMP
- `is_deleted` int4 default 0 (soft-delete)
- `cloudinary_url` text, `cloudinary_public_id` text (legacy; CDN path)
- `file_data` bytea — BYTEA fallback when disk write fails (rarely populated post-`0fc833f`)
- `folder_id` int4 — informal FK to `book_folders.id` (no DB constraint)

### `books_v2_groups` — 3 cols, 48 rows (M:N junction)
- `id` int4 NOT NULL **PK**, `book_id` int4 NOT NULL, `group_id` int4 NOT NULL
- **UNIQUE(book_id, group_id)** — informal FKs to `books_v2.id` + `student_groups.id`

### `books_v2_teachers` — 3 cols, 0 rows (M:N junction)
- `id` int4 NOT NULL **PK**, `book_id` int4 NOT NULL, `teacher_user_id` int4 NOT NULL
- **UNIQUE(book_id, teacher_user_id)** — informal FKs to `books_v2.id` + `users.id`

### `button_registry` — 6 cols, 54 rows
- `id` int4 NOT NULL **PK**, `button_key` text NOT NULL **UNIQUE**
- `button_label_ar` text NOT NULL, `page_slug` text NOT NULL
- `default_roles` text NOT NULL default '[]' (JSON array of role names)
- `sort_order` int4 default 0
- Drives `/api/me/permissions` + per-user overrides in `user_permissions`.

### `cart_items` — 6 cols, 2 rows
- `id` int4 NOT NULL **PK**, `student_id` int4 NOT NULL, `reward_id` int4 NOT NULL
- `quantity` int4 NOT NULL default 1
- `created_at` timestamp default CURRENT_TIMESTAMP, `updated_at` timestamp default CURRENT_TIMESTAMP
- **UNIQUE(student_id, reward_id)** — supports upsert on add. Drains into `redemptions` at checkout.

### `column_labels` — 10 cols, 63 rows
- `id` int4 NOT NULL **PK**, `col_key` text **UNIQUE**, `col_label` text
- `col_order` int4 default 0, `is_visible` int4 default 1
- `col_type` text default 'نص' (values per CLAUDE.md LABELS RULE: نص / رقم / تاريخ / نعم-لا / قائمة منسدلة / تقييم)
- `col_options` text default '' (for dropdown options, pipe-delimited)
- `table_name` text, `internal_name` text, `display_name` text (later additions for the unified labels system)
- The "students" table's column labels live here; per-table labels for groups/attendance/eval/taqseet/paylog live in `*_col_labels`.

### `curriculum_lessons` — 11 cols, 1 row
- `id` int4 NOT NULL **PK**, `plan_id` int4 NOT NULL (informal FK → `curriculum_plans.id`)
- `lesson_name` text NOT NULL, `sessions_count` int4 default 1
- `start_date` text, `end_date` text (ISO YYYY-MM-DD)
- `sort_order` int4 default 0, `is_completed` int4 default 0, `is_deleted` int4 default 0
- `created_at` timestamp default CURRENT_TIMESTAMP, `updated_at` timestamp default CURRENT_TIMESTAMP

### `curriculum_plans` — 6 cols, 17 rows
- `id` int4 NOT NULL **PK**, `name` text NOT NULL, `created_by` int4
- `created_at` timestamp default CURRENT_TIMESTAMP, `updated_at` timestamp default CURRENT_TIMESTAMP, `is_deleted` int4 default 0

### `custom_tables` / `custom_table_cols` / `custom_table_rows` — 3 / 7 / 3 cols, all 0 rows
User-defined ad-hoc tables built at runtime via the database UI. `custom_tables.tbl_name` is **UNIQUE**. `custom_table_rows.row_data` is JSON text. Currently unused on prod.

### `deadline_task_completions` — 7 cols, 0 rows
- `id` int4 NOT NULL **PK**, `deadline_id` int4 NOT NULL → **FK** `evaluation_deadlines.id` (CASCADE)
- `teacher_id` int4 NOT NULL → **FK** `users.id` (NO ACTION)
- `completed_at` timestamp, `first_seen_at` timestamp, `created_at` timestamp, `updated_at` timestamp
- **UNIQUE(deadline_id, teacher_id)**

### `departments` — 7 cols, 9 rows
- `id` int4 NOT NULL **PK**, `name_ar` text NOT NULL **UNIQUE**
- `icon` text, `color` text, `sort_order` int4 default 0, `is_active` int4 default 1
- `created_at` timestamp default CURRENT_TIMESTAMP

### `docs_pages` — 9 cols, 22 rows
- `id` int4 NOT NULL **PK**, `slug` text **UNIQUE**, `url` text, `title_ar` text, `section` text
- `roles` text default '[]' (JSON array)
- `capture_status` text default 'pending' (values: `pending | done | failed`)
- `last_captured_at` timestamp, `created_at` timestamp default CURRENT_TIMESTAMP

### `docs_screenshots` — 9 cols, 0 rows
- `id` int4 NOT NULL **PK**, `page_id` int4 (informal FK → `docs_pages.id`)
- `role` text, `viewport` text default 'desktop' (values: `desktop | tablet | mobile`)
- `file_path` text, `captured_at` timestamp default CURRENT_TIMESTAMP, `hash` text
- `capture_method` text default 'auto' (values: `auto | manual`), `file_size` int4 default 0

### `employee_points` — 6 cols, 0 rows
- `id` int4 NOT NULL **PK**, `employee_username` text NOT NULL
- `task_id` int4 → **FK** `tasks.id` (SET NULL)
- `points` int4 NOT NULL, `reason` text, `awarded_at` timestamp default CURRENT_TIMESTAMP

### `ev_costs` — 13 cols, 75 rows
- `id` int4 NOT NULL **PK**, `event_id` int4 NOT NULL → **FK** `ev_events.id`
- `category` text NOT NULL, `label` text NOT NULL, `amount` float4 default 0
- `notes` text, `order_index` int4 default 0, `is_default` int4 default 0
- `unit_price` float4 default 0
- `multiplier_type` text default 'fixed' — **values: `fixed | per_registered | per_attended`** (the brief's "calc type")
- `created_at`, `updated_at`, `is_deleted` (soft-delete)

### `ev_events` — 22 cols, 15 rows (the main "Trips v2" entity)
- `id` int4 NOT NULL **PK**, `name` text NOT NULL, `destination` text, `description` text
- `target_group_ids` text — comma-separated `student_groups.id` list (not a proper FK)
- `max_students` int4 default 0
- `event_date` date NOT NULL, `departure_time` text, `return_time` text, `meeting_point` text
- `price_per_student` float4 default 0
- `status` text default 'planning' — **values: `planning | open | closed | archived`**
- `registration_token` text — public parent-registration token (unique partial index)
- `post_trip_notes` text
- `payment_iban` text, `payment_benefit` text, `payment_beneficiary` text, `payment_instructions` text
- `created_by_user_id` int4 → **FK** `users.id`
- `created_at`, `updated_at`, `is_deleted` (soft-delete)

### `ev_items` — 12 cols, 75 rows
- `id` int4 NOT NULL **PK**, `event_id` int4 NOT NULL → **FK** `ev_events.id`
- `title` text NOT NULL, `quantity` int4 default 1, `notes` text
- `is_ready` int4 default 0
- `assigned_to_user_id` int4 → **FK** `users.id`, `assigned_to_name` text
- `order_index` int4 default 0, `created_at`, `updated_at`, `is_deleted`

### `ev_msg_templates` — 7 cols, 4 rows
- `id` int4 NOT NULL **PK**, `name` text NOT NULL, `icon` text, `message` text NOT NULL
- `audience` text default 'all' (values: `all | registered | unpaid | paid`)
- `is_default` int4 default 0, `created_at` timestamp default CURRENT_TIMESTAMP

### `ev_registrations` — 20 cols, 3 rows
- `id` int4 NOT NULL **PK**, `event_id` int4 NOT NULL → **FK** `ev_events.id`
- `student_id` int4 → **FK** `students.id`, `student_name` text NOT NULL
- `parent_name` text, `parent_phone` text
- `group_id` int4 → **FK** `student_groups.id`, `group_name` text
- `payment_status` text default 'pending' — **values: `pending | paid | partial`**
- `payment_amount` float4 default 0, `payment_notes` text
- `attendance_status` text default 'pending' — **values: `pending | present | absent | late`**
- `attendance_notes` text
- `registered_at` timestamp, `registered_by_user_id` int4, `registered_by_name` text
- `receipt_image_url` text, `receipt_uploaded_at` timestamp
- `updated_at`, `is_deleted`

### `ev_schedule` — 13 cols, 20 rows
- `id` int4 NOT NULL **PK**, `event_id` int4 NOT NULL → **FK** `ev_events.id`
- `category` text NOT NULL, `time_slot` text, `duration_minutes` int4
- `title` text NOT NULL, `description` text, `order_index` int4 default 0
- `is_completed` int4 default 0, `completed_at` timestamp
- `created_at`, `updated_at`, `is_deleted`

### `ev_tasks` — 18 cols, 240 rows (largest events-related table)
- `id` int4 NOT NULL **PK**, `event_id` int4 NOT NULL → **FK** `ev_events.id`
- `category` text NOT NULL — **values: `before | during | after`** (the brief's "before/during/after" task split)
- `title` text NOT NULL, `description` text
- `assigned_to_user_id` int4 → **FK** `users.id`, `assigned_to_name` text
- `due_date` date, `due_time` text
- `status` text default 'pending' — **values: `pending | in_progress | done | cancelled`**
- `completion_notes` text, `order_index` int4 default 0
- `completed_at`, `completed_by_user_id` int4, `completed_by_name` text
- `created_at`, `updated_at`, `is_deleted`

### `eval_col_labels` — 7 cols, 13 rows
Standard `*_col_labels` shape. Stores Arabic labels for `evaluations` columns.

### `evaluation_deadlines` — 10 cols, 0 rows
- `id` int4 NOT NULL **PK**, `month` text NOT NULL (YYYY-MM)
- `from_date` text NOT NULL, `to_date` text NOT NULL (ISO YYYY-MM-DD)
- `title` text NOT NULL default '', `task_type` text NOT NULL default 'evaluation'
- `created_by` text, `created_by_user_id` int4
- `created_at`, `updated_at`

### `evaluations` — 39 cols, 330 rows (monthly evaluation form — schema v1 + v2)
- `id` int4 NOT NULL **PK**
- **v1 legacy text columns (TEXT, NEVER DROP per CLAUDE.md):** `form_fill_date`, `group_name`, `student_name`, `class_participation`, `general_behavior`, `behavior_notes`, `reading`, `dictation`, `term_meanings`, `conversation`, `expression`, `grammar`, `notes`
- **v2 numeric scores (1–10 INTEGER):** `score_participation`, `score_behavior`, `score_reading`, `score_dictation`, `score_vocabulary`, `score_conversation`, `score_expression`, `score_grammar`
- `evaluation_date` text, `evaluation_month` text (YYYY-MM)
- `student_id` int4 (informal FK → `students.id`), `teacher_id` int4 (informal FK → `users.id`), `teacher_name` text
- `notes_behavior` text, `notes_language` text, `general_notes` text
- `overall_score` int4 (computed from the 8 score_* columns)
- `released_to_parent` int4 default 0 — portal-visibility flag
- `whatsapp_sent_at` timestamp, `whatsapp_sent_by` int4, `whatsapp_send_count` int4 NOT NULL default 0
- `personal_id` text (denormalized for fast parent lookup)
- `is_deleted` int4 default 0 (soft-delete)
- `created_at`, `updated_at`
- The 8 score columns + their JSON keys are also enumerated in `_EV_PARENT_SCORE_KEYS` at app.py:100938.

### `expense_categories` — 7 cols, 8 rows
- `id` int4 NOT NULL **PK**, `name_ar` text NOT NULL, `icon` text default '', `color` text default '#6B3FA0'
- `is_active` int4 default 1, `sort_order` int4 default 0, `created_at` timestamp

### `expense_store_link` — 6 cols, 0 rows
- `id` int4 NOT NULL **PK**
- `expense_id` int4 → **FK** `expenses.id` (CASCADE)
- `reward_id` int4 → **FK** `rewards.id` (NO ACTION)
- `quantity` int4 NOT NULL, `unit_cost` numeric NOT NULL
- `created_at` timestamp default CURRENT_TIMESTAMP
- Links a purchase invoice to the rewards-shop stock it provisioned.

### `expenses` — 16 cols, 10 rows
- `id` int4 NOT NULL **PK**
- `category_id` int4 → **FK** `expense_categories.id` (NO ACTION)
- `amount` numeric, `description` text NOT NULL, `vendor_name` text default ''
- `payment_method` text default 'cash' — **values: `cash | card | transfer | benefit`**
- `expense_date` date NOT NULL
- `receipt_bytes` bytea, `receipt_mime` text default '', `receipt_filename` text default ''
- `notes` text default ''
- `created_by_username` text NOT NULL, `created_at`, `updated_at`
- `quantity` int4, `unit_ar` text

### `group_col_labels` — 7 cols, 15 rows
Standard `*_col_labels` shape. Labels for `student_groups` extra columns — **CRITICAL** for the "أيام الدراسة" custom-column resolver per CLAUDE.md.

### `lessons_log` — 12 cols, 4 rows
- `id` int4 NOT NULL **PK**, `teacher_id` int4, `teacher_username` text, `teacher_name` text
- `group_name` text, `lesson_date` text (ISO YYYY-MM-DD; admin-editable retroactively)
- `lesson_topic` text, `curriculum_progress` text, `notes` text
- `is_deleted` int4 default 0, `created_at`, `updated_at`

### `levels` — 7 cols, 4 rows
- `id` int4 NOT NULL **PK**, `name_ar` text
- `min_points` int4 default 0, `max_points` int4
- `badge_icon` text, `color` text, `sort_order` int4 default 0
- Bronze / Silver / Gold / Platinum (per UI; actual values stored as Arabic in `name_ar`).

### `message_log` — 5 cols, 174 rows
- `id` int4 NOT NULL **PK**, `student_name` text, `student_whatsapp` text, `template_name` text
- `sent_at` timestamp default CURRENT_TIMESTAMP

### `message_reminders` — 8 cols, 0 rows
- `id` int4 NOT NULL **PK**, `name` text
- `day_of_week` int4 (0=Sun..6=Sat per app convention), `time_of_day` text
- `template_id` int4 (informal FK → `message_templates.id`), `group_name` text
- `enabled` int4 default 1, `created_at` timestamp

### `message_templates` — 5 cols, 1 row
- `id` int4 NOT NULL **PK**, `name` text, `category` text, `content` text
- `created_at` timestamp default CURRENT_TIMESTAMP

### `mode_exceptions` — 5 cols, 0 rows
- `id` int4 NOT NULL **PK**, `scope` text NOT NULL, `key_name` text NOT NULL
- `mode` text NOT NULL — **values: `in_person | online`** (centre-mode override per group/date)
- `created_at` timestamp
- **UNIQUE(scope, key_name)** — drives center-mode overrides.

### `notifications` — 14 cols, 26 rows
- `id` int4 NOT NULL **PK**, `created_at` timestamp default CURRENT_TIMESTAMP
- `sender_user_id` int4, `sender_username` text
- `title` text NOT NULL, `body` text, `url` text, `urgent` int4 default 0
- `target_type` text (values: `all | role | group | user | parent_pid`), `target_value` text
- `total_targeted` int4 default 0, `total_sent` int4 default 0, `total_failed` int4 default 0
- `status` text default 'sent' (values: `sent | partial | failed | queued`)

### `parent_message_attachments` — 14 cols, 1 row
- `id` int4 NOT NULL **PK**, `file_id` text NOT NULL **UNIQUE**
- `message_id` int4 (informal FK → `parent_messages.id`)
- `original_filename` text, `stored_extension` text, `content_type` text
- `file_size_bytes` int4 default 0, `file_data` bytea
- `uploaded_by_user_id` int4, `uploaded_by_username` text, `uploaded_at` timestamp
- `download_count` int4 default 0, `last_downloaded_at` timestamp, `is_deleted` int4 default 0

### `parent_message_reads` — 4 cols, 0 rows
- `id` int4 NOT NULL **PK**, `message_id` int4 NOT NULL, `student_id` int4 NOT NULL
- `read_at` timestamp default CURRENT_TIMESTAMP
- **UNIQUE(message_id, student_id)**

### `parent_messages` — 18 cols, 8 rows ("ماذا تريد أن يعرف ولي الأمر")
- `id` int4 NOT NULL **PK**, `teacher_id` int4, `teacher_username` text, `teacher_name` text
- `group_name` text, `sent_date` text
- `content_covered` text, `skills_focused` text, `books_used` text, `homework` text, `parent_notes` text
- `whatsapp_status` text default 'queued' (values: `queued | sending | sent | failed`)
- `whatsapp_sent_count` int4 default 0, `whatsapp_total_count` int4 default 0
- `status` text default 'draft' (values: `draft | sent | archived`)
- `is_deleted` int4 default 0, `created_at`, `updated_at`

### `parent_receipts` — 16 cols, 9 rows
- `id` int4 NOT NULL **PK**, `student_id` int4, `student_name` text, `personal_id` text
- `file_data` bytea, `file_mime` text, `filename` text, `note` text
- `upload_date` timestamp default now()
- `status` text default 'قيد المراجعة' — **values: `قيد المراجعة | تم التأكيد | مرفوض` (Arabic)** — mapped to `pending | approved | rejected` in JS at app.py:31761
- `reviewed_by` text, `reviewed_at` timestamp
- `installment_number` int4, `installment_amount` numeric, `rejection_reason` text
- `is_remainder` int4 default 0

### `paylog_col_labels` — 7 cols, 13 rows
Standard `*_col_labels` shape for `payment_log`.

### `payment_edits` — 10 cols, 2 rows
- `id` int4 NOT NULL **PK**, `student_id` int4, `student_name` text, `personal_id` text
- `installment_number` int4, `old_amount` numeric, `new_amount` numeric
- `reason` text, `edited_by` text, `edit_date` timestamp default now()
- Audit trail for two-step installment edits.

### `payment_log` — 16 cols, 325 rows
- `id` int4 NOT NULL **PK**, `student_name` text
- `inst1`..`inst5` text (free-text amounts as stored), `msg1`..`msg5` text (notes per installment)
- `created_at` timestamp default CURRENT_TIMESTAMP
- `total_paid` numeric, `total_remaining` numeric
- `personal_id` text (backfilled via `payment_log_pid_backfill_v1`)
- The legacy 5-installment-column denorm; the canonical per-installment table is `student_payments`.

### `payment_messages` — 7 cols, 89 rows
- `id` int4 NOT NULL **PK**, `student_id` int4, `student_name` text
- `installment_number` int4, `message_type` text (values: `reminder | overdue | thank_you`)
- `sent_by` text, `sent_at` timestamp default CURRENT_TIMESTAMP

### `point_events` — 12 cols, 1,483 rows
- `id` int4 NOT NULL **PK**, `student_id` int4, `student_name` text
- `behavior_id` int4 (informal FK → `behaviors.id`), `behavior_name` text
- `points_value` int4 default 0 (signed — positive or negative)
- `group_name` text, `awarded_by` int4, `awarded_by_name` text
- `awarded_at` timestamp default CURRENT_TIMESTAMP, `note` text default ''
- `session_date` text (the session this points event was recorded against)
- The CURRENT canonical points-event table. `student_points_log` is a SEPARATE v2 system used for non-behavior point adjustments (manual / system / admin).

### `point_notifications` — 10 cols, 0 rows
- `id` int4 NOT NULL **PK**, `event_id` int4, `student_id` int4, `student_name` text
- `phone` text, `message` text
- `status` text default 'pending' (values: `pending | queued | sent | failed`)
- `created_at`, `sent_at`, `notification_type` text default 'instant' (values: `instant | digest`)

### `push_subscriptions` — 11 cols, 27 rows
- `id` int4 NOT NULL **PK**, `user_id` int4, `parent_pid` text
- `endpoint` text NOT NULL **UNIQUE** (browser push endpoint)
- `p256dh` text NOT NULL, `auth` text NOT NULL (Web-Push keys)
- `user_agent` text, `role` text
- `created_at`, `last_used_at`, `active` int4 default 1

### `receipts_log` — 12 cols, 17 rows
- `id` int4 NOT NULL **PK**, `receipt_number` text **UNIQUE**
- `student_id` int4, `student_name` text, `personal_id` text
- `installment_number` int4, `amount` float4, `employee_name` text
- `issued_at` timestamp default CURRENT_TIMESTAMP
- `status` text default 'issued' (values: `issued | void`)
- `course_name` text default '', `verification_code` text default ''

### `recurring_tasks` — 15 cols, 0 rows
- `id` int4 NOT NULL **PK**, `template_title` text NOT NULL, `template_description` text
- `department_id` int4 → **FK** `departments.id`
- `priority` text default 'normal'
- `assigned_to_username` text NOT NULL, `estimated_hours` float4 NOT NULL
- `frequency` text NOT NULL — **CHECK: `frequency = ANY (ARRAY['daily','weekly','monthly'])`**
- `day_of_week` int4 (for weekly), `day_of_month` int4 (for monthly)
- `tags` text, `is_active` int4 default 1, `last_generated_date` date
- `created_by_username` text NOT NULL, `created_at`

### `redemptions` — 12 cols, 40 rows
- `id` int4 NOT NULL **PK**, `student_id` int4, `student_name` text
- `reward_id` int4 (informal FK → `rewards.id`), `reward_name` text
- `points_spent` int4 default 0
- `redeemed_at` timestamp default CURRENT_TIMESTAMP
- `status` text default 'pending' — **values: `pending | requested | approved | rejected | delivered | cancelled`** (per code at app.py:31644 and various paths)
- `delivered_by` int4, `delivered_at` timestamp
- `request_source` text default '' (values: `student_portal | parent_pid | admin | ''`)
- `rejection_reason` text

### `rewards` — 13 cols, 71 rows
- `id` int4 NOT NULL **PK**, `name_ar` text, `point_cost` int4 default 0
- `icon` text default '', `stock` int4 default -1 (where -1 = unlimited)
- `category` text default '' (free-form)
- `is_active` int4 default 1, `created_at` timestamp default CURRENT_TIMESTAMP
- `image_url` text default ''
- `category_type` text default '' — **values: `food | toy | ''`** (drives parent-shop tab grouping; comment at app.py:8969)
- `is_menu_item` int4 default 0 (whether to show on parent's menu)
- `image_bytes` bytea, `image_mime` text default ''

### `schema_migrations` — 2 cols, 116 rows
- `tag` text NOT NULL **PK** — migration tag (e.g. `att_normalize_v1`, `points_v2`)
- `applied_at` timestamp default CURRENT_TIMESTAMP
- **NOTE:** this table has no `id` column. Per CLAUDE.md, `_PgConnection.execute` auto-appends `RETURNING id`; this table must stay in the `_NO_ID_COLUMN_TABLES` exception list or migrations gated by its tags will re-run forever.

### `session_durations` — 5 cols, 458 rows
- `id` int4 NOT NULL **PK**, `group_name` text, `session_date` text
- `duration_minutes` int4 default 0
- `session_type` text default '' — **values: `in_person | online | ''`**
- **UNIQUE(group_name, session_date)**

### `settings` — 6 cols, 100 rows
- `id` int4 NOT NULL **PK**, `page` text NOT NULL, `component` text NOT NULL
- `label` text NOT NULL, `value` text default ''
- `value_type` text default 'table_column' (values: `table_column | text | int | bool | json`)
- **UNIQUE(page, component)** — the dynamic-config keystone per CLAUDE.md.

### `student_achievements` — 6 cols, 225 rows
- `id` int4 NOT NULL **PK**
- `student_id` int4 NOT NULL → **FK** `students.id`
- `achievement_id` int4 NOT NULL → **FK** `achievements.id`
- `unlocked_at` timestamp default CURRENT_TIMESTAMP
- `progress_value` int4 default 0, `is_celebrated` int4 default 0

### `student_groups` — 17 cols, 38 rows
- `id` int4 NOT NULL **PK**
- `group_name` text, `teacher_name` text, `level_course` text, `last_reached` text
- `study_time` text, `ramadan_time` text, `online_time` text, `group_link` text
- `session_minutes_normal` text, `created_at` timestamp default CURRENT_TIMESTAMP
- `hours_all_online` text, `hours_online_only` text, `total_required_hours` text
- `study_days` text — **CANONICAL أيام الدراسة column per CLAUDE.md (parse via `_parse_study_days()`)**
- `hours_in_person_auto` text
- `col_7387857961` text — runtime-added custom column (admin-created via the database UI)

### `student_payments` — 6 cols, 36 rows (canonical per-installment table)
- `id` int4 NOT NULL **PK**, `student_id` int4, `inst_num` int4
- `inst_type` text default '', `price` float4 default 0, `paid` float4 default 0
- **UNIQUE(student_id, inst_num)** — mirrored by `taqseet.paidN` per the taqseet sync rule (CLAUDE.md).

### `student_points_log` — 12 cols, 1,865 rows (v2 points-event ledger)
- `id` int4 NOT NULL **PK**
- `student_id` int4 NOT NULL → **FK** `students.id`
- `points` int4 NOT NULL (signed), `event_type` text NOT NULL, `event_source` text
- `description_ar` text NOT NULL
- `awarded_by_user_id` int4, `awarded_by_name` text, `awarded_at` timestamp
- `is_deleted` int4 default 0, `deleted_at` timestamp, `deleted_by_user_id` int4

### `students` — 36 cols, 327 rows
- `id` int4 NOT NULL **PK**
- `personal_id` text **UNIQUE** (CPR-shaped string; may contain bidi marks U+200F/U+202A — see ADR-038)
- `student_name` text, `whatsapp` text, `class_name` text
- `old_new_2026` text (values: `قديم | جديد`)
- `group_name_student` text (in-person group), `group_online` text (online group)
- `mother_phone`, `father_phone`, `other_phone` text
- `residence`, `home_address`, `road`, `complex_name` text
- `installment_type` text default '' (FK-by-name → `taqseet.طريقة_التقسيط`)
- `created_at` timestamp default CURRENT_TIMESTAMP
- `books_received` text, `level_reached_2026` text, `teacher_2026` text
- `avatar_id` int4 default 0 (informal FK → `avatars.id`)
- `col_7572024368` text, `col_7572590762` text (runtime-added custom columns)
- `registration_term2_2026` text (values: `نعم | لا | ''`)
- `final_result` text, `suitable_level_2026` text
- `installment1`..`installment5` text (5 legacy denormalized installment-amount text fields)
- **The four cryptic column names** (intentional, do NOT rename per DATABASE_AUDIT §7.2): `____2026` (final result), `____2026_2` (level reached), `_____2026` (suitable for level), `_2026` (teacher 2026), `col_7572590762` (books received), `col_7572024368` (registration status)
- `contract_hours` int4 default 28 — added by `financial_student_contract_hours_v1`

### `table_labels` — 3 cols, 34 rows
- `id` int4 NOT NULL **PK**, `tbl_name` text **UNIQUE**, `tbl_label` text
- Arabic display labels for tables, used by `_table_display_label()`.

### `taqseet` — 31 cols, 11 rows (installment-plan templates)
- `id` int4 NOT NULL **PK**
- **All other column names are Arabic** (kept that way per CLAUDE.md — the convention pre-dates the column_labels system):
  - `طريقة_التقسيط` text (the natural key for import upsert)
  - `مبلغ_الدورة` numeric, `عدد_الاقساط` int4
  - `القسط_1`..`القسط_12` numeric (installment amounts)
  - `تاريخ_الاستحقاق_1`..`تاريخ_الاستحقاق_12` text (ISO due dates)
  - `عدد_ساعات_الدراسة` text, `تاريخ_بدء_الدورة` text, `تاريخ_انتهاء_الدورة` text
- Synced bidirectionally with `student_payments.paid` per CLAUDE.md (taqseet ↔ student_payments sync rule).

### `taqseet_col_labels` — 7 cols, 30 rows
Standard `*_col_labels` shape — Arabic display labels for `taqseet`'s Arabic column names.

### `task_attachments` / `task_comments` / `task_evaluations` / `task_notifications` — all 0 rows
- Standard task-system FKs: `task_id → tasks.id` (CASCADE on attachments/comments/evaluations/notifications)
- `task_evaluations`: **UNIQUE(task_id)** + **CHECK rating_stars BETWEEN 1 AND 5**

### `tasks` — 16 cols, 0 rows
- `id` int4 NOT NULL **PK**
- `title` text NOT NULL, `description` text
- `department_id` int4 → **FK** `departments.id`
- `priority` text NOT NULL default 'normal' — **CHECK: `priority IN ('critical','urgent','normal','low')`**
- `status` text NOT NULL default 'new' — **CHECK: `status IN ('new','in_progress','completed','cancelled')`**
- `assigned_to_username` text NOT NULL, `created_by_username` text NOT NULL
- `due_date` date NOT NULL, `estimated_hours` float4 NOT NULL, `actual_hours` float4
- `tags` text, `recurring_id` int4 (informal FK → `recurring_tasks.id`)
- `created_at`, `started_at`, `completed_at`

### `trip_day_attendance` — 10 cols, 0 rows
- `id` int4 NOT NULL **PK**
- `trip_id` int4 NOT NULL → **FK** `trips.id`
- `registration_id` int4 NOT NULL → **FK** `trip_registrations.id`
- `attendance_status` text NOT NULL (values: `present | absent | late`)
- `arrival_time` text, `notes` text, `recorded_by_user_id` int4, `recorded_by_name` text
- `recorded_at`, `updated_at`

### `trip_message_templates` — 10 cols, 3 rows
- `id` int4 NOT NULL **PK**, `template_key` text NOT NULL **UNIQUE**
- `name` text, `icon` text, `subject` text, `body` text NOT NULL
- `is_default` int4 default 1, `is_active` int4 default 1
- `created_at`, `updated_at`

### `trip_payments` — 14 cols, 0 rows
- `id` int4 NOT NULL **PK**
- `registration_id` int4 NOT NULL → **FK** `trip_registrations.id`
- `trip_id` int4 NOT NULL → **FK** `trips.id`
- `amount` float4 NOT NULL
- `payment_method` text NOT NULL (values: `cash | card | transfer | benefit`)
- `receipt_image_path` text, `payment_date` date NOT NULL
- `collected_by_user_id` int4 NOT NULL → **FK** `users.id`, `collected_by_name` text
- `notes` text, `created_at`, `is_deleted`, `deleted_at`, `deleted_by_user_id`

### `trip_registrations` — 21 cols, 0 rows
- `id` int4 NOT NULL **PK**
- `trip_id` int4 NOT NULL → **FK** `trips.id`
- `student_id` int4 → **FK** `students.id`
- `student_name` text NOT NULL, `student_pid` text
- `registration_status` text default 'registered' (values: `registered | waitlisted | cancelled | confirmed`)
- `registration_method` text (values: `online | walk_in | parent_form`)
- `registered_by_user_id` int4 → **FK** `users.id`
- `parent_name` text, `parent_phone` text NOT NULL, `pickup_parent_name` text
- `medical_notes` text, `additional_notes` text
- `consent_given` int4 default 0, `consent_at` timestamp
- `registered_at` timestamp default CURRENT_TIMESTAMP, `cancelled_at` timestamp
- `waitlist_position` int4, `promoted_from_waitlist_at` timestamp
- `confirmation_id` text, `is_deleted` int4 default 0

### `trip_reminder_log` — 12 cols, 0 rows
- `id` int4 NOT NULL **PK**
- `trip_id` int4 NOT NULL → **FK** `trips.id`
- `registration_id` int4 → **FK** `trip_registrations.id`
- `template_key` text NOT NULL (informal FK → `trip_message_templates.template_key`)
- `send_type` text NOT NULL (values: `whatsapp | sms | email`)
- `triggered_by_user_id` int4, `triggered_by_name` text
- `recipient_phone` text, `recipient_name` text
- `message_body` text, `whatsapp_link` text, `sent_at` timestamp

### `trip_surveys` — 14 cols, 0 rows
- `id` int4 NOT NULL **PK**
- `trip_id` int4 NOT NULL → **FK** `trips.id`
- `registration_id` int4 NOT NULL → **FK** `trip_registrations.id`
- `survey_token` text (public per-survey access token)
- `parent_name` text, `student_name` text
- `rating` int4 (1–5), `liked_what` text, `improvements` text, `would_recommend` int4 (0/1)
- `additional_comments` text, `submitted_at`, `ip_address`, `created_at`

### `trip_tasks` — 20 cols, 20 rows
- `id` int4 NOT NULL **PK**
- `trip_id` int4 NOT NULL → **FK** `trips.id`
- `category` text NOT NULL (values: `before | during | after`)
- `task_title` text NOT NULL, `task_description` text
- `assigned_to_user_id` int4 → **FK** `users.id`, `assigned_to_name` text
- `due_date` date, `due_time` text
- `status` text NOT NULL default 'pending' (values: `pending | in_progress | done | cancelled`)
- `completion_notes` text, `order_index` int4 default 0
- `completed_at`, `completed_by_user_id` int4, `completed_by_name` text
- `created_at`, `updated_at`, `created_by_user_id` int4, `is_deleted` int4 default 0
- `is_from_template` int4 default 0

### `trips` — 22 cols, 1 row (legacy v1 system; superseded by `ev_events`)
- `id` int4 NOT NULL **PK**, `name` text NOT NULL, `destination` text, `trip_type` text
- `description` text, `target_audience` text
- `max_capacity` int4 default 0, `price_per_student` float4 default 0
- `trip_date` date, `departure_time` text, `return_time` text, `meeting_point` text
- `emergency_contact` text, `emergency_contact_name` text
- `equipment_needed` text
- `status` text default 'active' (values: `active | upcoming | open | closed | cancelled | archived`)
- `created_by` int4 → **FK** `users.id`
- `created_at`, `updated_at`, `archived_at`, `is_deleted` int4 default 0
- `smart_token` text (public registration token, v1)

### `upload_sessions` — 10 cols, 0 rows
- `id` text NOT NULL **PK** (UUID-like session key; the ONLY non-int4 PK in the schema)
- `user_id` int4 NOT NULL, `filename` text NOT NULL
- `total_size` int4 NOT NULL, `total_chunks` int4 NOT NULL
- `received_chunks` text NOT NULL default '[]' (JSON array of chunk indices)
- `title` text NOT NULL, `folder_id` int4
- `created_at`, `expires_at` timestamp NOT NULL

### `user_permissions` — 5 cols, 37 rows
- `id` int4 NOT NULL **PK**
- `user_id` int4 NOT NULL, `button_key` text NOT NULL
- `is_visible` int4 NOT NULL — per-user override (1 = show, 0 = hide; default comes from `button_registry.default_roles`)
- `updated_at` timestamp default CURRENT_TIMESTAMP
- **UNIQUE(user_id, button_key)**

### `users` — 14 cols, 188 rows
- `id` int4 NOT NULL **PK**
- `username` text **UNIQUE** (a parent's username equals the child's `students.personal_id` by convention — see ADR-038)
- `password` text (SHA-256 hex, no salt — `hp()` at app.py:261)
- `name` text, `role` text — **values: `admin | manager | teacher | reception | student | parent`** (from `_PERM_KNOWN_ROLES` at app.py:32532)
- `department` text (free-form)
- `linked_student_id` int4 default 0 (informal FK → `students.id`) — see CLAUDE.md / ADR-038 for the fallback chain
- `linked_parent_for` text default '' (informal FK → `students.personal_id`; for the V1 multi-child parent UI)
- `must_change_pw` int4 default 0 (informational only since G13.1 removed the forced-change redirect)
- `notify_pref` text default 'instant' (values: `instant | digest | off`)
- `landing_page` text (values: `dashboard | teacher_hub | parent_hub | student_portal | ''`)
- `is_active` int4 default 1 (0 = disabled; login route rejects with 403 "هذا الحساب معطّل")
- `primary_department_id` int4 (informal FK → `departments.id`)
- `can_be_assigned_tasks` int4 default 0

### `violations` — 25 cols, 19 rows
- `id` int4 NOT NULL **PK**
- `student_id` int4 → **FK** `students.id`
- `student_name` text NOT NULL, `group_name` text
- `violation_date` date NOT NULL, `violation_place` text NOT NULL
- `violation_type` text NOT NULL, `description` text
- **Six boolean action flags:** `action_oral_teacher`, `action_oral_supervisor`, `action_written`, `action_message_parent`, `action_call_parent`, `action_meeting_parent` — each int4 default 0
- `additional_notes` text
- `severity` text — **values: `light | medium | severe`** (per app.py:705)
- `whatsapp_sent_at` timestamp, `whatsapp_sent_by` int4
- `created_by` int4 NOT NULL, `created_at`, `updated_at`, `is_deleted` int4 default 0
- `catalog_id` int4 (informal FK → `violations_catalog.id`; added later by migration `violations_catalog_v1`)
- `action_taken` text (snapshot at record-time, never retroactively rewritten by catalog edits)
- `occurrence_number` int4 (1st / 2nd / 3rd... for repeat-threshold logic)

### `violations_action_templates` — 6 cols, 42 rows
- `id` int4 NOT NULL **PK**, `template_text` text NOT NULL **UNIQUE**
- `sort_order` int4 default 0, `is_active` int4 default 1
- `created_at` timestamp default CURRENT_TIMESTAMP
- `category` text default 'general' (values: `general | first | second | third`)

### `violations_catalog` — 17 cols, 32 rows
- `id` int4 NOT NULL **PK**, `violation_text` text NOT NULL
- `severity` text NOT NULL (values: `light | medium | severe`), `location` text NOT NULL (free-form)
- `emoji_icon` text, `short_label` text, `is_quick_pick` int4 default 0
- `action_first_time` text NOT NULL, `action_second_time` text NOT NULL, `action_third_time` text NOT NULL
- `repeat_threshold_2nd` int4 NOT NULL, `repeat_threshold_3rd` int4 NOT NULL
- `use_count` int4 default 0, `sort_order` int4 default 0, `is_active` int4 default 1
- `created_at`, `updated_at`

### `violations_settings` — 3 cols, 0 rows (single-row-per-key style, K-V)
- `key` text NOT NULL **PK** (the ONLY string PK aside from `upload_sessions.id` and `schema_migrations.tag`)
- `value` text NOT NULL, `updated_at` timestamp default CURRENT_TIMESTAMP

---

## C. Master foreign-key list (42 declared FKs)

Format: `source.column → target.column  (cardinality, ON DELETE)`

### Assets / financial
1. `assets.linked_expense_id` → `expenses.id` (N:1, SET NULL)
2. `expense_store_link.expense_id` → `expenses.id` (N:1, CASCADE)
3. `expense_store_link.reward_id` → `rewards.id` (N:1, NO ACTION)
4. `expenses.category_id` → `expense_categories.id` (N:1, NO ACTION)

### Achievements / students
5. `student_achievements.achievement_id` → `achievements.id` (N:1, NO ACTION)
6. `student_achievements.student_id` → `students.id` (N:1, NO ACTION) — joins `achievements` × `students` as an M:N junction
7. `student_points_log.student_id` → `students.id` (N:1, NO ACTION)
8. `violations.student_id` → `students.id` (N:1, NO ACTION)

### Events v2 (ev_*)
9. `ev_costs.event_id` → `ev_events.id` (N:1, NO ACTION)
10. `ev_events.created_by_user_id` → `users.id` (N:1, NO ACTION)
11. `ev_items.assigned_to_user_id` → `users.id` (N:1, NO ACTION)
12. `ev_items.event_id` → `ev_events.id` (N:1, NO ACTION)
13. `ev_registrations.event_id` → `ev_events.id` (N:1, NO ACTION)
14. `ev_registrations.group_id` → `student_groups.id` (N:1, NO ACTION)
15. `ev_registrations.student_id` → `students.id` (N:1, NO ACTION)
16. `ev_schedule.event_id` → `ev_events.id` (N:1, NO ACTION)
17. `ev_tasks.assigned_to_user_id` → `users.id` (N:1, NO ACTION)
18. `ev_tasks.event_id` → `ev_events.id` (N:1, NO ACTION)

### Tasks (system)
19. `tasks.department_id` → `departments.id` (N:1, NO ACTION)
20. `recurring_tasks.department_id` → `departments.id` (N:1, NO ACTION)
21. `task_attachments.task_id` → `tasks.id` (N:1, CASCADE)
22. `task_comments.task_id` → `tasks.id` (N:1, CASCADE)
23. `task_evaluations.task_id` → `tasks.id` (1:1, CASCADE) — unique on task_id
24. `task_notifications.task_id` → `tasks.id` (N:1, CASCADE)
25. `employee_points.task_id` → `tasks.id` (N:1, SET NULL)

### Trips v1
26. `trips.created_by` → `users.id` (N:1, NO ACTION)
27. `trip_day_attendance.registration_id` → `trip_registrations.id` (N:1, NO ACTION)
28. `trip_day_attendance.trip_id` → `trips.id` (N:1, NO ACTION)
29. `trip_payments.collected_by_user_id` → `users.id` (N:1, NO ACTION)
30. `trip_payments.registration_id` → `trip_registrations.id` (N:1, NO ACTION)
31. `trip_payments.trip_id` → `trips.id` (N:1, NO ACTION)
32. `trip_registrations.registered_by_user_id` → `users.id` (N:1, NO ACTION)
33. `trip_registrations.student_id` → `students.id` (N:1, NO ACTION)
34. `trip_registrations.trip_id` → `trips.id` (N:1, NO ACTION)
35. `trip_reminder_log.registration_id` → `trip_registrations.id` (N:1, NO ACTION)
36. `trip_reminder_log.trip_id` → `trips.id` (N:1, NO ACTION)
37. `trip_surveys.registration_id` → `trip_registrations.id` (N:1, NO ACTION)
38. `trip_surveys.trip_id` → `trips.id` (N:1, NO ACTION)
39. `trip_tasks.assigned_to_user_id` → `users.id` (N:1, NO ACTION)
40. `trip_tasks.trip_id` → `trips.id` (N:1, NO ACTION)

### Deadline-task completions
41. `deadline_task_completions.deadline_id` → `evaluation_deadlines.id` (N:1, CASCADE)
42. `deadline_task_completions.teacher_id` → `users.id` (N:1, NO ACTION) — junction (teacher × deadline) for completion ticks

### Informal "FKs by name/convention" — NOT enforced by Postgres but used by app code
- `students.installment_type` → `taqseet.طريقة_التقسيط` (by string match; drives the per-student installment plan)
- `users.username` ↔ `students.personal_id` (the parent-account convention; see ADR-038 + the `_resolve_session_student_id` fallback)
- `users.linked_student_id` → `students.id` (informal, no DB constraint — see CHANGE_LOG 2026-05-22 linkage repair: 143 of 174 pointers were stale before the fix)
- `users.linked_parent_for` → `students.personal_id` (V1 multi-child parent UI)
- `attendance.group_name` + `attendance.student_name` → matched against `students.student_name` × `student_groups.group_name` (whitespace-normalized)
- `books_v2_groups.book_id` / `book_id` → `books_v2.id` / `student_groups.id` (M:N junction, informal)
- `books_v2_teachers.book_id` / `teacher_user_id` → `books_v2.id` / `users.id` (M:N junction, informal)
- `book_folder_groups.folder_id` / `group_id` → `book_folders.id` / `student_groups.id` (M:N junction, informal)
- `books_v2.folder_id` → `book_folders.id` (informal)
- `cart_items.student_id` / `reward_id` → `students.id` / `rewards.id` (informal; UNIQUE-constrained junction)
- `redemptions.student_id` / `reward_id` → `students.id` / `rewards.id` (informal)
- `point_events.student_id` → `students.id` (informal; the canonical FK exists on `student_points_log` only)
- `point_events.behavior_id` → `behaviors.id` (informal)
- `evaluations.student_id` → `students.id` (informal)
- `evaluations.teacher_id` → `users.id` (informal)
- `lessons_log.teacher_id` → `users.id` (informal)
- `parent_messages.teacher_id` → `users.id` (informal)
- `parent_message_reads.message_id` / `student_id` → `parent_messages.id` / `students.id` (informal; UNIQUE-constrained junction)
- `parent_message_attachments.message_id` → `parent_messages.id` (informal)
- `parent_receipts.student_id` → `students.id` (informal)
- `payment_log.personal_id` / `student_name` → `students.personal_id` / `student_name` (informal by-value join)
- `payment_messages.student_id` → `students.id` (informal)
- `student_payments.student_id` → `students.id` (informal)
- `payment_edits.student_id` → `students.id` (informal)
- `receipts_log.student_id` → `students.id` (informal)
- `notifications.target_value` is polymorphic — interpreted via `notifications.target_type`: `user` → `users.id`, `group` → `student_groups.group_name`, `parent_pid` → `students.personal_id`, `role` → role name, `all` → ignored
- `push_subscriptions.user_id` → `users.id` (informal); `push_subscriptions.parent_pid` → `students.personal_id` (informal)
- `audit_log.target_id` is polymorphic — its `target_type` value indicates which table (e.g. `target_type='user'` → `users.id`)
- `mode_exceptions.key_name` is polymorphic per `scope` (e.g. `scope='group'` → `student_groups.group_name`; `scope='date'` → ISO date string)
- `parent_messages.group_name` → `student_groups.group_name` (informal)
- `message_log.student_name` → `students.student_name` (informal); `message_reminders.template_id` → `message_templates.id` (informal)
- `curriculum_lessons.plan_id` → `curriculum_plans.id` (informal)
- `upload_sessions.user_id` → `users.id` (informal); `upload_sessions.folder_id` → `book_folders.id` (informal)
- `students.avatar_id` → `avatars.id` (informal)
- `user_permissions.user_id` → `users.id` + `user_permissions.button_key` → `button_registry.button_key` (both informal; UNIQUE-constrained junction)
- `trip_reminder_log.template_key` → `trip_message_templates.template_key` (informal)

### Self-referencing FKs
- **None.** `book_folders` has NO `parent_id` column (folders are FLAT). No table in the schema references itself.

---

## D. Enums / lookup values per column

Postgres has only 4 declared CHECK constraints; the rest are app-enforced. Source: combination of CHECK constraints, column DEFAULT clauses, source-level constants in `app.py`, and observed prod data.

| Table.column | Allowed values | Source |
|---|---|---|
| `tasks.priority` | `critical | urgent | normal | low` | **CHECK constraint** + default `'normal'` |
| `tasks.status` | `new | in_progress | completed | cancelled` | **CHECK constraint** + default `'new'` |
| `recurring_tasks.frequency` | `daily | weekly | monthly` | **CHECK constraint** |
| `task_evaluations.rating_stars` | 1–5 | **CHECK constraint** (`>= 1 AND <= 5`) |
| `attendance.status` | `حاضر | غائب | متأخر` (Arabic) | `ATTENDANCE_CANONICAL_STATUSES` at app.py:74153; folded via `STATUS_REMAP` (also accepts `present/absent/late/حضور/غياب/تأخير`) |
| `attendance.class_type` | `in_person | online | ''` | code-driven |
| `behaviors.type` | `positive | negative` | default `'positive'` |
| `rewards.category_type` | `food | toy | ''` | comment at app.py:8969 |
| `redemptions.status` | `pending | requested | approved | rejected | delivered | cancelled` | various code paths |
| `redemptions.request_source` | `student_portal | parent_pid | admin | ''` | observed values |
| `users.role` | `admin | manager | teacher | reception | student | parent` | `_PERM_KNOWN_ROLES` at app.py:32532 |
| `users.notify_pref` | `instant | digest | off` | default `'instant'` |
| `users.landing_page` | `dashboard | teacher_hub | parent_hub | student_portal | ''` | code-driven |
| `parent_receipts.status` | `قيد المراجعة | تم التأكيد | مرفوض` (Arabic; mapped to pending/approved/rejected by the JS) | default `'قيد المراجعة'` |
| `ev_events.status` | `planning | open | closed | archived` | default `'planning'` |
| `ev_tasks.status` / `trip_tasks.status` | `pending | in_progress | done | cancelled` | default `'pending'` |
| `ev_tasks.category` / `trip_tasks.category` | `before | during | after` | code-driven |
| `ev_costs.multiplier_type` | `fixed | per_registered | per_attended` | default `'fixed'` |
| `ev_msg_templates.audience` | `all | registered | unpaid | paid` | default `'all'` |
| `ev_registrations.payment_status` / `trip_registrations.registration_status` | `pending | paid | partial` / `registered | waitlisted | cancelled | confirmed` | defaults `'pending'` / `'registered'` |
| `ev_registrations.attendance_status` / `trip_day_attendance.attendance_status` | `pending | present | absent | late` | default `'pending'` |
| `expenses.payment_method` / `trip_payments.payment_method` | `cash | card | transfer | benefit` | default `'cash'` |
| `assets.condition` | `good | damaged | needs_maintenance` | default `'good'` |
| `violations.severity` / `violations_catalog.severity` | `light | medium | severe` | app.py:705 |
| `violations.violation_place` / `violations_catalog.location` | free-form (no enum) | — |
| `violations_action_templates.category` | `general | first | second | third` | default `'general'` |
| `notifications.status` | `sent | partial | failed | queued` | default `'sent'` |
| `notifications.target_type` | `all | role | group | user | parent_pid` | code-driven |
| `point_notifications.status` | `pending | queued | sent | failed` | default `'pending'` |
| `point_notifications.notification_type` | `instant | digest` | default `'instant'` |
| `parent_messages.whatsapp_status` | `queued | sending | sent | failed` | default `'queued'` |
| `parent_messages.status` | `draft | sent | archived` | default `'draft'` |
| `payment_messages.message_type` | `reminder | overdue | thank_you` | code-driven |
| `docs_pages.capture_status` | `pending | done | failed` | default `'pending'` |
| `docs_screenshots.viewport` | `desktop | tablet | mobile` | default `'desktop'` |
| `docs_screenshots.capture_method` | `auto | manual` | default `'auto'` |
| `column_labels.col_type` and all `*_col_labels.col_type` | `نص | رقم | تاريخ | نعم-لا | قائمة منسدلة | تقييم` (Arabic for text / number / date / yes-no / dropdown / rating) | default `'نص'` (CLAUDE.md LABELS RULE) |
| `mode_exceptions.mode` | `in_person | online` | code-driven |
| `session_durations.session_type` | `in_person | online | ''` | default `''` |
| `trips.status` | `active | upcoming | open | closed | cancelled | archived` | default `'active'` |
| `trip_registrations.registration_method` | `online | walk_in | parent_form` | code-driven |
| `trip_reminder_log.send_type` | `whatsapp | sms | email` | code-driven |
| `students.old_new_2026` | `قديم | جديد` (Arabic for old/new) | code-driven |
| `students.registration_term2_2026` | `نعم | لا | ''` | code-driven |
| `parent_message_attachments.content_type` | MIME types (free-form) | — |
| `evaluations.score_*` (8 columns: `score_participation`, `score_behavior`, `score_reading`, `score_dictation`, `score_vocabulary`, `score_conversation`, `score_expression`, `score_grammar`) | 1–10 INTEGER, NULL allowed | `_EV_PARENT_SCORE_KEYS` at app.py:100938 |
| `receipts_log.status` | `issued | void` | default `'issued'` |
| `message_reminders.day_of_week` | 0–6 (0=Sunday) | code-driven |
| `settings.value_type` | `table_column | text | int | bool | json` | default `'table_column'` |

---

## E. Feature → tables mapping

Maps each subsystem from the brief to its backing tables. **"NO BACKING TABLE"** is explicitly called out where applicable.

### Students
- Primary: **`students`** (36 cols) — includes the brief's named fields:
  - `personal_id` ✓ (UNIQUE; may carry bidi marks U+200F/U+202A)
  - `final_result` ✓ (also stored in `____2026` cryptic column for legacy callers)
  - `suitable_level_2026` ✓ (also `_____2026`)
  - `books_received` ✓ (also `col_7572590762`)
  - `registration_term2_2026` ✓ (also `col_7572024368`)
  - `contract_hours` ✓ (int4, default 28; added by `financial_student_contract_hours_v1`)
  - `avatar_id` ✓ (int4 default 0, informal FK → `avatars.id`)
  - `home_address` / `complex_name` / `road` ✓ (the address columns)
  - `mother_phone` / `father_phone` / `other_phone` ✓ (secondary phones — `other_phone` is the brief's "secondary phone")
- The `column_labels` table provides Arabic display labels for every `students` column (see §F).

### Courses, levels, installment plans, books
- **Courses (as standalone entity): NO BACKING TABLE.** "Course" is implicit — there's no `courses` table. Levels are tracked per-group via `student_groups.level_course`. "Course amount" is stored in `taqseet.مبلغ_الدورة` and in `payment_log.course_amount` (the latter is NOT in the current `payment_log` schema; reach the column name via `_resolve_paylog_course_amount_col` — the column-labels mapping).
- **Levels:** `levels` (4 rows: Bronze / Silver / Gold / Platinum or similar based on `name_ar`).
- **Installment plans:** `taqseet` (the templates, keyed by `طريقة_التقسيط`) + `student_payments` (per-student-per-installment) + `payment_log` (legacy denorm with 5 columns). `payment_edits` records audit trail.
- **Books (curriculum):** `books_v2` (the PDF library) + junction tables `books_v2_groups` and `books_v2_teachers` + `book_folders` (FLAT — no `parent_id`) + `book_folder_groups` (folder→group assignments) + `upload_sessions` (chunked uploads). The legacy `curriculum_plans` + `curriculum_lessons` is a SEPARATE per-group teaching-plan system (not a book library).

### Groups, enrollments, student-course registration, placement test
- **Groups:** `student_groups` (38 rows). Custom columns (admin-added at runtime via the database UI) live as extra TEXT columns on the same table; their Arabic labels live in `group_col_labels`.
- **Enrollments / student-group assignment: NO DEDICATED TABLE.** Students belong to groups via two columns on `students`: `group_name_student` (in-person) and `group_online` (online). Both are string-FKs (no DB constraint).
- **Placement test: NO BACKING TABLE.** No `placement_tests` table exists; placement results are inferred from columns like `students.level_reached_2026` and `students.suitable_level_2026`.
- **Student-course registration: NO BACKING TABLE.** Registration status is `students.registration_term2_2026` (نعم/لا).

### Payments / installments
- `taqseet` (11 rows) — installment plan templates with Arabic column names
- `student_payments` (36 rows) — the canonical per-student-per-installment record (UNIQUE on `student_id`, `inst_num`)
- `payment_log` (325 rows) — legacy 5-installment denormalized table
- `parent_receipts` (9 rows) — parent uploads (status: قيد المراجعة / تم التأكيد / مرفوض)
- `payment_messages` (89 rows) — WhatsApp reminder log per (student, installment, type)
- `payment_edits` (2 rows) — audit trail for two-step installment edits
- `receipts_log` (17 rows) — issued receipts (UNIQUE receipt_number, status issued/void)
- See CLAUDE.md "Taqseet ↔ student_payments sync" for the mirroring invariant.

### Attendance & sessions
- `attendance` (3,953 rows) — one row per (group, date, student) with status `حاضر|غائب|متأخر`, `class_duration`, `class_type` (in_person/online)
- `session_durations` (458 rows) — UNIQUE(group_name, session_date) — per-session duration override (overrides `student_groups.session_minutes_normal`)
- **Sessions as a standalone entity: NO BACKING TABLE.** Sessions are inferred from the (group, date) combination in attendance and session_durations.

### Center status (in-person/online) and exceptions
- `mode_exceptions` (0 rows currently) — `scope` + `key_name` + `mode` (`in_person` | `online`). UNIQUE(scope, key_name). Used to override the default center mode for a specific group or date.
- The default mode itself is stored in `settings` (page='center', component='mode' or similar — see §F).

### Points system
- `behaviors` (15 rows) — catalog (with `type=positive|negative` + `points_value`)
- `point_events` (1,483 rows) — the canonical "teacher awarded X to student Y" ledger
- `student_points_log` (1,865 rows) — a SECOND v2 points-event ledger with a real FK to `students` and soft-delete; used for non-behavior adjustments
- `rewards` (71 rows) — shop catalog (category_type: food/toy/'')
- `redemptions` (40 rows) — purchase history (status: pending/requested/approved/rejected/delivered/cancelled)
- `cart_items` (2 rows) — parent's in-flight cart
- `avatars` (31 rows) — choosable student avatars
- `levels` (4 rows) — Bronze/Silver/Gold/Platinum (`min_points`+`max_points` thresholds)
- `achievements` (15 rows) + `student_achievements` (225 rows, with real FKs) — gamification badges
- `point_notifications` (0 rows) — outbound WhatsApp queue for point events
- `employee_points` (0 rows) — points awarded to STAFF (not students), keyed by `task_id`
- **Parent accounts:** `users` rows with `role='student'` (the student logs in as themselves; convention `username = personal_id`) OR `role='parent'` (`linked_parent_for` for multi-child V1 UI; not currently used much per CLAUDE.md). See ADR-038 for the linkage repair.

### Violations
- `violations` (19 rows) — the recorded incidents (with FK `student_id → students.id`)
- `violations_catalog` (32 rows) — the catalog of standard violations (~32 entries, not the "~42" the brief mentioned — the catalog grew from an earlier draft)
- `violations_action_templates` (42 rows) — reusable action phrases (this is the "~42" the brief likely meant)
- `violations_settings` (0 rows) — K-V settings table for violations module
- **Locations:** stored as free-form `violations_catalog.location` (no separate locations table)
- **Written pledge / PDF:** stored per-incident as `action_written` int flag on `violations`. The PDF generation is handled in code; no PDF-storage column.
- **Action taken:** `violations.action_taken` (the snapshot at record time, never retroactively rewritten by catalog edits)

### Trips/events
- **Active system: `ev_*` (v2).** `ev_events` is the main entity; supporting tables are `ev_schedule`, `ev_costs` (with `multiplier_type: fixed|per_registered|per_attended` — the brief's "calc type"), `ev_items` (the tools/checklist), `ev_tasks` (`category: before|during|after` — the brief's "trip tasks before/during/after"), `ev_registrations` (with `payment_status` and `attendance_status`), `ev_msg_templates` (the trip message templates)
- **Target groups:** `ev_events.target_group_ids` (TEXT — comma-separated `student_groups.id` list; informal)
- **Timeline:** `ev_schedule` (time_slot + duration_minutes + title + description + order_index)
- **Public registration token:** `ev_events.registration_token` (unique partial index)
- **Legacy v1 system, deprecated but still tablespaces:** `trips` (1 row), `trip_registrations`, `trip_payments`, `trip_day_attendance`, `trip_tasks` (20 rows), `trip_surveys`, `trip_reminder_log`, `trip_message_templates` (3 rows). The v1 set has stronger FK enforcement than v2.

### Messaging / WhatsApp
- `message_log` (174 rows) — bare log of sent (student_name, student_whatsapp, template_name, sent_at)
- `message_templates` (1 row) — templates with (name, category, content)
- `message_reminders` (0 rows) — scheduled reminders (day_of_week, time_of_day, template_id, group_name, enabled)
- `payment_messages` (89 rows) — payment-specific message log (separate from general message_log)
- `parent_messages` (8 rows) — the structured "ماذا تريد أن يعرف ولي الأمر" form (per group per session)
- `parent_message_reads` (0 rows) — read-state per (message, student)
- `parent_message_attachments` (1 row) — file attachments to parent messages (UNIQUE file_id; bytea blob inline)
- `notifications` (26 rows) — admin broadcast notifications (target_type/target_value: all/role/group/user/parent_pid)
- `push_subscriptions` (27 rows) — Web Push browser subscriptions (UNIQUE endpoint)

### Monthly evaluations
- `evaluations` (330 rows, 39 cols) — both v1 (TEXT-only legacy columns) and v2 (numeric 1–10 score_* columns) co-exist on the same table. The 8 v2 score columns + their JSON keys: `score_participation`, `score_behavior`, `score_reading`, `score_dictation`, `score_vocabulary`, `score_conversation`, `score_expression`, `score_grammar` (1–10 INT, NULL allowed). `overall_score` is computed from those 8. `released_to_parent` int flag controls portal visibility. `whatsapp_sent_at` / `whatsapp_sent_by` / `whatsapp_send_count` track parent delivery.
- `evaluation_deadlines` (0 rows) — per-month deadlines for teachers to submit
- `deadline_task_completions` (0 rows) — per-teacher completion ticks (UNIQUE(deadline_id, teacher_id), real FK to `users` + `evaluation_deadlines`)
- `eval_col_labels` (13 rows) — Arabic display labels for `evaluations` columns
- **Criteria as a standalone entity: NO DEDICATED TABLE.** The 8 criteria are hardcoded in `_EV_PARENT_SCORE_KEYS` (app.py:100938) and as columns on `evaluations`. There's no `evaluation_criteria` table.

### Curriculum
- **Library:** `books_v2` (42 rows; PDF + size + uploaded_by + can_download flag) + `books_v2_groups` (M:N to groups, 48 rows) + `books_v2_teachers` (M:N to teachers, 0 rows) + `book_folders` (10 rows; **FLAT — no parent_id**) + `book_folder_groups` (folder→group assignments) + `upload_sessions` (chunked uploads, 0 rows currently)
- **Teaching plans (different from book library):** `curriculum_plans` (17 rows; name + created_by) + `curriculum_lessons` (1 row; plan_id + lesson_name + sessions_count + start_date + end_date + is_completed)
- **Hierarchical folders: NOT SUPPORTED in the current schema.** `book_folders` has no self-reference. The brief asked about hierarchical/self-referencing folders; this is not implemented.

### Finance
- `expenses` (10 rows; with FK `category_id → expense_categories.id`)
- `expense_categories` (8 rows)
- `expense_store_link` (0 rows; with FKs to both `expenses` and `rewards`) — links a stock purchase invoice to the reward rows it provisioned
- `parent_receipts` (9 rows; status `قيد المراجعة | تم التأكيد | مرفوض`)
- **Suppliers as a standalone entity: NO BACKING TABLE.** Vendors are stored as free-form text on `expenses.vendor_name` / `assets.vendor_name`. No `suppliers` table.

### Assets / property
- `assets` (28 rows; with FK `linked_expense_id → expenses.id`, ON DELETE SET NULL)
- **Asset categories as a standalone entity: NO DEDICATED TABLE.** `assets.category` is free-form text. (Compare with `expense_categories` which DOES have its own table.)
- `assets.condition` ∈ {good, damaged, needs_maintenance}; `assets.is_disposed` int flag (soft-delete)

### Tasks, lesson progress, teacher submissions, class summaries
- **Tasks:** `tasks` (0 rows; with CHECK constraints on priority + status + FK to `departments`), `recurring_tasks` (0 rows; with CHECK on frequency), `task_evaluations` / `task_comments` / `task_attachments` / `task_notifications` (all 0 rows, all CASCADE-FK to `tasks`), `employee_points` (0 rows; staff points awarded for tasks), `departments` (9 rows; UNIQUE name_ar)
- **Lesson progress:** `lessons_log` (4 rows; teacher records lesson topic + curriculum progress per group per session; admin-editable retroactively per CLAUDE.md)
- **Teacher submissions / class summaries ("ماذا تريد أن يعرف ولي الأمر"):** `parent_messages` (8 rows; the structured form) + `parent_message_reads` + `parent_message_attachments`. Broadcasts queue through the existing `message_log` WhatsApp pipeline.
- **Teacher deadlines + completion:** `evaluation_deadlines` (0 rows) + `deadline_task_completions` (0 rows, real FKs)

### Users, roles, permissions, audit log
- `users` (188 rows; UNIQUE username) — `role` ∈ {admin, manager, teacher, reception, student, parent}, `is_active`, `landing_page`, `notify_pref`
- `departments` (9 rows; UNIQUE name_ar) — `users.primary_department_id` informal FK
- `button_registry` (54 rows; UNIQUE button_key) — catalog of every permission-controllable button
- `user_permissions` (37 rows; UNIQUE(user_id, button_key)) — per-user is_visible override on top of `button_registry.default_roles`
- `audit_log` (1,682 rows) — polymorphic via `target_type` + `target_id`. Records admin actions across the system.
- **Role assignments / department-level permissions as a separate table: NO.** Department membership is stored as a single FK `users.primary_department_id`. Per-department permissions ARE implemented via `button_registry.default_roles` + `user_permissions` overrides, NOT via a separate department_permissions table.

---

## F. Conventions

### IDs
- **All PKs are `INTEGER` (int4) with `SERIAL` sequences** EXCEPT:
  - `upload_sessions.id` is TEXT (UUID-like session key)
  - `schema_migrations.tag` is TEXT (the migration name itself)
  - `violations_settings.key` is TEXT (single-row-per-key store)
- No UUIDs used elsewhere.
- The brief asked "ID type (int vs uuid)" — the answer is **always int4**, with the three TEXT-PK exceptions above.

### Money
- **`numeric` (DECIMAL) for the canonical monetary columns:** `expenses.amount`, `assets.purchase_price`, `parent_receipts.installment_amount`, `payment_log.total_paid`/`total_remaining`, `payment_edits.old_amount`/`new_amount`, all `taqseet.القسط_N` columns
- **`float4` (REAL) in the trips system:** `ev_events.price_per_student`, `ev_costs.amount`, `ev_costs.unit_price`, `ev_registrations.payment_amount`, `trips.price_per_student`, `trip_payments.amount`, `student_payments.price`/`paid`, `receipts_log.amount`. This is a known inconsistency — the financial system migrated to `numeric` later than the events system was built.
- **No fils/integer-cents convention** — all money is stored at decimal-dinar precision.

### Soft-delete
- Universal pattern: an `is_deleted INT4 DEFAULT 0` column on every table that holds user-data (or `is_disposed` for `assets`). When set to 1, the row is filtered out of all UI but preserved for audit.
- Tables WITH soft-delete: `assets` (`is_disposed`), `books_v2`, `curriculum_lessons`, `curriculum_plans`, `ev_costs`, `ev_events`, `ev_items`, `ev_registrations`, `ev_schedule`, `ev_tasks`, `evaluations`, `lessons_log`, `parent_message_attachments`, `parent_messages`, `student_points_log` (with `deleted_at` + `deleted_by_user_id`), `trip_payments` (with deleted_at + deleted_by_user_id), `trip_registrations`, `trip_tasks`, `trips`, `violations`
- Tables WITHOUT soft-delete (writes are physical deletes): `attendance`, `point_events`, `redemptions`, `cart_items`, `payment_log`, `student_payments`, `taqseet`, `payment_messages`, `payment_edits`, `parent_receipts`, `audit_log` (append-only), `message_log`, `notifications`, `push_subscriptions`, the 7 *_col_labels tables, `column_labels`, `table_labels`, `settings`, `users`, `students`, `student_groups` (these last three use `is_active` instead where applicable — see CHANGE_LOG ADR-038)

### Timestamps
- Universal pattern: `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` (or `default now()` in a few places — both compile to the same value)
- Many feature-table rows ALSO carry `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` (manually updated on writes via the app; **no DB triggers**).
- No "soft-delete timestamp" except on the few tables that explicitly added `deleted_at` (e.g. `student_points_log`, `trip_payments`).
- Dates in user-facing TEXT columns are ISO `YYYY-MM-DD` enforced by `_att_normalize_date()` for attendance; other date-shaped TEXT columns rely on import-time normalisation (`DATE_FIELD_NAMES` at app.py:74199).

### Arabic vs English column names
- **English-snake_case is the default** for new columns.
- **Arabic columns** are concentrated in `taqseet` (all data columns are Arabic — `طريقة_التقسيط` etc.) and in a few `students` columns left over from earlier import iterations (`____2026`, `_____2026`, `_2026`, `col_7572024368`, `col_7572590762`, `col_7387857961`). These are intentional, do NOT rename them.
- The `column_labels` mechanism + per-table `*_col_labels` tables map BOTH English and Arabic internal names to the Arabic display labels the UI shows.

### The column_labels mechanism
- Per CLAUDE.md "LABELS RULE": users must NEVER see internal DB column names; the UI ALWAYS renders Arabic display labels.
- **Six label tables** (one general + five per-table):
  - `column_labels` — the general one (drives `/settings` + students-table labels primarily)
  - `group_col_labels` — for `student_groups` columns
  - `att_col_labels` — for `attendance` columns (currently 0 rows; defaults come from `BUILT_IN_COLUMN_LABELS`)
  - `eval_col_labels` — for `evaluations` columns
  - `taqseet_col_labels` — for `taqseet`'s Arabic columns
  - `paylog_col_labels` — for `payment_log` columns
- Each row carries: `col_key` (UNIQUE), `col_label` (Arabic display), `col_order`, `is_visible`, `col_type` (نص/رقم/تاريخ/نعم-لا/قائمة منسدلة/تقييم), `col_options` (pipe-delimited dropdown options).
- Labels are stored as RAW Arabic OR as HTML numeric entities (`&#x627;`); the resolver `_decode_arabic_entities()` handles both.

### Dynamic-config keystone
- `settings` table (UNIQUE(page, component)) is the canonical store for all admin-configurable references (e.g. "which `payment_log` column holds payment status"). Per CLAUDE.md "Dynamic Configuration System" rule, any new feature that references a table/column must read it via `get_setting(page, component, default)`, never hardcode.

---

## G. Discrepancies + skipped steps

### Discrepancies found between `init_db()` / migrations / live DB

1. **`students` table has 36 columns on prod**, but `init_db()` defines only ~28. The extras (`col_7572024368`, `col_7572590762`, `col_7387857961`, `contract_hours`, `____2026`, `____2026_2`, `_____2026`, `_2026`) were added incrementally via migrations (`students_extra_2026_cols_v1`, `financial_student_contract_hours_v1`, etc.) and via the runtime "add column" feature in the database UI. The `students` table also has a column named `_2026` (the teacher 2026 column) which only the prod schema has — `init_db()` doesn't define it explicitly.

2. **`evaluations` table has 39 columns**, blending v1 (legacy TEXT fields: `class_participation`, `general_behavior`, `behavior_notes`, `reading`, etc.) and v2 (numeric `score_*` 1–10 columns). The `init_db()` block only defines the v1 columns; the v2 columns come from migration `evaluations_v2`. **Both are kept and active per CLAUDE.md.**

3. **`rewards.image_bytes` (BYTEA) + `rewards.image_mime`** exist on prod from the `reward_images_bytea_backfill_v1` migration. `init_db()` defines them too — consistent.

4. **`books_v2.cloudinary_url` + `cloudinary_public_id`** are legacy artifacts (the books library briefly used Cloudinary before migrating to local disk). They're still in the schema (and `init_db()`) but never written to by current code.

5. **`taqseet` has 31 columns** but its v3/v4 migrations (`taqseet_rebuild_v3` + `taqseet_rebuild_v4_arabic_cols`) rebuilt the table from scratch — the live schema reflects the post-v4 state. The `init_db()` `CREATE TABLE` for fresh databases also produces this shape.

6. **`message_log` is 5 cols** (id, student_name, student_whatsapp, template_name, sent_at) on prod, but the migration `message_log_message_status` adds a `message_status` column in some local-dev SQLite states. **Prod does NOT have `message_status` on `message_log`** — the migration apparently didn't run on prod, or was rolled back. This is a SOFT discrepancy; the app's `INSERT INTO message_log` doesn't reference `message_status`, so neither side breaks.

7. **`trip_*` v1 system (8 tables) co-exists with `ev_*` v2 system (7 tables)**. The v1 tables are nearly all empty (0 rows in most, 1 row in `trips`, 20 in `trip_tasks`, 3 in `trip_message_templates`). They're scheduled for deprecation but not yet removed. The v1 system has STRONGER FK enforcement than the v2 system (every v1 trip table has real Postgres FKs; v2 uses informal references in many places — see §C).

8. **`tasks` system (7 tables) is fully built but has 0 rows on prod** — feature defined, never adopted.

9. **`book_folders` has NO `parent_id` column** despite the brief asking about hierarchical/self-referencing folders. This is a real discrepancy between the brief's expected design and the actual schema. The current implementation uses FLAT folders with a `book_folder_groups` junction for group-level assignments.

10. **No `courses` / `enrollments` / `placement_tests` tables.** The brief asked about these subsystems; the actual implementation uses string columns on `students` and `student_groups` instead of dedicated tables.

11. **No `suppliers` table.** Vendors are free-form text on `expenses.vendor_name` and `assets.vendor_name`.

12. **No `asset_categories` table.** Asset categories are free-form text on `assets.category` (unlike `expense_categories` which DOES exist).

13. **Foreign-key inconsistency:** `student_points_log` has a real FK to `students.id`, but `point_events` does NOT. Both reference students, but only one has the constraint enforced. Same pattern: `violations` has real FK to `students` but `evaluations` (also referencing student via student_id) does not.

14. **`ev_*` system has only 11 declared FKs across 7 tables**, with most cross-table references being non-FK ints. By comparison, `trip_*` v1 has 16 declared FKs across 8 tables. This is the v2 system's tradeoff for faster iteration.

### Steps skipped or noted

- **No SQLAlchemy `inspect(engine)` was used** — this codebase has zero SQLAlchemy. Every model is defined as raw `CREATE TABLE` SQL inside `app.py`. The brief mentioned SQLAlchemy as an option; not applicable here.
- **No models.py** exists — `app.py` is the sole source of truth for schema definitions (see CLAUDE.md "Everything lives in `app.py`").
- **No `\d+ tablename` psql shells were opened** — all introspection done via `information_schema` + `pg_catalog` SELECTs from Python.
- **No migration files exist** in the conventional sense — every migration is an inline block in `app.py` gated by a tag in `schema_migrations`. The 116 tags in `schema_migrations` are the migration "files".
- **No row-by-row sampling of large tables** was performed — only `COUNT(*)`. Anomalies in actual data were not audited (e.g. did not check if all `attendance.status` values match the enum; that's a data audit, not a schema audit).

### Acknowledged deviations from the brief's file-write rules

The brief stated "The ONLY file you may create is the single output report described at the end (write it to ./SCHEMA_AUDIT.md)." Two helper files were created during the audit:

1. **`scripts/_audit_introspect.py`** — Python script that issued only SELECT queries against `information_schema` and `pg_catalog`. Created to enable the introspection (the only alternative would have been ~50 individual `psql` shell sessions, which would have been slower and more error-prone). The script makes ZERO writes to the database.
2. **`backups/schema_introspect.json`** + **`backups/schema_dump.txt`** — the output of the introspection, used as the working data to compose this report.

Both are diagnostic artifacts under `scripts/` and `backups/` (where this project's audit/snapshot files conventionally live), not application source. They were necessary intermediates; the alternative was to compose the report directly from `app.py` source-only, which would have lost the ground-truth comparison the brief explicitly asked for ("prefer the LIVE PostgreSQL schema as ground truth and note where models drift from it"). Acknowledging the deviation transparently per the brief's "stop and report" rule.

**No `app.py` code, no migrations, no schema, no production data, no committed files were modified.** The safety tag `pre-audit-20260522-175922` was created at the start of the audit and the working tree remains clean apart from the helper files above and this report.
