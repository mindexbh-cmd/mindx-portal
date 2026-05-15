# Feature Inventory

*Source of truth for `feature-protector-agent`. Auto-generated bootstrap on 2026-05-15; enrich incrementally -- do NOT regenerate from scratch.*

**Totals:** 502 routes (355 require login). Categories: 69.

---

## Top-20 critical features (manually annotated)

Each has an explicit assertion that MUST hold after any change. If a proposed change breaks one of these, default verdict is **REJECT**.

| # | Feature | Route | Handler | Critical assertion |
|---|---|---|---|---|
| 1 | Login form | `/login` | `login` | Accepts username + password. Submits POST to /login. Role-dispatch routes admin->/dashboard, teacher->/teacher/hub, role=student->/portal/parent-hub, role=parent->/portal/parent. Error message stays Arabic-entity-encoded. |
| 2 | Admin dashboard | `/dashboard` | `index_page` | Loads HOME_HTML. Requires login_required. Contains the action grid + stats grid. Mobile breakpoints at 768px / 460px. |
| 3 | Database page | `/database` | `database_page` | Loads DATABASE_HTML. Contains the students/groups/attendance/taqseet tabs + the table tree. Custom-column add/rename/delete via /api/table/<tid>/*. |
| 4 | Attendance page | `/attendance` | `attendance_page` | Loads ATTENDANCE_HTML. Date input is <input type="date"> -> must send YYYY-MM-DD. Loads via /api/attendance/check (whitespace-tolerant filter). |
| 5 | Groups page | `/groups` | `groups_page` | Loads GROUPS_HTML. Detail panel uses _groups_days_column resolver for the days column. Authoritative-column resolver MUST stay in place. |
| 6 | Parent V2 hub | `/portal/parent-hub` | `portal_parent_hub_page` | Requires login_required + role=student. Fetches /api/portal/student/meta and renders 6 cards (payments/attendance/points/messages/evaluations/curriculum). Each card href is DIRECT -- no PID prompt. |
| 7 | Parent attendance sub-page | `/portal/parent-hub/attendance` | `portal_parent_hub_attendance_page` | Direct page. Renders PORTAL_PARENT_ATTENDANCE_HTML. Must NOT redirect through any PID page. |
| 8 | Parent payments sub-page | `/portal/parent-hub/payments` | `portal_parent_hub_payments_page` | Direct page. Reads /api/parent/payments via session-bound student. |
| 9 | Parent points sub-page | `/portal/parent-hub/points` | `portal_parent_hub_points_page` | Serves PORTAL_STUDENT_HTML (same as /portal/student). Avatar + balance + 8-week chart + rewards shop + redemption history. |
| 10 | Parent messages sub-page | `/portal/parent-hub/messages` | `portal_parent_hub_messages_page` | Reads parent_messages joined with parent_message_reads. Renders unread badge via /api/parent-messages/parent-unread-count. |
| 11 | Parent evaluations sub-page | `/portal/parent-hub/evaluations` | `portal_parent_hub_evaluations_page` | Reads evaluations where released_to_parent=1. Shows evaluations_v2 columns (score_*, evaluation_month, overall_score). |
| 12 | Public parent PID page | `/parent` | `parent_portal` | Anonymous visitor -> PORTAL_PARENT_PID_HUB_HTML (PID prompt). Logged-in role=student -> 302 to /portal/parent-hub; role=parent -> 302 to /portal/parent. WhatsApp deep-link compat REQUIRES the anonymous branch. |
| 13 | Public parent legacy | `/parent/legacy` | `parent_portal_legacy` | Anonymous -> PARENT_HTML (flat-scroll). Logged-in users redirected to their proper hub. Kept indefinitely as fallback for WhatsApp deep-links. |
| 14 | Parent V1 portal | `/portal/parent` | `portal_parent_page` | Requires login_required + role=parent. Multi-child UI driven by linked_parent_for JSON array. Resolves children via /api/portal/parent/me. |
| 15 | Teacher hub | `/teacher/hub` | `teacher_hub_page` | Requires login_required + role=teacher. Landing page for teacher accounts. |
| 16 | Health endpoint | `/api/health` | `api_health` | Public, unauthenticated. 503 on DB-ping or scratch-write failure. Used by safe_deploy.py as deploy gate. |
| 17 | Deep health endpoint | `/api/health/deep` | `api_health_deep` | Public. Row counts for critical user-data tables + books-storage writability. |
| 18 | Parent PID lookup | `/api/parent/lookup` | `api_parent_lookup` | Public POST, rate-limited per IP. Validates personal_id via _resolve_student_row_by_pid (bidi-tolerant). Returns attendance + payment summary + books. |
| 19 | Hub stats | `/api/parent/hub-stats` | `api_parent_hub_stats` | Powers the 5 hub-card subtitles. Two-tier teacher_name SELECT (Postgres-compat for pre-migration DBs). |
| 20 | Settings page | `/settings` | `settings_page` | Admin-only. Reads /api/settings + /api/settings/tables + /api/settings/columns/<table>. Backed by the Dynamic Configuration System. |

---

## Full route inventory (auto-generated)

Grouped by category. Each row: handler + line + methods + auth.

### `core` (29 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/` | GET | `index` | - | 28462 |
| `/.well-known/assetlinks.json` | GET | `well_known_assetlinks` | - | 105670 |
| `/__offline__` | GET | `pwa_offline_fallback` | - | 105636 |
| `/assets` | GET | `assets_page` | login_required | 43150 |
| `/attendance` | GET | `attendance` | login_required | 28720 |
| `/dashboard` | GET | `dashboard` | login_required | 28666 |
| `/database` | GET | `database` | - | 28736 |
| `/events/register/<token>` | GET | `events_public_register_get` | - | 96219 |
| `/events/register/<token>` | POST | `events_public_register_post` | - | 96293 |
| `/expenses` | GET | `expenses_page` | login_required | 42457 |
| `/groups` | GET | `groups` | login_required | 65688 |
| `/login` | GET,POST | `login` | - | 28520 |
| `/logout` | GET | `logout` | - | 28586 |
| `/manifest.json` | GET | `pwa_manifest` | - | 105731 |
| `/mx-helpers.js` | GET | `mx_helpers_js` | - | 76407 |
| `/points/board` | GET | `points_board_page` | login_required | 83514 |
| `/points/board/<path:group>` | GET | `points_board_page` | login_required | 83515 |
| `/points/bulk-adjust` | GET | `points_bulk_adjust_page` | login_required | 83474 |
| `/points/manage` | GET | `points_manage_page` | login_required | 83505 |
| `/settings` | GET | `settings_page` | - | 72422 |
| `/sw.js` | GET | `pwa_service_worker` | - | 105615 |
| `/tasks` | GET | `tasks_list_page` | login_required | 47994 |
| `/tasks/<int:tid>` | GET | `tasks_detail_page` | login_required | 47978 |
| `/tasks/dashboard/admin` | GET | `tasks_dashboard_admin_page` | login_required | 46865 |
| `/tasks/dashboard/personal` | GET | `tasks_dashboard_personal_page` | login_required | 46496 |
| `/tasks/dashboard/team` | GET | `tasks_dashboard_team_page` | login_required | 46620 |
| `/tasks/recurring` | GET | `tasks_recurring_page` | login_required | 47377 |
| `/verify-receipt/<path:receipt_number>` | GET | `verify_receipt_page` | - | 32795 |
| `/version` | GET | `version_endpoint` | - | 28592 |

### `parent-public` (9 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/parent` | GET | `parent_portal` | - | 28793 |
| `/parent/book/<int:bid>/download` | GET | `parent_book_download` | - | 91032 |
| `/parent/book/<int:bid>/meta` | GET | `parent_book_meta` | - | 90874 |
| `/parent/book/<int:bid>/page/<int:n>.webp` | GET | `parent_book_page_webp` | - | 90913 |
| `/parent/book/<int:bid>/view` | GET | `parent_book_view` | - | 90966 |
| `/parent/book/<int:bid>/viewer` | GET | `parent_book_viewer` | - | 90811 |
| `/parent/evaluations` | GET | `parent_evaluations_api` | - | 90356 |
| `/parent/evaluations/view` | GET | `parent_evaluations_page` | - | 90795 |
| `/parent/legacy` | GET | `parent_portal_legacy` | - | 28814 |

### `parent-hub` (7 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/portal/parent-hub` | GET | `portal_parent_hub_page` | login_required | 78717 |
| `/portal/parent-hub/attendance` | GET | `portal_parent_hub_attendance_page` | login_required | 78740 |
| `/portal/parent-hub/curriculum` | GET | `portal_books_v2_parent_page` | login_required | 93573 |
| `/portal/parent-hub/evaluations` | GET | `portal_parent_hub_evaluations_page` | login_required | 79346 |
| `/portal/parent-hub/messages` | GET | `portal_parent_hub_messages_page` | login_required | 79025 |
| `/portal/parent-hub/payments` | GET | `portal_parent_hub_payments_page` | login_required | 78729 |
| `/portal/parent-hub/points` | GET | `portal_parent_hub_points_page` | login_required | 78751 |

### `parent-v1` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/portal/parent` | GET | `portal_parent_page` | login_required | 79575 |

### `portal` (2 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/portal/change-password` | GET | `portal_change_pw_page` | login_required | 77921 |
| `/portal/student` | GET | `portal_student_page` | login_required | 77952 |

### `teacher` (6 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/teacher/attendance` | GET | `teacher_attendance_page` | login_required | 49765 |
| `/teacher/books` | GET | `teacher_books_v2_page` | login_required | 93741 |
| `/teacher/evaluations` | GET | `teacher_evaluations_page` | login_required | 52006 |
| `/teacher/hub` | GET | `teacher_hub_page` | login_required | 49890 |
| `/teacher/lessons` | GET | `teacher_lessons_page` | login_required | 50338 |
| `/teacher/parent-messages` | GET | `teacher_parent_messages_page` | login_required | 50906 |

### `admin` (23 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/admin/backups` | GET | `admin_backups_page` | - | 77119 |
| `/admin/books` | GET | `admin_books_v2_page` | login_required | 93398 |
| `/admin/diag/paylog-compare` | GET | `admin_diag_paylog_compare` | login_required | 71119 |
| `/admin/diag/paylog-mirror-status` | GET | `admin_diag_paylog_mirror_status` | login_required | 70997 |
| `/admin/diag/strong-link-status` | GET | `admin_diag_strong_link_status` | login_required | 70905 |
| `/admin/docs` | GET | `admin_docs_page` | - | 49348 |
| `/admin/evaluations` | GET | `admin_evaluations_page` | login_required | 54195 |
| `/admin/events` | GET | `admin_events_list_page` | login_required | 94334 |
| `/admin/events/<int:eid>` | GET | `admin_events_detail_page` | login_required | 98105 |
| `/admin/events/<int:eid>/followup` | GET | `admin_events_followup_page` | login_required | 98138 |
| `/admin/events/<int:eid>/print/financial` | GET | `admin_events_print_financial` | login_required | 97003 |
| `/admin/events/<int:eid>/print/full` | GET | `admin_events_print_full` | login_required | 97017 |
| `/admin/events/<int:eid>/print/list` | GET | `admin_events_print_list` | login_required | 96977 |
| `/admin/events/<int:eid>/print/schedule` | GET | `admin_events_print_schedule` | login_required | 96990 |
| `/admin/events/<int:eid>/receipts/<path:filename>` | GET | `admin_events_receipt_serve` | login_required | 96407 |
| `/admin/lessons` | GET | `admin_lessons_page` | login_required | 52693 |
| `/admin/parent-messages` | GET | `admin_parent_messages_page` | login_required | 53322 |
| `/admin/permissions` | GET | `admin_permissions_page` | - | 30824 |
| `/admin/receipts` | GET | `admin_receipts_page` | - | 29777 |
| `/admin/table-audit` | GET | `admin_table_audit_page` | - | 77310 |
| `/admin/teacher-deliveries` | GET | `admin_teacher_deliveries_page` | login_required | 56807 |
| `/admin/violations` | GET | `admin_violations_page` | login_required | 61005 |
| `/admin/violations-catalog` | GET | `admin_violations_catalog_page` | login_required | 61018 |

### `api:admin` (78 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/admin/attendance/frequent-absences` | GET | `api_attfreq_query` | login_required | 85370 |
| `/api/admin/attendance/send-absence-alert` | POST | `api_attfreq_send` | login_required | 85506 |
| `/api/admin/attendance/send-absence-alert-bulk` | GET | `` | - | 85594 |
| `/api/admin/events` | GET | `api_admin_events_list` | login_required | 94347 |
| `/api/admin/events` | POST | `api_admin_events_create` | login_required | 94414 |
| `/api/admin/events/<int:eid>` | PATCH | `api_admin_events_update` | login_required | 94622 |
| `/api/admin/events/<int:eid>` | DELETE | `api_admin_events_delete` | login_required | 97819 |
| `/api/admin/events/<int:eid>` | GET | `api_admin_events_get` | login_required | 98925 |
| `/api/admin/events/<int:eid>/costs` | GET | `api_admin_events_costs_list` | login_required | 94854 |
| `/api/admin/events/<int:eid>/costs` | POST | `api_admin_events_costs_create` | login_required | 94879 |
| `/api/admin/events/<int:eid>/costs/<int:cid>` | PATCH | `api_admin_events_costs_update` | login_required | 94956 |
| `/api/admin/events/<int:eid>/costs/<int:cid>` | DELETE | `api_admin_events_costs_delete` | login_required | 95049 |
| `/api/admin/events/<int:eid>/followup` | GET | `api_admin_events_followup` | login_required | 98162 |
| `/api/admin/events/<int:eid>/items` | GET | `api_admin_events_items_list` | login_required | 95139 |
| `/api/admin/events/<int:eid>/items` | POST | `api_admin_events_items_create` | login_required | 95161 |
| `/api/admin/events/<int:eid>/items/<int:iid>` | PATCH | `api_admin_events_items_update` | login_required | 95222 |
| `/api/admin/events/<int:eid>/items/<int:iid>` | DELETE | `api_admin_events_items_delete` | login_required | 95299 |
| `/api/admin/events/<int:eid>/messages/render` | POST | `api_admin_events_msg_render` | login_required | 96553 |
| `/api/admin/events/<int:eid>/messages/templates` | GET | `api_admin_events_msg_templates` | login_required | 96523 |
| `/api/admin/events/<int:eid>/registrations` | GET | `api_admin_events_reg_list` | login_required | 95513 |
| `/api/admin/events/<int:eid>/registrations` | POST | `api_admin_events_reg_create` | login_required | 95550 |
| `/api/admin/events/<int:eid>/registrations/<int:rid>` | PATCH | `api_admin_events_reg_update` | login_required | 95649 |
| `/api/admin/events/<int:eid>/registrations/<int:rid>` | DELETE | `api_admin_events_reg_delete` | login_required | 95746 |
| `/api/admin/events/<int:eid>/registrations/bulk-attendance` | POST | `api_admin_events_reg_bulk_attendance` | login_required | 95781 |
| `/api/admin/events/<int:eid>/schedule` | GET | `api_admin_events_schedule_list` | login_required | 97486 |
| `/api/admin/events/<int:eid>/schedule` | POST | `api_admin_events_schedule_create` | login_required | 97526 |
| `/api/admin/events/<int:eid>/schedule/<int:sid>` | PATCH | `api_admin_events_schedule_update` | login_required | 97595 |
| `/api/admin/events/<int:eid>/schedule/<int:sid>` | DELETE | `api_admin_events_schedule_delete` | login_required | 97674 |
| `/api/admin/events/<int:eid>/schedule/<int:sid>/toggle-complete` | GET | `` | - | 97708 |
| `/api/admin/events/<int:eid>/schedule/reorder` | POST | `api_admin_events_schedule_reorder` | login_required | 97773 |
| `/api/admin/events/<int:eid>/status` | PATCH | `api_admin_events_set_status` | login_required | 94549 |
| `/api/admin/events/<int:eid>/tasks` | GET | `api_admin_events_tasks_list` | login_required | 97110 |
| `/api/admin/events/<int:eid>/tasks` | POST | `api_admin_events_tasks_create` | login_required | 97158 |
| `/api/admin/events/<int:eid>/tasks/<int:tid>` | PATCH | `api_admin_events_tasks_update` | login_required | 97223 |
| `/api/admin/events/<int:eid>/tasks/<int:tid>` | DELETE | `api_admin_events_tasks_delete` | login_required | 97316 |
| `/api/admin/events/<int:eid>/tasks/reload-template` | POST | `api_admin_events_tasks_reload_template` | login_required | 97350 |
| `/api/admin/events/alerts` | GET | `api_admin_events_alerts` | login_required | 97887 |
| `/api/admin/events/assignees` | GET | `api_admin_events_assignees` | login_required | 97411 |
| `/api/admin/events/student-groups` | GET | `api_admin_events_student_groups` | login_required | 97861 |
| `/api/admin/groups/<int:gid>` | PATCH | `api_admin_groups_patch` | login_required | 65774 |
| `/api/admin/parent-audit-log` | GET | `api_admin_parent_audit_log` | login_required | 104362 |
| `/api/admin/parents` | GET | `api_admin_parents_list` | - | 79383 |
| `/api/admin/parents` | POST | `api_admin_parents_create` | - | 79423 |
| `/api/admin/parents/<int:pid>` | PATCH | `api_admin_parents_update` | - | 79517 |
| `/api/admin/parents/<int:pid>/reset-password` | POST | `api_admin_parents_reset` | - | 79554 |
| `/api/admin/push-subscriptions-count` | GET | `api_admin_push_subscriptions_count` | login_required | 104878 |
| `/api/admin/push/history` | GET | `api_admin_push_history` | - | 104838 |
| `/api/admin/push/send` | POST | `api_admin_push_send` | - | 104666 |
| `/api/admin/receipts` | GET | `api_admin_receipts_list` | - | 29782 |
| `/api/admin/receipts/<int:rid>/confirm` | POST | `api_admin_receipt_confirm` | - | 29918 |
| `/api/admin/receipts/<int:rid>/file` | GET | `api_admin_receipt_file` | - | 29874 |
| `/api/admin/receipts/<int:rid>/reject` | POST | `api_admin_receipt_reject` | - | 30095 |
| `/api/admin/receipts/<int:rid>/status` | POST | `api_admin_receipt_status` | - | 29898 |
| `/api/admin/receipts/count` | GET | `api_admin_receipts_count` | - | 29860 |
| `/api/admin/table-audit` | GET | `api_admin_table_audit` | - | 48482 |
| `/api/admin/table-audit/<table_name>/approve` | POST | `api_admin_table_audit_approve` | - | 48503 |
| `/api/admin/table-audit/<table_name>/delete` | POST | `api_admin_table_audit_delete` | - | 48536 |
| `/api/admin/table/truncate` | POST | `api_admin_table_truncate` | - | 34584 |
| `/api/admin/teacher/<int:teacher_id>/groups` | GET | `api_admin_teacher_groups` | login_required | 63716 |
| `/api/admin/teacher/<int:teacher_id>/send-request` | GET | `` | - | 63878 |
| `/api/admin/teacher/<int:teacher_id>/students` | GET | `api_admin_teacher_students` | login_required | 63782 |
| `/api/admin/users` | GET | `api_admin_users_list` | - | 30830 |
| `/api/admin/users/<int:uid>` | PATCH | `api_admin_user_patch` | - | 30898 |
| `/api/admin/users/<int:uid>/permissions` | GET | `api_admin_user_permissions_get` | - | 30853 |
| `/api/admin/users/<int:uid>/permissions` | PATCH | `api_admin_user_permissions_patch` | - | 30994 |
| `/api/admin/users/<int:uid>/reset-permissions` | POST | `api_admin_user_reset_permissions` | - | 31049 |
| `/api/admin/violations` | POST | `api_admin_violations_create` | login_required | 61191 |
| `/api/admin/violations` | GET | `api_admin_violations_list` | login_required | 61357 |
| `/api/admin/violations/<int:vid>` | PATCH | `api_admin_violations_update` | login_required | 61464 |
| `/api/admin/violations/<int:vid>` | DELETE | `api_admin_violations_delete` | login_required | 61639 |
| `/api/admin/violations/<int:vid>/pdf` | GET | `api_admin_violations_single_pdf` | login_required | 62512 |
| `/api/admin/violations/<int:vid>/pledge` | GET | `api_admin_violations_pledge` | login_required | 62490 |
| `/api/admin/violations/<int:vid>/send-whatsapp` | GET | `` | - | 62834 |
| `/api/admin/violations/dashboard-stats` | GET | `api_admin_violations_dashboard_stats` | login_required | 62603 |
| `/api/admin/violations/stats` | GET | `api_admin_violations_stats` | login_required | 61031 |
| `/api/admin/violations/student-history` | GET | `api_admin_violations_student_history` | login_required | 61692 |
| `/api/admin/violations/student-monthly-pdf` | GET | `api_admin_violations_manual_monthly_pdf` | login_required | 62907 |
| `/api/admin/violations/student/<int:sid>/monthly-pdf` | GET | `` | - | 62550 |

### `api:assets` (6 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/assets` | POST | `api_assets_create` | login_required | 40729 |
| `/api/assets` | GET | `api_assets_list` | login_required | 40796 |
| `/api/assets/<int:aid>` | GET | `api_assets_detail` | login_required | 40868 |
| `/api/assets/<int:aid>` | PATCH | `api_assets_update` | login_required | 40881 |
| `/api/assets/<int:aid>/dispose` | POST | `api_assets_dispose` | login_required | 40994 |
| `/api/assets/<int:aid>/image` | GET | `api_assets_image` | login_required | 40962 |

### `api:att-columns` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/att-columns` | GET | `api_att_columns_get` | - | 65224 |
| `/api/att-columns` | POST | `api_att_columns_add` | - | 65238 |
| `/api/att-columns/<col_key>` | DELETE | `api_att_columns_delete` | - | 65274 |
| `/api/att-columns/<col_key>` | PUT | `api_att_columns_rename` | - | 65289 |

### `api:attendance` (15 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/attendance` | GET | `api_attendance_get` | login_required | 64584 |
| `/api/attendance` | POST | `api_attendance_add` | login_required | 64670 |
| `/api/attendance/<int:rid>` | PUT | `api_attendance_update` | login_required | 64759 |
| `/api/attendance/<int:rid>` | DELETE | `api_attendance_delete` | login_required | 64779 |
| `/api/attendance/<int:rid>/mark-sent` | POST | `api_attendance_mark_sent` | login_required | 65152 |
| `/api/attendance/<int:rid>/unmark-sent` | POST | `api_attendance_unmark_sent` | login_required | 65164 |
| `/api/attendance/by-date-group` | GET | `api_attendance_by_date_group` | login_required | 64790 |
| `/api/attendance/by-date-summary` | GET | `api_attendance_by_date_summary` | login_required | 64856 |
| `/api/attendance/check` | GET | `api_attendance_check` | login_required | 66387 |
| `/api/attendance/general-stats` | GET | `api_attendance_general_stats` | login_required | 65175 |
| `/api/attendance/group-dates` | GET | `api_attendance_group_dates` | login_required | 69925 |
| `/api/attendance/groups` | GET | `api_attendance_groups` | login_required | 69909 |
| `/api/attendance/sessions` | GET | `api_attendance_sessions` | login_required | 69891 |
| `/api/attendance/student-stats` | GET | `api_attendance_student_stats` | login_required | 66811 |
| `/api/attendance/summary` | GET | `api_attendance_summary` | login_required | 66871 |

### `api:backup` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/backup/download` | GET | `api_backup_download` | - | 34886 |
| `/api/backup/excel` | GET | `api_backup_excel` | - | 35144 |
| `/api/backup/last` | GET | `api_backup_last` | - | 34863 |
| `/api/backup/progress` | GET | `api_backup_progress` | - | 34762 |

### `api:backups` (7 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/backups` | GET | `api_backups_list` | - | 34714 |
| `/api/backups/<int:bid>` | DELETE | `api_backups_delete` | - | 34796 |
| `/api/backups/<int:bid>/download` | GET | `api_backups_download` | - | 34772 |
| `/api/backups/<int:bid>/report` | GET | `api_backups_report` | - | 34740 |
| `/api/backups/run` | POST | `api_backups_run` | - | 34494 |
| `/api/backups/settings` | GET | `api_backups_settings_get` | - | 34818 |
| `/api/backups/settings` | PATCH,PUT | `api_backups_settings_set` | - | 34834 |

### `api:book-folders` (7 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/book-folders` | GET | `api_book_folders_list` | login_required | 87464 |
| `/api/book-folders` | POST | `api_book_folders_create` | login_required | 87519 |
| `/api/book-folders/<int:fid>` | PATCH | `api_book_folders_update` | login_required | 87617 |
| `/api/book-folders/<int:fid>` | DELETE | `api_book_folders_delete` | login_required | 87718 |
| `/api/book-folders/<int:fid>/books` | GET | `api_book_folders_get_books` | login_required | 88021 |
| `/api/book-folders/<int:fid>/groups` | GET | `api_book_folders_get_groups` | login_required | 87780 |
| `/api/book-folders/<int:fid>/groups` | PUT | `api_book_folders_set_groups` | login_required | 87860 |

### `api:books` (25 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/books` | GET | `api_books_v2_list_admin` | login_required | 86976 |
| `/api/books/<int:bid>` | GET | `api_books_v2_get_one` | login_required | 86997 |
| `/api/books/<int:bid>` | PATCH | `api_books_v2_update` | login_required | 87183 |
| `/api/books/<int:bid>` | DELETE | `api_books_v2_delete` | login_required | 87229 |
| `/api/books/<int:bid>/download` | GET | `api_books_v2_download` | login_required | 89237 |
| `/api/books/<int:bid>/groups` | POST | `api_books_v2_set_groups` | login_required | 87272 |
| `/api/books/<int:bid>/move` | PATCH | `api_books_v2_move` | login_required | 88941 |
| `/api/books/<int:bid>/reupload` | POST | `api_books_v2_reupload` | login_required | 87115 |
| `/api/books/<int:bid>/teachers` | POST | `api_books_v2_set_teachers` | login_required | 87419 |
| `/api/books/<int:bid>/view` | GET | `api_books_v2_view` | login_required | 89231 |
| `/api/books/all-with-folders` | GET | `api_books_v2_all_with_folders` | login_required | 86871 |
| `/api/books/bulk-publish` | POST | `api_books_v2_bulk_publish` | login_required | 87303 |
| `/api/books/cleanup-orphans` | POST | `api_books_v2_cleanup_orphans` | login_required | 91112 |
| `/api/books/diag` | GET | `api_books_v2_diag` | login_required | 91176 |
| `/api/books/for-student/<int:sid>` | GET | `api_books_v2_for_student` | login_required | 89089 |
| `/api/books/for-teacher` | GET | `api_books_v2_for_teacher` | login_required | 89051 |
| `/api/books/groups-list` | GET | `api_books_v2_groups_list` | login_required | 86850 |
| `/api/books/storage-check` | GET | `api_books_v2_storage_check` | login_required | 91043 |
| `/api/books/teachers-list` | GET | `api_books_v2_teachers_list` | login_required | 86953 |
| `/api/books/upload` | POST | `api_books_v2_upload` | login_required | 87010 |
| `/api/books/upload-multi` | POST | `api_books_v2_upload_multi` | login_required | 88145 |
| `/api/books/upload/chunk` | POST | `api_books_chunked_chunk` | login_required | 88514 |
| `/api/books/upload/finalize` | POST | `api_books_chunked_finalize` | login_required | 88612 |
| `/api/books/upload/init` | POST | `api_books_chunked_init` | login_required | 88446 |
| `/api/books/upload/status` | GET | `api_books_chunked_status` | login_required | 88909 |

### `api:center` (7 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/center/auto-meta` | GET | `api_center_auto_meta` | login_required | 66369 |
| `/api/center/exceptions` | GET | `api_center_exceptions_list` | - | 66247 |
| `/api/center/exceptions` | POST | `api_center_exceptions_add` | - | 66261 |
| `/api/center/exceptions/<int:eid>` | DELETE | `api_center_exceptions_delete` | - | 66294 |
| `/api/center/exceptions/replace` | POST | `api_center_exceptions_replace` | - | 66309 |
| `/api/center/mode` | GET | `api_center_mode_get` | login_required | 66344 |
| `/api/center/mode` | PATCH,PUT | `api_center_mode_set` | - | 66352 |

### `api:columns` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/columns` | GET | `api_columns_get` | - | 33341 |
| `/api/columns` | POST | `api_columns_add` | - | 33392 |
| `/api/columns/<col_key>` | DELETE | `api_columns_delete` | - | 33440 |
| `/api/columns/<col_key>` | PUT | `api_columns_update` | - | 33455 |

### `api:custom-table` (7 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/custom-table/<tid>/add-column` | POST | `api_unified_add_column` | - | 36502 |
| `/api/custom-table/<tid>/column-type` | PATCH | `api_unified_set_column_type` | - | 36761 |
| `/api/custom-table/<tid>/columns` | GET | `api_unified_columns_get` | login_required | 36416 |
| `/api/custom-table/<tid>/delete-column/<col_name>` | DELETE | `api_unified_delete_column` | - | 36795 |
| `/api/custom-table/<tid>/rename` | PATCH | `api_unified_rename_table` | - | 37051 |
| `/api/custom-table/<tid>/rename-column` | PATCH | `api_unified_rename_column` | - | 36595 |
| `/api/custom-table/<tid>/reorder-columns` | PATCH | `api_unified_reorder_columns` | - | 36678 |

### `api:custom-tables` (9 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/custom-tables` | GET | `api_custom_tables_get` | - | 65307 |
| `/api/custom-tables` | POST | `api_custom_tables_create` | - | 65325 |
| `/api/custom-tables/<int:tid>` | DELETE | `api_custom_tables_delete` | - | 65349 |
| `/api/custom-tables/<int:tid>/cols` | POST | `api_custom_table_col_add` | - | 65406 |
| `/api/custom-tables/<int:tid>/cols/<col_key>` | DELETE | `api_custom_table_col_delete` | - | 65436 |
| `/api/custom-tables/<int:tid>/cols/<col_key>` | PUT | `api_custom_table_col_rename` | - | 65451 |
| `/api/custom-tables/<int:tid>/rows` | POST | `api_custom_table_row_add` | - | 65368 |
| `/api/custom-tables/<int:tid>/rows/<int:rid>` | PUT | `api_custom_table_row_update` | - | 65382 |
| `/api/custom-tables/<int:tid>/rows/<int:rid>` | DELETE | `api_custom_table_row_delete` | - | 65395 |

### `api:dashboard` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/dashboard/active-groups-detailed` | GET | `api_dashboard_active_groups_detailed` | login_required | 66672 |
| `/api/dashboard/active-groups-today` | GET | `api_dashboard_active_groups_today` | login_required | 66765 |
| `/api/dashboard/recent-activity` | GET | `api_dashboard_recent_activity` | login_required | 66639 |
| `/api/dashboard/stats` | GET | `api_dashboard_stats` | login_required | 66448 |

### `api:departments` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/departments` | GET | `api_departments_list` | login_required | 48009 |

### `api:docs` (5 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/docs/capture-all` | POST | `api_docs_capture_all` | - | 49032 |
| `/api/docs/capture/<int:page_id>` | POST | `api_docs_capture_one` | - | 49003 |
| `/api/docs/pages` | GET | `api_docs_pages_list` | - | 48949 |
| `/api/docs/screenshots/<int:page_id>` | GET | `api_docs_screenshot_history` | - | 49104 |
| `/api/docs/upload/<int:page_id>` | POST | `api_docs_upload` | - | 49065 |

### `api:eval-columns` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/eval-columns` | GET | `api_eval_columns_get` | - | 37145 |
| `/api/eval-columns` | POST | `api_eval_columns_add` | - | 37152 |
| `/api/eval-columns/<col_key>` | DELETE | `api_eval_columns_delete` | - | 37192 |
| `/api/eval-columns/<col_key>` | PUT | `api_eval_columns_update` | - | 37207 |

### `api:evaluations` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/evaluations` | GET | `api_evaluations_get` | login_required | 37083 |
| `/api/evaluations` | POST | `api_evaluations_add` | login_required | 37090 |
| `/api/evaluations/<int:rid>` | PUT | `api_evaluations_update` | login_required | 37117 |
| `/api/evaluations/<int:rid>` | DELETE | `api_evaluations_delete` | login_required | 37134 |

### `api:expenses` (9 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/expenses` | POST | `api_expenses_create` | login_required | 40201 |
| `/api/expenses` | GET | `api_expenses_list` | login_required | 40384 |
| `/api/expenses/<int:eid>` | GET | `api_expenses_detail` | login_required | 40496 |
| `/api/expenses/<int:eid>` | PATCH | `api_expenses_update` | login_required | 40513 |
| `/api/expenses/<int:eid>` | DELETE | `api_expenses_delete` | login_required | 40610 |
| `/api/expenses/<int:eid>/receipt` | GET | `api_expenses_receipt` | login_required | 40635 |
| `/api/expenses/categories` | GET | `api_expenses_categories` | login_required | 40179 |
| `/api/expenses/dashboard` | GET | `api_expenses_dashboard` | login_required | 41124 |
| `/api/expenses/my-summary` | GET | `api_expenses_my_summary` | login_required | 41321 |

### `api:group-columns` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/group-columns` | GET | `api_group_columns_get` | - | 33470 |
| `/api/group-columns` | POST | `api_group_columns_add` | - | 33477 |
| `/api/group-columns/<col_key>` | DELETE | `api_group_columns_delete` | - | 33514 |
| `/api/group-columns/<col_key>` | PUT | `api_group_columns_update` | - | 33529 |

### `api:groups` (9 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/groups` | GET | `api_groups_get` | login_required | 65693 |
| `/api/groups` | POST | `api_groups_add` | login_required | 65726 |
| `/api/groups/<int:gid>` | PUT | `api_groups_update` | login_required | 65741 |
| `/api/groups/<int:gid>` | DELETE | `api_groups_delete` | login_required | 65762 |
| `/api/groups/<int:gid>/detail` | GET | `api_group_detail` | login_required | 32030 |
| `/api/groups/bulk` | POST | `api_groups_bulk` | login_required | 33323 |
| `/api/groups/cleanup-empty` | POST | `api_groups_cleanup_empty` | login_required | 65923 |
| `/api/groups/filters` | GET | `api_groups_filters` | login_required | 31977 |
| `/api/groups/search` | GET | `api_groups_search` | login_required | 31746 |

### `api:groups-students` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/groups-students` | GET | `api_groups_students` | login_required | 65935 |

### `api:health` (2 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/health` | GET | `api_health` | - | 105793 |
| `/api/health/deep` | GET | `api_health_deep` | - | 105823 |

### `api:import` (2 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/import` | POST | `api_import` | - | 69456 |
| `/api/import/from-drive` | POST | `api_import_from_drive` | - | 69596 |

### `api:lessons` (8 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/lessons/export` | GET | `api_lessons_export` | login_required | 84051 |
| `/api/lessons/log` | POST | `api_lessons_log_create` | login_required | 83580 |
| `/api/lessons/log` | GET | `api_lessons_log_list` | login_required | 83663 |
| `/api/lessons/log/<int:lid>` | PATCH | `api_lessons_log_update` | login_required | 83715 |
| `/api/lessons/log/<int:lid>` | DELETE | `api_lessons_log_delete` | login_required | 83811 |
| `/api/lessons/missing` | GET | `api_lessons_missing` | login_required | 83943 |
| `/api/lessons/stats` | GET | `api_lessons_stats` | login_required | 83846 |
| `/api/lessons/teachers` | GET | `api_lessons_teachers` | login_required | 84009 |

### `api:logout` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/logout` | POST,GET | `api_logout` | - | 67307 |

### `api:me` (2 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/me` | GET | `api_me` | login_required | 28652 |
| `/api/me/permissions` | GET | `api_me_permissions` | login_required | 31066 |

### `api:message-log` (3 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/message-log` | GET | `api_message_log_list` | login_required | 72345 |
| `/api/message-log` | POST | `api_message_log_add` | login_required | 72354 |
| `/api/message-log/<int:lid>` | DELETE | `api_message_log_delete` | login_required | 72369 |

### `api:message-reminders` (3 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/message-reminders` | GET | `api_message_reminders_list` | login_required | 72380 |
| `/api/message-reminders` | POST | `api_message_reminders_add` | login_required | 72389 |
| `/api/message-reminders/<int:rid>` | DELETE | `api_message_reminders_delete` | login_required | 72413 |

### `api:message-templates` (3 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/message-templates` | GET | `api_message_templates_list` | login_required | 72311 |
| `/api/message-templates` | POST | `api_message_templates_add` | login_required | 72320 |
| `/api/message-templates/<int:tid>` | DELETE | `api_message_templates_delete` | login_required | 72337 |

### `api:messaging` (2 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/messaging/templates` | GET | `api_messaging_templates_get` | - | 35581 |
| `/api/messaging/templates` | PUT,PATCH | `api_messaging_templates_put` | - | 35958 |

### `api:monthly-evaluations` (12 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/monthly-evaluations` | POST | `api_mev_create` | login_required | 85699 |
| `/api/monthly-evaluations` | GET | `api_mev_list` | login_required | 85849 |
| `/api/monthly-evaluations/<int:eid>` | PATCH | `api_mev_update` | login_required | 85924 |
| `/api/monthly-evaluations/<int:eid>` | DELETE | `api_mev_delete` | login_required | 86024 |
| `/api/monthly-evaluations/<int:eid>/send-to-parent` | POST | `api_mev_send_to_parent` | login_required | 86153 |
| `/api/monthly-evaluations/admin-stats` | GET | `api_mev_admin_stats` | login_required | 86365 |
| `/api/monthly-evaluations/bulk-release` | POST | `api_mev_bulk_release` | login_required | 86051 |
| `/api/monthly-evaluations/export` | GET | `api_mev_export` | login_required | 86482 |
| `/api/monthly-evaluations/group-students` | GET | `api_mev_group_students` | login_required | 86458 |
| `/api/monthly-evaluations/preview-message/<int:eid>` | GET | `api_mev_preview_message` | login_required | 86131 |
| `/api/monthly-evaluations/stats/<int:sid>` | GET | `api_mev_student_trend` | login_required | 86333 |
| `/api/monthly-evaluations/teachers` | GET | `api_mev_teachers` | login_required | 86426 |

### `api:notifications` (3 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/notifications` | GET | `api_notifications_list` | login_required | 44324 |
| `/api/notifications/<int:nid>/read` | POST | `api_notifications_mark_read` | login_required | 44361 |
| `/api/notifications/unread-count` | GET | `api_notifications_unread_count` | login_required | 44394 |

### `api:parent` (12 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/parent/cart` | GET | `api_parent_cart_get_v2` | - | 104074 |
| `/api/parent/cart/<int:cid>` | DELETE | `api_parent_cart_remove_v2` | - | 104159 |
| `/api/parent/cart/<int:cid>/quantity` | PUT | `api_parent_cart_set_qty_v2` | - | 104101 |
| `/api/parent/cart/add` | POST | `api_parent_cart_add_v2` | - | 103991 |
| `/api/parent/cart/checkout` | POST | `api_parent_cart_checkout_v2` | - | 104204 |
| `/api/parent/hub-stats` | GET | `api_parent_hub_stats` | - | 29009 |
| `/api/parent/lookup` | POST | `api_parent_lookup` | - | 28834 |
| `/api/parent/order/cancel` | POST | `api_parent_order_cancel` | - | 104289 |
| `/api/parent/receipt-file/<int:rid>` | GET | `api_parent_receipt_file` | - | 31505 |
| `/api/parent/store/menu` | GET | `api_parent_store_menu` | - | 29269 |
| `/api/parent/store/request` | POST | `api_parent_store_request` | - | 29392 |
| `/api/parent/upload-receipt` | POST | `api_parent_upload_receipt` | - | 31261 |

### `api:parent-messages` (13 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/parent-messages` | POST | `api_parent_messages_create` | login_required | 84346 |
| `/api/parent-messages` | GET | `api_parent_messages_list` | login_required | 84552 |
| `/api/parent-messages/<int:mid>` | GET | `api_parent_messages_get_one` | login_required | 84646 |
| `/api/parent-messages/<int:mid>` | PATCH | `api_parent_messages_update` | login_required | 84683 |
| `/api/parent-messages/<int:mid>` | DELETE | `api_parent_messages_delete` | login_required | 84755 |
| `/api/parent-messages/<int:mid>/finalize` | POST | `api_parent_messages_finalize` | login_required | 84508 |
| `/api/parent-messages/<int:mid>/read` | POST | `api_parent_messages_mark_read` | login_required | 84824 |
| `/api/parent-messages/<int:mid>/resend` | POST | `api_parent_messages_resend` | login_required | 84792 |
| `/api/parent-messages/<int:mid>/send` | POST | `api_parent_messages_send` | login_required | 84468 |
| `/api/parent-messages/export` | GET | `api_parent_messages_export` | login_required | 84979 |
| `/api/parent-messages/parent-unread-count` | GET | `api_parent_messages_unread_count` | login_required | 84868 |
| `/api/parent-messages/stats` | GET | `api_parent_messages_stats` | login_required | 84906 |
| `/api/parent-messages/teachers` | GET | `api_parent_messages_teachers` | login_required | 84943 |

### `api:paylog-columns` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/paylog-columns` | GET | `api_paylog_columns_get` | - | 33601 |
| `/api/paylog-columns` | POST | `api_paylog_columns_add` | - | 33608 |
| `/api/paylog-columns/<col_key>` | DELETE | `api_paylog_columns_delete` | - | 33648 |
| `/api/paylog-columns/<col_key>` | PUT | `api_paylog_columns_update` | - | 33663 |

### `api:payment` (5 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/payment/due-reminders` | GET | `api_payment_due_reminders` | login_required | 72089 |
| `/api/payment/student/<int:sid>/edit` | POST | `api_payment_student_edit` | login_required | 71880 |
| `/api/payment/student/<int:sid>/installment/<int:n>` | GET | `api_payment_student_installment` | login_required | 71701 |
| `/api/payment/student/<int:sid>/pay` | POST | `api_payment_student_pay` | login_required | 71721 |
| `/api/payment/student/<int:sid>/plan` | GET | `api_payment_student_plan` | login_required | 71691 |

### `api:payment-log` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/payment-log` | GET | `api_payment_log_get` | login_required | 33551 |
| `/api/payment-log` | POST | `api_payment_log_add` | login_required | 33558 |
| `/api/payment-log/<int:rid>` | PUT | `api_payment_log_update` | login_required | 33573 |
| `/api/payment-log/<int:rid>` | DELETE | `api_payment_log_delete` | login_required | 33590 |

### `api:payment-messages` (2 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/payment-messages` | POST | `api_payment_messages_add` | login_required | 72016 |
| `/api/payment-messages` | GET | `api_payment_messages_list` | login_required | 72049 |

### `api:payment-reminders` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/payment-reminders` | GET | `api_payment_reminders` | login_required | 72225 |

### `api:payments` (2 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/payments/<int:student_id>/<int:inst_num>` | PUT | `api_payment_put` | login_required | 67494 |
| `/api/payments/group` | GET | `api_payments_group` | login_required | 70073 |

### `api:points` (37 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/points/admin-purchase` | POST | `api_pts_admin_purchase` | login_required | 39477 |
| `/api/points/avatars` | GET | `api_pts_avatars` | login_required | 38659 |
| `/api/points/behaviors` | GET | `api_pts_behaviors_list` | login_required | 37628 |
| `/api/points/behaviors` | POST | `api_pts_behaviors_create` | login_required | 37658 |
| `/api/points/behaviors/<int:bid>` | PATCH | `api_pts_behaviors_update` | login_required | 37693 |
| `/api/points/behaviors/<int:bid>` | DELETE | `api_pts_behaviors_delete` | login_required | 37736 |
| `/api/points/bulk-grant` | POST | `api_pts_bulk_grant` | login_required | 38057 |
| `/api/points/digest/next` | GET | `api_pts_digest_next` | login_required | 48136 |
| `/api/points/digest/run` | POST | `api_pts_digest_run` | login_required | 48117 |
| `/api/points/grant` | POST | `api_pts_grant` | login_required | 37765 |
| `/api/points/grant/<int:event_id>` | DELETE | `api_pts_undo_grant` | login_required | 38244 |
| `/api/points/group` | GET | `api_pts_group_board` | login_required | 38779 |
| `/api/points/group/<int:gid>/hatch-eggs` | POST | `api_pts_hatch_eggs` | login_required | 38687 |
| `/api/points/group/hatch-eggs` | POST | `api_pts_hatch_eggs` | login_required | 38688 |
| `/api/points/groups` | GET | `api_pts_visible_groups` | login_required | 38829 |
| `/api/points/history` | GET | `api_pts_history` | login_required | 39736 |
| `/api/points/levels` | GET | `api_pts_levels` | login_required | 48079 |
| `/api/points/notifications` | GET | `api_pts_notifications_list` | login_required | 48094 |
| `/api/points/notifications/<int:nid>/sent` | POST | `api_pts_notifications_mark_sent` | login_required | 49354 |
| `/api/points/redeem` | POST | `api_pts_redeem` | login_required | 39413 |
| `/api/points/redemptions` | GET | `api_pts_redemptions_list` | login_required | 39377 |
| `/api/points/redemptions/<int:redeem_id>/approve` | GET | `` | - | 39893 |
| `/api/points/redemptions/<int:redeem_id>/cancel` | POST | `api_pts_redeem_cancel` | login_required | 39856 |
| `/api/points/redemptions/<int:redeem_id>/deliver` | POST | `api_pts_redeem_deliver` | login_required | 39620 |
| `/api/points/redemptions/<int:redeem_id>/reject` | GET | `` | - | 39968 |
| `/api/points/redemptions/<int:redeem_id>/undeliver` | GET | `` | - | 39681 |
| `/api/points/reports/admin` | GET | `api_pts_report_admin` | login_required | 39077 |
| `/api/points/reports/group` | GET | `api_pts_report_group` | login_required | 39009 |
| `/api/points/reports/student/<int:sid>` | GET | `api_pts_report_student` | login_required | 38903 |
| `/api/points/rewards` | GET | `api_pts_rewards_list` | login_required | 39157 |
| `/api/points/rewards` | POST | `api_pts_rewards_create` | login_required | 39188 |
| `/api/points/rewards/<int:rid>` | PATCH | `api_pts_rewards_update` | login_required | 39248 |
| `/api/points/session-budget` | GET | `api_pts_session_budget` | login_required | 38009 |
| `/api/points/session-events` | GET | `api_pts_session_events` | login_required | 38324 |
| `/api/points/session-stats` | GET | `api_pts_session_stats` | login_required | 38412 |
| `/api/points/student/<int:sid>` | GET | `api_pts_student_summary` | login_required | 38540 |
| `/api/points/student/<int:sid>/avatar` | PATCH | `api_pts_set_avatar` | login_required | 38575 |

### `api:portal` (9 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/portal/change-password` | POST | `api_portal_change_pw` | login_required | 77927 |
| `/api/portal/parent/me` | GET | `api_portal_parent_me` | login_required | 79587 |
| `/api/portal/parent/notify-pref` | POST | `api_portal_parent_notify_pref` | login_required | 79678 |
| `/api/portal/student/attendance` | GET | `api_portal_student_attendance` | login_required | 78246 |
| `/api/portal/student/me` | GET | `api_portal_student_me` | login_required | 78044 |
| `/api/portal/student/meta` | GET | `api_portal_student_meta` | login_required | 78171 |
| `/api/portal/student/payments` | GET | `api_portal_student_payments` | login_required | 78185 |
| `/api/portal/student/redeem` | POST | `api_portal_student_redeem` | login_required | 79700 |
| `/api/portal/student/redemptions` | GET | `api_portal_student_redemptions` | login_required | 78105 |

### `api:push` (3 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/push/subscribe` | POST | `api_push_subscribe` | - | 104537 |
| `/api/push/unsubscribe` | POST | `api_push_unsubscribe` | - | 104935 |
| `/api/push/vapid-public-key` | GET | `api_push_vapid_public_key` | - | 104503 |

### `api:receipts` (6 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/receipts` | GET | `api_receipts_list` | login_required | 32995 |
| `/api/receipts/<path:receipt_number>/cancel` | POST | `api_receipts_cancel` | login_required | 32744 |
| `/api/receipts/<path:receipt_number>/finalize` | POST | `api_receipts_finalize` | login_required | 32700 |
| `/api/receipts/issue` | POST | `api_receipts_issue` | login_required | 32945 |
| `/api/receipts/reserve` | POST | `api_receipts_reserve` | login_required | 32647 |
| `/api/receipts/student/<int:sid>` | GET | `api_receipts_student` | login_required | 32463 |

### `api:recurring-tasks` (5 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/recurring-tasks` | POST | `api_recurring_tasks_create` | login_required | 44990 |
| `/api/recurring-tasks` | GET | `api_recurring_tasks_list` | login_required | 45077 |
| `/api/recurring-tasks/<int:rid>` | PATCH | `api_recurring_tasks_update` | login_required | 45104 |
| `/api/recurring-tasks/<int:rid>` | DELETE | `api_recurring_tasks_delete` | login_required | 45193 |
| `/api/recurring-tasks/run-scheduler` | POST | `api_recurring_run_scheduler` | login_required | 45276 |

### `api:rewards` (3 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/rewards/<int:rid>/image` | GET | `api_rewards_image` | - | 39338 |
| `/api/rewards/<int:rid>/stock-history` | GET | `api_rewards_stock_history` | login_required | 41058 |
| `/api/rewards/stock-history/counts` | GET | `api_rewards_stock_history_counts` | login_required | 41033 |

### `api:session-durations` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/session-durations` | POST | `api_session_durations_save` | login_required | 69946 |

### `api:session-summary` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/session-summary` | GET | `api_session_summary` | login_required | 69975 |

### `api:settings` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/settings` | GET | `api_settings_get` | - | 35489 |
| `/api/settings` | PATCH | `api_settings_patch` | - | 35513 |
| `/api/settings/columns/<table_name>` | GET | `api_settings_columns` | - | 36317 |
| `/api/settings/tables` | GET | `api_settings_tables` | - | 36309 |

### `api:student` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/student/<sid>/payment-details` | GET | `api_student_payment_details` | login_required | 33253 |

### `api:students` (6 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/students` | GET | `api_students_get` | login_required | 32173 |
| `/api/students` | POST | `api_students_add` | login_required | 32262 |
| `/api/students/<int:sid>` | PUT,PATCH | `api_students_update` | login_required | 32346 |
| `/api/students/<int:sid>` | DELETE | `api_students_delete` | login_required | 32428 |
| `/api/students/<int:sid>/details` | GET | `api_student_details` | login_required | 33015 |
| `/api/students/bulk` | POST | `api_students_bulk` | login_required | 33305 |

### `api:table` (2 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/table/<table_name>/linked-options` | GET | `api_linked_options` | login_required | 35996 |
| `/api/table/<tid>/schema` | GET | `api_table_schema` | login_required | 36436 |

### `api:taqseet` (4 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/taqseet` | GET | `api_taqseet_get` | login_required | 67407 |
| `/api/taqseet` | POST | `api_taqseet_post` | login_required | 67417 |
| `/api/taqseet/<int:row_id>` | PUT | `api_taqseet_put` | login_required | 67453 |
| `/api/taqseet/<int:row_id>` | DELETE | `api_taqseet_delete` | login_required | 67480 |

### `api:taqseet-labels` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/taqseet-labels` | GET | `api_taqseet_labels_get` | login_required | 67488 |

### `api:tasks` (18 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/tasks` | POST | `api_tasks_create` | login_required | 43257 |
| `/api/tasks` | GET | `api_tasks_list` | login_required | 43384 |
| `/api/tasks/<int:tid>` | PATCH | `api_tasks_update` | login_required | 43644 |
| `/api/tasks/<int:tid>` | GET | `api_tasks_detail` | login_required | 43819 |
| `/api/tasks/<int:tid>/attachments` | POST | `api_tasks_attachment_upload` | login_required | 44034 |
| `/api/tasks/<int:tid>/attachments` | GET | `api_tasks_attachments_list` | login_required | 44093 |
| `/api/tasks/<int:tid>/attachments/<int:aid>` | GET | `api_tasks_attachment_serve` | login_required | 44119 |
| `/api/tasks/<int:tid>/attachments/<int:aid>` | DELETE | `api_tasks_attachment_delete` | login_required | 45614 |
| `/api/tasks/<int:tid>/comments` | POST | `api_tasks_comment_create` | login_required | 43914 |
| `/api/tasks/<int:tid>/comments` | GET | `api_tasks_comments_list` | login_required | 45686 |
| `/api/tasks/<int:tid>/comments/<int:cid>` | DELETE | `api_tasks_comment_delete` | login_required | 45651 |
| `/api/tasks/<int:tid>/evaluate` | POST | `api_tasks_evaluate` | login_required | 44224 |
| `/api/tasks/<int:tid>/evaluation` | GET | `api_tasks_evaluation_get` | login_required | 45484 |
| `/api/tasks/<int:tid>/evaluation` | PATCH | `api_tasks_evaluation_update` | login_required | 45511 |
| `/api/tasks/<int:tid>/status` | POST | `api_tasks_status` | login_required | 43551 |
| `/api/tasks/dashboard/admin` | GET | `api_tasks_dashboard_admin` | login_required | 44415 |
| `/api/tasks/dashboard/personal` | GET | `api_tasks_dashboard_personal` | login_required | 44708 |
| `/api/tasks/dashboard/team` | GET | `api_tasks_dashboard_team` | login_required | 44642 |

### `api:teacher` (6 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/teacher/attendance` | POST | `api_teacher_attendance_save` | login_required | 64460 |
| `/api/teacher/attendance/check` | GET | `api_teacher_attendance_check` | login_required | 64436 |
| `/api/teacher/evaluations/student-history/<int:student_id>` | GET | `` | - | 86244 |
| `/api/teacher/groups` | GET | `api_teacher_groups` | login_required | 64278 |
| `/api/teacher/groups-diag` | GET | `api_teacher_groups_diag` | - | 64243 |
| `/api/teacher/students` | GET | `api_teacher_students` | login_required | 64377 |

### `api:teacher-deliveries` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/teacher-deliveries/summary` | GET | `api_teacher_deliveries_summary` | login_required | 64017 |

### `api:users` (1 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/users/assignable` | GET | `api_users_assignable` | login_required | 48034 |

### `api:vars` (3 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/vars/columns` | GET | `api_vars_columns` | - | 35901 |
| `/api/vars/render-batch` | POST | `api_vars_render_batch` | - | 35924 |
| `/api/vars/tables` | GET | `api_vars_tables` | - | 35869 |

### `api:violations-action-templates` (3 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/violations-action-templates` | GET | `api_violations_action_templates_list` | login_required | 63551 |
| `/api/violations-action-templates` | POST | `api_violations_action_templates_create` | login_required | 63632 |
| `/api/violations-action-templates/<int:tid>` | DELETE | `api_violations_action_templates_delete` | login_required | 63689 |

### `api:violations-catalog` (9 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/violations-catalog` | GET | `api_violations_catalog_list` | login_required | 62946 |
| `/api/violations-catalog` | POST | `api_violations_catalog_create` | login_required | 63370 |
| `/api/violations-catalog/<int:cid>` | GET | `api_violations_catalog_get` | login_required | 63003 |
| `/api/violations-catalog/<int:cid>` | PATCH | `api_violations_catalog_patch` | login_required | 63424 |
| `/api/violations-catalog/<int:cid>` | DELETE | `api_violations_catalog_delete` | login_required | 63467 |
| `/api/violations-catalog/<int:cid>/increment-use` | GET | `` | - | 63527 |
| `/api/violations-catalog/<int:cid>/suggestion` | GET | `api_violations_catalog_suggestion` | login_required | 63089 |
| `/api/violations-catalog/<int:cid>/toggle-quick-pick` | GET | `` | - | 63492 |
| `/api/violations-catalog/quick-picks` | GET | `api_violations_catalog_quick_picks` | login_required | 62986 |

### `api:violations-escalation-rules` (3 routes)

| URL | Methods | Handler | Auth | Line |
|---|---|---|---|---|
| `/api/violations-escalation-rules` | GET | `api_violations_escalation_rules_get` | login_required | 63221 |
| `/api/violations-escalation-rules` | PUT | `api_violations_escalation_rules_put` | login_required | 63229 |
| `/api/violations-escalation-rules/preview` | GET | `api_violations_escalation_rules_preview` | login_required | 63270 |

---

## How to use this file

- **Read** before any code change touching shared code, routes, or templates.
- **Search** by feature name, URL, or handler -- every route is here.
- **Update** when a new route ships: append it to the relevant category section. The bootstrap script can be re-run to produce a diff, but do NOT overwrite manual top-20 annotations.
- **Annotate** when a feature gains a regression-worthy invariant -- add it to the top-20 with an explicit assertion sentence.
- **Verify** the Last verified date below before trusting the file as up-to-date.

**Last verified:** 2026-05-15 (bootstrap).
