from flask import Flask, request, session, redirect, g, jsonify, Response
import sqlite3, hashlib, os, json, re as _re
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mindx2026secret")
DB = os.environ.get("DB_PATH", "mindx.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg2
    import psycopg2.extras


class _Row(dict):
    """Row type that supports r[int], r['name'], dict(r), and r.keys() — compatible with sqlite3.Row usage throughout the app."""
    def __init__(self, values, columns):
        super().__init__(zip(columns, values))
        object.__setattr__(self, '_columns', columns)

    def __getitem__(self, key):
        if isinstance(key, int):
            return dict.__getitem__(self, self._columns[key])
        return dict.__getitem__(self, key)

    def keys(self):
        return list(self._columns)


class _StaticCursor:
    """Canned-rows cursor used to emulate SELECT last_insert_rowid()."""
    def __init__(self, rows):
        self._rows = list(rows)
        self.rowcount = len(rows)

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        out, self._rows = self._rows, []
        return out

    def close(self):
        pass


class _PgCursor:
    def __init__(self, cur):
        self._cur = cur
        self._cols = None

    def _columns(self):
        if self._cols is None and self._cur.description:
            self._cols = [d[0] for d in self._cur.description]
        return self._cols or []

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        return _Row(row, self._columns())

    def fetchall(self):
        rows = self._cur.fetchall()
        cols = self._columns()
        return [_Row(r, cols) for r in rows]

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass


def _pg_translate(sql):
    """Rewrite SQLite dialect to Postgres dialect."""
    m = _re.search(r"PRAGMA\s+table_info\s*\(\s*(\w+)\s*\)", sql, _re.I)
    if m:
        tbl = m.group(1).lower()
        return (
            "SELECT (ordinal_position - 1) AS cid, column_name AS name, "
            "data_type AS type, "
            "CASE WHEN is_nullable='NO' THEN 1 ELSE 0 END AS notnull, "
            "column_default AS dflt_value, 0 AS pk "
            "FROM information_schema.columns WHERE table_name = '" + tbl + "' "
            "ORDER BY ordinal_position"
        )
    sql = _re.sub(r"\bINTEGER\s+PRIMARY\s+KEY(\s+AUTOINCREMENT)?\b", "SERIAL PRIMARY KEY", sql, flags=_re.I)
    sql = sql.replace("datetime('now')", "NOW()::text")
    sql = _re.sub(r"\bDATETIME\b", "TIMESTAMP", sql)
    if _re.search(r"\bINSERT\s+OR\s+IGNORE\b", sql, _re.I):
        sql = _re.sub(r"\bINSERT\s+OR\s+IGNORE\b", "INSERT", sql, flags=_re.I)
        sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    sql = sql.replace("?", "%s")
    return sql


class _PgConnection:
    """Sqlite3.Connection-shaped wrapper over psycopg2."""
    def __init__(self, conn):
        self._conn = conn
        self._conn.autocommit = True  # Match SQLite's implicit-commit flow; avoids aborted-transaction pitfalls with try/except swallows.
        self._last_insert_id = None
        self.row_factory = None  # Unused; present for API compatibility.

    def execute(self, sql, params=()):
        if _re.search(r"\blast_insert_rowid\s*\(", sql, _re.I):
            return _StaticCursor([_Row([self._last_insert_id], ["last_insert_rowid"])])
        translated = _pg_translate(sql)
        is_insert = bool(_re.match(r"\s*INSERT\s+INTO\s", translated, _re.I))
        if is_insert and "RETURNING" not in translated.upper():
            translated = translated.rstrip().rstrip(";") + " RETURNING id"
        cur = self._conn.cursor()
        if params:
            cur.execute(translated, tuple(params))
        else:
            cur.execute(translated)
        if is_insert:
            try:
                row = cur.fetchone()
                if row is not None:
                    self._last_insert_id = row[0]
            except Exception:
                pass
        return _PgCursor(cur)

    def commit(self):
        pass  # autocommit mode

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def _new_connection():
    if USE_PG:
        return _PgConnection(psycopg2.connect(DATABASE_URL))
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    if "db" not in g:
        g.db = _new_connection()
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db:
        db.close()

def hp(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    db = _new_connection()
    db.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        name TEXT,
        role TEXT,
        department TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id TEXT UNIQUE,
        student_name TEXT,
        whatsapp TEXT,
        class_name TEXT,
        old_new_2026 TEXT,
        registration_term2_2026 TEXT,
        group_name_student TEXT,
        group_online TEXT,
        final_result TEXT,
        level_reached_2026 TEXT,
        suitable_level_2026 TEXT,
        books_received TEXT,
        teacher_2026 TEXT,
        installment1 TEXT,
        installment2 TEXT,
        installment3 TEXT,
        installment4 TEXT,
        installment5 TEXT,
        mother_phone TEXT,
        father_phone TEXT,
        other_phone TEXT,
        residence TEXT,
        home_address TEXT,
        road TEXT,
        complex_name TEXT,
        installment_type TEXT DEFAULT '',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    db.execute("""CREATE TABLE IF NOT EXISTS student_groups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        teacher_name TEXT,
        level_course TEXT,
        last_reached TEXT,
        study_time TEXT,
        study_days TEXT,
        ramadan_time TEXT,
        online_time TEXT,
        group_link TEXT,
        session_duration TEXT,
        session_minutes_normal TEXT,
        hours_in_person_auto TEXT,
        hours_online_only TEXT,
        hours_all_online TEXT,
        total_required_hours TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    db.execute("""CREATE TABLE IF NOT EXISTS column_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    db.execute("""CREATE TABLE IF NOT EXISTS group_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")

    db.execute("""CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attendance_date TEXT,
        day_name TEXT,
        group_name TEXT,
        student_name TEXT,
        contact_number TEXT,
        status TEXT,
        message TEXT,
        message_status TEXT,
        study_status TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS att_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    db.execute("""CREATE TABLE IF NOT EXISTS custom_tables(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tbl_name TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now')))""")
    db.execute("""CREATE TABLE IF NOT EXISTS custom_table_cols(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER,
        col_key TEXT,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    db.execute("""CREATE TABLE IF NOT EXISTS custom_table_rows(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER,
        row_data TEXT DEFAULT '{}')""")
    users = [
        ("admin","admin123","admin"),
        ("reception","rec123","reception"),
        ("teacher1","tea123","teacher"),
        ("teacher2","tea456","teacher"),
    ]
    for u, p, r in users:
        try:
            db.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)", (u, hp(p), r))
        except:
            pass
        db.execute("""CREATE TABLE IF NOT EXISTS taqseet(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        taqseet_method TEXT DEFAULT '',
        student_name TEXT DEFAULT '',
        course_amount TEXT DEFAULT '',
        num_installments TEXT DEFAULT '',
        inst1 TEXT DEFAULT '', paid1 TEXT DEFAULT '', date1 TEXT DEFAULT '',
        inst2 TEXT DEFAULT '', paid2 TEXT DEFAULT '', date2 TEXT DEFAULT '',
        inst3 TEXT DEFAULT '', paid3 TEXT DEFAULT '', date3 TEXT DEFAULT '',
        inst4 TEXT DEFAULT '', paid4 TEXT DEFAULT '', date4 TEXT DEFAULT '',
        inst5 TEXT DEFAULT '', paid5 TEXT DEFAULT '', date5 TEXT DEFAULT '',
        inst6 TEXT DEFAULT '', paid6 TEXT DEFAULT '', date6 TEXT DEFAULT '',
        inst7 TEXT DEFAULT '', paid7 TEXT DEFAULT '', date7 TEXT DEFAULT '',
        inst8 TEXT DEFAULT '', paid8 TEXT DEFAULT '', date8 TEXT DEFAULT '',
        inst9 TEXT DEFAULT '', paid9 TEXT DEFAULT '', date9 TEXT DEFAULT '',
        inst10 TEXT DEFAULT '', paid10 TEXT DEFAULT '', date10 TEXT DEFAULT '',
        inst11 TEXT DEFAULT '', paid11 TEXT DEFAULT '', date11 TEXT DEFAULT '',
        inst12 TEXT DEFAULT '', paid12 TEXT DEFAULT '', date12 TEXT DEFAULT '',
        study_hours TEXT DEFAULT '',
        start_date TEXT DEFAULT ''
    )""")
    # Add 10 default rows to taqseet if empty
    if db.execute("SELECT COUNT(*) FROM taqseet").fetchone()[0] == 0:
        for i in range(1, 11):
            db.execute("INSERT INTO taqseet (taqseet_method) VALUES (?)", (str(i),))
        db.commit()
    db.execute("""CREATE TABLE IF NOT EXISTS student_payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        inst_num INTEGER,
        inst_type TEXT DEFAULT '',
        price REAL DEFAULT 0,
        paid REAL DEFAULT 0,
        UNIQUE(student_id, inst_num)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS session_durations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        session_date TEXT,
        duration_minutes INTEGER DEFAULT 0,
        session_type TEXT DEFAULT '',
        UNIQUE(group_name, session_date)
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS message_templates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS message_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        student_whatsapp TEXT,
        template_name TEXT,
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS message_reminders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        day_of_week INTEGER,
        time_of_day TEXT,
        template_id INTEGER,
        group_name TEXT,
        enabled INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS taqseet_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    db.execute("""CREATE TABLE IF NOT EXISTS evaluations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_fill_date TEXT,
        group_name TEXT,
        student_name TEXT,
        class_participation TEXT,
        general_behavior TEXT,
        behavior_notes TEXT,
        reading TEXT,
        dictation TEXT,
        term_meanings TEXT,
        conversation TEXT,
        expression TEXT,
        grammar TEXT,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS eval_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    db.execute("""CREATE TABLE IF NOT EXISTS payment_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        personal_id TEXT,
        registration_status TEXT,
        course_amount TEXT,
        inst1 TEXT, msg1 TEXT,
        inst2 TEXT, msg2 TEXT,
        inst3 TEXT, msg3 TEXT,
        inst4 TEXT, msg4 TEXT,
        inst5 TEXT, msg5 TEXT,
        total_paid TEXT,
        total_remaining TEXT,
        payment_status TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS table_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tbl_name TEXT UNIQUE,
        tbl_label TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS paylog_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    # Seed built-in Arabic table labels on a fresh DB.
    for _tn, _tl in [
        ("students",         "قاعدة بيانات الطلبة"),
        ("student_groups",   "المجموعات"),
        ("attendance",       "سجل الغياب"),
        ("taqseet",          "جدول التقسيط"),
        ("evaluations",      "التقييمات"),
        ("payment_log",      "سجل الدفع"),
        ("student_payments", "دفعات الطلبة"),
        ("session_durations","مدة الحصص"),
        ("message_templates","قوالب الرسائل"),
        ("message_log",      "سجل الرسائل"),
        ("message_reminders","تذكيرات الرسائل"),
        ("users",            "المستخدمون"),
        ("settings",         "الإعدادات"),
    ]:
        try:
            db.execute("INSERT INTO table_labels(tbl_name, tbl_label) VALUES(?,?)", (_tn, _tl))
        except Exception:
            pass
    db.execute("""CREATE TABLE IF NOT EXISTS settings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page TEXT NOT NULL,
        component TEXT NOT NULL,
        label TEXT NOT NULL,
        value TEXT DEFAULT '',
        value_type TEXT DEFAULT 'table_column',
        UNIQUE(page, component)
    )""")
    # Seed default settings only if table is empty.
    try:
        if db.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'groups_table', 'جدول المجموعات', 'student_groups'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'groups_column', 'عمود اسم المجموعة', 'group_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'students_table', 'جدول الطلاب', 'students'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'student_name_column', 'عمود اسم الطالب', 'student_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'student_phone_column', 'عمود رقم الواتساب', 'whatsapp'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'groups_table', 'جدول المجموعات', 'student_groups'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'groups_column', 'عمود المجموعة', 'group_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'students_table', 'جدول الطلاب', 'students'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'name_column', 'عمود الاسم', 'student_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'phone_column', 'عمود الواتساب', 'whatsapp'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'table', 'جدول الدفع', 'taqseet'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'name_column', 'عمود الاسم', 'student_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'amount_column', 'عمود المبلغ', 'course_amount'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'groups_table', 'جدول المجموعات', 'student_groups'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'groups_column', 'عمود المجموعة', 'group_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('students', 'active_column', 'عمود حالة النشاط', 'registration_term2_2026'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('students', 'active_value',  'قيمة الطالب النشط', 'تم التسجيل'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('dashboard', 'students_table', 'جدول الطلاب', 'students'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('dashboard', 'groups_table', 'جدول المجموعات', 'student_groups'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('dashboard', 'attendance_table', 'جدول الغياب', 'attendance'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('dashboard', 'payment_table', 'جدول الدفع', 'taqseet'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('database', 'visible_tables', 'الجداول الظاهرة', 'all'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('groups', 'table', 'جدول المجموعات', 'student_groups'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('groups', 'name_column', 'عمود اسم المجموعة', 'group_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'attendance_table', 'جدول الغياب', 'attendance'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'student_group_column', 'عمود مجموعة الطالب', 'group_name_student'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'date_column', 'عمود التاريخ', 'attendance_date'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'day_column', 'عمود اليوم', 'day_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'status_column', 'عمود الحالة', 'status'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'message_column', 'عمود الرسالة', 'message'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'message_status_column', 'عمود حالة الرسالة', 'message_status'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('attendance', 'study_status_column', 'عمود حالة الدراسة', 'study_status'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'templates_table', 'جدول قوالب الرسائل', 'message_templates'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'templates_name_column', 'عمود اسم القالب', 'name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'templates_category_column', 'عمود تصنيف القالب', 'category'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'templates_content_column', 'عمود نص القالب', 'content'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'log_table', 'جدول سجل الرسائل', 'message_log'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'log_student_column', 'عمود الطالب في السجل', 'student_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'log_whatsapp_column', 'عمود واتساب السجل', 'student_whatsapp'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'log_template_column', 'عمود قالب السجل', 'template_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'reminders_table', 'جدول التذكيرات', 'message_reminders'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('messaging', 'student_id_column', 'عمود الرقم الشخصي', 'personal_id'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'students_table', 'جدول الطلاب للدفع', 'students'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'student_name_column', 'عمود اسم الطالب', 'student_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'installment_type_column', 'عمود نوع التقسيط', 'installment_type'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'taqseet_method_column', 'عمود طريقة التقسيط', 'taqseet_method'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'paid_amount_column', 'عمود المبلغ المدفوع', 'paid'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'payments_table', 'جدول المدفوعات', 'student_payments'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('payment', 'num_installments_column', 'عمود عدد الأقساط', 'num_installments'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('dashboard', 'students_class_column', 'عمود صف الطالب', 'class_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('dashboard', 'students_result_column', 'عمود نتيجة الطالب', 'final_result'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('dashboard', 'students_teacher_column', 'عمود مدرس الطالب', 'teacher_2026'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('dashboard', 'students_subject_column', 'عمود مادة الطالب', 'class_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('dashboard', 'attendance_status_column', 'عمود حالة الغياب', 'status'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('groups', 'teacher_column', 'عمود اسم المدرس', 'teacher_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('groups', 'level_column', 'عمود المستوى', 'level_course'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('groups', 'study_time_column', 'عمود وقت الدراسة', 'study_time'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('groups', 'link_column', 'عمود رابط المجموعة', 'group_link'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('evaluations', 'table', 'جدول التقييمات', 'evaluations'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('evaluations', 'student_name_column', 'عمود اسم الطالب', 'student_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('evaluations', 'group_column', 'عمود المجموعة', 'group_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('evaluations', 'date_column', 'عمود تاريخ التقييم', 'form_fill_date'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('evaluations', 'reading_column', 'عمود القراءة', 'reading'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('evaluations', 'dictation_column', 'عمود الإملاء', 'dictation'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('evaluations', 'conversation_column', 'عمود المحادثة', 'conversation'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('evaluations', 'expression_column', 'عمود التعبير', 'expression'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('evaluations', 'grammar_column', 'عمود القواعد', 'grammar'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('paylog', 'table', 'جدول سجل الدفع', 'payment_log'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('paylog', 'student_name_column', 'عمود اسم الطالب', 'student_name'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('paylog', 'personal_id_column', 'عمود الرقم', 'personal_id'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('paylog', 'course_amount_column', 'عمود مبلغ الدورة', 'course_amount'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('paylog', 'total_paid_column', 'عمود المدفوع', 'total_paid'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('paylog', 'total_remaining_column', 'عمود المتبقي', 'total_remaining'))
            db.execute("INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)", ('paylog', 'status_column', 'عمود حالة الدفع', 'payment_status'))
    except Exception:
        pass
    db.commit()
    db.close()

init_db()
if True:
    db2 = _new_connection()
    db2.execute("""CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        personal_id TEXT UNIQUE,
        student_name TEXT,
        whatsapp TEXT,
        class_name TEXT,
        old_new_2026 TEXT,
        registration_term2_2026 TEXT,
        group_name_student TEXT,
        group_online TEXT,
        final_result TEXT,
        level_reached_2026 TEXT,
        suitable_level_2026 TEXT,
        books_received TEXT,
        teacher_2026 TEXT,
        installment1 TEXT,
        installment2 TEXT,
        installment3 TEXT,
        installment4 TEXT,
        installment5 TEXT,
        mother_phone TEXT,
        father_phone TEXT,
        other_phone TEXT,
        residence TEXT,
        home_address TEXT,
        road TEXT,
        complex_name TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    db2.execute("""CREATE TABLE IF NOT EXISTS student_groups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        teacher_name TEXT,
        level_course TEXT,
        last_reached TEXT,
        study_time TEXT,
        study_days TEXT,
        ramadan_time TEXT,
        online_time TEXT,
        group_link TEXT,
        session_duration TEXT,
        session_minutes_normal TEXT,
        hours_in_person_auto TEXT,
        hours_online_only TEXT,
        hours_all_online TEXT,
        total_required_hours TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    
    db2.execute("""CREATE TABLE IF NOT EXISTS column_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    db2.execute("""CREATE TABLE IF NOT EXISTS group_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    # Seed default column labels if empty
    if db2.execute("SELECT COUNT(*) FROM column_labels").fetchone()[0] == 0:
        default_cols = [
            ("personal_id","&#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A;",1),("student_name","&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;",2),("whatsapp","&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x648;&#x627;&#x62A;&#x633;&#x627;&#x628; &#x627;&#x644;&#x645;&#x639;&#x62A;&#x645;&#x62F;",3),
            ("class_name","&#x627;&#x644;&#x635;&#x641;",4),("old_new_2026","&#x642;&#x62F;&#x64A;&#x645; &#x62C;&#x62F;&#x64A;&#x62F; 2026",5),("registration_term2_2026","&#x62A;&#x633;&#x62C;&#x64A;&#x644; &#x627;&#x644;&#x641;&#x635;&#x644; &#x627;&#x644;&#x62B;&#x627;&#x646;&#x64A; 2026",6),
            ("group_name_student","&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;",7),("group_online","&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; (&#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646;)",8),("final_result","&#x627;&#x644;&#x646;&#x62A;&#x64A;&#x62C;&#x629; &#x627;&#x644;&#x646;&#x647;&#x627;&#x626;&#x64A;&#x629; (&#x62A;&#x62D;&#x62F;&#x64A;&#x62F; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 2026)",9),
            ("level_reached_2026","&#x627;&#x644;&#x649; &#x627;&#x64A;&#x646; &#x648;&#x635;&#x644; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; 2026",10),("suitable_level_2026","&#x647;&#x644; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x645;&#x646;&#x627;&#x633;&#x628; &#x644;&#x647;&#x630;&#x627; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 2026&#x61F;",11),
            ("books_received","&#x627;&#x633;&#x62A;&#x644;&#x627;&#x645; &#x627;&#x644;&#x643;&#x62A;&#x628;",12),("teacher_2026","&#x627;&#x644;&#x645;&#x62F;&#x631;&#x633; 2026",13),
            ("installment1","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x627;&#x648;&#x644; 2026",14),("installment2","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62B;&#x627;&#x646;&#x64A;",15),("installment3","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62B;&#x627;&#x644;&#x62B;",16),
            ("installment4","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x631;&#x627;&#x628;&#x639;",17),("installment5","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62E;&#x627;&#x645;&#x633;",18),
            ("mother_phone","&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x645;",19),("father_phone","&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x628;",20),("other_phone","&#x647;&#x627;&#x62A;&#x641; &#x627;&#x62E;&#x631;",21),
            ("residence","&#x645;&#x643;&#x627;&#x646; &#x627;&#x644;&#x633;&#x643;&#x646;",22),("home_address","&#x639;&#x646;&#x648;&#x627;&#x646; &#x627;&#x644;&#x645;&#x646;&#x632;&#x644;",23),("road","&#x627;&#x644;&#x637;&#x631;&#x64A;&#x642;",24),("complex_name","&#x627;&#x644;&#x645;&#x62C;&#x645;&#x639;",25),
            ("installment_type","&#x627;&#x62E;&#x62A;&#x64A;&#x627;&#x631; &#x646;&#x648;&#x639; &#x627;&#x644;&#x62A;&#x642;&#x633;&#x64A;&#x637;",26),
        ]
        for key,label,order in default_cols:
            try:
                db2.execute("INSERT INTO column_labels(col_key,col_label,col_order) VALUES(?,?,?)",(key,label,order))
            except: pass

    # Add new columns if they don't exist yet
    new_cols = [
        ("class_name", "TEXT"),
        ("old_new_2026", "TEXT"),
        ("registration_term2_2026", "TEXT"),
        ("group_name_student", "TEXT"),
        ("group_online", "TEXT"),
        ("final_result", "TEXT"),
        ("suitable_level_2026", "TEXT"),
        ("books_received", "TEXT"),
        ("installment1", "TEXT"),
        ("installment2", "TEXT"),
        ("installment3", "TEXT"),
        ("installment4", "TEXT"),
        ("installment5", "TEXT"),
        ("installment_type", "TEXT"),
    ]
    existing = [row[1] for row in db2.execute("PRAGMA table_info(students)").fetchall()]
    for col, coltype in new_cols:
        if col not in existing:
            db2.execute("ALTER TABLE students ADD COLUMN " + col + " " + coltype)
    new_group_cols = [
        ("session_minutes_normal", "TEXT"),
        ("hours_in_person_auto", "TEXT"),
        ("hours_online_only", "TEXT"),
        ("hours_all_online", "TEXT"),
        ("total_required_hours", "TEXT"),
        ("study_days", "TEXT"),
    ]
    group_existing = [row[1] for row in db2.execute("PRAGMA table_info(student_groups)").fetchall()]
    for col, coltype in new_group_cols:
        if col not in group_existing:
            db2.execute("ALTER TABLE student_groups ADD COLUMN " + col + " " + coltype)
    # One-time cleanup: drop obsolete columns that were added in earlier deploys.
    drop_group_cols = [
        "student_count","online_days","online_time_ramadan",
        "sessions_total_auto","sessions_nonramadan_auto","sessions_ramadan_auto","sessions_online_auto",
    ]
    group_existing = [row[1] for row in db2.execute("PRAGMA table_info(student_groups)").fetchall()]
    for col in drop_group_cols:
        if col in group_existing:
            try:
                db2.execute('ALTER TABLE student_groups DROP COLUMN "' + col + '"')
            except Exception:
                pass
        try:
            db2.execute("DELETE FROM group_col_labels WHERE col_key=?", (col,))
        except Exception:
            pass
    db2.commit()
    # Seed the default group_col_labels ONCE per DB, via a migration marker row.
    # Never re-seed on later requests — that used to resurrect columns the user
    # had just deleted through the UI.
    db2.execute("CREATE TABLE IF NOT EXISTS schema_migrations(tag TEXT PRIMARY KEY, applied_at DATETIME DEFAULT CURRENT_TIMESTAMP)")
    applied = set(r[0] for r in db2.execute("SELECT tag FROM schema_migrations").fetchall())
    # Add session_type column to session_durations on existing DBs.
    sd_cols = [row[1] for row in db2.execute("PRAGMA table_info(session_durations)").fetchall()]
    if "session_type" not in sd_cols:
        try:
            db2.execute("ALTER TABLE session_durations ADD COLUMN session_type TEXT DEFAULT ''")
        except Exception:
            pass
        db2.commit()
    # Add the "total_required_hours" group label row once.
    if "group_labels_v3" not in applied:
        try:
            db2.execute(
                "INSERT INTO group_col_labels(col_key,col_label,col_order) VALUES(?,?,?)",
                ("total_required_hours",
                 "&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x62D;&#x642;&#x629;",
                 14)
            )
        except Exception:
            pass
        try:
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("group_labels_v3",))
        except Exception:
            pass
        db2.commit()
    if "group_labels_v2" not in applied:
        seed_group_labels = [
            ("group_name","&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;",1),
            ("teacher_name","&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;",2),
            ("level_course","&#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; / &#x627;&#x644;&#x645;&#x642;&#x631;&#x631;",3),
            ("last_reached","&#x627;&#x644;&#x645;&#x642;&#x631;&#x631; &#x627;&#x644;&#x630;&#x64A; &#x62A;&#x645; &#x627;&#x644;&#x648;&#x635;&#x648;&#x644; &#x627;&#x644;&#x64A;&#x647; &#x627;&#x644;&#x641;&#x635;&#x644; &#x627;&#x644;&#x641;&#x627;&#x626;&#x62A;",4),
            ("study_time","&#x648;&#x642;&#x62A; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;",5),
            ("ramadan_time","&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x634;&#x647;&#x631; &#x631;&#x645;&#x636;&#x627;&#x646;",6),
            ("online_time","&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646; (&#x627;&#x644;&#x639;&#x627;&#x62F;&#x64A;)",7),
            ("group_link","&#x631;&#x627;&#x628;&#x637; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;",8),
            ("session_duration","&#x627;&#x644;&#x62D;&#x635;&#x629; &#x628;&#x627;&#x644;&#x62F;&#x642;&#x64A;&#x642;&#x629; (&#x64A;&#x62F;&#x648;&#x64A;)",9),
            ("session_minutes_normal","&#x645;&#x62F;&#x629; &#x627;&#x644;&#x62D;&#x635;&#x629; &#x628;&#x627;&#x644;&#x62F;&#x642;&#x64A;&#x642;&#x629; &#x644;&#x644;&#x648;&#x642;&#x62A; &#x627;&#x644;&#x627;&#x639;&#x62A;&#x64A;&#x627;&#x62F;&#x64A; (&#x64A;&#x62F;&#x648;&#x64A;)",10),
            ("hours_in_person_auto","&#x639;&#x62F;&#x62F; &#x627;&#x644;&#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x62D;&#x636;&#x648;&#x631;&#x64A;&#x629; (&#x62A;&#x644;&#x642;&#x627;&#x626;&#x64A;)",11),
            ("hours_online_only","&#x639;&#x62F;&#x62F; &#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646; &#x641;&#x642;&#x637;",12),
            ("hours_all_online","&#x627;&#x644;&#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x64A;&#x629; &#x643;&#x644;&#x647;&#x627; &#x628;&#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646;",13),
            ("total_required_hours","&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x62D;&#x642;&#x629;",14),
        ]
        for key, label, order in seed_group_labels:
            try:
                db2.execute("INSERT INTO group_col_labels(col_key,col_label,col_order) VALUES(?,?,?)", (key, label, order))
            except Exception:
                pass
        try:
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("group_labels_v2",))
        except Exception:
            pass
    db2.commit()
    db2.execute("""CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attendance_date TEXT,
        day_name TEXT,
        group_name TEXT,
        student_name TEXT,
        contact_number TEXT,
        status TEXT,
        message TEXT,
        message_status TEXT,
        study_status TEXT)""")
    db2.execute("""CREATE TABLE IF NOT EXISTS att_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    db2.execute("""CREATE TABLE IF NOT EXISTS custom_tables(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tbl_name TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now')))""")
    db2.execute("""CREATE TABLE IF NOT EXISTS custom_table_cols(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER,
        col_key TEXT,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    db2.execute("""CREATE TABLE IF NOT EXISTS custom_table_rows(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER,
        row_data TEXT DEFAULT '{}')""")
    db2.execute("""CREATE TABLE IF NOT EXISTS message_templates(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db2.execute("""CREATE TABLE IF NOT EXISTS message_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        student_whatsapp TEXT,
        template_name TEXT,
        sent_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db2.execute("""CREATE TABLE IF NOT EXISTS message_reminders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        day_of_week INTEGER,
        time_of_day TEXT,
        template_id INTEGER,
        group_name TEXT,
        enabled INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    # Add paid1..paid12 columns to taqseet if missing
    tq_existing = [row[1] for row in db2.execute("PRAGMA table_info(taqseet)").fetchall()]
    for pn in range(1, 13):
        pcol = "paid" + str(pn)
        if pcol not in tq_existing:
            db2.execute("ALTER TABLE taqseet ADD COLUMN " + pcol + " TEXT DEFAULT ''")
    db2.commit()
    # Add 10 default rows to taqseet if empty
    if db2.execute("SELECT COUNT(*) FROM taqseet").fetchone()[0] == 0:
        for i in range(1, 11):
            db2.execute("INSERT INTO taqseet (taqseet_method) VALUES (?)", (str(i),))
        db2.commit()
    db2.execute("""CREATE TABLE IF NOT EXISTS student_payments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        inst_num INTEGER,
        inst_type TEXT DEFAULT '',
        price REAL DEFAULT 0,
        paid REAL DEFAULT 0,
        UNIQUE(student_id, inst_num)
    )""")
    db2.execute("""CREATE TABLE IF NOT EXISTS session_durations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        session_date TEXT,
        duration_minutes INTEGER DEFAULT 0,
        session_type TEXT DEFAULT '',
        UNIQUE(group_name, session_date)
    )""")
    # One-shot: drop the old payment_log feature. Guarded so it only runs once.
    if "drop_paylog_v1" not in applied:
        try: db2.execute("DROP TABLE IF EXISTS payment_log")
        except Exception: pass
        try: db2.execute("DROP TABLE IF EXISTS paylog_col_labels")
        except Exception: pass
        try: db2.execute("DELETE FROM schema_migrations WHERE tag = ?", ("paylog_labels_v1",))
        except Exception: pass
        try: db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("drop_paylog_v1",))
        except Exception: pass
        db2.commit()
    db2.execute("""CREATE TABLE IF NOT EXISTS taqseet_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    db2.execute("""CREATE TABLE IF NOT EXISTS evaluations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        form_fill_date TEXT,
        group_name TEXT,
        student_name TEXT,
        class_participation TEXT,
        general_behavior TEXT,
        behavior_notes TEXT,
        reading TEXT,
        dictation TEXT,
        term_meanings TEXT,
        conversation TEXT,
        expression TEXT,
        grammar TEXT,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db2.execute("""CREATE TABLE IF NOT EXISTS eval_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    if "eval_labels_v1" not in applied:
        seed_eval_labels = [
            ("form_fill_date",      "&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x645;&#x644;&#x621; &#x627;&#x644;&#x625;&#x633;&#x62A;&#x645;&#x627;&#x631;&#x629;", 1),
            ("group_name",          "&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;", 2),
            ("student_name",        "&#x627;&#x644;&#x627;&#x633;&#x645;", 3),
            ("class_participation", "&#x627;&#x644;&#x645;&#x634;&#x627;&#x631;&#x643;&#x629; &#x62F;&#x627;&#x62E;&#x644; &#x627;&#x644;&#x635;&#x641;", 4),
            ("general_behavior",    "&#x627;&#x644;&#x633;&#x644;&#x648;&#x643; &#x627;&#x644;&#x639;&#x627;&#x645;", 5),
            ("behavior_notes",      "&#x627;&#x644;&#x645;&#x644;&#x627;&#x62D;&#x638;&#x627;&#x62A; &#x639;&#x644;&#x649; &#x627;&#x644;&#x633;&#x644;&#x648;&#x643;", 6),
            ("reading",             "&#x627;&#x644;&#x642;&#x631;&#x627;&#x621;&#x629;", 7),
            ("dictation",           "&#x627;&#x644;&#x625;&#x645;&#x644;&#x627;&#x621;", 8),
            ("term_meanings",       "&#x645;&#x639;&#x627;&#x646;&#x64A; &#x627;&#x644;&#x645;&#x635;&#x637;&#x644;&#x62D;&#x627;&#x62A;", 9),
            ("conversation",        "&#x627;&#x644;&#x645;&#x62D;&#x627;&#x62F;&#x62B;&#x629;", 10),
            ("expression",          "&#x627;&#x644;&#x62A;&#x639;&#x628;&#x64A;&#x631;", 11),
            ("grammar",             "&#x627;&#x644;&#x642;&#x648;&#x627;&#x639;&#x62F;", 12),
            ("notes",               "&#x627;&#x644;&#x645;&#x644;&#x627;&#x62D;&#x638;&#x627;&#x62A;", 13),
        ]
        for key, label, order in seed_eval_labels:
            try:
                db2.execute("INSERT INTO eval_col_labels(col_key,col_label,col_order) VALUES(?,?,?)", (key, label, order))
            except Exception:
                pass
        try:
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("eval_labels_v1",))
        except Exception:
            pass
    db2.execute("""CREATE TABLE IF NOT EXISTS payment_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT,
        personal_id TEXT,
        registration_status TEXT,
        course_amount TEXT,
        inst1 TEXT, msg1 TEXT,
        inst2 TEXT, msg2 TEXT,
        inst3 TEXT, msg3 TEXT,
        inst4 TEXT, msg4 TEXT,
        inst5 TEXT, msg5 TEXT,
        total_paid TEXT,
        total_remaining TEXT,
        payment_status TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db2.execute("""CREATE TABLE IF NOT EXISTS paylog_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    if "paylog_labels_v2" not in applied:
        seed_paylog_labels = [
            ("student_name",        "&#x627;&#x644;&#x627;&#x633;&#x645;", 1),
            ("registration_status", "&#x62D;&#x627;&#x644;&#x629; &#x627;&#x644;&#x62A;&#x633;&#x62C;&#x64A;&#x644;", 2),
            ("course_amount",       "&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x62F;&#x648;&#x631;&#x629;", 3),
            ("inst1",               "&#x627;&#x644;&#x642;&#x633;&#x637; 1", 4),
            ("msg1",                "&#x627;&#x644;&#x642;&#x633;&#x637; 1 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;", 5),
            ("inst2",               "&#x627;&#x644;&#x642;&#x633;&#x637; 2", 6),
            ("msg2",                "&#x627;&#x644;&#x642;&#x633;&#x637; 2 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;", 7),
            ("inst3",               "&#x627;&#x644;&#x642;&#x633;&#x637; 3", 8),
            ("msg3",                "&#x627;&#x644;&#x642;&#x633;&#x637; 3 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;", 9),
            ("inst4",               "&#x627;&#x644;&#x642;&#x633;&#x637; 4", 10),
            ("msg4",                "&#x627;&#x644;&#x642;&#x633;&#x637; 4 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;", 11),
            ("inst5",               "&#x627;&#x644;&#x642;&#x633;&#x637; 5", 12),
            ("msg5",                "&#x627;&#x644;&#x642;&#x633;&#x637; 5 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;", 13),
            ("total_paid",          "&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639;", 14),
            ("total_remaining",     "&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62A;&#x628;&#x642;&#x64A;", 15),
            ("payment_status",      "&#x62D;&#x627;&#x644;&#x629; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639;&#x627;&#x62A;", 16),
        ]
        for key, label, order in seed_paylog_labels:
            try:
                db2.execute("INSERT INTO paylog_col_labels(col_key,col_label,col_order) VALUES(?,?,?)", (key, label, order))
            except Exception:
                pass
        try:
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("paylog_labels_v2",))
        except Exception:
            pass
    # Ensure col_type and col_options exist on every label-bearing table
    # (supports typed cells added later via the UI). Runs once per DB thanks
    # to the migration marker below.
    if "col_types_v1" not in applied:
        for _lbltbl in ("column_labels", "group_col_labels", "att_col_labels",
                        "eval_col_labels", "paylog_col_labels", "custom_table_cols"):
            try:
                _cols = [r[1] for r in db2.execute("PRAGMA table_info(" + _lbltbl + ")").fetchall()]
                if "col_type" not in _cols:
                    db2.execute("ALTER TABLE " + _lbltbl + " ADD COLUMN col_type TEXT DEFAULT 'نص'")
                if "col_options" not in _cols:
                    db2.execute("ALTER TABLE " + _lbltbl + " ADD COLUMN col_options TEXT DEFAULT ''")
            except Exception:
                pass
        try:
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("col_types_v1",))
        except Exception:
            pass
        db2.commit()

    # taqseet_col_labels originally shipped with only (id, col_key, col_label).
    # Add col_order / col_type / col_options so the add-column INSERT — which
    # specifies all five — stops failing silently and leaving rows un-stored.
    if "taqseet_labels_schema_v1" not in applied:
        try:
            _tc = [r[1] for r in db2.execute("PRAGMA table_info(taqseet_col_labels)").fetchall()]
            if "col_order" not in _tc:
                db2.execute("ALTER TABLE taqseet_col_labels ADD COLUMN col_order INTEGER DEFAULT 0")
            if "is_visible" not in _tc:
                db2.execute("ALTER TABLE taqseet_col_labels ADD COLUMN is_visible INTEGER DEFAULT 1")
            if "col_type" not in _tc:
                db2.execute("ALTER TABLE taqseet_col_labels ADD COLUMN col_type TEXT DEFAULT 'نص'")
            if "col_options" not in _tc:
                db2.execute("ALTER TABLE taqseet_col_labels ADD COLUMN col_options TEXT DEFAULT ''")
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("taqseet_labels_schema_v1",))
            db2.commit()
        except Exception:
            pass

    # Settings table — lets admins remap table/column references without code edits.
    db2.execute("""CREATE TABLE IF NOT EXISTS settings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page TEXT NOT NULL,
        component TEXT NOT NULL,
        label TEXT NOT NULL,
        value TEXT DEFAULT '',
        value_type TEXT DEFAULT 'table_column',
        UNIQUE(page, component)
    )""")
    if "settings_seed_v1" not in applied:
        _seed = [
            ('attendance', 'groups_table', 'جدول المجموعات', 'student_groups'),
            ('attendance', 'groups_column', 'عمود اسم المجموعة', 'group_name'),
            ('attendance', 'students_table', 'جدول الطلاب', 'students'),
            ('attendance', 'student_name_column', 'عمود اسم الطالب', 'student_name'),
            ('attendance', 'student_phone_column', 'عمود رقم الواتساب', 'whatsapp'),
            ('messaging', 'groups_table', 'جدول المجموعات', 'student_groups'),
            ('messaging', 'groups_column', 'عمود المجموعة', 'group_name'),
            ('messaging', 'students_table', 'جدول الطلاب', 'students'),
            ('messaging', 'name_column', 'عمود الاسم', 'student_name'),
            ('messaging', 'phone_column', 'عمود الواتساب', 'whatsapp'),
            ('payment', 'table', 'جدول الدفع', 'taqseet'),
            ('payment', 'name_column', 'عمود الاسم', 'student_name'),
            ('payment', 'amount_column', 'عمود المبلغ', 'course_amount'),
            ('payment', 'groups_table', 'جدول المجموعات', 'student_groups'),
            ('payment', 'groups_column', 'عمود المجموعة', 'group_name'),
            ('dashboard', 'students_table', 'جدول الطلاب', 'students'),
            ('dashboard', 'groups_table', 'جدول المجموعات', 'student_groups'),
            ('dashboard', 'attendance_table', 'جدول الغياب', 'attendance'),
            ('dashboard', 'payment_table', 'جدول الدفع', 'taqseet'),
            ('database', 'visible_tables', 'الجداول الظاهرة', 'all'),
            ('groups', 'table', 'جدول المجموعات', 'student_groups'),
            ('groups', 'name_column', 'عمود اسم المجموعة', 'group_name'),
            ('attendance', 'attendance_table', 'جدول الغياب', 'attendance'),
            ('attendance', 'student_group_column', 'عمود مجموعة الطالب', 'group_name_student'),
            ('attendance', 'date_column', 'عمود التاريخ', 'attendance_date'),
            ('attendance', 'day_column', 'عمود اليوم', 'day_name'),
            ('attendance', 'status_column', 'عمود الحالة', 'status'),
            ('attendance', 'message_column', 'عمود الرسالة', 'message'),
            ('attendance', 'message_status_column', 'عمود حالة الرسالة', 'message_status'),
            ('attendance', 'study_status_column', 'عمود حالة الدراسة', 'study_status'),
            ('messaging', 'templates_table', 'جدول قوالب الرسائل', 'message_templates'),
            ('messaging', 'templates_name_column', 'عمود اسم القالب', 'name'),
            ('messaging', 'templates_category_column', 'عمود تصنيف القالب', 'category'),
            ('messaging', 'templates_content_column', 'عمود نص القالب', 'content'),
            ('messaging', 'log_table', 'جدول سجل الرسائل', 'message_log'),
            ('messaging', 'log_student_column', 'عمود الطالب في السجل', 'student_name'),
            ('messaging', 'log_whatsapp_column', 'عمود واتساب السجل', 'student_whatsapp'),
            ('messaging', 'log_template_column', 'عمود قالب السجل', 'template_name'),
            ('messaging', 'reminders_table', 'جدول التذكيرات', 'message_reminders'),
            ('messaging', 'student_id_column', 'عمود الرقم الشخصي', 'personal_id'),
            ('payment', 'students_table', 'جدول الطلاب للدفع', 'students'),
            ('payment', 'student_name_column', 'عمود اسم الطالب', 'student_name'),
            ('payment', 'installment_type_column', 'عمود نوع التقسيط', 'installment_type'),
            ('payment', 'taqseet_method_column', 'عمود طريقة التقسيط', 'taqseet_method'),
            ('payment', 'paid_amount_column', 'عمود المبلغ المدفوع', 'paid'),
            ('payment', 'payments_table', 'جدول المدفوعات', 'student_payments'),
            ('payment', 'num_installments_column', 'عمود عدد الأقساط', 'num_installments'),
            ('dashboard', 'students_class_column', 'عمود صف الطالب', 'class_name'),
            ('dashboard', 'students_result_column', 'عمود نتيجة الطالب', 'final_result'),
            ('dashboard', 'students_teacher_column', 'عمود مدرس الطالب', 'teacher_2026'),
            ('dashboard', 'students_subject_column', 'عمود مادة الطالب', 'class_name'),
            ('dashboard', 'attendance_status_column', 'عمود حالة الغياب', 'status'),
            ('groups', 'teacher_column', 'عمود اسم المدرس', 'teacher_name'),
            ('groups', 'level_column', 'عمود المستوى', 'level_course'),
            ('groups', 'study_time_column', 'عمود وقت الدراسة', 'study_time'),
            ('groups', 'link_column', 'عمود رابط المجموعة', 'group_link'),
            ('evaluations', 'table', 'جدول التقييمات', 'evaluations'),
            ('evaluations', 'student_name_column', 'عمود اسم الطالب', 'student_name'),
            ('evaluations', 'group_column', 'عمود المجموعة', 'group_name'),
            ('evaluations', 'date_column', 'عمود تاريخ التقييم', 'form_fill_date'),
            ('evaluations', 'reading_column', 'عمود القراءة', 'reading'),
            ('evaluations', 'dictation_column', 'عمود الإملاء', 'dictation'),
            ('evaluations', 'conversation_column', 'عمود المحادثة', 'conversation'),
            ('evaluations', 'expression_column', 'عمود التعبير', 'expression'),
            ('evaluations', 'grammar_column', 'عمود القواعد', 'grammar'),
            ('paylog', 'table', 'جدول سجل الدفع', 'payment_log'),
            ('paylog', 'student_name_column', 'عمود اسم الطالب', 'student_name'),
            ('paylog', 'personal_id_column', 'عمود الرقم', 'personal_id'),
            ('paylog', 'course_amount_column', 'عمود مبلغ الدورة', 'course_amount'),
            ('paylog', 'total_paid_column', 'عمود المدفوع', 'total_paid'),
            ('paylog', 'total_remaining_column', 'عمود المتبقي', 'total_remaining'),
            ('paylog', 'status_column', 'عمود حالة الدفع', 'payment_status'),
        ]
        for _p, _c, _lbl, _v in _seed:
            try:
                db2.execute(
                    "INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?) "
                    "ON CONFLICT(page,component) DO NOTHING",
                    (_p, _c, _lbl, _v),
                )
            except Exception:
                try:
                    db2.execute(
                        "INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)",
                        (_p, _c, _lbl, _v),
                    )
                except Exception:
                    pass
        try:
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("settings_seed_v1",))
        except Exception:
            pass
        db2.commit()

    if "settings_seed_v2" not in applied:
        _seed_v2 = [
            ('attendance', 'attendance_table', 'جدول الغياب', 'attendance'),
            ('attendance', 'student_group_column', 'عمود مجموعة الطالب', 'group_name_student'),
            ('attendance', 'date_column', 'عمود التاريخ', 'attendance_date'),
            ('attendance', 'day_column', 'عمود اليوم', 'day_name'),
            ('attendance', 'status_column', 'عمود الحالة', 'status'),
            ('attendance', 'message_column', 'عمود الرسالة', 'message'),
            ('attendance', 'message_status_column', 'عمود حالة الرسالة', 'message_status'),
            ('attendance', 'study_status_column', 'عمود حالة الدراسة', 'study_status'),
            ('messaging', 'templates_table', 'جدول قوالب الرسائل', 'message_templates'),
            ('messaging', 'templates_name_column', 'عمود اسم القالب', 'name'),
            ('messaging', 'templates_category_column', 'عمود تصنيف القالب', 'category'),
            ('messaging', 'templates_content_column', 'عمود نص القالب', 'content'),
            ('messaging', 'log_table', 'جدول سجل الرسائل', 'message_log'),
            ('messaging', 'log_student_column', 'عمود الطالب في السجل', 'student_name'),
            ('messaging', 'log_whatsapp_column', 'عمود واتساب السجل', 'student_whatsapp'),
            ('messaging', 'log_template_column', 'عمود قالب السجل', 'template_name'),
            ('messaging', 'reminders_table', 'جدول التذكيرات', 'message_reminders'),
            ('messaging', 'student_id_column', 'عمود الرقم الشخصي', 'personal_id'),
            ('payment', 'students_table', 'جدول الطلاب للدفع', 'students'),
            ('payment', 'student_name_column', 'عمود اسم الطالب', 'student_name'),
            ('payment', 'installment_type_column', 'عمود نوع التقسيط', 'installment_type'),
            ('payment', 'taqseet_method_column', 'عمود طريقة التقسيط', 'taqseet_method'),
            ('payment', 'paid_amount_column', 'عمود المبلغ المدفوع', 'paid'),
            ('payment', 'payments_table', 'جدول المدفوعات', 'student_payments'),
            ('payment', 'num_installments_column', 'عمود عدد الأقساط', 'num_installments'),
            ('dashboard', 'students_class_column', 'عمود صف الطالب', 'class_name'),
            ('dashboard', 'students_result_column', 'عمود نتيجة الطالب', 'final_result'),
            ('dashboard', 'students_teacher_column', 'عمود مدرس الطالب', 'teacher_2026'),
            ('dashboard', 'students_subject_column', 'عمود مادة الطالب', 'class_name'),
            ('dashboard', 'attendance_status_column', 'عمود حالة الغياب', 'status'),
            ('groups', 'teacher_column', 'عمود اسم المدرس', 'teacher_name'),
            ('groups', 'level_column', 'عمود المستوى', 'level_course'),
            ('groups', 'study_time_column', 'عمود وقت الدراسة', 'study_time'),
            ('groups', 'link_column', 'عمود رابط المجموعة', 'group_link'),
            ('evaluations', 'table', 'جدول التقييمات', 'evaluations'),
            ('evaluations', 'student_name_column', 'عمود اسم الطالب', 'student_name'),
            ('evaluations', 'group_column', 'عمود المجموعة', 'group_name'),
            ('evaluations', 'date_column', 'عمود تاريخ التقييم', 'form_fill_date'),
            ('evaluations', 'reading_column', 'عمود القراءة', 'reading'),
            ('evaluations', 'dictation_column', 'عمود الإملاء', 'dictation'),
            ('evaluations', 'conversation_column', 'عمود المحادثة', 'conversation'),
            ('evaluations', 'expression_column', 'عمود التعبير', 'expression'),
            ('evaluations', 'grammar_column', 'عمود القواعد', 'grammar'),
            ('paylog', 'table', 'جدول سجل الدفع', 'payment_log'),
            ('paylog', 'student_name_column', 'عمود اسم الطالب', 'student_name'),
            ('paylog', 'personal_id_column', 'عمود الرقم', 'personal_id'),
            ('paylog', 'course_amount_column', 'عمود مبلغ الدورة', 'course_amount'),
            ('paylog', 'total_paid_column', 'عمود المدفوع', 'total_paid'),
            ('paylog', 'total_remaining_column', 'عمود المتبقي', 'total_remaining'),
            ('paylog', 'status_column', 'عمود حالة الدفع', 'payment_status'),
        ]
        for _p, _c, _lbl, _v in _seed_v2:
            try:
                db2.execute(
                    "INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?) "
                    "ON CONFLICT(page,component) DO NOTHING",
                    (_p, _c, _lbl, _v),
                )
            except Exception:
                try:
                    db2.execute(
                        "INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)",
                        (_p, _c, _lbl, _v),
                    )
                except Exception:
                    pass
        try:
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("settings_seed_v2",))
        except Exception:
            pass
        db2.commit()

    # Ensure table_labels table exists for every DB, then seed built-in
    # display names so the settings page / تعديل الجدول modal never shows
    # raw DB identifiers like "students" or "group_name_student".
    db2.execute("""CREATE TABLE IF NOT EXISTS table_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tbl_name TEXT UNIQUE,
        tbl_label TEXT)""")
    if "table_labels_seed_v1" not in applied:
        built_in_tbl_labels = [
            ("students",         "قاعدة بيانات الطلبة"),
            ("student_groups",   "المجموعات"),
            ("attendance",       "سجل الغياب"),
            ("taqseet",          "جدول التقسيط"),
            ("evaluations",      "التقييمات"),
            ("payment_log",      "سجل الدفع"),
            ("student_payments", "دفعات الطلبة"),
            ("session_durations","مدة الحصص"),
            ("message_templates","قوالب الرسائل"),
            ("message_log",      "سجل الرسائل"),
            ("message_reminders","تذكيرات الرسائل"),
            ("users",            "المستخدمون"),
            ("settings",         "الإعدادات"),
        ]
        for n, lbl in built_in_tbl_labels:
            try:
                db2.execute(
                    "INSERT INTO table_labels(tbl_name, tbl_label) VALUES(?,?) "
                    "ON CONFLICT(tbl_name) DO UPDATE SET tbl_label=EXCLUDED.tbl_label",
                    (n, lbl),
                )
            except Exception:
                try:
                    db2.execute("INSERT INTO table_labels(tbl_name, tbl_label) VALUES(?,?)", (n, lbl))
                except Exception:
                    pass
        try:
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("table_labels_seed_v1",))
        except Exception:
            pass
        db2.commit()

    # Seed Arabic labels for taqseet's numbered columns (inst1..inst12,
    # paid1..paid12, date1..date12) and the handful of misc fields so the
    # تعديل الجدول modal renders Arabic for every taqseet column.
    if "taqseet_labels_seed_v1" not in applied:
        try:
            rows_taq = [
                ("taqseet_method",   "طريقة التقسيط",     1),
                ("student_name",     "اسم الطالب",         2),
                ("course_amount",    "مبلغ الدورة",        3),
                ("num_installments", "عدد الأقساط",       4),
                ("study_hours",      "ساعات الدراسة",     200),
                ("start_date",       "تاريخ بدء الدورة",  201),
            ]
            for n in range(1, 13):
                base = 5 + (n - 1) * 3
                rows_taq.append(("inst" + str(n),  "القسط " + str(n),         base))
                rows_taq.append(("paid" + str(n),  "المبلغ المدفوع " + str(n), base + 1))
                rows_taq.append(("date" + str(n),  "تاريخ الاستحقاق " + str(n), base + 2))
            for key, label, order in rows_taq:
                try:
                    db2.execute(
                        "INSERT INTO taqseet_col_labels(col_key, col_label, col_order) "
                        "VALUES(?,?,?) "
                        "ON CONFLICT(col_key) DO UPDATE SET col_label=EXCLUDED.col_label",
                        (key, label, order),
                    )
                except Exception:
                    try:
                        cur = db2.execute(
                            "UPDATE taqseet_col_labels SET col_label=? WHERE col_key=?",
                            (label, key),
                        )
                        if cur.rowcount == 0:
                            db2.execute(
                                "INSERT INTO taqseet_col_labels(col_key, col_label, col_order) VALUES(?,?,?)",
                                (key, label, order),
                            )
                    except Exception:
                        pass
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("taqseet_labels_seed_v1",))
            db2.commit()
        except Exception:
            pass

    # ── Attendance data normalization (one-shot) ─────────────────────
    # Legacy imports wrote attendance_date as "31/1-2026م", "9/2/2026م",
    # and similar, so the attendance page never matched the ISO date the
    # <input type="date"> sends. Normalize every row here once, tagged
    # `att_normalize_v1`. The prod DB was also migrated out-of-band, and
    # that INSERT is gated by ON CONFLICT so re-running is harmless.
    if "students_active_v1" not in applied:
        try:
            db2.execute(
                "INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?) "
                "ON CONFLICT(page,component) DO NOTHING",
                ('students', 'active_column', 'عمود حالة النشاط', 'registration_term2_2026'),
            )
            db2.execute(
                "INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?) "
                "ON CONFLICT(page,component) DO NOTHING",
                ('students', 'active_value', 'قيمة الطالب النشط', 'تم التسجيل'),
            )
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("students_active_v1",))
            db2.commit()
        except Exception:
            pass

    if "att_normalize_v1" not in applied:
        try:
            import re as _re_att
            _STATUS_REMAP_MIG = {
                "غياب":  "غائب",   # غياب  -> غائب
                "تأخير": "متأخر", # تأخير -> متأخر
                "حضور":  "حاضر",   # حضور  -> حاضر
                "absent":  "غائب",
                "late":    "متأخر",
                "present": "حاضر",
            }
            def _mig_date(s):
                if not s: return ""
                s = str(s).strip()
                if not s: return ""
                nums = _re_att.findall(r"\d+", s)
                if len(nums) < 3: return s
                if len(nums[0]) == 4:
                    y, m, d = nums[0], nums[1], nums[2]
                elif len(nums[-1]) == 4:
                    d, m, y = nums[0], nums[1], nums[-1]
                else:
                    d, m, y = nums[0], nums[1], nums[2]
                    if len(y) == 2:
                        y = ("20" + y) if int(y) < 70 else ("19" + y)
                try:
                    iy, im, id_ = int(y), int(m), int(d)
                    if not (1 <= im <= 12 and 1 <= id_ <= 31): return s
                    return "%04d-%02d-%02d" % (iy, im, id_)
                except Exception:
                    return s
            rows = db2.execute("SELECT id, attendance_date, group_name, student_name, status FROM attendance").fetchall()
            for r in rows:
                rid = r[0]; d = r[1] or ""; g = r[2] or ""; n = r[3] or ""; st = r[4] or ""
                new_d = _mig_date(d)
                new_g = " ".join(g.split())
                new_n = " ".join(n.split())
                new_st_raw = st.strip()
                new_st = _STATUS_REMAP_MIG.get(new_st_raw, new_st_raw)
                if new_d != d or new_g != g or new_n != n or new_st != st:
                    db2.execute(
                        "UPDATE attendance SET attendance_date=?, group_name=?, student_name=?, status=? WHERE id=?",
                        (new_d, new_g, new_n, new_st, rid)
                    )
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("att_normalize_v1",))
            db2.commit()
        except Exception:
            pass

    db2.commit()
    db2.close()

SETTINGS_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>&#x625;&#x639;&#x62F;&#x627;&#x62F;&#x627;&#x62A; &#x645;&#x631;&#x626;&#x64A;&#x629; &#x2014; Mindex</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:'Segoe UI',Tahoma,Arial,sans-serif;}
body{background:linear-gradient(135deg,#eef2ff,#fdf2f8 55%,#ecfeff);min-height:100vh;padding:18px;color:#1f2937;}
.topbar{display:flex;justify-content:space-between;align-items:center;background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;padding:14px 22px;border-radius:14px;margin-bottom:16px;box-shadow:0 6px 18px rgba(107,63,160,0.25);}
.topbar h1{font-size:1.35rem;letter-spacing:.3px;}
.topbar-links{display:flex;gap:8px;}
.topbar a{color:#fff;background:rgba(255,255,255,0.18);padding:8px 16px;border-radius:10px;text-decoration:none;font-weight:700;font-size:14px;}
.topbar a:hover{background:rgba(255,255,255,0.3);}
.tabs{display:flex;flex-wrap:wrap;gap:6px;background:#fff;padding:8px;border-radius:14px;box-shadow:0 2px 10px rgba(0,0,0,0.04);margin-bottom:14px;}
.tab{padding:9px 14px;border-radius:10px;cursor:pointer;font-weight:700;font-size:14px;color:#555;background:#f4f4f8;border:2px solid transparent;transition:all .18s ease;user-select:none;}
.tab:hover{background:#eceff5;}
.tab.active{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border-color:transparent;box-shadow:0 3px 10px rgba(107,63,160,0.3);}
.workspace{display:grid;grid-template-columns:1.2fr 1fr;gap:14px;min-height:540px;}
@media(max-width:1000px){.workspace{grid-template-columns:1fr;}}
.panel{background:#fff;border-radius:16px;padding:18px;box-shadow:0 4px 14px rgba(0,0,0,0.05);position:relative;overflow:hidden;}
.panel-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;padding-bottom:10px;border-bottom:1.5px dashed #eceff5;}
.panel-title{font-size:1.05rem;font-weight:800;color:#4a2e87;display:flex;align-items:center;gap:6px;}
.panel-sub{font-size:12px;color:#888;}
.watermark{position:absolute;top:46%;left:50%;transform:translate(-50%,-50%) rotate(-18deg);font-size:5.5rem;font-weight:900;color:rgba(107,63,160,0.045);pointer-events:none;letter-spacing:6px;user-select:none;}
/* Preview mockup layout */
.preview-canvas{position:relative;border:2px solid #eef0f7;border-radius:14px;padding:14px;background:linear-gradient(180deg,#fcfcff,#f5f6fc);min-height:460px;}
.mock-header{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;padding:10px 14px;border-radius:10px;font-weight:800;font-size:14px;display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;box-shadow:0 3px 8px rgba(107,63,160,0.2);}
.mock-zone{background:#fff;border:1.5px solid #e7ebf2;border-radius:12px;padding:12px;margin-bottom:12px;position:relative;}
.mock-zone-label{position:absolute;top:-10px;right:12px;background:#fff;padding:0 8px;font-size:12px;font-weight:700;color:#6B3FA0;}
.mock-zone-body{display:flex;flex-wrap:wrap;gap:8px;min-height:42px;align-items:center;padding:4px 2px;}
.badge{display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border-radius:999px;font-size:12.5px;font-weight:700;color:#fff;cursor:pointer;transition:transform .15s ease,box-shadow .15s ease;box-shadow:0 2px 6px rgba(0,0,0,0.1);user-select:none;border:2px solid rgba(255,255,255,0.6);}
.badge:hover{transform:translateY(-2px);}
.badge .num{background:rgba(255,255,255,0.3);border-radius:50%;width:20px;height:20px;display:inline-flex;align-items:center;justify-content:center;font-size:11.5px;font-weight:900;}
.badge .text{max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.badge.hl, .card.hl{animation:pulse 1.1s ease-in-out infinite;}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(107,63,160,0.45);}70%{box-shadow:0 0 0 10px rgba(107,63,160,0);}100%{box-shadow:0 0 0 0 rgba(107,63,160,0);}}
/* Settings cards */
.cards{display:flex;flex-direction:column;gap:10px;max-height:72vh;overflow-y:auto;padding-left:4px;}
.cards::-webkit-scrollbar{width:8px;}
.cards::-webkit-scrollbar-thumb{background:#d0c7e8;border-radius:8px;}
.card{background:#fff;border:2px solid #eceff5;border-radius:12px;padding:12px 14px;display:flex;gap:10px;align-items:center;transition:all .18s ease;cursor:pointer;}
.card:hover{border-color:#b39ddb;box-shadow:0 4px 10px rgba(107,63,160,0.1);}
.card-num{flex:0 0 34px;height:34px;border-radius:10px;color:#fff;font-weight:900;display:flex;align-items:center;justify-content:center;font-size:14px;}
.card-body{flex:1;min-width:0;}
.card-label{font-size:13.5px;font-weight:700;color:#333;margin-bottom:2px;display:flex;align-items:center;gap:6px;}
.card-comp{font-size:11px;color:#999;font-family:monospace;}
.card-controls{display:flex;gap:6px;align-items:center;flex-wrap:wrap;margin-top:8px;}
.card select{padding:7px 10px;border:1.5px solid #d7dae0;border-radius:8px;font-size:13px;background:#fafbff;min-width:140px;max-width:200px;}
.card select:focus{outline:none;border-color:#8B5CC8;}
.card .check{color:#43A047;font-weight:900;font-size:13px;opacity:0;transition:opacity .2s ease;}
.card .check.show{opacity:1;}
.empty{text-align:center;color:#999;padding:40px 20px;font-size:15px;}
.loading-full{text-align:center;color:#999;padding:60px 20px;font-size:16px;font-weight:700;}
.toast{position:fixed;bottom:26px;left:50%;transform:translateX(-50%) translateY(20px);background:#43A047;color:#fff;padding:11px 22px;border-radius:12px;font-weight:700;font-size:14px;box-shadow:0 6px 20px rgba(67,160,71,0.35);opacity:0;transition:all .25s ease;pointer-events:none;z-index:999;}
.toast.err{background:#e53935;box-shadow:0 6px 20px rgba(229,57,53,0.35);}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0);}
/* Color groups */
.col-tbl{background:linear-gradient(135deg,#1976D2,#42A5F5);}
.col-name{background:linear-gradient(135deg,#388E3C,#66BB6A);}
.col-phone{background:linear-gradient(135deg,#F57C00,#FFB74D);}
.col-group{background:linear-gradient(135deg,#7B1FA2,#BA68C8);}
.col-amount{background:linear-gradient(135deg,#C62828,#EF5350);}
.col-date{background:linear-gradient(135deg,#00838F,#4DD0E1);}
.col-status{background:linear-gradient(135deg,#C2185B,#F06292);}
.col-install{background:linear-gradient(135deg,#5D4037,#A1887F);}
.col-other{background:linear-gradient(135deg,#455A64,#78909C);}
.legend{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:10px;font-size:11.5px;}
.legend-item{display:inline-flex;align-items:center;gap:5px;background:#f6f7fb;padding:4px 10px;border-radius:999px;color:#555;font-weight:700;}
.legend-dot{width:11px;height:11px;border-radius:50%;display:inline-block;}
</style>
</head>
<body>
<div class="topbar">
  <h1>&#x2699; &#x625;&#x639;&#x62F;&#x627;&#x62F;&#x627;&#x62A; &#x645;&#x631;&#x626;&#x64A;&#x629; &#x2014; &#x631;&#x628;&#x637; &#x627;&#x644;&#x62C;&#x62F;&#x627;&#x648;&#x644; &#x648;&#x627;&#x644;&#x623;&#x639;&#x645;&#x62F;&#x629;</h1>
  <div class="topbar-links">
    <a href="/dashboard">&#x2190; &#x627;&#x644;&#x631;&#x626;&#x64A;&#x633;&#x64A;&#x629;</a>
  </div>
</div>
<div id="tabs" class="tabs"></div>
<div id="workspace" class="loading-full">&#x62C;&#x627;&#x631;&#x64A; &#x627;&#x644;&#x62A;&#x62D;&#x645;&#x64A;&#x644;...</div>
<div id="toast" class="toast"></div>
<script>
/* ---------------- color helpers ---------------- */
function colorFor(component) {
  var c = (component || '').toLowerCase();
  if (c === 'table' || c.endsWith('_table')) return 'col-tbl';
  if (c.indexOf('phone') >= 0 || c.indexOf('whatsapp') >= 0) return 'col-phone';
  if (c.indexOf('amount') >= 0 || c === 'paid_amount_column' || c.indexOf('paid_column') >= 0 || c.indexOf('remaining') >= 0 || c === 'total_paid_column' || c === 'total_remaining_column') return 'col-amount';
  if (c.indexOf('group') >= 0) return 'col-group';
  if (c.indexOf('name_column') >= 0 || c === 'student_name_column' || c === 'log_student_column' || c === 'templates_name_column') return 'col-name';
  if (c.indexOf('date') >= 0 || c === 'day_column' || c === 'form_fill_date') return 'col-date';
  if (c.indexOf('status') >= 0) return 'col-status';
  if (c.indexOf('installment') >= 0 || c.indexOf('taqseet') >= 0) return 'col-install';
  return 'col-other';
}
/* ---------------- page schema ---------------- */
var PAGE_META = {
  attendance:  {title:'صفحة الغياب',           icon:'📅', zones:['فلاتر وجداول','أعمدة جدول الغياب']},
  messaging:   {title:'صفحة الرسائل',     icon:'💬', zones:['جداول الرسائل','أعمدة الرسائل']},
  payment:     {title:'صفحة الدفع',                   icon:'💰', zones:['جداول الدفع','أعمدة الدفع']},
  dashboard:   {title:'الداشبورد',                    icon:'🏠', zones:['جداول الداشبورد','أعمدة الداشبورد']},
  database:    {title:'قاعدة البيانات', icon:'🗄', zones:['إعدادات العرض']},
  groups:      {title:'صفحة المجموعات', icon:'👥', zones:['جداول المجموعات','أعمدة المجموعات']},
  evaluations: {title:'صفحة التقييمات', icon:'⭐',       zones:['جداول التقييمات','أعمدة التقييمات']},
  paylog:      {title:'سجل الدفع',                          icon:'📜', zones:['جداول سجل الدفع','أعمدة سجل الدفع']}
};
var PAGE_ORDER = ['attendance','messaging','payment','dashboard','database','groups','evaluations','paylog'];

var ALL_TABLES = [];
var SETTINGS = {};
var CURRENT_PAGE = 'attendance';
var COLUMN_CACHE = {}; /* table -> [cols] */

/* ---------------- utilities ---------------- */
function escAttr(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;'); }
function isColumnComponent(comp){ return comp.indexOf('column') >= 0 || comp.endsWith('_col'); }
function isTableComponent(comp){ return comp === 'table' || comp.endsWith('_table') || comp === 'visible_tables'; }
function pairedTableFor(comp, items){
  if (!isColumnComponent(comp)) return null;
  var prefix = comp.replace(/_column$/,'').replace(/_col$/,'');
  var cand = [prefix + '_table', 'table'];
  for (var i=0;i<cand.length;i++){
    var x = items.find(function(s){ return s.component === cand[i]; });
    if (x) return x;
  }
  /* fallbacks by prefix match */
  var first = items.find(function(s){ return isTableComponent(s.component); });
  return first || null;
}

/* ---------------- loading ---------------- */
function loadAll() {
  Promise.all([
    fetch('/api/settings/tables',{credentials:'include'}).then(function(r){return r.json();}),
    fetch('/api/settings',{credentials:'include'}).then(function(r){return r.json();})
  ]).then(function(res){
    ALL_TABLES = (res[0].tables || []);
    SETTINGS = res[1].settings || {};
    buildTabs();
    renderPage(CURRENT_PAGE);
  }).catch(function(){
    document.getElementById('workspace').textContent = 'خطأ في التحميل';
  });
}

/* ---------------- tabs ---------------- */
function buildTabs(){
  var tabs = document.getElementById('tabs');
  var keys = PAGE_ORDER.slice();
  /* any pages in SETTINGS not in PAGE_ORDER go to the end */
  Object.keys(SETTINGS).forEach(function(k){ if (keys.indexOf(k) < 0) keys.push(k); });
  var html = '';
  keys.forEach(function(k){
    var meta = PAGE_META[k] || {title:k, icon:'⚙'};
    var count = (SETTINGS[k] || []).length;
    html += '<div class="tab' + (k === CURRENT_PAGE ? ' active' : '') + '" data-tab="' + escAttr(k) + '">';
    html += meta.icon + ' ' + meta.title + ' <span style="opacity:.7;font-weight:600;">(' + count + ')</span>';
    html += '</div>';
  });
  tabs.innerHTML = html;
  tabs.addEventListener('click', function(e){
    var t = e.target.closest('.tab');
    if (!t) return;
    var k = t.getAttribute('data-tab');
    if (k === CURRENT_PAGE) return;
    CURRENT_PAGE = k;
    buildTabs();
    renderPage(k);
  });
}

/* ---------------- page render ---------------- */
function renderPage(page){
  var ws = document.getElementById('workspace');
  ws.className = '';
  var items = SETTINGS[page] || [];
  if (!items.length){
    ws.innerHTML = '<div class="panel"><div class="empty">لا توجد إعدادات لهذه الصفحة.</div></div>';
    return;
  }
  var meta = PAGE_META[page] || {title:page, icon:'⚙', zones:['جداول','أعمدة']};
  /* Split items: tables in zone 0, columns in zone 1 */
  var zoneItems = [[], []];
  items.forEach(function(s){
    if (isTableComponent(s.component)) zoneItems[0].push(s);
    else zoneItems[1].push(s);
  });
  /* number ALL items globally so badge number matches card number */
  var numbered = [];
  zoneItems[0].forEach(function(s){ numbered.push(s); });
  zoneItems[1].forEach(function(s){ numbered.push(s); });

  /* ----- left: preview ----- */
  var left = '';
  left += '<div class="watermark">معاينة</div>';
  left += '<div class="panel-head"><div class="panel-title">' + meta.icon + ' ' + meta.title + '</div><div class="panel-sub">' + items.length + ' إعداد</div></div>';
  left += '<div class="legend">';
  left += '<span class="legend-item"><span class="legend-dot col-tbl"></span>جدول</span>';
  left += '<span class="legend-item"><span class="legend-dot col-name"></span>اسم</span>';
  left += '<span class="legend-item"><span class="legend-dot col-phone"></span>هاتف</span>';
  left += '<span class="legend-item"><span class="legend-dot col-group"></span>مجموعة</span>';
  left += '<span class="legend-item"><span class="legend-dot col-amount"></span>مبلغ</span>';
  left += '<span class="legend-item"><span class="legend-dot col-date"></span>تاريخ</span>';
  left += '<span class="legend-item"><span class="legend-dot col-status"></span>حالة</span>';
  left += '</div>';
  left += '<div class="preview-canvas">';
  left += '<div class="mock-header"><span>' + meta.icon + ' ' + meta.title + '</span><span style="font-size:12px;opacity:.8;">&#x645;&#x639;&#x627;&#x64A;&#x646;&#x629; &#x62D;&#x64A;&#x629;</span></div>';

  var globalIdx = 0;
  for (var z=0; z<zoneItems.length; z++){
    if (!zoneItems[z].length) continue;
    var zname = (meta.zones && meta.zones[z]) || ('منطقة ' + (z+1));
    left += '<div class="mock-zone"><div class="mock-zone-label">' + zname + '</div><div class="mock-zone-body">';
    zoneItems[z].forEach(function(s){
      globalIdx++;
      var color = colorFor(s.component);
      left += '<span class="badge ' + color + '" data-component="' + escAttr(s.component) + '">';
      left += '<span class="num">' + globalIdx + '</span>';
      left += '<span class="text">' + s.label + '</span>';
      left += '</span>';
    });
    left += '</div></div>';
  }
  left += '</div>'; /* preview-canvas */

  /* ----- right: settings cards ----- */
  var right = '';
  right += '<div class="panel-head"><div class="panel-title">⚙ الإعدادات</div><div class="panel-sub">اختر الجدول أو العمود المناسب</div></div>';
  right += '<div class="cards" id="cardsList">';
  numbered.forEach(function(s, i){
    var num = i + 1;
    var color = colorFor(s.component);
    var isCol = isColumnComponent(s.component);
    right += '<div class="card" data-component="' + escAttr(s.component) + '">';
    right += '<div class="card-num ' + color + '">' + num + '</div>';
    right += '<div class="card-body">';
    right += '<div class="card-label">' + s.label + '<span class="check" id="chk_' + escAttr(s.component) + '">&#x2713;</span></div>';
    right += '<div class="card-comp">' + s.component + '</div>';
    right += '<div class="card-controls">';
    /* table dropdown (always) */
    right += '<select data-role="tbl" data-component="' + escAttr(s.component) + '">';
    right += '<option value="">— جدول —</option>';
    right += '<option value="all"' + (s.value === 'all' ? ' selected' : '') + '>الكل</option>';
    for (var ti=0; ti<ALL_TABLES.length; ti++){
      var tn = ALL_TABLES[ti].name;
      var tl = ALL_TABLES[ti].label || tn;
      var sel = (!isCol && s.value === tn) ? ' selected' : '';
      right += '<option value="' + escAttr(tn) + '"' + sel + '>' + tl + '</option>';
    }
    right += '</select>';
    if (isCol){
      right += '<select data-role="col" data-component="' + escAttr(s.component) + '">';
      right += '<option value="">— عمود —</option>';
      right += '</select>';
    }
    right += '</div>';
    right += '</div>';
    right += '</div>';
  });
  right += '</div>';

  ws.innerHTML = '<div class="panel" id="leftPanel">' + left + '</div><div class="panel" id="rightPanel">' + right + '</div>';
  ws.className = 'workspace';

  /* hydrate dropdowns for column-type settings */
  numbered.forEach(function(s){
    if (!isColumnComponent(s.component)) return;
    var paired = pairedTableFor(s.component, items);
    var card = document.querySelector('.card[data-component="' + cssEscape(s.component) + '"]');
    if (!card) return;
    var tblSel = card.querySelector('select[data-role="tbl"]');
    var colSel = card.querySelector('select[data-role="col"]');
    var tblValue = paired ? (paired.value || '') : '';
    if (tblSel && tblValue){
      /* Preselect the paired table if available in options */
      for (var i=0;i<tblSel.options.length;i++){
        if (tblSel.options[i].value === tblValue){ tblSel.selectedIndex = i; break; }
      }
    }
    if (tblSel && colSel){
      fetchCols(tblSel.value, colSel, s.value);
    }
  });

  wireInteractions();
}

/* ---------------- columns fetch ---------------- */
function fetchCols(tbl, colSel, preselect){
  if (!tbl || tbl === 'all'){
    colSel.innerHTML = '<option value="">— عمود —</option>';
    return;
  }
  if (COLUMN_CACHE[tbl]){
    fillCols(colSel, COLUMN_CACHE[tbl], preselect);
    return;
  }
  fetch('/api/settings/columns/' + encodeURIComponent(tbl), {credentials:'include'})
    .then(function(r){return r.json();})
    .then(function(d){
      var cols = d.columns || [];
      COLUMN_CACHE[tbl] = cols;
      fillCols(colSel, cols, preselect);
    });
}
function fillCols(colSel, cols, preselect){
  var html = '<option value="">— عمود —</option>';
  for (var i=0;i<cols.length;i++){
    var c = cols[i];
    var n = (c && typeof c === 'object') ? c.name  : String(c);
    var l = (c && typeof c === 'object') ? (c.label || c.name) : String(c);
    var sel = (preselect && n === preselect) ? ' selected' : '';
    html += '<option value="' + escAttr(n) + '"' + sel + '>' + l + '</option>';
  }
  colSel.innerHTML = html;
}

/* component keys are always ASCII identifiers (letters/digits/underscore), */
/* so no CSS escaping is needed for [data-component="..."] selectors. */
function cssEscape(s){ return String(s); }

/* ---------------- interactions ---------------- */
function wireInteractions(){
  /* hover bidirectional highlight + click-to-jump */
  var ws = document.getElementById('workspace');
  ws.addEventListener('mouseover', function(e){
    var t = e.target.closest('[data-component]');
    if (!t) return;
    setHighlight(t.getAttribute('data-component'), true);
  });
  ws.addEventListener('mouseout', function(e){
    var t = e.target.closest('[data-component]');
    if (!t) return;
    setHighlight(t.getAttribute('data-component'), false);
  });
  ws.addEventListener('click', function(e){
    var b = e.target.closest('.badge');
    if (b){
      var comp = b.getAttribute('data-component');
      var card = document.querySelector('.card[data-component="' + cssEscape(comp) + '"]');
      if (card){
        card.scrollIntoView({behavior:'smooth', block:'center'});
        card.classList.add('hl');
        setTimeout(function(){ card.classList.remove('hl'); }, 1500);
      }
    }
  });

  /* change handlers on selects: auto-save */
  ws.addEventListener('change', function(e){
    var sel = e.target;
    if (!sel || sel.tagName !== 'SELECT') return;
    var role = sel.getAttribute('data-role');
    var comp = sel.getAttribute('data-component');
    if (!comp) return;
    var card = sel.closest('.card');
    if (!card) return;
    if (role === 'tbl'){
      if (isColumnComponent(comp)){
        /* table changed; repopulate columns, don't save yet */
        var colSel = card.querySelector('select[data-role="col"]');
        if (colSel){ fetchCols(sel.value, colSel, ''); }
      } else {
        /* plain table setting: save the table value */
        saveSetting(CURRENT_PAGE, comp, sel.value, card);
      }
    } else if (role === 'col'){
      saveSetting(CURRENT_PAGE, comp, sel.value, card);
    }
  });
}

function setHighlight(comp, on){
  var sel = '[data-component="' + cssEscape(comp) + '"]';
  var els = document.querySelectorAll(sel);
  for (var i=0;i<els.length;i++){
    if (on) els[i].classList.add('hl');
    else els[i].classList.remove('hl');
  }
}

/* ---------------- save ---------------- */
function saveSetting(page, component, value, card){
  fetch('/api/settings', {
    method:'PATCH',
    headers:{'Content-Type':'application/json'},
    credentials:'include',
    body: JSON.stringify({page:page, component:component, value:value})
  }).then(function(r){return r.json();}).then(function(d){
    if (d.ok){
      /* update local cache */
      var arr = SETTINGS[page] || [];
      for (var i=0;i<arr.length;i++){ if (arr[i].component === component){ arr[i].value = value; break; } }
      /* check animation on card */
      var chk = card.querySelector('.check');
      if (chk){
        chk.classList.add('show');
        setTimeout(function(){ chk.classList.remove('show'); }, 1600);
      }
      toast('تم الحفظ ✓', false);
    } else {
      toast((d.error || 'خطأ'), true);
    }
  }).catch(function(){ toast('خطأ في الاتصال', true); });
}

/* ---------------- toast ---------------- */
var toastTimer = null;
function toast(msg, isErr){
  var el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show' + (isErr ? ' err' : '');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(function(){ el.className = 'toast' + (isErr ? ' err' : ''); }, 1800);
}

loadAll();
</script>
</body>
</html>"""


def login_required(f):
    @wraps(f)
    def dec(*a, **k):
        if "user" not in session:
            return redirect("/")
        return f(*a, **k)
    return dec

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mindex</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Tahoma,Arial,sans-serif;}
body{background:linear-gradient(135deg,#f3eeff 0%,#e8f8fb 100%);display:flex;align-items:center;justify-content:center;min-height:100vh;}
.box{background:#fff;border:1px solid #E0D5F0;border-radius:20px;padding:40px 36px;width:380px;box-shadow:0 8px 40px rgba(107,63,160,0.13);}
.logo-area{display:flex;flex-direction:column;align-items:center;gap:6px;margin-bottom:32px;}
.logo-circle{width:110px;height:110px;border-radius:50%;border:3px solid #6B3FA0;background:#fff;display:flex;align-items:center;justify-content:center;}
.logo-circle svg{width:90px;height:90px;}
.centre-name{font-size:15px;font-weight:800;color:#6B3FA0;text-align:center;line-height:1.4;}
.centre-slogan{font-size:12px;color:#00BCD4;font-weight:600;text-align:center;}
label{display:block;text-align:right;font-size:13px;color:#6B3FA0;margin-bottom:6px;font-weight:600;}
input{width:100%;padding:12px 14px;border:1.5px solid #E0D5F0;border-radius:10px;font-size:14px;margin-bottom:16px;outline:none;background:#faf7ff;}
input:focus{border-color:#6B3FA0;background:#fff;}
button{width:100%;padding:13px;background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:700;cursor:pointer;}
.err{background:#fee;color:#c00;padding:10px;border-radius:8px;margin-bottom:12px;text-align:center;font-size:13px;}
</style>
</head>
<body>
<div class="box">
<div class="logo-area">
<div class="logo-circle">
<svg viewBox="0 0 90 90" xmlns="http://www.w3.org/2000/svg">
<rect x="12" y="48" width="66" height="30" rx="4" fill="#00BCD4"/>
<ellipse cx="45" cy="36" rx="18" ry="16" fill="#9C5BB5"/>
<polygon points="33,18 38,10 45,16 52,10 57,18 33,18" fill="#FFD700"/>
<path d="M40 42 Q45 47 50 42" stroke="#7B3FA0" stroke-width="1.5" fill="none" stroke-linecap="round"/>
<circle cx="41" cy="39" r="1.5" fill="#7B3FA0"/>
<circle cx="49" cy="39" r="1.5" fill="#7B3FA0"/>
</svg>
</div>
<div class="centre-name">MINDEX EDUCATION<br>&amp; TRAINING CENTRE</div>
<div class="centre-slogan">Play &middot; Enjoy &middot; Learn</div>
</div>
ERROR_PLACEHOLDER
<form method="POST" action="/login">
<label>&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x62E;&#x62F;&#x645;</label>
<input type="text" name="username" placeholder="username" required>
<label>&#x643;&#x644;&#x645;&#x629; &#x627;&#x644;&#x645;&#x631;&#x648;&#x631;</label>
<input type="password" name="password" placeholder="password" required>
<button type="submit">&#x62F;&#x62E;&#x648;&#x644; &larr;</button>
</form>
</div>
</body>
</html>"""

HOME_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mindex</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Tahoma,Arial,sans-serif;}
body{background:linear-gradient(135deg,#f8f4ff 0%,#e8f8fb 100%);min-height:100vh;direction:rtl;}
.dh-topbar{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;padding:16px 32px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 4px 16px rgba(107,63,160,.15);}
.dh-topbar-title{font-size:22px;font-weight:800;display:flex;align-items:center;gap:12px;}
.dh-topbar-right{display:flex;align-items:center;gap:12px;font-size:14px;}
.dh-logout{background:rgba(255,255,255,.18);color:#fff;border:1.5px solid rgba(255,255,255,.5);padding:7px 16px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:600;}
.dh-logout:hover{background:rgba(255,255,255,.3);}
.dh-main{padding:28px 32px;max-width:1400px;margin:0 auto;}
.dh-section-title{font-size:20px;font-weight:800;color:#4a148c;margin:8px 0 16px;display:flex;align-items:center;gap:10px;}
.dh-section-title:not(:first-child){margin-top:32px;}
.dh-stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:18px;}
.dh-stat-card{background:#fff;border-radius:14px;padding:20px 18px 18px 22px;box-shadow:0 3px 12px rgba(0,0,0,.06);display:flex;flex-direction:column;gap:6px;position:relative;overflow:hidden;transition:transform .15s,box-shadow .15s;border:1px solid #eee;}
.dh-stat-card:hover{transform:translateY(-2px);box-shadow:0 6px 22px rgba(0,0,0,.09);}
.dh-stat-card::before{content:'';position:absolute;top:0;right:0;width:5px;height:100%;background:#6B3FA0;}
.dh-stat-card.purple::before{background:linear-gradient(180deg,#6B3FA0,#8B5CC8);}
.dh-stat-card.teal::before{background:linear-gradient(180deg,#00897B,#26A69A);}
.dh-stat-card.orange::before{background:linear-gradient(180deg,#E65100,#FB8C00);}
.dh-stat-card.blue::before{background:linear-gradient(180deg,#1565C0,#1E88E5);}
.dh-stat-card.red::before{background:linear-gradient(180deg,#c0392b,#e74c3c);}
.dh-stat-card.green::before{background:linear-gradient(180deg,#2E7D32,#43A047);}
.dh-stat-card.pink::before{background:linear-gradient(180deg,#AD1457,#EC407A);}
.dh-stat-card.indigo::before{background:linear-gradient(180deg,#3F51B5,#5C6BC0);}
.dh-stat-top{display:flex;align-items:center;justify-content:space-between;gap:8px;}
.dh-stat-icon{font-size:26px;opacity:.85;}
.dh-stat-number{font-size:32px;font-weight:800;color:#222;line-height:1.1;font-variant-numeric:tabular-nums;}
.dh-stat-label{font-size:13px;color:#666;font-weight:600;}
.dh-actions-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;}
.dh-action-card{color:#fff;border-radius:16px;padding:24px 22px;text-decoration:none;display:flex;flex-direction:column;gap:6px;min-height:130px;box-shadow:0 4px 16px rgba(107,63,160,.15);cursor:pointer;border:none;transition:transform .15s,box-shadow .15s;font-family:inherit;text-align:right;font-size:inherit;}
.dh-action-card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(107,63,160,.25);}
.dh-action-icon{font-size:32px;}
.dh-action-title{font-size:18px;font-weight:800;}
.dh-action-desc{font-size:12.5px;font-weight:500;opacity:.92;margin-top:2px;}
.dh-a-purple{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);}
.dh-a-teal{background:linear-gradient(135deg,#00897B,#26A69A);}
.dh-a-orange{background:linear-gradient(135deg,#E65100,#FB8C00);}
.dh-a-blue{background:linear-gradient(135deg,#1565C0,#1E88E5);}
.dh-a-green{background:linear-gradient(135deg,#2E7D32,#43A047);}
.dh-a-search{background:linear-gradient(135deg,#00695C,#4DB6AC);}
@media (max-width: 768px){
  .dh-main{padding:20px 14px;}
  .dh-stats-grid,.dh-actions-grid{grid-template-columns:1fr 1fr;gap:12px;}
  .dh-stat-number{font-size:24px;}
  .dh-topbar{padding:14px 16px;}
  .dh-topbar-title{font-size:17px;}
}
@media (max-width: 460px){
  .dh-stats-grid,.dh-actions-grid{grid-template-columns:1fr;}
}
/* Student-search modal */
.srm-header{background:linear-gradient(135deg,#00897B,#4DB6AC);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;}
.srm-header span{color:#fff;font-size:1.2rem;font-weight:bold;}
.srm-close{color:#fff;font-size:1.8rem;cursor:pointer;line-height:1;}
.srm-search{padding:14px 20px;background:#e0f2f1;border-bottom:1px solid #b2dfdb;}
.srm-search input{width:100%;padding:10px 14px;border-radius:10px;border:1.5px solid #4DB6AC;font-size:1rem;background:#fff;outline:none;}
.srm-body{padding:14px 20px;max-height:70vh;overflow:auto;}
.srm-result{padding:10px 12px;border:1px solid #e0e0e0;border-radius:10px;margin-bottom:6px;cursor:pointer;background:#fafafa;transition:all .15s;}
.srm-result:hover{background:#e0f2f1;border-color:#4DB6AC;}
.srm-result-name{font-weight:700;color:#00695C;}
.srm-result-meta{font-size:0.85em;color:#555;margin-top:2px;}
.srm-card{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:0;}
.srm-section{padding:14px 18px;border-bottom:1px solid #eee;}
.srm-section:last-child{border-bottom:none;}
.srm-section-title{font-weight:700;color:#00695C;font-size:1.05em;margin-bottom:10px;display:flex;align-items:center;gap:6px;}
.srm-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;}
.srm-field{display:flex;flex-direction:column;gap:3px;}
.srm-field label{font-size:0.82em;color:#607D8B;font-weight:600;}
.srm-field input,.srm-field select{padding:7px 10px;border:1.2px solid #b2dfdb;border-radius:8px;font-size:0.95rem;background:#fafafa;outline:none;}
.srm-field input:focus,.srm-field select:focus{background:#fff;border-color:#4DB6AC;}
.srm-readonly{background:#eceff1 !important;color:#455A64;}
.srm-totals{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px;}
.srm-stat{background:#f5f5f5;padding:10px;border-radius:8px;text-align:center;}
.srm-stat-num{font-size:1.3em;font-weight:700;color:#00695C;}
.srm-stat-lbl{font-size:0.8em;color:#607D8B;margin-top:2px;}
.srm-actions{padding:12px 18px;border-top:1px solid #eee;text-align:center;display:flex;gap:10px;justify-content:center;}
.srm-save{padding:10px 32px;background:linear-gradient(135deg,#00897B,#4DB6AC);color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;}
.srm-cancel{padding:10px 24px;background:#eceff1;color:#455A64;border:none;border-radius:10px;font-weight:600;cursor:pointer;}
.srm-pct-bar{height:6px;background:#eee;border-radius:3px;overflow:hidden;margin-top:4px;}
.srm-pct-bar-inner{height:100%;background:#4DB6AC;}
.ss-groups-trigger{width:100%;padding:9px 12px;border-radius:9px;border:1.5px solid #FB8C00;background:#fff;font-size:0.95rem;font-weight:600;color:#3e2723;cursor:pointer;text-align:right;}.ss-groups-trigger:hover{background:#fff8f0;}.ss-groups-trigger.open{border-color:#E65100;box-shadow:0 0 0 3px rgba(230,81,0,0.15);}.ss-groups-panel{position:absolute;top:calc(100% + 4px);right:0;left:0;background:#fff;border:1.5px solid #FB8C00;border-radius:10px;box-shadow:0 6px 18px rgba(230,81,0,0.2);z-index:1000;padding:10px;max-height:320px;overflow:auto;}.ss-groups-search{width:100%;padding:7px 10px;border:1px solid #ffcc80;border-radius:7px;font-size:0.88rem;margin-bottom:8px;direction:rtl;}.ss-groups-all-row{display:flex;align-items:center;gap:8px;padding:8px 10px;background:#fff3e0;border:1px dashed #FB8C00;border-radius:8px;font-weight:800;color:#E65100;cursor:pointer;margin-bottom:8px;user-select:none;}.ss-groups-list{display:flex;flex-direction:column;gap:4px;}.ss-groups-item{display:flex;align-items:center;gap:8px;padding:6px 10px;border-radius:6px;cursor:pointer;user-select:none;font-size:0.92rem;color:#3e2723;}.ss-groups-item:hover{background:#fff8f0;}.ss-groups-item input{accent-color:#E65100;cursor:pointer;}.ss-groups-empty{padding:14px;text-align:center;color:#999;font-size:0.88rem;}

/* ---- Student-search edit protection ---- */
.srm-field .srm-lock{font-size:0.9em;margin-right:4px;color:#9e9e9e;}
.srm-field.edit .srm-lock{color:#2E7D32;}
.srm-readonly{background:#eceff1 !important;color:#455A64;cursor:not-allowed;border-color:#cfd8dc !important;}
.srm-edit-banner{display:none;background:linear-gradient(135deg,#fffde7,#fff59d);border:1.5px dashed #f57f17;color:#795548;padding:10px 14px;border-radius:10px;margin:0 18px 8px 18px;font-weight:700;text-align:center;}
.srm-edit-banner.show{display:block;}
.srm-btn-edit{padding:10px 28px;background:#e67e22;color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;}
.srm-btn-edit:hover{background:#d35400;}
.srm-btn-save{padding:10px 28px;background:#27ae60;color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;}
.srm-btn-save:hover{background:#229954;}
.srm-btn-cancel-edit{padding:10px 24px;background:#e74c3c;color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;}
.srm-btn-cancel-edit:hover{background:#c0392b;}
.srm-btn-delete{padding:10px 24px;background:#8e44ad;color:#fff;border:none;border-radius:10px;font-weight:700;cursor:pointer;}
.srm-btn-delete:hover{background:#6c3483;}
/* Typed-confirmation modal */
.srm-type-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:100001;align-items:center;justify-content:center;direction:rtl;}
.srm-type-bg.open{display:flex;}
.srm-type-box{background:#fff;border-radius:14px;padding:26px 28px;max-width:440px;width:92%;box-shadow:0 14px 44px rgba(0,0,0,.3);text-align:center;}
.srm-type-box h3{color:#c62828;font-size:1.1rem;font-weight:800;margin-bottom:10px;}
.srm-type-box p{color:#555;font-size:0.92rem;margin-bottom:12px;}
.srm-type-expected{display:block;background:#fce4ec;border:1px dashed #e57373;color:#b71c1c;font-weight:800;padding:8px;border-radius:8px;margin-bottom:12px;}
.srm-type-input{width:100%;padding:10px 12px;border:2px solid #e74c3c;border-radius:9px;font-size:0.95rem;direction:rtl;margin-bottom:14px;}
.srm-type-actions{display:flex;gap:10px;justify-content:center;}
/* Change-log review modal */
.srm-log-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:100001;align-items:center;justify-content:center;direction:rtl;}
.srm-log-bg.open{display:flex;}
.srm-log-box{background:#fff;border-radius:14px;max-width:560px;width:94%;max-height:80vh;overflow:auto;box-shadow:0 14px 44px rgba(0,0,0,.3);}
.srm-log-head{background:linear-gradient(135deg,#E65100,#FB8C00);color:#fff;padding:14px 20px;font-weight:800;font-size:1.05rem;}
.srm-log-body{padding:14px 20px;color:#333;}
.srm-log-item{padding:8px 10px;border-bottom:1px dashed #eee;font-size:0.92rem;}
.srm-log-item .srm-log-field{font-weight:800;color:#E65100;}
.srm-log-item .srm-log-from{color:#c62828;text-decoration:line-through;margin:0 4px;}
.srm-log-item .srm-log-to{color:#2E7D32;font-weight:700;margin:0 4px;}
.srm-log-actions{padding:12px 20px;border-top:1px solid #eee;display:flex;gap:10px;justify-content:center;background:#fff9f2;}
.srm-auto-lock-banner{display:none;position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#455a64;color:#fff;padding:10px 20px;border-radius:10px;font-weight:700;font-size:0.92rem;box-shadow:0 4px 14px rgba(0,0,0,.25);z-index:100002;}
.srm-auto-lock-banner.show{display:block;}

</style>
</head>
<body>
<div class="dh-topbar">
  <div class="dh-topbar-title">&#x1F393; MINDEX EDUCATION &amp; TRAINING CENTRE</div>
  <div class="dh-topbar-right">
    <span>&#x645;&#x631;&#x62D;&#x628;&#x627;&#x64B; <b>USER_PLACEHOLDER</b></span>
    <a href="/settings" class="dh-logout" style="background:linear-gradient(135deg,#6B3FA0,#8B5CC8);margin-left:8px;">&#9881; &#x625;&#x639;&#x62F;&#x627;&#x62F;&#x627;&#x62A;</a>
    <a href="/api/logout" class="dh-logout">&#x62E;&#x631;&#x648;&#x62C;</a>
  </div>
</div>
<div class="dh-main">
  <div class="dh-section-title">&#x1F4CA; &#x625;&#x62D;&#x635;&#x627;&#x626;&#x64A;&#x627;&#x62A;</div>
  <div class="dh-stats-grid">
    <div class="dh-stat-card teal">
      <div class="dh-stat-top"><span class="dh-stat-icon">&#x1F1EC;&#x1F1E7;</span></div>
      <div class="dh-stat-number" id="stat-english-students">&ndash;</div>
      <div class="dh-stat-label">&#x637;&#x644;&#x627;&#x628; &#x627;&#x644;&#x625;&#x646;&#x62C;&#x644;&#x64A;&#x632;&#x64A;</div>
    </div>
    <div class="dh-stat-card purple">
      <div class="dh-stat-top"><span class="dh-stat-icon">&#x1F9EE;</span></div>
      <div class="dh-stat-number" id="stat-math-students">&ndash;</div>
      <div class="dh-stat-label">&#x637;&#x644;&#x627;&#x628; &#x627;&#x644;&#x631;&#x64A;&#x627;&#x636;&#x64A;&#x627;&#x62A;</div>
    </div>
    <div class="dh-stat-card blue">
      <div class="dh-stat-top"><span class="dh-stat-icon">&#x1F465;</span></div>
      <div class="dh-stat-number" id="stat-groups">&ndash;</div>
      <div class="dh-stat-label">&#x639;&#x62F;&#x62F; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</div>
    </div>
    <div class="dh-stat-card green">
      <div class="dh-stat-top"><span class="dh-stat-icon">&#x1F468;&#x200D;&#x1F3EB;</span></div>
      <div class="dh-stat-number" id="stat-teachers">&ndash;</div>
      <div class="dh-stat-label">&#x639;&#x62F;&#x62F; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;&#x64A;&#x646;</div>
    </div>
    <div class="dh-stat-card orange">
      <div class="dh-stat-top"><span class="dh-stat-icon">&#x1F4BC;</span></div>
      <div class="dh-stat-number" id="stat-staff">&ndash;</div>
      <div class="dh-stat-label">&#x639;&#x62F;&#x62F; &#x627;&#x644;&#x645;&#x648;&#x638;&#x641;&#x64A;&#x646;</div>
    </div>
    <div class="dh-stat-card pink">
      <div class="dh-stat-top"><span class="dh-stat-icon">&#x1F4D8;</span></div>
      <div class="dh-stat-number" id="stat-english-levels">&ndash;</div>
      <div class="dh-stat-label">&#x645;&#x633;&#x62A;&#x648;&#x64A;&#x627;&#x62A; &#x627;&#x644;&#x625;&#x646;&#x62C;&#x644;&#x64A;&#x632;&#x64A;</div>
    </div>
    <div class="dh-stat-card indigo">
      <div class="dh-stat-top"><span class="dh-stat-icon">&#x1F4C5;</span></div>
      <div class="dh-stat-number" id="stat-attendance-rate">&ndash;</div>
      <div class="dh-stat-label">&#x646;&#x633;&#x628;&#x629; &#x627;&#x644;&#x627;&#x644;&#x62A;&#x632;&#x627;&#x645; &#x628;&#x627;&#x644;&#x62D;&#x636;&#x648;&#x631;</div>
    </div>
    <div class="dh-stat-card red">
      <div class="dh-stat-top"><span class="dh-stat-icon">&#x26A0;&#xFE0F;</span></div>
      <div class="dh-stat-number" id="stat-violations">&ndash;</div>
      <div class="dh-stat-label">&#x639;&#x62F;&#x62F; &#x627;&#x644;&#x645;&#x62E;&#x627;&#x644;&#x641;&#x627;&#x62A;</div>
    </div>
  </div>

  <div class="dh-section-title">&#x26A1; &#x627;&#x644;&#x642;&#x648;&#x627;&#x626;&#x645; &#x627;&#x644;&#x631;&#x626;&#x64A;&#x633;&#x64A;&#x629;</div>
  <div class="dh-actions-grid">
    <a href="/database" class="dh-action-card dh-a-purple">
      <div class="dh-action-icon">&#x1F4C1;</div>
      <div class="dh-action-title">&#x642;&#x627;&#x639;&#x62F;&#x629; &#x627;&#x644;&#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;</div>
      <div class="dh-action-desc">&#x62C;&#x645;&#x64A;&#x639; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629; &#x648;&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</div>
    </a>
    <a href="/attendance" class="dh-action-card dh-a-teal">
      <div class="dh-action-icon">&#x1F4C5;</div>
      <div class="dh-action-title">&#x62A;&#x633;&#x62C;&#x64A;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</div>
      <div class="dh-action-desc">&#x625;&#x636;&#x627;&#x641;&#x629; &#x623;&#x648; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62D;&#x636;&#x648;&#x631;</div>
    </a>
    <button class="dh-action-card dh-a-purple" onclick="pmOpen()">
      <div class="dh-action-icon">&#x1F4B3;</div>
      <div class="dh-action-title">&#x645;&#x62A;&#x627;&#x628;&#x639;&#x629; &#x627;&#x644;&#x62F;&#x641;&#x639;</div>
      <div class="dh-action-desc">&#x625;&#x62F;&#x627;&#x631;&#x629; &#x627;&#x644;&#x623;&#x642;&#x633;&#x627;&#x637; &#x648;&#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639;&#x627;&#x62A;</div>
    </button>
    <button class="dh-action-card dh-a-orange" onclick="ssOpen()">
      <div class="dh-action-icon">&#x1F4CA;</div>
      <div class="dh-action-title">&#x645;&#x644;&#x62E;&#x635; &#x627;&#x644;&#x62D;&#x635;&#x635;</div>
      <div class="dh-action-desc">&#x639;&#x62F;&#x62F; &#x627;&#x644;&#x62D;&#x635;&#x635; &#x648;&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x648;&#x642;&#x62A;</div>
    </button>
    <button class="dh-action-card dh-a-blue" onclick="sdOpen()">
      <div class="dh-action-icon">&#x23F1;&#xFE0F;</div>
      <div class="dh-action-title">&#x645;&#x62F;&#x629; &#x627;&#x644;&#x62D;&#x635;&#x635;</div>
      <div class="dh-action-desc">&#x62A;&#x62D;&#x62F;&#x64A;&#x62F; &#x648;&#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x645;&#x62F;&#x629; &#x643;&#x644; &#x62D;&#x635;&#x629;</div>
    </button>
    <button class="dh-action-card dh-a-search" onclick="srOpen()">
      <div class="dh-action-icon">&#x1F50D;</div>
      <div class="dh-action-title">&#x628;&#x62D;&#x62B; &#x639;&#x646; &#x637;&#x627;&#x644;&#x628;</div>
      <div class="dh-action-desc">&#x628;&#x62D;&#x62B; &#x633;&#x631;&#x64A;&#x639; &#x628;&#x627;&#x644;&#x627;&#x633;&#x645; &#x623;&#x648; &#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A;</div>
    </button>
    <button class="dh-action-card dh-a-green" onclick="msgOpen()">
      <div class="dh-action-icon">&#x1F4E9;</div>
      <div class="dh-action-title">&#x625;&#x631;&#x633;&#x627;&#x644; &#x627;&#x644;&#x631;&#x633;&#x627;&#x626;&#x644;</div>
      <div class="dh-action-desc">&#x642;&#x648;&#x627;&#x644;&#x628; &#x631;&#x633;&#x627;&#x626;&#x644; &#x648;&#x627;&#x62A;&#x633;&#x627;&#x628; &#x644;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</div>
    </button>
  </div>
</div>

<div id="sr-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:9999;overflow:auto;">
  <div style="background:#fff;margin:20px auto;border-radius:14px;max-width:760px;width:95%;padding:0;overflow:hidden;box-shadow:0 8px 32px rgba(0,137,123,0.25);">
    <div class="srm-header"><span>&#x1F50D; &#x628;&#x62D;&#x62B; &#x639;&#x646; &#x637;&#x627;&#x644;&#x628;</span><span class="srm-close" onclick="srClose()">&times;</span></div>
    <div class="srm-search">
      <input id="sr-query" type="text" oninput="srFilter()" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x644;&#x627;&#x633;&#x645; &#x623;&#x648; &#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A;&#x2026;">
    </div>
    <div class="srm-body">
      <div id="sr-results"></div>
      <div id="sr-details" style="margin-top:10px;"></div>
    </div>
  </div>
</div>

<div id="ss-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:9999;overflow:auto;"><div style="background:#fff;margin:40px auto;border-radius:14px;max-width:980px;width:94%;padding:0;overflow:hidden;box-shadow:0 8px 32px rgba(230,81,0,0.25);"><div style="background:linear-gradient(135deg,#E65100,#FB8C00);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#fff;font-size:1.2rem;font-weight:bold;">&#x1F4CA; &#x645;&#x644;&#x62E;&#x635; &#x627;&#x644;&#x62D;&#x635;&#x635;</span><span onclick="document.getElementById('ss-modal').style.display='none'" style="color:#fff;font-size:1.8rem;cursor:pointer;line-height:1;">&times;</span></div><div style="padding:14px 20px;background:#fff8f0;border-bottom:1px solid #ffe0b2;display:grid;grid-template-columns:1fr 1fr auto;gap:14px;align-items:end;"><div style="position:relative;"><label style="display:block;font-weight:bold;color:#E65100;margin-bottom:6px;font-size:0.9rem;">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</label><button type="button" id="ss-groups-btn" class="ss-groups-trigger">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x2014;</button><div id="ss-groups-panel" class="ss-groups-panel" style="display:none;"><input id="ss-groups-search" class="ss-groups-search" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x639;&#x646; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;..."><label class="ss-groups-all-row"><input type="checkbox" id="ss-groups-all"> &#x62C;&#x645;&#x64A;&#x639; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</label><div id="ss-groups-list" class="ss-groups-list"></div></div></div><div><label style="display:block;font-weight:bold;color:#E65100;margin-bottom:6px;font-size:0.9rem;">&#x1F50D; &#x628;&#x62D;&#x62B; &#x639;&#x646; &#x637;&#x627;&#x644;&#x628;</label><input id="ss-search" type="text" oninput="ssOnSearch()" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x641;&#x64A; &#x643;&#x644; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;..." style="width:100%;padding:9px 12px;border-radius:9px;border:1.5px solid #FB8C00;background:#fff;font-size:0.95rem;direction:rtl;"></div><div><button onclick="ssOpenAllGroups()" style="background:linear-gradient(135deg,#6A1B9A,#AB47BC);color:#fff;border:none;padding:10px 16px;border-radius:10px;font-size:0.9rem;font-weight:800;cursor:pointer;white-space:nowrap;">&#x1F4CA; &#x645;&#x644;&#x62E;&#x635; &#x62C;&#x645;&#x64A;&#x639; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</button></div></div><div id="ss-body" style="padding:18px 22px;max-height:70vh;overflow:auto;font-size:1.05rem;color:#333;"></div></div></div>

<div id="sd-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:9999;overflow:auto;"><div style="background:#fff;margin:40px auto;border-radius:14px;max-width:560px;width:92%;padding:0;overflow:hidden;box-shadow:0 8px 32px rgba(21,101,192,0.25);"><div style="background:linear-gradient(135deg,#1565C0,#1E88E5);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#fff;font-size:1.2rem;font-weight:bold;">&#x23F1;&#xFE0F; &#x645;&#x62F;&#x629; &#x627;&#x644;&#x62D;&#x635;&#x635;</span><span onclick="document.getElementById('sd-modal').style.display='none'" style="color:#fff;font-size:1.8rem;cursor:pointer;line-height:1;">&times;</span></div><div style="padding:14px 20px;background:#e3f2fd;border-bottom:1px solid #bbdefb;"><label style="display:block;font-weight:bold;color:#0d47a1;margin-bottom:6px;">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label><select id="sd-group" onchange="sdLoadDates()" style="width:100%;padding:8px 12px;border-radius:8px;border:1.5px solid #1E88E5;font-size:0.95rem;"><option value="">&mdash; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &mdash;</option></select></div><div id="sd-body" style="padding:14px 20px;max-height:55vh;overflow:auto;font-size:0.95rem;color:#333;"></div><div id="sd-footer" style="padding:12px 20px;border-top:1px solid #eee;text-align:center;display:none;"><button id="sd-save" onclick="sdSave()" style="padding:10px 36px;background:linear-gradient(135deg,#1565C0,#1E88E5);color:#fff;border:none;border-radius:10px;font-size:1rem;font-weight:700;cursor:pointer;">&#x62D;&#x641;&#x638;</button></div></div></div>

<script>
function _fmtHM(m){
  m=parseInt(m||0,10);if(!m)return"";
  var h=Math.floor(m/60),r=m%60,s="";
  if(h)s+=h+" \u0633\u0627\u0639\u0629";
  if(r)s+=(s?" ":"")+r+" \u062F\u0642\u064A\u0642\u0629";
  return s;
}
function dhLoadStats(){
  fetch('/api/dashboard/stats').then(function(r){return r.json();}).then(function(d){
    function set(id, v){ var el = document.getElementById(id); if (el) el.textContent = v; }
    set('stat-english-students', d.english_students || 0);
    set('stat-math-students',    d.math_students || 0);
    set('stat-groups',           d.groups || 0);
    set('stat-teachers',         d.teachers || 0);
    set('stat-staff',            d.staff || 0);
    set('stat-english-levels',   d.english_levels || 0);
    set('stat-attendance-rate',  (d.attendance_rate || 0) + '%');
    set('stat-violations',       d.violations || 0);
  }).catch(function(){
    // leave placeholders; not fatal
  });
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', dhLoadStats);
else dhLoadStats();
function _ssFmtH(v){
  var n=parseFloat(v||0);if(!n&&n!==0)return"0";
  if(Math.abs(n-Math.round(n))<0.01) return String(Math.round(n));
  return n.toFixed(1);
}
/* Render minutes as "X ساعة Y دقيقة" per the spec. */
function _ssFmtMin(m){
  m = parseInt(m||0, 10);
  if (!m || m < 0) return '0 دقيقة';
  var h = Math.floor(m/60), r = m%60, out = '';
  if (h) out += h + ' ساعة';
  if (r) out += (out?' ':'') + r + ' دقيقة';
  return out || '0 دقيقة';
}
/* Compact "HH:MM" for the all-groups table. */
function _ssFmtHHMM(m){
  m = parseInt(m||0, 10);
  if (!m || m < 0) return '0:00';
  var h = Math.floor(m/60), r = m%60;
  return h + ':' + (r < 10 ? '0'+r : r);
}
function _ssRateColor(p){
  var n = parseFloat(p||0);
  if (n >= 90) return '#2E7D32';
  if (n >= 75) return '#F9A825';
  if (n >= 50) return '#EF6C00';
  return '#c62828';
}
function _ssTableHead(){
  return ''
    + '<thead>'
    +   '<tr style="background:linear-gradient(135deg,#E65100,#FB8C00);color:#fff;">'
    +     '<th style="padding:10px 12px;text-align:right;font-size:0.85rem;">اسم الطالب</th>'
    +     '<th style="padding:10px 12px;text-align:right;font-size:0.85rem;">المجموعة</th>'
    +     '<th style="padding:10px 12px;text-align:center;font-size:0.85rem;">إجمالي الحصص</th>'
    +     '<th style="padding:10px 12px;text-align:center;font-size:0.85rem;">إجمالي الساعات</th>'
    +     '<th style="padding:10px 12px;text-align:center;font-size:0.85rem;">حضر (عدد / ساعات)</th>'
    +     '<th style="padding:10px 12px;text-align:center;font-size:0.85rem;">غاب (عدد / ساعات)</th>'
    +     '<th style="padding:10px 12px;text-align:center;font-size:0.85rem;">متأخر</th>'
    +     '<th style="padding:10px 12px;text-align:center;font-size:0.85rem;">نسبة الحضور</th>'
    +   '</tr>'
    + '</thead>';
}
function _ssRow(r){
  var rate = parseFloat(r.rate_pct||0);
  var color = _ssRateColor(rate);
  return ''
    + '<tr>'
    +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;font-weight:700;color:#3e2723;text-align:right;">' + (r.student_name||'') + '</td>'
    +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;color:#5d4037;font-size:0.88rem;">' + (r.group_name||'') + '</td>'
    +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:800;color:#1565C0;">' + (r.total_sessions||0) + '</td>'
    +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:700;color:#1565C0;font-size:0.85rem;">' + _ssFmtMin(r.hours_total_min) + '</td>'
    +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:700;color:#2E7D32;font-size:0.85rem;">' + (r.present||0) + ' <span style="color:#888;">&nbsp;/&nbsp;</span> ' + _ssFmtMin(r.hours_present_min) + '</td>'
    +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:700;color:#c62828;font-size:0.85rem;">' + (r.absent||0) + ' <span style="color:#888;">&nbsp;/&nbsp;</span> ' + _ssFmtMin(r.hours_absent_min) + '</td>'
    +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:700;color:#E65100;font-size:0.85rem;">' + (r.late||0) + '</td>'
    +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:800;color:' + color + ';">' + rate.toFixed(1) + '%</td>'
    + '</tr>';
}
function _ssRenderStudents(list, headerHtml){
  var body = document.getElementById('ss-body');
  var html = headerHtml || '';
  if (!list || !list.length){
    html += '<div style="padding:24px;text-align:center;color:#888;font-weight:700;">لا توجد بيانات</div>';
    body.innerHTML = html;
    return;
  }
  html += '<div style="overflow:auto;border:1px solid #ffe0b2;border-radius:10px;">';
  html += '<table style="width:100%;border-collapse:collapse;background:#fff;">';
  html += _ssTableHead();
  html += '<tbody>';
  list.forEach(function(r){ html += _ssRow(r); });
  html += '</tbody></table></div>';
  body.innerHTML = html;
}
/* Rich student-search card. Used when the fuzzy search returns matches. */
function _ssRenderStudentCards(list){
  var body = document.getElementById('ss-body');
  if (!list || !list.length){
    body.innerHTML = '<div style="padding:30px;text-align:center;color:#c62828;font-weight:700;">لم يتم العثور على الطالب</div>';
    return;
  }
  var html = '<div style="background:linear-gradient(135deg,#e1f5fe,#b3e5fc);border:1px solid #81d4fa;border-radius:10px;padding:10px 14px;margin-bottom:12px;font-weight:700;color:#01579B;">ὐD نتائج البحث: ' + list.length + ' طالب</div>';
  list.forEach(function(r){
    var rate = parseFloat(r.rate_pct||0);
    var color = _ssRateColor(rate);
    html += '<div style="background:#fff;border:2px solid #ffcc80;border-radius:14px;padding:14px 18px;margin-bottom:12px;box-shadow:0 2px 8px rgba(230,81,0,0.08);">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px dashed #ffcc80;">';
    html +=   '<div style="font-weight:800;color:#3e2723;font-size:1.1rem;">Ἱ3 ' + (r.student_name||'') + '</div>';
    html +=   '<div style="font-weight:700;color:' + color + ';font-size:1.1rem;">' + rate.toFixed(1) + '%</div>';
    html += '</div>';
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;font-size:0.92rem;">';
    html +=   '<div style="background:#f3e5f5;border-radius:8px;padding:8px 10px;"><div style="color:#777;font-size:0.78rem;">المجموعة</div><div style="font-weight:700;color:#6A1B9A;">' + (r.group_name||'—') + '</div></div>';
    html +=   '<div style="background:#e3f2fd;border-radius:8px;padding:8px 10px;"><div style="color:#777;font-size:0.78rem;">إجمالي الحصص</div><div style="font-weight:800;color:#1565C0;">' + (r.total_sessions||0) + '</div></div>';
    html +=   '<div style="background:#e8f5e9;border-radius:8px;padding:8px 10px;"><div style="color:#777;font-size:0.78rem;">إجمالي الساعات</div><div style="font-weight:800;color:#2E7D32;">' + _ssFmtMin(r.hours_total_min) + '</div></div>';
    html +=   '<div style="background:#e8f5e9;border-radius:8px;padding:8px 10px;"><div style="color:#777;font-size:0.78rem;">حضر</div><div style="font-weight:700;color:#2E7D32;">' + (r.present||0) + ' — ' + _ssFmtMin(r.hours_present_min) + '</div></div>';
    html +=   '<div style="background:#fce4ec;border-radius:8px;padding:8px 10px;"><div style="color:#777;font-size:0.78rem;">غاب</div><div style="font-weight:700;color:#c62828;">' + (r.absent||0) + ' — ' + _ssFmtMin(r.hours_absent_min) + '</div></div>';
    html +=   '<div style="background:#fff3e0;border-radius:8px;padding:8px 10px;"><div style="color:#777;font-size:0.78rem;">متأخر</div><div style="font-weight:700;color:#E65100;">' + (r.late||0) + '</div></div>';
    html += '</div>';
    html += '</div>';
  });
  body.innerHTML = html;
}
var _ssAvailableGroups = [];
var _ssSelectedSet = {};
var _ssLoadTimer = null;

function _ssUpdateTriggerLabel(){
  var btn = document.getElementById('ss-groups-btn');
  if (!btn) return;
  var keys = Object.keys(_ssSelectedSet);
  var count = keys.length;
  var total = _ssAvailableGroups.length;
  if (!count){
    btn.textContent = '— اختر مجموعة —';
  } else if (count === total && total > 0){
    btn.textContent = 'جميع المجموعات (' + total + ')';
  } else if (count === 1){
    btn.textContent = keys[0];
  } else {
    var preview = keys.slice(0, 2).join('، ');
    btn.textContent = count + ' مجموعات: ' + preview + (count > 2 ? '…' : '');
  }
}

function _ssUpdateAllCheckboxState(){
  var master = document.getElementById('ss-groups-all');
  if (!master) return;
  var count = Object.keys(_ssSelectedSet).length;
  var total = _ssAvailableGroups.length;
  master.indeterminate = count > 0 && count < total;
  master.checked = count > 0 && count === total;
}

function _ssPopulateGroupsList(filterStr){
  var list = document.getElementById('ss-groups-list');
  if (!list) return;
  var q = (filterStr || '').trim().toLowerCase();
  var frag = document.createDocumentFragment();
  var shown = 0;
  _ssAvailableGroups.forEach(function(g){
    if (q && g.toLowerCase().indexOf(q) < 0) return;
    shown++;
    var row = document.createElement('label');
    row.className = 'ss-groups-item';
    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.dataset.group = g;
    cb.checked = !!_ssSelectedSet[g];
    cb.addEventListener('change', function(){
      if (cb.checked) _ssSelectedSet[g] = 1;
      else delete _ssSelectedSet[g];
      _ssUpdateTriggerLabel();
      _ssUpdateAllCheckboxState();
      _ssScheduleLoad();
    });
    var txt = document.createElement('span');
    txt.textContent = g;
    row.appendChild(cb);
    row.appendChild(txt);
    frag.appendChild(row);
  });
  list.innerHTML = '';
  if (!shown){
    var empty = document.createElement('div');
    empty.className = 'ss-groups-empty';
    empty.textContent = 'لا توجد مجموعات مطابقة';
    list.appendChild(empty);
  } else {
    list.appendChild(frag);
  }
}

function _ssGroupsOpenPanel(){
  var p = document.getElementById('ss-groups-panel');
  var b = document.getElementById('ss-groups-btn');
  if (!p || !b) return;
  p.style.display = 'block';
  b.classList.add('open');
  var s = document.getElementById('ss-groups-search');
  if (s){ s.value = ''; _ssPopulateGroupsList(''); setTimeout(function(){ s.focus(); }, 30); }
}

function _ssGroupsClosePanel(){
  var p = document.getElementById('ss-groups-panel');
  var b = document.getElementById('ss-groups-btn');
  if (!p || !b) return;
  p.style.display = 'none';
  b.classList.remove('open');
}

function _ssGroupsTogglePanel(){
  var p = document.getElementById('ss-groups-panel');
  if (!p) return;
  if (p.style.display === 'block') _ssGroupsClosePanel();
  else _ssGroupsOpenPanel();
}

function _ssDocClickClose(ev){
  var p = document.getElementById('ss-groups-panel');
  var b = document.getElementById('ss-groups-btn');
  if (!p || !b) return;
  if (p.style.display !== 'block') return;
  if (p.contains(ev.target) || b.contains(ev.target)) return;
  _ssGroupsClosePanel();
}

function _ssScheduleLoad(){
  clearTimeout(_ssLoadTimer);
  _ssLoadTimer = setTimeout(_ssLoadSelection, 220);
}

function _ssSelectedList(){
  return Object.keys(_ssSelectedSet);
}

function _ssLoadSelection(){
  var selected = _ssSelectedList();
  var body = document.getElementById('ss-body');
  // Clear any active student-search text so results don't mix.
  var qInp = document.getElementById('ss-search');
  if (qInp) qInp.value = '';
  if (!selected.length){
    body.innerHTML = '<div style="padding:30px;text-align:center;color:#888;font-weight:600;">اختر مجموعة لعرض الملخص</div>';
    return;
  }
  body.innerHTML = '<div style="padding:24px;text-align:center;color:#888;">جاري التحميل...</div>';
  var qs = selected.map(function(g){ return 'g=' + encodeURIComponent(g); }).join('&');
  fetch('/api/attendance/summary?view=groups&' + qs).then(function(r){ return r.json(); }).then(function(d){
    var total = _ssAvailableGroups.length;
    var label, chips;
    if (selected.length === 1){
      label = selected[0];
    } else if (selected.length === total && total > 0){
      label = 'جميع المجموعات (' + total + ')';
    } else {
      label = selected.length + ' مجموعات';
    }
    chips = selected.join('، ');
    var header = ''
      + '<div style="background:linear-gradient(135deg,#fff3e0,#ffe0b2);border:1px solid #ffcc80;border-radius:12px;padding:14px 18px;margin-bottom:12px;">'
      +   '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px;padding-bottom:8px;border-bottom:1px dashed #ffcc80;">'
      +     '<div style="font-weight:800;color:#E65100;font-size:1.05rem;">📊 ' + label + '</div>'
      +     '<div style="color:#5d4037;font-weight:700;font-size:0.9rem;">المجموعات المختارة: <span style="color:#6A1B9A;">' + chips + '</span></div>'
      +   '</div>'
      +   '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;font-size:0.92rem;">'
      +     '<div style="background:#fff;border-radius:8px;padding:8px 10px;border:1px solid #ffe0b2;"><div style="color:#777;font-size:0.78rem;">إجمالي الحصص</div><div style="font-weight:800;color:#1565C0;">' + (d.total_sessions||0) + '</div></div>'
      +     '<div style="background:#fff;border-radius:8px;padding:8px 10px;border:1px solid #ffe0b2;"><div style="color:#777;font-size:0.78rem;">إجمالي الساعات</div><div style="font-weight:800;color:#2E7D32;">' + _ssFmtMin(d.total_minutes) + '</div></div>'
      +     '<div style="background:#fff;border-radius:8px;padding:8px 10px;border:1px solid #ffe0b2;"><div style="color:#777;font-size:0.78rem;">عدد الطلبة</div><div style="font-weight:800;color:#6A1B9A;">' + (d.students_count || (d.students||[]).length || 0) + '</div></div>'
      +     '<div style="background:#fff;border-radius:8px;padding:8px 10px;border:1px solid #ffe0b2;"><div style="color:#777;font-size:0.78rem;">متوسط نسبة الحضور</div><div style="font-weight:800;color:' + _ssRateColor(d.avg_attendance_rate || 0) + ';">' + ((d.avg_attendance_rate || 0).toFixed ? (d.avg_attendance_rate||0).toFixed(1) : (d.avg_attendance_rate||0)) + '%</div></div>'
      +   '</div>'
      + '</div>';
    _ssRenderStudents(d.students, header);
  }).catch(function(){
    body.innerHTML = '<div style="padding:30px;text-align:center;color:#c62828;">خطأ في التحميل</div>';
  });
}

function ssOpen(){
  document.getElementById('ss-modal').style.display = 'block';
  var body = document.getElementById('ss-body');
  body.innerHTML = '<div style="padding:24px;text-align:center;color:#888;">جاري التحميل...</div>';
  fetch('/api/attendance/summary?view=init').then(function(r){ return r.json(); }).then(function(d){
    _ssAvailableGroups = d.groups || [];
    _ssSelectedSet = {};
    _ssPopulateGroupsList('');
    _ssUpdateTriggerLabel();
    _ssUpdateAllCheckboxState();
    document.getElementById('ss-search').value = '';
    body.innerHTML = '<div style="padding:30px;text-align:center;color:#888;font-weight:600;">اختر مجموعة لعرض الملخص</div>';
    _ssWireGroupsPicker();
  }).catch(function(){
    body.innerHTML = '<div style="padding:30px;text-align:center;color:#c62828;">خطأ في التحميل</div>';
  });
}

/* Back-compat shim: other dashboard cards used to call ssOnGroupChange. */
function ssOnGroupChange(){ _ssLoadSelection(); }

function _ssWireGroupsPicker(){
  var btn = document.getElementById('ss-groups-btn');
  if (btn && !btn._wired){
    btn._wired = true;
    btn.addEventListener('click', function(ev){ ev.stopPropagation(); _ssGroupsTogglePanel(); });
  }
  var master = document.getElementById('ss-groups-all');
  if (master && !master._wired){
    master._wired = true;
    master.addEventListener('change', function(){
      if (master.checked){
        _ssSelectedSet = {};
        _ssAvailableGroups.forEach(function(g){ _ssSelectedSet[g] = 1; });
      } else {
        _ssSelectedSet = {};
      }
      _ssPopulateGroupsList(document.getElementById('ss-groups-search').value || '');
      _ssUpdateTriggerLabel();
      _ssScheduleLoad();
    });
  }
  var sInp = document.getElementById('ss-groups-search');
  if (sInp && !sInp._wired){
    sInp._wired = true;
    sInp.addEventListener('input', function(){ _ssPopulateGroupsList(sInp.value); });
    sInp.addEventListener('keydown', function(ev){
      if (ev.key === 'Escape'){ _ssGroupsClosePanel(); }
    });
  }
  if (!document._ssClickWired){
    document._ssClickWired = true;
    document.addEventListener('click', _ssDocClickClose);
  }
}

var _ssSearchTimer = null;
function ssOnSearch(){
  clearTimeout(_ssSearchTimer);
  _ssSearchTimer = setTimeout(_ssDoSearch, 320);
}
function _ssDoSearch(){
  var q = (document.getElementById('ss-search').value || '').trim();
  var body = document.getElementById('ss-body');
  if (!q){
    var gv = document.getElementById('ss-group').value;
    if (gv) { ssOnGroupChange(); return; }
    body.innerHTML = '<div style="padding:30px;text-align:center;color:#888;font-weight:600;">اختر مجموعة لعرض الملخص</div>';
    return;
  }
  body.innerHTML = '<div style="padding:24px;text-align:center;color:#888;">جاري البحث...</div>';
  fetch('/api/attendance/summary?view=student&q=' + encodeURIComponent(q)).then(function(r){return r.json();}).then(function(d){
    _ssRenderStudentCards(d.matches || []);
  });
}

/* =======================================================================
 * All-groups summary: sortable table + XLSX export
 * ======================================================================= */
var _ssAllGroups = { rows: [], overall: null, sortKey: 'group_name', sortDir: 1 };

function ssOpenAllGroups(){
  document.getElementById('ss-modal').style.display = 'block';
  document.getElementById('ss-search').value = '';
  _ssSelectedSet = {};
  if (typeof _ssUpdateTriggerLabel === "function") _ssUpdateTriggerLabel();
  if (typeof _ssUpdateAllCheckboxState === "function") _ssUpdateAllCheckboxState();
  if (typeof _ssPopulateGroupsList === "function") _ssPopulateGroupsList("");
  var body = document.getElementById('ss-body');
  body.innerHTML = '<div style="padding:24px;text-align:center;color:#888;">جاري التحميل...</div>';
  fetch('/api/attendance/summary?view=all_groups').then(function(r){return r.json();}).then(function(d){
    _ssAllGroups.rows    = (d.groups || []).slice();
    _ssAllGroups.overall = d.overall || null;
    _ssAllGroups.sortKey = 'group_name';
    _ssAllGroups.sortDir = 1;
    _ssRenderAllGroups();
  }).catch(function(){
    body.innerHTML = '<div style="padding:30px;text-align:center;color:#c62828;">خطأ في التحميل</div>';
  });
}
function _ssSort(key){
  if (_ssAllGroups.sortKey === key) { _ssAllGroups.sortDir *= -1; }
  else { _ssAllGroups.sortKey = key; _ssAllGroups.sortDir = 1; }
  _ssRenderAllGroups();
}
function _ssArrow(key){
  if (_ssAllGroups.sortKey !== key) return '';
  return _ssAllGroups.sortDir > 0 ? ' ▲' : ' ▼';
}
function _ssRenderAllGroups(){
  var body = document.getElementById('ss-body');
  var rows = _ssAllGroups.rows.slice();
  var k = _ssAllGroups.sortKey, d = _ssAllGroups.sortDir;
  rows.sort(function(a, b){
    var va = a[k], vb = b[k];
    if (typeof va === 'number' && typeof vb === 'number') return (va - vb) * d;
    return String(va||'').localeCompare(String(vb||''), 'ar') * d;
  });
  var html = ''
    + '<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:12px;">'
    +   '<div style="font-weight:800;color:#E65100;font-size:1.1rem;">ὌA ملخص جميع المجموعات</div>'
    +   '<button onclick="ssExportAllGroups()" style="background:linear-gradient(135deg,#1B5E20,#43A047);color:#fff;border:none;padding:8px 18px;border-radius:10px;font-size:0.9rem;font-weight:700;cursor:pointer;">὎5 تصدير Excel</button>'
    + '</div>'
    + '<div style="overflow:auto;border:1px solid #ffe0b2;border-radius:10px;">'
    + '<table style="width:100%;border-collapse:collapse;background:#fff;">'
    +   '<thead>'
    +     '<tr style="background:linear-gradient(135deg,#E65100,#FB8C00);color:#fff;cursor:pointer;">'
    +       '<th onclick="_ssSort(\\'group_name\\')" style="padding:10px 12px;text-align:right;font-size:0.9rem;">المجموعة' + _ssArrow('group_name') + '</th>'
    +       '<th onclick="_ssSort(\\'total_sessions\\')" style="padding:10px 12px;text-align:center;font-size:0.9rem;">عدد الحصص' + _ssArrow('total_sessions') + '</th>'
    +       '<th onclick="_ssSort(\\'total_minutes\\')" style="padding:10px 12px;text-align:center;font-size:0.9rem;">إجمالي الساعات' + _ssArrow('total_minutes') + '</th>'
    +       '<th onclick="_ssSort(\\'students_count\\')" style="padding:10px 12px;text-align:center;font-size:0.9rem;">عدد الطلبة' + _ssArrow('students_count') + '</th>'
    +       '<th onclick="_ssSort(\\'avg_attendance_rate\\')" style="padding:10px 12px;text-align:center;font-size:0.9rem;">متوسط الحضور %' + _ssArrow('avg_attendance_rate') + '</th>'
    +     '</tr>'
    +   '</thead>'
    +   '<tbody>';
  rows.forEach(function(r){
    var color = _ssRateColor(r.avg_attendance_rate);
    html += '<tr>'
      +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;font-weight:700;color:#3e2723;text-align:right;">' + (r.group_name||'') + '</td>'
      +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:700;color:#1565C0;">' + (r.total_sessions||0) + '</td>'
      +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:700;color:#2E7D32;">' + _ssFmtHHMM(r.total_minutes) + '</td>'
      +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:700;color:#6A1B9A;">' + (r.students_count||0) + '</td>'
      +   '<td style="padding:8px 10px;border-bottom:1px solid #f0e6d8;text-align:center;font-weight:800;color:' + color + ';">' + (r.avg_attendance_rate||0).toFixed(1) + '%</td>'
      + '</tr>';
  });
  if (_ssAllGroups.overall){
    var o = _ssAllGroups.overall;
    var color = _ssRateColor(o.avg_attendance_rate);
    html += '<tr style="background:#fff3e0;font-weight:800;">'
      +   '<td style="padding:10px 12px;color:#E65100;text-align:right;">إجمالي كل المجموعات</td>'
      +   '<td style="padding:10px 12px;text-align:center;color:#1565C0;">' + (o.total_sessions||0) + '</td>'
      +   '<td style="padding:10px 12px;text-align:center;color:#2E7D32;">' + _ssFmtHHMM(o.total_minutes) + '</td>'
      +   '<td style="padding:10px 12px;text-align:center;color:#6A1B9A;">' + (o.students_count||0) + '</td>'
      +   '<td style="padding:10px 12px;text-align:center;color:' + color + ';">' + (o.avg_attendance_rate||0).toFixed(1) + '%</td>'
      + '</tr>';
  }
  html += '</tbody></table></div>';
  body.innerHTML = html;
}
function _ssLoadXLSX(cb){
  if (window.XLSX) { cb(); return; }
  var s = document.createElement('script');
  s.src = 'https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js';
  s.onload  = cb;
  s.onerror = function(){ alert('فشل تحميل مكتبة Excel'); };
  document.head.appendChild(s);
}
function ssExportAllGroups(){
  _ssLoadXLSX(function(){
    var header = ['المجموعة', 'عدد الحصص', 'إجمالي الساعات', 'عدد الطلبة', 'متوسط الحضور %'];
    var aoa = [header];
    _ssAllGroups.rows.forEach(function(r){
      aoa.push([
        r.group_name || '',
        r.total_sessions || 0,
        _ssFmtHHMM(r.total_minutes),
        r.students_count || 0,
        r.avg_attendance_rate || 0
      ]);
    });
    if (_ssAllGroups.overall){
      var o = _ssAllGroups.overall;
      aoa.push([
        'إجمالي كل المجموعات',
        o.total_sessions || 0, _ssFmtHHMM(o.total_minutes),
        o.students_count || 0, o.avg_attendance_rate || 0
      ]);
    }
    var ws = XLSX.utils.aoa_to_sheet(aoa);
    ws['!cols'] = [{wch:28},{wch:12},{wch:14},{wch:12},{wch:16}];
    var wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'ملخص المجموعات');
    XLSX.writeFile(wb, 'groups_summary.xlsx');
  });
}
function sdOpen(){
  document.getElementById("sd-modal").style.display="block";
  document.getElementById("sd-body").innerHTML="";
  document.getElementById("sd-footer").style.display="none";
  var sel=document.getElementById("sd-group");
  sel.innerHTML="<option value=''>\u2014 \u0627\u062E\u062A\u0631 \u0645\u062C\u0645\u0648\u0639\u0629 \u2014</option>";
  fetch("/api/attendance/groups").then(r=>r.json()).then(function(groups){
    groups.forEach(function(g){var o=document.createElement("option");o.value=g;o.textContent=g;sel.appendChild(o);});
  });
}
function sdLoadDates(){
  var g=document.getElementById("sd-group").value;
  var body=document.getElementById("sd-body");
  var footer=document.getElementById("sd-footer");
  if(!g){body.innerHTML="";footer.style.display="none";return;}
  body.innerHTML="\u062C\u0627\u0631\u064A \u0627\u0644\u062A\u062D\u0645\u064A\u0644...";
  footer.style.display="none";
  fetch("/api/attendance/group-dates?group="+encodeURIComponent(g)).then(r=>r.json()).then(function(rows){
    if(!rows||!rows.length){body.innerHTML="\u0644\u0627 \u062A\u0648\u062C\u062F \u062D\u0635\u0635";return;}
    var html="<table style='width:100%;border-collapse:collapse;'><thead><tr style='background:#e3f2fd;color:#0d47a1;'><th style='padding:8px;border:1px solid #bbdefb;text-align:center;'>\u0627\u0644\u062A\u0627\u0631\u064A\u062E</th><th style='padding:8px;border:1px solid #bbdefb;text-align:center;'>\u0627\u0644\u0645\u062F\u0629 (\u062F\u0642\u064A\u0642\u0629)</th><th style='padding:8px;border:1px solid #bbdefb;text-align:center;'>\u0646\u0648\u0639 \u0627\u0644\u062D\u0635\u0629</th></tr></thead><tbody>";
    rows.forEach(function(r){
      var st = (r.session_type||'');
      var selHu = (st==='\u062D\u0636\u0648\u0631' ? ' selected' : '');
      var selOn = (st==='\u0623\u0648\u0646\u0644\u0627\u064A\u0646' ? ' selected' : '');
      html+="<tr><td style='padding:6px;border:1px solid #e0e0e0;text-align:center;font-weight:600;'>"+(r.session_date||"")+"</td>"
          +"<td style='padding:6px;border:1px solid #e0e0e0;text-align:center;'>"
          +"<input type='number' class='sd-dur' data-date='"+(r.session_date||"")+"' value='"+(r.duration_minutes||"")+"' min='0' style='width:90px;padding:5px 8px;border-radius:6px;border:1px solid #1E88E5;text-align:center;'></td>"
          +"<td style='padding:6px;border:1px solid #e0e0e0;text-align:center;'>"
          +"<select class='sd-type' data-date='"+(r.session_date||"")+"' style='padding:5px 8px;border-radius:6px;border:1px solid #1E88E5;min-width:100px;'>"
          +"<option value=''>\u2014</option>"
          +"<option value='\u062D\u0636\u0648\u0631'"+selHu+">\u062D\u0636\u0648\u0631</option>"
          +"<option value='\u0623\u0648\u0646\u0644\u0627\u064A\u0646'"+selOn+">\u0623\u0648\u0646\u0644\u0627\u064A\u0646</option>"
          +"</select></td></tr>";
    });
    html+="</tbody></table>";
    body.innerHTML=html;
    footer.style.display="block";
  }).catch(function(){body.innerHTML="\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u062A\u062D\u0645\u064A\u0644";});
}
function sdSave(){
  var g=document.getElementById("sd-group").value;if(!g)return;
  var items=[];
  document.querySelectorAll(".sd-dur").forEach(function(inp){
    var d=inp.dataset.date;
    var sel=document.querySelector(".sd-type[data-date='"+d+"']");
    var st=sel?sel.value:'';
    items.push({session_date:d,duration_minutes:parseInt(inp.value||0,10)||0,session_type:st});
  });
  var btn=document.getElementById("sd-save");var orig=btn.textContent;btn.textContent="...";btn.disabled=true;
  fetch("/api/session-durations",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({group_name:g,items:items})})
    .then(r=>r.json()).then(function(d){
      btn.textContent=d.ok?"\u062A\u0645 \u0627\u0644\u062D\u0641\u0638 \u2713":"\u062E\u0637\u0623";
      setTimeout(function(){btn.textContent=orig;btn.disabled=false;},1600);
    }).catch(function(){btn.textContent="\u062E\u0637\u0623";setTimeout(function(){btn.textContent=orig;btn.disabled=false;},1600);});
}

// ===== Student search (fuzzy) =====
var _srStudents = [];
var _srCurrentId = null;
function _srNorm(s){
  return String(s==null?'':s)
    .replace(/[\u0623\u0625\u0622\u0671]/g, '\u0627')  // أ إ آ ٱ → ا
    .replace(/\u0629/g, '\u0647')  // ة → ه
    .replace(/\u0649/g, '\u064A')  // ى → ي
    .replace(/[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g, '')  // strip diacritics
    .replace(/\s+/g, ' ')
    .toLowerCase()
    .trim();
}
function _srScore(query, candidate){
  // Higher = better match. Substring > subsequence > char overlap.
  var q = _srNorm(query);
  var c = _srNorm(candidate);
  if (!q) return 0;
  if (c === q) return 10000;
  if (c.indexOf(q) === 0) return 9000;
  if (c.indexOf(q) >= 0) return 8000;
  // Subsequence: q's chars appear in c in order, possibly with gaps.
  var i = 0, j = 0, matched = 0;
  while (i < q.length && j < c.length) {
    if (q.charAt(i) === c.charAt(j)) { matched++; i++; }
    j++;
  }
  if (i === q.length) return 5000 + matched * 10 - (c.length - q.length);
  // Partial char overlap as last resort.
  var shared = 0, seen = {};
  for (var k=0; k<c.length; k++) seen[c.charAt(k)] = true;
  for (var k=0; k<q.length; k++) if (seen[q.charAt(k)]) shared++;
  if (shared >= Math.max(1, q.length - 2)) return 100 + shared;
  return 0;
}
function srOpen(){
  document.getElementById('sr-modal').style.display = 'block';
  document.getElementById('sr-query').value = '';
  document.getElementById('sr-results').innerHTML = '';
  document.getElementById('sr-details').innerHTML = '';
  _srCurrentId = null;
  fetch('/api/students').then(function(r){return r.json();}).then(function(data){
    _srStudents = data.students || [];
    document.getElementById('sr-query').focus();
  }).catch(function(){ document.getElementById('sr-results').innerHTML = '<div style="color:#c00;padding:12px;">\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u062A\u062D\u0645\u064A\u0644</div>'; });
}
function srClose(){ document.getElementById('sr-modal').style.display = 'none'; _srCurrentId = null; }
function srFilter(){
  var q = document.getElementById('sr-query').value.trim();
  var results = document.getElementById('sr-results');
  if (!q) { results.innerHTML = ''; return; }
  var scored = [];
  for (var i=0; i<_srStudents.length; i++) {
    var s = _srStudents[i];
    var scoreName = _srScore(q, s.student_name || '');
    var scorePid = _srScore(q, s.personal_id || '');
    var score = Math.max(scoreName, scorePid);
    if (score > 0) scored.push({ s: s, score: score });
  }
  scored.sort(function(a,b){
    var ad = (a.s && a.s.is_active === false) ? 1 : 0;
    var bd = (b.s && b.s.is_active === false) ? 1 : 0;
    if (ad !== bd) return ad - bd;  // active first
    return b.score - a.score;
  });
  scored = scored.slice(0, 10);
  if (!scored.length) { results.innerHTML = '<div style="padding:12px;color:#888;">\u0644\u0627 \u062A\u0648\u062C\u062F \u0646\u062A\u0627\u0626\u062C</div>'; return; }
  var html = '';
  for (var i=0; i<scored.length; i++) {
    var s = scored[i].s;
    var _inactBadge = (s.is_active === false)
      ? ' <span style="background:#fce4ec;color:#c62828;font-size:0.7em;padding:1px 7px;border-radius:999px;font-weight:700;margin-right:6px;vertical-align:middle;">\u063A\u064A\u0631 \u0646\u0634\u0637</span>'
      : '';
    html += '<div class="srm-result" onclick="srPick('+s.id+')">'
         +  '<div class="srm-result-name">'+(s.student_name||'-')+_inactBadge+'</div>'
         +  '<div class="srm-result-meta">\u0631\u0642\u0645: '+(s.personal_id||'-')
         +  (s.class_name?(' &middot; \u0627\u0644\u0635\u0641: '+s.class_name):'')
         +  (s.group_name_student?(' &middot; \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629: '+s.group_name_student):'')
         +  '</div></div>';
  }
  results.innerHTML = html;
}
function srPick(sid){
  _srCurrentId = sid;
  document.getElementById('sr-results').innerHTML = '';
  document.getElementById('sr-details').innerHTML = '<div style="padding:12px;color:#555;">\u062C\u0627\u0631\u064A \u0627\u0644\u062A\u062D\u0645\u064A\u0644...</div>';
  fetch('/api/students/'+sid+'/details').then(function(r){return r.json();}).then(function(d){
    if (!d.ok) { document.getElementById('sr-details').innerHTML = '<div style="color:#c00;padding:12px;">'+(d.error||'\u062E\u0637\u0623')+'</div>'; return; }
    _srRenderCard(d);
  });
}
function _srField(id, label, value){
  var v = value == null ? '' : String(value);
  v = v.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
  // Fields ALWAYS render as disabled inputs in view mode. Edit mode flips
  // the disabled flag + replaces the lock icon via _srApplyMode().
  return '<div class="srm-field"><label><span class="srm-lock">🔒</span>'+label+'</label>'
       + '<input id="'+id+'" data-sr="'+id+'" value="'+v+'" class="srm-readonly" disabled></div>';
}
var _srMode = 'view';
var _srOriginal = {};
var _srIdleTimer = null;
var _srAutoLockMs = 120000; /* 2 minutes of inactivity → auto-exit edit */
var _SR_FIELD_IDS = ['personal_id','student_name','whatsapp','class_name','group_name_student','group_online','old_new_2026','registration_term2_2026','teacher_2026','books_received','final_result','level_reached_2026','suitable_level_2026','mother_phone','father_phone','other_phone','residence','home_address','road','complex_name','installment_type','installment1','installment2','installment3','installment4','installment5'];
var _SR_FIELD_LABELS = {
  personal_id: 'الرقم الشخصي',
  student_name: 'اسم الطالب',
  whatsapp: 'الواتساب',
  class_name: 'الصف',
  group_name_student: 'المجموعة',
  group_online: 'المجموعة (أونلاين)',
  old_new_2026: 'قديم/جديد 2026',
  registration_term2_2026: 'تسجيل الفصل الثاني 2026',
  teacher_2026: 'المدرس 2026',
  books_received: 'استلام الكتب',
  final_result: 'النتيجة النهائية',
  level_reached_2026: 'إلى أين وصل 2026',
  suitable_level_2026: 'مناسب للمستوى 2026؟',
  mother_phone: 'هاتف الأم',
  father_phone: 'هاتف الأب',
  other_phone: 'هاتف آخر',
  residence: 'مكان السكن',
  home_address: 'العنوان',
  road: 'الطريق',
  complex_name: 'المجمع',
  installment_type: 'نوع التقسيط',
  installment1: 'القسط 1',
  installment2: 'القسط 2',
  installment3: 'القسط 3',
  installment4: 'القسط 4',
  installment5: 'القسط 5'
};
function _srCurrentValues(){
  var out = {};
  _SR_FIELD_IDS.forEach(function(k){
    var el = document.getElementById('sr_'+k);
    if (el) out[k] = el.value;
  });
  return out;
}
function _srApplyMode(){
  var fields = document.querySelectorAll('#sr-details .srm-field');
  for (var i=0; i<fields.length; i++){
    var inp = fields[i].querySelector('input');
    var lock = fields[i].querySelector('.srm-lock');
    if (!inp) continue;
    if (_srMode === 'edit'){
      fields[i].classList.add('edit');
      inp.removeAttribute('disabled');
      inp.classList.remove('srm-readonly');
      if (lock) lock.textContent = '🔓';
    } else {
      fields[i].classList.remove('edit');
      inp.setAttribute('disabled','disabled');
      inp.classList.add('srm-readonly');
      if (lock) lock.textContent = '🔒';
    }
  }
  var banner = document.getElementById('sr-edit-banner');
  if (banner) banner.classList.toggle('show', _srMode === 'edit');
  _srRenderActions();
}
function _srRenderActions(){
  var box = document.getElementById('sr-actions');
  if (!box) return;
  if (_srMode === 'edit'){
    box.innerHTML =
        '<button class="srm-btn-save" onclick="_srTrySave()">💾 حفظ التغييرات</button>'
      + '<button class="srm-btn-cancel-edit" onclick="_srExitEditMode(true)">❌ إلغاء التعديل</button>'
      + '<button class="srm-btn-delete" onclick="_srTryDelete()">🗑 حذف الطالب</button>';
  } else {
    box.innerHTML =
        '<button class="srm-btn-edit" onclick="_srEnterEditMode()">✏ تعديل بيانات الطالب</button>'
      + '<button class="srm-cancel" onclick="srClose()">إغلاق</button>';
  }
}
function _srResetIdle(){
  if (_srIdleTimer) clearTimeout(_srIdleTimer);
  if (_srMode !== 'edit') return;
  _srIdleTimer = setTimeout(function(){
    if (_srMode !== 'edit') return;
    _srExitEditMode(false);
    var b = document.getElementById('srm-auto-lock');
    if (b){
      b.classList.add('show');
      setTimeout(function(){ b.classList.remove('show'); }, 3200);
    }
  }, _srAutoLockMs);
}
function _srWireIdleInputs(){
  _SR_FIELD_IDS.forEach(function(k){
    var el = document.getElementById('sr_'+k);
    if (el && !el._srWired){
      el._srWired = true;
      el.addEventListener('input', _srResetIdle);
    }
  });
}
function _srEnterEditMode(){
  if (_srMode === 'edit') return;
  if (!_srCurrentId) return;
  var sName = (_srOriginal.student_name || '—');
  if (typeof window.mxConfirm === 'function'){
    window.mxConfirm({
      title: '⚠ تنبيه: أنت على وشك تعديل بيانات الطالب',
      message: sName + '\\n\\nهل أنت متأكد؟',
      yesText: 'نعم، متأكد',
      noText:  'إلغاء'
    }, function(){
      _srMode = 'edit';
      _srApplyMode();
      _srWireIdleInputs();
      _srResetIdle();
      var first = document.getElementById('sr_student_name');
      if (first) first.focus();
    });
  } else {
    if (!confirm('⚠ هل أنت متأكد من تعديل بيانات الطالب ' + sName + '؟')) return;
    _srMode = 'edit'; _srApplyMode(); _srWireIdleInputs(); _srResetIdle();
  }
}
function _srExitEditMode(rollback){
  if (_srMode !== 'edit') return;
  if (rollback){
    _SR_FIELD_IDS.forEach(function(k){
      var el = document.getElementById('sr_'+k);
      if (el) el.value = _srOriginal[k] != null ? _srOriginal[k] : '';
    });
  }
  _srMode = 'view';
  if (_srIdleTimer){ clearTimeout(_srIdleTimer); _srIdleTimer = null; }
  _srApplyMode();
}
function _srComputeDiff(){
  var current = _srCurrentValues();
  var diffs = [];
  _SR_FIELD_IDS.forEach(function(k){
    var a = _srOriginal[k] != null ? String(_srOriginal[k]) : '';
    var b = current[k]      != null ? String(current[k])      : '';
    if (a !== b){
      diffs.push({field:k, label: _SR_FIELD_LABELS[k] || k, from:a, to:b});
    }
  });
  return diffs;
}
function _srTrySave(){
  var diffs = _srComputeDiff();
  if (!diffs.length){
    if (typeof window.mxToast === 'function') window.mxToast('لا توجد تغييرات للحفظ', 'info');
    else alert('لا توجد تغييرات');
    return;
  }
  var body = document.getElementById('srm-log-body');
  var html = '<p style="margin-bottom:8px;font-weight:700;color:#E65100;">تم تعديل ' + diffs.length + ' حقل:</p>';
  diffs.forEach(function(d){
    html += '<div class="srm-log-item">'
         +    '<span class="srm-log-field">' + d.label + '</span>: '
         +    'تم تغيير من <span class="srm-log-from">' + (d.from ? _srEsc(d.from) : '—') + '</span>'
         +    'إلى <span class="srm-log-to">' + (d.to ? _srEsc(d.to) : '—') + '</span>'
         +  '</div>';
  });
  html += '<p style="margin-top:10px;color:#555;font-size:0.9rem;">هل أنت متأكد من حفظ هذه التغييرات؟ سيتم تحديث بيانات الطالب في قاعدة البيانات.</p>';
  body.innerHTML = html;
  var modal = document.getElementById('srm-log-modal');
  modal.classList.add('open');
  document.getElementById('srm-log-yes').onclick = function(){
    modal.classList.remove('open');
    _srDoSave(diffs);
  };
  document.getElementById('srm-log-no').onclick = function(){
    modal.classList.remove('open');
  };
}
function _srEsc(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function _srDoSave(diffs){
  var body = {};
  diffs.forEach(function(d){ body[d.field] = d.to; });
  fetch('/api/students/'+_srCurrentId, { method:'PUT', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify(body) })
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d.ok){
        if (typeof window.mxToast === 'function') window.mxToast('تم تحديث بيانات الطالب بنجاح', 'success');
        _srMode = 'view';
        srPick(_srCurrentId);
        fetch('/api/students').then(function(r){return r.json();}).then(function(data){ _srStudents = data.students || []; });
      } else {
        if (typeof window.mxToast === 'function') window.mxToast(d.error || 'حدث خطأ', 'error');
        else alert(d.error || 'حدث خطأ');
      }
    })
    .catch(function(){
      if (typeof window.mxToast === 'function') window.mxToast('حدث خطأ في الاتصال', 'error');
      else alert('حدث خطأ في الاتصال');
    });
}
function _srTryDelete(){
  if (!_srCurrentId) return;
  var sName = _srOriginal.student_name || '';
  function step1(){
    window.mxConfirm({
      title: 'هل تريد حذف بيانات هذا الطالب؟',
      message: sName,
      yesText: 'متابعة',
      noText:  'إلغاء'
    }, step2);
  }
  function step2(){
    window.mxConfirm({
      title: '⚠ تحذير: هذا الإجراء لا يمكن التراجع عنه',
      message: 'هل أنت متأكد تماماً من حذف ' + sName + '؟',
      yesText: 'نعم، متأكد تماماً',
      noText:  'إلغاء'
    }, step3);
  }
  function step3(){
    var m = document.getElementById('srm-type-modal');
    var inp = document.getElementById('srm-type-input');
    var expected = document.getElementById('srm-type-expected');
    document.getElementById('srm-type-title').textContent = '⚠ اكتب اسم الطالب للتأكيد';
    document.getElementById('srm-type-msg').textContent = 'اكتب الاسم تماماً كما هو أدناه، ثم اضغط "تأكيد الحذف".';
    expected.textContent = sName;
    inp.value = '';
    m.classList.add('open');
    setTimeout(function(){ inp.focus(); }, 50);
    document.getElementById('srm-type-yes').onclick = function(){
      if ((inp.value || '').trim() === (sName || '').trim()){
        m.classList.remove('open');
        _srDoDelete();
      } else {
        inp.style.background = '#ffebee';
        setTimeout(function(){ inp.style.background = ''; }, 900);
      }
    };
    document.getElementById('srm-type-no').onclick = function(){
      m.classList.remove('open');
    };
  }
  if (typeof window.mxConfirm === 'function') step1();
  else {
    if (!confirm('هل تريد حذف ' + sName + '؟')) return;
    if (!confirm('⚠ لا يمكن التراجع. متأكد؟')) return;
    var typed = prompt('اكتب اسم الطالب للتأكيد:');
    if ((typed||'').trim() === (sName||'').trim()) _srDoDelete();
  }
}
function _srDoDelete(){
  fetch('/api/students/'+_srCurrentId, { method:'DELETE', credentials:'include' })
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d.ok){
        if (typeof window.mxToast === 'function') window.mxToast('تم حذف بيانات الطالب', 'success');
        _srCurrentId = null;
        document.getElementById('sr-details').innerHTML = '';
        fetch('/api/students').then(function(r){return r.json();}).then(function(data){ _srStudents = data.students || []; });
      } else {
        if (typeof window.mxToast === 'function') window.mxToast(d.error || 'تعذّر الحذف', 'error');
        else alert(d.error || 'تعذّر الحذف');
      }
    })
    .catch(function(){
      if (typeof window.mxToast === 'function') window.mxToast('خطأ في الاتصال', 'error');
    });
}
function _srRenderCard(d){
  var s = d.student || {};
  var att = d.attendance || {};
  var tot = d.payment_totals || {};
  // Reset state each time a new student is picked.
  _srMode = 'view';
  _srOriginal = {};
  _SR_FIELD_IDS.forEach(function(k){ _srOriginal[k] = (s[k] != null ? String(s[k]) : ''); });
  if (_srIdleTimer){ clearTimeout(_srIdleTimer); _srIdleTimer = null; }

  var html = '<div class="srm-card">';
  html += '<div id="sr-edit-banner" class="srm-edit-banner">⚠ أنت في وضع التعديل — تأكد من صحة البيانات قبل الحفظ</div>';
  // BASIC
  html += '<div class="srm-section"><div class="srm-section-title">\U0001F464 البيانات الأساسية</div><div class="srm-grid">';
  html += _srField('sr_personal_id','الرقم الشخصي', s.personal_id);
  html += _srField('sr_student_name','اسم الطالب', s.student_name);
  html += _srField('sr_whatsapp','الواتساب', s.whatsapp);
  html += _srField('sr_class_name','الصف', s.class_name);
  html += _srField('sr_group_name_student','المجموعة', s.group_name_student);
  html += _srField('sr_group_online','المجموعة (الاونلاين)', s.group_online);
  html += _srField('sr_old_new_2026','قديم جديد 2026', s.old_new_2026);
  html += _srField('sr_registration_term2_2026','تسجيل الفصل الثاني 2026', s.registration_term2_2026);
  html += _srField('sr_teacher_2026','المدرس 2026', s.teacher_2026);
  html += _srField('sr_books_received','استلام الكتب', s.books_received);
  html += _srField('sr_final_result','النتيجة النهائية', s.final_result);
  html += _srField('sr_level_reached_2026','إلى أين وصل 2026', s.level_reached_2026);
  html += _srField('sr_suitable_level_2026','مناسب للمستوى 2026؟', s.suitable_level_2026);
  html += '</div></div>';
  // CONTACT
  html += '<div class="srm-section"><div class="srm-section-title">\U0001F4DE الاتصال والسكن</div><div class="srm-grid">';
  html += _srField('sr_mother_phone','هاتف الأم', s.mother_phone);
  html += _srField('sr_father_phone','هاتف الأب', s.father_phone);
  html += _srField('sr_other_phone','هاتف آخر', s.other_phone);
  html += _srField('sr_residence','مكان السكن', s.residence);
  html += _srField('sr_home_address','العنوان', s.home_address);
  html += _srField('sr_road','الطريق', s.road);
  html += _srField('sr_complex_name','المجمع', s.complex_name);
  html += '</div></div>';
  // PAYMENTS
  html += '<div class="srm-section"><div class="srm-section-title">\U0001F4B3 تفاصيل الدفع</div><div class="srm-grid">';
  html += _srField('sr_installment_type','نوع التقسيط', s.installment_type);
  html += _srField('sr_installment1','القسط 1', s.installment1);
  html += _srField('sr_installment2','القسط 2', s.installment2);
  html += _srField('sr_installment3','القسط 3', s.installment3);
  html += _srField('sr_installment4','القسط 4', s.installment4);
  html += _srField('sr_installment5','القسط 5', s.installment5);
  html += '</div>';
  html += '<div class="srm-totals">'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+(tot.paid||0)+'</div><div class="srm-stat-lbl">المدفوع</div></div>'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+(tot.price||0)+'</div><div class="srm-stat-lbl">السعر الإجمالي</div></div>'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+(tot.remaining||0)+'</div><div class="srm-stat-lbl">المتبقي</div></div>'
       + '</div></div>';
  // ATTENDANCE
  var pct = function(v){ return (v||0)+'%'; };
  var bar = function(v){ return '<div class="srm-pct-bar"><div class="srm-pct-bar-inner" style="width:'+(Math.min(100,v||0))+'%"></div></div>'; };
  html += '<div class="srm-section"><div class="srm-section-title">\U0001F4C5 إحصائيات الحضور ('+(att.total||0)+' جلسة)</div>';
  html += '<div class="srm-totals">'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+pct(att.present_rate)+'</div><div class="srm-stat-lbl">نسبة الحضور ('+(att.present||0)+')</div>'+bar(att.present_rate)+'</div>'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+pct(att.absent_rate)+'</div><div class="srm-stat-lbl">نسبة الغياب ('+(att.absent||0)+')</div>'+bar(att.absent_rate)+'</div>'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+pct(att.late_rate)+'</div><div class="srm-stat-lbl">نسبة التأخير ('+(att.late||0)+')</div>'+bar(att.late_rate)+'</div>'
       + '</div></div>';
  // PAYLOG (سجل الدفع) — a row from payment_log matched to this student.
  // Rendered read-only; see api_student_details for the lookup order.
  html += '<div class="srm-section"><div class="srm-section-title">\U0001F4B0 سجل الدفع</div>';
  var pl = d.paylog;
  if (!pl) {
    html += '<div style="padding:14px;text-align:center;color:#888;font-weight:600;background:#f8f9fa;border-radius:8px;">لا يوجد سجل دفع لهذا الطالب</div>';
  } else {
    var remainNum = parseFloat(pl.total_remaining) || 0;
    var remainColor = remainNum > 0 ? '#c62828' : '#2E7D32';
    var paidColor = '#2E7D32';
    function _plCell(lbl, val, style){
      var v = (val === '' || val == null) ? '—' : _srEsc(String(val));
      return '<div style="background:#fff;border:1px solid #eee;border-radius:8px;padding:8px 10px;">' +
             '<div style="color:#777;font-size:0.78rem;">' + lbl + '</div>' +
             '<div style="font-weight:800;' + (style || 'color:#455A64;') + '">' + v + '</div>' +
             '</div>';
    }
    html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px;margin-bottom:10px;font-size:0.9rem;">';
    html += _plCell('حالة التسجيل', pl.registration_status, 'color:#6A1B9A;');
    html += _plCell('مبلغ الدورة', pl.course_amount, 'color:#1565C0;');
    html += _plCell('حالة المدفوعات', pl.payment_status, 'color:#E65100;');
    html += '</div>';
    // Installments table
    html += '<div style="background:#fff;border:1px solid #eee;border-radius:10px;padding:8px;margin-bottom:10px;">';
    html += '<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">';
    html += '<thead><tr style="background:#e3f2fd;color:#0d47a1;">' +
            '<th style="padding:7px 10px;text-align:right;">القسط</th>' +
            '<th style="padding:7px 10px;text-align:right;">المبلغ</th>' +
            '<th style="padding:7px 10px;text-align:right;">الحالة</th>' +
            '</tr></thead><tbody>';
    (pl.installments || []).forEach(function(it){
      var amt = (it.amount === '' || it.amount == null) ? '—' : _srEsc(String(it.amount));
      var stRaw = (it.status || '').toString().trim();
      var stHtml;
      if (!stRaw) {
        stHtml = '<span style="color:#999;">—</span>';
      } else if (stRaw === 'تم الدفع' || stRaw.indexOf('دفع') >= 0 && stRaw.indexOf('لم') < 0) {
        stHtml = '<span style="background:#e8f5e9;color:#2E7D32;padding:2px 10px;border-radius:999px;font-weight:700;">' + _srEsc(stRaw) + '</span>';
      } else if (stRaw.indexOf('معف') >= 0) {
        stHtml = '<span style="background:#fff3e0;color:#E65100;padding:2px 10px;border-radius:999px;font-weight:700;">' + _srEsc(stRaw) + '</span>';
      } else {
        stHtml = '<span style="background:#fce4ec;color:#c62828;padding:2px 10px;border-radius:999px;font-weight:700;">' + _srEsc(stRaw) + '</span>';
      }
      html += '<tr style="border-top:1px solid #f0f0f0;">' +
              '<td style="padding:7px 10px;font-weight:700;color:#37474F;">القسط ' + (it.num||'') + '</td>' +
              '<td style="padding:7px 10px;color:#1565C0;font-weight:700;">' + amt + '</td>' +
              '<td style="padding:7px 10px;">' + stHtml + '</td>' +
              '</tr>';
    });
    html += '</tbody></table></div>';
    // Totals row with spec-mandated colors (paid always green, remaining red>0 green=0)
    html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:6px;">';
    html += '<div style="background:#e8f5e9;border:2px solid #a5d6a7;border-radius:10px;padding:10px 14px;text-align:center;">' +
            '<div style="color:#555;font-size:0.82rem;">المبلغ المدفوع</div>' +
            '<div style="font-weight:800;font-size:1.15rem;color:' + paidColor + ';">' + _srEsc(String(pl.total_paid || '0')) + '</div>' +
            '</div>';
    html += '<div style="background:' + (remainNum > 0 ? '#fce4ec' : '#e8f5e9') + ';border:2px solid ' + (remainNum > 0 ? '#f48fb1' : '#a5d6a7') + ';border-radius:10px;padding:10px 14px;text-align:center;">' +
            '<div style="color:#555;font-size:0.82rem;">المبلغ المتبقي</div>' +
            '<div style="font-weight:800;font-size:1.15rem;color:' + remainColor + ';">' + _srEsc(String(pl.total_remaining || '0')) + '</div>' +
            '</div>';
    html += '</div>';
  }
  html += '</div>';
  // ACTIONS
  html += '<div class="srm-actions" id="sr-actions"></div>';
  html += '</div>';
  document.getElementById('sr-details').innerHTML = html;
  _srApplyMode();
}
function srSave(){ _srTrySave(); }  /* backward-compat shim */
</script>

<style>
.msg-modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:9999;overflow:auto;}
.msg-box{background:#fff;margin:20px auto;border-radius:14px;max-width:780px;width:95%;padding:0;overflow:hidden;box-shadow:0 8px 32px rgba(107,63,160,0.25);}
.msg-header{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;}
.msg-header-title{color:#fff;font-size:1.2rem;font-weight:bold;display:flex;align-items:center;gap:8px;}
.msg-header .msg-close{color:#fff;font-size:1.8rem;cursor:pointer;line-height:1;background:none;border:none;padding:0;}
.msg-body{padding:18px 22px;max-height:80vh;overflow:auto;}
.msg-actions-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:18px;}
.msg-action-btn{color:#fff;border:none;border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:4px;cursor:pointer;text-align:right;font-family:inherit;font-size:inherit;box-shadow:0 4px 14px rgba(0,0,0,.08);transition:transform .15s,box-shadow .15s;}
.msg-action-btn:hover{transform:translateY(-2px);box-shadow:0 8px 22px rgba(0,0,0,.15);}
.msg-action-btn .mab-title{font-size:1rem;font-weight:800;display:flex;align-items:center;gap:6px;}
.msg-action-btn .mab-desc{font-size:.78rem;opacity:.92;}
.mab-teal{background:linear-gradient(135deg,#00897B,#26A69A);}
.mab-purple{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);}
.mab-orange{background:linear-gradient(135deg,#E65100,#FB8C00);}
.mab-red{background:linear-gradient(135deg,#c0392b,#e74c3c);}
.msg-abs-section-head{display:flex;justify-content:space-between;align-items:center;margin:14px 0 6px;gap:10px;flex-wrap:wrap;}
.msg-abs-section-head .msg-cat-header{margin:0;padding-bottom:0;border:none;}
.msg-abs-sent{font-size:.82rem;color:#2E7D32;font-weight:700;margin-inline-end:6px;}
.msg-abs-count-absent{color:#c0392b;}
.msg-abs-count-late{color:#E65100;}
.msg-abs-alert{margin:10px 0 14px;padding:14px 18px;border-radius:12px;font-weight:700;font-size:1rem;display:flex;align-items:center;gap:10px;box-shadow:0 2px 10px rgba(0,0,0,.06);transition:background .25s,color .25s,border-color .25s;}
.msg-abs-alert.alert-warn{background:linear-gradient(135deg,#ffebee,#ffcdd2);color:#b71c1c;border:1.5px solid #ef9a9a;}
.msg-abs-alert.alert-ok{background:linear-gradient(135deg,#e8f5e9,#c8e6c9);color:#1b5e20;border:1.5px solid #81c784;}
.msg-abs-alert.alert-info{background:linear-gradient(135deg,#f3e5f5,#e1bee7);color:#4a148c;border:1.5px solid #b39ddb;}
.msg-abs-filters{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:14px;padding:10px 12px;background:#faf7ff;border:1px solid #e1d3f7;border-radius:12px;}
.msg-abs-spacer{flex:1;}
.msg-abs-filter{display:inline-flex;align-items:center;gap:6px;padding:7px 14px;border-radius:20px;border:1.5px solid #d1c4e9;background:#fff;color:#4a148c;font-family:inherit;font-size:.88rem;font-weight:700;cursor:pointer;transition:all .15s;}
.msg-abs-filter:hover{background:#ede7f6;}
.msg-abs-filter.active{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border-color:transparent;box-shadow:0 3px 10px rgba(107,63,160,.28);}
.msg-abs-filter-count{display:inline-block;min-width:22px;padding:1px 7px;border-radius:12px;background:rgba(0,0,0,.1);color:inherit;font-weight:800;font-size:.78rem;text-align:center;}
.msg-abs-filter.active .msg-abs-filter-count{background:rgba(255,255,255,.25);}
.msg-abs-section{margin-top:14px;}
.msg-abs-section-title{display:flex;justify-content:space-between;align-items:center;font-weight:800;color:#4a148c;font-size:1rem;margin:0 0 8px;border-bottom:2px dashed #d1c4e9;padding-bottom:6px;}
.msg-abs-section-count{background:#ede7f6;color:#4a148c;border-radius:12px;padding:2px 10px;font-size:.85rem;font-weight:800;}
.msg-abs-card-list{display:flex;flex-direction:column;gap:10px;min-height:10px;}
.msg-abs-card{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:12px 14px;background:#fff;border:1px solid #e1d3f7;border-inline-start:4px solid #c0392b;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.04);transition:opacity .3s ease, transform .3s ease, max-height .3s ease, background .2s, border-color .2s;opacity:1;transform:translateX(0);max-height:180px;overflow:hidden;}
.msg-abs-card.status-late{border-inline-start-color:#E65100;}
.msg-abs-card.is-sent{background:#f3fbf4;border-color:#c8e6c9;border-inline-start-color:#2E7D32;}
.msg-abs-card.leaving{opacity:0;transform:translateX(-40px);max-height:0;padding-top:0;padding-bottom:0;margin-top:-10px;border-width:0;}
.msg-abs-card.arriving{opacity:0;transform:translateY(-10px);}
.msg-abs-card-left{display:flex;flex-direction:column;gap:3px;min-width:0;flex:1;}
.msg-abs-card-name{font-weight:800;color:#4a148c;font-size:1rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.msg-abs-card-meta{display:flex;align-items:center;gap:8px;font-size:.78rem;color:#6a5494;flex-wrap:wrap;}
.msg-abs-badge{display:inline-flex;align-items:center;gap:3px;padding:2px 9px;border-radius:10px;font-weight:700;font-size:.74rem;}
.msg-abs-badge-absent{background:#ffebee;color:#c0392b;}
.msg-abs-badge-late{background:#fff3e0;color:#E65100;}
.msg-abs-card-right{display:flex;align-items:center;gap:8px;flex-shrink:0;}
.msg-abs-sent-badge{font-size:.78rem;color:#2E7D32;font-weight:700;white-space:nowrap;}
.msg-abs-last{font-size:.74rem;color:#888;white-space:nowrap;}
.msg-abs-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px;}
.msg-abs-stat{position:relative;background:#fff;border:1px solid #eee;border-radius:12px;padding:12px 14px;box-shadow:0 2px 8px rgba(0,0,0,.04);display:flex;flex-direction:column;gap:3px;overflow:hidden;}
.msg-abs-stat::before{content:'';position:absolute;top:0;right:0;width:4px;height:100%;background:#999;}
.msg-abs-stat-absent::before{background:#c0392b;}
.msg-abs-stat-late::before{background:#E65100;}
.msg-abs-stat-sent::before{background:#2E7D32;}
.msg-abs-stat-never::before{background:#6B3FA0;}
.msg-abs-stat-top{display:flex;justify-content:flex-end;}
.msg-abs-stat-icon{font-size:18px;opacity:.85;}
.msg-abs-stat-num{font-size:1.6rem;font-weight:800;color:#222;line-height:1.1;font-variant-numeric:tabular-nums;}
.msg-abs-stat-lbl{font-size:.78rem;color:#666;font-weight:700;}
.msg-abs-confirm{display:none;position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:10001;align-items:center;justify-content:center;animation:msg-abs-fade .18s ease;}
.msg-abs-confirm.show{display:flex;}
@keyframes msg-abs-fade{from{opacity:0;}to{opacity:1;}}
.msg-abs-confirm-box{background:#fff;border-radius:14px;padding:22px 24px;max-width:380px;width:92%;box-shadow:0 16px 48px rgba(0,0,0,.25);text-align:center;transform:scale(.96);animation:msg-abs-pop .18s ease forwards;}
@keyframes msg-abs-pop{to{transform:scale(1);}}
.msg-abs-confirm-title{font-size:1.05rem;font-weight:800;color:#4a148c;margin-bottom:6px;}
.msg-abs-confirm-sub{font-size:.9rem;color:#6a5494;margin-bottom:18px;font-weight:600;}
.msg-abs-confirm-btns{display:flex;gap:10px;justify-content:center;}
.msg-abs-confirm-btn{border:none;border-radius:10px;padding:10px 22px;font-weight:800;cursor:pointer;font-family:inherit;font-size:.92rem;}
.msg-abs-confirm-btn-yes{background:linear-gradient(135deg,#2E7D32,#43A047);color:#fff;box-shadow:0 3px 10px rgba(46,125,50,.3);}
.msg-abs-confirm-btn-yes:hover{filter:brightness(1.05);}
.msg-abs-confirm-btn-no{background:#eceff1;color:#455A64;}
.msg-abs-confirm-btn-no:hover{background:#cfd8dc;}
.msg-abs-undo{position:fixed;left:0;right:0;bottom:0;background:#37474f;color:#eceff1;font-size:.82rem;padding:9px 16px;display:none;align-items:center;justify-content:center;gap:10px;z-index:10000;font-weight:600;cursor:pointer;transform:translateY(100%);transition:transform .25s ease, opacity .25s ease;opacity:0;box-shadow:0 -2px 12px rgba(0,0,0,.2);}
.msg-abs-undo.show{display:flex;transform:translateY(0);opacity:1;}
.msg-abs-undo:hover{background:#455a64;}
.msg-abs-undo-count{opacity:.7;font-variant-numeric:tabular-nums;min-width:24px;text-align:left;}
.msg-abs-all-dates{display:inline-flex;align-items:center;gap:6px;margin-top:6px;font-size:.82rem;color:#4a148c;font-weight:700;cursor:pointer;user-select:none;}
.msg-abs-all-dates input{width:auto;margin:0;cursor:pointer;accent-color:#6B3FA0;}
.msg-abs-card-date{display:inline-flex;align-items:center;gap:3px;padding:2px 8px;border-radius:10px;background:#ede7f6;color:#4a148c;font-weight:700;font-size:.74rem;}



.msg-cat-header{font-weight:800;color:#4a148c;margin:14px 0 8px;font-size:1rem;border-bottom:1.5px dashed #d1c4e9;padding-bottom:5px;}
.msg-tpl-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;}
.msg-tpl-card{position:relative;background:#f5f0ff;border:1px solid #e1d3f7;border-radius:10px;padding:12px 14px;cursor:pointer;transition:background .12s,border-color .12s;}
.msg-tpl-card:hover{background:#ede3ff;border-color:#b39ddb;}
.msg-tpl-card .mtc-name{font-weight:800;color:#4a148c;font-size:.98rem;margin-bottom:3px;padding-inline-start:22px;}
.msg-tpl-card .mtc-preview{font-size:.83rem;color:#6a5494;line-height:1.45;max-height:3em;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;padding-inline-start:22px;}
.msg-tpl-card .mtc-del{position:absolute;top:6px;inset-inline-start:6px;width:22px;height:22px;border:none;border-radius:50%;background:#fff;color:#c62828;font-weight:900;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.15);line-height:22px;font-size:14px;padding:0;}
.msg-tpl-card .mtc-del:hover{background:#ffebee;}
.msg-tpl-empty{padding:10px;color:#888;font-size:.9rem;}
.msg-compose-tools{display:flex;gap:8px;align-items:center;margin-bottom:4px;}
.msg-compose-tools .spacer{flex:1;}
.msg-back{background:#ede7f6;color:#4a148c;border:none;border-radius:8px;padding:7px 14px;font-weight:700;cursor:pointer;font-size:.9rem;display:inline-flex;align-items:center;gap:6px;font-family:inherit;}
.msg-back:hover{background:#d1c4e9;}
.msg-save-tpl{background:linear-gradient(135deg,#00897B,#26A69A);color:#fff;border:none;border-radius:8px;padding:7px 14px;font-weight:700;cursor:pointer;font-size:.9rem;font-family:inherit;}
.msg-save-tpl:hover{filter:brightness(1.05);}
.msg-label{display:block;font-weight:700;color:#4a148c;margin:14px 0 6px;font-size:.95rem;}
.msg-textarea{width:100%;min-height:130px;padding:11px 13px;border:1.5px solid #b39ddb;border-radius:10px;font-size:.97rem;background:#faf7ff;font-family:inherit;direction:rtl;resize:vertical;outline:none;}
.msg-textarea:focus{border-color:#6B3FA0;background:#fff;}
.msg-vars{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;}
.msg-var{background:linear-gradient(135deg,#00897B,#26A69A);color:#fff;border:none;padding:7px 14px;border-radius:20px;font-size:.88rem;font-weight:700;cursor:pointer;font-family:inherit;transition:transform .1s;}
.msg-var:hover{transform:translateY(-1px);}
.msg-var-custom{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);}
.msg-picker{display:flex;gap:10px;flex-wrap:wrap;margin-top:6px;}
.msg-picker-field{flex:1;min-width:180px;}
.msg-picker-field .msg-label{margin-top:6px;}
.msg-select{width:100%;padding:10px 12px;border:1.5px solid #b39ddb;border-radius:10px;font-size:.95rem;background:#faf7ff;outline:none;font-family:inherit;}
.msg-select:focus{border-color:#6B3FA0;background:#fff;}
.msg-input{width:100%;padding:10px 12px;border:1.5px solid #b39ddb;border-radius:10px;font-size:.95rem;background:#faf7ff;outline:none;font-family:inherit;}
.msg-input:focus{border-color:#6B3FA0;background:#fff;}
.msg-students-head{display:flex;justify-content:space-between;align-items:center;}
.msg-bulk{background:linear-gradient(135deg,#E65100,#FB8C00);color:#fff;border:none;border-radius:8px;padding:7px 14px;font-weight:700;cursor:pointer;font-size:.87rem;font-family:inherit;}
.msg-bulk:hover{filter:brightness(1.05);}
.msg-bulk:disabled{background:#bdbdbd;cursor:not-allowed;}
.msg-student-list{display:flex;flex-direction:column;gap:8px;margin-top:8px;}
.msg-student-row{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:#f5f0ff;border:1px solid #e1d3f7;border-radius:10px;gap:10px;}
.msg-student-name{font-weight:700;color:#4a148c;font-size:.96rem;}
.msg-wa{background:linear-gradient(135deg,#128C7E,#25D366);color:#fff;border:none;padding:7px 14px;border-radius:8px;font-weight:700;cursor:pointer;font-size:.85rem;text-decoration:none;display:inline-flex;align-items:center;gap:5px;font-family:inherit;}
.msg-wa:hover{filter:brightness(1.05);}
.msg-wa-disabled{background:#bdbdbd;cursor:not-allowed;pointer-events:none;}
.msg-empty{padding:14px;color:#888;text-align:center;font-size:.92rem;}
.msg-log-tbl{width:100%;border-collapse:collapse;font-size:.92rem;}
.msg-log-tbl th{background:#ede7f6;color:#4a148c;padding:8px 10px;text-align:right;border-bottom:2px solid #d1c4e9;font-size:.88rem;}
.msg-log-tbl td{padding:7px 10px;border-bottom:1px solid #eee;}
.msg-log-tbl tr:hover td{background:#faf7ff;}
.msg-rem-list{display:flex;flex-direction:column;gap:8px;margin-top:8px;}
.msg-rem-row{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;background:#f5f0ff;border:1px solid #e1d3f7;border-radius:10px;gap:10px;}
.msg-rem-row .mrr-main{font-weight:700;color:#4a148c;font-size:.95rem;}
.msg-rem-row .mrr-meta{font-size:.8rem;color:#6a5494;margin-top:2px;}
.msg-rem-del{background:#ffebee;color:#c62828;border:none;border-radius:8px;padding:6px 12px;font-weight:700;cursor:pointer;font-size:.82rem;font-family:inherit;}
.msg-rem-del:hover{background:#ffcdd2;}
.msg-form-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;margin-bottom:10px;}
.msg-submit{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border:none;border-radius:10px;padding:10px 28px;font-weight:800;cursor:pointer;font-family:inherit;font-size:.95rem;}
.msg-submit:hover{filter:brightness(1.05);}
.msg-submit-row{display:flex;gap:10px;justify-content:flex-end;margin-top:10px;}
.msg-cancel{background:#ede7f6;color:#4a148c;border:none;border-radius:10px;padding:10px 22px;font-weight:700;cursor:pointer;font-family:inherit;font-size:.95rem;}
</style>
<div id="msg-modal" class="msg-modal">
  <div class="msg-box">
    <div class="msg-header">
      <span class="msg-header-title">&#x1F4E9; &#x625;&#x631;&#x633;&#x627;&#x644; &#x627;&#x644;&#x631;&#x633;&#x627;&#x626;&#x644;</span>
      <button class="msg-close" onclick="msgClose()">&times;</button>
    </div>
    <div class="msg-body">
      <div id="msg-hub">
        <div class="msg-actions-row">
          <button type="button" class="msg-action-btn mab-teal" onclick="msgShowComposer()">
            <span class="mab-title">&#x1F4E4; &#x625;&#x631;&#x633;&#x627;&#x644; &#x631;&#x633;&#x627;&#x644;&#x629;</span>
            <span class="mab-desc">&#x643;&#x62A;&#x627;&#x628;&#x629; &#x631;&#x633;&#x627;&#x644;&#x629; &#x648;&#x625;&#x631;&#x633;&#x627;&#x644;&#x647;&#x627; &#x644;&#x637;&#x644;&#x628;&#x629; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</span>
          </button>
          <button type="button" class="msg-action-btn mab-purple" onclick="msgOpenLog()">
            <span class="mab-title">&#x1F4DC; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x631;&#x633;&#x627;&#x626;&#x644;</span>
            <span class="mab-desc">&#x62C;&#x645;&#x64A;&#x639; &#x627;&#x644;&#x631;&#x633;&#x627;&#x626;&#x644; &#x627;&#x644;&#x62A;&#x64A; &#x62A;&#x645; &#x625;&#x631;&#x633;&#x627;&#x644;&#x647;&#x627;</span>
          </button>
          <button type="button" class="msg-action-btn mab-orange" onclick="msgOpenReminders()">
            <span class="mab-title">&#x23F0; &#x62C;&#x62F;&#x648;&#x644;&#x629; &#x62A;&#x630;&#x643;&#x64A;&#x631;</span>
            <span class="mab-desc">&#x62C;&#x62F;&#x648;&#x644;&#x629; &#x62A;&#x630;&#x643;&#x64A;&#x631; &#x644;&#x625;&#x631;&#x633;&#x627;&#x644; &#x631;&#x633;&#x627;&#x644;&#x629; &#x641;&#x64A; &#x648;&#x642;&#x62A; &#x645;&#x62D;&#x62F;&#x62F;</span>
          </button>
          <button type="button" class="msg-action-btn mab-red" onclick="msgOpenAbsence()">
            <span class="mab-title">&#x1F6A8; &#x631;&#x633;&#x627;&#x626;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628; &#x648;&#x627;&#x644;&#x62A;&#x623;&#x62E;&#x64A;&#x631;</span>
            <span class="mab-desc">&#x625;&#x631;&#x633;&#x627;&#x644; &#x631;&#x633;&#x627;&#x626;&#x644; &#x644;&#x644;&#x63A;&#x627;&#x626;&#x628;&#x64A;&#x646; &#x648;&#x627;&#x644;&#x645;&#x62A;&#x623;&#x62E;&#x631;&#x64A;&#x646; &#x641;&#x64A; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x644;&#x64A;&#x648;&#x645; &#x645;&#x62D;&#x62F;&#x62F;</span>
          </button>
        </div>
        <div id="msg-tpl-wrap"></div>
      </div>
      <div id="msg-composer" style="display:none;">
        <div class="msg-compose-tools">
          <button type="button" class="msg-back" onclick="msgShowHub()">&#x276F; &#x631;&#x62C;&#x648;&#x639;</button>
          <span class="spacer"></span>
          <button type="button" class="msg-save-tpl" onclick="msgOpenSaveDialog()">&#x1F4BE; &#x62D;&#x641;&#x638; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</button>
        </div>
        <label class="msg-label" for="msg-tpl-picker">&#x1F4DA; &#x627;&#x62E;&#x62A;&#x631; &#x642;&#x627;&#x644;&#x628;&#x627;&#x64B; &#x645;&#x62D;&#x641;&#x648;&#x638;&#x627;&#x64B;</label>
        <select id="msg-tpl-picker" class="msg-select" onchange="msgLoadTemplateFromPicker(this)">
          <option value="">&mdash; &#x627;&#x628;&#x62F;&#x623; &#x631;&#x633;&#x627;&#x644;&#x629; &#x62C;&#x62F;&#x64A;&#x62F;&#x629; &#x623;&#x648; &#x627;&#x62E;&#x62A;&#x631; &#x642;&#x627;&#x644;&#x628;&#x627;&#x64B; &mdash;</option>
        </select>
        <label class="msg-label" for="msg-text">&#x646;&#x635; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</label>
        <textarea id="msg-text" class="msg-textarea" placeholder="&#x627;&#x643;&#x62A;&#x628; &#x642;&#x627;&#x644;&#x628; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;&#x2026;"></textarea>
        <div class="msg-vars">
          <button type="button" class="msg-var" onclick="msgInsertVar('name')">&#x1F464; &#x627;&#x644;&#x627;&#x633;&#x645;</button>
          <button type="button" class="msg-var" onclick="msgInsertVar('time')">&#x1F551; &#x627;&#x644;&#x648;&#x642;&#x62A;</button>
          <button type="button" class="msg-var" onclick="msgInsertVar('days')">&#x1F4C5; &#x627;&#x644;&#x623;&#x64A;&#x627;&#x645;</button>
          <button type="button" class="msg-var msg-var-custom" onclick="msgInsertCustomVar()">&#x2728; &#x645;&#x62A;&#x63A;&#x64A;&#x631; &#x633;</button>
        </div>
        <div class="msg-picker">
          <div class="msg-picker-field">
            <label class="msg-label" for="msg-table">&#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</label>
            <select id="msg-table" class="msg-select" onchange="msgOnTableChange()">
              <option value="">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x2014;</option>
              <option value="students">&#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</option>
              <option value="groups">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</option>
            </select>
          </div>
          <div class="msg-picker-field">
            <label class="msg-label" for="msg-col">&#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;</label>
            <select id="msg-col" class="msg-select"><option value="">&mdash;</option></select>
          </div>
        </div>
        <label class="msg-label" for="msg-group">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label>
        <select id="msg-group" class="msg-select" onchange="msgRenderStudents()">
          <option value="">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x2014;</option>
        </select>
        <div class="msg-students-head">
          <label class="msg-label" id="msg-students-label" style="display:none;margin-bottom:0;">&#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</label>
          <button type="button" id="msg-bulk-btn" class="msg-bulk" style="display:none;" onclick="msgBulkOpen()">&#x1F680; &#x641;&#x62A;&#x62D; &#x627;&#x644;&#x643;&#x644;</button>
        </div>
        <div id="msg-students" class="msg-student-list"></div>
      </div>
    </div>
  </div>
</div>
<div id="msg-save-modal" class="msg-modal">
  <div class="msg-box">
    <div class="msg-header">
      <span class="msg-header-title">&#x1F4BE; &#x62D;&#x641;&#x638; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</span>
      <button class="msg-close" onclick="msgCloseSaveDialog()">&times;</button>
    </div>
    <div class="msg-body">
      <label class="msg-label" for="msg-tpl-name">&#x627;&#x633;&#x645; &#x627;&#x644;&#x642;&#x627;&#x644;&#x628;</label>
      <input id="msg-tpl-name" class="msg-input" type="text">
      <label class="msg-label" for="msg-tpl-cat">&#x627;&#x644;&#x62A;&#x635;&#x646;&#x64A;&#x641;</label>
      <select id="msg-tpl-cat" class="msg-select">
        <option value="&#x631;&#x633;&#x627;&#x626;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;">&#x631;&#x633;&#x627;&#x626;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</option>
        <option value="&#x631;&#x633;&#x627;&#x626;&#x644; &#x627;&#x644;&#x623;&#x648;&#x642;&#x627;&#x62A;">&#x631;&#x633;&#x627;&#x626;&#x644; &#x627;&#x644;&#x623;&#x648;&#x642;&#x627;&#x62A;</option>
        <option value="&#x631;&#x633;&#x627;&#x626;&#x644; &#x627;&#x644;&#x62F;&#x641;&#x639;">&#x631;&#x633;&#x627;&#x626;&#x644; &#x627;&#x644;&#x62F;&#x641;&#x639;</option>
        <option value="&#x623;&#x62E;&#x631;&#x649;">&#x623;&#x62E;&#x631;&#x649;</option>
      </select>
      <div class="msg-submit-row">
        <button type="button" class="msg-cancel" onclick="msgCloseSaveDialog()">&#x625;&#x644;&#x63A;&#x627;&#x621;</button>
        <button type="button" class="msg-submit" onclick="msgSaveTemplate()">&#x62D;&#x641;&#x638;</button>
      </div>
    </div>
  </div>
</div>
<div id="msg-log-modal" class="msg-modal">
  <div class="msg-box">
    <div class="msg-header">
      <span class="msg-header-title">&#x1F4DC; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x631;&#x633;&#x627;&#x626;&#x644;</span>
      <button class="msg-close" onclick="msgCloseLog()">&times;</button>
    </div>
    <div class="msg-body">
      <div id="msg-log-body"></div>
    </div>
  </div>
</div>
<div id="msg-rem-modal" class="msg-modal">
  <div class="msg-box">
    <div class="msg-header">
      <span class="msg-header-title">&#x23F0; &#x62C;&#x62F;&#x648;&#x644;&#x629; &#x62A;&#x630;&#x643;&#x64A;&#x631;</span>
      <button class="msg-close" onclick="msgCloseReminders()">&times;</button>
    </div>
    <div class="msg-body">
      <div class="msg-cat-header">&#x62A;&#x630;&#x643;&#x64A;&#x631; &#x62C;&#x62F;&#x64A;&#x62F;</div>
      <div class="msg-form-grid">
        <div><label class="msg-label" for="msg-rem-name" style="margin:0 0 4px;">&#x627;&#x633;&#x645; &#x627;&#x644;&#x62A;&#x630;&#x643;&#x64A;&#x631;</label><input id="msg-rem-name" class="msg-input" type="text"></div>
        <div><label class="msg-label" for="msg-rem-day" style="margin:0 0 4px;">&#x627;&#x644;&#x64A;&#x648;&#x645;</label>
          <select id="msg-rem-day" class="msg-select">
            <option value="0">&#x627;&#x644;&#x623;&#x62D;&#x62F;</option>
            <option value="1">&#x627;&#x644;&#x627;&#x62B;&#x646;&#x64A;&#x646;</option>
            <option value="2">&#x627;&#x644;&#x62B;&#x644;&#x627;&#x62B;&#x627;&#x621;</option>
            <option value="3">&#x627;&#x644;&#x623;&#x631;&#x628;&#x639;&#x627;&#x621;</option>
            <option value="4">&#x627;&#x644;&#x62E;&#x645;&#x64A;&#x633;</option>
            <option value="5">&#x627;&#x644;&#x62C;&#x645;&#x639;&#x629;</option>
            <option value="6">&#x627;&#x644;&#x633;&#x628;&#x62A;</option>
          </select>
        </div>
        <div><label class="msg-label" for="msg-rem-time" style="margin:0 0 4px;">&#x627;&#x644;&#x648;&#x642;&#x62A;</label><input id="msg-rem-time" class="msg-input" type="time"></div>
        <div><label class="msg-label" for="msg-rem-tpl" style="margin:0 0 4px;">&#x627;&#x644;&#x642;&#x627;&#x644;&#x628;</label><select id="msg-rem-tpl" class="msg-select"></select></div>
        <div><label class="msg-label" for="msg-rem-group" style="margin:0 0 4px;">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label><select id="msg-rem-group" class="msg-select"></select></div>
      </div>
      <div class="msg-submit-row">
        <button type="button" class="msg-submit" onclick="msgSaveReminder()">&#x62D;&#x641;&#x638;</button>
      </div>
      <div class="msg-cat-header">&#x627;&#x644;&#x62A;&#x630;&#x643;&#x64A;&#x631;&#x627;&#x62A; &#x627;&#x644;&#x62D;&#x627;&#x644;&#x64A;&#x629;</div>
      <div id="msg-rem-list" class="msg-rem-list"></div>
    </div>
  </div>
</div>
<div id="msg-abs-modal" class="msg-modal">
  <div class="msg-box">
    <div class="msg-header" style="background:linear-gradient(135deg,#c0392b,#e74c3c);">
      <span class="msg-header-title">&#x1F6A8; &#x631;&#x633;&#x627;&#x626;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628; &#x648;&#x627;&#x644;&#x62A;&#x623;&#x62E;&#x64A;&#x631;</span>
      <button class="msg-close" onclick="msgCloseAbsence()">&times;</button>
    </div>
    <div class="msg-body">
      <div class="msg-abs-stats">
        <div class="msg-abs-stat msg-abs-stat-absent">
          <div class="msg-abs-stat-top"><span class="msg-abs-stat-icon">&#x1F534;</span></div>
          <div class="msg-abs-stat-num" id="msg-abs-gs-absent">&ndash;</div>
          <div class="msg-abs-stat-lbl">&#x63A;&#x627;&#x626;&#x628;&#x648;&#x646; &#x627;&#x644;&#x64A;&#x648;&#x645;</div>
        </div>
        <div class="msg-abs-stat msg-abs-stat-late">
          <div class="msg-abs-stat-top"><span class="msg-abs-stat-icon">&#x23F0;</span></div>
          <div class="msg-abs-stat-num" id="msg-abs-gs-late">&ndash;</div>
          <div class="msg-abs-stat-lbl">&#x645;&#x62A;&#x623;&#x62E;&#x631;&#x648;&#x646; &#x627;&#x644;&#x64A;&#x648;&#x645;</div>
        </div>
        <div class="msg-abs-stat msg-abs-stat-sent">
          <div class="msg-abs-stat-top"><span class="msg-abs-stat-icon">&#x2705;</span></div>
          <div class="msg-abs-stat-num" id="msg-abs-gs-sent">&ndash;</div>
          <div class="msg-abs-stat-lbl">&#x62A;&#x645; &#x625;&#x631;&#x633;&#x627;&#x644; &#x631;&#x633;&#x627;&#x626;&#x644; (&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A;)</div>
        </div>
        <div class="msg-abs-stat msg-abs-stat-never">
          <div class="msg-abs-stat-top"><span class="msg-abs-stat-icon">&#x26A0;&#xFE0F;</span></div>
          <div class="msg-abs-stat-num" id="msg-abs-gs-never">&ndash;</div>
          <div class="msg-abs-stat-lbl">&#x644;&#x645; &#x62A;&#x64F;&#x631;&#x633;&#x644; &#x644;&#x647;&#x645; &#x631;&#x633;&#x627;&#x626;&#x644; (&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A;)</div>
        </div>
      </div>
      <div class="msg-form-grid">
        <div>
          <label class="msg-label" for="msg-abs-date" style="margin:0 0 4px;">&#x627;&#x644;&#x62A;&#x627;&#x631;&#x64A;&#x62E;</label>
          <input id="msg-abs-date" class="msg-input" type="date" onchange="msgAbsenceLoad()">
          <label class="msg-abs-all-dates"><input type="checkbox" id="msg-abs-all-dates-chk" onchange="msgAbsenceToggleAllDates()"> &#x1F5D3;&#xFE0F; &#x62C;&#x645;&#x64A;&#x639; &#x627;&#x644;&#x62A;&#x648;&#x627;&#x631;&#x64A;&#x62E;</label>
        </div>
        <div>
          <label class="msg-label" for="msg-abs-group" style="margin:0 0 4px;">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label>
          <select id="msg-abs-group" class="msg-select" onchange="msgAbsenceLoad()">
            <option value="">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x2014;</option>
            <option value="__all__">&#x1F310; &#x62C;&#x645;&#x64A;&#x639; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</option>
          </select>
        </div>
      </div>
      <div id="msg-abs-alert" class="msg-abs-alert" style="display:none;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x648;&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x644;&#x639;&#x631;&#x636; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</div>
      <div id="msg-abs-filters" class="msg-abs-filters" style="display:none;">
        <button type="button" class="msg-abs-filter active" data-filter="unsent" onclick="msgAbsenceSetFilter('unsent')">
          &#x1F534; <span>&#x628;&#x62F;&#x648;&#x646; &#x631;&#x633;&#x627;&#x644;&#x629;</span>
          <span class="msg-abs-filter-count" id="msg-abs-fc-unsent">0</span>
        </button>
        <button type="button" class="msg-abs-filter" data-filter="sent" onclick="msgAbsenceSetFilter('sent')">
          &#x2705; <span>&#x62A;&#x645; &#x627;&#x644;&#x625;&#x631;&#x633;&#x627;&#x644;</span>
          <span class="msg-abs-filter-count" id="msg-abs-fc-sent">0</span>
        </button>
        <button type="button" class="msg-abs-filter" data-filter="all" onclick="msgAbsenceSetFilter('all')">
          &#x1F4CB; <span>&#x627;&#x644;&#x643;&#x644;</span>
          <span class="msg-abs-filter-count" id="msg-abs-fc-all">0</span>
        </button>
        <span class="msg-abs-spacer"></span>
        <button type="button" id="msg-abs-bulk-btn" class="msg-bulk" onclick="msgAbsenceBulk()">&#x1F680; &#x641;&#x62A;&#x62D; &#x627;&#x644;&#x643;&#x644;</button>
      </div>
      <div id="msg-abs-status" class="msg-empty" style="display:none;"></div>
      <div id="msg-abs-section-unsent" class="msg-abs-section" style="display:none;">
        <div class="msg-abs-section-title">
          <span>&#x1F534; &#x628;&#x62D;&#x627;&#x62C;&#x629; &#x625;&#x644;&#x649; &#x631;&#x633;&#x627;&#x644;&#x629;</span>
          <span class="msg-abs-section-count" id="msg-abs-unsent-count">0</span>
        </div>
        <div id="msg-abs-unsent-list" class="msg-abs-card-list"></div>
      </div>
      <div id="msg-abs-section-sent" class="msg-abs-section" style="display:none;">
        <div class="msg-abs-section-title">
          <span>&#x2705; &#x62A;&#x645; &#x627;&#x644;&#x625;&#x631;&#x633;&#x627;&#x644;</span>
          <span class="msg-abs-section-count" id="msg-abs-sent-count">0</span>
        </div>
        <div id="msg-abs-sent-list" class="msg-abs-card-list"></div>
      </div>
    </div>
  </div>
</div>
<div id="msg-abs-confirm" class="msg-abs-confirm">
  <div class="msg-abs-confirm-box">
    <div class="msg-abs-confirm-title">&#x647;&#x644; &#x623;&#x631;&#x633;&#x644;&#x62A; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629; &#x641;&#x639;&#x644;&#x627;&#x64B;&#x61F;</div>
    <div class="msg-abs-confirm-sub" id="msg-abs-confirm-name"></div>
    <div class="msg-abs-confirm-btns">
      <button type="button" id="msg-abs-confirm-no"  class="msg-abs-confirm-btn msg-abs-confirm-btn-no">&#x644;&#x627; &#x625;&#x644;&#x63A;&#x627;&#x621;</button>
      <button type="button" id="msg-abs-confirm-yes" class="msg-abs-confirm-btn msg-abs-confirm-btn-yes">&#x646;&#x639;&#x645; &#x623;&#x631;&#x633;&#x644;&#x62A;</button>
    </div>
  </div>
</div>
<div id="msg-abs-undo" class="msg-abs-undo">
  <span id="msg-abs-undo-text"></span>
  <span id="msg-abs-undo-count" class="msg-abs-undo-count"></span>
</div>
<script>
var _msgGroups = [];
var _msgStudentsByGroup = {};
var _msgTableColumns = { students: [], groups: [] };
var _msgTemplates = [];
var _msgReminders = [];
var _msgCurrentTemplateName = '';
var _msgLoaded = false;
var _msgSchedulerStarted = false;
var _MSG_CATEGORIES = ['\u0631\u0633\u0627\u0626\u0644 \u0627\u0644\u063A\u064A\u0627\u0628', '\u0631\u0633\u0627\u0626\u0644 \u0627\u0644\u0623\u0648\u0642\u0627\u062A', '\u0631\u0633\u0627\u0626\u0644 \u0627\u0644\u062F\u0641\u0639', '\u0623\u062E\u0631\u0649'];
var _MSG_DAY_NAMES  = ['\u0627\u0644\u0623\u062D\u062F','\u0627\u0644\u0627\u062B\u0646\u064A\u0646','\u0627\u0644\u062B\u0644\u0627\u062B\u0627\u0621','\u0627\u0644\u0623\u0631\u0628\u0639\u0627\u0621','\u0627\u0644\u062E\u0645\u064A\u0633','\u0627\u0644\u062C\u0645\u0639\u0629','\u0627\u0644\u0633\u0628\u062A'];

function msgOpen(){
  document.getElementById('msg-modal').style.display='block';
  msgShowHub();
  msgStartScheduler();
  if (_msgLoaded) { _msgRefreshTemplates(); return; }
  _msgLoaded = true;
  Promise.all([
    fetch('/api/groups',{credentials:'include'}).then(function(r){return r.json();}),
    fetch('/api/students',{credentials:'include'}).then(function(r){return r.json();}),
    fetch('/api/columns',{credentials:'include'}).then(function(r){return r.json();}).catch(function(){return {columns:[]};}),
    fetch('/api/group-columns',{credentials:'include'}).then(function(r){return r.json();}).catch(function(){return {columns:[]};})
  ]).then(function(res){
    _msgGroups = (res[0] && res[0].groups) ? res[0].groups : [];
    var students = (res[1] && res[1].students) ? res[1].students : [];
    _msgStudentsByGroup = {};
    for (var i=0; i<students.length; i++) {
      var s = students[i];
      var g = (s.group_name_student || '').trim();
      if (!g) continue;
      if (!_msgStudentsByGroup[g]) _msgStudentsByGroup[g] = [];
      _msgStudentsByGroup[g].push(s);
    }
    _msgTableColumns.students = _msgBuildColumnList((res[2] && res[2].columns) || [], students[0]);
    _msgTableColumns.groups   = _msgBuildColumnList((res[3] && res[3].columns) || [], _msgGroups[0]);
    _msgPopulateGroupSelects();
    _msgRefreshTemplates();
  }).catch(function(){ _msgLoaded = false; });
}
function _msgPopulateGroupSelects(){
  var targets = ['msg-group','msg-rem-group'];
  var seen = {};
  var names = [];
  for (var i=0; i<_msgGroups.length; i++) {
    var n = (_msgGroups[i].group_name || '').trim();
    if (!n || seen[n]) continue;
    seen[n] = 1; names.push(n);
  }
  targets.forEach(function(id){
    var sel = document.getElementById(id); if (!sel) return;
    var first = sel.options[0]; sel.innerHTML = '';
    if (id === 'msg-group') { sel.appendChild(new Option('\u2014 \u0627\u062E\u062A\u0631 \u0645\u062C\u0645\u0648\u0639\u0629 \u2014','')); }
    else { sel.appendChild(new Option('\u0627\u062E\u062A\u0631 \u0645\u062C\u0645\u0648\u0639\u0629','')); }
    names.forEach(function(n){ sel.appendChild(new Option(n, n)); });
  });
}
function msgClose(){ document.getElementById('msg-modal').style.display='none'; }
function msgShowHub(){
  document.getElementById('msg-hub').style.display='block';
  document.getElementById('msg-composer').style.display='none';
}
function msgShowComposer(){
  document.getElementById('msg-hub').style.display='none';
  document.getElementById('msg-composer').style.display='block';
}
function _msgInsertAtCursor(token){
  var ta = document.getElementById('msg-text');
  var start = ta.selectionStart != null ? ta.selectionStart : ta.value.length;
  var end = ta.selectionEnd != null ? ta.selectionEnd : ta.value.length;
  ta.value = ta.value.substring(0, start) + token + ta.value.substring(end);
  var pos = start + token.length;
  ta.focus();
  try { ta.setSelectionRange(pos, pos); } catch(e){}
}
function msgInsertVar(kind){
  var map = { name:'{\u0627\u0633\u0645}', time:'{\u0648\u0642\u062A}', days:'{\u0623\u064A\u0627\u0645}' };
  if (map[kind]) _msgInsertAtCursor(map[kind]);
}
function msgInsertCustomVar(){
  var t = document.getElementById('msg-table').value;
  var c = document.getElementById('msg-col').value;
  if (!t || !c) return;
  _msgInsertAtCursor('{' + t + ':' + c + '}');
}
function _msgDecodeEntities(s){
  var d = document.createElement('textarea');
  d.innerHTML = String(s == null ? '' : s);
  return d.value;
}
function _msgBuildColumnList(labelRows, sampleRow){
  var keys = []; var seen = {};
  labelRows.forEach(function(r){
    if (!r || !r.col_key) return;
    seen[r.col_key] = 1;
    keys.push({ key: r.col_key, label: _msgDecodeEntities(r.col_label || r.col_key) });
  });
  if (sampleRow) {
    Object.keys(sampleRow).forEach(function(k){
      if (seen[k] || k === 'id' || k === 'created_at') return;
      keys.push({ key: k, label: k });
    });
  }
  return keys;
}
function msgOnTableChange(){
  var t = document.getElementById('msg-table').value;
  var sel = document.getElementById('msg-col');
  sel.innerHTML = '<option value="">—</option>';
  (_msgTableColumns[t] || []).forEach(function(c){
    var opt = document.createElement('option');
    opt.value = c.key; opt.textContent = c.label + ' (' + c.key + ')';
    sel.appendChild(opt);
  });
}
function _msgFindGroup(name){
  for (var i=0; i<_msgGroups.length; i++) {
    if ((_msgGroups[i].group_name || '') === name) return _msgGroups[i];
  }
  return null;
}
function _msgCleanPhone(raw){
  var digits = String(raw || '').replace(/[^0-9]/g, '');
  if (!digits) return '';
  if (digits.indexOf('00') === 0) digits = digits.substring(2);
  if (digits.length === 8) digits = '973' + digits;
  return digits;
}
function _msgFill(tpl, student, group){
  var name = (student && student.student_name) || '';
  var time = (group && group.study_time) || '';
  var days = (group && group.study_days) || '';
  var text = String(tpl || '')
    .replace(/\{\u0627\u0633\u0645\}/g, name)
    .replace(/\{\u0648\u0642\u062A\}/g, time)
    .replace(/\{\u0623\u064A\u0627\u0645\}/g, days);
  text = text.replace(/\{(students|groups):([A-Za-z0-9_]+)\}/g, function(_m, table, col){
    var src = table === 'students' ? student : group;
    if (!src) return '';
    var v = src[col];
    return (v == null) ? '' : String(v);
  });
  return text;
}
function msgRenderStudents(){
  var gname = document.getElementById('msg-group').value;
  var wrap = document.getElementById('msg-students');
  var lbl = document.getElementById('msg-students-label');
  var bulk = document.getElementById('msg-bulk-btn');
  wrap.innerHTML = '';
  if (!gname) { lbl.style.display = 'none'; bulk.style.display = 'none'; return; }
  lbl.style.display = 'block'; bulk.style.display = 'inline-block';
  var students = _msgStudentsByGroup[gname] || [];
  if (!students.length) {
    var empty = document.createElement('div');
    empty.className = 'msg-empty';
    empty.textContent = '\u0644\u0627 \u064A\u0648\u062C\u062F \u0637\u0644\u0628\u0629 \u0641\u064A \u0647\u0630\u0647 \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629';
    wrap.appendChild(empty);
    return;
  }
  students.forEach(function(s){
    var row = document.createElement('div');
    row.className = 'msg-student-row';
    var nameSpan = document.createElement('span');
    nameSpan.className = 'msg-student-name';
    nameSpan.textContent = s.student_name || '-';
    row.appendChild(nameSpan);
    var phone = _msgCleanPhone(s.whatsapp);
    if (phone) {
      var btn = document.createElement('button');
      btn.type = 'button'; btn.className = 'msg-wa';
      btn.textContent = '\u0648\u0627\u062A\u0633\u0627\u0628';
      btn.addEventListener('click', (function(student, groupName){
        return function(){ _msgOpenWa(student, groupName); };
      })(s, gname));
      row.appendChild(btn);
    } else {
      var span = document.createElement('span');
      span.className = 'msg-wa msg-wa-disabled';
      span.textContent = '\u0644\u0627 \u064A\u0648\u062C\u062F \u0631\u0642\u0645';
      row.appendChild(span);
    }
    wrap.appendChild(row);
  });
}
function _msgOpenWa(student, gname){
  var phone = _msgCleanPhone(student && student.whatsapp);
  if (!phone) return;
  var group = _msgFindGroup(gname);
  var tpl = document.getElementById('msg-text').value || '';
  var text = _msgFill(tpl, student, group);
  var url = 'https://wa.me/' + phone + (text ? ('?text=' + encodeURIComponent(text)) : '');
  window.open(url, '_blank');
  _msgLogSend(student, phone);
}
function _msgLogSend(student, phone){
  var body = {
    student_name: (student && student.student_name) || '',
    student_whatsapp: phone || ((student && student.whatsapp) || ''),
    template_name: _msgCurrentTemplateName || '\u0631\u0633\u0627\u0644\u0629 \u0645\u062E\u0635\u0635\u0629'
  };
  fetch('/api/message-log', { method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify(body) }).catch(function(){});
}
function msgBulkOpen(){
  var gname = document.getElementById('msg-group').value;
  if (!gname) { alert('\u0627\u062E\u062A\u0631 \u0645\u062C\u0645\u0648\u0639\u0629 \u0623\u0648\u0644\u0627\u064B'); return; }
  var students = _msgStudentsByGroup[gname] || [];
  var targets = students.filter(function(s){ return _msgCleanPhone(s.whatsapp); });
  if (!targets.length) { alert('\u0644\u0627 \u064A\u0648\u062C\u062F \u0623\u064A \u0637\u0627\u0644\u0628 \u0628\u0631\u0642\u0645 \u0648\u0627\u062A\u0633\u0627\u0628 \u0635\u0627\u0644\u062D \u0641\u064A \u0647\u0630\u0647 \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629'); return; }
  if (targets.length > 1 && !confirm('\u0633\u064A\u062A\u0645 \u0641\u062A\u062D \u0639\u062F\u0629 \u0646\u0648\u0627\u0641\u0630 \u0648\u0627\u062A\u0633\u0627\u0628 \u2014 \u0647\u0644 \u062A\u0631\u064A\u062F \u0627\u0644\u0645\u062A\u0627\u0628\u0639\u0629\u061F')) return;
  var group = _msgFindGroup(gname);
  var tpl = document.getElementById('msg-text').value || '';
  targets.forEach(function(s, idx){
    var phone = _msgCleanPhone(s.whatsapp);
    var text = _msgFill(tpl, s, group);
    var url = 'https://wa.me/' + phone + (text ? ('?text=' + encodeURIComponent(text)) : '');
    setTimeout(function(){ window.open(url, '_blank'); _msgLogSend(s, phone); }, idx * 400);
  });
}

// ---- Templates ----
function _msgRefreshTemplates(){
  return fetch('/api/message-templates',{credentials:'include'}).then(function(r){return r.json();}).then(function(d){
    _msgTemplates = (d && d.templates) || [];
    _msgRenderTemplateList();
    _msgPopulateReminderTemplateSelect();
    _msgPopulateTemplatePicker();
  });
}
function _msgPopulateTemplatePicker(){
  var sel = document.getElementById('msg-tpl-picker'); if (!sel) return;
  var prev = sel.value;
  sel.innerHTML = '';
  sel.appendChild(new Option('\u2014 \u0627\u0628\u062F\u0623 \u0631\u0633\u0627\u0644\u0629 \u062C\u062F\u064A\u062F\u0629 \u0623\u0648 \u0627\u062E\u062A\u0631 \u0642\u0627\u0644\u0628\u0627\u064B \u2014', ''));
  if (!_msgTemplates.length) return;
  var byCat = {};
  _msgTemplates.forEach(function(t){
    var cat = t.category || _MSG_CATEGORIES[_MSG_CATEGORIES.length - 1];
    if (!byCat[cat]) byCat[cat] = [];
    byCat[cat].push(t);
  });
  var order = _MSG_CATEGORIES.slice();
  Object.keys(byCat).forEach(function(c){ if (order.indexOf(c) < 0) order.push(c); });
  order.forEach(function(cat){
    var rows = byCat[cat] || []; if (!rows.length) return;
    var og = document.createElement('optgroup'); og.label = cat;
    rows.forEach(function(t){ og.appendChild(new Option(t.name || '-', String(t.id))); });
    sel.appendChild(og);
  });
  // Preserve previous selection if the template still exists.
  if (prev) {
    for (var i=0; i<sel.options.length; i++) { if (sel.options[i].value === prev) { sel.value = prev; return; } }
  }
}
function msgLoadTemplateFromPicker(sel){
  var id = sel.value;
  if (!id) return;
  var tpl = null;
  for (var i=0; i<_msgTemplates.length; i++) { if (String(_msgTemplates[i].id) === String(id)) { tpl = _msgTemplates[i]; break; } }
  if (!tpl) return;
  _msgCurrentTemplateName = tpl.name || '';
  document.getElementById('msg-text').value = tpl.content || '';
}
function _msgRenderTemplateList(){
  var wrap = document.getElementById('msg-tpl-wrap');
  wrap.innerHTML = '';
  if (!_msgTemplates.length) {
    var h = document.createElement('div'); h.className = 'msg-cat-header'; h.textContent = '\u0627\u0644\u0642\u0648\u0627\u0644\u0628 \u0627\u0644\u0645\u062D\u0641\u0648\u0638\u0629'; wrap.appendChild(h);
    var e = document.createElement('div'); e.className = 'msg-tpl-empty'; e.textContent = '\u0644\u0627 \u062A\u0648\u062C\u062F \u0642\u0648\u0627\u0644\u0628 \u0645\u062D\u0641\u0648\u0638\u0629 \u0628\u0639\u062F'; wrap.appendChild(e);
    return;
  }
  var byCat = {};
  _msgTemplates.forEach(function(t){
    var cat = t.category || '\u0623\u062E\u0631\u0649';
    if (!byCat[cat]) byCat[cat] = [];
    byCat[cat].push(t);
  });
  var order = _MSG_CATEGORIES.slice();
  Object.keys(byCat).forEach(function(c){ if (order.indexOf(c) < 0) order.push(c); });
  order.forEach(function(cat){
    var rows = byCat[cat] || []; if (!rows.length) return;
    var h = document.createElement('div'); h.className = 'msg-cat-header'; h.textContent = cat; wrap.appendChild(h);
    var list = document.createElement('div'); list.className = 'msg-tpl-list';
    rows.forEach(function(t){
      var card = document.createElement('div'); card.className = 'msg-tpl-card';
      var del = document.createElement('button'); del.type='button'; del.className='mtc-del'; del.textContent='×';
      del.title = '\u062D\u0630\u0641';
      del.addEventListener('click', function(ev){ ev.stopPropagation(); _msgDeleteTemplate(t.id); });
      card.appendChild(del);
      var name = document.createElement('div'); name.className='mtc-name'; name.textContent = t.name || '-'; card.appendChild(name);
      var prev = document.createElement('div'); prev.className='mtc-preview'; prev.textContent = t.content || ''; card.appendChild(prev);
      card.addEventListener('click', function(){ _msgLoadTemplate(t); });
      list.appendChild(card);
    });
    wrap.appendChild(list);
  });
}
function _msgLoadTemplate(t){
  _msgCurrentTemplateName = t.name || '';
  document.getElementById('msg-text').value = t.content || '';
  var pick = document.getElementById('msg-tpl-picker'); if (pick) pick.value = String(t.id || '');
  msgShowComposer();
}
function _msgDeleteTemplate(id){
  if (!confirm('\u062D\u0630\u0641 \u0647\u0630\u0627 \u0627\u0644\u0642\u0627\u0644\u0628\u061F')) return;
  fetch('/api/message-templates/' + id, { method:'DELETE', credentials:'include' })
    .then(function(){ return _msgRefreshTemplates(); });
}
function msgOpenSaveDialog(){
  var content = (document.getElementById('msg-text').value || '').trim();
  if (!content) return;
  document.getElementById('msg-tpl-name').value = _msgCurrentTemplateName || '';
  document.getElementById('msg-save-modal').style.display = 'block';
}
function msgCloseSaveDialog(){ document.getElementById('msg-save-modal').style.display = 'none'; }
function msgSaveTemplate(){
  var name = (document.getElementById('msg-tpl-name').value || '').trim();
  var cat = document.getElementById('msg-tpl-cat').value || '\u0623\u062E\u0631\u0649';
  var content = document.getElementById('msg-text').value || '';
  if (!name || !content.trim()) return;
  fetch('/api/message-templates', { method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify({name:name, category:cat, content:content}) })
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d && d.ok) { _msgCurrentTemplateName = name; msgCloseSaveDialog(); _msgRefreshTemplates(); }
    });
}

// ---- Log ----
function msgOpenLog(){
  document.getElementById('msg-log-modal').style.display = 'block';
  var body = document.getElementById('msg-log-body'); body.innerHTML = '';
  fetch('/api/message-log',{credentials:'include'}).then(function(r){return r.json();}).then(function(d){
    var rows = (d && d.log) || [];
    if (!rows.length) { body.innerHTML = '<div class="msg-empty">\u0644\u0627 \u062A\u0648\u062C\u062F \u0631\u0633\u0627\u0626\u0644 \u0645\u0633\u062C\u0644\u0629</div>'; return; }
    var tbl = document.createElement('table'); tbl.className = 'msg-log-tbl';
    var thead = document.createElement('thead');
    var trh = document.createElement('tr');
    ['\u0627\u0644\u062A\u0627\u0631\u064A\u062E','\u0627\u0644\u0637\u0627\u0644\u0628','\u0627\u0644\u0648\u0627\u062A\u0633\u0627\u0628','\u0627\u0644\u0642\u0627\u0644\u0628'].forEach(function(h){
      var th = document.createElement('th'); th.textContent = h; trh.appendChild(th);
    });
    thead.appendChild(trh); tbl.appendChild(thead);
    var tbody = document.createElement('tbody');
    rows.forEach(function(r){
      var tr = document.createElement('tr');
      [r.sent_at, r.student_name, r.student_whatsapp, r.template_name].forEach(function(v){
        var td = document.createElement('td'); td.textContent = v || '-'; tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tbl.appendChild(tbody);
    body.appendChild(tbl);
  });
}
function msgCloseLog(){ document.getElementById('msg-log-modal').style.display = 'none'; }

// ---- Reminders ----
function _msgPopulateReminderTemplateSelect(){
  var sel = document.getElementById('msg-rem-tpl'); if (!sel) return;
  sel.innerHTML = '';
  sel.appendChild(new Option('\u0627\u062E\u062A\u0631 \u0642\u0627\u0644\u0628\u0627\u064B', ''));
  _msgTemplates.forEach(function(t){ sel.appendChild(new Option((t.name || '') + ' (' + (t.category || '') + ')', String(t.id))); });
}
function msgOpenReminders(){
  _msgPopulateReminderTemplateSelect();
  _msgPopulateGroupSelects();
  _msgLoadReminders();
  document.getElementById('msg-rem-modal').style.display = 'block';
}
function msgCloseReminders(){ document.getElementById('msg-rem-modal').style.display = 'none'; }
function _msgLoadReminders(){
  return fetch('/api/message-reminders',{credentials:'include'}).then(function(r){return r.json();}).then(function(d){
    _msgReminders = (d && d.reminders) || [];
    _msgRenderReminders();
  });
}
function _msgRenderReminders(){
  var wrap = document.getElementById('msg-rem-list'); wrap.innerHTML = '';
  if (!_msgReminders.length) {
    var e = document.createElement('div'); e.className = 'msg-empty'; e.textContent = '\u0644\u0627 \u062A\u0648\u062C\u062F \u062A\u0630\u0643\u064A\u0631\u0627\u062A \u0645\u062C\u062F\u0648\u0644\u0629'; wrap.appendChild(e); return;
  }
  _msgReminders.forEach(function(r){
    var row = document.createElement('div'); row.className = 'msg-rem-row';
    var tplName = '';
    for (var i=0; i<_msgTemplates.length; i++) {
      if (String(_msgTemplates[i].id) === String(r.template_id)) { tplName = _msgTemplates[i].name; break; }
    }
    var left = document.createElement('div');
    var main = document.createElement('div'); main.className = 'mrr-main'; main.textContent = r.name || '-'; left.appendChild(main);
    var meta = document.createElement('div'); meta.className = 'mrr-meta';
    meta.textContent = _MSG_DAY_NAMES[r.day_of_week || 0] + ' · ' + (r.time_of_day || '') + ' · ' + (tplName || '?') + ' · ' + (r.group_name || '');
    left.appendChild(meta);
    row.appendChild(left);
    var del = document.createElement('button'); del.type='button'; del.className='msg-rem-del'; del.textContent = '\u062D\u0630\u0641';
    del.addEventListener('click', function(){ _msgDeleteReminder(r.id); });
    row.appendChild(del);
    wrap.appendChild(row);
  });
}
function msgSaveReminder(){
  var body = {
    name: (document.getElementById('msg-rem-name').value || '').trim(),
    day_of_week: parseInt(document.getElementById('msg-rem-day').value || '0', 10),
    time_of_day: (document.getElementById('msg-rem-time').value || '').trim(),
    template_id: parseInt(document.getElementById('msg-rem-tpl').value || '0', 10),
    group_name: document.getElementById('msg-rem-group').value || ''
  };
  if (!body.name || !body.time_of_day || !body.template_id || !body.group_name) return;
  fetch('/api/message-reminders', { method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify(body) })
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d && d.ok) {
        ['msg-rem-name','msg-rem-time','msg-rem-group'].forEach(function(id){ var el = document.getElementById(id); if (el) el.value=''; });
        _msgLoadReminders();
      }
    });
  _msgRequestNotificationPermission();
}
function _msgDeleteReminder(id){
  if (!confirm('\u062D\u0630\u0641 \u0647\u0630\u0627 \u0627\u0644\u062A\u0630\u0643\u064A\u0631\u061F')) return;
  fetch('/api/message-reminders/' + id, { method:'DELETE', credentials:'include' })
    .then(function(){ _msgLoadReminders(); });
}

// ---- Scheduler ----
function _msgRequestNotificationPermission(){
  if (typeof Notification === 'undefined') return;
  if (Notification.permission === 'default') { try { Notification.requestPermission(); } catch(e){} }
}
function msgStartScheduler(){
  if (_msgSchedulerStarted) return;
  _msgSchedulerStarted = true;
  _msgRequestNotificationPermission();
  // Initial load of reminders + templates even if composer hasn't been opened.
  fetch('/api/message-reminders',{credentials:'include'}).then(function(r){return r.json();}).then(function(d){ _msgReminders = (d && d.reminders) || []; }).catch(function(){});
  fetch('/api/message-templates',{credentials:'include'}).then(function(r){return r.json();}).then(function(d){ _msgTemplates = (d && d.templates) || []; }).catch(function(){});
  _msgCheckReminders();
  setInterval(_msgCheckReminders, 30 * 1000);
  // Reload list every 10 min so edits in another tab propagate.
  setInterval(function(){
    fetch('/api/message-reminders',{credentials:'include'}).then(function(r){return r.json();}).then(function(d){ _msgReminders = (d && d.reminders) || []; }).catch(function(){});
    fetch('/api/message-templates',{credentials:'include'}).then(function(r){return r.json();}).then(function(d){ _msgTemplates = (d && d.templates) || []; }).catch(function(){});
  }, 10 * 60 * 1000);
}
function _msgCheckReminders(){
  if (!_msgReminders.length) return;
  var now = new Date();
  var day = now.getDay();
  var mins = now.getHours() * 60 + now.getMinutes();
  var todayKey = now.getFullYear() + '-' + (now.getMonth()+1) + '-' + now.getDate();
  _msgReminders.forEach(function(r){
    if (!r || r.enabled === 0) return;
    if (parseInt(r.day_of_week, 10) !== day) return;
    var tparts = (r.time_of_day || '').split(':');
    var rMin = parseInt(tparts[0] || '0', 10) * 60 + parseInt(tparts[1] || '0', 10);
    if (mins < rMin) return;
    // Only fire within 5 minutes of the target to avoid spamming on late loads.
    if (mins - rMin > 5) return;
    var storageKey = 'msg_rem_' + r.id + '_' + todayKey;
    if (localStorage.getItem(storageKey)) return;
    localStorage.setItem(storageKey, '1');
    _msgFireReminder(r);
  });
}
function _msgFireReminder(r){
  if (typeof Notification === 'undefined') return;
  if (Notification.permission !== 'granted') { _msgRequestNotificationPermission(); return; }
  var body = '\u0631\u0633\u0627\u0644\u0629 \u062C\u062F\u064A\u062F\u0629: ' + (r.name || '') + ' · ' + (r.group_name || '');
  try {
    var n = new Notification('\u062A\u0630\u0643\u064A\u0631 \u0645\u0650\u0646 \u0625\u0631\u0633\u0627\u0644 \u0627\u0644\u0631\u0633\u0627\u0626\u0644', { body: body, tag: 'msg-rem-' + r.id });
    n.onclick = function(){
      try { window.focus(); } catch(e){}
      msgOpen();
      var tpl = null;
      for (var i=0; i<_msgTemplates.length; i++) {
        if (String(_msgTemplates[i].id) === String(r.template_id)) { tpl = _msgTemplates[i]; break; }
      }
      if (tpl) _msgLoadTemplate(tpl); else msgShowComposer();
      var gsel = document.getElementById('msg-group');
      if (gsel && r.group_name) { gsel.value = r.group_name; msgRenderStudents(); }
      try { n.close(); } catch(e){}
    };
  } catch(e) {}
}

var _msgAbsenceRows = [];
var _msgAbsenceFilter = 'unsent';
var _MSG_ABS_DAYS = ['\u0627\u0644\u0623\u062D\u062F','\u0627\u0644\u0627\u062B\u0646\u064A\u0646','\u0627\u0644\u062B\u0644\u0627\u062B\u0627\u0621','\u0627\u0644\u0623\u0631\u0628\u0639\u0627\u0621','\u0627\u0644\u062E\u0645\u064A\u0633','\u0627\u0644\u062C\u0645\u0639\u0629','\u0627\u0644\u0633\u0628\u062A'];
var _msgAbsUndoTimeout = null;
var _msgAbsUndoTick = null;
var _msgAbsUndoActive = false;

function msgOpenAbsence(){
  document.getElementById('msg-abs-modal').style.display = 'block';
  _msgAbsencePopulateGroups();
  _msgAbsenceRefreshGeneralStats();
  var d = document.getElementById('msg-abs-date');
  if (!d.value) {
    var now = new Date();
    var m = String(now.getMonth()+1).padStart(2,'0');
    var day = String(now.getDate()).padStart(2,'0');
    d.value = now.getFullYear()+'-'+m+'-'+day;
  }
  _msgAbsenceSetFilterButton('unsent');
  _msgAbsenceFilter = 'unsent';
  if (document.getElementById('msg-abs-group').value) msgAbsenceLoad();
  else _msgAbsenceResetView('\u0627\u062E\u062A\u0631 \u0627\u0644\u062A\u0627\u0631\u064A\u062E \u0648\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 \u0644\u0639\u0631\u0636 \u0627\u0644\u0637\u0644\u0628\u0629');
}
function msgCloseAbsence(){
  document.getElementById('msg-abs-modal').style.display = 'none';
  _msgAbsenceHideUndo();
}
function msgAbsenceToggleAllDates(){
  var chk = document.getElementById('msg-abs-all-dates-chk');
  var dateInp = document.getElementById('msg-abs-date');
  if (chk && chk.checked) {
    dateInp.disabled = true;
    dateInp.classList.add('msg-input-disabled');
  } else {
    dateInp.disabled = false;
    dateInp.classList.remove('msg-input-disabled');
  }
  msgAbsenceLoad();
}

function _msgAbsenceResetView(message){
  document.getElementById('msg-abs-alert').style.display = 'none';
  document.getElementById('msg-abs-filters').style.display = 'none';
  document.getElementById('msg-abs-section-unsent').style.display = 'none';
  document.getElementById('msg-abs-section-sent').style.display = 'none';
  var status = document.getElementById('msg-abs-status');
  if (message) { status.style.display = 'block'; status.textContent = message; }
  else { status.style.display = 'none'; }
}

function _msgAbsencePopulateGroups(){
  var sel = document.getElementById('msg-abs-group'); if (!sel) return;
  var previous = sel.value;
  // Preserve the two fixed options at the top: the placeholder and جميع المجموعات.
  var keep = [];
  for (var i=0; i<sel.options.length; i++) {
    var v = sel.options[i].value;
    if (v === '' || v === '__all__') keep.push(sel.options[i].cloneNode(true));
  }
  fetch('/api/attendance/groups',{credentials:'include'}).then(function(r){ return r.json(); }).then(function(data){
    sel.innerHTML = '';
    keep.forEach(function(o){ sel.appendChild(o); });
    (Array.isArray(data) ? data : []).forEach(function(n){
      n = (n || '').trim(); if (!n) return;
      sel.appendChild(new Option(n, n));
    });
    if (previous) {
      for (var j=0; j<sel.options.length; j++) { if (sel.options[j].value === previous) { sel.value = previous; break; } }
    }
  }).catch(function(){});
}

function _msgAbsenceRefreshGeneralStats(){
  var today = (document.getElementById('msg-abs-date') && document.getElementById('msg-abs-date').value) || '';
  var url = '/api/attendance/general-stats' + (today ? ('?today=' + encodeURIComponent(today)) : '');
  fetch(url, {credentials:'include'}).then(function(r){ return r.json(); }).then(function(d){
    if (!d) return;
    document.getElementById('msg-abs-gs-absent').textContent = d.absent_today != null ? d.absent_today : '-';
    document.getElementById('msg-abs-gs-late').textContent   = d.late_today != null   ? d.late_today   : '-';
    document.getElementById('msg-abs-gs-sent').textContent   = d.sent_ever != null    ? d.sent_ever    : '-';
    document.getElementById('msg-abs-gs-never').textContent  = d.never_sent != null   ? d.never_sent   : '-';
  }).catch(function(){});
}

function msgAbsenceLoad(){
  var chk = document.getElementById('msg-abs-all-dates-chk');
  var allDates = !!(chk && chk.checked);
  var d = allDates ? '__all__' : document.getElementById('msg-abs-date').value;
  var g = document.getElementById('msg-abs-group').value;
  // "Today" shown in the stats strip follows the picker when a specific
  // date is chosen; when "all dates" is on, leave it at whatever was set.
  if (!allDates) _msgAbsenceRefreshGeneralStats();
  if (!d || !g) { _msgAbsenceResetView('\u0627\u062E\u062A\u0631 \u0627\u0644\u062A\u0627\u0631\u064A\u062E \u0648\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 \u0644\u0639\u0631\u0636 \u0627\u0644\u0637\u0644\u0628\u0629'); return; }
  _msgAbsenceResetView('\u062C\u0627\u0631\u064A \u0627\u0644\u062A\u062D\u0645\u064A\u0644...');
  fetch('/api/attendance/by-date-group?date=' + encodeURIComponent(d) + '&group=' + encodeURIComponent(g), { credentials:'include' })
    .then(function(r){ return r.json(); })
    .then(function(data){
      var rows = (data && data.rows) || [];
      _msgAbsenceRows = rows.filter(function(r){ var s = (r.status||'').trim(); return s === '\u063A\u0627\u0626\u0628' || s === '\u0645\u062A\u0623\u062E\u0631'; });
      if (!_msgAbsenceRows.length) { _msgAbsenceResetView('\u0644\u0627 \u062A\u0648\u062C\u062F \u0633\u062C\u0644\u0627\u062A \u063A\u064A\u0627\u0628 \u0644\u0647\u0630\u0627 \u0627\u0644\u064A\u0648\u0645'); return; }
      document.getElementById('msg-abs-status').style.display = 'none';
      document.getElementById('msg-abs-filters').style.display = 'flex';
      _msgAbsenceRender();
    })
    .catch(function(){ _msgAbsenceResetView('\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u062A\u062D\u0645\u064A\u0644'); });
}

function _msgAbsenceIsSent(r){ return (r.message_status || '').trim() === '\u062A\u0645 \u0627\u0644\u0625\u0631\u0633\u0627\u0644'; }
function _msgAbsenceStatusKind(r){ return ((r.status || '').trim() === '\u0645\u062A\u0623\u062E\u0631') ? 'late' : 'absent'; }

function _msgAbsenceSortRows(rows){
  return rows.slice().sort(function(a,b){
    var sa = _msgAbsenceIsSent(a) ? 1 : 0;
    var sb = _msgAbsenceIsSent(b) ? 1 : 0;
    if (sa !== sb) return sa - sb;
    var ka = _msgAbsenceStatusKind(a); var kb = _msgAbsenceStatusKind(b);
    if (ka !== kb) return ka === 'absent' ? -1 : 1;
    return (a.student_name || '').localeCompare(b.student_name || '');
  });
}

function _msgAbsenceRender(){
  var sorted = _msgAbsenceSortRows(_msgAbsenceRows);
  var unsentList = document.getElementById('msg-abs-unsent-list');
  var sentList = document.getElementById('msg-abs-sent-list');
  unsentList.innerHTML = ''; sentList.innerHTML = '';
  var nUnsentAbs = 0, nUnsentLate = 0, nSent = 0;
  sorted.forEach(function(r){
    var card = _msgAbsenceBuildCard(r);
    if (_msgAbsenceIsSent(r)) { sentList.appendChild(card); nSent++; }
    else { unsentList.appendChild(card); if (_msgAbsenceStatusKind(r) === 'late') nUnsentLate++; else nUnsentAbs++; }
  });
  _msgAbsenceUpdateSummary(nUnsentAbs, nUnsentLate, nSent);
  _msgAbsenceApplyFilter();
}

function _msgAbsenceBuildCard(r){
  var card = document.createElement('div');
  card.className = 'msg-abs-card';
  card.dataset.attId = String(r.id);
  card.dataset.sent = _msgAbsenceIsSent(r) ? '1' : '0';
  card.dataset.kind = _msgAbsenceStatusKind(r);
  if (card.dataset.kind === 'late') card.classList.add('status-late');
  if (card.dataset.sent === '1') card.classList.add('is-sent');
  var left = document.createElement('div'); left.className = 'msg-abs-card-left';
  var nameEl = document.createElement('div'); nameEl.className = 'msg-abs-card-name';
  // With the "all groups" option, surface the group name next to each student.
  var nameLabel = r.student_name || '-';
  if (document.getElementById('msg-abs-group').value === '__all__' && r.group_name) {
    nameLabel += ' · ' + r.group_name;
  }
  nameEl.textContent = nameLabel;
  left.appendChild(nameEl);
  var meta = document.createElement('div'); meta.className = 'msg-abs-card-meta';
  // In "all dates" mode the roster spans multiple days, so surface the
  // attendance_date on every card so rows from different days don't blur.
  var allDatesOn = !!(document.getElementById('msg-abs-all-dates-chk') && document.getElementById('msg-abs-all-dates-chk').checked);
  if (allDatesOn && r.attendance_date) {
    var dp = document.createElement('span'); dp.className = 'msg-abs-card-date';
    dp.textContent = '\U0001F4C5 ' + r.attendance_date;
    meta.appendChild(dp);
  }
  var badge = document.createElement('span');
  badge.className = 'msg-abs-badge msg-abs-badge-' + card.dataset.kind;
  badge.textContent = card.dataset.kind === 'late' ? '\u0645\u062A\u0623\u062E\u0631' : '\u063A\u0627\u0626\u0628';
  meta.appendChild(badge);
  var last = document.createElement('span'); last.className = 'msg-abs-last';
  var ls = r.last_sent || '';
  last.textContent = ls ? ('\u0622\u062E\u0631 \u0625\u0631\u0633\u0627\u0644: ' + _msgAbsenceFormatDate(ls)) : '\u0644\u0645 \u064A\u064F\u0631\u0633\u0644 \u0628\u0639\u062F';
  meta.appendChild(last);
  left.appendChild(meta);
  card.appendChild(left);
  var right = document.createElement('div'); right.className = 'msg-abs-card-right';
  var sentBadge = document.createElement('span'); sentBadge.className = 'msg-abs-sent-badge';
  sentBadge.textContent = card.dataset.sent === '1' ? '\u2713 \u062A\u0645 \u0627\u0644\u0625\u0631\u0633\u0627\u0644' : '';
  right.appendChild(sentBadge);
  var phone = _msgCleanPhone(r.whatsapp);
  if (phone) {
    var btn = document.createElement('button'); btn.type='button'; btn.className='msg-wa';
    btn.textContent = '\u0648\u0627\u062A\u0633\u0627\u0628';
    btn.addEventListener('click', (function(rec){ return function(){ _msgAbsenceOpenWa(rec); }; })(r));
    right.appendChild(btn);
  } else {
    var sp = document.createElement('span'); sp.className='msg-wa msg-wa-disabled'; sp.textContent = '\u0644\u0627 \u064A\u0648\u062C\u062F \u0631\u0642\u0645';
    right.appendChild(sp);
  }
  card.appendChild(right);
  return card;
}

function _msgAbsenceFormatDate(raw){
  if (!raw) return '';
  var s = String(raw).replace('T',' ');
  var m = s.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})/);
  return m ? (m[1] + ' ' + m[2]) : s;
}

function _msgAbsenceUpdateSummary(nUnsentAbs, nUnsentLate, nSent){
  var nUnsent = nUnsentAbs + nUnsentLate;
  document.getElementById('msg-abs-unsent-count').textContent = nUnsent;
  document.getElementById('msg-abs-sent-count').textContent = nSent;
  document.getElementById('msg-abs-fc-unsent').textContent = nUnsent;
  document.getElementById('msg-abs-fc-sent').textContent = nSent;
  document.getElementById('msg-abs-fc-all').textContent = nUnsent + nSent;
  var alert = document.getElementById('msg-abs-alert');
  alert.style.display = 'flex';
  alert.className = 'msg-abs-alert';
  if (nUnsent === 0) {
    alert.classList.add('alert-ok');
    alert.innerHTML = '&#x2705; <span>' + '\u0643\u0644 \u0627\u0644\u0631\u0633\u0627\u0626\u0644 \u062A\u0645 \u0625\u0631\u0633\u0627\u0644\u0647\u0627 \u0644\u0647\u0630\u0627 \u0627\u0644\u064A\u0648\u0645' + '</span>';
  } else {
    alert.classList.add('alert-warn');
    alert.innerHTML = '&#x1F534; <span><b>' + nUnsentAbs + '</b>' + ' \u063A\u0627\u0626\u0628\u064A\u0646 \u0648 ' + '<b>' + nUnsentLate + '</b>' + ' \u0645\u062A\u0623\u062E\u0631\u064A\u0646 \u0628\u062F\u0648\u0646 \u0631\u0633\u0627\u0644\u0629 \u0627\u0644\u064A\u0648\u0645' + '</span>';
  }
}

function _msgAbsenceSetFilterButton(filter){
  document.querySelectorAll('.msg-abs-filter').forEach(function(b){
    b.classList.toggle('active', b.dataset.filter === filter);
  });
}
function msgAbsenceSetFilter(filter){
  _msgAbsenceFilter = filter;
  _msgAbsenceSetFilterButton(filter);
  _msgAbsenceApplyFilter();
}

function _msgAbsenceApplyFilter(){
  var unsent = document.getElementById('msg-abs-section-unsent');
  var sent = document.getElementById('msg-abs-section-sent');
  var f = _msgAbsenceFilter;
  var showUnsent = (f === 'unsent' || f === 'all');
  var showSent   = (f === 'sent'   || f === 'all');
  var uHas = !!document.querySelector('#msg-abs-unsent-list .msg-abs-card');
  var sHas = !!document.querySelector('#msg-abs-sent-list .msg-abs-card');
  unsent.style.display = (showUnsent && uHas) ? 'block' : 'none';
  sent.style.display   = (showSent   && sHas) ? 'block' : 'none';
  document.getElementById('msg-abs-bulk-btn').style.display = (f !== 'sent' && uHas) ? 'inline-flex' : 'none';
  var status = document.getElementById('msg-abs-status');
  if (!uHas && !sHas) { status.style.display = 'block'; status.textContent = '\u0644\u0627 \u064A\u0648\u062C\u062F \u0637\u0644\u0628\u0629'; return; }
  if (f === 'unsent' && !uHas) { status.style.display = 'block'; status.textContent = '\u0643\u0644 \u0627\u0644\u0631\u0633\u0627\u0626\u0644 \u062A\u0645 \u0625\u0631\u0633\u0627\u0644\u0647\u0627'; return; }
  if (f === 'sent'   && !sHas) { status.style.display = 'block'; status.textContent = '\u0644\u0645 \u064A\u062A\u0645 \u0625\u0631\u0633\u0627\u0644 \u0623\u064A \u0631\u0633\u0627\u0644\u0629 \u0628\u0639\u062F'; return; }
  status.style.display = 'none';
}

function _msgAbsenceDayName(dateStr){
  if (!dateStr) return '';
  var m = String(dateStr).match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!m) return '';
  // Use explicit year/month/day and UTC to avoid timezone drift around midnight.
  var d = new Date(Date.UTC(parseInt(m[1],10), parseInt(m[2],10)-1, parseInt(m[3],10)));
  if (isNaN(d)) return '';
  return _MSG_ABS_DAYS[d.getUTCDay()];
}

function _msgAbsenceMessage(row){
  var kind = _msgAbsenceStatusKind(row);
  var name = row.student_name || '';
  var date = row.attendance_date || '';
  var day = _msgAbsenceDayName(date);
  var dayPhrase = day ? ('\u064A\u0648\u0645 ' + day + ' \u0627\u0644\u0645\u0648\u0627\u0641\u0642 ' + date) : date;
  if (kind === 'late') return '\u0646\u0641\u064A\u062F\u0643\u0645 \u0628\u0623\u0646 \u0627\u0644\u0637\u0627\u0644\u0628/\u0629 ' + name + ' \u062A\u0623\u062E\u0631/\u062A \u0639\u0646 \u0627\u0644\u062D\u0636\u0648\u0631 ' + dayPhrase;
  return '\u0646\u0641\u064A\u062F\u0643\u0645 \u0628\u0623\u0646 \u0627\u0644\u0637\u0627\u0644\u0628/\u0629 ' + name + ' \u0643\u0627\u0646/\u062A \u063A\u0627\u0626\u0628\u0627\u064B/\u0629 ' + dayPhrase;
}

function _msgAbsenceTemplateName(row){
  return _msgAbsenceStatusKind(row) === 'late' ? '\u062A\u0623\u062E\u064A\u0631' : '\u063A\u064A\u0627\u0628';
}

function _msgAbsenceLogSend(row, phone, cb){
  var body = { student_name: row.student_name || '', student_whatsapp: phone || (row.whatsapp || ''), template_name: _msgAbsenceTemplateName(row) };
  fetch('/api/message-log', { method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify(body) })
    .then(function(r){ return r.json(); })
    .then(function(d){ if (typeof cb === 'function') cb((d && d.id) || null); })
    .catch(function(){ if (typeof cb === 'function') cb(null); });
}

function _msgAbsenceMarkSent(row){
  if (!row || !row.id) return;
  fetch('/api/attendance/' + row.id + '/mark-sent', { method:'POST', credentials:'include' }).catch(function(){});
}

function _msgAbsenceUnmarkSent(row){
  if (!row || !row.id) return;
  fetch('/api/attendance/' + row.id + '/unmark-sent', { method:'POST', credentials:'include' }).catch(function(){});
}

function _msgAbsenceNowString(){
  var d = new Date();
  function p(n){ return String(n).padStart(2,'0'); }
  return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+' '+p(d.getHours())+':'+p(d.getMinutes())+':'+p(d.getSeconds());
}

function _msgAbsenceRecomputeCounts(){
  var nUnsentAbs = 0, nUnsentLate = 0, nSent = 0;
  _msgAbsenceRows.forEach(function(r){
    if (_msgAbsenceIsSent(r)) nSent++;
    else if (_msgAbsenceStatusKind(r) === 'late') nUnsentLate++;
    else nUnsentAbs++;
  });
  _msgAbsenceUpdateSummary(nUnsentAbs, nUnsentLate, nSent);
  _msgAbsenceApplyFilter();
}

function _msgAbsenceTransition(row, toSent){
  var card = document.querySelector('.msg-abs-card[data-att-id="' + row.id + '"]');
  if (!card) return;
  if ((toSent && card.dataset.sent === '1') || (!toSent && card.dataset.sent === '0')) return;
  card.classList.add('leaving');
  setTimeout(function(){
    var fresh = _msgAbsenceBuildCard(row);
    fresh.classList.add('arriving');
    var target = document.getElementById(toSent ? 'msg-abs-sent-list' : 'msg-abs-unsent-list');
    target.appendChild(fresh);
    card.parentNode && card.parentNode.removeChild(card);
    _msgAbsenceRecomputeCounts();
    requestAnimationFrame(function(){ fresh.classList.remove('arriving'); });
  }, 320);
}

function _msgAbsenceShowConfirm(row, onYes){
  var box = document.getElementById('msg-abs-confirm');
  document.getElementById('msg-abs-confirm-name').textContent = row.student_name || '';
  box.classList.add('show');
  var yes = document.getElementById('msg-abs-confirm-yes');
  var no = document.getElementById('msg-abs-confirm-no');
  function cleanup(){ box.classList.remove('show'); yes.onclick = null; no.onclick = null; }
  yes.onclick = function(){ cleanup(); onYes(); };
  no.onclick = function(){ cleanup(); };
}

function _msgAbsenceHideUndo(){
  if (_msgAbsUndoTimeout) { clearTimeout(_msgAbsUndoTimeout); _msgAbsUndoTimeout = null; }
  if (_msgAbsUndoTick)    { clearInterval(_msgAbsUndoTick); _msgAbsUndoTick = null; }
  var bar = document.getElementById('msg-abs-undo');
  bar.classList.remove('show');
  _msgAbsUndoActive = false;
  setTimeout(function(){ if (!bar.classList.contains('show')) bar.style.display = 'none'; }, 280);
  bar.onclick = null;
}

function _msgAbsenceShowUndo(label, onUndo){
  _msgAbsenceHideUndo();
  var bar = document.getElementById('msg-abs-undo');
  var text = document.getElementById('msg-abs-undo-text');
  var count = document.getElementById('msg-abs-undo-count');
  var secs = 30;
  text.textContent = '\u21A9 \u062A\u0631\u0627\u062C\u0639 \u2014 ' + label;
  count.textContent = '(' + secs + ')';
  bar.style.display = 'flex';
  _msgAbsUndoActive = true;
  requestAnimationFrame(function(){ bar.classList.add('show'); });
  bar.onclick = function(){
    if (!_msgAbsUndoActive) return;
    _msgAbsenceHideUndo();
    if (typeof onUndo === 'function') onUndo();
  };
  _msgAbsUndoTick = setInterval(function(){
    secs--;
    if (secs <= 0) { _msgAbsenceHideUndo(); return; }
    count.textContent = '(' + secs + ')';
  }, 1000);
  _msgAbsUndoTimeout = setTimeout(function(){ _msgAbsenceHideUndo(); }, secs * 1000);
}

function _msgAbsenceUndoRow(row){
  // Remove the log entry this toast owns (if any), unmark attendance,
  // clear local last-sent if we were the one that set it, and bounce
  // the card back to the unsent list.
  if (row._last_log_id) {
    fetch('/api/message-log/' + row._last_log_id, { method:'DELETE', credentials:'include' }).catch(function(){});
    row._last_log_id = null;
  }
  _msgAbsenceUnmarkSent(row);
  row.message_status = '';
  if (row._last_sent_was_self) { row.last_sent = row._prior_last_sent || null; row._last_sent_was_self = false; }
  _msgAbsenceTransition(row, false);
  _msgAbsenceRefreshGeneralStats();
}

function _msgAbsenceSendAndMark(row){
  var phone = _msgCleanPhone(row.whatsapp); if (!phone) return;
  _msgAbsenceLogSend(row, phone, function(logId){ row._last_log_id = logId; });
  _msgAbsenceMarkSent(row);
  row._prior_last_sent = row.last_sent;
  row._last_sent_was_self = true;
  row.message_status = '\u062A\u0645 \u0627\u0644\u0625\u0631\u0633\u0627\u0644';
  row.last_sent = _msgAbsenceNowString();
  _msgAbsenceTransition(row, true);
  _msgAbsenceRefreshGeneralStats();
}

function _msgAbsenceOpenWa(row){
  var phone = _msgCleanPhone(row.whatsapp); if (!phone) return;
  var text = _msgAbsenceMessage(row);
  // 1) Fire the wa.me open inside the user gesture so the popup isn't blocked.
  window.open('https://wa.me/' + phone + '?text=' + encodeURIComponent(text), '_blank');
  // 2) Ask whether the user actually sent it. Marking + logging only happen on yes.
  _msgAbsenceShowConfirm(row, function(){
    _msgAbsenceSendAndMark(row);
    _msgAbsenceShowUndo((row.student_name || ''), function(){ _msgAbsenceUndoRow(row); });
  });
}

function _msgAbsenceVisibleTargets(){
  var f = _msgAbsenceFilter;
  return _msgAbsenceRows.filter(function(r){
    if (_msgAbsenceIsSent(r)) return false;
    if (!_msgCleanPhone(r.whatsapp)) return false;
    if (f === 'sent') return false;
    return true;
  });
}

function msgAbsenceBulk(){
  var targets = _msgAbsenceVisibleTargets();
  if (!targets.length) { alert('\u0644\u0627 \u064A\u0648\u062C\u062F \u0637\u0644\u0628\u0629 \u0645\u0637\u0627\u0628\u0642\u0648\u0646 \u0644\u0644\u0641\u0644\u062A\u0631 \u0627\u0644\u062D\u0627\u0644\u064A'); return; }
  if (targets.length > 1 && !confirm('\u0633\u064A\u062A\u0645 \u0641\u062A\u062D \u0639\u062F\u0629 \u0646\u0648\u0627\u0641\u0630 \u0648\u0627\u062A\u0633\u0627\u0628 \u2014 \u0647\u0644 \u062A\u0631\u064A\u062F \u0627\u0644\u0645\u062A\u0627\u0628\u0639\u0629\u061F')) return;
  // Open all wa.me URLs first (stagger so popup blockers don't nuke them),
  // then auto-mark+log without per-row confirmation. The undo toast acts as
  // the single recovery surface.
  targets.forEach(function(row, idx){
    setTimeout(function(){
      var phone = _msgCleanPhone(row.whatsapp);
      var text = _msgAbsenceMessage(row);
      window.open('https://wa.me/' + phone + '?text=' + encodeURIComponent(text), '_blank');
      _msgAbsenceSendAndMark(row);
    }, idx * 400);
  });
  // Show one grouped undo toast once the last send has fired.
  setTimeout(function(){
    _msgAbsenceShowUndo(targets.length + ' \u0637\u0644\u0627\u0628', function(){
      targets.forEach(function(row){ _msgAbsenceUndoRow(row); });
    });
  }, targets.length * 400 + 100);
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', msgStartScheduler);
else msgStartScheduler();
</script>

<div id="pay-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:9999;overflow:auto;"><div style="background:#fff;margin:20px auto;border-radius:14px;max-width:99%;padding:0;overflow:hidden;box-shadow:0 8px 32px rgba(107,63,160,0.25);"><div style="background:linear-gradient(135deg,#6B3FA0,#8B5CC8);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#fff;font-size:1.2rem;font-weight:bold;">&#x1F4B3; &#x645;&#x62A;&#x627;&#x628;&#x639;&#x629; &#x627;&#x644;&#x62F;&#x641;&#x639;</span><span onclick="document.getElementById('pay-modal').style.display='none'" style="color:#fff;font-size:1.8rem;cursor:pointer;line-height:1;">&times;</span></div><div style="padding:14px 16px;background:#f8f4ff;border-bottom:1px solid #e0d0f8;"><div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;"><div><label style="display:block;font-weight:bold;color:#4a148c;margin-bottom:4px;">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label><select id="pm-group" onchange="pmLoadGroup()" style="padding:7px 12px;border-radius:8px;border:1.5px solid #8B5CC8;min-width:160px;font-size:0.95rem;"><option value="">&mdash; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &mdash;</option></select></div><div><label style="display:block;font-weight:bold;color:#4a148c;margin-bottom:4px;">&#x627;&#x644;&#x62A;&#x627;&#x631;&#x64A;&#x62E;</label><div style="display:flex;gap:8px;align-items:center;"><input type="date" id="pm-date" onchange="pmSetDay()" style="padding:7px 12px;border-radius:8px;border:1.5px solid #8B5CC8;font-size:0.95rem;"><label style="display:inline-flex;align-items:center;gap:6px;font-weight:700;color:#4a148c;background:#ede7f6;padding:7px 12px;border-radius:8px;border:1.5px solid #8B5CC8;cursor:pointer;white-space:nowrap;user-select:none;"><input type="checkbox" id="pm-all-dates" onchange="pmToggleAllDates()" style="accent-color:#6B3FA0;cursor:pointer;">&#x1F5D3;&#xFE0F; &#x62C;&#x645;&#x64A;&#x639; &#x627;&#x644;&#x62A;&#x648;&#x627;&#x631;&#x64A;&#x62E;</label></div></div><div><label style="display:block;font-weight:bold;color:#4a148c;margin-bottom:4px;">&#x627;&#x644;&#x64A;&#x648;&#x645;</label><input type="text" id="pm-day" readonly style="padding:7px 12px;border-radius:8px;border:1.5px solid #ccc;background:#f0f0f0;min-width:90px;font-size:0.95rem;"></div><div><label style="display:block;font-weight:bold;color:#4a148c;margin-bottom:4px;">&#x628;&#x62D;&#x62B;</label><input type="text" id="pm-search" oninput="pmFilter()" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x644;&#x627;&#x633;&#x645;..." style="padding:7px 12px;border-radius:8px;border:1.5px solid #8B5CC8;min-width:170px;font-size:0.95rem;"></div></div></div><div style="overflow-x:auto;"><table id="pm-tbl" style="border-collapse:collapse;width:100%;min-width:400px;font-size:0.76rem;"><thead><tr style="background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;text-align:center;"><th rowspan="2" style="padding:8px 14px;border:1px solid #9b6fd4;position:sticky;right:0;background:linear-gradient(135deg,#6B3FA0,#8B5CC8);z-index:2;min-width:140px;">&#x627;&#x644;&#x627;&#x633;&#x645;</th><th colspan="4" style="padding:7px 4px;border:1px solid #9b6fd4;">&#x642;&#x633;&#x637; 1</th></tr><tr style="background:#ede7f6;color:#4a148c;text-align:center;"><th style="padding:5px 3px;border:1px solid #c5b3e6;white-space:nowrap;">&#x646;&#x648;&#x639; &#x627;&#x644;&#x623;&#x642;&#x633;&#x627;&#x637;</th><th style="padding:5px 3px;border:1px solid #c5b3e6;white-space:nowrap;">&#x627;&#x644;&#x633;&#x639;&#x631;</th><th style="padding:5px 3px;border:1px solid #c5b3e6;white-space:nowrap;">&#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639;</th><th style="padding:5px 3px;border:1px solid #c5b3e6;white-space:nowrap;">&#x627;&#x644;&#x645;&#x62A;&#x628;&#x642;&#x64A;</th></tr></thead><tbody id="pm-tbody"></tbody></table></div></div></div>
<script>
var _pmStudents=[];var _pmTaqseet=[];
function _norm(s){return(s||"").replace(/[\u0623\u0625\u0622\u0671]/g,"\u0627").replace(/\u0629/g,"\u0647").replace(/\u0649/g,"\u064A");}
function pmOpen(){
  document.getElementById("pay-modal").style.display="block";
  if(!window._pmGL){window._pmGL=true;
    fetch("/api/students").then(r=>r.json()).then(function(data){
      var seen={};var sel=document.getElementById("pm-group");
      (data.students||data).forEach(function(st){
        var g=st.group_name_student||"";
        if(g&&!seen[g]){seen[g]=1;var o=document.createElement("option");o.value=g;o.textContent=g;sel.appendChild(o);}
      });
      _pmStudents=data.students||data;
      fetch("/api/taqseet").then(function(r){return r.json();}).then(function(tq){_pmTaqseet=tq;});
    });
  }
}
function pmTypeChange(sel){
  var inst=sel.dataset.inst;
  var val=sel.value;
  if(!val)return;
  var sid=sel.dataset.sid;
  var studentMethod=null;
  for(var m=0;m<_pmStudents.length;m++){if(String(_pmStudents[m].id)===String(sid)){studentMethod=String(_pmStudents[m].installment_type||"");break;}}
  if(!studentMethod)return;
  var tq=null;
  for(var k=0;k<_pmTaqseet.length;k++){if(String(_pmTaqseet[k].taqseet_method)===studentMethod){tq=_pmTaqseet[k];break;}}
  if(!tq)return;
  var price=tq["inst"+val]||"";
  var row=sel.closest("tr");
  if(!row)return;
  var priceInp=null;var _ps=row.querySelectorAll(".pm-price");for(var _pi=0;_pi<_ps.length;_pi++){if(String(_ps[_pi].dataset.inst)===String(inst)){priceInp=_ps[_pi];break;}}
  if(priceInp&&(priceInp.value===null||priceInp.value===""||priceInp.value==="0")){priceInp.value=price;pmCalc(priceInp);}
}
function pmSetDay(){
  var cb=document.getElementById("pm-all-dates");
  if (cb && cb.checked) { document.getElementById("pm-day").value=""; return; }
  var d=document.getElementById("pm-date").value;if(!d)return;
  var days=["\u0627\u0644\u0623\u062d\u062f","\u0627\u0644\u0627\u062b\u0646\u064a\u0646","\u0627\u0644\u062b\u0644\u0627\u062b\u0627\u0621","\u0627\u0644\u0623\u0631\u0628\u0639\u0627\u0621","\u0627\u0644\u062e\u0645\u064a\u0633","\u0627\u0644\u062c\u0645\u0639\u0629","\u0627\u0644\u0633\u0628\u062a"];
  document.getElementById("pm-day").value=days[new Date(d).getDay()];
}
/* Toggle "جميع التواريخ" — disables the date/day inputs and signals the
   save path to write pay_date="__all__". The loader never filters by date
   server-side, so the table already reflects every record regardless of
   the selected date; this toggle is purely UX parity with other pages. */
function pmToggleAllDates(){
  var cb=document.getElementById("pm-all-dates");
  var dateInp=document.getElementById("pm-date");
  var dayInp=document.getElementById("pm-day");
  var on=!!(cb && cb.checked);
  if (dateInp){ dateInp.disabled=on; dateInp.style.background=on?"#eceff1":""; if(on) dateInp.value=""; }
  if (dayInp){  dayInp.disabled =on; dayInp.style.background =on?"#eceff1":"#f0f0f0"; if(on) dayInp.value=""; }
}
function pmLoadGroup(){
  var g=document.getElementById("pm-group").value;if(!g)return;
  fetch("/api/payments/group?group="+encodeURIComponent(g)).then(r=>r.json()).then(function(rows){
    var tb=document.getElementById("pm-tbody");tb.innerHTML="";
    rows.forEach(function(row){
      var tr=document.createElement("tr");tr.dataset.name=row.name||"";tr.dataset.sid=row.id;
      var td0=document.createElement("td");
      td0.style.cssText="padding:6px 10px;border:1px solid #ddd;font-weight:bold;background:#f9f5ff;position:sticky;right:0;z-index:1;white-space:nowrap;";
      td0.textContent=row.name||"";tr.appendChild(td0);
      for(var i=1;i<=1;i++){
        var pd=row["inst_"+i]||{};
        var tdT=document.createElement("td");tdT.style.cssText="padding:3px;border:1px solid #ddd;text-align:center;";
        var sel=document.createElement("select");sel.dataset.sid=row.id;sel.dataset.inst=i;sel.className="pm-type";sel.onchange=function(){pmTypeChange(this);};
        sel.style.cssText="padding:3px;border-radius:5px;border:1px solid #8B5CC8;width:58px;";
        var o0=document.createElement("option");o0.value="";o0.textContent="-";sel.appendChild(o0);
        for(var n=1;n<=12;n++){var op=document.createElement("option");op.value=n;op.textContent="\u0642\u0633\u0637 "+n;if(String(pd.inst_type)==String(n))op.selected=true;sel.appendChild(op);}
        tdT.appendChild(sel);tr.appendChild(tdT);
        var tdP=document.createElement("td");tdP.style.cssText="padding:3px;border:1px solid #ddd;text-align:center;";
        var iP=document.createElement("input");iP.type="number";iP.dataset.sid=row.id;iP.dataset.inst=i;iP.className="pm-price";
        iP.style.cssText="width:70px;padding:3px;border-radius:5px;border:1px solid #ccc;";iP.value=pd.price!=null&&pd.price!==0?pd.price:(row["tq_inst"+i]||"");iP.placeholder="\u0627\u0644\u0633\u0639\u0631";
        iP.oninput=function(){pmCalc(this);};tdP.appendChild(iP);tr.appendChild(tdP);
        var tdPd=document.createElement("td");tdPd.style.cssText="padding:3px;border:1px solid #ddd;text-align:center;";
        var iPd=document.createElement("input");iPd.type="number";iPd.dataset.sid=row.id;iPd.dataset.inst=i;iPd.className="pm-paid";
        iPd.style.cssText="width:70px;padding:3px;border-radius:5px;border:1px solid #ccc;";iPd.value=pd.paid!=null&&pd.paid!==0?pd.paid:"";iPd.placeholder="\u0627\u0644\u0645\u062f\u0641\u0648\u0639";
        iPd.oninput=function(){pmCalc(this);};tdPd.appendChild(iPd);tr.appendChild(tdPd);
        var tdR=document.createElement("td");tdR.style.cssText="padding:3px;border:1px solid #ddd;text-align:center;background:#f0fff0;";
        var sp=document.createElement("span");sp.className="pm-rem-"+i;
        var pr=parseFloat(pd.price)||0;var pa=parseFloat(pd.paid)||0;
        sp.textContent=pr?(pr-pa).toFixed(2):"";tdR.appendChild(sp);
        var sv=document.createElement("button");sv.textContent="\u062d\u0641\u0638";sv.dataset.sid=row.id;sv.dataset.inst=i;
        sv.style.cssText="display:block;width:100%;margin-top:2px;padding:2px 4px;background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border:none;border-radius:5px;cursor:pointer;font-size:0.7rem;";
        sv.onclick=function(){pmSave(this);};tdR.appendChild(sv);tr.appendChild(tdR);
      }
      tb.appendChild(tr);
    });
  });
}
function pmCalc(inp){
  var tr=inp.closest("tr");var inst=inp.dataset.inst;
  var pr=parseFloat((tr.querySelector(".pm-price[data-inst='"+inst+"']")||{}).value)||0;
  var pa=parseFloat((tr.querySelector(".pm-paid[data-inst='"+inst+"']")||{}).value)||0;
  var sp=tr.querySelector(".pm-rem-"+inst);if(sp)sp.textContent=pr?(pr-pa).toFixed(2):"";
}
function pmSave(btn){
  var sid=btn.dataset.sid;var inst=btn.dataset.inst;var tr=btn.closest("tr");
  var _pmAll=!!(document.getElementById("pm-all-dates")||{}).checked;
  var body={inst_type:((tr.querySelector(".pm-type[data-inst='"+inst+"']")||{}).value||""),
    price:parseFloat(((tr.querySelector(".pm-price[data-inst='"+inst+"']")||{}).value))||0,
    paid:parseFloat(((tr.querySelector(".pm-paid[data-inst='"+inst+"']")||{}).value))||0,
    pay_date:(_pmAll?"__all__":((document.getElementById("pm-date")||{}).value||"")),
    day_name:(_pmAll?"":((document.getElementById("pm-day")||{}).value||""))};
  fetch("/api/payments/"+sid+"/"+inst,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}).then(r=>r.json()).then(function(d){btn.textContent=d.ok?"\u2713":"\u274c";setTimeout(function(){btn.textContent="\u062d\u0641\u0638";},1800);});
}
function pmFilter(){
  var q=_norm(document.getElementById("pm-search").value.toLowerCase());
  document.querySelectorAll("#pm-tbody tr").forEach(function(tr){var n=_norm((tr.dataset.name||"").toLowerCase());tr.style.display=n.includes(q)?"":"none";});
}
</script>
<div id="srm-type-modal" class="srm-type-bg"><div class="srm-type-box"><h3 id="srm-type-title">&#x62A;&#x623;&#x643;&#x64A;&#x62F; &#x627;&#x644;&#x62D;&#x630;&#x641;</h3><p id="srm-type-msg"></p><span class="srm-type-expected" id="srm-type-expected"></span><input class="srm-type-input" id="srm-type-input" type="text" placeholder="&#x627;&#x643;&#x62A;&#x628; &#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x643;&#x645;&#x627; &#x647;&#x648;"><div class="srm-type-actions"><button class="srm-btn-delete" id="srm-type-yes">&#x62A;&#x623;&#x643;&#x64A;&#x62F; &#x627;&#x644;&#x62D;&#x630;&#x641;</button><button class="srm-btn-cancel-edit" id="srm-type-no">&#x625;&#x644;&#x63A;&#x627;&#x621;</button></div></div></div><div id="srm-log-modal" class="srm-log-bg"><div class="srm-log-box"><div class="srm-log-head">&#x1F4CB; &#x645;&#x631;&#x627;&#x62C;&#x639;&#x629; &#x627;&#x644;&#x62A;&#x63A;&#x64A;&#x64A;&#x631;&#x627;&#x62A; &#x642;&#x628;&#x644; &#x627;&#x644;&#x62D;&#x641;&#x638;</div><div class="srm-log-body" id="srm-log-body"></div><div class="srm-log-actions"><button class="srm-btn-save" id="srm-log-yes">&#x646;&#x639;&#x645;&#x60C; &#x627;&#x62D;&#x641;&#x638;</button><button class="srm-btn-cancel-edit" id="srm-log-no">&#x631;&#x627;&#x62C;&#x639; &#x645;&#x631;&#x629; &#x623;&#x62E;&#x631;&#x649;</button></div></div></div><div id="srm-auto-lock" class="srm-auto-lock-banner">&#x1F6AB; &#x62A;&#x645; &#x625;&#x644;&#x63A;&#x627;&#x621; &#x627;&#x644;&#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x62A;&#x644;&#x642;&#x627;&#x626;&#x64A;&#x627;&#x64B; &#x628;&#x633;&#x628;&#x628; &#x639;&#x62F;&#x645; &#x627;&#x644;&#x646;&#x634;&#x627;&#x637;</div>
</body>
</html>"""
ATTENDANCE_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>&#x62A;&#x633;&#x62C;&#x64A;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628; - Mindex</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Tahoma,Arial,sans-serif;}
body{background:#f5f3ff;min-height:100vh;direction:rtl;}
.topbar{background:linear-gradient(135deg,#00897B,#26A69A);color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;}
.topbar h1{font-size:20px;font-weight:800;}
.btn-back{background:rgba(255,255,255,.18);color:#fff;border:1.5px solid rgba(255,255,255,.5);padding:8px 18px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;}
.btn-back:hover{background:rgba(255,255,255,.3);}
.main{padding:24px 28px;}
.card{background:#fff;border-radius:14px;padding:22px 24px;box-shadow:0 2px 14px rgba(0,137,123,.1);margin-bottom:24px;}
.controls-row{display:flex;align-items:flex-end;gap:16px;flex-wrap:wrap;}
.ctrl-group{display:flex;flex-direction:column;gap:5px;}
.ctrl-label{font-size:12px;font-weight:700;color:#00897B;}
select.group-select{padding:10px 16px;border:1.5px solid #80CBC4;border-radius:10px;font-size:15px;font-weight:600;color:#333;background:#f0fdfc;outline:none;min-width:200px;cursor:pointer;}
select.group-select:focus{border-color:#00897B;background:#fff;}
input.date-input{padding:10px 14px;border:1.5px solid #80CBC4;border-radius:10px;font-size:15px;font-weight:600;color:#333;background:#f0fdfc;outline:none;cursor:pointer;min-width:160px;direction:ltr;}
input.date-input:focus{border-color:#00897B;background:#fff;}
.day-badge{display:inline-flex;align-items:center;justify-content:center;padding:10px 18px;background:linear-gradient(135deg,#00897B,#26A69A);color:#fff;border-radius:10px;font-size:15px;font-weight:700;min-width:110px;}
.day-badge.empty{background:#e0f2f1;color:#9e9e9e;font-weight:600;}
.student-count{font-size:13px;color:#fff;background:#00897B;padding:6px 14px;border-radius:20px;font-weight:700;align-self:flex-end;margin-bottom:2px;}
/* Alert banner */
.alert-banner{display:none;padding:14px 20px;border-radius:12px;font-size:14px;font-weight:600;margin-bottom:20px;display:none;align-items:center;gap:10px;}
.alert-banner.exists{background:#fff3e0;border:2px solid #FB8C00;color:#e65100;display:flex;}
.alert-banner.new{background:#e8f5e9;border:2px solid #43A047;color:#2e7d32;display:flex;}
.alert-icon{font-size:20px;}
/* Table */
.att-section{margin-top:0;}
.att-section-header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:14px;}
.att-section-title{font-size:18px;font-weight:800;color:#00897B;display:flex;align-items:center;gap:8px;}
.btn-save-all{background:linear-gradient(135deg,#00897B,#26A69A);color:#fff;border:none;padding:11px 28px;border-radius:11px;font-size:15px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:8px;}
.btn-save-all:hover{opacity:.9;}
.btn-save-all:disabled{background:#b2dfdb;cursor:not-allowed;opacity:.7;}
.att-footer-btns{display:flex;align-items:center;gap:14px;margin-top:22px;padding:0 4px;}
.btn-cancel-att{background:#fff;color:#e53935;border:2px solid #e53935;padding:11px 28px;border-radius:11px;font-size:15px;font-weight:700;cursor:pointer;display:flex;align-items:center;gap:8px;transition:all .2s;}
.btn-cancel-att:hover{background:#fdecea;transform:translateY(-2px);}
.search-wrap{display:flex;align-items:center;gap:10px;margin-bottom:16px;background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,137,123,.1);padding:10px 16px;border:2px solid #e0f2f1;}
.search-wrap:focus-within{border-color:#26A69A;box-shadow:0 2px 16px rgba(0,137,123,.2);}
.search-icon{font-size:18px;color:#80CBC4;flex-shrink:0;}
.search-input{flex:1;border:none;outline:none;font-size:15px;color:#333;background:transparent;direction:rtl;}
.search-input::placeholder{color:#b2dfdb;}
.search-clear{background:none;border:none;cursor:pointer;color:#80CBC4;font-size:18px;padding:0 2px;line-height:1;transition:color .2s;}
.search-clear:hover{color:#e53935;}
.search-result-badge{font-size:12px;color:#fff;background:#26A69A;border-radius:8px;padding:2px 8px;white-space:nowrap;}
.action-cell{text-align:center;white-space:nowrap;}

.sent-cell{text-align:center;padding:4px;}
.sent-check{width:18px;height:18px;cursor:pointer;accent-color:#1a8754;vertical-align:middle;}.btn-wa{display:inline-flex;align-items:center;gap:5px;background:linear-gradient(135deg,#25D366,#128C7E);color:#fff;border:none;padding:6px 12px;border-radius:9px;font-size:13px;font-weight:700;cursor:pointer;text-decoration:none;transition:all .2s;}
.btn-wa:hover{transform:translateY(-1px);box-shadow:0 3px 10px rgba(37,211,102,.4);color:#fff;}
.btn-wa-disabled{opacity:0.38;cursor:not-allowed;pointer-events:none;background:linear-gradient(135deg,#bbb,#999) !important;color:#555 !important;box-shadow:none !important;}
.wa-na{color:#b2dfdb;font-size:16px;}
.wa-missing{color:#ffb3b3;font-size:13px;}
.att-table-wrap{background:#fff;border-radius:14px;box-shadow:0 2px 14px rgba(0,137,123,.1);overflow:hidden;}
.att-table-wrap table{width:100%;border-collapse:collapse;}
.att-table-wrap thead tr{background:linear-gradient(135deg,#00897B,#26A69A);color:#fff;}
.att-table-wrap th{padding:13px 18px;font-size:14px;font-weight:700;text-align:right;}
.att-table-wrap th:first-child{text-align:center;width:52px;}
.att-table-wrap tbody tr{border-bottom:1px solid #e0f2f1;transition:background .15s;}
.att-table-wrap tbody tr:hover{background:#f0fdf9;}
.att-table-wrap td{padding:10px 18px;font-size:14px;color:#333;text-align:right;vertical-align:middle;}
.att-table-wrap td:first-child{text-align:center;color:#aaa;font-size:13px;font-weight:600;}
.student-name-cell{font-weight:600;color:#1a1a2e;font-size:15px;}
.status-select{padding:7px 14px;border:1.5px solid #80CBC4;border-radius:8px;font-size:14px;font-weight:600;background:#f0fdfc;color:#333;outline:none;cursor:pointer;min-width:130px;}
.status-select:focus{border-color:#00897B;background:#fff;}
.status-select.present{border-color:#43A047;background:#e8f5e9;color:#2e7d32;}
.status-select.absent{border-color:#e53935;background:#fce4ec;color:#c62828;}
.status-select.late{border-color:#FB8C00;background:#fff3e0;color:#e65100;}
.empty-state{text-align:center;padding:48px 20px;color:#aaa;font-size:15px;}
.att-stat{text-align:center;font-weight:700;font-variant-numeric:tabular-nums;}
.att-stat-present{color:#2e7d32;}
.att-stat-absent{color:#c62828;}
.att-stat-late{color:#e65100;}
.att-stat-pct{color:#00695C;}
.att-stat-pct-low{color:#c62828;}
.att-stat-pct-mid{color:#e65100;}
.att-stat-bar{height:4px;border-radius:2px;background:#e0f2f1;margin-top:3px;overflow:hidden;}
.att-stat-bar-fill{height:100%;background:linear-gradient(135deg,#00897B,#4DB6AC);}
.toast{position:fixed;bottom:28px;right:28px;background:#00897B;color:#fff;padding:13px 24px;border-radius:12px;font-size:14px;font-weight:600;z-index:9999;display:none;box-shadow:0 4px 20px rgba(0,137,123,.3);}
.toast.show{display:block;}
.spinner{display:none;align-items:center;gap:8px;color:#00897B;font-size:13px;font-weight:600;}
.spinner.show{display:flex;}
.spin-circle{width:16px;height:16px;border:2px solid #b2dfdb;border-top-color:#00897B;border-radius:50%;animation:spin .7s linear infinite;}
@keyframes spin{to{transform:rotate(360deg);}}
</style>
</head>
<body>
<div class="topbar">
  <h1>&#128197; &#x62A;&#x633;&#x62C;&#x64A;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</h1>
  <a href="/settings" style="background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;padding:11px 22px;border-radius:11px;font-size:15px;font-weight:700;text-decoration:none;margin-left:8px;display:inline-block;">&#9881; &#x625;&#x639;&#x62F;&#x627;&#x62F;&#x627;&#x62A;</a><a href="/dashboard" class="btn-back">&larr; &#x627;&#x644;&#x631;&#x626;&#x64A;&#x633;&#x64A;&#x629;</a>
</div>
<div class="main">
  <div id="attInstrCard">
    <div class="att-intro-title">&#x1F4CB; &#x62E;&#x637;&#x648;&#x627;&#x62A; &#x62A;&#x633;&#x62C;&#x64A;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</div>
    <ol>
      <li>1&#8419; &#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</li>
      <li>2&#8419; &#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x62A;&#x627;&#x631;&#x64A;&#x62E;</li>
      <li>3&#8419; &#x633;&#x62C;&#x644; &#x62D;&#x636;&#x648;&#x631; &#x623;&#x648; &#x63A;&#x64A;&#x627;&#x628; &#x643;&#x644; &#x637;&#x627;&#x644;&#x628;</li>
      <li>4&#8419; &#x627;&#x636;&#x63A;&#x637; &#x62D;&#x641;&#x638;</li>
    </ol>
  </div>
  <div class="card">
    <div class="controls-row">
      <div class="ctrl-group">
        <span class="ctrl-label">&#128218; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</span>
        <select class="group-select" id="groupSelect" onchange="onControlChange()">
          <option value="">&#8212; &#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#8212;</option>
        </select>
      </div>
      <div class="ctrl-group">
        <span class="ctrl-label">&#128197; &#x627;&#x644;&#x62A;&#x627;&#x631;&#x64A;&#x62E;</span>
        <input type="date" class="date-input" id="dateInput" onchange="onControlChange()">
      </div>
      <div class="ctrl-group">
        <span class="ctrl-label">&#128340; &#x627;&#x644;&#x64A;&#x648;&#x645;</span>
        <div class="day-badge empty" id="dayBadge">&#8212;</div>
      </div>
      <span class="student-count" id="studentCount" style="display:none;"></span>
      <div class="spinner" id="checkSpinner"><div class="spin-circle"></div><span>&#1580;&#1575;&#1585;&#1610; &#1575;&#1604;&#1578;&#1581;&#1602;&#1602;...</span></div>
    </div>
  </div>

  <div class="alert-banner" id="alertBanner">
    <span class="alert-icon" id="alertIcon"></span>
    <span id="alertText"></span>
  </div>

  <div class="search-wrap" id="searchWrap" style="display:flex;">
    <span class="search-icon">&#128269;</span>
    <input type="text" class="search-input" id="searchInput"
           placeholder="&#1575;&#1576;&#1581;&#1579; &#1576;&#1575;&#1604;&#1575;&#1587;&#1605; &#1571;&#1608; &#1575;&#1604;&#1585;&#1602;&#1605; &#1575;&#1604;&#1588;&#1582;&#1589;&#1610;..."
           oninput="onSearchInput(this.value)"
           autocomplete="off">
    <span class="search-result-badge" id="searchBadge" style="display:none;"></span>
    <button class="search-clear" id="searchClear" onclick="clearSearch()" style="display:none;" title="&#1605;&#1587;&#1581;">&#10006;</button>
  </div>
  <div class="att-section" id="attSection" style="display:none;">
    <div class="att-section-header">
      <div class="att-section-title">
        <span>&#9997;&#65039; &#1603;&#1588;&#1601; &#1575;&#1604;&#1581;&#1590;&#1608;&#1585;</span>
        <span id="attSectionGroupName" style="color:#26A69A;font-size:16px;"></span>
      </div>

    </div>
    <div class="att-table-wrap">
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>&#1575;&#1604;&#1575;&#1587;&#1605;</th>
            <th>&#1575;&#1604;&#1581;&#1575;&#1604;&#1577;</th>
            <th>&#1573;&#1580;&#1585;&#1575;&#1569;</th>
            <th>&#x62A;&#x645; &#x627;&#x644;&#x625;&#x631;&#x633;&#x627;&#x644;</th>
            <th style="text-align:center;">&#x623;&#x64A;&#x627;&#x645; &#x627;&#x644;&#x62D;&#x636;&#x648;&#x631;</th>
            <th style="text-align:center;">&#x623;&#x64A;&#x627;&#x645; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</th>
            <th style="text-align:center;">&#x623;&#x64A;&#x627;&#x645; &#x627;&#x644;&#x62A;&#x623;&#x62E;&#x64A;&#x631;</th>
            <th style="text-align:center;">&#x646;&#x633;&#x628;&#x629; &#x627;&#x644;&#x62D;&#x636;&#x648;&#x631; %</th>
          </tr>
        </thead>
        <tbody id="attTableBody"></tbody>
      </table>
    </div>
    <div class="att-footer-btns" id="attFooterBtns" style="display:none;">
      <button class="btn-save-all" id="btnSaveAll" onclick="saveAllAttendance()">
        <span>&#128190;</span> <span id="btnSaveLabel">&#1581;&#1601;&#1592; &#1575;&#1604;&#1578;&#1587;&#1580;&#1610;&#1604;&#1575;&#1578;</span>
      </button>
      <button class="btn-cancel-att" onclick="window.location.href='/dashboard'">
        <span>&#10006;</span> &#1573;&#1604;&#1594;&#1575;&#1569;
      </button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
var groupsData = {};
var AR_DAYS = ['\u0627\u0644\u0623\u062d\u062f','\u0627\u0644\u0627\u062b\u0646\u064a\u0646','\u0627\u0644\u062b\u0644\u0627\u062b\u0627\u0621','\u0627\u0644\u0623\u0631\u0628\u0639\u0627\u0621','\u0627\u0644\u062e\u0645\u064a\u0633','\u0627\u0644\u062c\u0645\u0639\u0629','\u0627\u0644\u0633\u0628\u062a'];
var currentMode = 'new'; // 'new' or 'exists'
var existingRecords = {}; // keyed by student_name -> record id
var checkTimeout = null;

function showToast(msg, bg) {
  var t = document.getElementById('toast');
  t.textContent = msg;
  t.style.background = bg || '#00897B';
  t.classList.add('show');
  setTimeout(function(){ t.classList.remove('show'); }, 3500);
}

function normalizeAr(s) {
  if (!s) return '';
  return s
    .replace(/[\u0623\u0625\u0622\u0627]/g, '\u0627')  // \u0623\u0625\u0622\u0627 \u2192 \u0627
    .replace(/[\u0629\u0647]/g, '\u0647')               // \u0629\u0647 \u2192 \u0647
    .replace(/[\u0649\u064a]/g, '\u064a')               // \u0649\u064a \u2192 \u064a
    .replace(/[\u064b-\u065f]/g, '');                   // remove tashkeel
}

var _searchTimeout = null;

function onSearchInput(val) {
  var clearBtn = document.getElementById('searchClear');
  var badge = document.getElementById('searchBadge');
  if (val.trim()) {
    clearBtn.style.display = 'inline-block';
  } else {
    clearBtn.style.display = 'none';
    badge.style.display = 'none';
  }
  clearTimeout(_searchTimeout);
  _searchTimeout = setTimeout(function() {
    performSearch(val.trim());
  }, 300);
}

function clearSearch() {
  var input = document.getElementById('searchInput');
  var clearBtn = document.getElementById('searchClear');
  var badge = document.getElementById('searchBadge');
  if (input) input.value = '';
  if (clearBtn) clearBtn.style.display = 'none';
  if (badge) badge.style.display = 'none';
}

function performSearch(query) {
  var badge = document.getElementById('searchBadge');
  if (!query) { badge.style.display = 'none'; return; }

  var norm = normalizeAr(query);
  var found = null;
  var foundGroup = '';

  // Search in groupsData
  var groups = Object.keys(groupsData);
  for (var g = 0; g < groups.length; g++) {
    var grp = groups[g];
    var students = groupsData[grp];
    for (var s = 0; s < students.length; s++) {
      var st = students[s];
      var nameNorm = normalizeAr(st.student_name || '');
      var idNorm = (st.personal_id || '').toString().trim();
      if (nameNorm.indexOf(norm) !== -1 || idNorm.indexOf(query) !== -1) {
        found = st;
        foundGroup = grp;
        break;
      }
    }
    if (found) break;
  }

  if (found) {
    badge.textContent = '\u062A\u0645 \u0627\u0644\u0639\u062B\u0648\u0631 \u0639\u0644\u0649: ' + foundGroup;
    badge.style.display = 'inline-block';
    // Select the group in dropdown
    var sel = document.getElementById('groupSelect');
    sel.value = foundGroup;
    onControlChange();
  } else {
    badge.textContent = '\u0644\u0627 \u062A\u0648\u062C\u062F \u0646\u062A\u064A\u062C\u0629';
    badge.style.background = '#ef9a9a';
    badge.style.display = 'inline-block';
    setTimeout(function() {
      badge.style.background = '#26A69A';
    }, 2000);
  }
}

function onWaSent(link) {
  var row = link.closest('tr');
  if (row) {
    var cb = row.querySelector('.sent-check');
    if (cb) cb.checked = true;
    saveAllAttendance();
  }
}

function buildWaMsg(name, status) {
  var date = document.getElementById('dateInput') ? document.getElementById('dateInput').value : '';
  var dayBadge = document.getElementById('dayBadge');
  var day = (dayBadge && !dayBadge.className.includes('empty')) ? dayBadge.textContent.trim() : '';
  var dateFormatted = date;
  if (date && date.includes('-')) {
    var parts = date.split('-');
    if (parts.length === 3) dateFormatted = parts[2] + '/' + parts[1] + '/' + parts[0];
  }
  var isAbsent = (status === '\u063a\u0627\u0626\u0628');
  var statusWord = isAbsent ? '\u063a\u0627\u0626\u0628\u064b\u0627' : '\u0645\u062a\u0623\u062e\u0631\u064b\u0627';
  var NL = String.fromCharCode(10);
  var msg = '\u0627\u0644\u0633\u0644\u0627\u0645 \u0639\u0644\u064a\u0643\u0645 \u0648\u0631\u062d\u0645\u0629 \u0627\u0644\u0644\u0647 \u0648\u0628\u0631\u0643\u0627\u062a\u0647' + NL + NL
    + '\u0648\u0644\u064a \u0623\u0645\u0631 \u0627\u0644\u0637\u0627\u0644\u0628/\u0629 ' + name + '\u060c' + NL
    + '\u0646\u0648\u062f \u0625\u062d\u0627\u0637\u062a\u0643\u0645 \u0639\u0644\u0645\u064b\u0627 \u0628\u0623\u0646 \u0627\u0644\u0637\u0627\u0644\u0628/\u0629 ' + name + ' \u0643\u0627\u0646 ' + statusWord + ' \u064a\u0648\u0645 ' + day + ' \u0627\u0644\u0645\u0648\u0627\u0641\u0642 ' + dateFormatted + NL + NL
    + '\u0648\u062d\u0631\u0635\u064b\u0627 \u0645\u0646\u0627 \u0639\u0644\u0649 \u0645\u062a\u0627\u0628\u0639\u0629 \u0623\u0628\u0646\u0627\u0626\u0646\u0627 \u0627\u0644\u0637\u0644\u0628\u0629 \u0648\u0627\u0644\u0627\u0637\u0645\u0626\u0646\u0627\u0646 \u0639\u0644\u0649 \u0645\u0633\u062a\u0648\u0627\u0647\u0645 \u0627\u0644\u062f\u0631\u0627\u0633\u064a\u060c \u0646\u0623\u0645\u0644 \u062f\u0639\u0645\u0643\u0645 \u0627\u0644\u0643\u0631\u064a\u0645 \u0641\u064a \u062a\u0639\u0632\u064a\u0632 \u0627\u0644\u0627\u0644\u062a\u0632\u0627\u0645 \u0628\u0627\u0644\u062d\u0636\u0648\u0631 \u0627\u0644\u0645\u0646\u062a\u0638\u0645\u060c \u0644\u0645\u0627 \u0644\u0630\u0644\u0643 \u0645\u0646 \u0623\u062b\u0631 \u0625\u064a\u062c\u0627\u0628\u064a \u0641\u064a \u0627\u0633\u062a\u064a\u0639\u0627\u0628 \u0627\u0644\u062f\u0631\u0648\u0633 \u0648\u0636\u0645\u0627\u0646 \u062a\u0633\u0644\u0633\u0644 \u0627\u0644\u0639\u0645\u0644\u064a\u0629 \u0627\u0644\u062a\u0639\u0644\u064a\u0645\u064a\u0629\u060c \u062d\u064a\u062b \u0625\u0646 \u0627\u0644\u063a\u064a\u0627\u0628 \u0648\u0627\u0644\u062a\u0623\u062e\u0631 \u0627\u0644\u0645\u062a\u0643\u0631\u0631 \u0642\u062f \u064a\u0624\u062b\u0631 \u0633\u0644\u0628\u064b\u0627 \u0639\u0644\u0649 \u0627\u0644\u062a\u062d\u0635\u064a\u0644 \u0627\u0644\u062f\u0631\u0627\u0633\u064a.' + NL + NL
    + '\u0646\u0634\u0643\u0631 \u0644\u0643\u0645 \u062d\u0633\u0646 \u062a\u0639\u0627\u0648\u0646\u0643\u0645 \u0648\u0627\u0647\u062a\u0645\u0627\u0645\u0643\u0645\u060c \u0648\u0646\u062a\u0645\u0646\u0649 \u0644\u0644\u0637\u0627\u0644\u0628/\u0629 \u062f\u0648\u0627\u0645 \u0627\u0644\u062a\u0648\u0641\u064a\u0642 \u0648\u0627\u0644\u0646\u062c\u0627\u062d.' + NL + NL
    + '\u060c\u0648\u062a\u0641\u0636\u0644\u0648\u0627 \u0628\u0642\u0628\u0648\u0644 \u0641\u0627\u0626\u0642 \u0627\u0644\u0627\u062d\u062a\u0631\u0627\u0645 \u0648\u0627\u0644\u062a\u0642\u062f\u064a\u0631' + NL + NL
    + '\u0645\u0645\u0644\u0643\u0629 \u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a';
  return msg;
}

function loadGroups() {
  fetch('/api/groups-students')
    .then(function(r){ return r.json(); })
    .then(function(data) {
      groupsData = data;
      var sel = document.getElementById('groupSelect');
      sel.innerHTML = '<option value="">&#8212; \u0627\u062e\u062a\u0631 \u0627\u0644\u0645\u062c\u0645\u0648\u0639\u0629 &#8212;</option>';
      var groups = Object.keys(data).sort();
      for(var i=0; i<groups.length; i++) {
        var opt = document.createElement('option');
        opt.value = groups[i];
        opt.textContent = groups[i] + ' (' + data[groups[i]].length + ' \u0637\u0627\u0644\u0628)';
        sel.appendChild(opt);
      }
      // Update search placeholder with count
      var totalStudents = Object.values(data).reduce(function(a,b){return a+b.length;},0);
      var inp = document.getElementById('searchInput');
      if(inp) inp.placeholder = '\u0627\u0628\u062d\u062b \u0628\u064a\u0646 ' + totalStudents + ' \u0637\u0627\u0644\u0628...';
    })
    .catch(function() { showToast('\u062e\u0637\u0623 \u0641\u064a \u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a', '#e53935'); });
}

function updateDayBadge(val) {
  var badge = document.getElementById('dayBadge');
  if(!val) { badge.textContent = '\u2014'; badge.className = 'day-badge empty'; return; }
  var p = val.split('-');
  var d = new Date(parseInt(p[0]), parseInt(p[1])-1, parseInt(p[2]));
  badge.textContent = AR_DAYS[d.getDay()];
  badge.className = 'day-badge';
}

function onControlChange() {
  var group = document.getElementById('groupSelect').value;
  var date = document.getElementById('dateInput').value;
  updateDayBadge(date);

  // Hide everything and reset
  document.getElementById('attSection').style.display = 'none';
  document.getElementById('attFooterBtns').style.display = 'none';
  clearSearch();
  document.getElementById('alertBanner').className = 'alert-banner';
  document.getElementById('alertBanner').style.display = 'none';
  document.getElementById('studentCount').style.display = 'none';

  if(!group || !date) return;

  // Debounce check
  if(checkTimeout) clearTimeout(checkTimeout);
  checkTimeout = setTimeout(function(){ checkAndLoad(group, date); }, 300);
}

function checkAndLoad(group, date) {
  document.getElementById('checkSpinner').classList.add('show');
  Promise.all([
    fetch('/api/attendance/check?group=' + encodeURIComponent(group) + '&date=' + encodeURIComponent(date)).then(function(r){ return r.json(); }),
    fetch('/api/attendance/student-stats?group=' + encodeURIComponent(group)).then(function(r){ return r.json(); }).catch(function(){ return {stats:{}}; })
  ]).then(function(results) {
    var data = results[0];
    var statsResp = results[1] || {};
    var stats = statsResp.stats || {};
      document.getElementById('checkSpinner').classList.remove('show');
      var students = groupsData[group] || [];
      document.getElementById('studentCount').textContent = students.length + ' \u0637\u0627\u0644\u0628';
      document.getElementById('studentCount').style.display = 'inline-block';
      document.getElementById('attSectionGroupName').textContent = '\u2014 ' + group;

      if(data.exists) {
        currentMode = 'exists';
        existingRecords = {};
        for(var i=0; i<data.records.length; i++) {
          _indexAttRecord(existingRecords, data.records[i]);
        }
        showAlert('exists', '\u26a0\ufe0f \u062a\u0645 \u062a\u0633\u062c\u064a\u0644 \u0627\u0644\u063a\u064a\u0627\u0628 \u0644\u0647\u0630\u0647 \u0627\u0644\u0645\u062c\u0645\u0648\u0639\u0629 \u0641\u064a \u0647\u0630\u0627 \u0627\u0644\u062a\u0627\u0631\u064a\u062e \u0645\u0633\u0628\u0642\u0627\u064b. \u064a\u0645\u0643\u0646\u0643 \u062a\u0639\u062f\u064a\u0644 \u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0623\u062f\u0646\u0627\u0647.');
        document.getElementById('btnSaveLabel').textContent = '\u062d\u0641\u0638 \u0627\u0644\u062a\u0639\u062f\u064a\u0644\u0627\u062a';
        renderTable(students, data.records, stats);
      } else {
        currentMode = 'new';
        existingRecords = {};
        showAlert('new', '\u2705 \u0644\u0645 \u064a\u062a\u0645 \u062a\u0633\u062c\u064a\u0644 \u063a\u064a\u0627\u0628 \u0644\u0647\u0630\u0647 \u0627\u0644\u0645\u062c\u0645\u0648\u0639\u0629 \u0641\u064a \u0647\u0630\u0627 \u0627\u0644\u062a\u0627\u0631\u064a\u062e.');
        document.getElementById('btnSaveLabel').textContent = '\u062d\u0641\u0638 \u0627\u0644\u062a\u0633\u062c\u064a\u0644\u0627\u062a';
        renderTable(students, [], stats);
      }
      document.getElementById('attSection').style.display = 'block';
      document.getElementById('attFooterBtns').style.display = 'flex';
    })
    .catch(function() {
      document.getElementById('checkSpinner').classList.remove('show');
      showToast('\u062e\u0637\u0623 \u0641\u064a \u0627\u0644\u062a\u062d\u0642\u0642', '#e53935');
    });
}

function showAlert(type, msg) {
  var banner = document.getElementById('alertBanner');
  banner.className = 'alert-banner ' + type;
  banner.style.display = 'flex';
  document.getElementById('alertText').textContent = msg;
}

function onStatusChange(sel) {
  sel.className = 'status-select';
  if(sel.value === '\u062d\u0627\u0636\u0631') sel.className += ' present';
  else if(sel.value === '\u063a\u0627\u0626\u0628') sel.className += ' absent';
  else if(sel.value === '\u0645\u062a\u0623\u062e\u0631') sel.className += ' late';
  // Update WhatsApp button in the same row
  var tr = sel.closest('tr');
  if (!tr) return;
  var actionCell = tr.querySelector('.action-cell');
  if (!actionCell) return;
  var existingLink = actionCell.querySelector('.btn-wa, .wa-na');
  var name = sel.getAttribute('data-name') || '';
  var wa = actionCell.getAttribute('data-wa') || (existingLink ? existingLink.getAttribute('data-wa') : '') || '';
  var status = sel.value;
  var showBtn = (status === '\u063a\u0627\u0626\u0628' || status === '\u0645\u062a\u0623\u062e\u0631');
  if (!wa) { return; } // no phone, keep as-is
  if (showBtn) {
    var msg = buildWaMsg(name, status);
    var waNum = wa.replace(/[^0-9]/g, '');
    if (waNum.charAt(0) === '0') waNum = '973' + waNum.slice(1);
    var waUrl = 'https://wa.me/' + waNum + '?text=' + encodeURIComponent(msg);
    actionCell.innerHTML = '<a class="btn-wa" href="' + waUrl + '" target="_blank" data-name="' + name.replace(/"/g,'&quot;') + '" data-wa="' + wa + '">&#128229; \u0625\u0631\u0633\u0627\u0644 \u0631\u0633\u0627\u0644\u0629</a>';
  } else {
    actionCell.innerHTML = '<button class="btn-wa btn-wa-disabled" disabled data-name="' + name.replace(/"/g,'&quot;') + '" data-wa="' + wa + '">&#128229; \u0625\u0631\u0633\u0627\u0644 \u0631\u0633\u0627\u0644\u0629</button>';
  }
}

// Multi-key lookup helpers for attendance records.
//
// Imported rows and manually-entered rows share group_name + attendance_date
// but may disagree on student_name: an Excel may carry trailing whitespace,
// an alternate Arabic spelling, or a completely different romanisation. The
// roster (from /api/groups-students) and the attendance rows both carry
// personal_id though, so we index every record under three keys — exact
// name, normalised name, personal_id — and look up each roster student by
// whichever key hits first. That is what "match by name OR by student ID"
// means in practice.
function _attNormalizeName(s) {
  if (!s) return '';
  return String(s).toLowerCase()
    .replace(/[\u0623\u0625\u0622\u0671]/g, '\u0627')   // alef family -> alef
    .replace(/\u0629/g, '\u0647')                         // teh marbouta -> heh
    .replace(/\u0649/g, '\u064A')                         // alef maksura -> yeh
    .replace(/[\u064B-\u065F]/g, '')                      // tashkeel
    .replace(/\s+/g, ' ')                                  // collapse whitespace runs
    .trim();
}
function _indexAttRecord(map, rec) {
  if (!rec) return;
  var name = (rec.student_name || '').toString().trim();
  var pid  = (rec.personal_id  || '').toString().trim();
  if (name) {
    if (!map['n:' + name])                         map['n:' + name] = rec;
    var norm = _attNormalizeName(name);
    if (norm && !map['w:' + norm])                 map['w:' + norm] = rec;
  }
  if (pid && !map['p:' + pid])                     map['p:' + pid] = rec;
}
function _attAddStatusKeys(statusMap, msgMap, rec) {
  if (!rec) return;
  var name = (rec.student_name || '').toString().trim();
  var pid  = (rec.personal_id  || '').toString().trim();
  var st   = rec.status || '';
  var ms   = rec.message_status || '';
  if (name) {
    statusMap['n:' + name] = st; msgMap['n:' + name] = ms;
    var norm = _attNormalizeName(name);
    if (norm) { statusMap['w:' + norm] = st; msgMap['w:' + norm] = ms; }
  }
  if (pid) { statusMap['p:' + pid] = st; msgMap['p:' + pid] = ms; }
}
function _attLookup(map, name, pid) {
  if (!map) return '';
  name = (name || '').toString().trim();
  pid  = (pid  || '').toString().trim();
  if (name && map['n:' + name] != null) return map['n:' + name];
  if (name) {
    var norm = _attNormalizeName(name);
    if (norm && map['w:' + norm] != null) return map['w:' + norm];
  }
  if (pid && map['p:' + pid] != null) return map['p:' + pid];
  return '';
}

function renderTable(students, existingList, stats) {
  stats = stats || {};
  var statusMap = {}; var msgStatusMap = {};
  for(var i=0; i<existingList.length; i++) {
    var _r = existingList[i];
    _attAddStatusKeys(statusMap, msgStatusMap, _r);
  }

  var html = '';
  if(!students.length) {
    html = '<tr><td colspan="9" class="empty-state">\u0644\u0627 \u064a\u0648\u062c\u062f \u0637\u0644\u0627\u0628 \u0641\u064a \u0647\u0630\u0647 \u0627\u0644\u0645\u062c\u0645\u0648\u0639\u0629</td></tr>';
  } else {
    for(var i=0; i<students.length; i++) {
      var name = students[i].student_name || '-';
      var pid  = (students[i].personal_id || '').toString();
      var savedStatus    = _attLookup(statusMap,    name, pid);
      var savedMsgStatus = _attLookup(msgStatusMap, name, pid);
      var cssClass = 'status-select';
      if(savedStatus === '\u062d\u0627\u0636\u0631') cssClass += ' present';
      else if(savedStatus === '\u063a\u0627\u0626\u0628') cssClass += ' absent';
      else if(savedStatus === '\u0645\u062a\u0623\u062e\u0631') cssClass += ' late';

      html += '<tr>';
      html += '<td>' + (i+1) + '</td>';
      html += '<td class="student-name-cell">' + name + '</td>';
      html += '<td><select class="' + cssClass + '" data-name="' + name.replace(/"/g, '&quot;') + '" data-pid="' + pid.replace(/"/g, '&quot;') + '" onchange="onStatusChange(this)">';
      html += '<option value="">&#8212; \u0627\u062e\u062a\u0631 &#8212;</option>';
      html += '<option value="\u062d\u0627\u0636\u0631"' + (savedStatus==='\u062d\u0627\u0636\u0631'?' selected':'') + '>\u062d\u0627\u0636\u0631</option>';
      html += '<option value="\u063a\u0627\u0626\u0628"' + (savedStatus==='\u063a\u0627\u0626\u0628'?' selected':'') + '>\u063a\u0627\u0626\u0628</option>';
      html += '<option value="\u0645\u062a\u0623\u062e\u0631"' + (savedStatus==='\u0645\u062a\u0623\u062e\u0631'?' selected':'') + '>\u0645\u062a\u0623\u062e\u0631</option>';
      html += '</select></td>';
      // WhatsApp button cell
      var wa = students[i].whatsapp || '';
      var showWaBtn = (savedStatus === '\u063a\u0627\u0626\u0628' || savedStatus === '\u0645\u062a\u0623\u062e\u0631');
      html += '<td class="action-cell">';
      if (wa) {
        if (showWaBtn) {
          var msgType = buildWaMsg(name, savedStatus);
          var waNum = wa.replace(/[^0-9]/g, '');
          if (waNum.charAt(0) === '0') waNum = '973' + waNum.slice(1);
          var waUrl = 'https://wa.me/' + waNum + '?text=' + encodeURIComponent(msgType);
          html += '<a class="btn-wa" href="' + waUrl + '" target="_blank" data-name="' + name.replace(/"/g,'&quot;') + '" data-wa="' + wa + '" onclick="onWaSent(this)">&#128229; \u0625\u0631\u0633\u0627\u0644 \u0631\u0633\u0627\u0644\u0629</a>';
        } else {
          html += '<button class="btn-wa btn-wa-disabled" disabled data-name="' + name.replace(/"/g,'&quot;') + '" data-wa="' + wa + '">&#128229; \u0625\u0631\u0633\u0627\u0644 \u0631\u0633\u0627\u0644\u0629</button>';
        }
      } else {
        html += '<span class="wa-na wa-missing">&#128242; &#10006;</span>';
      }
      html += '</td>';
      
      html += '<td class="sent-cell"><input type="checkbox" class="sent-check"' + (savedMsgStatus === '1' ? ' checked' : '') + '></td>';
      // Attendance stat cells (present/absent/late/percentage).
      var st = stats[name] || {present:0, absent:0, late:0, total:0, pct:0};
      var pctCls = 'att-stat att-stat-pct';
      if (st.total) {
        if (st.pct < 50) pctCls = 'att-stat att-stat-pct-low';
        else if (st.pct < 75) pctCls = 'att-stat att-stat-pct-mid';
      }
      html += '<td class="att-stat att-stat-present">' + st.present + '</td>';
      html += '<td class="att-stat att-stat-absent">' + st.absent + '</td>';
      html += '<td class="att-stat att-stat-late">' + st.late + '</td>';
      html += '<td class="' + pctCls + '">' + (st.total ? (st.pct + '%') : '&mdash;') +
              (st.total ? '<div class="att-stat-bar"><div class="att-stat-bar-fill" style="width:' + Math.min(100, st.pct) + '%;"></div></div>' : '') +
              '</td>';
      html += '</tr>';
    }
  }
  document.getElementById('attTableBody').innerHTML = html;
}

function saveAllAttendance() {
  var group = document.getElementById('groupSelect').value;
  var date = document.getElementById('dateInput').value;
  var dayBadge = document.getElementById('dayBadge');
  var dayName = dayBadge.className.includes('empty') ? '' : dayBadge.textContent;

  if(!group || !date) { showToast('\u0627\u062e\u062a\u0631 \u0645\u062c\u0645\u0648\u0639\u0629 \u0648\u062a\u0627\u0631\u064a\u062e\u0627\u064b', '#e53935'); return; }

  var rows = document.querySelectorAll('#attTableBody tr');
  var saves = [];
  var updates = [];

  rows.forEach(function(tr) {
    var sel = tr.querySelector('.status-select');
    if(!sel) return;
    var name = sel.getAttribute('data-name');
    var status = sel.value;
    if(!name) return;
    var pid = sel.getAttribute('data-pid') || '';

    var existing = (currentMode === 'exists') ? _attLookup(existingRecords, name, pid) : null;
    if (existing) {
      // Update existing record (manual entry or imported).
      updates.push({ id: existing.id, status: status,
        attendance_date: existing.attendance_date,
        day_name: existing.day_name,
        group_name: existing.group_name,
        student_name: existing.student_name,
        contact_number: existing.contact_number || '',
        message: existing.message || '',
        message_status: (tr.querySelector('.sent-check') && tr.querySelector('.sent-check').checked) ? '1' : (existing.message_status || ''),
        study_status: existing.study_status || ''
      });
    } else {
      // Either mode==='new', or a student on the roster has no match in
      // existingRecords (e.g. a new student added after the import).
      // Either way, insert a fresh row.
      saves.push({ attendance_date: date, day_name: dayName,
        group_name: group, student_name: name,
        contact_number: '', status: status, message: '', message_status: '', study_status: '' });
    }
  });

  var btn = document.getElementById('btnSaveAll');
  btn.disabled = true;

  var total = saves.length + updates.length;
  var done = 0;

  function finish() {
    btn.disabled = false;
    showToast('\u062a\u0645 \u062d\u0641\u0638 ' + done + '/' + total + ' \u0633\u062c\u0644', '#00897B');
    // Reload to reflect saved state
    checkAndLoad(group, date);
  }

  if(total === 0) { btn.disabled = false; showToast('\u0644\u0627 \u062a\u0648\u062c\u062f \u062a\u063a\u064a\u064a\u0631\u0627\u062a', '#888'); return; }

  var pending = total;

  saves.forEach(function(rec) {
    fetch('/api/attendance', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(rec) })
      .then(function(r){ return r.json(); }).then(function(d){ if(d.ok) done++; pending--; if(pending===0) finish(); })
      .catch(function(){ pending--; if(pending===0) finish(); });
  });

  updates.forEach(function(rec) {
    fetch('/api/attendance/' + rec.id, { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(rec) })
      .then(function(r){ return r.json(); }).then(function(d){ if(d.ok) done++; pending--; if(pending===0) finish(); })
      .catch(function(){ pending--; if(pending===0) finish(); });
  });
}

loadGroups();
</script>
</body>
</html>"""


DATABASE_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>&#x642;&#x627;&#x639;&#x62F;&#x629; &#x627;&#x644;&#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; - Mindex</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Tahoma,Arial,sans-serif;}
html{height:100%;overflow:hidden;margin:0;direction:rtl;}body{height:100%;overflow:hidden;margin:0;}
body{background:#f5f3ff;direction:rtl;display:flex;flex-direction:column;}
.topbar{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;}
.topbar h1{font-size:20px;font-weight:800;}
.btn-home{background:rgba(255,255,255,.18);color:#fff;border:1.5px solid rgba(255,255,255,.5);padding:8px 18px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;}
.btn-home:hover{background:rgba(255,255,255,.3);}
.main{padding:24px 28px;flex:1;overflow-y:auto;overflow-x:hidden;min-height:0;direction:ltr;}.main>*{direction:rtl;}
.page-title{font-size:22px;font-weight:800;color:#6B3FA0;margin-bottom:20px;}
.stats{display:flex;gap:14px;margin-bottom:22px;}
.stat-card{background:#fff;border-radius:12px;padding:14px 22px;box-shadow:0 2px 10px rgba(107,63,160,.1);display:flex;flex-direction:column;align-items:center;min-width:120px;}
.stat-num{font-size:28px;font-weight:800;color:#6B3FA0;}
.stat-label{font-size:12px;color:#888;margin-top:2px;}
.btn-add{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border:none;padding:11px 26px;border-radius:11px;font-size:15px;font-weight:700;cursor:pointer;margin-bottom:20px;display:inline-flex;align-items:center;gap:8px;}
.btn-add:hover{opacity:.9;}
.search-bar{display:flex;gap:10px;margin-bottom:18px;}
.search-bar input{flex:1;padding:10px 16px;border:1.5px solid #E0D5F0;border-radius:10px;font-size:14px;outline:none;background:#fff;}
.search-bar input:focus{border-color:#6B3FA0;}
.btn-search{background:#6B3FA0;color:#fff;border:none;padding:10px 20px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;}
.table-wrap{background:#fff;border-radius:12px;box-shadow:0 1px 6px rgba(107,63,160,.08);overflow-x:auto;overflow-y:auto;direction:rtl;border:1px solid #f0ebff;}
/* Sticky nav bar with pills that scroll to each section. */
.db-nav{position:sticky;top:0;background:rgba(255,255,255,0.95);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px);z-index:60;padding:12px 24px;margin:-24px -28px 24px;border-bottom:1px solid #eee;display:flex;gap:10px;flex-wrap:wrap;align-items:center;box-shadow:0 2px 10px rgba(0,0,0,0.04);}
.db-nav-label{font-size:13px;color:#888;font-weight:700;margin-left:4px;}
.db-nav-btn{padding:8px 16px;border-radius:10px;background:#f5f3ff;color:#6B3FA0;font-weight:700;font-size:14px;text-decoration:none;white-space:nowrap;border:1.5px solid transparent;cursor:pointer;transition:all .15s;}
.db-nav-btn:hover{background:#ede7f6;border-color:#8B5CC8;}
.db-nav-btn.active{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border-color:transparent;box-shadow:0 3px 8px rgba(107,63,160,0.25);}
.db-nav-btn.teal{background:#e0f2f1;color:#00695C;}
.db-nav-btn.teal:hover{background:#b2dfdb;border-color:#00897B;}
.db-nav-btn.teal.active{background:linear-gradient(135deg,#00695C,#4DB6AC);color:#fff;}
.db-nav-btn.cyan{background:#e0f7fa;color:#0097A7;}
.db-nav-btn.cyan:hover{background:#b2ebf2;border-color:#00BCD4;}
.db-nav-btn.cyan.active{background:linear-gradient(135deg,#00838F,#00BCD4);color:#fff;}
.db-nav-btn.orange{background:#fff3e0;color:#E65100;}
.db-nav-btn.orange:hover{background:#ffe0b2;border-color:#FB8C00;}
.db-nav-btn.orange.active{background:linear-gradient(135deg,#E65100,#FB8C00);color:#fff;}
.db-nav-btn.blue{background:#e3f2fd;color:#1565C0;}
.db-nav-btn.blue:hover{background:#bbdefb;border-color:#1E88E5;}
.db-nav-btn.blue.active{background:linear-gradient(135deg,#1565C0,#1E88E5);color:#fff;}
/* Section cards grouping each data table + its action bar. */
.db-section{background:#fff;border-radius:16px;padding:22px 24px;margin-bottom:28px;box-shadow:0 3px 14px rgba(107,63,160,.08);border:1px solid #eee;scroll-margin-top:80px;}
.db-section-title{font-size:19px;font-weight:800;margin-bottom:14px;padding-bottom:12px;border-bottom:2px solid #f0ebff;display:flex;align-items:center;gap:10px;}
.db-section .table-wrap{box-shadow:none;border:1px solid #eee;}
.custom-table-section{background:#fff;border-radius:16px;padding:22px 24px;margin:0 0 28px 0;box-shadow:0 3px 14px rgba(21,101,192,.08);border:1px solid #e0f0ff;scroll-margin-top:80px;}
.custom-table-section .table-wrap{box-shadow:none;border:1px solid #eee;}
table{width:100%;border-collapse:collapse;min-width:2800px;}
thead tr{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;}
th{padding:13px 12px;font-size:13px;font-weight:700;text-align:right;white-space:nowrap;}
tbody tr{border-bottom:1px solid #f0ebff;transition:background .15s;}
tbody tr:hover{background:#faf7ff;}
td{padding:11px 12px;font-size:13px;text-align:right;color:#444;} td.phone-cell{direction:ltr;unicode-bidi:embed;}
td.name-cell{font-weight:600;color:#6B3FA0;text-align:right;}
.installment-cell{min-width:200px;}
.installment-select{width:100%;padding:3px 5px;border:1px solid #ccc;border-radius:4px;font-size:12px;background:#fff;}
.installment-select-edit{width:100%;padding:6px;border:1px solid #ccc;border-radius:6px;font-size:14px;}
.tq-detail{color:#555;font-size:11px;display:block;margin-top:2px;direction:rtl;}
.badge{display:inline-block;padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600;}
.badge-pass{background:#e8f5e9;color:#2e7d32;}
.badge-fail{background:#fce4ec;color:#c62828;}
.badge-pend{background:#fff8e1;color:#f57f17;}
.no-data{text-align:center;padding:48px;color:#bbb;font-size:16px;}
.action-btn{background:none;border:none;cursor:pointer;padding:4px 8px;border-radius:6px;font-size:15px;}
.btn-edit{color:#6B3FA0;}
.btn-edit:hover{background:#f3eeff;}
.btn-del{color:#e53935;}
.btn-del:hover{background:#fce4ec;}
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:1000;align-items:center;justify-content:center;}
.modal-bg.open{display:flex;}
.modal{background:#fff;border-radius:18px;padding:30px 28px;width:720px;max-width:96vw;max-height:90vh;overflow-y:auto;box-shadow:0 10px 40px rgba(107,63,160,.2);}
.modal h2{font-size:20px;font-weight:800;color:#6B3FA0;margin-bottom:22px;text-align:center;}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.form-grid .full{grid-column:1/-1;}
.field label{display:block;font-size:13px;color:#6B3FA0;font-weight:600;margin-bottom:5px;}
.field input,.field select{width:100%;padding:10px 13px;border:1.5px solid #E0D5F0;border-radius:9px;font-size:14px;outline:none;background:#faf7ff;direction:rtl;} .field input.ltr{direction:ltr;text-align:left;}
.field input:focus,.field select:focus{border-color:#6B3FA0;background:#fff;}
.modal-actions{display:flex;gap:12px;justify-content:center;margin-top:22px;}
.btn-save{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border:none;padding:11px 34px;border-radius:11px;font-size:15px;font-weight:700;cursor:pointer;}
.btn-cancel{background:#f0ebff;color:#6B3FA0;border:none;padding:11px 28px;border-radius:11px;font-size:15px;font-weight:600;cursor:pointer;}
.btn-cancel:hover{background:#e0d5f0;}
.toast{position:fixed;bottom:28px;right:28px;background:#6B3FA0;color:#fff;padding:13px 24px;border-radius:12px;font-size:14px;font-weight:600;z-index:9999;display:none;box-shadow:0 4px 20px rgba(107,63,160,.3);}
.toast.show{display:block;}
.confirm-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:2000;align-items:center;justify-content:center;}
.confirm-bg.open{display:flex;}
.confirm-box{background:#fff;border-radius:16px;padding:28px 32px;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,.2);max-width:380px;width:94%;}
.confirm-box h3{font-size:18px;font-weight:800;color:#c62828;margin-bottom:12px;}
.confirm-box p{color:#555;margin-bottom:22px;font-size:14px;}
.confirm-actions{display:flex;gap:12px;justify-content:center;}
.btn-confirm-del{background:#e53935;color:#fff;border:none;padding:10px 26px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;}
.btn-confirm-cancel{background:#f5f5f5;color:#444;border:none;padding:10px 22px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;}
.btn-del-row{background:none;border:none;color:#e53935;font-size:16px;cursor:pointer;padding:4px 8px;border-radius:6px;}
.btn-del-row:hover{background:#fce4ec;}
.editable{cursor:pointer;}
.editable:hover{background:#f3eeff;}
.btn-delete-table{background:linear-gradient(135deg,#c0392b,#e74c3c);color:#fff;border:none;padding:10px 18px;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:6px;}
.btn-delete-table:hover{opacity:0.9;}
.custom-table-section{margin:30px 0 0 0;}
.custom-table-title{font-size:1.2em;font-weight:700;color:#1565C0;margin-bottom:8px;}
.wizard-step{display:none;}
.wizard-step.active{display:block;}
.col-name-input{width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;margin-bottom:6px;box-sizing:border-box;}
.wizard-nav{display:flex;gap:10px;margin-top:14px;justify-content:flex-end;}
.step-indicator{display:flex;gap:6px;margin-bottom:16px;}
.step-dot{width:10px;height:10px;border-radius:50%;background:#ddd;}
.step-dot.active{background:#1976D2;}
.btn-tab{background:#f0ebff;color:#6c3fa0;border:none;padding:8px 14px;border-radius:8px;font-size:.9em;font-weight:600;cursor:pointer;}
.btn-tab.active{background:#6c3fa0;color:#fff;}
.btn-tab:hover{opacity:0.85;}
.bulk-cb{width:16px;height:16px;cursor:pointer;accent-color:#6B3FA0;vertical-align:middle;}
.bulk-col{width:38px;text-align:center;padding:6px 4px !important;}
/* Taqseet: cells locked because the course amount is fully allocated. */
.taqseet-locked{background:#ececec !important;color:#bbb !important;cursor:not-allowed !important;user-select:none;}
.taqseet-locked:focus{outline:none;}
.btn-bulk-del{display:none;background:linear-gradient(135deg,#c0392b,#e74c3c);color:#fff;border:none;padding:10px 18px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;align-items:center;gap:6px;}
.btn-bulk-del.show{display:inline-flex;}
.btn-bulk-del:hover{opacity:0.9;}
/* Frozen column styling — cells that stay pinned as the .table-wrap scrolls */
.frozen-col{position:sticky!important;z-index:2;}
thead .frozen-col{z-index:4;background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;}
tbody .frozen-col{background:#fff;box-shadow:-2px 0 4px rgba(0,0,0,0.06);}
tbody tr:hover .frozen-col{background:#faf7ff;}
.freeze-modal-body{max-height:50vh;overflow-y:auto;border:1px solid #eee;border-radius:8px;padding:4px 10px;margin:10px 0;}
.freeze-modal-body label{display:flex;align-items:center;gap:8px;padding:6px 4px;cursor:pointer;border-bottom:1px solid #f5f5f5;}
.freeze-modal-body label:last-child{border-bottom:none;}
.freeze-modal-body label:hover{background:#f3eeff;}
.freeze-modal-body input{margin:0;}
</style>
</head>
<body>
<div class="topbar">
  <h1>&#x627;&#x644;&#x635;&#x641;&#x62D;&#x629; &#x627;&#x644;&#x631;&#x626;&#x64A;&#x633;&#x64A;&#x629; &#x644;&#x645;&#x639;&#x644;&#x648;&#x645;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</h1>
  <a href="/settings" class="btn-home" style="background:linear-gradient(135deg,#6B3FA0,#8B5CC8);margin-left:8px;">&#9881; &#x625;&#x639;&#x62F;&#x627;&#x62F;&#x627;&#x62A;</a><a href="/dashboard" class="btn-home">&larr; &#x627;&#x644;&#x631;&#x626;&#x64A;&#x633;&#x64A;&#x629;</a>
</div>
<div class="main">
  <div class="page-title-bar" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
    <div class="page-title" style="margin-bottom:0;">&#x642;&#x627;&#x639;&#x62F;&#x629; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</div>
    <div style="display:flex;gap:10px;align-items:center;">
      <a href="/attendance" style="background:linear-gradient(135deg,#00897B,#26A69A);color:#fff;padding:11px 26px;border-radius:11px;font-size:15px;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;gap:8px;">&#x62A;&#x633;&#x62C;&#x64A;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628; &#x1F4C5;</a>
      <a href="/groups" class="btn-groups" style="background:linear-gradient(135deg,#00BCD4,#0097A7);color:#fff;padding:11px 26px;border-radius:11px;font-size:15px;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;gap:8px;">&#128101; &#x645;&#x639;&#x644;&#x648;&#x645;&#x627;&#x62A; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</a>
    </div>
  </div>
  <div class="db-nav" id="dbNav">
    <span class="db-nav-label">&#x627;&#x644;&#x627;&#x646;&#x62A;&#x642;&#x627;&#x644; &#x625;&#x644;&#x649;:</span>
    <a class="db-nav-btn" href="#sec-students" data-target="sec-students" onclick="dbNavGo(event,'sec-students')">&#x1F393; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</a>
    <a class="db-nav-btn cyan" href="#sec-groups" data-target="sec-groups" onclick="dbNavGo(event,'sec-groups')">&#x1F465; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</a>
    <a class="db-nav-btn" href="#sec-taqseet" data-target="sec-taqseet" onclick="dbNavGo(event,'sec-taqseet')">&#x1F4CB; &#x627;&#x644;&#x62A;&#x642;&#x633;&#x64A;&#x637;</a>
    <a class="db-nav-btn orange" href="#sec-attendance" data-target="sec-attendance" onclick="dbNavGo(event,'sec-attendance')">&#x1F4C5; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</a>
    <a class="db-nav-btn blue" href="#sec-evals" data-target="sec-evals" onclick="dbNavGo(event,'sec-evals')">&#x1F4DD; &#x627;&#x644;&#x62A;&#x642;&#x64A;&#x64A;&#x645;&#x627;&#x62A;</a>
    <a class="db-nav-btn teal" href="#sec-paylog" data-target="sec-paylog" onclick="dbNavGo(event,'sec-paylog')">&#x1F4B0; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x641;&#x639;</a>
    <span id="dbNavCustom"></span>
  </div>
  <div class="db-section" id="sec-students">
  <div class="db-section-title" style="color:#6B3FA0;">&#x1F393; &#x642;&#x627;&#x639;&#x62F;&#x629; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</div>
  <div class="stats">
    <div class="stat-card">
      <span class="stat-num" id="totalCount">0</span>
      <span class="stat-label">&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</span>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:20px;"><button class="btn-add" style="margin-bottom:0;" onclick="openAddModal()">+ &#x625;&#x636;&#x627;&#x641;&#x629; &#x637;&#x627;&#x644;&#x628;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#43A047,#2E7D32);" onclick="openStudentExcelModal()">&#128196; &#x625;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openUniversalTableEditModal('students')">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
  <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#3F51B5,#5C6BC0);" onclick="openGenericExcelModal()">&#x1F4E5; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; Excel</button><button class="btn-delete-table" onclick="openDeleteTableModal()">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal('students')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00897B,#26A69A);" onclick="utemFocusSearch('students')">&#x1F50D; &#x628;&#x62D;&#x62B;</button><button id="bulkDelBtn_students" class="btn-bulk-del" onclick="_bulkDelete('studentsBody',function(id){return '/api/students/'+id;},loadStudents,'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x637;&#x627;&#x644;&#x628;&#x61F;')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button></div>
  <div class="search-bar">
    <input type="text" id="searchInput" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x644;&#x627;&#x633;&#x645; &#x623;&#x648; &#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A;..." oninput="filterTable()">
    <button class="btn-search" onclick="filterTable()">&#x628;&#x62D;&#x62B;</button>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th class="bulk-col"><input type="checkbox" id="selectAll_students" class="bulk-cb" onclick="_bulkSelectAll('studentsBody','selectAll_students','bulkDelBtn_students',this.checked)"></th>
          <th>#</th>
          <th>&#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A;</th>
          <th>&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;</th>
          <th>&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x648;&#x627;&#x62A;&#x633;&#x627;&#x628; &#x627;&#x644;&#x645;&#x639;&#x62A;&#x645;&#x62F;</th>
          <th>&#x627;&#x644;&#x635;&#x641;</th>
          <th>&#x642;&#x62F;&#x64A;&#x645; &#x62C;&#x62F;&#x64A;&#x62F; 2026</th>
          <th>&#x62A;&#x633;&#x62C;&#x64A;&#x644; &#x627;&#x644;&#x641;&#x635;&#x644; &#x627;&#x644;&#x62B;&#x627;&#x646;&#x64A; 2026</th>
          <th>&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</th>
          <th>&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; (&#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646;)</th>
          <th>&#x627;&#x644;&#x646;&#x62A;&#x64A;&#x62C;&#x629; &#x627;&#x644;&#x646;&#x647;&#x627;&#x626;&#x64A;&#x629; (&#x62A;&#x62D;&#x62F;&#x64A;&#x62F; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 2026)</th>
          <th>&#x627;&#x644;&#x649; &#x627;&#x64A;&#x646; &#x648;&#x635;&#x644; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; 2026</th>
          <th>&#x647;&#x644; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x645;&#x646;&#x627;&#x633;&#x628; &#x644;&#x647;&#x630;&#x627; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 2026&#x61F;</th>
          <th>&#x627;&#x633;&#x62A;&#x644;&#x627;&#x645; &#x627;&#x644;&#x643;&#x62A;&#x628;</th>
          <th>&#x627;&#x644;&#x645;&#x62F;&#x631;&#x633; 2026</th>
          <th>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x627;&#x648;&#x644; 2026</th>
          <th>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62B;&#x627;&#x646;&#x64A;</th>
          <th>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62B;&#x627;&#x644;&#x62B;</th>
          <th>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x631;&#x627;&#x628;&#x639;</th>
          <th>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62E;&#x627;&#x645;&#x633;</th>
          <th>&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x645;</th>
          <th>&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x628;</th>
          <th>&#x647;&#x627;&#x62A;&#x641; &#x627;&#x62E;&#x631;</th>
          <th>&#x645;&#x643;&#x627;&#x646; &#x627;&#x644;&#x633;&#x643;&#x646;</th>
          <th>&#x639;&#x646;&#x648;&#x627;&#x646; &#x627;&#x644;&#x645;&#x646;&#x632;&#x644;</th>
          <th>&#x627;&#x644;&#x637;&#x631;&#x64A;&#x642;</th>
          <th>&#x627;&#x644;&#x645;&#x62C;&#x645;&#x639;</th>
          <th>&#x627;&#x62C;&#x631;&#x627;&#x621;&#x627;&#x62A;</th>
        </tr>
      </thead>
      <tbody id="studentsBody">
        <tr><td colspan="28" class="no-data">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x60C; &#x627;&#x636;&#x641; &#x627;&#x648;&#x644; &#x637;&#x627;&#x644;&#x628;</td></tr>
      </tbody>
    </table>
  </div>
  </div>

<!-- ===== GROUPS TABLE SECTION ===== -->
<div class="db-section" id="sec-groups">
  <div class="db-section-title" style="color:#0097A7;">&#128101; &#x645;&#x639;&#x644;&#x648;&#x645;&#x627;&#x62A; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</div>
  <div class="stats">
    <div class="stat-card" style="border-top:3px solid #00BCD4;">
      <span class="stat-num" id="groupsTotalCount" style="color:#00BCD4;">0</span>
      <span class="stat-label">&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</span>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:20px;"><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00BCD4,#0097A7);" onclick="openAddGroupModal2()">+ &#x625;&#x636;&#x627;&#x641;&#x629; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#43A047,#2E7D32);" onclick="openGenericExcelModal('student_groups')">&#128196; &#x625;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openUniversalTableEditModal('groups')">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#3F51B5,#5C6BC0);" onclick="openGenericExcelModal()">&#x1F4E5; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; Excel</button><button class="btn-delete-table" onclick="openDeleteTableModal()">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal('groups')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00897B,#26A69A);" onclick="utemFocusSearch('groups')">&#x1F50D; &#x628;&#x62D;&#x62B;</button><button id="bulkDelBtn_groups" class="btn-bulk-del" onclick="_bulkDelete('groupsBody2',function(id){return '/api/groups/'+id;},loadGroups2,'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;&#x61F;')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#c0392b,#e74c3c);" onclick="cleanupEmptyGroups()">&#x1F9F9; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x635;&#x641;&#x648;&#x641; &#x627;&#x644;&#x641;&#x627;&#x631;&#x63A;&#x629;</button></div>
  <div class="search-bar">
    <input type="text" id="groupSearchInput" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x623;&#x648; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;..." oninput="filterGroupTable2()">
    <button class="btn-search" style="background:#0097A7;" onclick="filterGroupTable2()">&#x628;&#x62D;&#x62B;</button>
  </div>
  <div class="table-wrap">
    <table style="min-width:1300px;">
      <thead>
        <tr id="groupsTheadRow" style="background:linear-gradient(135deg,#00BCD4,#0097A7);">
          <th class="bulk-col"><input type="checkbox" id="selectAll_groups" class="bulk-cb" onclick="_bulkSelectAll('groupsBody2','selectAll_groups','bulkDelBtn_groups',this.checked)"></th>
          <th>#</th><th>&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</th><th>&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;</th><th>&#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; / &#x627;&#x644;&#x645;&#x642;&#x631;&#x631;</th>
          <th>&#x627;&#x644;&#x645;&#x642;&#x631;&#x631; &#x627;&#x644;&#x630;&#x64A; &#x62A;&#x645; &#x627;&#x644;&#x648;&#x635;&#x648;&#x644; &#x627;&#x644;&#x64A;&#x647; &#x627;&#x644;&#x641;&#x635;&#x644; &#x627;&#x644;&#x641;&#x627;&#x626;&#x62A;</th><th>&#x648;&#x642;&#x62A; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;</th>
          <th>&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x634;&#x647;&#x631; &#x631;&#x645;&#x636;&#x627;&#x646;</th><th>&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646; (&#x627;&#x644;&#x639;&#x627;&#x62F;&#x64A;)</th>
          <th>&#x631;&#x627;&#x628;&#x637; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</th><th>&#x627;&#x644;&#x62D;&#x635;&#x629; &#x628;&#x627;&#x644;&#x62F;&#x642;&#x64A;&#x642;&#x629; (&#x64A;&#x62F;&#x648;&#x64A;)</th><th>&#x627;&#x62C;&#x631;&#x627;&#x621;&#x627;&#x62A;</th>
        </tr>
      </thead>
      <tbody id="groupsBody2">
        <tr><td colspan="12" class="no-data">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x60C; &#x627;&#x636;&#x641; &#x627;&#x648;&#x644; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</td></tr>
      </tbody>
    </table>
  </div>
</div>
<!-- TAQSEET (PAYMENT PLANS) TABLE -->
<div class="db-section" id="sec-taqseet">
  <div class="db-section-title" style="color:#6c3fa0;">&#128203; &#x637;&#x631;&#x64A;&#x642;&#x629; &#x627;&#x644;&#x62A;&#x642;&#x633;&#x64A;&#x637;</div>
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
    <span id="taqseetCount" style="background:#6c3fa0;color:#fff;border-radius:12px;padding:2px 12px;font-size:0.9em;">0</span>
    <button onclick="openAddTaqseet()" style="padding:8px 16px;border-radius:8px;border:none;background:linear-gradient(135deg,#1976D2,#42A5F5);color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#43; &#x625;&#x636;&#x627;&#x641;&#x629; &#x635;&#x641;</button>
    <button onclick="openGenericExcelModal('taqseet')" style="padding:8px 16px;border-radius:8px;border:none;background:linear-gradient(135deg,#43A047,#2E7D32);color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#128196; &#x625;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button><button onclick="openGenericExcelModal()" style="padding:8px 16px;border-radius:8px;border:none;background:linear-gradient(135deg,#3F51B5,#5C6BC0);color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#x1F4E5; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; Excel</button><button class="btn-delete-table" style="padding:8px 16px;font-size:13px;" onclick="openDeleteTableModal()">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
    <button onclick="openUniversalTableEditModal('taqseet')" style="padding:8px 16px;border-radius:8px;border:none;background:#9C27B0;color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
    <button onclick="openFreezeModal('taqseet')" style="padding:8px 16px;border-radius:8px;border:none;background:linear-gradient(135deg,#1565C0,#1E88E5);color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00897B,#26A69A);" onclick="utemFocusSearch('taqseet')">&#x1F50D; &#x628;&#x62D;&#x62B;</button>
    <button id="bulkDelBtn_taqseet" class="btn-bulk-del" style="padding:8px 16px;font-size:13px;" onclick="_bulkDelete('taqseetBody',function(id){return '/api/taqseet/'+id;},loadTaqseet,'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x635;&#x641;&#x61F;')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button>
  </div>
  <div id="taqseetWrap" style="overflow-x:auto;border-radius:12px;box-shadow:0 2px 12px #6c3fa022;">
    <table id="taqseetTable" style="width:100%;border-collapse:collapse;background:#fff;font-size:13px;">
      <thead>
        <tr style="background:linear-gradient(135deg,#6c3fa0,#9b59b6);color:#fff;">
          <th class="bulk-col" style="padding:10px 8px;"><input type="checkbox" id="selectAll_taqseet" class="bulk-cb" onclick="_bulkSelectAll('taqseetBody','selectAll_taqseet','bulkDelBtn_taqseet',this.checked)"></th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:50px;">#</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:120px;">&#x637;&#x631;&#x64A;&#x642;&#x629; &#x627;&#x644;&#x62A;&#x642;&#x633;&#x64A;&#x637;</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:130px;">&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:100px;">&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x62F;&#x648;&#x631;&#x629;</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:80px;">&#x639;&#x62F;&#x62F; &#x627;&#x644;&#x623;&#x642;&#x633;&#x627;&#x637;</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 1</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 1</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 1</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 2</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 2</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 2</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 3</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 3</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 3</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 4</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 4</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 4</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 5</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 5</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 5</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 6</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 6</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 6</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 7</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 7</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 7</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 8</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 8</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 8</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 9</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 9</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 9</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 10</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 10</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 10</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 11</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 11</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 11</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:90px;">&#x627;&#x644;&#x642;&#x633;&#x637; 12</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639; 12</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x62D;&#x642;&#x627;&#x642; 12</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:100px;">&#x639;&#x62F;&#x62F; &#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:110px;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x628;&#x62F;&#x621; &#x627;&#x644;&#x62F;&#x648;&#x631;&#x629;</th>
          <th style="padding:10px 8px;white-space:nowrap;min-width:80px;">&#x625;&#x62C;&#x631;&#x627;&#x621;&#x627;&#x62A;</th>
        </tr>
      </thead>
      <tbody id="taqseetBody"></tbody>
    </table>
  </div>
</div>
<div class="db-section" id="sec-attendance">
  <div class="db-section-title" style="color:#6c3fa0;">&#128197; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</div>
  <div class="stats" style="margin-bottom:10px;">
    <div class="stat-card">
      <span class="stat-num" id="attendanceTotalCount">0</span>
      <span class="stat-label">&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x633;&#x62C;&#x644;&#x627;&#x62A;</span>
    </div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
  <button class="btn-add" style="background:linear-gradient(135deg,#6c3fa0,#9b59b6);" onclick="openAttendanceAddModal()">+ &#x625;&#x636;&#x627;&#x641;&#x629; &#x633;&#x62C;&#x644;</button><button class="btn-add" style="background:linear-gradient(135deg,#388E3C,#66BB6A);" onclick="openAttendanceExcelModal()">&#128196; &#x625;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button>
  <button class="btn-add" style="background:linear-gradient(135deg,#E65100,#FFA726);" onclick="openUniversalTableEditModal('attendance')">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
  <button class="btn-add" style="background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal('attendance')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00897B,#26A69A);" onclick="utemFocusSearch('attendance')">&#x1F50D; &#x628;&#x62D;&#x62B;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#3F51B5,#5C6BC0);" onclick="openGenericExcelModal()">&#x1F4E5; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; Excel</button><button class="btn-delete-table" onclick="openDeleteTableModal()">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
  <button id="bulkDelBtn_attendance" class="btn-bulk-del" onclick="_bulkDelete('attendanceBody',function(id){return '/api/attendance/'+id;},loadAttendance,'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x633;&#x62C;&#x644;&#x61F;')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button></div>
  <div class="search-bar">
    <input type="text" id="attendanceSearchInput" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x641;&#x64A; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;..." oninput="filterAttendanceTable()">
    <button class="btn-search" onclick="filterAttendanceTable()">&#x628;&#x62D;&#x62B;</button>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th class="bulk-col"><input type="checkbox" id="selectAll_attendance" class="bulk-cb" onclick="_bulkSelectAll('attendanceBody','selectAll_attendance','bulkDelBtn_attendance',this.checked)"></th>
          <th>#</th>
          <th>&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x623;&#x62E;&#x630; &#x627;&#x644;&#x62D;&#x636;&#x648;&#x631;</th>
          <th>&#x627;&#x644;&#x64A;&#x648;&#x645;</th>
          <th>&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</th>
          <th>&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;</th>
          <th>&#x631;&#x642;&#x645; &#x627;&#x644;&#x62A;&#x648;&#x627;&#x635;&#x644;</th>
          <th>&#x627;&#x644;&#x62D;&#x627;&#x644;&#x629;</th>
          <th>&#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</th>
          <th>&#x62D;&#x627;&#x644;&#x629; &#x625;&#x631;&#x633;&#x627;&#x644; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</th>
          <th>&#x62D;&#x627;&#x644;&#x629; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;</th>
          <th>&#x625;&#x62C;&#x631;&#x627;&#x621;&#x627;&#x62A;</th>
        </tr>
      </thead>
      <tbody id="attendanceBody"></tbody>
    </table>
  </div>
</div>
<!-- ===== EVALUATIONS TABLE SECTION ===== -->
<div class="db-section" id="sec-evals">
  <div class="db-section-title" style="color:#1565C0;">&#x1F4DD; &#x627;&#x644;&#x62A;&#x642;&#x64A;&#x64A;&#x645;&#x627;&#x62A;</div>
  <div class="stats">
    <div class="stat-card" style="border-top:3px solid #1976D2;">
      <span class="stat-num" id="evalsTotalCount" style="color:#1976D2;">0</span>
      <span class="stat-label">&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x633;&#x62C;&#x644;&#x627;&#x62A;</span>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:20px;flex-wrap:wrap;">
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1976D2,#42A5F5);" onclick="openAddEvalModal()">+ &#x625;&#x636;&#x627;&#x641;&#x629; &#x633;&#x62C;&#x644;</button>
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#43A047,#2E7D32);" onclick="openGenericExcelModal('evaluations')">&#128196; &#x625;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button>
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openUniversalTableEditModal('evaluations')">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal('evals')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00897B,#26A69A);" onclick="utemFocusSearch('evals')">&#x1F50D; &#x628;&#x62D;&#x62B;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#3F51B5,#5C6BC0);" onclick="openGenericExcelModal()">&#x1F4E5; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; Excel</button><button class="btn-delete-table" onclick="openDeleteTableModal()">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
    <button id="bulkDelBtn_evals" class="btn-bulk-del" onclick="_bulkDelete('evalsBody',function(id){return '/api/evaluations/'+id;},loadEvaluations,'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x633;&#x62C;&#x644;&#x61F;')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button>
  </div>
  <div class="search-bar">
    <input type="text" id="evalsSearchInput" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x623;&#x648; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;..." oninput="filterEvalsTable()">
    <button class="btn-search" style="background:#1976D2;" onclick="filterEvalsTable()">&#x628;&#x62D;&#x62B;</button>
  </div>
  <div class="table-wrap">
    <table style="min-width:1400px;">
      <thead>
        <tr id="evalsTheadRow" style="background:linear-gradient(135deg,#1565C0,#1976D2);">
          <th class="bulk-col"><input type="checkbox" id="selectAll_evals" class="bulk-cb" onclick="_bulkSelectAll('evalsBody','selectAll_evals','bulkDelBtn_evals',this.checked)"></th>
          <th>#</th>
          <th>&#x625;&#x62C;&#x631;&#x627;&#x621;&#x627;&#x62A;</th>
        </tr>
      </thead>
      <tbody id="evalsBody">
        <tr><td colspan="3" class="no-data">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x62A;&#x642;&#x64A;&#x64A;&#x645;&#x627;&#x62A;</td></tr>
      </tbody>
    </table>
  </div>
</div>
<!-- ===== PAYMENT LOG TABLE SECTION ===== -->
<div class="db-section" id="sec-paylog">
  <div class="db-section-title" style="color:#00695C;">&#x1F4B0; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x641;&#x639;</div>
  <div class="stats">
    <div class="stat-card" style="border-top:3px solid #00897B;">
      <span class="stat-num" id="paylogTotalCount" style="color:#00897B;">0</span>
      <span class="stat-label">&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x633;&#x62C;&#x644;&#x627;&#x62A;</span>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:20px;flex-wrap:wrap;">
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00897B,#26A69A);" onclick="openAddPaylogModal()">+ &#x625;&#x636;&#x627;&#x641;&#x629; &#x633;&#x62C;&#x644;</button>
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#43A047,#2E7D32);" onclick="openGenericExcelModal('payment_log')">&#128196; &#x625;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button>
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openUniversalTableEditModal('payment_log')">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal('paylog')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00897B,#26A69A);" onclick="utemFocusSearch('paylog')">&#x1F50D; &#x628;&#x62D;&#x62B;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#3F51B5,#5C6BC0);" onclick="openGenericExcelModal()">&#x1F4E5; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; Excel</button><button class="btn-delete-table" onclick="openDeleteTableModal()">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
    <button id="bulkDelBtn_paylog" class="btn-bulk-del" onclick="_bulkDelete('paylogBody',function(id){return '/api/payment-log/'+id;},loadPaymentLog,'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x633;&#x62C;&#x644;&#x61F;')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button>
  </div>
  <div class="search-bar">
    <input type="text" id="paylogSearchInput" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;..." oninput="filterPaylogTable()">
    <button class="btn-search" style="background:#00897B;" onclick="filterPaylogTable()">&#x628;&#x62D;&#x62B;</button>
  </div>
  <div class="table-wrap">
    <table style="min-width:1600px;">
      <thead>
        <tr id="paylogTheadRow" style="background:linear-gradient(135deg,#00695C,#00897B);">
          <th class="bulk-col"><input type="checkbox" id="selectAll_paylog" class="bulk-cb" onclick="_bulkSelectAll('paylogBody','selectAll_paylog','bulkDelBtn_paylog',this.checked)"></th>
          <th>#</th>
          <th>&#x625;&#x62C;&#x631;&#x627;&#x621;&#x627;&#x62A;</th>
        </tr>
      </thead>
      <tbody id="paylogBody">
        <tr><td colspan="3" class="no-data">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x633;&#x62C;&#x644;&#x627;&#x62A; &#x62F;&#x641;&#x639;</td></tr>
      </tbody>
    </table>
  </div>
</div>
</div>
<div class="modal-bg" id="modal">
  <div class="modal">
    <h2 id="modalTitle">&#x625;&#x636;&#x627;&#x641;&#x629; &#x637;&#x627;&#x644;&#x628; &#x62C;&#x62F;&#x64A;&#x62F;</h2>
    <input type="hidden" id="editId">
    <div class="form-grid">
<div class="field"><label>&#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A; *</label><input id="f_personal_id" placeholder="&#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A;"></div>
<div class="field"><label>&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; *</label><input id="f_student_name" placeholder="&#x627;&#x644;&#x627;&#x633;&#x645; &#x627;&#x644;&#x643;&#x627;&#x645;&#x644;"></div>
<div class="field"><label>&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x648;&#x627;&#x62A;&#x633;&#x627;&#x628; &#x627;&#x644;&#x645;&#x639;&#x62A;&#x645;&#x62F;</label><input id="f_whatsapp" placeholder="+973 XXXX XXXX" class="ltr"></div>
<div class="field"><label>&#x627;&#x644;&#x635;&#x641;</label><input id="f_class_name" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x635;&#x641; A"></div>
<div class="field"><label>&#x642;&#x62F;&#x64A;&#x645; &#x62C;&#x62F;&#x64A;&#x62F; 2026</label><input id="f_old_new_2026" placeholder="&#x642;&#x62F;&#x64A;&#x645; &#x623;&#x648; &#x62C;&#x62F;&#x64A;&#x62F;"></div>
<div class="field"><label>&#x62A;&#x633;&#x62C;&#x64A;&#x644; &#x627;&#x644;&#x641;&#x635;&#x644; &#x627;&#x644;&#x62B;&#x627;&#x646;&#x64A; 2026</label><input id="f_registration_term2_2026" placeholder="&#x646;&#x639;&#x645; / &#x644;&#x627;"></div>
<div class="field"><label>&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label><input id="f_group_name_student" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;"></div>
<div class="field"><label>&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; (&#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646;)</label><input id="f_group_online" placeholder="&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646;"></div>
<div class="field"><label>&#x627;&#x644;&#x646;&#x62A;&#x64A;&#x62C;&#x629; &#x627;&#x644;&#x646;&#x647;&#x627;&#x626;&#x64A;&#x629; (&#x62A;&#x62D;&#x62F;&#x64A;&#x62F; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 2026)</label><select id="f_final_result"><option value="">-- &#x627;&#x62E;&#x62A;&#x631; --</option><option>&#x646;&#x627;&#x62C;&#x62D;</option><option>&#x631;&#x627;&#x633;&#x628;</option><option>&#x642;&#x64A;&#x62F; &#x627;&#x644;&#x62A;&#x642;&#x64A;&#x64A;&#x645;</option><option>&#x63A;&#x627;&#x626;&#x628;</option></select></div>
<div class="field"><label>&#x627;&#x644;&#x649; &#x627;&#x64A;&#x646; &#x648;&#x635;&#x644; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; 2026</label><input id="f_level_reached" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x627;&#x644;&#x648;&#x62D;&#x62F;&#x629; 5"></div>
<div class="field"><label>&#x647;&#x644; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x645;&#x646;&#x627;&#x633;&#x628; &#x644;&#x647;&#x630;&#x627; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 2026&#x61F;</label><input id="f_suitable_level" placeholder="&#x646;&#x639;&#x645; / &#x644;&#x627;"></div>
<div class="field"><label>&#x627;&#x633;&#x62A;&#x644;&#x627;&#x645; &#x627;&#x644;&#x643;&#x62A;&#x628;</label><input id="f_books_received" placeholder="&#x646;&#x639;&#x645; / &#x644;&#x627;"></div>
<div class="field"><label>&#x627;&#x644;&#x645;&#x62F;&#x631;&#x633; 2026</label><input id="f_teacher" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;"></div>
<div class="field"><label>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x627;&#x648;&#x644; 2026</label><input id="f_installment1" placeholder="&#x645;&#x62F;&#x641;&#x648;&#x639; / &#x63A;&#x64A;&#x631; &#x645;&#x62F;&#x641;&#x648;&#x639;"></div>
<div class="field"><label>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62B;&#x627;&#x646;&#x64A;</label><input id="f_installment2" placeholder="&#x645;&#x62F;&#x641;&#x648;&#x639; / &#x63A;&#x64A;&#x631; &#x645;&#x62F;&#x641;&#x648;&#x639;"></div>
<div class="field"><label>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62B;&#x627;&#x644;&#x62B;</label><input id="f_installment3" placeholder="&#x645;&#x62F;&#x641;&#x648;&#x639; / &#x63A;&#x64A;&#x631; &#x645;&#x62F;&#x641;&#x648;&#x639;"></div>
<div class="field"><label>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x631;&#x627;&#x628;&#x639;</label><input id="f_installment4" placeholder="&#x645;&#x62F;&#x641;&#x648;&#x639; / &#x63A;&#x64A;&#x631; &#x645;&#x62F;&#x641;&#x648;&#x639;"></div>
<div class="field"><label>&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62E;&#x627;&#x645;&#x633;</label><input id="f_installment5" placeholder="&#x645;&#x62F;&#x641;&#x648;&#x639; / &#x63A;&#x64A;&#x631; &#x645;&#x62F;&#x641;&#x648;&#x639;"></div>
<div class="field"><label>&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x645;</label><input id="f_mother_phone" placeholder="+973 XXXX XXXX" class="ltr"></div>
<div class="field"><label>&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x628;</label><input id="f_father_phone" placeholder="+973 XXXX XXXX" class="ltr"></div>
<div class="field"><label>&#x647;&#x627;&#x62A;&#x641; &#x627;&#x62E;&#x631;</label><input id="f_other_phone" placeholder="+973 XXXX XXXX" class="ltr"></div>
<div class="field"><label>&#x645;&#x643;&#x627;&#x646; &#x627;&#x644;&#x633;&#x643;&#x646;</label><input id="f_residence" placeholder="&#x627;&#x644;&#x645;&#x646;&#x637;&#x642;&#x629;"></div>
<div class="field full"><label>&#x639;&#x646;&#x648;&#x627;&#x646; &#x627;&#x644;&#x645;&#x646;&#x632;&#x644;</label><input id="f_home_address" placeholder="&#x639;&#x646;&#x648;&#x627;&#x646; &#x627;&#x644;&#x645;&#x646;&#x632;&#x644;"></div>
<div class="field"><label>&#x627;&#x644;&#x637;&#x631;&#x64A;&#x642;</label><input id="f_road" placeholder="&#x631;&#x642;&#x645; &#x627;&#x644;&#x637;&#x631;&#x64A;&#x642;"></div>
<div class="field"><label>&#x627;&#x644;&#x645;&#x62C;&#x645;&#x639;</label><input id="f_complex" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x639;"></div>
</div>
<div class="field"><label>&#x627;&#x62E;&#x62A;&#x64A;&#x627;&#x631; &#x646;&#x648;&#x639; &#x627;&#x644;&#x62A;&#x642;&#x633;&#x64A;&#x637;</label><select id="f_installment_type" class="installment-select-edit" onchange="updateEditInstallmentDetail(this.value)"><option value="">-- &#x627;&#x62E;&#x62A;&#x631; --</option></select><small id="edit_installment_detail" style="display:block;color:#555;margin-top:4px;font-size:12px;direction:rtl"></small></div>
</div>
    <div class="modal-actions">
      <button class="btn-save" onclick="saveStudent()">&#x62D;&#x641;&#x638;</button>
      <button class="btn-cancel" onclick="closeModal()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<div class="confirm-bg" id="confirmModal">
  <div class="confirm-box">
    <h3>&#x62A;&#x627;&#x643;&#x64A;&#x62F; &#x627;&#x644;&#x62D;&#x630;&#x641;</h3>
    <p>&#x647;&#x644; &#x627;&#x646;&#x62A; &#x645;&#x62A;&#x627;&#x643;&#x62F; &#x627;&#x646;&#x643; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; &#x647;&#x630;&#x627; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;&#x61F; &#x644;&#x627; &#x64A;&#x645;&#x643;&#x646; &#x627;&#x644;&#x62A;&#x631;&#x627;&#x62C;&#x639; &#x639;&#x646; &#x647;&#x630;&#x627; &#x627;&#x644;&#x627;&#x62C;&#x631;&#x627;&#x621;.</p>
    <div class="confirm-actions">
      <button class="btn-confirm-del" id="confirmDelBtn">&#x62D;&#x630;&#x641;</button>
      <button class="btn-confirm-cancel" onclick="closeConfirm()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div></div><!-- TABLE EDIT MODAL -->
<div class="modal-bg" id="tableEditModal">
<div class="modal" style="border-top:4px solid #FF6B35;max-width:560px;">
<h2 style="color:#E55A2B;">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</h2>
<div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:2px solid #f0ebff;padding-bottom:10px;">
<button id="tab-add-col" onclick="switchTab('add-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#FF6B35;color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#x2795; &#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F;</button>
<button id="tab-del-col" onclick="switchTab('del-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#f0ebff;color:#6B3FA0;font-weight:700;cursor:pointer;font-size:13px;">&#x274C; &#x62D;&#x630;&#x641; &#x639;&#x645;&#x648;&#x62F;</button>
<button id="tab-edit-col" onclick="switchTab('edit-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#f0ebff;color:#6B3FA0;font-weight:700;cursor:pointer;font-size:13px;">&#9998; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x639;&#x646;&#x648;&#x627;&#x646;</button>
</div>
<!-- Tab: Add Column -->
<div id="panel-add-col">
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">&#x639;&#x646;&#x648;&#x627;&#x646; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F; *</label><input id="new_col_label" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x645;&#x644;&#x627;&#x62D;&#x638;&#x627;&#x62A;" style="width:100%;padding:10px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;"></div>
<div class="field" style="margin-bottom:14px;">
  <label style="color:#E55A2B;">&#x645;&#x648;&#x642;&#x639; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F;</label>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
    <select id="new_col_position" onchange="togglePositionCol()" style="padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:0 0 auto;">
      <option value="end">&#x641;&#x64A; &#x627;&#x644;&#x646;&#x647;&#x627;&#x64A;&#x629;</option>
      <option value="start">&#x641;&#x64A; &#x627;&#x644;&#x628;&#x62F;&#x627;&#x64A;&#x629;</option>
      <option value="after">&#x628;&#x639;&#x62F; &#x639;&#x645;&#x648;&#x62F;:</option>
    </select>
    <select id="new_col_after" style="display:none;padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:1;">
      <option value="">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x2014;</option>
    </select>
  </div>
</div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="addColumn()">&#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F;</button>
</div>
</div>
<!-- Tab: Delete Column -->
<div id="panel-del-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#e53935;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x644;&#x644;&#x62D;&#x630;&#x641; *</label>
<select id="del_col_key" style="width:100%;padding:10px;border:1.5px solid #fce4ec;border-radius:9px;font-size:14px;background:#fff9f9;"><option value="">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F; &#x2014;</option></select></div>
<div style="background:#fff3f3;border-radius:8px;padding:10px;font-size:12px;color:#c62828;margin-bottom:12px;">&#x26A0;&#xFE0F; &#x62A;&#x62D;&#x630;&#x64A;&#x631;: &#x62D;&#x630;&#x641; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x64A;&#x62D;&#x630;&#x641; &#x62C;&#x645;&#x64A;&#x639; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x647; &#x645;&#x646; &#x643;&#x644; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629;. &#x644;&#x627; &#x64A;&#x645;&#x643;&#x646; &#x627;&#x644;&#x62A;&#x631;&#x627;&#x62C;&#x639;.</div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:#e53935;" onclick="deleteColumn()">&#x62D;&#x630;&#x641; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;</button>
</div>
</div>
<!-- Tab: Edit Column Label -->
<div id="panel-edit-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#6B3FA0;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; *</label>
<select id="edit_col_key" onchange="fillEditLabel()" style="width:100%;padding:10px;border:1.5px solid #E0D5F0;border-radius:9px;font-size:14px;background:#faf7ff;"><option value="">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F; &#x2014;</option></select></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#6B3FA0;">&#x627;&#x644;&#x627;&#x633;&#x645; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F; *</label><input id="edit_col_label" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;" style="width:100%;padding:10px;border:1.5px solid #E0D5F0;border-radius:9px;font-size:14px;background:#faf7ff;"></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" onclick="updateColumnLabel()">&#x62D;&#x641;&#x638; &#x627;&#x644;&#x639;&#x646;&#x648;&#x627;&#x646;</button>
</div>
</div>
<div class="modal-actions" style="margin-top:18px;justify-content:center;">
<button class="btn-cancel" onclick="closeTableEditModal()">&#x625;&#x63A;&#x644;&#x627;&#x642;</button>
</div>
</div>
</div>
<!-- STUDENT EXCEL IMPORT MODAL --><div class="modal-bg" id="studentExcelModal"><div class="modal" style="border-top:4px solid #43A047;max-width:500px;"><h2 style="color:#2E7D32;">&#128196; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; &#x637;&#x644;&#x628;&#x629; &#x645;&#x646; Excel</h2><div style="margin-bottom:16px;background:#f1f8e9;border-radius:10px;padding:14px;font-size:13px;color:#33691e;direction:rtl;"><b>&#x62A;&#x639;&#x644;&#x64A;&#x645;&#x627;&#x62A;:</b> &#x64A;&#x62C;&#x628; &#x623;&#x646; &#x64A;&#x643;&#x648;&#x646; &#x645;&#x644;&#x641; Excel &#x64A;&#x62D;&#x62A;&#x648;&#x64A; &#x639;&#x644;&#x649; &#x627;&#x644;&#x623;&#x639;&#x645;&#x62F;&#x629; &#x628;&#x647;&#x630;&#x627; &#x627;&#x644;&#x62A;&#x631;&#x62A;&#x64A;&#x628;:<br>&#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A;&#x60C; &#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;&#x60C; &#x627;&#x644;&#x648;&#x627;&#x62A;&#x633;&#x627;&#x628;&#x60C; &#x627;&#x644;&#x646;&#x62A;&#x64A;&#x62C;&#x629;&#x60C; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 2026&#x60C; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633; 2026&#x60C; &#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x645;&#x60C; &#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x628;&#x60C; &#x647;&#x627;&#x62A;&#x641; &#x627;&#x62E;&#x631;&#x60C; &#x627;&#x644;&#x633;&#x643;&#x646;&#x60C; &#x627;&#x644;&#x639;&#x646;&#x648;&#x627;&#x646;&#x60C; &#x627;&#x644;&#x637;&#x631;&#x64A;&#x642;&#x60C; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x639;</div><div style="text-align:center;margin:20px 0;"><input type="file" id="studentExcelFile" accept=".xlsx,.xls,.csv" style="display:none;"><button onclick="document.getElementById('studentExcelFile').click();" style="background:#43A047;color:#fff;border:none;padding:12px 28px;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;">&#128193; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x644;&#x641; Excel</button><div id="studentExcelFileName" style="margin-top:10px;font-size:13px;color:#666;">&#x644;&#x645; &#x64A;&#x62A;&#x645; &#x627;&#x62E;&#x62A;&#x64A;&#x627;&#x631; &#x645;&#x644;&#x641;</div></div><div id="studentExcelPreview" style="display:none;margin-bottom:14px;"><div style="font-size:13px;color:#2E7D32;font-weight:700;margin-bottom:6px;" id="studentExcelCount"></div></div><div class="modal-actions"><button class="btn-save" id="studentExcelImportBtn" style="background:linear-gradient(135deg,#43A047,#2E7D32);display:none;" onclick="importStudentsFromExcel()">&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;</button><button class="btn-cancel" onclick="closeStudentExcelModal()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button></div></div></div><!-- GROUP EXCEL IMPORT MODAL --><div class="modal-bg" id="groupExcelModal"><div class="modal" style="border-top:4px solid #43A047;max-width:500px;"><h2 style="color:#2E7D32;">&#128196; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A; &#x645;&#x646; Excel</h2><div style="margin-bottom:16px;background:#f1f8e9;border-radius:10px;padding:14px;font-size:13px;color:#33691e;direction:rtl;"><b>&#x62A;&#x639;&#x644;&#x64A;&#x645;&#x627;&#x62A;:</b> &#x64A;&#x62C;&#x628; &#x623;&#x646; &#x64A;&#x643;&#x648;&#x646; &#x645;&#x644;&#x641; Excel &#x64A;&#x62D;&#x62A;&#x648;&#x64A; &#x639;&#x644;&#x649; &#x627;&#x644;&#x623;&#x639;&#x645;&#x62F;&#x629; &#x628;&#x647;&#x630;&#x627; &#x627;&#x644;&#x62A;&#x631;&#x62A;&#x64A;&#x628;:<br>&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;&#x60C; &#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;&#x60C; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649;&#x60C; &#x627;&#x644;&#x645;&#x642;&#x631;&#x631; &#x627;&#x644;&#x641;&#x627;&#x626;&#x62A;&#x60C; &#x648;&#x642;&#x62A; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;&#x60C; &#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x631;&#x645;&#x636;&#x627;&#x646;&#x60C; &#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646;&#x60C; &#x631;&#x627;&#x628;&#x637; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;&#x60C; &#x627;&#x644;&#x62D;&#x635;&#x629; &#x628;&#x627;&#x644;&#x62F;&#x642;&#x64A;&#x642;&#x629;</div><div style="text-align:center;margin:20px 0;"><input type="file" id="groupExcelFile" accept=".xlsx,.xls,.csv" style="display:none;"><button onclick="document.getElementById('groupExcelFile').click();" style="background:#43A047;color:#fff;border:none;padding:12px 28px;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;">&#128193; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x644;&#x641; Excel</button><div id="groupExcelFileName" style="margin-top:10px;font-size:13px;color:#666;">&#x644;&#x645; &#x64A;&#x62A;&#x645; &#x627;&#x62E;&#x62A;&#x64A;&#x627;&#x631; &#x645;&#x644;&#x641;</div></div><div id="groupExcelPreview" style="display:none;margin-bottom:14px;"><div style="font-size:13px;color:#2E7D32;font-weight:700;margin-bottom:6px;" id="groupExcelCount"></div></div><div class="modal-actions"><button class="btn-save" id="groupExcelImportBtn" style="background:linear-gradient(135deg,#43A047,#2E7D32);display:none;" onclick="importGroupsFromExcel()">&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;</button><button class="btn-cancel" onclick="closeGroupExcelModal()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button></div></div></div>
<!-- ATTENDANCE ADD/EDIT MODAL -->
<div class="modal-bg" id="attendanceModal" style="display:none">
  <div class="modal" style="max-width:520px;width:95%">
    <h2 id="attendanceModalTitle" style="margin-bottom:16px;color:#6c3fa0;">&#x625;&#x636;&#x627;&#x641;&#x629; &#x633;&#x62C;&#x644; &#x63A;&#x64A;&#x627;&#x628;</h2>
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div style="display:flex;gap:10px;">
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x623;&#x62E;&#x630; &#x627;&#x644;&#x62D;&#x636;&#x648;&#x631;</label>
          <input type="date" id="att_date" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">&#x627;&#x644;&#x64A;&#x648;&#x645;</label>
          <input type="text" id="att_day" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x627;&#x644;&#x623;&#x62D;&#x62F;" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label>
          <input type="text" id="att_group" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;</label>
          <input type="text" id="att_student" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">&#x631;&#x642;&#x645; &#x627;&#x644;&#x62A;&#x648;&#x627;&#x635;&#x644;</label>
          <input type="text" id="att_contact" placeholder="&#x631;&#x642;&#x645; &#x627;&#x644;&#x648;&#x627;&#x62A;&#x633;&#x627;&#x628;" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">&#x627;&#x644;&#x62D;&#x627;&#x644;&#x629;</label>
          <select id="att_status" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
            <option value="">-- &#x627;&#x62E;&#x62A;&#x631; --</option>
            <option>&#x62D;&#x627;&#x636;&#x631;</option>
            <option>&#x63A;&#x627;&#x626;&#x628;</option>
            <option>&#x645;&#x62A;&#x623;&#x62E;&#x631;</option>
            <option>&#x645;&#x639;&#x62A;&#x630;&#x631;</option>
          </select>
        </div>
      </div>
      <div>
        <label style="font-size:.85em;color:#555;">&#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</label>
        <textarea id="att_message" rows="3" placeholder="&#x646;&#x635; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;resize:vertical;"></textarea>
      </div>
      <div style="display:flex;gap:10px;">
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">&#x62D;&#x627;&#x644;&#x629; &#x625;&#x631;&#x633;&#x627;&#x644; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</label>
          <select id="att_msg_status" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
            <option value="">-- &#x627;&#x62E;&#x62A;&#x631; --</option>
            <option>&#x62A;&#x645; &#x627;&#x644;&#x625;&#x631;&#x633;&#x627;&#x644;</option>
            <option>&#x644;&#x645; &#x64A;&#x64F;&#x631;&#x633;&#x644;</option>
            <option>&#x641;&#x634;&#x644; &#x627;&#x644;&#x625;&#x631;&#x633;&#x627;&#x644;</option>
          </select>
        </div>
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">&#x62D;&#x627;&#x644;&#x629; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;</label>
          <select id="att_study_status" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
            <option value="">-- &#x627;&#x62E;&#x62A;&#x631; --</option>
            <option>&#x645;&#x633;&#x62A;&#x645;&#x631;</option>
            <option>&#x645;&#x646;&#x642;&#x637;&#x639;</option>
            <option>&#x645;&#x648;&#x642;&#x648;&#x641;</option>
          </select>
        </div>
      </div>
    </div>
    <div style="display:flex;gap:10px;margin-top:16px;justify-content:flex-end;">
      <button class="btn-cancel" onclick="closeAttendanceModal()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
      <button class="btn-save" onclick="saveAttendanceRecord()">&#x62D;&#x641;&#x638;</button>
    </div>
  </div>
</div>
<!-- ATTENDANCE CONFIRM DELETE MODAL -->
<div class="confirm-bg" id="attendanceConfirmModal" style="display:none">
  <div class="confirm-box">
    <p>&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; &#x647;&#x630;&#x627; &#x627;&#x644;&#x633;&#x62C;&#x644;&#x61F;</p>
    <div style="display:flex;gap:10px;justify-content:center;">
      <button class="btn-cancel" onclick="closeAttendanceConfirm()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
      <button class="btn-delete" onclick="confirmAttendanceDelete()">&#x62D;&#x630;&#x641;</button>
    </div>
  </div>
</div>
<!-- GENERIC EXCEL IMPORT MODAL -->
<div class="modal-bg" id="genExcelModal">
  <div class="modal" style="border-top:4px solid #3F51B5;max-width:520px;">
    <h2 style="color:#3F51B5;">&#x1F4E5; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; Excel</h2>
    <div style="margin-bottom:14px;">
      <label style="display:block;font-size:13px;color:#3F51B5;font-weight:600;margin-bottom:6px;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</label>
      <select id="genExcelTable" onchange="onGenExcelTableChange()" style="width:100%;padding:10px;border:1.5px solid #C5CAE9;border-radius:9px;font-size:14px;background:#fafafa;">
        <option value="">&mdash; &#x627;&#x62E;&#x62A;&#x631; &mdash;</option>
        <option value="students">&#x642;&#x627;&#x639;&#x62F;&#x629; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</option>
        <option value="student_groups">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</option>
        <option value="attendance">&#x633;&#x62C;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</option>
        <option value="taqseet">&#x62C;&#x62F;&#x648;&#x644; &#x627;&#x644;&#x62A;&#x642;&#x633;&#x64A;&#x637;</option>
        <option value="evaluations">&#x627;&#x644;&#x62A;&#x642;&#x64A;&#x64A;&#x645;&#x627;&#x62A;</option>
        <option value="payment_log">&#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x641;&#x639;</option>
      </select>
    </div>
    <div id="genExcelFileRow" style="display:none;text-align:center;margin:14px 0;">
      <input type="file" id="genExcelFileInput" accept=".xlsx,.xls,.csv" style="display:none;" onchange="readGenericExcelFile(this)">
      <button onclick="document.getElementById('genExcelFileInput').click();" style="background:#3F51B5;color:#fff;border:none;padding:12px 28px;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;">&#x1F4C1; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x644;&#x641; Excel</button>
    </div>
    <div id="genExcelStatus" style="margin-top:10px;font-size:13px;color:#555;text-align:center;min-height:18px;"></div>
    <div class="modal-actions">
      <button class="btn-save" id="genExcelImportBtn" style="background:linear-gradient(135deg,#3F51B5,#5C6BC0);display:none;" onclick="importGenericFromExcel()">&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;</button>
      <button class="btn-cancel" onclick="closeGenericExcelModal()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<!-- ATTENDANCE EXCEL IMPORT MODAL -->
<div class="modal-bg" id="attendanceExcelModal" style="display:none">
  <div class="modal" style="max-width:480px;width:95%">
    <h2 style="margin-bottom:14px;color:#388E3C;">&#128196; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; &#x633;&#x62C;&#x644; &#x63A;&#x64A;&#x627;&#x628; &#x645;&#x646; Excel</h2>
    <div style="background:#f1f8e9;border-radius:8px;padding:12px;margin-bottom:14px;font-size:.88em;color:#2E7D32;line-height:1.7;">
      <b>&#x62A;&#x639;&#x644;&#x64A;&#x645;&#x627;&#x62A;:</b> &#x64A;&#x62C;&#x628; &#x623;&#x646; &#x64A;&#x62D;&#x62A;&#x648;&#x64A; &#x645;&#x644;&#x641; Excel &#x639;&#x644;&#x649; &#x627;&#x644;&#x623;&#x639;&#x645;&#x62F;&#x629; &#x628;&#x647;&#x630;&#x627; &#x627;&#x644;&#x62A;&#x631;&#x62A;&#x64A;&#x628;:<br>
      &#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x623;&#x62E;&#x630; &#x627;&#x644;&#x62D;&#x636;&#x648;&#x631;&#x60C; &#x627;&#x644;&#x64A;&#x648;&#x645;&#x60C; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;&#x60C; &#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;&#x60C; &#x631;&#x642;&#x645; &#x627;&#x644;&#x62A;&#x648;&#x627;&#x635;&#x644;&#x60C; &#x627;&#x644;&#x62D;&#x627;&#x644;&#x629;&#x60C; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;&#x60C; &#x62D;&#x627;&#x644;&#x629; &#x625;&#x631;&#x633;&#x627;&#x644; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;&#x60C; &#x62D;&#x627;&#x644;&#x629; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;
    </div>
    <button class="btn-add" style="width:100%;justify-content:center;" onclick="document.getElementById('attendanceExcelFileInput').click()">&#128194; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x644;&#x641; Excel</button>
    <input type="file" id="attendanceExcelFileInput" accept=".xlsx,.xls,.csv" style="display:none" onchange="readAttendanceExcelFile(this)">
    <div id="attendanceExcelStatus" style="margin-top:10px;font-size:.9em;color:#555;text-align:center;"></div>
    <div style="display:flex;gap:10px;margin-top:14px;justify-content:flex-end;">
      <button class="btn-cancel" onclick="closeAttendanceExcelModal()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
      <button class="btn-save" id="attendanceExcelImportBtn" onclick="importAttendanceFromExcel()" style="display:none">&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;</button>
    </div>
  </div>
</div>

<!-- ATTENDANCE TABLE EDIT MODAL -->
<div class="modal-bg" id="attendanceTableEditModal" style="display:none">
  <div class="modal" style="max-width:460px;width:95%">
    <h2 style="margin-bottom:12px;color:#E65100;font-size:1.1em;">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x62C;&#x62F;&#x648;&#x644; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</h2>
    <div style="display:flex;gap:6px;margin-bottom:14px;">
      <button class="btn-tab active" id="attTab1" onclick="switchAttTab('add')">&#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F;</button>
      <button class="btn-tab" id="attTab2" onclick="switchAttTab('del')">&#x62D;&#x630;&#x641; &#x639;&#x645;&#x648;&#x62F;</button>
      <button class="btn-tab" id="attTab3" onclick="switchAttTab('rename')">&#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x639;&#x646;&#x648;&#x627;&#x646;</button>
    </div>
    <!-- Add column panel -->
    <div id="attTabPanelAdd">
      <label style="font-size:.85em;color:#555;display:block;margin-bottom:4px;">&#x627;&#x633;&#x645; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F;</label>
      <input type="text" id="att_new_col_name" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;" class="col-name-input">
      <div style="margin:8px 0 4px 0;font-size:.85em;color:#555;">&#x645;&#x643;&#x627;&#x646; &#x627;&#x644;&#x625;&#x636;&#x627;&#x641;&#x629;:</div>
      <select id="att_col_position" class="col-name-input" onchange="toggleAttPosition()">
        <option value="end">&#x641;&#x64A; &#x627;&#x644;&#x646;&#x647;&#x627;&#x64A;&#x629;</option>
        <option value="start">&#x641;&#x64A; &#x627;&#x644;&#x628;&#x62F;&#x627;&#x64A;&#x629;</option>
        <option value="after">&#x628;&#x639;&#x62F; &#x639;&#x645;&#x648;&#x62F;:</option>
      </select>
      <select id="att_after_col" class="col-name-input" style="display:none;margin-top:6px;"></select>
      <button class="btn-save" style="margin-top:10px;width:100%;" onclick="addAttendanceColumn()">&#x625;&#x636;&#x627;&#x641;&#x629;</button>
    </div>
    <!-- Delete column panel -->
    <div id="attTabPanelDel" style="display:none">
      <label style="font-size:.85em;color:#555;display:block;margin-bottom:4px;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x644;&#x644;&#x62D;&#x630;&#x641;</label>
      <select id="att_del_col" class="col-name-input"></select>
      <button style="margin-top:10px;width:100%;padding:10px;border:none;border-radius:8px;font-weight:700;cursor:pointer;background:#e53935;color:#fff;" onclick="deleteAttendanceColumn()">&#x62D;&#x630;&#x641; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;</button>
    </div>
    <!-- Rename column panel -->
    <div id="attTabPanelRename" style="display:none">
      <label style="font-size:.85em;color:#555;display:block;margin-bottom:4px;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;</label>
      <select id="att_rename_col" class="col-name-input" onchange="fillAttRenameLabel()"></select>
      <label style="font-size:.85em;color:#555;display:block;margin-top:8px;margin-bottom:4px;">&#x627;&#x644;&#x627;&#x633;&#x645; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F;</label>
      <input type="text" id="att_rename_label" class="col-name-input" placeholder="&#x627;&#x644;&#x627;&#x633;&#x645; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F;">
      <button class="btn-save" style="margin-top:10px;width:100%;" onclick="updateAttendanceColumnLabel()">&#x62D;&#x641;&#x638;</button>
    </div>
    <div style="margin-top:14px;text-align:left;">
      <button class="btn-cancel" onclick="closeAttendanceTableEditModal()">&#x625;&#x63A;&#x644;&#x627;&#x642;</button>
    </div>
  </div>
</div>

<!-- DYNAMIC CUSTOM TABLES CONTAINER -->
<div id="customTablesContainer"></div>

<!-- CUSTOM TABLE EDIT MODAL (add/delete/rename cols) -->
<div class="modal-bg" id="customTableEditModal" style="display:none">
  <div class="modal" style="max-width:480px;width:96%">
    <h2 id="customTableEditTitle" style="margin-bottom:12px;color:#1565C0;font-size:1.1em;">&#x2699; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</h2>
    <div style="display:flex;gap:6px;margin-bottom:14px;" id="customTblTabBtns">
      <button class="btn-tab active" id="ctab1" onclick="switchCustomTab('add')">&#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F;</button>
      <button class="btn-tab" id="ctab2" onclick="switchCustomTab('del')">&#x62D;&#x630;&#x641; &#x639;&#x645;&#x648;&#x62F;</button>
      <button class="btn-tab" id="ctab3" onclick="switchCustomTab('rename')">&#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x639;&#x646;&#x648;&#x627;&#x646;</button>
    </div>
    <div id="ctabPanelAdd">
      <input type="text" id="ctbl_new_col_name" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F;" class="col-name-input">
      <div style="margin:8px 0 4px 0;font-size:.85em;color:#555;">&#x645;&#x643;&#x627;&#x646; &#x627;&#x644;&#x625;&#x636;&#x627;&#x641;&#x629;:</div>
      <select id="ctbl_position" class="col-name-input" onchange="toggleCustomPosition()">
        <option value="end">&#x641;&#x64A; &#x627;&#x644;&#x646;&#x647;&#x627;&#x64A;&#x629;</option>
        <option value="start">&#x641;&#x64A; &#x627;&#x644;&#x628;&#x62F;&#x627;&#x64A;&#x629;</option>
        <option value="after">&#x628;&#x639;&#x62F; &#x639;&#x645;&#x648;&#x62F;:</option>
      </select>
      <select id="ctbl_after_col" class="col-name-input" style="display:none;margin-top:6px;"></select>
      <button class="btn-save" style="margin-top:10px;width:100%;" onclick="addCustomColumn()">&#x625;&#x636;&#x627;&#x641;&#x629;</button>
    </div>
    <div id="ctabPanelDel" style="display:none">
      <select id="ctbl_del_col" class="col-name-input"></select>
      <button class="btn-delete" style="margin-top:10px;width:100%;padding:10px;border:none;border-radius:8px;font-weight:700;cursor:pointer;background:#e53935;color:#fff;" onclick="deleteCustomColumn()">&#x62D;&#x630;&#x641; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;</button>
    </div>
    <div id="ctabPanelRename" style="display:none">
      <select id="ctbl_rename_col" class="col-name-input" onchange="fillCustomRenameLabel()"></select>
      <input type="text" id="ctbl_rename_label" placeholder="&#x627;&#x644;&#x627;&#x633;&#x645; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F;" class="col-name-input" style="margin-top:8px;">
      <button class="btn-save" style="margin-top:10px;width:100%;" onclick="updateCustomColumnLabel()">&#x62D;&#x641;&#x638; &#x627;&#x644;&#x62A;&#x639;&#x62F;&#x64A;&#x644;</button>
    </div>
    <div style="margin-top:14px;text-align:left;">
      <button class="btn-cancel" onclick="closeCustomTableEditModal()">&#x625;&#x63A;&#x644;&#x627;&#x642;</button>
    </div>
  </div>
</div>

<!-- ADD ROW MODAL FOR CUSTOM TABLE -->
<div class="modal-bg" id="customRowModal" style="display:none">
  <div class="modal" style="max-width:500px;width:96%">
    <h2 id="customRowModalTitle" style="margin-bottom:14px;color:#1565C0;font-size:1.1em;">&#x625;&#x636;&#x627;&#x641;&#x629; &#x635;&#x641;</h2>
    <div id="customRowFormFields" style="display:flex;flex-direction:column;gap:10px;"></div>
    <div style="display:flex;gap:10px;margin-top:16px;justify-content:flex-end;">
      <button class="btn-cancel" onclick="closeCustomRowModal()">&#x625;&#x644;&#x63A;&#x627;&#x621;</button>
      <button class="btn-save" onclick="saveCustomRow()">&#x62D;&#x641;&#x638;</button>
    </div>
  </div>
</div>

<!-- CONFIRM DELETE CUSTOM TABLE -->
<div class="confirm-bg" id="customTableDeleteConfirm" style="display:none">
  <div class="confirm-box">
    <p id="customTableDeleteMsg">&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; &#x647;&#x630;&#x627; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;&#x61F;</p>
    <div style="display:flex;gap:10px;justify-content:center;">
      <button class="btn-cancel" onclick="closeCustomTableDeleteConfirm()">&#x625;&#x644;&#x63A;&#x627;&#x621;</button>
      <button style="background:#e53935;color:#fff;border:none;padding:10px 22px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;" onclick="confirmCustomTableDelete()">&#x62D;&#x630;&#x641;</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<!-- SHARED FREEZE COLUMNS MODAL -->
<div class="modal-bg" id="freezeModal">
  <div class="modal" style="max-width:520px;border-top:4px solid #1565C0;">
    <h2 id="freezeModalTitle" style="color:#1565C0;">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F; &#x627;&#x644;&#x623;&#x639;&#x645;&#x62F;&#x629;</h2>
    <div style="background:#e3f2fd;border-radius:8px;padding:10px;font-size:13px;color:#0d47a1;margin-bottom:8px;direction:rtl;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x623;&#x639;&#x645;&#x62F;&#x629; &#x627;&#x644;&#x62A;&#x64A; &#x62A;&#x631;&#x64A;&#x62F; &#x62A;&#x62B;&#x628;&#x64A;&#x62A;&#x647;&#x627; &#x639;&#x644;&#x649; &#x627;&#x644;&#x64A;&#x645;&#x64A;&#x646; &#x639;&#x646;&#x62F; &#x627;&#x644;&#x62A;&#x645;&#x631;&#x64A;&#x631;.</div>
    <div id="freezeModalBody" class="freeze-modal-body" dir="rtl"></div>
    <div class="modal-actions">
      <button class="btn-save" style="background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="applyFreezeFromModal()">&#x62A;&#x637;&#x628;&#x64A;&#x642;</button>
      <button class="btn-cancel" onclick="closeFreezeModal()">&#x625;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<div class="modal-bg" id="groupModal2">
  <div class="modal" style="border-top:4px solid #00BCD4;">
    <h2 id="groupModalTitle2" style="color:#0097A7;">&#x625;&#x636;&#x627;&#x641;&#x629; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x62C;&#x62F;&#x64A;&#x62F;&#x629;</h2>
    <input type="hidden" id="groupEditId2">
    <div class="form-grid">
      <div class="field"><label style="color:#0097A7;">&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; *</label><input id="gf2_group_name" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;</label><input id="gf2_teacher_name" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; / &#x627;&#x644;&#x645;&#x642;&#x631;&#x631;</label><input id="gf2_level_course" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 3" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x627;&#x644;&#x645;&#x642;&#x631;&#x631; &#x627;&#x644;&#x630;&#x64A; &#x62A;&#x645; &#x627;&#x644;&#x648;&#x635;&#x648;&#x644; &#x627;&#x644;&#x64A;&#x647; &#x627;&#x644;&#x641;&#x635;&#x644; &#x627;&#x644;&#x641;&#x627;&#x626;&#x62A;</label><input id="gf2_last_reached" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x627;&#x644;&#x648;&#x62D;&#x62F;&#x629; 5" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x648;&#x642;&#x62A; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;</label><input id="gf2_study_time" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x627;&#x644;&#x633;&#x628;&#x62A; 4-5 &#x645;&#x633;&#x627;&#x621;" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x634;&#x647;&#x631; &#x631;&#x645;&#x636;&#x627;&#x646;</label><input id="gf2_ramadan_time" placeholder="&#x645;&#x62B;&#x627;&#x644;: 8-9 &#x645;&#x633;&#x627;&#x621;" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646; (&#x627;&#x644;&#x639;&#x627;&#x62F;&#x64A;)</label><input id="gf2_online_time" placeholder="&#x645;&#x62B;&#x627;&#x644;: 5-6 &#x645;&#x633;&#x627;&#x621;" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x631;&#x627;&#x628;&#x637; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label><input id="gf2_group_link" placeholder="https://..." class="ltr" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x627;&#x644;&#x62D;&#x635;&#x629; &#x628;&#x627;&#x644;&#x62F;&#x642;&#x64A;&#x642;&#x629; (&#x64A;&#x62F;&#x648;&#x64A;)</label><input id="gf2_session_duration" placeholder="&#x645;&#x62B;&#x627;&#x644;: 60 &#x62F;&#x642;&#x64A;&#x642;&#x629;" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x645;&#x62F;&#x629; &#x627;&#x644;&#x62D;&#x635;&#x629; &#x628;&#x627;&#x644;&#x62F;&#x642;&#x64A;&#x642;&#x629; &#x644;&#x644;&#x648;&#x642;&#x62A; &#x627;&#x644;&#x627;&#x639;&#x62A;&#x64A;&#x627;&#x62F;&#x64A; (&#x64A;&#x62F;&#x648;&#x64A;)</label><input id="gf2_session_minutes_normal" placeholder="&#x645;&#x62B;&#x627;&#x644;: 60" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x639;&#x62F;&#x62F; &#x627;&#x644;&#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x62D;&#x636;&#x648;&#x631;&#x64A;&#x629; (&#x62A;&#x644;&#x642;&#x627;&#x626;&#x64A;)</label><input id="gf2_hours_in_person_auto" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x639;&#x62F;&#x62F; &#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646; &#x641;&#x642;&#x637;</label><input id="gf2_hours_online_only" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x627;&#x644;&#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x64A;&#x629; &#x643;&#x644;&#x647;&#x627; &#x628;&#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646;</label><input id="gf2_hours_all_online" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x633;&#x627;&#x639;&#x627;&#x62A; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x62D;&#x642;&#x629;</label><input id="gf2_total_required_hours" placeholder="&#x645;&#x62B;&#x627;&#x644;: 40" style="border-color:#b2ebf2;background:#f0fdff;"></div>
    </div>
    <div class="modal-actions">
      <button class="btn-save" style="background:linear-gradient(135deg,#00BCD4,#0097A7);" onclick="saveGroup2()">&#x62D;&#x641;&#x638;</button>
      <button class="btn-cancel" style="background:#e0f7fa;color:#0097A7;" onclick="closeGroupModal2()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<div class="confirm-bg" id="groupConfirmModal2">
  <div class="confirm-box">
    <h3>&#x62A;&#x627;&#x643;&#x64A;&#x62F; &#x627;&#x644;&#x62D;&#x630;&#x641;</h3>
    <p>&#x647;&#x644; &#x627;&#x646;&#x62A; &#x645;&#x62A;&#x627;&#x643;&#x62F; &#x645;&#x646; &#x62D;&#x630;&#x641; &#x647;&#x630;&#x647; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;&#x61F;</p>
    <div class="confirm-actions">
      <button class="btn-confirm-del" id="groupConfirmDelBtn2">&#x62D;&#x630;&#x641;</button>
      <button class="btn-confirm-cancel" onclick="closeGroupConfirm2()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<!-- GROUP TABLE EDIT MODAL -->
<div class="modal-bg" id="groupTableEditModal">
<div class="modal" style="border-top:4px solid #FF6B35;max-width:560px;">
<h2 style="color:#E55A2B;">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x62C;&#x62F;&#x648;&#x644; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</h2>
<div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:2px solid #e0f7fa;padding-bottom:10px;">
<button id="gtab-add-col" onclick="switchGroupTab('add-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#FF6B35;color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#43; &#1573;&#1590;&#1575;&#1601;&#1577; &#1593;&#1605;&#1608;&#1583;</button>
<button id="gtab-del-col" onclick="switchGroupTab('del-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#e0f7fa;color:#0097A7;font-weight:700;cursor:pointer;font-size:13px;">&#10060; &#1581;&#1584;&#1601; &#1593;&#1605;&#1608;&#1583;</button>
<button id="gtab-edit-col" onclick="switchGroupTab('edit-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#e0f7fa;color:#0097A7;font-weight:700;cursor:pointer;font-size:13px;">&#9998; &#1578;&#1593;&#1583;&#1610;&#1604; &#1593;&#1606;&#1608;&#1575;&#1606;</button>
</div>
<div id="gpanel-add-col">
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">&#1593;&#1606;&#1608;&#1575;&#1606; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#1575;&#1604;&#1580;&#1583;&#1610;&#1583; *</label><input id="g_new_col_label" placeholder="&#1605;&#1579;&#1575;&#1604;: &#1605;&#1604;&#1575;&#1581;&#1592;&#1575;&#1578;" style="width:100%;padding:10px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;"></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">&#1605;&#1608;&#1602;&#1593; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#1575;&#1604;&#1580;&#1583;&#1610;&#1583;</label>
<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
<select id="g_new_col_position" onchange="toggleGroupPositionCol()" style="padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:0 0 auto;">
<option value="end">&#1601;&#1610; &#1575;&#1604;&#1606;&#1607;&#1575;&#1610;&#1577;</option>
<option value="start">&#1601;&#1610; &#1575;&#1604;&#1576;&#1583;&#1575;&#1610;&#1577;</option>
<option value="after">&#1576;&#1593;&#1583; &#1593;&#1605;&#1608;&#1583;:</option>
</select>
<select id="g_new_col_after" style="display:none;padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:1;"><option value="">&#8212; &#1575;&#1582;&#1578;&#1585; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#8212;</option></select>
</div></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="addGroupColumn()">&#1573;&#1590;&#1575;&#1601;&#1577; &#1593;&#1605;&#1608;&#1583;</button>
</div></div>
<div id="gpanel-del-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#e53935;">&#1575;&#1582;&#1578;&#1585; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#1604;&#1604;&#1581;&#1584;&#1601; *</label>
<select id="g_del_col_key" style="width:100%;padding:10px;border:1.5px solid #fce4ec;border-radius:9px;font-size:14px;background:#fff9f9;"><option value="">&#8212; &#1575;&#1582;&#1578;&#1585; &#1593;&#1605;&#1608;&#1583; &#8212;</option></select></div>
<div style="background:#fff3f3;border-radius:8px;padding:10px;font-size:12px;color:#c62828;margin-bottom:12px;">&#9888; &#1578;&#1581;&#1584;&#1610;&#1585;: &#1581;&#1584;&#1601; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#1610;&#1581;&#1584;&#1601; &#1580;&#1605;&#1610;&#1593; &#1576;&#1610;&#1575;&#1606;&#1575;&#1578;&#1607; &#1605;&#1606; &#1603;&#1604; &#1575;&#1604;&#1605;&#1580;&#1605;&#1608;&#1593;&#1575;&#1578;. &#1604;&#1575; &#1610;&#1605;&#1603;&#1606; &#1575;&#1604;&#1578;&#1585;&#1575;&#1580;&#1593;.</div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:#e53935;" onclick="deleteGroupColumn()">&#1581;&#1584;&#1601; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583;</button>
</div></div>
<div id="gpanel-edit-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#0097A7;">&#1575;&#1582;&#1578;&#1585; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; *</label>
<select id="g_edit_col_key" onchange="fillGroupEditLabel()" style="width:100%;padding:10px;border:1.5px solid #b2ebf2;border-radius:9px;font-size:14px;background:#f0fdff;"><option value="">&#8212; &#1575;&#1582;&#1578;&#1585; &#1593;&#1605;&#1608;&#1583; &#8212;</option></select></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#0097A7;">&#1575;&#1604;&#1575;&#1587;&#1605; &#1575;&#1604;&#1580;&#1583;&#1610;&#1583; *</label><input id="g_edit_col_label" placeholder="&#1575;&#1587;&#1605; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583;" style="width:100%;padding:10px;border:1.5px solid #b2ebf2;border-radius:9px;font-size:14px;background:#f0fdff;"></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#00BCD4,#0097A7);" onclick="updateGroupColumnLabel()">&#1581;&#1601;&#1592; &#1575;&#1604;&#1593;&#1606;&#1608;&#1575;&#1606;</button>
</div></div>
<div class="modal-actions" style="margin-top:18px;justify-content:center;">
<button class="btn-cancel" style="background:#e0f7fa;color:#0097A7;" onclick="closeGroupTableEditModal()">&#1573;&#1594;&#1604;&#1575;&#1602;</button>
</div>
</div>
</div>
<!-- PAYMENT LOG ADD/EDIT MODAL -->
<div class="modal-bg" id="paylogModal">
  <div class="modal" style="border-top:4px solid #00897B;max-width:720px;">
    <h2 id="paylogModalTitle" style="color:#00695C;">&#x1F4B0; &#x625;&#x636;&#x627;&#x641;&#x629; &#x633;&#x62C;&#x644; &#x62F;&#x641;&#x639;</h2>
    <input type="hidden" id="paylogEditId">
    <div class="form-grid">
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x627;&#x633;&#x645; *</label><input id="pl_student_name" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x62D;&#x627;&#x644;&#x629; &#x627;&#x644;&#x62A;&#x633;&#x62C;&#x64A;&#x644;</label><input id="pl_registration_status" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x62F;&#x648;&#x631;&#x629;</label><input id="pl_course_amount" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 1</label><input id="pl_inst1" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 1 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</label><input id="pl_msg1" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 2</label><input id="pl_inst2" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 2 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</label><input id="pl_msg2" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 3</label><input id="pl_inst3" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 3 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</label><input id="pl_msg3" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 4</label><input id="pl_inst4" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 4 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</label><input id="pl_msg4" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 5</label><input id="pl_inst5" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x642;&#x633;&#x637; 5 &#x644;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;</label><input id="pl_msg5" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639;</label><input id="pl_total_paid" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x645;&#x62A;&#x628;&#x642;&#x64A;</label><input id="pl_total_remaining" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x62D;&#x627;&#x644;&#x629; &#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639;&#x627;&#x62A;</label><input id="pl_payment_status" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
    </div>
    <div class="modal-actions">
      <button class="btn-save" style="background:linear-gradient(135deg,#00897B,#00695C);" onclick="savePaylog()">&#x62D;&#x641;&#x638;</button>
      <button class="btn-cancel" style="background:#e0f2f1;color:#00695C;" onclick="closePaylogModal()">&#x625;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<!-- UNIVERSAL TABLE EDIT MODAL -->
<style>
.utem-col-row{display:flex;align-items:center;gap:8px;padding:8px;border-bottom:1px solid #eee;}
.utem-col-row:last-child{border-bottom:none;}
.utem-col-label{flex:1;font-size:14px;color:#333;}
.utem-col-input{flex:1;padding:6px 10px;border:1.5px solid #90CAF9;border-radius:7px;font-size:14px;}
.utem-col-btn{background:none;border:1px solid #ddd;border-radius:7px;padding:5px 10px;cursor:pointer;font-size:14px;transition:all .15s;}
.utem-col-btn:hover{background:#f5f5f5;}
.utem-col-btn.ok{background:#43A047;color:#fff;border-color:#43A047;}
.utem-col-btn.cancel{background:#e0e0e0;}
.utem-col-btn.del{color:#e53935;}
.utem-col-btn.del:hover{background:#ffebee;}
.utem-cols-body{max-height:45vh;overflow-y:auto;border:1px solid #e8e8e8;border-radius:10px;padding:4px;background:#fafafa;margin:10px 0;}
</style>
<div class="modal-bg" id="universalTableEditModal">
  <div class="modal" style="max-width:680px;border-top:4px solid #1976D2;">
    <h2 id="utemTitle" style="color:#1565C0;">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</h2>
    <div class="field" style="margin-bottom:12px;">
      <label style="color:#1565C0;">&#x627;&#x633;&#x645; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</label>
      <input id="utemTableName" style="width:100%;padding:9px 12px;border:1.5px solid #bbdefb;border-radius:9px;background:#f0f7ff;" />
    </div>
    <div style="font-weight:700;color:#1565C0;margin-top:8px;">&#x627;&#x644;&#x623;&#x639;&#x645;&#x62F;&#x629;</div>
    <div id="utemColumnsBody" class="utem-cols-body"></div>
    <div class="field" style="margin-bottom:6px;padding-top:10px;border-top:1px solid #eee;">
      <label style="color:#FF6B35;font-weight:700;">&#x2795; &#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F; &#x62C;&#x62F;&#x64A;&#x62F;</label>
      <div style="display:flex;gap:8px;align-items:center;margin-top:6px;flex-wrap:wrap;">
        <input id="utemNewColLabel" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;" style="flex:1;min-width:160px;padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;background:#fff9f7;"/>
        <select id="utemNewColType" onchange="_utemToggleNewOptionsArea()" style="padding:9px 10px;border:1.5px solid #ffd4c2;border-radius:9px;background:#fff9f7;font-size:13px;"></select>
        <button class="btn-save" style="background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="utemAddColumn()">&#x625;&#x636;&#x627;&#x641;&#x629;</button>
      </div>
      <div id="utemNewOptsWrap" style="display:none;margin-top:8px;">
        <label style="color:#FF6B35;font-size:12px;">&#x62E;&#x64A;&#x627;&#x631;&#x627;&#x62A; &#x627;&#x644;&#x642;&#x627;&#x626;&#x645;&#x629; &#x627;&#x644;&#x645;&#x646;&#x633;&#x62F;&#x644;&#x629; (&#x645;&#x641;&#x635;&#x648;&#x644;&#x629; &#x628;&#x641;&#x627;&#x635;&#x644;&#x629;)</label>
        <textarea id="utemNewColOpts" rows="2" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x646;&#x639;&#x645;,&#x644;&#x627;,&#x631;&#x628;&#x645;&#x627;" style="width:100%;padding:8px 10px;border:1.5px solid #ffd4c2;border-radius:9px;background:#fff9f7;font-size:13px;"></textarea>
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn-save" style="background:linear-gradient(135deg,#1976D2,#1565C0);" onclick="utemSave()">&#x1F4BE; &#x62D;&#x641;&#x638;</button>
      <button class="btn-cancel" style="background:#e3f2fd;color:#1565C0;" onclick="utemClose()">&#x625;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<!-- PAYMENT LOG TABLE EDIT MODAL -->
<div class="modal-bg" id="paylogTableEditModal">
<div class="modal" style="border-top:4px solid #FF6B35;max-width:560px;">
<h2 style="color:#E55A2B;">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x62C;&#x62F;&#x648;&#x644; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x641;&#x639;</h2>
<div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:2px solid #e0f2f1;padding-bottom:10px;">
<button id="pltab-add-col" onclick="switchPaylogTab('add-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#FF6B35;color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#43; &#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F;</button>
<button id="pltab-del-col" onclick="switchPaylogTab('del-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#e0f2f1;color:#00695C;font-weight:700;cursor:pointer;font-size:13px;">&#10060; &#x62D;&#x630;&#x641; &#x639;&#x645;&#x648;&#x62F;</button>
<button id="pltab-edit-col" onclick="switchPaylogTab('edit-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#e0f2f1;color:#00695C;font-weight:700;cursor:pointer;font-size:13px;">&#9998; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x639;&#x646;&#x648;&#x627;&#x646;</button>
</div>
<div id="plpanel-add-col">
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">&#x639;&#x646;&#x648;&#x627;&#x646; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F; *</label><input id="pl_new_col_label" style="width:100%;padding:10px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;"></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">&#x645;&#x648;&#x642;&#x639; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;</label>
<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
<select id="pl_new_col_position" onchange="togglePaylogPositionCol()" style="padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:0 0 auto;">
<option value="end">&#x641;&#x64A; &#x627;&#x644;&#x646;&#x647;&#x627;&#x64A;&#x629;</option>
<option value="start">&#x641;&#x64A; &#x627;&#x644;&#x628;&#x62F;&#x627;&#x64A;&#x629;</option>
<option value="after">&#x628;&#x639;&#x62F; &#x639;&#x645;&#x648;&#x62F;:</option>
</select>
<select id="pl_new_col_after" style="display:none;padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:1;"><option value="">&#8212; &#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#8212;</option></select>
</div></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="addPaylogColumn()">&#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F;</button>
</div></div>
<div id="plpanel-del-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#e53935;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x644;&#x644;&#x62D;&#x630;&#x641; *</label>
<select id="pl_del_col_key" style="width:100%;padding:10px;border:1.5px solid #fce4ec;border-radius:9px;font-size:14px;background:#fff9f9;"><option value="">&#8212; &#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F; &#8212;</option></select></div>
<div style="background:#fff3f3;border-radius:8px;padding:10px;font-size:12px;color:#c62828;margin-bottom:12px;">&#9888; &#x62A;&#x62D;&#x630;&#x64A;&#x631;: &#x62D;&#x630;&#x641; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x64A;&#x62D;&#x630;&#x641; &#x62C;&#x645;&#x64A;&#x639; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x647;. &#x644;&#x627; &#x64A;&#x645;&#x643;&#x646; &#x627;&#x644;&#x62A;&#x631;&#x627;&#x62C;&#x639;.</div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:#e53935;" onclick="deletePaylogColumn()">&#x62D;&#x630;&#x641; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;</button>
</div></div>
<div id="plpanel-edit-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#00695C;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; *</label>
<select id="pl_edit_col_key" onchange="fillPaylogEditLabel()" style="width:100%;padding:10px;border:1.5px solid #b2dfdb;border-radius:9px;font-size:14px;background:#f0fdfb;"><option value="">&#8212; &#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F; &#8212;</option></select></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#00695C;">&#x627;&#x644;&#x627;&#x633;&#x645; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F; *</label><input id="pl_edit_col_label" style="width:100%;padding:10px;border:1.5px solid #b2dfdb;border-radius:9px;font-size:14px;background:#f0fdfb;"></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#00897B,#00695C);" onclick="updatePaylogColumnLabel()">&#x62D;&#x641;&#x638; &#x627;&#x644;&#x639;&#x646;&#x648;&#x627;&#x646;</button>
</div></div>
<div class="modal-actions" style="margin-top:18px;justify-content:center;">
<button class="btn-cancel" style="background:#e0f2f1;color:#00695C;" onclick="closePaylogTableEditModal()">&#x625;&#x63A;&#x644;&#x627;&#x642;</button>
</div>
</div>
</div>
<!-- EVALUATIONS ADD/EDIT MODAL -->
<div class="modal-bg" id="evalModal">
  <div class="modal" style="border-top:4px solid #1976D2;max-width:720px;">
    <h2 id="evalModalTitle" style="color:#1565C0;">&#x1F4DD; &#x625;&#x636;&#x627;&#x641;&#x629; &#x62A;&#x642;&#x64A;&#x64A;&#x645;</h2>
    <input type="hidden" id="evalEditId">
    <div class="form-grid">
      <div class="field"><label style="color:#1565C0;">&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x645;&#x644;&#x621; &#x627;&#x644;&#x625;&#x633;&#x62A;&#x645;&#x627;&#x631;&#x629;</label><input type="date" id="ev_form_fill_date" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label><input id="ev_group_name" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x627;&#x644;&#x627;&#x633;&#x645; *</label><input id="ev_student_name" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x627;&#x644;&#x645;&#x634;&#x627;&#x631;&#x643;&#x629; &#x62F;&#x627;&#x62E;&#x644; &#x627;&#x644;&#x635;&#x641;</label><input id="ev_class_participation" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x627;&#x644;&#x633;&#x644;&#x648;&#x643; &#x627;&#x644;&#x639;&#x627;&#x645;</label><input id="ev_general_behavior" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field full"><label style="color:#1565C0;">&#x627;&#x644;&#x645;&#x644;&#x627;&#x62D;&#x638;&#x627;&#x62A; &#x639;&#x644;&#x649; &#x627;&#x644;&#x633;&#x644;&#x648;&#x643;</label><input id="ev_behavior_notes" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x627;&#x644;&#x642;&#x631;&#x627;&#x621;&#x629;</label><input id="ev_reading" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x627;&#x644;&#x625;&#x645;&#x644;&#x627;&#x621;</label><input id="ev_dictation" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x645;&#x639;&#x627;&#x646;&#x64A; &#x627;&#x644;&#x645;&#x635;&#x637;&#x644;&#x62D;&#x627;&#x62A;</label><input id="ev_term_meanings" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x627;&#x644;&#x645;&#x62D;&#x627;&#x62F;&#x62B;&#x629;</label><input id="ev_conversation" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x627;&#x644;&#x62A;&#x639;&#x628;&#x64A;&#x631;</label><input id="ev_expression" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field"><label style="color:#1565C0;">&#x627;&#x644;&#x642;&#x648;&#x627;&#x639;&#x62F;</label><input id="ev_grammar" style="border-color:#bbdefb;background:#f0f7ff;"></div>
      <div class="field full"><label style="color:#1565C0;">&#x627;&#x644;&#x645;&#x644;&#x627;&#x62D;&#x638;&#x627;&#x62A;</label><input id="ev_notes" style="border-color:#bbdefb;background:#f0f7ff;"></div>
    </div>
    <div class="modal-actions">
      <button class="btn-save" style="background:linear-gradient(135deg,#1976D2,#1565C0);" onclick="saveEval()">&#x62D;&#x641;&#x638;</button>
      <button class="btn-cancel" style="background:#e3f2fd;color:#1565C0;" onclick="closeEvalModal()">&#x625;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<!-- EVALUATIONS TABLE EDIT MODAL -->
<div class="modal-bg" id="evalTableEditModal">
<div class="modal" style="border-top:4px solid #FF6B35;max-width:560px;">
<h2 style="color:#E55A2B;">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x62C;&#x62F;&#x648;&#x644; &#x627;&#x644;&#x62A;&#x642;&#x64A;&#x64A;&#x645;&#x627;&#x62A;</h2>
<div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:2px solid #e3f2fd;padding-bottom:10px;">
<button id="evtab-add-col" onclick="switchEvalTab('add-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#FF6B35;color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#43; &#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F;</button>
<button id="evtab-del-col" onclick="switchEvalTab('del-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#e3f2fd;color:#1565C0;font-weight:700;cursor:pointer;font-size:13px;">&#10060; &#x62D;&#x630;&#x641; &#x639;&#x645;&#x648;&#x62F;</button>
<button id="evtab-edit-col" onclick="switchEvalTab('edit-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#e3f2fd;color:#1565C0;font-weight:700;cursor:pointer;font-size:13px;">&#9998; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x639;&#x646;&#x648;&#x627;&#x646;</button>
</div>
<div id="evpanel-add-col">
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">&#x639;&#x646;&#x648;&#x627;&#x646; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F; *</label><input id="ev_new_col_label" style="width:100%;padding:10px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;"></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">&#x645;&#x648;&#x642;&#x639; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;</label>
<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
<select id="ev_new_col_position" onchange="toggleEvalPositionCol()" style="padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:0 0 auto;">
<option value="end">&#x641;&#x64A; &#x627;&#x644;&#x646;&#x647;&#x627;&#x64A;&#x629;</option>
<option value="start">&#x641;&#x64A; &#x627;&#x644;&#x628;&#x62F;&#x627;&#x64A;&#x629;</option>
<option value="after">&#x628;&#x639;&#x62F; &#x639;&#x645;&#x648;&#x62F;:</option>
</select>
<select id="ev_new_col_after" style="display:none;padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:1;"><option value="">&#8212; &#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#8212;</option></select>
</div></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="addEvalColumn()">&#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F;</button>
</div></div>
<div id="evpanel-del-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#e53935;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x644;&#x644;&#x62D;&#x630;&#x641; *</label>
<select id="ev_del_col_key" style="width:100%;padding:10px;border:1.5px solid #fce4ec;border-radius:9px;font-size:14px;background:#fff9f9;"><option value="">&#8212; &#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F; &#8212;</option></select></div>
<div style="background:#fff3f3;border-radius:8px;padding:10px;font-size:12px;color:#c62828;margin-bottom:12px;">&#9888; &#x62A;&#x62D;&#x630;&#x64A;&#x631;: &#x62D;&#x630;&#x641; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x64A;&#x62D;&#x630;&#x641; &#x62C;&#x645;&#x64A;&#x639; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x647;. &#x644;&#x627; &#x64A;&#x645;&#x643;&#x646; &#x627;&#x644;&#x62A;&#x631;&#x627;&#x62C;&#x639;.</div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:#e53935;" onclick="deleteEvalColumn()">&#x62D;&#x630;&#x641; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;</button>
</div></div>
<div id="evpanel-edit-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#1565C0;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; *</label>
<select id="ev_edit_col_key" onchange="fillEvalEditLabel()" style="width:100%;padding:10px;border:1.5px solid #bbdefb;border-radius:9px;font-size:14px;background:#f0f7ff;"><option value="">&#8212; &#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F; &#8212;</option></select></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#1565C0;">&#x627;&#x644;&#x627;&#x633;&#x645; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F; *</label><input id="ev_edit_col_label" style="width:100%;padding:10px;border:1.5px solid #bbdefb;border-radius:9px;font-size:14px;background:#f0f7ff;"></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#1976D2,#1565C0);" onclick="updateEvalColumnLabel()">&#x62D;&#x641;&#x638; &#x627;&#x644;&#x639;&#x646;&#x648;&#x627;&#x646;</button>
</div></div>
<div class="modal-actions" style="margin-top:18px;justify-content:center;">
<button class="btn-cancel" style="background:#e3f2fd;color:#1565C0;" onclick="closeEvalTableEditModal()">&#x625;&#x63A;&#x644;&#x627;&#x642;</button>
</div>
</div>
</div>
<script src="https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js"></script>
<!-- DELETE TABLE MODAL -->
<div class="modal-bg" id="deleteTableModal">
  <div class="modal" style="max-width:480px;width:95%;border-top:4px solid #e74c3c;">
    <h2 style="margin-bottom:16px;color:#c0392b;">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</h2>
    <p style="margin-bottom:12px;color:#555;font-size:.95em;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644; &#x627;&#x644;&#x630;&#x64A; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641;&#x647;:</p>
    <div id="deleteTableList" style="max-height:280px;overflow-y:auto;border:1.5px solid #eee;border-radius:10px;padding:8px;margin-bottom:16px;background:#fafafa;"></div>
    <div style="display:flex;gap:10px;justify-content:flex-end;">
      <button class="btn-cancel" onclick="closeDeleteTableModal()">&#x625;&#x644;&#x63A;&#x627;&#x621;</button>
      <button class="btn-save" style="background:linear-gradient(135deg,#c0392b,#e74c3c);" onclick="confirmDeleteTableSave()">&#x62D;&#x641;&#x638;</button>
    </div>
  </div>
</div>
<!-- DELETE TABLE CONFIRM MODAL -->
<div class="confirm-bg" id="deleteTableConfirmModal">
  <div class="confirm-box">
    <p>&#x647;&#x644; &#x623;&#x646;&#x62A; &#x645;&#x62A;&#x623;&#x643;&#x62F; &#x645;&#x646; &#x62D;&#x630;&#x641; &#x647;&#x630;&#x627; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;&#x61F;</p>
    <div style="display:flex;gap:10px;justify-content:center;margin-top:14px;">
      <button class="btn-cancel" onclick="closeDeleteTableConfirm()">&#x625;&#x644;&#x63A;&#x627;&#x621;</button>
      <button class="btn-delete" onclick="executeDeleteTable()">&#x62A;&#x623;&#x643;&#x64A;&#x62F;</button>
    </div>
  </div>
</div>
<script>
// Database-page section nav: smooth-scroll to the picked table and track the
// active tab. Works for the four fixed sections plus any custom tables.
function dbNavGo(e, id) {
  if (e) e.preventDefault();
  var el = document.getElementById(id);
  if (el) el.scrollIntoView({behavior: 'smooth', block: 'start'});
  dbNavSetActive(id);
}
function dbNavSetActive(id) {
  document.querySelectorAll('.db-nav-btn').forEach(function(b){ b.classList.remove('active'); });
  var btn = document.querySelector('.db-nav-btn[data-target="'+id+'"]');
  if (btn) btn.classList.add('active');
}
function dbNavRefreshCustom(tables) {
  var holder = document.getElementById('dbNavCustom');
  if (!holder) return;
  var html = '';
  (tables || []).forEach(function(t){
    var id = 'ctsec_' + t.id;
    var name = (t.tbl_name || '').replace(/"/g,'&quot;').replace(/</g,'&lt;');
    html += '<a class="db-nav-btn blue" href="#' + id + '" data-target="' + id + '" onclick="dbNavGo(event,\\'' + id + '\\')">' + '\U0001F4CB ' + name + '</a>';
  });
  holder.innerHTML = html;
}
// Bulk-select helpers shared across all tables on this page.
function _bulkToggleAll(tbodyId, checked){
  var tb = document.getElementById(tbodyId); if(!tb) return;
  tb.querySelectorAll('.bulk-cb').forEach(function(b){ b.checked = checked; });
}
function _bulkUpdate(tbodyId, selectAllId, btnId){
  var tb = document.getElementById(tbodyId); if(!tb) return;
  var all = tb.querySelectorAll('.bulk-cb');
  var checked = tb.querySelectorAll('.bulk-cb:checked');
  var btn = document.getElementById(btnId);
  if(btn){ if(checked.length>0) btn.classList.add('show'); else btn.classList.remove('show'); }
  var sa = document.getElementById(selectAllId);
  if(sa){
    sa.checked = all.length>0 && checked.length===all.length;
    sa.indeterminate = checked.length>0 && checked.length<all.length;
  }
}
function _bulkSelectAll(tbodyId, selectAllId, btnId, checked){
  _bulkToggleAll(tbodyId, checked);
  _bulkUpdate(tbodyId, selectAllId, btnId);
}
function _bulkIds(tbodyId){
  var tb = document.getElementById(tbodyId); if(!tb) return [];
  return Array.from(tb.querySelectorAll('.bulk-cb:checked')).map(function(b){ return b.getAttribute('data-id'); });
}
function _bulkDelete(tbodyId, urlFn, refreshFn, confirmMsg){
  var ids = _bulkIds(tbodyId);
  if(!ids.length) return;
  if(!confirm(confirmMsg.replace('{n}', ids.length))) return;
  Promise.all(ids.map(function(id){
    return fetch(urlFn(id), {method:'DELETE', credentials:'include'}).then(function(r){return r.ok;}).catch(function(){return false;});
  })).then(function(results){
    var ok = results.filter(function(x){return x;}).length;
    showToast('\u062A\u0645 \u062D\u0630\u0641 ' + ok + ' \u0645\u0646 ' + ids.length, ok===ids.length?'#6B3FA0':'#e53935');
    if(typeof refreshFn === 'function') refreshFn();
  });
}

// Freeze-columns helpers shared across every table on this page.
// Freeze state is saved to localStorage keyed by tableKey (e.g. "students",
// "groups", "custom_<tid>"). Stored as an array of column indices (the <th>
// positions inside the table's thead tr).
var _freezeCurrentTable = null;
function _freezeKey(tableKey){ return 'freeze_'+tableKey; }
function _freezeLoad(tableKey){
  try { return JSON.parse(localStorage.getItem(_freezeKey(tableKey)) || '[]') || []; }
  catch(e){ return []; }
}
function _freezeSave(tableKey, indices){
  try { localStorage.setItem(_freezeKey(tableKey), JSON.stringify(indices)); } catch(e){}
}
function _freezeTableForKey(tableKey){
  if (tableKey.indexOf('custom_') === 0) {
    var tid = tableKey.substring(7);
    var tbody = document.getElementById('ctbody_' + tid);
    return tbody ? tbody.closest('table') : null;
  }
  var tbodyIds = { students:'studentsBody', groups:'groupsBody2', taqseet:'taqseetBody', attendance:'attendanceBody', evals:'evalsBody', paylog:'paylogBody' };
  var tbody = document.getElementById(tbodyIds[tableKey]);
  return tbody ? tbody.closest('table') : null;
}
function applyFreezeToTable(tableKey){
  var table = _freezeTableForKey(tableKey);
  if (!table) return;
  // Clear any prior freeze styling.
  table.querySelectorAll('.frozen-col').forEach(function(el){
    el.classList.remove('frozen-col');
    el.style.position = '';
    el.style.right = '';
    el.style.zIndex = '';
  });
  var indices = _freezeLoad(tableKey);
  if (!indices.length) return;
  var headerTr = table.querySelector('thead tr');
  if (!headerTr) return;
  var ths = headerTr.querySelectorAll('th');
  var bodyRows = table.querySelectorAll('tbody tr');
  var cumRight = 0;
  for (var i = 0; i < ths.length; i++) {
    if (indices.indexOf(i) < 0) continue;
    var w = ths[i].offsetWidth;
    _pinCell(ths[i], cumRight, true);
    for (var r = 0; r < bodyRows.length; r++) {
      var cell = bodyRows[r].children[i];
      if (cell) _pinCell(cell, cumRight, false);
    }
    cumRight += w;
  }
}
function _pinCell(el, offset, isHeader){
  el.classList.add('frozen-col');
  el.style.position = 'sticky';
  el.style.right = offset + 'px';
  el.style.zIndex = isHeader ? '4' : '2';
}
function openFreezeModal(tableKey){
  _freezeCurrentTable = tableKey;
  var table = _freezeTableForKey(tableKey);
  if (!table) { showToast('\u0627\u0644\u062C\u062F\u0648\u0644 \u063A\u064A\u0631 \u0645\u062A\u0627\u062D','#e53935'); return; }
  var ths = table.querySelectorAll('thead tr th');
  var frozen = _freezeLoad(tableKey);
  var body = document.getElementById('freezeModalBody');
  var html = '';
  for (var i = 0; i < ths.length; i++) {
    var th = ths[i];
    if (th.classList.contains('bulk-col')) continue;
    var label = (th.textContent || '').trim();
    if (!label) label = '#' + (i+1);
    var checked = frozen.indexOf(i) >= 0 ? 'checked' : '';
    html += '<label><input type="checkbox" data-idx="'+i+'" '+checked+'><span>'+label.replace(/</g,'&lt;')+'</span></label>';
  }
  body.innerHTML = html || '<div style="color:#888;padding:8px;">\u0644\u0627 \u062A\u0648\u062C\u062F \u0623\u0639\u0645\u062F\u0629</div>';
  document.getElementById('freezeModal').classList.add('open');
}
function closeFreezeModal(){
  document.getElementById('freezeModal').classList.remove('open');
  _freezeCurrentTable = null;
}
function applyFreezeFromModal(){
  if (!_freezeCurrentTable) { closeFreezeModal(); return; }
  var boxes = document.querySelectorAll('#freezeModalBody input[type=checkbox]:checked');
  var indices = Array.from(boxes).map(function(b){ return parseInt(b.getAttribute('data-idx'),10); }).filter(function(x){ return !isNaN(x); });
  indices.sort(function(a,b){ return a-b; });
  _freezeSave(_freezeCurrentTable, indices);
  applyFreezeToTable(_freezeCurrentTable);
  showToast('\u062A\u0645 \u062A\u062D\u062F\u064A\u062B \u0627\u0644\u062A\u062C\u0645\u064A\u062F','#1565C0');
  closeFreezeModal();
}
// \u2500\u2500\u2500 Taqseet (Payment Plans) Table \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
var allTaqseet = null;
var editingTaqseetId = null;
var taqseetLabels = {};  // col_key -> Arabic label for dynamically-added columns

function loadTaqseet() {
  Promise.all([
    fetch('/api/taqseet').then(function(r){return r.json();}),
    fetch('/api/taqseet-labels').then(function(r){return r.ok ? r.json() : {};}).catch(function(){return {};})
  ]).then(function(res){
    allTaqseet = res[0] || [];
    taqseetLabels = res[1] || {};
    document.getElementById('taqseetCount').textContent = allTaqseet.length;
    renderTaqseet();
  });
}

function renderTaqseet() {
  var tbody = document.getElementById('taqseetBody');
  if (!allTaqseet || !allTaqseet.length) {
    tbody.innerHTML = '<tr><td colspan="45" style="text-align:center;color:#aaa;padding:24px;">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;</td></tr>';
    _bulkUpdate('taqseetBody','selectAll_taqseet','bulkDelBtn_taqseet');
    applyFreezeToTable('taqseet');
    return;
  }
  var baseFields = ['taqseet_method','student_name','course_amount','num_installments',
    'inst1','paid1','date1','inst2','paid2','date2','inst3','paid3','date3','inst4','paid4','date4',
    'inst5','paid5','date5','inst6','paid6','date6','inst7','paid7','date7','inst8','paid8','date8',
    'inst9','paid9','date9','inst10','paid10','date10','inst11','paid11','date11','inst12','paid12','date12',
    'study_hours','start_date'];
  // Detect extra columns (auto-created via Excel import) present in the data
  // but not in the static header. Append them after the baseline columns so
  // they show up in the UI.
  var seen = {id:1, created_at:1};
  baseFields.forEach(function(f){ seen[f] = 1; });
  var extraFields = [];
  allTaqseet.forEach(function(r){
    Object.keys(r).forEach(function(k){
      if(!seen[k]){ seen[k] = 1; extraFields.push(k); }
    });
  });
  var fields = baseFields.concat(extraFields);
  // If extras exist, append matching <th> cells to the thead (idempotent).
  if(extraFields.length){
    var thead = document.querySelector('#taqseetTable thead tr');
    if(thead){
      var existingKeys = {};
      thead.querySelectorAll('th[data-col]').forEach(function(th){ existingKeys[th.dataset.col] = 1; });
      var actionsTh = thead.lastElementChild;
      extraFields.forEach(function(k){
        if(existingKeys[k]) return;
        var th = document.createElement('th');
        th.dataset.col = k;
        th.style.cssText = 'padding:10px 8px;white-space:nowrap;min-width:110px;';
        th.textContent = (taqseetLabels && taqseetLabels[k]) || k;
        thead.insertBefore(th, actionsTh);
      });
    }
  }
  tbody.innerHTML = allTaqseet.map(function(r, i) {
    var bg = i % 2 === 0 ? '#fff' : '#f8f4ff';
    var cells = fields.map(function(f) {
      // num_installments is auto-calculated from inst1..inst12 and is not hand-editable.
      if (f === 'num_installments') {
        return '<td data-id="' + r.id + '" data-field="' + f + '" title="\u064A\u062D\u0633\u0628 \u062A\u0644\u0642\u0627\u0626\u064A\u0627\u064B" style="padding:8px;min-width:80px;background:#eef5ff;color:#1565C0;font-weight:700;text-align:center;">' + (r[f]||'') + '</td>';
      }
      return '<td class="editable" contenteditable="true" data-id="' + r.id + '" data-field="' + f + '" style="padding:8px;min-width:80px;">' + (r[f]||'') + '</td>';
    }).join('');
    return '<tr style="background:' + bg + ';">' +
      '<td class="bulk-col" style="padding:8px;"><input type="checkbox" class="bulk-cb" data-id="' + r.id + '" onclick="_bulkUpdate(\\'taqseetBody\\',\\'selectAll_taqseet\\',\\'bulkDelBtn_taqseet\\')"></td>' +
      '<td style="padding:8px;text-align:center;color:#6c3fa0;font-weight:700;">' + (i+1) + '</td>' +
      cells +
      '<td style="padding:8px;white-space:nowrap;text-align:center;">' +
        '<button class="btn-icon" style="background:#c0392b;color:#fff;border:none;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:12px;" onclick="deleteTaqseet(' + r.id + ')">&#x62D;&#x630;&#x641;</button>' +
      '</td>' +
    '</tr>';
  }).join('');
  // Attach blur events + real-time lock updates for inst*/course_amount.
  tbody.querySelectorAll('.editable[data-field]').forEach(function(td) {
    td.addEventListener('blur', function() {
      saveTaqseetCell(parseInt(this.dataset.id), this.dataset.field, this);
    });
    var f = td.dataset.field;
    if (/^inst\d+$/.test(f) || f === 'course_amount') {
      td.addEventListener('input', function() {
        updateTaqseetLockState(this.closest('tr'));
      });
    }
  });
  // Initial lock evaluation per row (reflect whatever's already saved).
  tbody.querySelectorAll('tr').forEach(function(tr){ updateTaqseetLockState(tr); });
  applyFreezeToTable('taqseet');
}

function _taqseetParseNum(s){
  var v = parseFloat(String(s == null ? '' : s).replace(/,/g, ''));
  return isNaN(v) ? 0 : v;
}
function _taqseetSetLocked(cell, lock){
  if (!cell) return;
  if (lock) {
    cell.setAttribute('contenteditable', 'false');
    cell.classList.add('taqseet-locked');
  } else {
    cell.setAttribute('contenteditable', 'true');
    cell.classList.remove('taqseet-locked');
  }
}
function updateTaqseetLockState(tr){
  if (!tr) return;
  var courseCell = tr.querySelector('td[data-field="course_amount"]');
  var courseAmt = courseCell ? _taqseetParseNum(courseCell.innerText) : 0;
  // No valid ceiling -> every inst cell stays editable.
  if (courseAmt <= 0) {
    for (var i = 1; i <= 12; i++) {
      _taqseetSetLocked(tr.querySelector('td[data-field="inst'+i+'"]'), false);
    }
    return;
  }
  var sum = 0, locked = false;
  for (var i = 1; i <= 12; i++) {
    var c = tr.querySelector('td[data-field="inst'+i+'"]');
    if (!c) continue;
    if (locked) { _taqseetSetLocked(c, true); continue; }
    var v = _taqseetParseNum(c.innerText);
    if (v > 0) sum += v;
    _taqseetSetLocked(c, false);
    if (sum >= courseAmt) locked = true;
  }
}

function saveTaqseetCell(id, field, el) {
  var val = el.innerText.trim();
  var r = allTaqseet ? allTaqseet.find(function(x){return x.id===id;}) : null;
  if (!r) return;
  var updated = {};
  for (var k in r) { updated[k] = r[k]; }
  updated[field] = val;
  var affectsInstallments = /^inst\d+$/.test(field) || field === 'course_amount';
  var installmentCount = 0;
  if (affectsInstallments) {
    var sum = 0;
    for (var i = 1; i <= 12; i++) {
      var v = parseFloat(String(updated['inst'+i] || '').replace(/,/g, ''));
      if (!isNaN(v) && v > 0) { sum += v; installmentCount++; }
    }
    var courseAmt = parseFloat(String(updated.course_amount || '').replace(/,/g, ''));
    if (!isNaN(courseAmt) && courseAmt > 0 && sum > courseAmt) {
      showToast('\u0645\u062C\u0645\u0648\u0639 \u0627\u0644\u0623\u0642\u0633\u0627\u0637 (' + sum + ') \u064A\u062A\u062C\u0627\u0648\u0632 \u0645\u0628\u0644\u063A \u0627\u0644\u062F\u0648\u0631\u0629 (' + courseAmt + ')', '#e53935');
      el.innerText = r[field] == null ? '' : String(r[field]);
      updateTaqseetLockState(el.closest('tr'));
      return;
    }
    updated.num_installments = String(installmentCount);
  }
  fetch('/api/taqseet/' + id, {method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify(updated)})
    .then(function(res){return res.json();})
    .then(function(){
      if (r) {
        r[field] = val;
        if (affectsInstallments) {
          r.num_installments = String(installmentCount);
          var tr = el.closest('tr');
          if (tr) {
            var niCell = tr.querySelector('td[data-field="num_installments"]');
            if (niCell) niCell.innerText = String(installmentCount);
          }
        }
      }
    });
}

function openAddTaqseet() {
  var nextNum = allTaqseet ? allTaqseet.length + 1 : 1;
  fetch('/api/taqseet', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({taqseet_method: String(nextNum),
      student_name:'', course_amount:'', num_installments:'',
      inst1:'', paid1:'', date1:'', inst2:'', paid2:'', date2:'', inst3:'', paid3:'', date3:'',
      inst4:'', paid4:'', date4:'', inst5:'', paid5:'', date5:'', inst6:'', paid6:'', date6:'',
      inst7:'', paid7:'', date7:'', inst8:'', paid8:'', date8:'', inst9:'', paid9:'', date9:'',
      inst10:'', paid10:'', date10:'', inst11:'', paid11:'', date11:'', inst12:'', paid12:'', date12:'',
      study_hours:'', start_date:''})})
    .then(function(){ loadTaqseet(); showToast('&#x62A;&#x645; &#x625;&#x636;&#x627;&#x641;&#x629; &#x635;&#x641; &#x62C;&#x62F;&#x64A;&#x62F;', '#1a8754'); });
}

function deleteTaqseet(id) {
  if (!confirm('&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; &#x647;&#x630;&#x627; &#x627;&#x644;&#x635;&#x641;&#x61F;')) return;
  fetch('/api/taqseet/' + id, {method:'DELETE'}).then(function(){
    loadTaqseet();
    showToast('&#x62A;&#x645; &#x627;&#x644;&#x62D;&#x630;&#x641;','#c0392b');
  });
}

function openTaqseetEditModal() {
  // The taqseet schema columns are fixed; individual cells are edited inline
  // by clicking them (contenteditable). This modal surfaces that fact plus
  // the bulk-clear action so the "edit table" button does something useful.
  var m = document.getElementById('taqseetEditHelpModal');
  if (m) { m.classList.add('open'); return; }
  m = document.createElement('div');
  m.id = 'taqseetEditHelpModal';
  m.className = 'modal-bg open';
  m.innerHTML =
    '<div class="modal" style="border-top:4px solid #9C27B0;max-width:540px;">' +
      '<h2 style="color:#6c3fa0;">⚙ تعديل جدول التقسيط</h2>' +
      '<ul style="line-height:1.9;padding-right:20px;font-size:14px;color:#333;">' +
        '<li>لتعديل أي خلية: اضغط عليها مباشرةً في الجدول واكتب القيمة الجديدة، ثم انتقل إلى خلية أخرى ليتم الحفظ تلقائياً.</li>' +
        '<li>عدد الأقساط يُحسب تلقائياً من خلايا الأقساط ولا يُعدَّل يدوياً.</li>' +
        '<li>لإضافة صف جديد: اضغط زر «إضافة صف».</li>' +
        '<li>لاستيراد بيانات من Excel: اضغط زر «إضافة بيانات من Excel».</li>' +
        '<li>لحذف صف: حدّده بالمربّع واضغط «حذف المحدّد»، أو استخدم زر «حذف» في آخر الصف.</li>' +
      '</ul>' +
      '<div class="modal-actions"><button class="btn-cancel" style="background:#e1bee7;color:#6c3fa0;" onclick="closeTaqseetEditModal()">حسناً</button></div>' +
    '</div>';
  document.body.appendChild(m);
}
function closeTaqseetEditModal() {
  var m = document.getElementById('taqseetEditHelpModal');
  if (m) m.classList.remove('open');
}
// &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;

let allStudents=[];
let deleteTargetId=null;
var allColumns=[];
function getTaqseetDetail(method){
  if(!method||!allTaqseetData.length)return '';
  var t=allTaqseetData.find(function(x){return x.taqseet_method===method;});
  if(!t)return '';
  return '&#x637;&#x631;&#x64A;&#x642;&#x629; '+method+' &#x2014; &#x645;&#x628;&#x644;&#x63A; &#x627;&#x644;&#x62F;&#x648;&#x631;&#x629;: '+(t.course_amount||'')+'&#x60C; &#x639;&#x62F;&#x62F; &#x627;&#x644;&#x623;&#x642;&#x633;&#x627;&#x637;: '+(t.num_installments||'')+'&#x60C; &#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x623;&#x648;&#x644;: '+(t.inst1||'')+'&#x60C; &#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62B;&#x627;&#x646;&#x64A;: '+(t.inst2||'');
}
function populateTaqseetDropdowns(){
  var selects=document.querySelectorAll('.installment-select');
  selects.forEach(function(sel){
    var curVal=sel.value;
    while(sel.options.length>1)sel.remove(1);
    allTaqseetData.forEach(function(t){
      var opt=document.createElement('option');
      opt.value=t.taqseet_method;
      opt.text=t.taqseet_method;
      if(t.taqseet_method===curVal)opt.selected=true;
      sel.appendChild(opt);
    });
  });
}
function updateInstallmentType(sid,val){
  fetch('/api/students/'+sid,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({installment_type:val})})
  .then(function(r){return r.json();})
  .then(function(d){if(d.ok){var s=allStudents.find(function(x){return x.id===sid;});if(s)s.installment_type=val; renderTable(allStudents);}});
}
function populateEditInstallmentSelect(curVal){
  var sel=document.getElementById('f_installment_type');
  if(!sel)return;
  while(sel.options.length>1)sel.remove(1);
  allTaqseetData.forEach(function(t){
    var opt=document.createElement('option');
    opt.value=t.taqseet_method;
    opt.text=t.taqseet_method;
    if(t.taqseet_method===curVal)opt.selected=true;
    sel.appendChild(opt);
  });
  updateEditInstallmentDetail(curVal);
}
function updateEditInstallmentDetail(val){
  var detail=getTaqseetDetail(val);
  var existing=document.getElementById('edit_installment_detail');
  if(existing)existing.textContent=detail;
}
var allTaqseetData=[];
async function loadStudents(){
const [sRes,cRes,tRes]=await Promise.all([fetch('/api/students'),fetch('/api/columns'),fetch('/api/taqseet').catch(()=>({ok:false,json:()=>Promise.resolve([])}))]);
const sData=await sRes.json(); const cData=await cRes.json();
allStudents=sData.students||[]; allColumns=cData.columns||[]; allTaqseetData=await tRes.json(); populateTaqseetDropdowns();
renderTable(allStudents);
document.getElementById('totalCount').textContent=allStudents.length;
buildTableHeader();
applyFreezeToTable('students');
}
function buildTableHeader(){
var thead=document.querySelector('#studentsBody').closest('table').querySelector('thead tr');
if(!thead)return;
var html='<th class="bulk-col"><input type="checkbox" id="selectAll_students" class="bulk-cb" onclick="_bulkSelectAll(\\'studentsBody\\',\\'selectAll_students\\',\\'bulkDelBtn_students\\',this.checked)"></th><th>#</th>';
for(var i=0;i<allColumns.length;i++){html+='<th>'+allColumns[i].col_label+'</th>';}
html+='<th>&#x627;&#x62C;&#x631;&#x627;&#x621;&#x627;&#x62A;</th>';
thead.innerHTML=html;
}
function renderTable(list){
var body=document.getElementById('studentsBody');
var colCount=allColumns.length+3;
if(!list.length){body.innerHTML='<tr><td colspan="'+colCount+'" class="no-data">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x60C; &#x627;&#x636;&#x641; &#x627;&#x648;&#x644; &#x637;&#x627;&#x644;&#x628;</td></tr>';_bulkUpdate('studentsBody','selectAll_students','bulkDelBtn_students');applyFreezeToTable('students');return;}
var html='';
for(var i=0;i<list.length;i++){
var s2=list[i];
var row='<tr><td class="bulk-col"><input type="checkbox" class="bulk-cb" data-id="'+s2.id+'" onclick="_bulkUpdate(\\'studentsBody\\',\\'selectAll_students\\',\\'bulkDelBtn_students\\')"></td><td>'+(i+1)+'</td>';
for(var j=0;j<allColumns.length;j++){
var key=allColumns[j].col_key;
var val=s2[key]||'';
if(key==='personal_id'){row+='<td><b>'+val+'</b></td>';}
else if(key==='student_name'){row+='<td class="name-cell">'+val+'</td>';}
else if(key==='final_result'){
var badge=val==='&#x646;&#x627;&#x62C;&#x62D;'?'badge-pass':val==='&#x631;&#x627;&#x633;&#x628;'?'badge-fail':'badge-pend';
row+='<td>'+(val?'<span class="badge '+badge+'">'+val+'</span>':'-')+'</td>';
}else if(key==='installment_type'){var tqDetail=getTaqseetDetail(val);row+='<td class="installment-cell"><select class="installment-select" onchange="updateInstallmentType('+s2.id+',this.value)"><option value="">-- &#x627;&#x62E;&#x62A;&#x631; --</option>'+allTaqseetData.map(function(t){return '<option value="'+t.taqseet_method+'"'+(t.taqseet_method===val?' selected="selected"':'')+'>'+t.taqseet_method+'</option>';}).join('')+'</select>'+(tqDetail?'<br><small class="tq-detail">'+tqDetail+'</small>':'')+'</td>';}else{row+='<td>'+(val||'-')+'</td>';}
}
row+='<td><button class="action-btn btn-edit" onclick="openEdit('+s2.id+')">&#9998;</button><button class="action-btn btn-del" onclick="askDelete('+s2.id+')">&#128465;</button></td></tr>';
html+=row;
}
body.innerHTML=html;
applyFreezeToTable('students');
}
function filterTable(){
  const q=document.getElementById('searchInput').value.toLowerCase();
  renderTable(allStudents.filter(s=>(s.student_name||'').toLowerCase().includes(q)||(s.personal_id||'').toLowerCase().includes(q)));
}
function clearForm(){ ['personal_id','student_name','whatsapp','class_name','old_new_2026','registration_term2_2026','group_name_student','group_online','final_result','level_reached','suitable_level','books_received','teacher','installment1','installment2','installment3','installment4','installment5','mother_phone','father_phone','other_phone','residence','home_address','road','complex'].forEach(k=>{const el=document.getElementById('f_'+k);if(el)el.value='';}); document.getElementById('editId').value=''; } function openAddModal(){clearForm();document.getElementById('modalTitle').innerHTML='&#x625;&#x636;&#x627;&#x641;&#x629; &#x637;&#x627;&#x644;&#x628; &#x62C;&#x62F;&#x64A;&#x62F;';document.getElementById('modal').classList.add('open');}
function openEdit(id){ const s=allStudents.find(x=>x.id===id);if(!s)return; document.getElementById('editId').value=id; document.getElementById('modalTitle').innerHTML='&#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;'; document.getElementById('f_personal_id').value=s.personal_id||''; document.getElementById('f_student_name').value=s.student_name||''; document.getElementById('f_whatsapp').value=s.whatsapp||''; document.getElementById('f_class_name').value=s.class_name||''; document.getElementById('f_old_new_2026').value=s.old_new_2026||''; document.getElementById('f_registration_term2_2026').value=s.registration_term2_2026||''; document.getElementById('f_group_name_student').value=s.group_name_student||''; document.getElementById('f_group_online').value=s.group_online||''; document.getElementById('f_final_result').value=s.final_result||''; document.getElementById('f_level_reached').value=s.level_reached_2026||''; document.getElementById('f_suitable_level').value=s.suitable_level_2026||''; document.getElementById('f_books_received').value=s.books_received||''; document.getElementById('f_teacher').value=s.teacher_2026||''; document.getElementById('f_installment1').value=s.installment1||''; document.getElementById('f_installment2').value=s.installment2||''; document.getElementById('f_installment3').value=s.installment3||''; document.getElementById('f_installment4').value=s.installment4||''; document.getElementById('f_installment5').value=s.installment5||''; document.getElementById('f_mother_phone').value=s.mother_phone||''; document.getElementById('f_father_phone').value=s.father_phone||''; document.getElementById('f_other_phone').value=s.other_phone||''; document.getElementById('f_residence').value=s.residence||''; document.getElementById('f_home_address').value=s.home_address||''; document.getElementById('f_road').value=s.road||''; document.getElementById('f_complex').value=s.complex_name||''; document.getElementById('f_installment_type').value=s.installment_type||''; populateEditInstallmentSelect(s.installment_type||''); document.getElementById('modal').classList.add('open'); } function closeModal(){document.getElementById('modal').classList.remove('open');}
async function saveStudent(){ const editId=document.getElementById('editId').value; const body={ personal_id:document.getElementById('f_personal_id').value.trim(), student_name:document.getElementById('f_student_name').value.trim(), whatsapp:document.getElementById('f_whatsapp').value.trim(), class_name:document.getElementById('f_class_name').value.trim(), old_new_2026:document.getElementById('f_old_new_2026').value.trim(), registration_term2_2026:document.getElementById('f_registration_term2_2026').value.trim(), group_name_student:document.getElementById('f_group_name_student').value.trim(), group_online:document.getElementById('f_group_online').value.trim(), final_result:document.getElementById('f_final_result').value, level_reached_2026:document.getElementById('f_level_reached').value.trim(), suitable_level_2026:document.getElementById('f_suitable_level').value.trim(), books_received:document.getElementById('f_books_received').value.trim(), teacher_2026:document.getElementById('f_teacher').value.trim(), installment1:document.getElementById('f_installment1').value.trim(), installment2:document.getElementById('f_installment2').value.trim(), installment3:document.getElementById('f_installment3').value.trim(), installment4:document.getElementById('f_installment4').value.trim(), installment5:document.getElementById('f_installment5').value.trim(), mother_phone:document.getElementById('f_mother_phone').value.trim(), father_phone:document.getElementById('f_father_phone').value.trim(), other_phone:document.getElementById('f_other_phone').value.trim(), residence:document.getElementById('f_residence').value.trim(), home_address:document.getElementById('f_home_address').value.trim(), road:document.getElementById('f_road').value.trim(), complex_name:document.getElementById('f_complex').value.trim(), installment_type:document.getElementById('f_installment_type').value.trim(), }; if(!body.personal_id||!body.student_name){showToast('&#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A; &#x648;&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x645;&#x637;&#x644;&#x648;&#x628;&#x627;&#x646;','#e53935');return;} const url=editId?'/api/students/'+editId:'/api/students'; const method=editId?'PUT':'POST'; const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); const data=await res.json(); if(data.ok){closeModal();showToast(editId?'&#x62A;&#x645; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x628;&#x646;&#x62C;&#x627;&#x62D;':'&#x62A;&#x645; &#x625;&#x636;&#x627;&#x641;&#x629; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x628;&#x646;&#x62C;&#x627;&#x62D;');loadStudents();} else{showToast(data.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');} } function askDelete(id){deleteTargetId=id;document.getElementById('confirmModal').classList.add('open');document.getElementById('confirmDelBtn').onclick=confirmDelete;}
async function confirmDelete(){
  if(!deleteTargetId)return;
  const res=await fetch('/api/students/'+deleteTargetId,{method:'DELETE'});
  const data=await res.json();
  closeConfirm();
  if(data.ok){showToast('&#x62A;&#x645; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x628;&#x646;&#x62C;&#x627;&#x62D;');loadStudents();}
  else{showToast(data.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627; &#x641;&#x64A; &#x627;&#x644;&#x62D;&#x630;&#x641;','#e53935');}
  deleteTargetId=null;
}
function closeConfirm(){document.getElementById('confirmModal').classList.remove('open');}
function showToast(msg,bg='#6B3FA0'){const t=document.getElementById('toast');t.textContent=msg;t.style.background=bg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3000);}
// Belt-and-suspenders: set the student-modal labels via unicode escapes so the
// text renders even if a user's browser or a cached proxy somehow fails to
// decode the HTML entities in the static markup.
(function(){
  var STUDENT_LABELS = {
    f_personal_id: '\u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u0634\u062E\u0635\u064A *',
    f_student_name: '\u0627\u0633\u0645 \u0627\u0644\u0637\u0627\u0644\u0628 *',
    f_whatsapp: '\u0647\u0627\u062A\u0641 \u0627\u0644\u0648\u0627\u062A\u0633\u0627\u0628 \u0627\u0644\u0645\u0639\u062A\u0645\u062F',
    f_class_name: '\u0627\u0644\u0635\u0641',
    f_old_new_2026: '\u0642\u062F\u064A\u0645 \u062C\u062F\u064A\u062F 2026',
    f_registration_term2_2026: '\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u0641\u0635\u0644 \u0627\u0644\u062B\u0627\u0646\u064A 2026',
    f_group_name_student: '\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629',
    f_group_online: '\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 (\u0627\u0644\u0627\u0648\u0646\u0644\u0627\u064A\u0646)',
    f_final_result: '\u0627\u0644\u0646\u062A\u064A\u062C\u0629 \u0627\u0644\u0646\u0647\u0627\u0626\u064A\u0629 (\u062A\u062D\u062F\u064A\u062F \u0627\u0644\u0645\u0633\u062A\u0648\u0649 2026)',
    f_level_reached: '\u0627\u0644\u0649 \u0627\u064A\u0646 \u0648\u0635\u0644 \u0627\u0644\u0637\u0627\u0644\u0628 2026',
    f_suitable_level: '\u0647\u0644 \u0627\u0644\u0637\u0627\u0644\u0628 \u0645\u0646\u0627\u0633\u0628 \u0644\u0647\u0630\u0627 \u0627\u0644\u0645\u0633\u062A\u0648\u0649 2026\u061F',
    f_books_received: '\u0627\u0633\u062A\u0644\u0627\u0645 \u0627\u0644\u0643\u062A\u0628',
    f_teacher: '\u0627\u0644\u0645\u062F\u0631\u0633 2026',
    f_installment1: '\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u0627\u0648\u0644 2026',
    f_installment2: '\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u062B\u0627\u0646\u064A',
    f_installment3: '\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u062B\u0627\u0644\u062B',
    f_installment4: '\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u0631\u0627\u0628\u0639',
    f_installment5: '\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u062E\u0627\u0645\u0633',
    f_mother_phone: '\u0647\u0627\u062A\u0641 \u0627\u0644\u0627\u0645',
    f_father_phone: '\u0647\u0627\u062A\u0641 \u0627\u0644\u0627\u0628',
    f_other_phone: '\u0647\u0627\u062A\u0641 \u0627\u062E\u0631',
    f_residence: '\u0645\u0643\u0627\u0646 \u0627\u0644\u0633\u0643\u0646',
    f_home_address: '\u0639\u0646\u0648\u0627\u0646 \u0627\u0644\u0645\u0646\u0632\u0644',
    f_road: '\u0627\u0644\u0637\u0631\u064A\u0642',
    f_complex: '\u0627\u0644\u0645\u062C\u0645\u0639',
    f_installment_type: '\u0627\u062E\u062A\u064A\u0627\u0631 \u0646\u0648\u0639 \u0627\u0644\u062A\u0642\u0633\u064A\u0637'
  };
  function applyStudentLabels(){
    for (var id in STUDENT_LABELS) {
      var inp = document.getElementById(id);
      if (inp && inp.previousElementSibling && inp.previousElementSibling.tagName === 'LABEL') {
        inp.previousElementSibling.textContent = STUDENT_LABELS[id];
      }
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', applyStudentLabels);
  else applyStudentLabels();
})();
loadStudents();
loadTaqseet();
var allGroups2=[];
var groupDeleteTargetId2=null;
function loadGroups2(){
  Promise.all([fetch('/api/groups',{credentials:'include'}),fetch('/api/group-columns',{credentials:'include'})]).then(function(rs){
    return Promise.all([rs[0].json(),rs[1].json()]);
  }).then(function(results){
    allGroups2=results[0].groups||[];
    allGroupColumns=results[1].columns||[];
    buildGroupTableHeader();
    renderGroupTable2(allGroups2);
    document.getElementById('groupsTotalCount').textContent=allGroups2.length;
    applyFreezeToTable('groups');
  }).catch(function(){});
}
function buildGroupTableHeader(){
  var thead=document.getElementById('groupsTheadRow');
  if(!thead)return;
  var html='<th class="bulk-col"><input type="checkbox" id="selectAll_groups" class="bulk-cb" onclick="_bulkSelectAll(\\'groupsBody2\\',\\'selectAll_groups\\',\\'bulkDelBtn_groups\\',this.checked)"></th><th>#</th>';
  for(var i=0;i<allGroupColumns.length;i++){html+='<th>'+allGroupColumns[i].col_label+'</th>';}
  html+='<th>&#1575;&#1580;&#1585;&#1575;&#1569;&#1575;&#1578;</th>';
  thead.innerHTML=html;
}
function renderGroupTable2(list){
  var body=document.getElementById('groupsBody2');
  var colCount=allGroupColumns.length+3;
  if(!list.length){body.innerHTML='<tr><td colspan="'+colCount+'" class="no-data">&#1604;&#1575; &#1578;&#1608;&#1580;&#1583; &#1576;&#1610;&#1575;&#1606;&#1575;&#1578;&#1548; &#1575;&#1590;&#1601; &#1575;&#1608;&#1604; &#1605;&#1580;&#1605;&#1608;&#1593;&#1577;</td></tr>';_bulkUpdate('groupsBody2','selectAll_groups','bulkDelBtn_groups');applyFreezeToTable('groups');return;}
  var html='';
  for(var i=0;i<list.length;i++){
    var g=list[i];
    var row='<tr><td class="bulk-col"><input type="checkbox" class="bulk-cb" data-id="'+g.id+'" onclick="_bulkUpdate(\\'groupsBody2\\',\\'selectAll_groups\\',\\'bulkDelBtn_groups\\')"></td><td>'+(i+1)+'</td>';
    for(var j=0;j<allGroupColumns.length;j++){
      var key=allGroupColumns[j].col_key;
      var val=g[key]||'';
      if(key==='group_name'){row+='<td style="font-weight:600;color:#0097A7;text-align:right;">'+val+'</td>';}
      else if(key==='group_link'){row+='<td>'+(val?'<a href="'+val+'" target="_blank" style="color:#00BCD4;">&#1601;&#1578;&#1581;</a>':'-')+'</td>';}
      else{row+='<td>'+(val||'-')+'</td>';}
    }
    row+='<td><button class="action-btn btn-edit" style="color:#0097A7;" onclick="openGroupEdit2('+g.id+')">&#9998;</button><button class="action-btn btn-del" onclick="askGroupDelete2('+g.id+')">&#128465;</button></td></tr>';
    html+=row;
  }
  body.innerHTML=html;
  applyFreezeToTable('groups');
}
function filterGroupTable2(){
  var q=document.getElementById('groupSearchInput').value.toLowerCase();
  renderGroupTable2(allGroups2.filter(function(g){return (g.group_name||'').toLowerCase().indexOf(q)>-1||(g.teacher_name||'').toLowerCase().indexOf(q)>-1;}));
}
function clearGroupForm2(){
  var ids=['group_name','teacher_name','level_course','last_reached','study_time','ramadan_time','online_time','group_link','session_duration','session_minutes_normal','hours_in_person_auto','hours_online_only','hours_all_online','total_required_hours'];
  for(var x=0;x<ids.length;x++){var el=document.getElementById('gf2_'+ids[x]);if(el)el.value='';}
  document.getElementById('groupEditId2').value='';
}
function openAddGroupModal2(){clearGroupForm2();document.getElementById('groupModalTitle2').textContent='\u0627\u0636\u0627\u0641\u0629 \u0645\u062C\u0645\u0648\u0639\u0629 \u062C\u062F\u064A\u062F\u0629';document.getElementById('groupModal2').classList.add('open');}
function openGroupEdit2(id){
  var g=null;
  for(var x=0;x<allGroups2.length;x++){if(allGroups2[x].id===id){g=allGroups2[x];break;}}
  if(!g)return;
  document.getElementById('groupEditId2').value=id;
  document.getElementById('groupModalTitle2').textContent='\u062A\u0639\u062F\u064A\u0644 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629';
  document.getElementById('gf2_group_name').value=g.group_name||'';
  document.getElementById('gf2_teacher_name').value=g.teacher_name||'';
  document.getElementById('gf2_level_course').value=g.level_course||'';
  document.getElementById('gf2_last_reached').value=g.last_reached||'';
  document.getElementById('gf2_study_time').value=g.study_time||'';
  document.getElementById('gf2_ramadan_time').value=g.ramadan_time||'';
  document.getElementById('gf2_online_time').value=g.online_time||'';
  document.getElementById('gf2_group_link').value=g.group_link||'';
  document.getElementById('gf2_session_duration').value=g.session_duration||'';
  document.getElementById('gf2_session_minutes_normal').value=g.session_minutes_normal||'';
  document.getElementById('gf2_hours_in_person_auto').value=g.hours_in_person_auto||'';
  document.getElementById('gf2_hours_online_only').value=g.hours_online_only||'';
  document.getElementById('gf2_hours_all_online').value=g.hours_all_online||'';
  document.getElementById('gf2_total_required_hours').value=g.total_required_hours||'';
  document.getElementById('groupModal2').classList.add('open');
}
function closeGroupModal2(){document.getElementById('groupModal2').classList.remove('open');}
function saveGroup2(){
  var editId=document.getElementById('groupEditId2').value;
  var bd={
    group_name:document.getElementById('gf2_group_name').value.trim(),
    teacher_name:document.getElementById('gf2_teacher_name').value.trim(),
    level_course:document.getElementById('gf2_level_course').value.trim(),
    last_reached:document.getElementById('gf2_last_reached').value.trim(),
    study_time:document.getElementById('gf2_study_time').value.trim(),
    ramadan_time:document.getElementById('gf2_ramadan_time').value.trim(),
    online_time:document.getElementById('gf2_online_time').value.trim(),
    group_link:document.getElementById('gf2_group_link').value.trim(),
    session_duration:document.getElementById('gf2_session_duration').value.trim(),
    session_minutes_normal:document.getElementById('gf2_session_minutes_normal').value.trim(),
    hours_in_person_auto:document.getElementById('gf2_hours_in_person_auto').value.trim(),
    hours_online_only:document.getElementById('gf2_hours_online_only').value.trim(),
    hours_all_online:document.getElementById('gf2_hours_all_online').value.trim(),
    total_required_hours:document.getElementById('gf2_total_required_hours').value.trim()
  };
  if(!bd.group_name){showToast('&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x645;&#x637;&#x644;&#x648;&#x628;','#e53935');return;}
  var url=editId?'/api/groups/'+editId:'/api/groups';
  var method=editId?'PUT':'POST';
  fetch(url,{method:method,headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(bd)}).then(function(r){return r.json();}).then(function(data){
    if(data.ok){closeGroupModal2();showToast(editId?'&#x62A;&#x645; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;':'&#x62A;&#x645; &#x625;&#x636;&#x627;&#x641;&#x629; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;','#00BCD4');loadGroups2();}
    else{showToast(data.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');}
  }).catch(function(){showToast('&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');});
}
function cleanupEmptyGroups(){
  if(!confirm('\u0647\u0644 \u062A\u0631\u064A\u062F \u062D\u0630\u0641 \u062C\u0645\u064A\u0639 \u0627\u0644\u0635\u0641\u0648\u0641 \u0627\u0644\u0641\u0627\u0631\u063A\u0629\u061F')) return;
  fetch('/api/groups/cleanup-empty',{method:'POST',credentials:'include'})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){showToast('\u062A\u0645 \u062D\u0630\u0641 ' + (d.deleted||0) + ' \u0635\u0641 \u0641\u0627\u0631\u063A','#00BCD4');loadGroups2();}
      else{showToast(d.error||'\u062D\u062F\u062B \u062E\u0637\u0623','#e53935');}
    }).catch(function(){showToast('\u062D\u062F\u062B \u062E\u0637\u0623','#e53935');});
}
function askGroupDelete2(id){groupDeleteTargetId2=id;document.getElementById('groupConfirmModal2').classList.add('open');document.getElementById('groupConfirmDelBtn2').onclick=confirmGroupDelete2;}
function confirmGroupDelete2(){
  if(!groupDeleteTargetId2)return;
  fetch('/api/groups/'+groupDeleteTargetId2,{method:'DELETE',credentials:'include'}).then(function(r){return r.json();}).then(function(data){
    closeGroupConfirm2();
    if(data.ok){showToast('&#x62A;&#x645; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;','#00BCD4');loadGroups2();}
    else{showToast(data.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');}
    groupDeleteTargetId2=null;
  }).catch(function(){closeGroupConfirm2();});
}
function closeGroupConfirm2(){document.getElementById('groupConfirmModal2').classList.remove('open');}
// --- Universal Table Edit Modal ---
// Shared edit-table modal used by every table (built-in + custom).
// Renders a per-column row with: label | type selector | options (if dropdown)
// | rename button | delete button. Plus an "add column" form at the bottom
// and a table-rename input at the top.

var _utemTableKey = null;
var _utemColumns = [];
var _utemEditingKey = null;

var _UTEM_LOADERS = {
  students: 'loadStudents',
  groups: 'loadGroups2', student_groups: 'loadGroups2',
  taqseet: 'loadTaqseet',
  attendance: 'loadAttendance',
  evaluations: 'loadEvaluations', evals: 'loadEvaluations',
  payment_log: 'loadPaymentLog', paylog: 'loadPaymentLog'
};
function _utemReload(){ var fn = window[_UTEM_LOADERS[_utemTableKey]]; if(typeof fn === 'function') fn(); }

var UTEM_TYPES = ['\u0646\u0635','\u0631\u0642\u0645','\u062a\u0627\u0631\u064a\u062e','\u0642\u0627\u0626\u0645\u0629 \u0645\u0646\u0633\u062f\u0644\u0629','\u0646\u0639\u0645/\u0644\u0627','\u062a\u0642\u064a\u064a\u0645'];

function _utemTypeOptions(selected){
  var html = '';
  for (var i=0;i<UTEM_TYPES.length;i++){
    var t = UTEM_TYPES[i];
    var sel = (t === selected) ? ' selected' : '';
    html += '<option value="' + t + '"' + sel + '>' + t + '</option>';
  }
  return html;
}

function openUniversalTableEditModal(tableKey){
  _utemTableKey = tableKey;
  _utemEditingKey = null;
  fetch('/api/custom-table/' + encodeURIComponent(tableKey) + '/columns', {credentials:'include'})
    .then(function(r){return r.json();})
    .then(function(d){
      if(!d.ok){ showToast(d.error || '\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); return; }
      _utemColumns = d.columns || [];
      document.getElementById('utemTableName').value = d.db_table || tableKey;
      _utemRenderColumns();
      document.getElementById('utemNewColType').innerHTML = _utemTypeOptions('\u0646\u0635');
      _utemToggleNewOptionsArea();
      document.getElementById('universalTableEditModal').classList.add('open');
    })
    .catch(function(){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); });
}
function utemClose(){ document.getElementById('universalTableEditModal').classList.remove('open'); }
function _esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;'); }
function _utemRenderColumns(){
  var body = document.getElementById('utemColumnsBody');
  if(!_utemColumns.length){ body.innerHTML = '<div style="padding:20px;text-align:center;color:#999;">لا توجد أعمدة</div>'; return; }
  var html = '';
  for(var i=0;i<_utemColumns.length;i++){
    var c = _utemColumns[i];
    var key = c.col_key;
    var lbl = c.col_label;
    var tp  = c.col_type || 'نص';
    var opts = c.col_options || '';
    var keyAttr = _esc(key);
    if (_utemEditingKey === key) {
      html += '<div class="utem-col-row" data-key="' + keyAttr + '">' +
        '<input class="utem-col-input" id="utemRenameInput_' + keyAttr + '" value="' + _esc(lbl) + '"/>' +
        '<button class="utem-col-btn ok" data-utem-action="commit" data-col-key="' + keyAttr + '">&#x2713;</button>' +
        '<button class="utem-col-btn cancel" data-utem-action="cancel">&#x2715;</button>' +
      '</div>';
    } else {
      var optsHtml = '';
      if (tp === 'قائمة منسدلة') {
        optsHtml = '<input class="utem-col-opts" id="utemOpts_' + keyAttr + '" data-col-key="' + keyAttr + '" placeholder="خيارات مفصولة بفاصلة مثال: نعم,لا,ربما" value="' + _esc(opts) + '" data-utem-action="save-type-blur" style="max-width:180px;padding:5px 8px;border:1.2px solid #ddd;border-radius:6px;font-size:12px;" />';
      }
      html += '<div class="utem-col-row" data-key="' + keyAttr + '">' +
        '<span class="utem-col-label">' + _esc(lbl) + '</span>' +
        '<select class="utem-col-type" id="utemType_' + keyAttr + '" data-col-key="' + keyAttr + '" data-utem-action="save-type" style="padding:5px 8px;border-radius:6px;border:1.2px solid #ddd;font-size:12px;">' + _utemTypeOptions(tp) + '</select>' +
        optsHtml +
        '<button class="utem-col-btn" title="إعادة تسمية" data-utem-action="start-rename" data-col-key="' + keyAttr + '">&#x270F;</button>' +
        '<button class="utem-col-btn del" title="حذف" data-utem-action="delete" data-col-key="' + keyAttr + '" data-col-label="' + _esc(lbl) + '">&#x1F5D1;</button>' +
      '</div>';
    }
  }
  body.innerHTML = html;
  _utemWireBodyDelegation();
  if (_utemEditingKey) {
    var el = document.getElementById('utemRenameInput_' + _utemEditingKey);
    if (el) { el.focus(); el.select(); }
  }
}

function _utemWireBodyDelegation(){
  var body = document.getElementById('utemColumnsBody');
  if (!body || body._utemWired) return;
  body._utemWired = true;
  body.addEventListener('click', function(ev){
    var t = ev.target.closest('[data-utem-action]');
    if (!t || t.tagName === 'SELECT' || t.tagName === 'INPUT') return;
    var action = t.getAttribute('data-utem-action');
    var key = t.getAttribute('data-col-key') || '';
    if (action === 'start-rename') { _utemStartRename(key); }
    else if (action === 'cancel')  { _utemCancelRename(); }
    else if (action === 'commit')  { _utemCommitRename(key); }
    else if (action === 'delete')  {
      var label = t.getAttribute('data-col-label') || key;
      _utemDeleteColumn(key, label);
    }
  });
  body.addEventListener('change', function(ev){
    var t = ev.target;
    if (!t || t.tagName !== 'SELECT') return;
    var action = t.getAttribute('data-utem-action');
    if (action === 'save-type') {
      var key = t.getAttribute('data-col-key') || '';
      _utemSaveType(key);
    }
  });
  body.addEventListener('blur', function(ev){
    var t = ev.target;
    if (!t || t.tagName !== 'INPUT') return;
    var action = t.getAttribute('data-utem-action');
    if (action === 'save-type-blur') {
      var key = t.getAttribute('data-col-key') || '';
      _utemSaveType(key);
    }
  }, true);
}

function _utemStartRename(key){ _utemEditingKey = key; _utemRenderColumns(); }
function _utemCancelRename(){ _utemEditingKey = null; _utemRenderColumns(); }
function _utemCommitRename(key){
  var inp = document.getElementById('utemRenameInput_' + key);
  if(!inp) return;
  var newLabel = inp.value.trim();
  if(!newLabel){ showToast('\u0627\u0644\u0627\u0633\u0645 \u0645\u0637\u0644\u0648\u0628','#e53935'); return; }
  fetch('/api/custom-table/' + encodeURIComponent(_utemTableKey) + '/rename-column', {
    method:'PATCH', headers:{'Content-Type':'application/json'}, credentials:'include',
    body: JSON.stringify({old_name: key, new_label: newLabel})
  }).then(function(r){return r.json();}).then(function(d){
    if(d.ok){ _utemEditingKey = null; showToast('\u062a\u0645 \u0627\u0644\u062a\u0639\u062f\u064a\u0644','#1976D2'); openUniversalTableEditModal(_utemTableKey); _utemReload(); }
    else { showToast(d.error || '\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
  }).catch(function(){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); });
}
function _utemDeleteColumn(key, label){
  label = label || key;
  function doDelete(){
    fetch('/api/custom-table/' + encodeURIComponent(_utemTableKey) + '/delete-column/' + encodeURIComponent(key), {
      method:'DELETE', credentials:'include'
    }).then(function(r){return r.json();}).then(function(d){
      if(d.ok){
        if (typeof window.mxToast === 'function') window.mxToast('تم حذف العمود: ' + label, 'success');
        else showToast('تم الحذف','#e53935');
        openUniversalTableEditModal(_utemTableKey);
        _utemReload();
      } else {
        if (typeof window.mxToast === 'function') window.mxToast(d.error || 'حدث خطأ', 'error');
        else showToast(d.error || 'حدث خطأ','#e53935');
      }
    }).catch(function(){ showToast('حدث خطأ','#e53935'); });
  }
  if (typeof window.mxConfirm === 'function') {
    window.mxConfirm({
      title: 'تأكيد حذف العمود',
      message: 'هل تريد حذف العمود "' + label + '"؟ سيتم حذف جميع البيانات في هذا العمود ولا يمكن التراجع عن هذا الإجراء.',
      yesText: 'نعم، احذف',
      noText:  'إلغاء'
    }, doDelete);
  } else {
    if (!confirm('هل أنت متأكد؟ سيتم حذف جميع البيانات في عمود "' + label + '"')) return;
    doDelete();
  }
}
function _utemSaveType(key){
  var selEl = document.getElementById('utemType_' + key);
  var optEl = document.getElementById('utemOpts_' + key);
  var tp = selEl ? selEl.value : '\u0646\u0635';
  var opts = optEl ? optEl.value : '';
  fetch('/api/custom-table/' + encodeURIComponent(_utemTableKey) + '/column-type', {
    method:'PATCH', headers:{'Content-Type':'application/json'}, credentials:'include',
    body: JSON.stringify({col_key: key, col_type: tp, col_options: opts})
  }).then(function(r){return r.json();}).then(function(d){
    if(d.ok){ openUniversalTableEditModal(_utemTableKey); _utemReload(); }
    else { showToast(d.error || '\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
  });
}
function _utemToggleNewOptionsArea(){
  var tp = document.getElementById('utemNewColType').value;
  var area = document.getElementById('utemNewOptsWrap');
  if (area) area.style.display = (tp === '\u0642\u0627\u0626\u0645\u0629 \u0645\u0646\u0633\u062f\u0644\u0629') ? 'block' : 'none';
}
function utemAddColumn(){
  var lblEl = document.getElementById('utemNewColLabel');
  var tpEl  = document.getElementById('utemNewColType');
  var optsEl= document.getElementById('utemNewColOpts');
  var label = lblEl.value.trim();
  if(!label){ showToast('\u0627\u0644\u0627\u0633\u0645 \u0645\u0637\u0644\u0648\u0628','#e53935'); return; }
  var tp = tpEl.value || '\u0646\u0635';
  var opts = optsEl ? optsEl.value.trim() : '';
  fetch('/api/custom-table/' + encodeURIComponent(_utemTableKey) + '/add-column', {
    method:'POST', headers:{'Content-Type':'application/json'}, credentials:'include',
    body: JSON.stringify({col_label: label, col_type: tp, col_options: opts})
  }).then(function(r){return r.json();}).then(function(d){
    if(d.ok){ lblEl.value=''; if(optsEl) optsEl.value=''; tpEl.value='\u0646\u0635'; _utemToggleNewOptionsArea();
              showToast('\u062a\u0645\u062a \u0627\u0644\u0625\u0636\u0627\u0641\u0629','#00897B'); openUniversalTableEditModal(_utemTableKey); _utemReload(); }
    else { showToast(d.error || '\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
  }).catch(function(){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); });
}
function utemSave(){
  var nm = document.getElementById('utemTableName').value.trim();
  if(!nm){ utemClose(); return; }
  fetch('/api/custom-table/' + encodeURIComponent(_utemTableKey) + '/rename', {
    method:'PATCH', headers:{'Content-Type':'application/json'}, credentials:'include',
    body: JSON.stringify({new_label: nm, new_name: nm})
  }).then(function(r){return r.json();}).then(function(d){
    utemClose(); showToast('\u062a\u0645 \u0627\u0644\u062d\u0641\u0638','#1976D2'); _utemReload();
  }).catch(function(){ utemClose(); });
}

// ─── Typed cell rendering (Part 3) ─────────────────────────────────────
// Used by future custom-table renders; exposed globally so any table may opt in.
function renderCell(value, colType, colOptions, rowId, fieldKey) {
  var v = (value == null) ? '' : String(value);
  var esc = _esc(v);
  var type = colType || '\u0646\u0635';
  var idAttr = rowId != null ? (' data-id="' + rowId + '"') : '';
  var fAttr  = fieldKey ? (' data-field="' + fieldKey + '"') : '';
  var base = idAttr + fAttr + ' class="cell-input"';
  switch (type) {
    case '\u0631\u0642\u0645':
      return '<input type="number" value="' + esc + '"' + base + '>';
    case '\u062a\u0627\u0631\u064a\u062e':
      return '<input type="date" value="' + esc + '"' + base + '>';
    case '\u0642\u0627\u0626\u0645\u0629 \u0645\u0646\u0633\u062f\u0644\u0629':
      var opts = String(colOptions||'').split(',').map(function(o){return o.trim();}).filter(function(o){return o.length;});
      var html = '<select' + base + '><option value=""></option>';
      for (var i=0;i<opts.length;i++){ var s = (opts[i] === v) ? ' selected' : ''; html += '<option' + s + '>' + _esc(opts[i]) + '</option>'; }
      return html + '</select>';
    case '\u0646\u0639\u0645/\u0644\u0627':
      var ch = (v === '1' || v === 'true' || v === '\u0646\u0639\u0645') ? ' checked' : '';
      return '<input type="checkbox"' + ch + base + '>';
    case '\u062a\u0642\u064a\u064a\u0645':
      return '<input type="number" min="1" max="10" value="' + esc + '"' + base + '>';
    default:
      return '<input type="text" value="' + esc + '"' + base + '>';
  }
}

// ─── Shared toolbar (Part 1) ───────────────────────────────────────────
// Produces the canonical 6-button toolbar HTML for any table. Future tables
// (custom or built-in) just need to have their container-id populated via
// renderToolbar(tableKey, containerId, opts).
// opts: { addRowFn, tbodyId, refreshFn, deleteMsg, extraButtons }
function renderToolbar(tableKey, containerId, opts) {
  opts = opts || {};
  var c = document.getElementById(containerId);
  if (!c) return;
  var addFn = opts.addRowFn;
  if (!addFn) {
    var defaultAdd = { students:'openAddModal', groups:'openAddGroupModal2', student_groups:'openAddGroupModal2',
                       taqseet:'openAddTaqseet', attendance:'openAttendanceAddModal',
                       evaluations:'openAddEvalModal', evals:'openAddEvalModal',
                       payment_log:'openAddPaylogModal', paylog:'openAddPaylogModal' };
    addFn = defaultAdd[tableKey] || 'openUniversalAddRow';
  }
  var tbodyId = opts.tbodyId || (
    { students:'studentsBody', groups:'groupsBody2', student_groups:'groupsBody2',
      taqseet:'taqseetBody', attendance:'attendanceBody',
      evaluations:'evalsBody', evals:'evalsBody',
      payment_log:'paylogBody', paylog:'paylogBody' }[tableKey] || (tableKey + 'Body')
  );
  var refreshFn = opts.refreshFn || _UTEM_LOADERS[tableKey] || ('load_' + tableKey);
  var delMsg = opts.deleteMsg || '\u0647\u0644 \u062a\u0631\u064a\u062f \u062d\u0630\u0641 {n} \u0639\u0646\u0635\u0631\u061f';
  var html = ''
    + '<div style="display:flex;gap:10px;align-items:center;margin-bottom:20px;flex-wrap:wrap;">'
    + '<button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1976D2,#42A5F5);" onclick="'+addFn+'()">&#x2795; \u0625\u0636\u0627\u0641\u0629 \u0635\u0641</button>'
    + '<button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openUniversalTableEditModal(\\'+tableKey+\\')">&#9881; \u062a\u0639\u062f\u064a\u0644 \u0627\u0644\u062c\u062f\u0648\u0644</button>'
    + '<button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#3F51B5,#5C6BC0);" onclick="openGenericExcelModal(\\'+tableKey+\\')">&#x1F4E5; \u0627\u0633\u062a\u064a\u0631\u0627\u062f Excel</button>'
    + '<button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#c0392b,#e74c3c);" onclick="openDeleteTableModal()">&#x1F5D1; \u062d\u0630\u0641 \u0627\u0644\u062c\u062f\u0648\u0644</button>'
    + '<button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal(\\'+tableKey+\\')">&#x1F4CC; \u062a\u062c\u0645\u064a\u062f</button>'
    + '<button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00897B,#26A69A);" onclick="utemFocusSearch(\\'+tableKey+\\')">&#x1F50D; \u0628\u062d\u062b</button>'
    + '<button id="bulkDelBtn_'+tableKey+'" class="btn-bulk-del" onclick="_bulkDelete(\\'+tbodyId+\\',function(id){return \\'/api/'+tableKey+'/\\'+id;},'+refreshFn+',\\'+delMsg+\\')">&#x1F5D1; \u062d\u0630\u0641 \u0627\u0644\u0645\u062d\u062f\u062f</button>'
    + (opts.extraButtons || '')
    + '</div>';
  c.innerHTML = html;
}

// Search-button helper: focus the table's search input.
function utemFocusSearch(tableKey){
  var ids = {students:'searchInput', groups:'groupSearchInput', student_groups:'groupSearchInput',
             taqseet:null, attendance:'attendanceSearchInput',
             evaluations:'evalsSearchInput', evals:'evalsSearchInput',
             payment_log:'paylogSearchInput', paylog:'paylogSearchInput'};
  var id = ids[tableKey];
  if(id){ var el = document.getElementById(id); if(el){ el.focus(); el.scrollIntoView({behavior:'smooth',block:'center'}); } }
}

var studentExcelData=[];function openStudentExcelModal(){studentExcelData=[];document.getElementById("studentExcelFile").value="";document.getElementById("studentExcelFileName").textContent="&#x644;&#x645; &#x64A;&#x62A;&#x645; &#x627;&#x62E;&#x62A;&#x64A;&#x627;&#x631; &#x645;&#x644;&#x641;";document.getElementById("studentExcelPreview").style.display="none";document.getElementById("studentExcelImportBtn").style.display="none";document.getElementById("studentExcelModal").classList.add("open");}function closeStudentExcelModal(){document.getElementById("studentExcelModal").classList.remove("open");}document.addEventListener("DOMContentLoaded",function(){var sf=document.getElementById("studentExcelFile");if(sf){sf.addEventListener("change",function(e){var file=e.target.files[0];if(!file)return;document.getElementById("studentExcelFileName").textContent=file.name;var reader=new FileReader();reader.onload=function(ev){var data=ev.target.result;var rows=data.split(String.fromCharCode(10)).filter(function(r){return r.trim()!="";});if(rows.length<2){showToast("&#x627;&#x644;&#x645;&#x644;&#x641; &#x641;&#x627;&#x631;&#x63A;","#e53935");return;}var sep=rows[0].indexOf(String.fromCharCode(9))>-1?"\t":",",parsed=[];for(var i=1;i<rows.length;i++){var cols=rows[i].split(sep);if(cols.length<2)continue;parsed.push({personal_id:(cols[0]||"").trim(),student_name:(cols[1]||"").trim(),whatsapp:(cols[2]||"").trim(),final_result:(cols[3]||"").trim(),level_reached_2026:(cols[4]||"").trim(),teacher_2026:(cols[5]||"").trim(),mother_phone:(cols[6]||"").trim(),father_phone:(cols[7]||"").trim(),other_phone:(cols[8]||"").trim(),residence:(cols[9]||"").trim(),home_address:(cols[10]||"").trim(),road:(cols[11]||"").trim(),complex_name:(cols[12]||"").trim()});}studentExcelData=parsed;document.getElementById("studentExcelCount").textContent="&#x62A;&#x645; &#x642;&#x631;&#x627;&#x621;&#x629; "+parsed.length+" &#x637;&#x627;&#x644;&#x628;. &#x627;&#x636;&#x63A;&#x637; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;.";document.getElementById("studentExcelPreview").style.display="block";document.getElementById("studentExcelImportBtn").style.display="inline-block";};reader.readAsText(file,"UTF-8");});}var gf=document.getElementById("groupExcelFile");if(gf){gf.addEventListener("change",function(e){var file=e.target.files[0];if(!file)return;document.getElementById("groupExcelFileName").textContent=file.name;var reader=new FileReader();reader.onload=function(ev){var data=ev.target.result;var rows=data.split(String.fromCharCode(10)).filter(function(r){return r.trim()!="";});if(rows.length<2){showToast("&#x627;&#x644;&#x645;&#x644;&#x641; &#x641;&#x627;&#x631;&#x63A;","#e53935");return;}var sep=rows[0].indexOf(String.fromCharCode(9))>-1?"\t":",",parsed=[];for(var i=1;i<rows.length;i++){var cols=rows[i].split(sep);if(cols.length<2)continue;parsed.push({group_name:(cols[0]||"").trim(),teacher_name:(cols[1]||"").trim(),level_course:(cols[2]||"").trim(),last_reached:(cols[3]||"").trim(),study_time:(cols[4]||"").trim(),ramadan_time:(cols[5]||"").trim(),online_time:(cols[6]||"").trim(),group_link:(cols[7]||"").trim(),session_duration:(cols[8]||"").trim()});}groupExcelData=parsed;document.getElementById("groupExcelCount").textContent="&#x62A;&#x645; &#x642;&#x631;&#x627;&#x621;&#x629; "+parsed.length+" &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;. &#x627;&#x636;&#x63A;&#x637; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;.";document.getElementById("groupExcelPreview").style.display="block";document.getElementById("groupExcelImportBtn").style.display="inline-block";};reader.readAsText(file,"UTF-8");});}});function importStudentsFromExcel(){if(!studentExcelData.length){showToast("&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;","#e53935");return;}var btn=document.getElementById("studentExcelImportBtn");btn.disabled=true;btn.textContent="&#x62C;&#x627;&#x631;&#x64A; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;...";fetch("/api/students/bulk",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({rows:studentExcelData})}).then(function(r){return r.text();}).then(function(txt){var data;try{data=JSON.parse(txt);}catch(e){showToast("&#x627;&#x646;&#x62A;&#x647;&#x62A; &#x627;&#x644;&#x62C;&#x644;&#x633;&#x629;&#x60C; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x62E;&#x648;&#x644; &#x645;&#x62C;&#x62F;&#x62F;&#x627;","#e53935");btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";return;}if(data.ok){closeStudentExcelModal();showToast("&#x62A;&#x645; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; "+data.imported+" &#x637;&#x627;&#x644;&#x628; &#x628;&#x646;&#x62C;&#x627;&#x62D;");loadStudents();}else{showToast("&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;","#e53935");}btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";}).catch(function(){showToast("&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627; &#x641;&#x64A; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;","#e53935");btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";});}var groupExcelData=[];function openGroupExcelModal(){groupExcelData=[];document.getElementById("groupExcelFile").value="";document.getElementById("groupExcelFileName").textContent="&#x644;&#x645; &#x64A;&#x62A;&#x645; &#x627;&#x62E;&#x62A;&#x64A;&#x627;&#x631; &#x645;&#x644;&#x641;";document.getElementById("groupExcelPreview").style.display="none";document.getElementById("groupExcelImportBtn").style.display="none";document.getElementById("groupExcelModal").classList.add("open");}function closeGroupExcelModal(){document.getElementById("groupExcelModal").classList.remove("open");}function importGroupsFromExcel(){if(!groupExcelData.length){showToast("&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;","#e53935");return;}var btn=document.getElementById("groupExcelImportBtn");btn.disabled=true;btn.textContent="&#x62C;&#x627;&#x631;&#x64A; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;...";fetch("/api/groups/bulk",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({rows:groupExcelData})}).then(function(r){return r.text();}).then(function(txt){var data;try{data=JSON.parse(txt);}catch(e){showToast("&#x627;&#x646;&#x62A;&#x647;&#x62A; &#x627;&#x644;&#x62C;&#x644;&#x633;&#x629;&#x60C; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x62E;&#x648;&#x644; &#x645;&#x62C;&#x62F;&#x62F;&#x627;","#e53935");btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";return;}if(data.ok){closeGroupExcelModal();showToast("&#x62A;&#x645; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; "+data.imported+" &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x628;&#x646;&#x62C;&#x627;&#x62D;","#00BCD4");loadGroups2();}else{showToast("&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;","#e53935");}btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";}).catch(function(){showToast("&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627; &#x641;&#x64A; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;","#e53935");btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";});}
loadGroups2();

// --- Evaluations (\u0627\u0644\u062a\u0642\u064a\u064a\u0645\u0627\u062a) ---
var allEvals = [];
var allEvalColumns = [];
function loadEvaluations() {
  Promise.all([
    fetch('/api/evaluations',{credentials:'include'}).then(function(r){return r.json();}),
    fetch('/api/eval-columns',{credentials:'include'}).then(function(r){return r.json();})
  ]).then(function(res){
    allEvals = res[0].rows || [];
    allEvalColumns = res[1].columns || [];
    buildEvalsHeader();
    renderEvalsTable(allEvals);
    var c = document.getElementById('evalsTotalCount'); if(c) c.textContent = allEvals.length;
    applyFreezeToTable('evals');
  }).catch(function(){});
}
function buildEvalsHeader(){
  var thead = document.getElementById('evalsTheadRow');
  if(!thead) return;
  var html = '<th class="bulk-col"><input type="checkbox" id="selectAll_evals" class="bulk-cb" onclick="_bulkSelectAll(\\'evalsBody\\',\\'selectAll_evals\\',\\'bulkDelBtn_evals\\',this.checked)"></th><th>#</th>';
  for(var i=0;i<allEvalColumns.length;i++){ html += '<th>'+allEvalColumns[i].col_label+'</th>'; }
  html += '<th>\u0625\u062c\u0631\u0627\u0621\u0627\u062a</th>';
  thead.innerHTML = html;
}
function renderEvalsTable(list){
  var body = document.getElementById('evalsBody'); if(!body) return;
  var colCount = allEvalColumns.length + 3;
  if(!list || !list.length){
    body.innerHTML = '<tr><td colspan="'+colCount+'" class="no-data">\u0644\u0627 \u062a\u0648\u062c\u062f \u062a\u0642\u064a\u064a\u0645\u0627\u062a</td></tr>';
    _bulkUpdate('evalsBody','selectAll_evals','bulkDelBtn_evals');
    applyFreezeToTable('evals');
    return;
  }
  var html = '';
  for(var i=0;i<list.length;i++){
    var r = list[i];
    html += '<tr><td class="bulk-col"><input type="checkbox" class="bulk-cb" data-id="'+r.id+'" onclick="_bulkUpdate(\\'evalsBody\\',\\'selectAll_evals\\',\\'bulkDelBtn_evals\\')"></td><td>'+(i+1)+'</td>';
    for(var j=0;j<allEvalColumns.length;j++){
      var key = allEvalColumns[j].col_key;
      var val = r[key];
      if(key==='student_name'){ html += '<td style="font-weight:600;color:#1565C0;text-align:right;">'+(val||'-')+'</td>'; }
      else { html += '<td>'+(val==null||val===''?'-':val)+'</td>'; }
    }
    html += '<td><button class="action-btn btn-edit" style="color:#1565C0;" onclick="openEvalEdit('+r.id+')">\u062a\u0639\u062f\u064a\u0644</button><button class="action-btn btn-del" onclick="askEvalDelete('+r.id+')">\u062d\u0630\u0641</button></td></tr>';
  }
  body.innerHTML = html;
  applyFreezeToTable('evals');
}
function filterEvalsTable(){
  var q = (document.getElementById('evalsSearchInput').value || '').toLowerCase();
  if(!q){ renderEvalsTable(allEvals); return; }
  renderEvalsTable(allEvals.filter(function(r){
    return (String(r.student_name||'').toLowerCase().indexOf(q) > -1) ||
           (String(r.group_name||'').toLowerCase().indexOf(q) > -1);
  }));
}
var EV_IDS = ['form_fill_date','group_name','student_name','class_participation','general_behavior','behavior_notes','reading','dictation','term_meanings','conversation','expression','grammar','notes'];
function evClearForm(){
  for(var i=0;i<EV_IDS.length;i++){ var el=document.getElementById('ev_'+EV_IDS[i]); if(el) el.value=''; }
  document.getElementById('evalEditId').value = '';
}
function openAddEvalModal(){ evClearForm(); document.getElementById('evalModalTitle').textContent='\u1f4dd \u0625\u0636\u0627\u0641\u0629 \u062a\u0642\u064a\u064a\u0645'; document.getElementById('evalModal').classList.add('open'); }
function openEvalEdit(id){
  var r = null;
  for(var i=0;i<allEvals.length;i++){ if(allEvals[i].id===id){ r = allEvals[i]; break; } }
  if(!r) return;
  document.getElementById('evalEditId').value = id;
  document.getElementById('evalModalTitle').textContent = '\u270e \u062a\u0639\u062f\u064a\u0644 \u062a\u0642\u064a\u064a\u0645';
  for(var i=0;i<EV_IDS.length;i++){ var el=document.getElementById('ev_'+EV_IDS[i]); if(el) el.value = r[EV_IDS[i]] || ''; }
  document.getElementById('evalModal').classList.add('open');
}
function closeEvalModal(){ document.getElementById('evalModal').classList.remove('open'); }
function saveEval(){
  var editId = document.getElementById('evalEditId').value;
  var body = {};
  for(var i=0;i<EV_IDS.length;i++){ var el=document.getElementById('ev_'+EV_IDS[i]); if(el) body[EV_IDS[i]] = el.value.trim(); }
  if(!body.student_name){ showToast('\u0627\u0644\u0627\u0633\u0645 \u0645\u0637\u0644\u0648\u0628','#e53935'); return; }
  var url = editId ? '/api/evaluations/'+editId : '/api/evaluations';
  var method = editId ? 'PUT' : 'POST';
  fetch(url,{method:method,headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(body)})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closeEvalModal(); showToast(editId?'\u062a\u0645 \u062a\u0639\u062f\u064a\u0644 \u0627\u0644\u0633\u062c\u0644':'\u062a\u0645 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0633\u062c\u0644','#1976D2'); loadEvaluations(); }
      else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
    }).catch(function(){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); });
}
function askEvalDelete(id){
  if(!confirm('\u0647\u0644 \u062a\u0631\u064a\u062f \u062d\u0630\u0641 \u0647\u0630\u0627 \u0627\u0644\u0633\u062c\u0644\u061f')) return;
  fetch('/api/evaluations/'+id,{method:'DELETE',credentials:'include'}).then(function(r){return r.json();}).then(function(d){
    if(d.ok){ showToast('\u062a\u0645 \u0627\u0644\u062d\u0630\u0641','#e53935'); loadEvaluations(); }
    else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
  });
}
// ---- Evaluations column management ----
function openEvalTableEditModal(){
  var delSel = document.getElementById('ev_del_col_key');
  var editSel = document.getElementById('ev_edit_col_key');
  var afterSel = document.getElementById('ev_new_col_after');
  delSel.innerHTML = '<option value=""></option>';
  editSel.innerHTML = '<option value=""></option>';
  afterSel.innerHTML = '<option value=""></option>';
  for(var i=0;i<allEvalColumns.length;i++){
    var c = allEvalColumns[i];
    delSel.innerHTML  += '<option value="'+c.col_key+'">'+c.col_label+'</option>';
    editSel.innerHTML += '<option value="'+c.col_key+'">'+c.col_label+'</option>';
    afterSel.innerHTML+= '<option value="'+c.col_key+'">'+c.col_label+'</option>';
  }
  document.getElementById('ev_new_col_label').value = '';
  document.getElementById('ev_new_col_position').value = 'end';
  toggleEvalPositionCol();
  switchEvalTab('add-col');
  document.getElementById('evalTableEditModal').classList.add('open');
}
function closeEvalTableEditModal(){ document.getElementById('evalTableEditModal').classList.remove('open'); }
function switchEvalTab(tab){
  var tabs = ['add-col','del-col','edit-col'];
  for(var i=0;i<tabs.length;i++){
    var b = document.getElementById('evtab-'+tabs[i]);
    var p = document.getElementById('evpanel-'+tabs[i]);
    if(tabs[i]===tab){ if(b){ b.style.background='#FF6B35'; b.style.color='#fff'; } if(p) p.style.display='block'; }
    else { if(b){ b.style.background='#e3f2fd'; b.style.color='#1565C0'; } if(p) p.style.display='none'; }
  }
}
function toggleEvalPositionCol(){
  var pos = document.getElementById('ev_new_col_position').value;
  document.getElementById('ev_new_col_after').style.display = (pos==='after') ? 'inline-block' : 'none';
}
function fillEvalEditLabel(){
  var key = document.getElementById('ev_edit_col_key').value;
  var c = null;
  for(var i=0;i<allEvalColumns.length;i++){ if(allEvalColumns[i].col_key===key){ c = allEvalColumns[i]; break; } }
  document.getElementById('ev_edit_col_label').value = c ? c.col_label : '';
}
function addEvalColumn(){
  var label = document.getElementById('ev_new_col_label').value.trim();
  if(!label){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); return; }
  var key = label.replace(/\s+/g,'_').toLowerCase().replace(/[^a-z0-9_]/g,'');
  if(!/^[a-z_][a-z0-9_]*$/.test(key)){ key = 'col_' + Date.now(); }
  var position = document.getElementById('ev_new_col_position').value;
  var after_col = document.getElementById('ev_new_col_after').value;
  fetch('/api/eval-columns',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({col_key:key,col_label:label,position:position,after_col:after_col})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closeEvalTableEditModal(); showToast('\u062a\u0645 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0639\u0645\u0648\u062f','#1976D2'); loadEvaluations(); }
      else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
    });
}
function deleteEvalColumn(){
  var key = document.getElementById('ev_del_col_key').value;
  if(!key){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); return; }
  fetch('/api/eval-columns/'+encodeURIComponent(key),{method:'DELETE',credentials:'include'})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closeEvalTableEditModal(); showToast('\u062a\u0645 \u062d\u0630\u0641 \u0627\u0644\u0639\u0645\u0648\u062f','#e53935'); loadEvaluations(); }
      else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
    });
}
function updateEvalColumnLabel(){
  var key = document.getElementById('ev_edit_col_key').value;
  var label = document.getElementById('ev_edit_col_label').value.trim();
  if(!key || !label){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); return; }
  fetch('/api/eval-columns/'+encodeURIComponent(key),{method:'PUT',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({col_label:label})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closeEvalTableEditModal(); showToast('\u062a\u0645 \u062a\u0639\u062f\u064a\u0644 \u0627\u0644\u0639\u0646\u0648\u0627\u0646','#1976D2'); loadEvaluations(); }
      else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
    });
}
loadEvaluations();

// --- Payment Log (\u0633\u062c\u0644 \u0627\u0644\u062f\u0641\u0639) ---
var allPaylog = [];
var allPaylogColumns = [];
function loadPaymentLog() {
  Promise.all([
    fetch('/api/payment-log',{credentials:'include'}).then(function(r){return r.json();}),
    fetch('/api/paylog-columns',{credentials:'include'}).then(function(r){return r.json();})
  ]).then(function(res){
    allPaylog = res[0].rows || [];
    allPaylogColumns = res[1].columns || [];
    buildPaylogHeader();
    renderPaylogTable(allPaylog);
    var c = document.getElementById('paylogTotalCount'); if(c) c.textContent = allPaylog.length;
    applyFreezeToTable('paylog');
  }).catch(function(){});
}
function buildPaylogHeader(){
  var thead = document.getElementById('paylogTheadRow');
  if(!thead) return;
  var html = '<th class="bulk-col"><input type="checkbox" id="selectAll_paylog" class="bulk-cb" onclick="_bulkSelectAll(\\'paylogBody\\',\\'selectAll_paylog\\',\\'bulkDelBtn_paylog\\',this.checked)"></th><th>#</th>';
  for(var i=0;i<allPaylogColumns.length;i++){ html += '<th>'+allPaylogColumns[i].col_label+'</th>'; }
  html += '<th>\u0625\u062c\u0631\u0627\u0621\u0627\u062a</th>';
  thead.innerHTML = html;
}
function renderPaylogTable(list){
  var body = document.getElementById('paylogBody'); if(!body) return;
  var colCount = allPaylogColumns.length + 3;
  if(!list || !list.length){
    body.innerHTML = '<tr><td colspan="'+colCount+'" class="no-data">\u0644\u0627 \u062a\u0648\u062c\u062f \u0633\u062c\u0644\u0627\u062a \u062f\u0641\u0639</td></tr>';
    _bulkUpdate('paylogBody','selectAll_paylog','bulkDelBtn_paylog');
    applyFreezeToTable('paylog');
    return;
  }
  var html = '';
  for(var i=0;i<list.length;i++){
    var r = list[i];
    html += '<tr><td class="bulk-col"><input type="checkbox" class="bulk-cb" data-id="'+r.id+'" onclick="_bulkUpdate(\\'paylogBody\\',\\'selectAll_paylog\\',\\'bulkDelBtn_paylog\\')"></td><td>'+(i+1)+'</td>';
    for(var j=0;j<allPaylogColumns.length;j++){
      var key = allPaylogColumns[j].col_key;
      var val = r[key];
      if(key==='student_name'){ html += '<td style="font-weight:600;color:#00695C;text-align:right;">'+(val||'-')+'</td>'; }
      else { html += '<td>'+(val==null||val===''?'-':val)+'</td>'; }
    }
    html += '<td><button class="action-btn btn-edit" style="color:#00695C;" onclick="openPaylogEdit('+r.id+')">\u062a\u0639\u062f\u064a\u0644</button><button class="action-btn btn-del" onclick="askPaylogDelete('+r.id+')">\u062d\u0630\u0641</button></td></tr>';
  }
  body.innerHTML = html;
  applyFreezeToTable('paylog');
}
function filterPaylogTable(){
  var q = (document.getElementById('paylogSearchInput').value || '').toLowerCase();
  if(!q){ renderPaylogTable(allPaylog); return; }
  renderPaylogTable(allPaylog.filter(function(r){
    return String(r.student_name||'').toLowerCase().indexOf(q) > -1;
  }));
}
var PL_IDS = ['student_name','registration_status','course_amount','inst1','msg1','inst2','msg2','inst3','msg3','inst4','msg4','inst5','msg5','total_paid','total_remaining','payment_status'];
function plClearForm(){
  for(var i=0;i<PL_IDS.length;i++){ var el=document.getElementById('pl_'+PL_IDS[i]); if(el) el.value=''; }
  document.getElementById('paylogEditId').value = '';
}
function openAddPaylogModal(){ plClearForm(); document.getElementById('paylogModalTitle').textContent='\u1f4b0 \u0625\u0636\u0627\u0641\u0629 \u0633\u062c\u0644 \u062f\u0641\u0639'; document.getElementById('paylogModal').classList.add('open'); }
function openPaylogEdit(id){
  var r = null;
  for(var i=0;i<allPaylog.length;i++){ if(allPaylog[i].id===id){ r = allPaylog[i]; break; } }
  if(!r) return;
  document.getElementById('paylogEditId').value = id;
  document.getElementById('paylogModalTitle').textContent = '\u270e \u062a\u0639\u062f\u064a\u0644 \u0633\u062c\u0644 \u062f\u0641\u0639';
  for(var i=0;i<PL_IDS.length;i++){ var el=document.getElementById('pl_'+PL_IDS[i]); if(el) el.value = r[PL_IDS[i]] || ''; }
  document.getElementById('paylogModal').classList.add('open');
}
function closePaylogModal(){ document.getElementById('paylogModal').classList.remove('open'); }
function savePaylog(){
  var editId = document.getElementById('paylogEditId').value;
  var body = {};
  for(var i=0;i<PL_IDS.length;i++){ var el=document.getElementById('pl_'+PL_IDS[i]); if(el) body[PL_IDS[i]] = el.value.trim(); }
  if(!body.student_name){ showToast('\u0627\u0644\u0627\u0633\u0645 \u0645\u0637\u0644\u0648\u0628','#e53935'); return; }
  var url = editId ? '/api/payment-log/'+editId : '/api/payment-log';
  var method = editId ? 'PUT' : 'POST';
  fetch(url,{method:method,headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(body)})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closePaylogModal(); showToast(editId?'\u062a\u0645 \u062a\u0639\u062f\u064a\u0644 \u0627\u0644\u0633\u062c\u0644':'\u062a\u0645 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0633\u062c\u0644','#00897B'); loadPaymentLog(); }
      else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
    }).catch(function(){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); });
}
function askPaylogDelete(id){
  if(!confirm('\u0647\u0644 \u062a\u0631\u064a\u062f \u062d\u0630\u0641 \u0647\u0630\u0627 \u0627\u0644\u0633\u062c\u0644\u061f')) return;
  fetch('/api/payment-log/'+id,{method:'DELETE',credentials:'include'}).then(function(r){return r.json();}).then(function(d){
    if(d.ok){ showToast('\u062a\u0645 \u0627\u0644\u062d\u0630\u0641','#e53935'); loadPaymentLog(); }
    else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
  });
}
function openPaylogTableEditModal(){
  var delSel = document.getElementById('pl_del_col_key');
  var editSel = document.getElementById('pl_edit_col_key');
  var afterSel = document.getElementById('pl_new_col_after');
  delSel.innerHTML = '<option value=""></option>';
  editSel.innerHTML = '<option value=""></option>';
  afterSel.innerHTML = '<option value=""></option>';
  for(var i=0;i<allPaylogColumns.length;i++){
    var c = allPaylogColumns[i];
    delSel.innerHTML  += '<option value="'+c.col_key+'">'+c.col_label+'</option>';
    editSel.innerHTML += '<option value="'+c.col_key+'">'+c.col_label+'</option>';
    afterSel.innerHTML+= '<option value="'+c.col_key+'">'+c.col_label+'</option>';
  }
  document.getElementById('pl_new_col_label').value = '';
  document.getElementById('pl_new_col_position').value = 'end';
  togglePaylogPositionCol();
  switchPaylogTab('add-col');
  document.getElementById('paylogTableEditModal').classList.add('open');
}
function closePaylogTableEditModal(){ document.getElementById('paylogTableEditModal').classList.remove('open'); }
function switchPaylogTab(tab){
  var tabs = ['add-col','del-col','edit-col'];
  for(var i=0;i<tabs.length;i++){
    var b = document.getElementById('pltab-'+tabs[i]);
    var p = document.getElementById('plpanel-'+tabs[i]);
    if(tabs[i]===tab){ if(b){ b.style.background='#FF6B35'; b.style.color='#fff'; } if(p) p.style.display='block'; }
    else { if(b){ b.style.background='#e0f2f1'; b.style.color='#00695C'; } if(p) p.style.display='none'; }
  }
}
function togglePaylogPositionCol(){
  var pos = document.getElementById('pl_new_col_position').value;
  document.getElementById('pl_new_col_after').style.display = (pos==='after') ? 'inline-block' : 'none';
}
function fillPaylogEditLabel(){
  var key = document.getElementById('pl_edit_col_key').value;
  var c = null;
  for(var i=0;i<allPaylogColumns.length;i++){ if(allPaylogColumns[i].col_key===key){ c = allPaylogColumns[i]; break; } }
  document.getElementById('pl_edit_col_label').value = c ? c.col_label : '';
}
function addPaylogColumn(){
  var label = document.getElementById('pl_new_col_label').value.trim();
  if(!label){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); return; }
  var key = label.replace(/\s+/g,'_').toLowerCase().replace(/[^a-z0-9_]/g,'');
  if(!/^[a-z_][a-z0-9_]*$/.test(key)){ key = 'col_' + Date.now(); }
  var position = document.getElementById('pl_new_col_position').value;
  var after_col = document.getElementById('pl_new_col_after').value;
  fetch('/api/paylog-columns',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({col_key:key,col_label:label,position:position,after_col:after_col})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closePaylogTableEditModal(); showToast('\u062a\u0645 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0639\u0645\u0648\u062f','#00897B'); loadPaymentLog(); }
      else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
    });
}
function deletePaylogColumn(){
  var key = document.getElementById('pl_del_col_key').value;
  if(!key){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); return; }
  fetch('/api/paylog-columns/'+encodeURIComponent(key),{method:'DELETE',credentials:'include'})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closePaylogTableEditModal(); showToast('\u062a\u0645 \u062d\u0630\u0641 \u0627\u0644\u0639\u0645\u0648\u062f','#e53935'); loadPaymentLog(); }
      else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
    });
}
function updatePaylogColumnLabel(){
  var key = document.getElementById('pl_edit_col_key').value;
  var label = document.getElementById('pl_edit_col_label').value.trim();
  if(!key || !label){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); return; }
  fetch('/api/paylog-columns/'+encodeURIComponent(key),{method:'PUT',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({col_label:label})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closePaylogTableEditModal(); showToast('\u062a\u0645 \u062a\u0639\u062f\u064a\u0644 \u0627\u0644\u0639\u0646\u0648\u0627\u0646','#00897B'); loadPaymentLog(); }
      else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
    });
}
loadPaymentLog();



// \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
// DELETE TABLE MODAL FUNCTIONS
// \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
let _selectedDeleteTableId = null;
let _selectedDeleteTableName = null;

async function openDeleteTableModal() {
  _selectedDeleteTableId = null;
  _selectedDeleteTableName = null;
  window._selectedDeleteTableType = null;
  var listEl = document.getElementById('deleteTableList');
  listEl.innerHTML = '<p style="color:#888;text-align:center;padding:20px;">&#x062C;&#x0627;&#x0631; &#x0627;&#x0644;&#x062A;&#x062D;&#x0645;&#x064A;&#x0644;...</p>';
  document.body.appendChild(document.getElementById('deleteTableModal'));
  document.body.appendChild(document.getElementById('deleteTableConfirmModal'));
  document.getElementById('deleteTableModal').classList.add('open');
  try {
    var res = await fetch('/api/custom-tables');
    var customTables = await res.json();
    var allItems = [];
    var fixedDefs = [
      {domId: 'studentsBody', name: '&#x0642;&#x0627;&#x0639;&#x062F;&#x0629; &#x0628;&#x064A;&#x0627;&#x0646;&#x0627;&#x062A; &#x0627;&#x0644;&#x0637;&#x0644;&#x0628;&#x0629;'},
      {domId: 'groupsBody2', name: '&#x0645;&#x0639;&#x0644;&#x0648;&#x0645;&#x0627;&#x062A; &#x0627;&#x0644;&#x0645;&#x062C;&#x0645;&#x0648;&#x0639;&#x0627;&#x062A;'},
      {domId: 'taqseetTable', name: '&#x0637;&#x0631;&#x064A;&#x0642;&#x0629; &#x0627;&#x0644;&#x062A;&#x0642;&#x0633;&#x064A;&#x0637;'},
    ];
    for (var i = 0; i < fixedDefs.length; i++) {
      if (document.getElementById(fixedDefs[i].domId)) {
        allItems.push({id: 'fixed__' + fixedDefs[i].domId, name: fixedDefs[i].name, type: 'fixed'});
      }
    }
    if (customTables && customTables.length > 0) {
      for (var j = 0; j < customTables.length; j++) {
        allItems.push({id: customTables[j].id, name: customTables[j].tbl_name, type: 'custom'});
      }
    }
    if (allItems.length === 0) {
      listEl.innerHTML = '<p style="color:#888;text-align:center;padding:20px;">&#x0644;&#x0627; &#x062A;&#x0648;&#x062C;&#x062F; &#x062C;&#x062F;&#x0627;&#x0648;&#x0644; &#x0644;&#x0639;&#x0631;&#x0636;&#x0647;&#x0627;</p>';
      return;
    }
    var html = '';
    for (var k = 0; k < allItems.length; k++) {
      var t = allItems[k];
      var icon = t.type === 'custom' ? '&#x1F4CB;' : '&#x1F4CA;';
      var badge = t.type === 'fixed' ? '<span style="font-size:0.72em;background:#e67e22;color:#fff;border-radius:6px;padding:1px 7px;margin-right:6px;vertical-align:middle;">&#x062B;&#x0627;&#x0628;&#x062A;</span>' : '';
      html += '<div class="delete-table-item" id="dti_' + t.id + '" data-tid="' + t.id + '" data-tname="' + t.name + '" data-ttype="' + t.type + '" onclick="selectDeleteTableFromEl(this)" style="padding:12px 16px;border-radius:8px;cursor:pointer;border:2px solid transparent;margin-bottom:6px;background:#fff;transition:all .2s;font-weight:600;font-size:1em;color:#333;display:flex;align-items:center;gap:8px;">' +
        '<span style="font-size:1.2em;">' + icon + '</span>' + badge + t.name + '</div>';
    }
    listEl.innerHTML = html;
  } catch(e) {
    listEl.innerHTML = '<p style="color:#e74c3c;text-align:center;padding:20px;">&#x062E;&#x0637;&#x0623; &#x0641;&#x064A; &#x062A;&#x062D;&#x0645;&#x064A;&#x0644; &#x0627;&#x0644;&#x0628;&#x064A;&#x0627;&#x0646;&#x0627;&#x062A;</p>';
  }
}

function selectDeleteTableFromEl(el) {
  var id = el.getAttribute('data-tid');
  var name = el.getAttribute('data-tname');
  var type = el.getAttribute('data-ttype');
  _selectedDeleteTableId = id;
  _selectedDeleteTableName = name;
  window._selectedDeleteTableType = type;
  document.querySelectorAll('.delete-table-item').forEach(function(item) {
    item.style.borderColor = 'transparent';
    item.style.background = '#fff';
    item.style.color = '#333';
  });
  el.style.borderColor = '#e74c3c';
  el.style.background = '#ffeaea';
  el.style.color = '#c0392b';
}

function closeDeleteTableModal() {
  document.getElementById('deleteTableModal').classList.remove('open');
  _selectedDeleteTableId = null;
  _selectedDeleteTableName = null;
}

function confirmDeleteTableSave() {
  if (!_selectedDeleteTableId) {
    alert('\u064A\u0631\u062C\u0649 \u0627\u062E\u062A\u064A\u0627\u0631 \u062C\u062F\u0648\u0644 \u0623\u0648\u0644\u0627\u064B');
    return;
  }
  document.getElementById('deleteTableModal').classList.remove('open');
  document.getElementById('deleteTableConfirmModal').classList.add('open');
}

function closeDeleteTableConfirm() {
  document.getElementById('deleteTableConfirmModal').classList.remove('open');
  document.getElementById('deleteTableModal').classList.add('open');
}

async function executeDeleteTable() {
  if (!_selectedDeleteTableId) return;
  document.getElementById('deleteTableConfirmModal').classList.remove('open');
  var tableType = window._selectedDeleteTableType || 'custom';
  if (tableType === 'fixed') {
    alert('\u0644\u0627 \u064A\u0645\u0643\u0646 \u062D\u0630\u0641 \u0627\u0644\u062C\u062F\u0627\u0648\u0644 \u0627\u0644\u062B\u0627\u0628\u062A\u0629. \u064A\u0645\u0643\u0646 \u062D\u0630\u0641 \u0627\u0644\u062C\u062F\u0627\u0648\u0644 \u0627\u0644\u0645\u062E\u0635\u0635\u0629 \u0641\u0642\u0637.');
    _selectedDeleteTableId = null;
    _selectedDeleteTableName = null;
    return;
  }
  try {
    var res = await fetch('/api/custom-tables/' + _selectedDeleteTableId, { method: 'DELETE' });
    var data = await res.json();
    if (data.ok) {
      typeof loadCustomTables === 'function' && loadCustomTables();
      _selectedDeleteTableId = null;
      _selectedDeleteTableName = null;
    } else {
      alert('\u062E\u0637\u0623: ' + (data.error || '\u0641\u0634\u0644 \u0627\u0644\u062D\u0630\u0641'));
    }
  } catch(e) {
    alert('\u062D\u062F\u062B \u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0627\u062A\u0635\u0627\u0644 \u0628\u0627\u0644\u062E\u0627\u062F\u0645');
  }
}
// \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

function openTableEditModal(){
  loadColumnsForEdit();
  document.getElementById('tableEditModal').classList.add('open');
  switchTab('add-col');
}
function closeTableEditModal(){document.getElementById('tableEditModal').classList.remove('open');}
function switchTab(tab){
  var tabs=['add-col','del-col','edit-col'];
  for(var i=0;i<tabs.length;i++){
    var panel=document.getElementById('panel-'+tabs[i]);
    var btn=document.getElementById('tab-'+tabs[i]);
    if(panel)panel.style.display=(tabs[i]===tab)?'block':'none';
    if(btn){btn.style.background=tabs[i]===tab?'#FF6B35':'#f0ebff';btn.style.color=tabs[i]===tab?'#fff':'#6B3FA0';}
  }
}
function loadColumnsForEdit(){
  fetch('/api/columns').then(function(r){return r.json();}).then(function(data){
    var cols=data.columns||[];
    var delSel=document.getElementById('del_col_key');
    var editSel=document.getElementById('edit_col_key');
    var afterSel=document.getElementById('new_col_after');
    delSel.innerHTML='<option value="">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F; &#x2014;</option>';
    editSel.innerHTML='<option value="">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F; &#x2014;</option>';
    afterSel.innerHTML='<option value="">&#x2014; &#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x2014;</option>';
    for(var i=0;i<cols.length;i++){
      delSel.innerHTML+='<option value="'+cols[i].col_key+'">'+cols[i].col_label+'</option>';
      editSel.innerHTML+='<option value="'+cols[i].col_key+'" data-label="'+cols[i].col_label+'">'+cols[i].col_label+'</option>';
      afterSel.innerHTML+='<option value="'+cols[i].col_key+'">'+cols[i].col_label+'</option>';
    }
  });
}
function fillEditLabel(){
  var sel=document.getElementById('edit_col_key');
  var opt=sel.options[sel.selectedIndex];
  document.getElementById('edit_col_label').value=opt?opt.getAttribute('data-label'):'';
}
function togglePositionCol(){
  var posVal=document.getElementById('new_col_position').value;
  var afterSel=document.getElementById('new_col_after');
  if(afterSel) afterSel.style.display=(posVal==='after')?'block':'none';
}
function addColumn(){
  var label=document.getElementById('new_col_label').value.trim();
  if(!label){showToast('&#x627;&#x62F;&#x62E;&#x644; &#x639;&#x646;&#x648;&#x627;&#x646; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;','#e53935');return;}
  var posVal=document.getElementById('new_col_position').value;
  var afterCol=document.getElementById('new_col_after').value;
  var key='col_'+Date.now();
  var payload={col_key:key,col_label:label,position:posVal};
  if(posVal==='after'&&afterCol){payload.after_col=afterCol;}
  fetch('/api/columns',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(payload)}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('&#x627;&#x646;&#x62A;&#x647;&#x62A; &#x627;&#x644;&#x62C;&#x644;&#x633;&#x629;&#x60C; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x62E;&#x648;&#x644; &#x645;&#x62C;&#x62F;&#x62F;&#x627;','#e53935');return;}
    if(d.ok){document.getElementById('new_col_label').value='';document.getElementById('new_col_position').value='end';togglePositionCol();closeTableEditModal();showToast('&#x62A;&#x645; &#x625;&#x636;&#x627;&#x641;&#x629; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F; &#x628;&#x646;&#x62C;&#x627;&#x62D;');loadStudents();}
    else{showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');}
  });
}
function deleteColumn(){
  var key=document.getElementById('del_col_key').value;
  if(!key){showToast('&#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F;&#x627;','#e53935');return;}
  if(!confirm('&#x647;&#x644; &#x623;&#x646;&#x62A; &#x645;&#x62A;&#x623;&#x643;&#x62F; &#x645;&#x646; &#x62D;&#x630;&#x641; &#x647;&#x630;&#x627; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;&#x61F; &#x633;&#x64A;&#x62A;&#x645; &#x62D;&#x630;&#x641; &#x62C;&#x645;&#x64A;&#x639; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x647;.'))return;
  fetch('/api/columns/'+key,{method:'DELETE',credentials:'include'}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('&#x627;&#x646;&#x62A;&#x647;&#x62A; &#x627;&#x644;&#x62C;&#x644;&#x633;&#x629;&#x60C; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x62E;&#x648;&#x644; &#x645;&#x62C;&#x62F;&#x62F;&#x627;','#e53935');return;}
    if(d.ok){closeTableEditModal();showToast('&#x62A;&#x645; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;');loadStudents();}
    else{showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');}
  });
}
function updateColumnLabel(){
  var key=document.getElementById('edit_col_key').value;
  var label=document.getElementById('edit_col_label').value.trim();
  if(!key||!label){showToast('&#x627;&#x62E;&#x62A;&#x631; &#x639;&#x645;&#x648;&#x62F;&#x627; &#x648;&#x627;&#x62F;&#x62E;&#x644; &#x627;&#x644;&#x627;&#x633;&#x645;','#e53935');return;}
  fetch('/api/columns/'+key,{method:'PUT',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({col_label:label})}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('&#x627;&#x646;&#x62A;&#x647;&#x62A; &#x627;&#x644;&#x62C;&#x644;&#x633;&#x629;&#x60C; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x62E;&#x648;&#x644; &#x645;&#x62C;&#x62F;&#x62F;&#x627;','#e53935');return;}
    if(d.ok){closeTableEditModal();showToast('&#x62A;&#x645; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x639;&#x646;&#x648;&#x627;&#x646;');loadStudents();}
    else{showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');}
  });
}


var allGroupColumns=[];
function openGroupTableEditModal(){
  try {
    console.log('[groups] openGroupTableEditModal fired');
    var modal = document.getElementById('groupTableEditModal');
    if(!modal){ console.error('[groups] groupTableEditModal element missing'); alert('\u062E\u0637\u0623: \u0627\u0644\u0646\u0627\u0641\u0630\u0629 \u063A\u064A\u0631 \u0645\u0648\u062C\u0648\u062F\u0629'); return; }
    loadGroupColumnsForEdit();
    modal.classList.add('open');
    switchGroupTab('add-col');
  } catch(e) {
    console.error('[groups] openGroupTableEditModal threw:', e);
    showToast('\u062E\u0637\u0623: ' + (e && e.message ? e.message : e), '#e53935');
  }
}
function closeGroupTableEditModal(){document.getElementById('groupTableEditModal').classList.remove('open');}
function switchGroupTab(tab){
  var tabs=['add-col','del-col','edit-col'];
  for(var i=0;i<tabs.length;i++){
    var panel=document.getElementById('gpanel-'+tabs[i]);
    var btn=document.getElementById('gtab-'+tabs[i]);
    if(panel)panel.style.display=(tabs[i]===tab)?'block':'none';
    if(btn){btn.style.background=tabs[i]===tab?'#FF6B35':'#e0f7fa';btn.style.color=tabs[i]===tab?'#fff':'#0097A7';}
  }
}
function loadGroupColumnsForEdit(){
  fetch('/api/group-columns',{credentials:'include'}).then(function(r){
    if(!r.ok){ console.error('[groups] /api/group-columns HTTP', r.status); }
    return r.json();
  }).then(function(data){
    var cols=data.columns||[];
    console.log('[groups] loaded', cols.length, 'column labels');
    var delSel=document.getElementById('g_del_col_key');
    var editSel=document.getElementById('g_edit_col_key');
    var afterSel=document.getElementById('g_new_col_after');
    if(delSel)delSel.innerHTML='<option value="">&#8212; &#1575;&#1582;&#1578;&#1585; &#1593;&#1605;&#1608;&#1583; &#8212;</option>';
    if(editSel)editSel.innerHTML='<option value="">&#8212; &#1575;&#1582;&#1578;&#1585; &#1593;&#1605;&#1608;&#1583; &#8212;</option>';
    if(afterSel)afterSel.innerHTML='<option value="">&#8212; &#1575;&#1582;&#1578;&#1585; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#8212;</option>';
    for(var i=0;i<cols.length;i++){
      if(delSel)delSel.innerHTML+='<option value="'+cols[i].col_key+'">'+cols[i].col_label+'</option>';
      if(editSel)editSel.innerHTML+='<option value="'+cols[i].col_key+'" data-label="'+cols[i].col_label+'">'+cols[i].col_label+'</option>';
      if(afterSel)afterSel.innerHTML+='<option value="'+cols[i].col_key+'">'+cols[i].col_label+'</option>';
    }
  });
}
function fillGroupEditLabel(){
  var sel=document.getElementById('g_edit_col_key');
  var opt=sel.options[sel.selectedIndex];
  var lbl=document.getElementById('g_edit_col_label');
  if(lbl)lbl.value=opt?opt.getAttribute('data-label'):'';
}
function toggleGroupPositionCol(){
  var posVal=document.getElementById('g_new_col_position').value;
  var afterSel=document.getElementById('g_new_col_after');
  if(afterSel)afterSel.style.display=(posVal==='after')?'block':'none';
}
function addGroupColumn(){
  var label=document.getElementById('g_new_col_label').value.trim();
  if(!label){showToast('\u0627\u062F\u062E\u0644 \u0639\u0646\u0648\u0627\u0646 \u0627\u0644\u0639\u0645\u0648\u062F','#e53935');return;}
  var posVal=document.getElementById('g_new_col_position').value;
  var afterCol=document.getElementById('g_new_col_after').value;
  var key='gcol_'+Date.now();
  var payload={col_key:key,col_label:label,position:posVal};
  if(posVal==='after'&&afterCol){payload.after_col=afterCol;}
  fetch('/api/group-columns',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(payload)}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('\u0627\u0646\u062A\u0647\u062A \u0627\u0644\u062C\u0644\u0633\u0629\u060C \u0633\u062C\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \u0645\u062C\u062F\u062F\u0627','#e53935');return;}
    if(d.ok){document.getElementById('g_new_col_label').value='';document.getElementById('g_new_col_position').value='end';toggleGroupPositionCol();closeGroupTableEditModal();showToast('\u062A\u0645 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0639\u0645\u0648\u062F \u0628\u0646\u062C\u0627\u062D','#00BCD4');loadGroups2();}
    else{showToast(d.error||'\u062D\u062F\u062B \u062E\u0637\u0623','#e53935');}
  });
}
function deleteGroupColumn(){
  var key = document.getElementById('g_del_col_key').value;
  if (!key) { showToast('\u0627\u062E\u062A\u0631 \u0639\u0645\u0648\u062F\u0627', '#e53935'); return; }
  if (!confirm('\u0647\u0644 \u0623\u0646\u062A \u0645\u062A\u0623\u0643\u062F \u0645\u0646 \u062D\u0630\u0641 \u0647\u0630\u0627 \u0627\u0644\u0639\u0645\u0648\u062F\u061F')) return;
  fetch('/api/group-columns/' + encodeURIComponent(key), { method: 'DELETE', credentials: 'include' })
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d && d.ok) {
        closeGroupTableEditModal();
        showToast('\u062A\u0645 \u062D\u0630\u0641 \u0627\u0644\u0639\u0645\u0648\u062F', '#00BCD4');
        loadGroups2();
      } else {
        showToast((d && d.error) || '\u062D\u062F\u062B \u062E\u0637\u0623', '#e53935');
      }
    })
    .catch(function(){ showToast('\u062D\u062F\u062B \u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0627\u062A\u0635\u0627\u0644', '#e53935'); });
}
function updateGroupColumnLabel(){
  var key=document.getElementById('g_edit_col_key').value;
  var label=document.getElementById('g_edit_col_label').value.trim();
  if(!key||!label){showToast('\u0627\u062E\u062A\u0631 \u0639\u0645\u0648\u062F\u0627 \u0648\u0627\u062F\u062E\u0644 \u0627\u0644\u0627\u0633\u0645','#e53935');return;}
  fetch('/api/group-columns/'+key,{method:'PUT',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({col_label:label})}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('\u0627\u0646\u062A\u0647\u062A \u0627\u0644\u062C\u0644\u0633\u0629\u060C \u0633\u062C\u0644 \u0627\u0644\u062F\u062E\u0648\u0644 \u0645\u062C\u062F\u062F\u0627','#e53935');return;}
    if(d.ok){closeGroupTableEditModal();showToast('\u062A\u0645 \u062A\u0639\u062F\u064A\u0644 \u0627\u0644\u0639\u0646\u0648\u0627\u0646','#00BCD4');loadGroups2();}
    else{showToast(d.error||'\u062D\u062F\u062B \u062E\u0637\u0623','#e53935');}
  });
}

var allAttendance = [];
var editingAttendanceId = null;
var deletingAttendanceId = null;

function loadAttendance() {
  fetch('/api/attendance').then(r=>r.json()).then(data=>{
    allAttendance = data;
    document.getElementById('attendanceTotalCount').textContent = data.length;
    renderAttendanceTable(data);
  });
}

function renderAttendanceTable(data) {
  var tbody = document.getElementById('attendanceBody');
  if(!data || data.length === 0) {
    tbody.innerHTML = '<tr><td colspan="12" class="no-data">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x633;&#x62C;&#x644;&#x627;&#x62A;&#x60C; &#x627;&#x636;&#x641; &#x623;&#x648;&#x644; &#x633;&#x62C;&#x644;</td></tr>';
    _bulkUpdate('attendanceBody','selectAll_attendance','bulkDelBtn_attendance');
    applyFreezeToTable('attendance');
    return;
  }
  var html = '';
  for(var i=0; i<data.length; i++) {
    var r = data[i];
    html += '<tr>';
    html += '<td class="bulk-col"><input type="checkbox" class="bulk-cb" data-id="' + r.id + '" onclick="_bulkUpdate(\\'attendanceBody\\',\\'selectAll_attendance\\',\\'bulkDelBtn_attendance\\')"></td>';
    html += '<td>' + (i+1) + '</td>';
    html += '<td class="editable" data-id="' + r.id + '" data-field="attendance_date" onclick="editAttendanceCellEl(this)">' + (r.attendance_date||'') + '</td>';
    html += '<td class="editable" data-id="' + r.id + '" data-field="day_name" onclick="editAttendanceCellEl(this)">' + (r.day_name||'') + '</td>';
    html += '<td class="editable" data-id="' + r.id + '" data-field="group_name" onclick="editAttendanceCellEl(this)">' + (r.group_name||'') + '</td>';
    html += '<td class="editable" data-id="' + r.id + '" data-field="student_name" onclick="editAttendanceCellEl(this)">' + (r.student_name||'') + '</td>';
    html += '<td class="editable" data-id="' + r.id + '" data-field="contact_number" onclick="editAttendanceCellEl(this)">' + (r.contact_number||'') + '</td>';
    html += '<td class="editable" data-id="' + r.id + '" data-field="status" onclick="editAttendanceCellEl(this)">' + (r.status||'') + '</td>';
    html += '<td class="editable" data-id="' + r.id + '" data-field="message" onclick="editAttendanceCellEl(this)">' + (r.message||'') + '</td>';
    html += '<td class="editable" data-id="' + r.id + '" data-field="message_status" onclick="editAttendanceCellEl(this)">' + (r.message_status||'') + '</td>';
    html += '<td class="editable" data-id="' + r.id + '" data-field="study_status" onclick="editAttendanceCellEl(this)">' + (r.study_status||'') + '</td>';
    html += '<td><button class="btn-del-row" onclick="openAttendanceConfirm(' + r.id + ')">&#128465;</button></td>';
    html += '</tr>';
  }
  tbody.innerHTML = html;
  applyFreezeToTable('attendance');
}
function filterAttendanceTable() {
  var q = document.getElementById('attendanceSearchInput').value.toLowerCase();
  if(!q) { renderAttendanceTable(allAttendance); return; }
  var filtered = allAttendance.filter(function(r) {
    return Object.values(r).some(function(v) { return String(v||'').toLowerCase().indexOf(q) !== -1; });
  });
  renderAttendanceTable(filtered);
}

function openAttendanceAddModal() {
  editingAttendanceId = null;
  document.getElementById('attendanceModalTitle').innerHTML = '&#x625;&#x636;&#x627;&#x641;&#x629; &#x633;&#x62C;&#x644; &#x63A;&#x64A;&#x627;&#x628;';
  document.getElementById('att_date').value = '';
  document.getElementById('att_day').value = '';
  document.getElementById('att_group').value = '';
  document.getElementById('att_student').value = '';
  document.getElementById('att_contact').value = '';
  document.getElementById('att_status').value = '';
  document.getElementById('att_message').value = '';
  document.getElementById('att_msg_status').value = '';
  document.getElementById('att_study_status').value = '';
  document.getElementById('attendanceModal').style.display = 'flex';
}

function closeAttendanceModal() {
  document.getElementById('attendanceModal').style.display = 'none';
  editingAttendanceId = null;
}

function saveAttendanceRecord() {
  var data = {
    attendance_date: document.getElementById('att_date').value,
    day_name: document.getElementById('att_day').value,
    group_name: document.getElementById('att_group').value,
    student_name: document.getElementById('att_student').value,
    contact_number: document.getElementById('att_contact').value,
    status: document.getElementById('att_status').value,
    message: document.getElementById('att_message').value,
    message_status: document.getElementById('att_msg_status').value,
    study_status: document.getElementById('att_study_status').value
  };
  var url = editingAttendanceId ? '/api/attendance/' + editingAttendanceId : '/api/attendance';
  var method = editingAttendanceId ? 'PUT' : 'POST';
  fetch(url, {method: method, headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ closeAttendanceModal(); showToast('&#x62A;&#x645; &#x627;&#x644;&#x62D;&#x641;&#x638;','#4CAF50'); loadAttendance(); loadTaqseet(); }
      else { showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

function editAttendanceCellEl(tdEl) {
  if(tdEl.querySelector('input,select,textarea')) return;
  var id = parseInt(tdEl.getAttribute('data-id'));
  var field = tdEl.getAttribute('data-field');
  editAttendanceCell(id, field, tdEl);
}

function editAttendanceCell(id, field, tdEl) {
  if(tdEl.querySelector('input,select,textarea')) return;
  var oldVal = tdEl.textContent.trim();
  var input;
  var selectOptions = {
    'status': ['','&#x62D;&#x627;&#x636;&#x631;','&#x63A;&#x627;&#x626;&#x628;','&#x645;&#x62A;&#x623;&#x62E;&#x631;','&#x645;&#x639;&#x62A;&#x630;&#x631;'],
    'message_status': ['','&#x62A;&#x645; &#x627;&#x644;&#x625;&#x631;&#x633;&#x627;&#x644;','&#x644;&#x645; &#x64A;&#x64F;&#x631;&#x633;&#x644;','&#x641;&#x634;&#x644; &#x627;&#x644;&#x625;&#x631;&#x633;&#x627;&#x644;'],
    'study_status': ['','&#x645;&#x633;&#x62A;&#x645;&#x631;','&#x645;&#x646;&#x642;&#x637;&#x639;','&#x645;&#x648;&#x642;&#x648;&#x641;']
  };
  if(selectOptions[field]) {
    input = document.createElement('select');
    input.style.cssText = 'width:100%;padding:4px;border:1px solid #aaa;border-radius:4px;';
    selectOptions[field].forEach(function(v){
      var o = document.createElement('option');
      o.value = v; o.textContent = v||'-- \u0627\u062E\u062A\u0631 --';
      if(v === oldVal) o.selected = true;
      input.appendChild(o);
    });
  } else if(field === 'message') {
    input = document.createElement('textarea');
    input.value = oldVal;
    input.rows = 3;
    input.style.cssText = 'width:100%;padding:4px;border:1px solid #aaa;border-radius:4px;resize:vertical;';
  } else if(field === 'attendance_date') {
    input = document.createElement('input');
    input.type = 'date';
    input.value = oldVal;
    input.style.cssText = 'width:100%;padding:4px;border:1px solid #aaa;border-radius:4px;';
  } else {
    input = document.createElement('input');
    input.type = 'text';
    input.value = oldVal;
    input.style.cssText = 'width:100%;padding:4px;border:1px solid #aaa;border-radius:4px;';
  }
  tdEl.innerHTML = '';
  tdEl.appendChild(input);
  input.focus();
  var saved = false;
  function saveCell() {
    if(saved) return;
    saved = true;
    var newVal = input.value;
    var rec = null;
    for(var i=0; i<allAttendance.length; i++) { if(allAttendance[i].id===id){ rec=allAttendance[i]; break; } }
    if(!rec) return;
    var updated = Object.assign({}, rec);
    updated[field] = newVal;
    fetch('/api/attendance/' + id, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify(updated)})
      .then(function(r){ return r.json(); }).then(function(d){
        if(d.ok){ showToast('&#x62A;&#x645; &#x627;&#x644;&#x62A;&#x62D;&#x62F;&#x64A;&#x62B;','#4CAF50'); loadAttendance(); }
        else { showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); loadAttendance(); }
      });
  }
  input.addEventListener('blur', saveCell);
  input.addEventListener('keydown', function(e){ if(e.key==='Enter' && field!=='message') { input.blur(); } });
}
function openAttendanceConfirm(id) {
  deletingAttendanceId = id;
  document.getElementById('attendanceConfirmModal').style.display = 'flex';
}

function closeAttendanceConfirm() {
  document.getElementById('attendanceConfirmModal').style.display = 'none';
  deletingAttendanceId = null;
}

function confirmAttendanceDelete() {
  if(!deletingAttendanceId) return;
  fetch('/api/attendance/' + deletingAttendanceId, {method:'DELETE'})
    .then(function(r){ return r.json(); }).then(function(d){
      closeAttendanceConfirm();
      if(d.ok){ showToast('&#x62A;&#x645; &#x627;&#x644;&#x62D;&#x630;&#x641;','#e53935'); loadAttendance(); }
      else { showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

loadAttendance();

// &#x2500;&#x2500;&#x2500; Custom Tables JS &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;
var allCustomTables = [];
var currentCustomTableId = null;
var editingCustomRowId = null;
var deletingCustomTableId = null;

function loadCustomTables() {
  fetch('/api/custom-tables').then(function(r){ return r.json(); }).then(function(data){
    allCustomTables = data;
    renderAllCustomTables();
  });
}

function renderAllCustomTables() {
  var container = document.getElementById('customTablesContainer');
  if(!container) return;
  var html = '';
  for(var i=0; i<allCustomTables.length; i++) {
    var t = allCustomTables[i];
    html += buildCustomTableHTML(t);
  }
  container.innerHTML = html;
  // Re-apply saved freeze state on each custom table.
  for (var j = 0; j < allCustomTables.length; j++) {
    applyFreezeToTable('custom_' + allCustomTables[j].id);
  }
  // Keep the section-nav tabs in sync with whatever custom tables exist.
  if (typeof dbNavRefreshCustom === 'function') {
    dbNavRefreshCustom(allCustomTables);
  }
}

function buildCustomTableHTML(t) {
  var cols = t.cols || [];
  var rows = t.rows || [];
  var tbodyId = 'ctbody_' + t.id;
  var saId = 'selectAll_custom_' + t.id;
  var btnId = 'bulkDelBtn_custom_' + t.id;
  var headerCells = '<th class="bulk-col"><input type="checkbox" id="' + saId + '" class="bulk-cb" onclick="_bulkSelectAll(\\'' + tbodyId + '\\',\\'' + saId + '\\',\\'' + btnId + '\\',this.checked)"></th><th>#</th>';
  for(var i=0; i<cols.length; i++) {
    headerCells += '<th>' + (cols[i].col_label||'') + '</th>';
  }
  headerCells += '<th>&#128465;</th>';

  var bodyRows = '';
  if(rows.length === 0) {
    bodyRows = '<tr><td colspan="' + (cols.length+3) + '" class="no-data">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x60C; &#x623;&#x636;&#x641; &#x623;&#x648;&#x644; &#x635;&#x641;</td></tr>';
  } else {
    for(var j=0; j<rows.length; j++) {
      var r = rows[j];
      var rd = r.row_data || {};
      bodyRows += '<tr>';
      bodyRows += '<td class="bulk-col"><input type="checkbox" class="bulk-cb" data-id="' + r.id + '" onclick="_bulkUpdate(\\'' + tbodyId + '\\',\\'' + saId + '\\',\\'' + btnId + '\\')"></td>';
      bodyRows += '<td>' + (j+1) + '</td>';
      for(var k=0; k<cols.length; k++) {
        var ck = cols[k].col_key;
        var val = rd[ck] || '';
        bodyRows += '<td class="editable" data-tid="' + t.id + '" data-rid="' + r.id + '" data-ckey="' + ck + '" onclick="editCustomCell(this)">' + val + '</td>';
      }
      bodyRows += '<td><button class="btn-del-row" onclick="deleteCustomRow(' + t.id + ',' + r.id + ')">&#128465;</button></td>';
      bodyRows += '</tr>';
    }
  }

  var tid = t.id;
  var bulkBtn = '<button id="' + btnId + '" class="btn-bulk-del" style="font-size:13px;padding:6px 12px;border-radius:8px;" onclick="_bulkDelete(\\'' + tbodyId + '\\',function(id){return \\'/api/custom-tables/' + tid + '/rows/\\'+id;},loadCustomTables,\\'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x635;&#x641;&#x61F;\\')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button>';
  var freezeBtn = '<button class="btn-add" style="background:linear-gradient(135deg,#1565C0,#1E88E5);font-size:13px;padding:6px 12px;border-radius:8px;" onclick="openFreezeModal(\\'custom_' + tid + '\\')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button>';

  return '<div class="custom-table-section" id="ctsec_' + t.id + '">' +
    '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:10px;">' +
    '<span class="custom-table-title">&#128203; ' + t.tbl_name + '</span>' +
    '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
    '<button class="btn-add" onclick="openCustomRowModal(' + t.id + ')">+ &#x625;&#x636;&#x627;&#x641;&#x629; &#x635;&#x641;</button>' +
    '<button class="btn-add" style="background:linear-gradient(135deg,#E65100,#FFA726);" onclick="openCustomTableEditModal(' + t.id + ')">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>' +
    '<button class="btn-del-row" style="font-size:13px;padding:6px 12px;border-radius:8px;" data-tid="' + t.id + '" onclick="openCustomTableDeleteConfirmById(this)">&#128465; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>' +
    freezeBtn +
    bulkBtn +
    '</div></div>' +
    '<div class="table-wrap"><table>' +
    '<thead><tr id="cthead_' + t.id + '">' + headerCells + '</tr></thead>' +
    '<tbody id="' + tbodyId + '">' + bodyRows + '</tbody>' +
    '</table></div></div>';
}
// &#x2500;&#x2500; Row add/edit &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;
function openCustomRowModal(tid) {
  currentCustomTableId = tid;
  editingCustomRowId = null;
  var t = null;
  for(var i=0; i<allCustomTables.length; i++) { if(allCustomTables[i].id===tid) { t=allCustomTables[i]; break; } }
  if(!t) return;
  document.getElementById('customRowModalTitle').innerHTML = '&#x625;&#x636;&#x627;&#x641;&#x629; &#x635;&#x641; - ' + t.tbl_name;
  var fields = document.getElementById('customRowFormFields');
  fields.innerHTML = '';
  var cols = t.cols || [];
  for(var j=0; j<cols.length; j++) {
    var wrapper = document.createElement('div');
    wrapper.innerHTML = '<label style="font-size:.85em;color:#555;">' + cols[j].col_label + '</label>' +
      '<input type="text" id="crow_' + cols[j].col_key + '" class="col-name-input" placeholder="' + cols[j].col_label + '" style="margin-top:3px;">';
    fields.appendChild(wrapper);
  }
  document.getElementById('customRowModal').style.display = 'flex';
}

function closeCustomRowModal() {
  document.getElementById('customRowModal').style.display = 'none';
  currentCustomTableId = null;
  editingCustomRowId = null;
}

function saveCustomRow() {
  var tid = currentCustomTableId;
  var t = null;
  for(var i=0; i<allCustomTables.length; i++) { if(allCustomTables[i].id===tid) { t=allCustomTables[i]; break; } }
  if(!t) return;
  var row_data = {};
  var cols = t.cols || [];
  for(var j=0; j<cols.length; j++) {
    var inp = document.getElementById('crow_' + cols[j].col_key);
    if(inp) row_data[cols[j].col_key] = inp.value;
  }
  var url = '/api/custom-tables/' + tid + '/rows';
  var method = 'POST';
  if(editingCustomRowId) {
    url = '/api/custom-tables/' + tid + '/rows/' + editingCustomRowId;
    method = 'PUT';
  }
  fetch(url, {method:method, headers:{'Content-Type':'application/json'}, body:JSON.stringify({row_data: row_data})})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok) { closeCustomRowModal(); showToast('&#x62A;&#x645; &#x627;&#x644;&#x62D;&#x641;&#x638;','#4CAF50'); loadCustomTables(); }
      else { showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

function deleteCustomRow(tid, rid) {
  fetch('/api/custom-tables/' + tid + '/rows/' + rid, {method:'DELETE'})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok) { showToast('&#x62A;&#x645; &#x627;&#x644;&#x62D;&#x630;&#x641;','#e53935'); loadCustomTables(); }
      else { showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

// &#x2500;&#x2500; Inline cell edit &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;
function editCustomCell(tdEl) {
  if(tdEl.querySelector('input')) return;
  var tid = parseInt(tdEl.getAttribute('data-tid'));
  var rid = parseInt(tdEl.getAttribute('data-rid'));
  var ckey = tdEl.getAttribute('data-ckey');
  var oldVal = tdEl.textContent.trim();
  var input = document.createElement('input');
  input.type = 'text';
  input.value = oldVal;
  input.style.cssText = 'width:100%;padding:4px;border:1px solid #aaa;border-radius:4px;';
  tdEl.innerHTML = '';
  tdEl.appendChild(input);
  input.focus();
  var saved = false;
  function saveCell() {
    if(saved) return; saved = true;
    var newVal = input.value;
    var t = null;
    for(var i=0; i<allCustomTables.length; i++) { if(allCustomTables[i].id===tid) { t=allCustomTables[i]; break; } }
    if(!t) return;
    var row = null;
    for(var j=0; j<t.rows.length; j++) { if(t.rows[j].id===rid) { row=t.rows[j]; break; } }
    if(!row) return;
    var updated = Object.assign({}, row.row_data);
    updated[ckey] = newVal;
    fetch('/api/custom-tables/' + tid + '/rows/' + rid, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({row_data: updated})})
      .then(function(r){ return r.json(); }).then(function(d){
        if(d.ok){ showToast('&#x62A;&#x645; &#x627;&#x644;&#x62A;&#x62D;&#x62F;&#x64A;&#x62B;','#4CAF50'); loadCustomTables(); }
        else{ showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); loadCustomTables(); }
      });
  }
  input.addEventListener('blur', saveCell);
  input.addEventListener('keydown', function(e){ if(e.key==='Enter') input.blur(); });
}

// &#x2500;&#x2500; Table edit modal (add/delete/rename cols) &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;
function openCustomTableEditModal(tid) {
  currentCustomTableId = tid;
  var t = null;
  for(var i=0; i<allCustomTables.length; i++) { if(allCustomTables[i].id===tid) { t=allCustomTables[i]; break; } }
  if(!t) return;
  document.getElementById('customTableEditTitle').innerHTML = '&#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x62C;&#x62F;&#x648;&#x644;: ' + t.tbl_name;
  switchCustomTab('add');
  loadCustomColsForEdit(t);
  document.getElementById('customTableEditModal').style.display = 'flex';
}

function closeCustomTableEditModal() {
  document.getElementById('customTableEditModal').style.display = 'none';
  currentCustomTableId = null;
}

function switchCustomTab(tab) {
  var panels = ['ctabPanelAdd','ctabPanelDel','ctabPanelRename'];
  var btns = ['ctab1','ctab2','ctab3'];
  var tabMap = {add:0, del:1, rename:2};
  for(var i=0; i<panels.length; i++) {
    document.getElementById(panels[i]).style.display = i===tabMap[tab] ? 'block' : 'none';
    document.getElementById(btns[i]).classList.toggle('active', i===tabMap[tab]);
  }
}

function loadCustomColsForEdit(t) {
  var cols = t.cols || [];
  var delSel = document.getElementById('ctbl_del_col');
  var renameSel = document.getElementById('ctbl_rename_col');
  var afterSel = document.getElementById('ctbl_after_col');
  delSel.innerHTML = '';
  renameSel.innerHTML = '';
  afterSel.innerHTML = '';
  for(var i=0; i<cols.length; i++) {
    var o1 = document.createElement('option');
    o1.value = cols[i].col_key; o1.textContent = cols[i].col_label;
    delSel.appendChild(o1);
    var o2 = document.createElement('option');
    o2.value = cols[i].col_key; o2.textContent = cols[i].col_label;
    renameSel.appendChild(o2);
    var o3 = document.createElement('option');
    o3.value = cols[i].col_key; o3.textContent = cols[i].col_label;
    afterSel.appendChild(o3);
  }
  document.getElementById('ctbl_new_col_name').value = '';
  document.getElementById('ctbl_position').value = 'end';
  document.getElementById('ctbl_after_col').style.display = 'none';
  fillCustomRenameLabel();
}

function toggleCustomPosition() {
  var pos = document.getElementById('ctbl_position').value;
  document.getElementById('ctbl_after_col').style.display = pos === 'after' ? 'block' : 'none';
}

function fillCustomRenameLabel() {
  var sel = document.getElementById('ctbl_rename_col');
  var lbl = document.getElementById('ctbl_rename_label');
  if(sel && sel.options[sel.selectedIndex]) {
    lbl.value = sel.options[sel.selectedIndex].text;
  }
}

function addCustomColumn() {
  var tid = currentCustomTableId;
  var col_label = document.getElementById('ctbl_new_col_name').value.trim();
  if(!col_label) { showToast('&#x623;&#x62F;&#x62E;&#x644; &#x627;&#x633;&#x645; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;','#e53935'); return; }
  var position = document.getElementById('ctbl_position').value;
  var after_key = document.getElementById('ctbl_after_col').value;
  var payload = { col_label: col_label, position: position, after_key: after_key };
  fetch('/api/custom-tables/' + tid + '/cols', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('&#x62A;&#x645; &#x625;&#x636;&#x627;&#x641;&#x629; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;','#00BCD4'); loadCustomTables(); closeCustomTableEditModal(); }
      else{ showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

function deleteCustomColumn() {
  var tid = currentCustomTableId;
  var col_key = document.getElementById('ctbl_del_col').value;
  if(!col_key) return;
  fetch('/api/custom-tables/' + tid + '/cols/' + col_key, {method:'DELETE'})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('&#x62A;&#x645; &#x627;&#x644;&#x62D;&#x630;&#x641;','#e53935'); loadCustomTables(); closeCustomTableEditModal(); }
      else{ showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

function updateCustomColumnLabel() {
  var tid = currentCustomTableId;
  var col_key = document.getElementById('ctbl_rename_col').value;
  var new_label = document.getElementById('ctbl_rename_label').value.trim();
  if(!new_label || !col_key) { showToast('&#x623;&#x62F;&#x62E;&#x644; &#x627;&#x644;&#x627;&#x633;&#x645; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F;','#e53935'); return; }
  fetch('/api/custom-tables/' + tid + '/cols/' + col_key, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({col_label: new_label})})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('&#x62A;&#x645; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x639;&#x646;&#x648;&#x627;&#x646;','#00BCD4'); loadCustomTables(); closeCustomTableEditModal(); }
      else{ showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

// &#x2500;&#x2500; Delete table &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;
function openCustomTableDeleteConfirmById(btn) {
  var tid = parseInt(btn.getAttribute('data-tid'));
  var t = null;
  for(var i=0; i<allCustomTables.length; i++) { if(allCustomTables[i].id===tid){ t=allCustomTables[i]; break; } }
  var name = t ? t.tbl_name : '';
  openCustomTableDeleteConfirm(tid, name);
}

function openCustomTableDeleteConfirm(tid, name) {
  deletingCustomTableId = tid;
  document.getElementById('customTableDeleteMsg').textContent = '\u0647\u0644 \u062A\u0631\u064A\u062F \u062D\u0630\u0641 \u062C\u062F\u0648\u0644 "' + name + '"\u061F \u0633\u064A\u062A\u0645 \u062D\u0630\u0641 \u062C\u0645\u064A\u0639 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A.';
  document.getElementById('customTableDeleteConfirm').style.display = 'flex';
}
function closeCustomTableDeleteConfirm() {
  document.getElementById('customTableDeleteConfirm').style.display = 'none';
  deletingCustomTableId = null;
}

function confirmCustomTableDelete() {
  if(!deletingCustomTableId) return;
  fetch('/api/custom-tables/' + deletingCustomTableId, {method:'DELETE'})
    .then(function(r){ return r.json(); }).then(function(d){
      closeCustomTableDeleteConfirm();
      if(d.ok){ showToast('&#x62A;&#x645; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;','#e53935'); loadCustomTables(); }
      else{ showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

// &#x2500;&#x2500; Import stub (placeholder) &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;
function openCustomImportModal(tid) {
  showToast('&#x645;&#x64A;&#x632;&#x629; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; &#x642;&#x631;&#x64A;&#x628;&#x627;&#x64B;','#FF9800');
}

// Load custom tables on page load
loadCustomTables();

// &#x2500;&#x2500;&#x2500; Attendance Excel Import &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;
var attendanceExcelRows = [];

function openAttendanceExcelModal() {
  attendanceExcelRows = [];
  document.getElementById('attendanceExcelStatus').textContent = '';
  document.getElementById('attendanceExcelImportBtn').style.display = 'none';
  document.getElementById('attendanceExcelFileInput').value = '';
  document.getElementById('attendanceExcelModal').style.display = 'flex';
}

function closeAttendanceExcelModal() {
  document.getElementById('attendanceExcelModal').style.display = 'none';
  attendanceExcelRows = [];
}

function readAttendanceExcelFile(input) {
  var file = input.files[0];
  if(!file) return;
  var reader = new FileReader();
  reader.onload = function(e) {
    try {
      var data = new Uint8Array(e.target.result);
      var workbook = XLSX.read(data, {type: 'array'});
      var sheet = workbook.Sheets[workbook.SheetNames[0]];
      var rows = XLSX.utils.sheet_to_json(sheet, {header:1, defval:''});
      // Skip header row (row 0)
      var dataRows = rows.slice(1).filter(function(r) { return r.some(function(c){ return String(c).trim() !== ''; }); });
      attendanceExcelRows = dataRows;
      document.getElementById('attendanceExcelStatus').textContent = '\u062A\u0645 \u0642\u0631\u0627\u0621\u0629 ' + dataRows.length + ' \u0635\u0641. \u0627\u0636\u063A\u0637 \u0627\u0633\u062A\u064A\u0631\u0627\u062F.';
      document.getElementById('attendanceExcelImportBtn').style.display = dataRows.length > 0 ? 'inline-flex' : 'none';
    } catch(err) {
      document.getElementById('attendanceExcelStatus').textContent = '\u062E\u0637\u0623 \u0641\u064A \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u0645\u0644\u0641: ' + err.message;
    }
  };
  reader.readAsArrayBuffer(file);
}

function importAttendanceFromExcel() {
  if(!attendanceExcelRows || attendanceExcelRows.length === 0) return;
  var fields = ['attendance_date','day_name','group_name','student_name','contact_number','status','message','message_status','study_status'];
  var batch = attendanceExcelRows.map(function(row) {
    var obj = {};
    fields.forEach(function(f,i){ obj[f] = String(row[i]||''); });
    return obj;
  });
  var statusEl = document.getElementById('attendanceExcelStatus');
  statusEl.textContent = '\u062C\u0627\u0631\u064A \u0627\u0644\u0627\u0633\u062A\u064A\u0631\u0627\u062F...';
  // Route attendance imports through the same /api/import endpoint every
  // other table uses — that gives us upsert on (group,date,name), status
  // remap (\u063A\u064A\u0627\u0628 \u2192 \u063A\u0627\u0626\u0628, etc.), and a detailed counters payload
  // including updated vs inserted.
  fetch('/api/import', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({table: 'attendance', rows: batch})
  })
  .then(function(r){ return r.json(); })
  .then(function(d){
    if (d && d.ok) {
      var ins = d.inserted || 0, upd = d.updated || 0, skp = d.skipped || 0, err = d.errors || 0;
      var parts = ['\u062A\u0645 \u0627\u0644\u0625\u062F\u0631\u0627\u062C: ' + ins];
      if (upd) parts.push('\u062A\u062D\u062F\u064A\u062B: ' + upd);
      if (skp) parts.push('\u062A\u062C\u0627\u0647\u0644: ' + skp);
      if (err) parts.push('\u062E\u0637\u0623: ' + err);
      statusEl.textContent = parts.join(' \u2014 ');
      try { window.dispatchEvent(new CustomEvent('mx-imported', {detail: d})); } catch(e) {}
      if (typeof loadAttendance === 'function') loadAttendance();
      setTimeout(closeAttendanceExcelModal, 1500);
    } else {
      statusEl.textContent = '\u062E\u0637\u0623: ' + ((d && d.error) || '');
    }
  })
  .catch(function(){
    statusEl.textContent = '\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0627\u062A\u0635\u0627\u0644';
  });
}

// Generic Excel Import
var IMPORT_DEFS = {
  students: {
    title: "\u0642\u0627\u0639\u062F\u0629 \u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0637\u0644\u0628\u0629",
    refresh: "loadStudents",
    fields: [
      {key:"personal_id", ar:"\u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u0634\u062E\u0635\u064A"},
      {key:"student_name", ar:"\u0627\u0633\u0645 \u0627\u0644\u0637\u0627\u0644\u0628"},
      {key:"whatsapp", ar:"\u0647\u0627\u062A\u0641 \u0627\u0644\u0648\u0627\u062A\u0633\u0627\u0628 \u0627\u0644\u0645\u0639\u062A\u0645\u062F"},
      {key:"class_name", ar:"\u0627\u0644\u0635\u0641"},
      {key:"old_new_2026", ar:"\u0642\u062F\u064A\u0645 \u062C\u062F\u064A\u062F 2026"},
      {key:"registration_term2_2026", ar:"\u0627\u0644\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u0641\u0635\u0644 \u0627\u0644\u062B\u0627\u0646\u064A 2026"},
      {key:"group_name_student", ar:"\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629"},
      {key:"group_online", ar:"\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 (\u0627\u0644\u0627\u0648\u0646\u0644\u0627\u064A\u0646)"},
      {key:"final_result", ar:"\u0627\u0644\u0646\u062A\u064A\u062C\u0629 \u0627\u0644\u0646\u0647\u0627\u0626\u064A\u0629 (\u062A\u062D\u062F\u064A\u062F \u0627\u0644\u0645\u0633\u062A\u0648\u0649 2026)"},
      {key:"level_reached_2026", ar:"\u0627\u0644\u0649 \u0627\u064A\u0646 \u0648\u0635\u0644 \u0627\u0644\u0637\u0627\u0644\u0628 2026"},
      {key:"suitable_level_2026", ar:"\u0647\u0644 \u0627\u0644\u0637\u0627\u0644\u0628 \u0645\u0646\u0627\u0633\u0628 \u0644\u0647\u0630\u0627 \u0627\u0644\u0645\u0633\u062A\u0648\u0649 2026\u061F"},
      {key:"books_received", ar:"\u0627\u0633\u062A\u0644\u0627\u0645 \u0627\u0644\u0643\u062A\u0628"},
      {key:"teacher_2026", ar:"\u0627\u0644\u0645\u062F\u0631\u0633 2026"},
      {key:"installment1", ar:"\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u0627\u0648\u0644 2026"},
      {key:"installment2", ar:"\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u062B\u0627\u0646\u064A"},
      {key:"installment3", ar:"\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u062B\u0627\u0644\u062B"},
      {key:"installment4", ar:"\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u0631\u0627\u0628\u0639"},
      {key:"installment5", ar:"\u0627\u0644\u0642\u0633\u0637 \u0627\u0644\u062E\u0627\u0645\u0633"},
      {key:"mother_phone", ar:"\u0647\u0627\u062A\u0641 \u0627\u0644\u0627\u0645"},
      {key:"father_phone", ar:"\u0647\u0627\u062A\u0641 \u0627\u0644\u0627\u0628"},
      {key:"other_phone", ar:"\u0647\u0627\u062A\u0641 \u0627\u062E\u0631"},
      {key:"residence", ar:"\u0645\u0643\u0627\u0646 \u0627\u0644\u0633\u0643\u0646"},
      {key:"home_address", ar:"\u0639\u0646\u0648\u0627\u0646 \u0627\u0644\u0645\u0646\u0632\u0644"},
      {key:"road", ar:"\u0627\u0644\u0637\u0631\u064A\u0642"},
      {key:"complex_name", ar:"\u0627\u0644\u0645\u062C\u0645\u0639"},
      {key:"installment_type", ar:"\u0627\u062E\u062A\u064A\u0627\u0631 \u0646\u0648\u0639 \u0627\u0644\u062A\u0642\u0633\u064A\u0637"}
    ]
  },
  student_groups: {
    title: "\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0627\u062A",
    refresh: "loadGroups2",
    fields: [
      {key:"group_name", ar:"\u0627\u0633\u0645 \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629"},
      {key:"teacher_name", ar:"\u0627\u0633\u0645 \u0627\u0644\u0645\u062F\u0631\u0633"},
      {key:"level_course", ar:"\u0627\u0644\u0645\u0633\u062A\u0648\u0649 \u0627\u0648 \u0627\u0644\u0645\u0642\u0631\u0631"},
      {key:"level_course", ar:"\u0627\u0644\u0645\u0633\u062A\u0648\u0649 / \u0627\u0644\u0645\u0642\u0631\u0631"},
      {key:"last_reached", ar:"\u0627\u0644\u0645\u0642\u0631\u0631 \u0627\u0644\u0630\u064A \u062A\u0645 \u0627\u0644\u0648\u0635\u0648\u0644 \u0627\u0644\u064A\u0647 \u0627\u0644\u0641\u0635\u0644 \u0627\u0644\u0641\u0627\u0626\u062A"},
      {key:"study_time", ar:"\u0648\u0642\u062A \u0627\u0644\u062F\u0631\u0627\u0633\u0629"},
      {key:"ramadan_time", ar:"\u062A\u0648\u0642\u064A\u062A \u0634\u0647\u0631 \u0631\u0645\u0636\u0627\u0646"},
      {key:"online_time", ar:"\u062A\u0648\u0642\u064A\u062A \u0627\u0644\u0627\u0648\u0646\u0644\u0627\u064A\u0646 (\u0627\u0644\u0639\u0627\u062F\u064A)"},
      {key:"group_link", ar:"\u0631\u0627\u0628\u0637 \u0628\u062B \u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629"},
      {key:"session_minutes_normal", ar:"\u0645\u062F\u0629 \u0627\u0644\u062D\u0635\u0629 \u0628\u0627\u0644\u062F\u0642\u064A\u0642\u0629 \u0644\u0644\u0648\u0642\u062A \u0627\u0644\u0627\u0639\u062A\u064A\u0627\u062F\u064A (\u064A\u062F\u0648\u064A)"},
      {key:"session_duration", ar:"\u0627\u0644\u062D\u0635\u0629 \u0628\u0627\u0644\u062F\u0642\u064A\u0642\u0629 \u0644\u0644\u0627\u0648\u0646\u0644\u0627\u064A\u0646 \u0648\u0634\u0647\u0631 \u0631\u0645\u0636\u0627\u0646"},
      {key:"hours_in_person_auto", ar:"\u0639\u062F\u062F \u0627\u0644\u0633\u0627\u0639\u0627\u062A \u0627\u0644\u062D\u0636\u0648\u0631\u064A\u0629 (\u062A\u0644\u0642\u0627\u0626\u064A)"},
      {key:"hours_online_only", ar:"\u0639\u062F\u062F \u0633\u0627\u0639\u0627\u062A \u0627\u0644\u0627\u0648\u0646\u0644\u0627\u064A\u0646 \u0641\u0642\u0637"},
      {key:"hours_all_online", ar:"\u0627\u0644\u0633\u0627\u0639\u0627\u062A \u0627\u0644\u062F\u0631\u0627\u0633\u064A\u0629 \u0643\u0644\u0647\u0627 \u0628\u0627\u0644\u0627\u0648\u0646\u0644\u0627\u064A\u0646"},
      {key:"total_required_hours", ar:"\u0625\u062C\u0645\u0627\u0644\u064A \u0627\u0644\u0633\u0627\u0639\u0627\u062A \u0627\u0644\u0645\u0633\u062A\u062D\u0642\u0629"}
    ]
  },
  attendance: {
    title: "\u0633\u062C\u0644 \u0627\u0644\u063A\u064A\u0627\u0628",
    refresh: "loadAttendance",
    fields: [
      {key:"attendance_date", ar:"\u062A\u0627\u0631\u064A\u062E \u0623\u062E\u0630 \u0627\u0644\u062D\u0636\u0648\u0631"},
      {key:"day_name", ar:"\u0627\u0644\u064A\u0648\u0645"},
      {key:"group_name", ar:"\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629"},
      {key:"student_name", ar:"\u0627\u0633\u0645 \u0627\u0644\u0637\u0627\u0644\u0628"},
      {key:"contact_number", ar:"\u0631\u0642\u0645 \u0627\u0644\u062A\u0648\u0627\u0635\u0644"},
      {key:"status", ar:"\u0627\u0644\u062D\u0627\u0644\u0629"},
      {key:"message", ar:"\u0627\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"message_status", ar:"\u062D\u0627\u0644\u0629 \u0625\u0631\u0633\u0627\u0644 \u0627\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"study_status", ar:"\u062D\u0627\u0644\u0629 \u0627\u0644\u062F\u0631\u0627\u0633\u0629"}
    ]
  },
  taqseet: {
    title: "\u062C\u062F\u0648\u0644 \u0627\u0644\u062A\u0642\u0633\u064A\u0637",
    refresh: "",
    fields: [
      {key:"taqseet_method", ar:"\u0646\u0648\u0639 \u0627\u0644\u062A\u0642\u0633\u064A\u0637"},
      {key:"student_name", ar:"\u0627\u0633\u0645 \u0627\u0644\u0637\u0627\u0644\u0628"},
      {key:"course_amount", ar:"\u0645\u0628\u0644\u063A \u0627\u0644\u062F\u0648\u0631\u0629"},
      {key:"num_installments", ar:"\u0639\u062F\u062F \u0627\u0644\u0623\u0642\u0633\u0627\u0637"},
      {key:"study_hours", ar:"\u0633\u0627\u0639\u0627\u062A \u0627\u0644\u062F\u0631\u0627\u0633\u0629"},
      {key:"start_date", ar:"\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0628\u062F\u0621"},
      {key:"student_name", ar:"\u0627\u0644\u0627\u0633\u0645"},
      {key:"personal_id", ar:"\u0627\u0644\u0631\u0642\u0645"},
      {key:"registration_status", ar:"\u062D\u0627\u0644\u0629 \u0627\u0644\u062A\u0633\u062C\u064A\u0644"},
      {key:"course_amount", ar:"\u0627\u0644\u0645\u0628\u0644\u063A \u0627\u0644\u0627\u062C\u0645\u0627\u0644\u064A \u0627\u0644\u0645\u0633\u062A\u062D\u0642"},
      {key:"course_amount", ar:"\u0627\u0644\u0645\u0628\u0644\u063A \u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A \u0627\u0644\u0645\u0633\u062A\u062D\u0642"},
      {key:"inst1", ar:"\u0627\u0644\u0642\u0633\u0637 1"},
      {key:"inst2", ar:"\u0627\u0644\u0642\u0633\u0637 2"},
      {key:"inst3", ar:"\u0627\u0644\u0642\u0633\u0637 3"},
      {key:"inst4", ar:"\u0627\u0644\u0642\u0633\u0637 4"},
      {key:"inst5", ar:"\u0627\u0644\u0642\u0633\u0637 5"},
      {key:"inst6", ar:"\u0627\u0644\u0642\u0633\u0637 6"},
      {key:"inst7", ar:"\u0627\u0644\u0642\u0633\u0637 7"},
      {key:"inst8", ar:"\u0627\u0644\u0642\u0633\u0637 8"},
      {key:"inst9", ar:"\u0627\u0644\u0642\u0633\u0637 9"},
      {key:"inst10", ar:"\u0627\u0644\u0642\u0633\u0637 10"},
      {key:"inst11", ar:"\u0627\u0644\u0642\u0633\u0637 11"},
      {key:"inst12", ar:"\u0627\u0644\u0642\u0633\u0637 12"},
      {key:"msg1", ar:"\u0627\u0644\u0642\u0633\u0637 1 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg2", ar:"\u0627\u0644\u0642\u0633\u0637 2 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg3", ar:"\u0627\u0644\u0642\u0633\u0637 3 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg4", ar:"\u0627\u0644\u0642\u0633\u0637 4 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg5", ar:"\u0627\u0644\u0642\u0633\u0637 5 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg6", ar:"\u0627\u0644\u0642\u0633\u0637 6 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg7", ar:"\u0627\u0644\u0642\u0633\u0637 7 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg8", ar:"\u0627\u0644\u0642\u0633\u0637 8 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg9", ar:"\u0627\u0644\u0642\u0633\u0637 9 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg10", ar:"\u0627\u0644\u0642\u0633\u0637 10 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg11", ar:"\u0627\u0644\u0642\u0633\u0637 11 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"msg12", ar:"\u0627\u0644\u0642\u0633\u0637 12 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"total_paid", ar:"\u0627\u0644\u0645\u0628\u0644\u063A \u0627\u0644\u0645\u062F\u0641\u0648\u0639"},
      {key:"total_remaining", ar:"\u0627\u0644\u0645\u0628\u0644\u063A \u0627\u0644\u0645\u062A\u0628\u0642\u064A"},
      {key:"payment_status", ar:"\u062D\u0627\u0644\u0629 \u0627\u0644\u0645\u062F\u0641\u0648\u0639\u0627\u062A"},
    ]
  },
  evaluations: {
    title: "\u0627\u0644\u062a\u0642\u064a\u064a\u0645\u0627\u062a",
    refresh: "loadEvaluations",
    fields: [
      {key:"form_fill_date", ar:"\u062a\u0627\u0631\u064a\u062e \u0645\u0644\u0621 \u0627\u0644\u0625\u0633\u062a\u0645\u0627\u0631\u0629"},
      {key:"group_name", ar:"\u0627\u0644\u0645\u062c\u0645\u0648\u0639\u0629"},
      {key:"student_name", ar:"\u0627\u0644\u0627\u0633\u0645"},
      {key:"student_name", ar:"\u0627\u0633\u0645 \u0627\u0644\u0637\u0627\u0644\u0628"},
      {key:"class_participation", ar:"\u0627\u0644\u0645\u0634\u0627\u0631\u0643\u0629 \u062f\u0627\u062e\u0644 \u0627\u0644\u0635\u0641"},
      {key:"general_behavior", ar:"\u0627\u0644\u0633\u0644\u0648\u0643 \u0627\u0644\u0639\u0627\u0645"},
      {key:"behavior_notes", ar:"\u0627\u0644\u0645\u0644\u0627\u062d\u0638\u0627\u062a \u0639\u0644\u0649 \u0627\u0644\u0633\u0644\u0648\u0643"},
      {key:"reading", ar:"\u0627\u0644\u0642\u0631\u0627\u0621\u0629"},
      {key:"dictation", ar:"\u0627\u0644\u0625\u0645\u0644\u0627\u0621"},
      {key:"term_meanings", ar:"\u0645\u0639\u0627\u0646\u064a \u0627\u0644\u0645\u0635\u0637\u0644\u062d\u0627\u062a"},
      {key:"conversation", ar:"\u0627\u0644\u0645\u062d\u0627\u062f\u062b\u0629"},
      {key:"expression", ar:"\u0627\u0644\u062a\u0639\u0628\u064a\u0631"},
      {key:"grammar", ar:"\u0627\u0644\u0642\u0648\u0627\u0639\u062f"},
      {key:"notes", ar:"\u0627\u0644\u0645\u0644\u0627\u062d\u0638\u0627\u062a"}
    ]
  },
  payment_log: {
    title: "\u0633\u062c\u0644 \u0627\u0644\u062f\u0641\u0639",
    refresh: "loadPaymentLog",
    fields: [
      {key:"student_name", ar:"\u0627\u0644\u0627\u0633\u0645"},
      {key:"personal_id", ar:"الرقم"},
      {key:"registration_status", ar:"\u062d\u0627\u0644\u0629 \u0627\u0644\u062a\u0633\u062c\u064a\u0644"},
      {key:"course_amount", ar:"\u0645\u0628\u0644\u063a \u0627\u0644\u062f\u0648\u0631\u0629"},
      {key:"inst1", ar:"\u0627\u0644\u0642\u0633\u0637 1"},
      {key:"msg1", ar:"\u0627\u0644\u0642\u0633\u0637 1 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"inst2", ar:"\u0627\u0644\u0642\u0633\u0637 2"},
      {key:"msg2", ar:"\u0627\u0644\u0642\u0633\u0637 2 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"inst3", ar:"\u0627\u0644\u0642\u0633\u0637 3"},
      {key:"msg3", ar:"\u0627\u0644\u0642\u0633\u0637 3 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"inst4", ar:"\u0627\u0644\u0642\u0633\u0637 4"},
      {key:"msg4", ar:"\u0627\u0644\u0642\u0633\u0637 4 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"inst5", ar:"\u0627\u0644\u0642\u0633\u0637 5"},
      {key:"msg5", ar:"\u0627\u0644\u0642\u0633\u0637 5 \u0644\u0644\u0631\u0633\u0627\u0644\u0629"},
      {key:"total_paid", ar:"\u0627\u0644\u0645\u0628\u0644\u063a \u0627\u0644\u0645\u062f\u0641\u0648\u0639"},
      {key:"total_remaining", ar:"\u0627\u0644\u0645\u0628\u0644\u063a \u0627\u0644\u0645\u062a\u0628\u0642\u064a"},
      {key:"payment_status", ar:"\u062d\u0627\u0644\u0629 \u0627\u0644\u0645\u062f\u0641\u0648\u0639\u0627\u062a"}
    ]
  }
};
var genExcelRows = [];
var genExcelHeaders = [];
function openGenericExcelModal(preselectTable) {
  var sel = document.getElementById('genExcelTable');
  sel.value = preselectTable || '';
  document.getElementById('genExcelFileInput').value = '';
  document.getElementById('genExcelFileRow').style.display = sel.value ? 'block' : 'none';
  document.getElementById('genExcelStatus').textContent = '';
  document.getElementById('genExcelImportBtn').style.display = 'none';
  genExcelRows = []; genExcelHeaders = [];
  document.getElementById('genExcelModal').classList.add('open');
}
function closeGenericExcelModal() {
  document.getElementById('genExcelModal').classList.remove('open');
  genExcelRows = []; genExcelHeaders = [];
}
function onGenExcelTableChange() {
  var tbl = document.getElementById('genExcelTable').value;
  document.getElementById('genExcelFileRow').style.display = tbl ? 'block' : 'none';
  document.getElementById('genExcelFileInput').value = '';
  document.getElementById('genExcelStatus').textContent = '';
  document.getElementById('genExcelImportBtn').style.display = 'none';
  genExcelRows = []; genExcelHeaders = [];
}
function _countMatches(headers, defs){
  var n = 0;
  for(var i=0;i<headers.length;i++){
    var hn = _arNorm(headers[i]); if(!hn) continue;
    for(var j=0;j<defs.fields.length;j++){
      var f = defs.fields[j];
      if(hn === f.key || hn === _arNorm(f.ar)){ n++; break; }
    }
  }
  return n;
}
function _parseWith(data, opts){
  var wb = XLSX.read(data, opts);
  var sheet = wb.Sheets[wb.SheetNames[0]];
  return XLSX.utils.sheet_to_json(sheet, {header:1, defval:''});
}
function _findHeaderIdx(rows){
  var limit = Math.min(rows.length, 30);
  for(var i=0;i<limit;i++){
    var r = rows[i];
    if(r && r.some(function(c){ return String(c==null?'':c).trim() !== ''; })) return i;
  }
  return -1;
}
function _decodeBytes(data, enc){
  try { return new TextDecoder(enc, {fatal:false}).decode(data); }
  catch(e){ return null; }
}
function readGenericExcelFile(input) {
  var file = input.files[0]; if(!file) return;
  var tbl = document.getElementById('genExcelTable').value;
  var statusEl = document.getElementById('genExcelStatus');
  if(!tbl){ statusEl.textContent = "\u0627\u062E\u062A\u0631 \u0627\u0644\u062C\u062F\u0648\u0644 \u0623\u0648\u0644\u0627\u064B"; return; }
  var reader = new FileReader();
  reader.onload = function(e) {
    try {
      var data = new Uint8Array(e.target.result);
      var isCsv = /\.(csv|txt)$/i.test(file.name);
      var defs = IMPORT_DEFS[tbl];
      var best = null;
      var attempts = [];
      if(isCsv){
        var utf8 = _decodeBytes(data,'utf-8');
        var w1256 = _decodeBytes(data,'windows-1256');
        if(utf8)  attempts.push({type:'string', data:utf8,  label:'utf-8'});
        if(w1256) attempts.push({type:'string', data:w1256, label:'windows-1256'});
      }
      attempts.push({type:'array', data:data, label:'xlsx'});
      for(var a=0;a<attempts.length;a++){
        try {
          var rows = _parseWith(attempts[a].data, {type: attempts[a].type});
          if(!rows.length) continue;
          var hIdx = _findHeaderIdx(rows);
          if(hIdx < 0) continue;
          var headers = rows[hIdx].map(function(h){ return String(h==null?'':h).replace(/^\uFEFF/,'').trim(); });
          var m = _countMatches(headers, defs);
          if(!best || m > best.matchCount){
            best = { rows: rows, headers: headers, matchCount: m, cp: attempts[a].label, headerIdx: hIdx };
          }
          if(m > 0) break;
        } catch(ex) { /* try next */ }
      }
      if(!best || !best.rows.length || !best.headers.length){
        statusEl.textContent = "\u0627\u0644\u0645\u0644\u0641 \u0641\u0627\u0631\u063A";
        return;
      }
      genExcelHeaders = best.headers;
      genExcelRows = best.rows.slice(best.headerIdx + 1).filter(function(r){
        return r.some(function(c){ return String(c).trim() !== ''; });
      });
      try { console.log('[import] headers:', genExcelHeaders, 'codepage:', best.cp, 'matches:', best.matchCount); } catch(e){}
      var matched = [], unmatched = [];
      for(var i=0;i<genExcelHeaders.length;i++){
        var h = genExcelHeaders[i]; if(!h){ continue; }
        var hn = _arNorm(h), found = null;
        for(var j=0;j<defs.fields.length;j++){
          var f = defs.fields[j];
          if(hn === f.key || hn === _arNorm(f.ar)){ found = f.key; break; }
        }
        if(found) matched.push(h + ' \u2192 ' + found);
        else unmatched.push(h);
      }
      var html = '<div style="text-align:right;">'
        + '<div><b>' + genExcelRows.length + '</b> ' + (genExcelRows.length===1?"\u0635\u0641":"\u0635\u0641\u0648\u0641") + ' \u2014 '
        + '\u0645\u0637\u0627\u0628\u0642\u0629: <b>' + matched.length + '</b> / \u063A\u064A\u0631 \u0645\u0637\u0627\u0628\u0642: <b>' + unmatched.length + '</b>'
        + (best.cp ? ' <span style="color:#888;font-size:11px;">(' + best.cp + ')</span>' : '')
        + '</div>';
      if(unmatched.length){
        html += '<div style="margin-top:6px;color:#c62828;font-size:12px;">\u0627\u0644\u0623\u0639\u0645\u062F\u0629 \u0627\u0644\u062A\u064A \u0644\u0645 \u064A\u062A\u0645 \u0627\u0644\u062A\u0639\u0631\u0641 \u0639\u0644\u064A\u0647\u0627: ' + unmatched.map(function(u){return '"' + u + '"';}).join('\u060C ') + '</div>';
      }
      if(!matched.length){
        html += '<div style="margin-top:6px;color:#c62828;font-weight:700;">\u0644\u0627 \u062A\u0648\u062C\u062F \u0631\u0624\u0648\u0633 \u0645\u0639\u0631\u0648\u0641\u0629</div>'
          + '<div style="margin-top:4px;color:#555;font-size:11px;">\u0627\u0644\u0631\u0624\u0648\u0633 \u0627\u0644\u062A\u064A \u062A\u0645 \u0642\u0631\u0627\u0621\u062A\u0647\u0627: ' + genExcelHeaders.map(function(u){return '"' + u + '"';}).join('\u060C ') + '</div>';
      }
      html += '</div>';
      statusEl.innerHTML = html;
      document.getElementById('genExcelImportBtn').style.display = (genExcelRows.length > 0 && matched.length > 0) ? 'inline-flex' : 'none';
    } catch(err) {
      statusEl.textContent = "\u062E\u0637\u0623: " + err.message;
    }
  };
  reader.readAsArrayBuffer(file);
}
function _arNorm(s){
  var t = String(s==null?'':s).replace(/^\uFEFF/,'');
  try { t = t.normalize('NFKD'); } catch(e) {}
  return t
    .toLowerCase()
    .replace(/[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g,'')
    .replace(/[\u200B-\u200F\u202A-\u202E\u2060\uFEFF]/g,'')
    .replace(/\u0640/g,'')
    .replace(/[\u00A0\u1680\u180E\u2000-\u200A\u202F\u205F\u3000]/g,' ')
    .replace(/[\u0623\u0625\u0622\u0671]/g,'\u0627')
    .replace(/\u0629/g,'\u0647')
    .replace(/\u0649/g,'\u064A')
    .replace(/\s+/g,' ')
    .trim();
}
function _genColKey(raw) {
  // Generate a deterministic, safe column identifier from an arbitrary
  // (often Arabic) header string. ASCII slug if possible, otherwise a
  // DJB2 hash of the normalized text prefixed with "xcol_".
  var s = String(raw==null?'':raw);
  var slug = s.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,'');
  if (/^[a-z_][a-z0-9_]{0,63}$/.test(slug)) return slug;
  var norm = _arNorm(s);
  var h = 5381;
  for (var i=0; i<norm.length; i++){ h = ((h<<5) + h + norm.charCodeAt(i)) >>> 0; }
  return 'xcol_' + h.toString(36);
}
function mapGenericRow(headers, row, defs, opts) {
  // opts: { allowAutoCreate: bool, labelMap: {key->label} out-param }
  opts = opts || {};
  var result = {};
  for(var i=0; i<headers.length; i++){
    var rawHdr = headers[i];
    var h = _arNorm(rawHdr); if(!h) continue;       // skip empty headers
    var matched = false;
    for(var j=0; j<defs.fields.length; j++){
      var f = defs.fields[j];
      if(h === f.key || h === _arNorm(f.ar)){
        result[f.key] = String(row[i]==null?'':row[i]);
        if (opts.labelMap && !opts.labelMap[f.key]) {
          opts.labelMap[f.key] = String(rawHdr||'').trim() || f.ar;
        }
        matched = true;
        break;
      }
    }
    if (!matched && opts.allowAutoCreate) {
      var k = _genColKey(rawHdr);
      if (k) {
        result[k] = String(row[i]==null?'':row[i]);
        if (opts.labelMap) opts.labelMap[k] = String(rawHdr||'').trim();
      }
    }
  }
  return result;
}
function importGenericFromExcel() {
  var tbl = document.getElementById('genExcelTable').value;
  var defs = IMPORT_DEFS[tbl];
  if(!defs || !genExcelRows.length) return;
  var allowAutoCreate = (tbl === 'taqseet');
  var labelMap = {};
  // Preserve Excel row order exactly: iterate top-to-bottom with a plain for
  // loop, skip only rows where every raw cell is empty. Rows with any
  // non-empty cell pass through even if the mapping yields an empty dict
  // (no matching header — we still want the row represented).
  var mapped = [];
  for (var _i = 0; _i < genExcelRows.length; _i++) {
    var _raw = genExcelRows[_i];
    var _hasAny = false;
    if (_raw && _raw.length) {
      for (var _j = 0; _j < _raw.length; _j++) {
        var _c = _raw[_j];
        if (_c != null && String(_c).trim() !== '') { _hasAny = true; break; }
      }
    }
    if (!_hasAny) continue;
    mapped.push(mapGenericRow(genExcelHeaders, _raw, defs, {allowAutoCreate: allowAutoCreate, labelMap: labelMap}));
  }
  var btn = document.getElementById('genExcelImportBtn');
  var statusEl = document.getElementById('genExcelStatus');
  btn.disabled = true;
  btn.textContent = "\u062C\u0627\u0631\u064A \u0627\u0644\u0627\u0633\u062A\u064A\u0631\u0627\u062F...";
  // For taqseet: let the backend ALTER TABLE to add any Excel-header keys that
  // aren't already columns, and persist the Arabic labels so they render.
  var body = {table: tbl, rows: mapped};
  if (allowAutoCreate) { body.auto_create = true; body.column_labels = labelMap; }
  fetch('/api/import', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})
    .then(function(r){ return r.json(); })
    .then(function(d){
      btn.disabled = false;
      btn.textContent = "\u0627\u0633\u062A\u064A\u0631\u0627\u062F";
      if(d && d.ok){
        var ins = (d.inserted != null ? d.inserted : (d.imported || 0));
        var upd = d.updated || 0;
        var skp = (d.skipped != null ? d.skipped : (d.ignored || 0));
        var err = d.errors || 0;
        var parts = ["\u062A\u0645 \u0627\u0644\u0625\u062F\u0631\u0627\u062C: " + ins];
        if(upd) parts.push("\u062A\u062D\u062F\u064A\u062B: " + upd);
        if(skp) parts.push("\u062A\u062C\u0627\u0647\u0644: " + skp);
        if(err) parts.push("\u062E\u0637\u0623: " + err);
        statusEl.textContent = parts.join(" \u2014 ");
        try { window.dispatchEvent(new CustomEvent('mx-imported', {detail: d})); } catch(e) {}
        if(defs.refresh && typeof window[defs.refresh] === 'function') { try { window[defs.refresh](); } catch(e) {} }
        if(typeof showToast === 'function') showToast(parts.join(" \u2014 "));
        if(ins + upd > 0 && skp === 0 && err === 0) {
          setTimeout(closeGenericExcelModal, 1200);
        }
      } else {
        statusEl.textContent = "\u062E\u0637\u0623: " + ((d && d.error) || '');
      }
    })
    .catch(function(){
      btn.disabled = false;
      btn.textContent = "\u0627\u0633\u062A\u064A\u0631\u0627\u062F";
      statusEl.textContent = "\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0627\u062A\u0635\u0627\u0644";
    });
}

// &#x2500;&#x2500;&#x2500; Attendance Column Management &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;
var allAttColumns = [];

function loadAttColumns(callback) {
  fetch('/api/att-columns').then(function(r){ return r.json(); }).then(function(cols){
    allAttColumns = cols;
    if(callback) callback(cols);
  });
}

function openAttendanceTableEditModal() {
  loadAttColumns(function(cols) {
    // Populate dropdowns
    var delSel = document.getElementById('att_del_col');
    var renameSel = document.getElementById('att_rename_col');
    var afterSel = document.getElementById('att_after_col');
    delSel.innerHTML = '';
    renameSel.innerHTML = '';
    afterSel.innerHTML = '';
    cols.forEach(function(c) {
      var o1 = document.createElement('option'); o1.value = c.col_key; o1.innerHTML = c.col_label; delSel.appendChild(o1);
      var o2 = document.createElement('option'); o2.value = c.col_key; o2.innerHTML = c.col_label; renameSel.appendChild(o2);
      var o3 = document.createElement('option'); o3.value = c.col_key; o3.innerHTML = c.col_label; afterSel.appendChild(o3);
    });
    document.getElementById('att_new_col_name').value = '';
    document.getElementById('att_col_position').value = 'end';
    document.getElementById('att_after_col').style.display = 'none';
    fillAttRenameLabel();
    switchAttTab('add');
    document.getElementById('attendanceTableEditModal').style.display = 'flex';
  });
}

function closeAttendanceTableEditModal() {
  document.getElementById('attendanceTableEditModal').style.display = 'none';
}

function switchAttTab(tab) {
  var panels = ['attTabPanelAdd','attTabPanelDel','attTabPanelRename'];
  var btns = ['attTab1','attTab2','attTab3'];
  var idx = {add:0, del:1, rename:2}[tab];
  panels.forEach(function(p,i){ document.getElementById(p).style.display = i===idx?'block':'none'; });
  btns.forEach(function(b,i){ document.getElementById(b).classList.toggle('active', i===idx); });
}

function toggleAttPosition() {
  var pos = document.getElementById('att_col_position').value;
  document.getElementById('att_after_col').style.display = pos==='after'?'block':'none';
}

function fillAttRenameLabel() {
  var sel = document.getElementById('att_rename_col');
  var lbl = document.getElementById('att_rename_label');
  if(sel && sel.options[sel.selectedIndex]) lbl.value = sel.options[sel.selectedIndex].text;
}

function addAttendanceColumn() {
  var col_label = document.getElementById('att_new_col_name').value.trim();
  if(!col_label){ showToast('&#x623;&#x62F;&#x62E;&#x644; &#x627;&#x633;&#x645; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;','#e53935'); return; }
  var position = document.getElementById('att_col_position').value;
  var after_key = document.getElementById('att_after_col').value;
  fetch('/api/att-columns', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({col_label:col_label, position:position, after_key:after_key})})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('&#x62A;&#x645; &#x625;&#x636;&#x627;&#x641;&#x629; &#x627;&#x644;&#x639;&#x645;&#x648;&#x62F;','#00BCD4'); closeAttendanceTableEditModal(); loadAttendance(); }
      else { showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

function deleteAttendanceColumn() {
  var col_key = document.getElementById('att_del_col').value;
  if(!col_key) return;
  fetch('/api/att-columns/' + col_key, {method:'DELETE'})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('&#x62A;&#x645; &#x627;&#x644;&#x62D;&#x630;&#x641;','#e53935'); closeAttendanceTableEditModal(); loadAttendance(); }
      else { showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}

function updateAttendanceColumnLabel() {
  var col_key = document.getElementById('att_rename_col').value;
  var new_label = document.getElementById('att_rename_label').value.trim();
  if(!new_label||!col_key){ showToast('&#x623;&#x62F;&#x62E;&#x644; &#x627;&#x644;&#x627;&#x633;&#x645; &#x627;&#x644;&#x62C;&#x62F;&#x64A;&#x62F;','#e53935'); return; }
  fetch('/api/att-columns/' + col_key, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({col_label:new_label})})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('&#x62A;&#x645; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x639;&#x646;&#x648;&#x627;&#x646;','#00BCD4'); closeAttendanceTableEditModal(); loadAttendance(); }
      else { showToast(d.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x623;','#e53935'); }
    });
}
</script>
<script>
// Fix: pass vertical scroll events to page when table container can't scroll vertically
(function(){
  function fixScrollPassthrough(el){
    el.addEventListener('wheel',function(e){
      if(e.deltaY===0) return;
      var canUp=this.scrollTop>0;
      var canDown=this.scrollTop<(this.scrollHeight-this.offsetHeight-1);
      if(!canUp&&!canDown){e.preventDefault();window.scrollBy(0,e.deltaY);}
    },{passive:false});
  }
  document.querySelectorAll('.table-wrap').forEach(fixScrollPassthrough);
  var tw=document.getElementById('taqseetWrap');
  if(tw) fixScrollPassthrough(tw);
})();
</script>
</body>
</html>"""

def render_login(error=""):
    err_html = f'<div class="err">{error}</div>' if error else ""
    return LOGIN_HTML.replace("ERROR_PLACEHOLDER", err_html)

@app.route("/")
def index():
    session.clear()
    return render_login()

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_login()
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?",
                      (username, hp(password))).fetchone()
    if not user:
        return render_login("&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x62E;&#x62F;&#x645; &#x627;&#x648; &#x643;&#x644;&#x645;&#x629; &#x627;&#x644;&#x645;&#x631;&#x648;&#x631; &#x63A;&#x644;&#x637;"), 401
    session["user"] = dict(user)
    return redirect("/dashboard")

@app.route("/dashboard")
@login_required
def dashboard():
    user = session.get("user") or {}
    username = user.get("username") or user.get("name") or ""
    return HOME_HTML.replace("USER_PLACEHOLDER", username)

@app.route("/attendance")
@login_required
def attendance():
    return ATTENDANCE_HTML

@app.route("/database")
@login_required
def database():
    return DATABASE_HTML

@app.route("/api/students", methods=["GET"])
@login_required
def api_students_get():
    """Every student, each row annotated with `is_active` so the
    student-search modal can rank active matches first while still
    finding inactive ones."""
    db = get_db()
    act_col = (get_setting("students", "active_column", "registration_term2_2026") or "").strip()
    act_val = (get_setting("students", "active_value",  "تم التسجيل") or "").strip()
    act_col = act_col if _is_safe_ident(act_col) else ""
    rows = db.execute("SELECT * FROM students ORDER BY id ASC").fetchall()
    out = []
    for r in rows:
        d = dict(r)
        if act_col:
            v = (d.get(act_col) or "").strip() if isinstance(d.get(act_col), str) else d.get(act_col)
            d["is_active"] = (str(v or "").strip() == act_val)
        else:
            d["is_active"] = True
        out.append(d)
    return jsonify({"students": out})

@app.route("/api/students", methods=["POST"])
@login_required
def api_students_add():
    d = request.get_json()
    try:
        db = get_db()
        db.execute("""INSERT INTO students
            (personal_id,student_name,whatsapp,class_name,old_new_2026,registration_term2_2026,
             group_name_student,group_online,final_result,level_reached_2026,suitable_level_2026,
             books_received,teacher_2026,installment1,installment2,installment3,installment4,
             installment5,mother_phone,father_phone,other_phone,residence,home_address,road,complex_name,installment_type)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d.get("personal_id"), d.get("student_name"), d.get("whatsapp"),
             d.get("class_name"), d.get("old_new_2026"), d.get("registration_term2_2026"),
             d.get("group_name_student"), d.get("group_online"),
             d.get("final_result"), d.get("level_reached_2026"), d.get("suitable_level_2026"),
             d.get("books_received"), d.get("teacher_2026"),
             d.get("installment1"), d.get("installment2"), d.get("installment3"),
             d.get("installment4"), d.get("installment5"),
             d.get("mother_phone"), d.get("father_phone"), d.get("other_phone"),
             d.get("residence"), d.get("home_address"), d.get("road"), d.get("complex_name"), d.get("installment_type","")))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/students/<int:sid>", methods=["PUT"])
@login_required
def api_students_update(sid):
    d = request.get_json()
    try:
        db = get_db()
        db.execute("""UPDATE students SET
            personal_id=?,student_name=?,whatsapp=?,class_name=?,old_new_2026=?,
            registration_term2_2026=?,group_name_student=?,group_online=?,
            final_result=?,level_reached_2026=?,suitable_level_2026=?,books_received=?,
            teacher_2026=?,installment1=?,installment2=?,installment3=?,installment4=?,
            installment5=?,mother_phone=?,father_phone=?,other_phone=?,residence=?,
            home_address=?,road=?,complex_name=?,installment_type=?
            WHERE id=?""",
            (d.get("personal_id"), d.get("student_name"), d.get("whatsapp"),
             d.get("class_name"), d.get("old_new_2026"), d.get("registration_term2_2026"),
             d.get("group_name_student"), d.get("group_online"),
             d.get("final_result"), d.get("level_reached_2026"), d.get("suitable_level_2026"),
             d.get("books_received"), d.get("teacher_2026"),
             d.get("installment1"), d.get("installment2"), d.get("installment3"),
             d.get("installment4"), d.get("installment5"),
             d.get("mother_phone"), d.get("father_phone"), d.get("other_phone"),
             d.get("residence"), d.get("home_address"), d.get("road"), d.get("complex_name"), d.get("installment_type"), sid))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/students/<int:sid>", methods=["DELETE"])
@login_required
def api_students_delete(sid):
    try:
        db = get_db()
        db.execute("DELETE FROM students WHERE id=?", (sid,))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/students/<int:sid>/details", methods=["GET"])
@login_required
def api_student_details(sid):
    db = get_db()
    student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    if not student:
        return jsonify({"ok": False, "error": "not found"}), 404
    s_dict = dict(student)
    pay_rows = db.execute(
        "SELECT inst_num, inst_type, price, paid FROM student_payments WHERE student_id=? ORDER BY inst_num",
        (sid,)
    ).fetchall()
    payments = [dict(r) for r in pay_rows]
    def _num(v):
        try: return float(v or 0)
        except Exception: return 0.0
    total_paid = sum(_num(p.get("paid")) for p in payments)
    total_price = sum(_num(p.get("price")) for p in payments)
    remaining = total_price - total_paid

    # ── Paylog record lookup ──────────────────────────────────────
    # Users asked for the سجل الدفع row matched against this student
    # (by personal_id first, falling back to name). All table + column
    # names flow through get_setting so an admin can repoint them
    # from the /settings page without code changes.
    def _plcfg(comp, default):
        v = get_setting('paylog', comp, default)
        return v if _is_safe_ident(v) else default
    pl_table   = _plcfg('table',                 'payment_log')
    pl_name    = _plcfg('student_name_column',   'student_name')
    pl_pid     = _plcfg('personal_id_column',    'personal_id')
    pl_amount  = _plcfg('course_amount_column',  'course_amount')
    pl_paid    = _plcfg('total_paid_column',     'total_paid')
    pl_remain  = _plcfg('total_remaining_column','total_remaining')
    pl_status  = _plcfg('status_column',         'payment_status')
    pl_record = None
    # Ladder of lookup attempts. Stops on first hit. Covers the common
    # failure modes the user reported: extra whitespace, internal
    # whitespace runs, one side has the name but the other doesn't have
    # a personal_id, Arabic prefix/suffix differences.
    try:
        live_pl_cols = set(get_table_columns(pl_table))
        if live_pl_cols:
            pid_raw  = (s_dict.get("personal_id") or "").strip()
            name_raw = (s_dict.get("student_name") or "").strip()
            name_collapsed = " ".join(name_raw.split())  # collapse whitespace runs
            attempts = []
            if pid_raw and pl_pid in live_pl_cols:
                attempts.append((
                    "TRIM(" + pl_pid + ") = ?",
                    (pid_raw,),
                ))
            if name_collapsed and pl_name in live_pl_cols:
                # Exact trim match
                attempts.append((
                    "TRIM(" + pl_name + ") = ?",
                    (name_collapsed,),
                ))
                # Fuzzy contains in either direction — covers cases where
                # one table stores the family name and the other has the
                # full four-part name.
                attempts.append((
                    "TRIM(" + pl_name + ") LIKE ?",
                    ("%" + name_collapsed + "%",),
                ))
                attempts.append((
                    "? LIKE '%' || TRIM(" + pl_name + ") || '%'",
                    (name_collapsed,),
                ))
            for where, params in attempts:
                try:
                    row = db.execute(
                        "SELECT * FROM " + pl_table + " WHERE " + where + " LIMIT 1",
                        params,
                    ).fetchone()
                    if row:
                        pl_record = dict(row)
                        break
                except Exception:
                    continue
            # Final fallback: if still no hit, scan every paylog row and
            # compare names via _att_normalize_ar, which folds alef/yeh/
            # teh-marbouta variants, drops tashkeel, and — crucially —
            # collapses internal whitespace runs that SQL TRIM() leaves
            # behind. Table is small (hundreds of rows), so cost is fine.
            if pl_record is None and name_collapsed and pl_name in live_pl_cols:
                try:
                    target = _att_normalize_ar(name_collapsed)
                    if target:
                        rows = db.execute("SELECT * FROM " + pl_table).fetchall()
                        for r in rows:
                            other = _att_normalize_ar((r[pl_name] or "").strip())
                            if not other:
                                continue
                            if other == target or target in other or other in target:
                                pl_record = dict(r)
                                break
                except Exception:
                    pass
    except Exception:
        pl_record = None

    paylog_payload = None
    if pl_record:
        # Normalize into the shape the client renders. The 5 installment
        # slots follow the paylog schema's inst1..inst5 / msg1..msg5
        # columns; kept out of get_setting because they're a convention,
        # not user-configurable table mappings.
        installments = []
        for n in range(1, 6):
            installments.append({
                "num":    n,
                "amount": pl_record.get("inst" + str(n)) or "",
                "status": pl_record.get("msg"  + str(n)) or "",
            })
        paylog_payload = {
            "registration_status": pl_record.get("registration_status") or "",
            "course_amount":       pl_record.get(pl_amount) or "",
            "total_paid":          pl_record.get(pl_paid)   or "",
            "total_remaining":     pl_record.get(pl_remain) or "",
            "payment_status":      pl_record.get(pl_status) or "",
            "installments":        installments,
        }
    # Attendance rollup by student_name. Status labels match what the
    # attendance modal writes: حاضر / غائب / متأخر / معتذر.
    STATUS_PRESENT = "\u062D\u0627\u0636\u0631"
    STATUS_ABSENT  = "\u063A\u0627\u0626\u0628"
    STATUS_LATE    = "\u0645\u062A\u0623\u062E\u0631"
    STATUS_EXCUSED = "\u0645\u0639\u062A\u0630\u0631"
    student_name = s_dict.get("student_name") or ""
    att_rows = db.execute(
        "SELECT status FROM attendance WHERE student_name=?",
        (student_name,)
    ).fetchall() if student_name else []
    total = len(att_rows)
    def _count(label):
        return sum(1 for r in att_rows if (r["status"] or "").strip() == label)
    present = _count(STATUS_PRESENT)
    absent  = _count(STATUS_ABSENT)
    late    = _count(STATUS_LATE)
    excused = _count(STATUS_EXCUSED)
    def _pct(n):
        return round(n / total * 100, 1) if total else 0.0
    return jsonify({
        "ok": True,
        "student": s_dict,
        "payments": payments,
        "payment_totals": {
            "paid": total_paid,
            "price": total_price,
            "remaining": remaining,
        },
        "attendance": {
            "total": total,
            "present": present,
            "absent": absent,
            "late": late,
            "excused": excused,
            "present_rate": _pct(present),
            "absent_rate":  _pct(absent),
            "late_rate":    _pct(late),
        },
        "paylog": paylog_payload,
    })

@app.route("/api/students/bulk", methods=["POST"])
@login_required
def api_students_bulk():
    d = request.get_json()
    rows = d.get("rows", [])
    ok_count = 0
    errors = []
    db = get_db()
    for s in rows:
        try:
            db.execute("""INSERT OR IGNORE INTO students (personal_id,student_name,whatsapp,class_name,old_new_2026,registration_term2_2026,group_name_student,group_online,final_result,level_reached_2026,suitable_level_2026,books_received,teacher_2026,installment1,installment2,installment3,installment4,installment5,mother_phone,father_phone,other_phone,residence,home_address,road,complex_name) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (s.get("personal_id"), s.get("student_name"), s.get("whatsapp"), s.get("class_name"), s.get("old_new_2026"), s.get("registration_term2_2026"), s.get("group_name_student"), s.get("group_online"), s.get("final_result"), s.get("level_reached_2026"), s.get("suitable_level_2026"), s.get("books_received"), s.get("teacher_2026"), s.get("installment1"), s.get("installment2"), s.get("installment3"), s.get("installment4"), s.get("installment5"), s.get("mother_phone"), s.get("father_phone"), s.get("other_phone"), s.get("residence"), s.get("home_address"), s.get("road"), s.get("complex_name")))
            ok_count += 1
        except Exception as ex:
            errors.append(str(ex))
    db.commit()
    return jsonify({"ok": True, "imported": ok_count, "errors": len(errors)})

@app.route("/api/groups/bulk", methods=["POST"])
@login_required
def api_groups_bulk():
    d = request.get_json()
    rows = d.get("rows", [])
    ok_count = 0
    errors = []
    db = get_db()
    for g in rows:
        try:
            db.execute("""INSERT INTO student_groups (group_name,teacher_name,level_course,last_reached,study_time,ramadan_time,online_time,group_link,session_duration) VALUES(?,?,?,?,?,?,?,?,?)""",
                (g.get("group_name"), g.get("teacher_name"), g.get("level_course"), g.get("last_reached"), g.get("study_time"), g.get("ramadan_time"), g.get("online_time"), g.get("group_link"), g.get("session_duration")))
            ok_count += 1
        except Exception as ex:
            errors.append(str(ex))
    db.commit()
    return jsonify({"ok": True, "imported": ok_count, "errors": len(errors)})

@app.route("/api/columns", methods=["GET"])
@login_required
def api_columns_get():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS column_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1,
        col_type TEXT DEFAULT 'نص',
        col_options TEXT DEFAULT '')""")
    if db.execute("SELECT COUNT(*) FROM column_labels").fetchone()[0] == 0:
        default_cols = [
            ("personal_id","&#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A;",1),("student_name","&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;",2),("whatsapp","&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x648;&#x627;&#x62A;&#x633;&#x627;&#x628; &#x627;&#x644;&#x645;&#x639;&#x62A;&#x645;&#x62F;",3),
            ("class_name","&#x627;&#x644;&#x635;&#x641;",4),("old_new_2026","&#x642;&#x62F;&#x64A;&#x645; &#x62C;&#x62F;&#x64A;&#x62F; 2026",5),("registration_term2_2026","&#x62A;&#x633;&#x62C;&#x64A;&#x644; &#x627;&#x644;&#x641;&#x635;&#x644; &#x627;&#x644;&#x62B;&#x627;&#x646;&#x64A; 2026",6),
            ("group_name_student","&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;",7),("group_online","&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; (&#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646;)",8),
            ("final_result","&#x627;&#x644;&#x646;&#x62A;&#x64A;&#x62C;&#x629; &#x627;&#x644;&#x646;&#x647;&#x627;&#x626;&#x64A;&#x629; (&#x62A;&#x62D;&#x62F;&#x64A;&#x62F; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 2026)",9),
            ("level_reached_2026","&#x627;&#x644;&#x649; &#x627;&#x64A;&#x646; &#x648;&#x635;&#x644; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; 2026",10),("suitable_level_2026","&#x647;&#x644; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x645;&#x646;&#x627;&#x633;&#x628; &#x644;&#x647;&#x630;&#x627; &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 2026&#x61F;",11),
            ("books_received","&#x627;&#x633;&#x62A;&#x644;&#x627;&#x645; &#x627;&#x644;&#x643;&#x62A;&#x628;",12),("teacher_2026","&#x627;&#x644;&#x645;&#x62F;&#x631;&#x633; 2026",13),
            ("installment1","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x627;&#x648;&#x644; 2026",14),("installment2","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62B;&#x627;&#x646;&#x64A;",15),("installment3","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62B;&#x627;&#x644;&#x62B;",16),
            ("installment4","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x631;&#x627;&#x628;&#x639;",17),("installment5","&#x627;&#x644;&#x642;&#x633;&#x637; &#x627;&#x644;&#x62E;&#x627;&#x645;&#x633;",18),
            ("mother_phone","&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x645;",19),("father_phone","&#x647;&#x627;&#x62A;&#x641; &#x627;&#x644;&#x627;&#x628;",20),("other_phone","&#x647;&#x627;&#x62A;&#x641; &#x627;&#x62E;&#x631;",21),
            ("residence","&#x645;&#x643;&#x627;&#x646; &#x627;&#x644;&#x633;&#x643;&#x646;",22),("home_address","&#x639;&#x646;&#x648;&#x627;&#x646; &#x627;&#x644;&#x645;&#x646;&#x632;&#x644;",23),("road","&#x627;&#x644;&#x637;&#x631;&#x64A;&#x642;",24),("complex_name","&#x627;&#x644;&#x645;&#x62C;&#x645;&#x639;",25),
            ("installment_type","&#x627;&#x62E;&#x62A;&#x64A;&#x627;&#x631; &#x646;&#x648;&#x639; &#x627;&#x644;&#x62A;&#x642;&#x633;&#x64A;&#x637;",26),
        ]
        for key,label,order in default_cols:
            try:
                db.execute("INSERT INTO column_labels(col_key,col_label,col_order) VALUES(?,?,?)",(key,label,order))
            except: pass
        db.commit()
    rows = db.execute("SELECT col_key,col_label,col_order,is_visible FROM column_labels ORDER BY col_order").fetchall()
    return jsonify({"columns": [dict(r) for r in rows]})

@app.route("/api/columns", methods=["POST"])
@login_required
def api_columns_add():
    d = request.get_json()
    col_key = d.get("col_key","").strip().replace(" ","_").lower()
    col_label = d.get("col_label","").strip()
    position = d.get("position","end")
    after_col = d.get("after_col","")
    if not col_key or not col_label:
        return jsonify({"ok":False,"error":"missing data"}),400
    db = get_db()
    try:
        all_cols = db.execute("SELECT col_key,col_order FROM column_labels ORDER BY col_order").fetchall()
        if position == "start":
            new_order = 0
            for row in all_cols:
                db.execute("UPDATE column_labels SET col_order=col_order+1 WHERE col_key=?", (row[0],))
        elif position == "after" and after_col:
            after_row = db.execute("SELECT col_order FROM column_labels WHERE col_key=?", (after_col,)).fetchone()
            if after_row:
                new_order = after_row[0] + 1
                for row in all_cols:
                    if row[1] >= new_order:
                        db.execute("UPDATE column_labels SET col_order=col_order+1 WHERE col_key=?", (row[0],))
            else:
                max_order = db.execute("SELECT MAX(col_order) FROM column_labels").fetchone()[0] or 0
                new_order = max_order + 1
        else:
            max_order = db.execute("SELECT MAX(col_order) FROM column_labels").fetchone()[0] or 0
            new_order = max_order + 1
        db.execute("INSERT INTO column_labels(col_key,col_label,col_order) VALUES(?,?,?)",(col_key,col_label,new_order))
        db.execute("ALTER TABLE students ADD COLUMN "+col_key+" TEXT")
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400
@app.route("/api/columns/<col_key>", methods=["DELETE"])
@login_required
def api_columns_delete(col_key):
    db = get_db()
    try:
        pragma = db.execute("PRAGMA table_info(students)").fetchall()
        all_cols = [r[1] for r in pragma]
        if col_key in all_cols:
            db.execute('ALTER TABLE students DROP COLUMN "' + col_key + '"')
        db.execute("DELETE FROM column_labels WHERE col_key=?",(col_key,))
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400

@app.route("/api/columns/<col_key>", methods=["PUT"])
@login_required
def api_columns_update(col_key):
    d = request.get_json()
    new_label = d.get("col_label","").strip()
    if not new_label:
        return jsonify({"ok":False,"error":"missing label"}),400
    db = get_db()
    try:
        db.execute("UPDATE column_labels SET col_label=? WHERE col_key=?",(new_label,col_key))
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400

@app.route("/api/group-columns", methods=["GET"])
@login_required
def api_group_columns_get():
    db = get_db()
    rows = db.execute("SELECT col_key,col_label,col_order,is_visible FROM group_col_labels ORDER BY col_order").fetchall()
    return jsonify({"columns": [dict(r) for r in rows]})

@app.route("/api/group-columns", methods=["POST"])
@login_required
def api_group_columns_add():
    d = request.get_json()
    col_key = d.get("col_key","").strip().replace(" ","_").lower()
    col_label = d.get("col_label","").strip()
    position = d.get("position","end")
    after_col = d.get("after_col","")
    if not col_key or not col_label:
        return jsonify({"ok":False,"error":"missing data"}),400
    db = get_db()
    try:
        all_cols = db.execute("SELECT col_key,col_order FROM group_col_labels ORDER BY col_order").fetchall()
        if position == "start":
            new_order = 0
            for row in all_cols:
                db.execute("UPDATE group_col_labels SET col_order=col_order+1 WHERE col_key=?", (row[0],))
        elif position == "after" and after_col:
            after_row = db.execute("SELECT col_order FROM group_col_labels WHERE col_key=?", (after_col,)).fetchone()
            if after_row:
                new_order = after_row[0] + 1
                for row in all_cols:
                    if row[1] >= new_order:
                        db.execute("UPDATE group_col_labels SET col_order=col_order+1 WHERE col_key=?", (row[0],))
            else:
                max_order = db.execute("SELECT MAX(col_order) FROM group_col_labels").fetchone()[0] or 0
                new_order = max_order + 1
        else:
            max_order = db.execute("SELECT MAX(col_order) FROM group_col_labels").fetchone()[0] or 0
            new_order = max_order + 1
        db.execute("INSERT INTO group_col_labels(col_key,col_label,col_order) VALUES(?,?,?)",(col_key,col_label,new_order))
        db.execute("ALTER TABLE student_groups ADD COLUMN "+col_key+" TEXT")
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400

@app.route("/api/group-columns/<col_key>", methods=["DELETE"])
@login_required
def api_group_columns_delete(col_key):
    safe_key = "".join(c for c in col_key if c.isalnum() or c == "_")
    if not safe_key or safe_key != col_key:
        return jsonify({"ok": False, "error": "invalid column name"}), 400
    db = get_db()
    try:
        db.execute('ALTER TABLE student_groups DROP COLUMN "' + safe_key + '"')
    except Exception:
        pass  # Column may not exist on the physical table; label row still needs to go.
    db.execute("DELETE FROM group_col_labels WHERE col_key=?", (col_key,))
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/group-columns/<col_key>", methods=["PUT"])
@login_required
def api_group_columns_update(col_key):
    d = request.get_json()
    new_label = d.get("col_label","").strip()
    if not new_label:
        return jsonify({"ok":False,"error":"missing label"}),400
    db = get_db()
    try:
        db.execute("UPDATE group_col_labels SET col_label=? WHERE col_key=?",(new_label,col_key))
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400


# --- Payment Log (سجل الدفع) ---------------------------------------------

def _payment_log_writable_cols(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(payment_log)").fetchall()]
    return [c for c in cols if c not in ("id", "created_at")]

@app.route("/api/payment-log", methods=["GET"])
@login_required
def api_payment_log_get():
    db = get_db()
    rows = db.execute("SELECT * FROM payment_log ORDER BY id ASC").fetchall()
    return jsonify({"rows": [dict(r) for r in rows]})

@app.route("/api/payment-log", methods=["POST"])
@login_required
def api_payment_log_add():
    d = request.get_json() or {}
    db = get_db()
    try:
        cols = _payment_log_writable_cols(db)
        placeholders = ",".join(["?"] * len(cols))
        values = tuple(d.get(c) for c in cols)
        db.execute("INSERT INTO payment_log (" + ",".join(cols) + ") VALUES (" + placeholders + ")", values)
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/payment-log/<int:rid>", methods=["PUT"])
@login_required
def api_payment_log_update(rid):
    d = request.get_json() or {}
    db = get_db()
    try:
        cols = [c for c in _payment_log_writable_cols(db) if c in d]
        if not cols:
            return jsonify({"ok": True})
        set_clause = ",".join([c + "=?" for c in cols])
        values = tuple(d.get(c) for c in cols) + (rid,)
        db.execute("UPDATE payment_log SET " + set_clause + " WHERE id=?", values)
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/payment-log/<int:rid>", methods=["DELETE"])
@login_required
def api_payment_log_delete(rid):
    try:
        db = get_db()
        db.execute("DELETE FROM payment_log WHERE id=?", (rid,))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/paylog-columns", methods=["GET"])
@login_required
def api_paylog_columns_get():
    db = get_db()
    rows = db.execute("SELECT col_key,col_label,col_order,is_visible FROM paylog_col_labels ORDER BY col_order").fetchall()
    return jsonify({"columns": [dict(r) for r in rows]})

@app.route("/api/paylog-columns", methods=["POST"])
@login_required
def api_paylog_columns_add():
    d = request.get_json()
    col_key = d.get("col_key","").strip().replace(" ","_").lower()
    col_label = d.get("col_label","").strip()
    position = d.get("position","end")
    after_col = d.get("after_col","")
    if not col_key or not col_label:
        return jsonify({"ok":False,"error":"missing data"}),400
    safe_key = "".join(c for c in col_key if c.isalnum() or c == "_")
    if not safe_key or safe_key != col_key:
        return jsonify({"ok":False,"error":"invalid column name"}),400
    db = get_db()
    try:
        all_cols = db.execute("SELECT col_key,col_order FROM paylog_col_labels ORDER BY col_order").fetchall()
        if position == "start":
            new_order = 0
            for row in all_cols:
                db.execute("UPDATE paylog_col_labels SET col_order=col_order+1 WHERE col_key=?", (row[0],))
        elif position == "after" and after_col:
            after_row = db.execute("SELECT col_order FROM paylog_col_labels WHERE col_key=?", (after_col,)).fetchone()
            if after_row:
                new_order = after_row[0] + 1
                for row in all_cols:
                    if row[1] >= new_order:
                        db.execute("UPDATE paylog_col_labels SET col_order=col_order+1 WHERE col_key=?", (row[0],))
            else:
                max_order = db.execute("SELECT MAX(col_order) FROM paylog_col_labels").fetchone()[0] or 0
                new_order = max_order + 1
        else:
            max_order = db.execute("SELECT MAX(col_order) FROM paylog_col_labels").fetchone()[0] or 0
            new_order = max_order + 1
        db.execute("INSERT INTO paylog_col_labels(col_key,col_label,col_order) VALUES(?,?,?)",(col_key,col_label,new_order))
        db.execute("ALTER TABLE payment_log ADD COLUMN "+col_key+" TEXT")
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400

@app.route("/api/paylog-columns/<col_key>", methods=["DELETE"])
@login_required
def api_paylog_columns_delete(col_key):
    safe_key = "".join(c for c in col_key if c.isalnum() or c == "_")
    if not safe_key or safe_key != col_key:
        return jsonify({"ok": False, "error": "invalid column name"}), 400
    db = get_db()
    try:
        db.execute('ALTER TABLE payment_log DROP COLUMN "' + safe_key + '"')
    except Exception:
        pass
    db.execute("DELETE FROM paylog_col_labels WHERE col_key=?", (col_key,))
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/paylog-columns/<col_key>", methods=["PUT"])
@login_required
def api_paylog_columns_update(col_key):
    d = request.get_json()
    new_label = d.get("col_label","").strip()
    if not new_label:
        return jsonify({"ok":False,"error":"missing label"}),400
    db = get_db()
    try:
        db.execute("UPDATE paylog_col_labels SET col_label=? WHERE col_key=?",(new_label,col_key))
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400


# --- Unified Table Management (works for all tables) ---------------------

# Maps a frontend table key to (db_table_name, labels_table_name_or_None).
# Also accepts numeric ids for entries in custom_tables.
_TABLE_MAP = {
    "students":       ("students",        "column_labels"),
    "groups":         ("student_groups",  "group_col_labels"),
    "student_groups": ("student_groups",  "group_col_labels"),
    "attendance":     ("attendance",      "att_col_labels"),
    "evaluations":    ("evaluations",     "eval_col_labels"),
    "evals":          ("evaluations",     "eval_col_labels"),
    "payment_log":    ("payment_log",     "paylog_col_labels"),
    "paylog":         ("payment_log",     "paylog_col_labels"),
    "taqseet":        ("taqseet",         "taqseet_col_labels"),
}

def _resolve_table(tid):
    """Return (db_table, labels_table) for a table identifier.

    tid can be either a built-in table key (e.g. 'students', 'payment_log')
    or a stringified numeric id that points at a row in custom_tables.
    Returns (None, None) if not found.
    """
    tid_str = str(tid or "").strip()
    if tid_str.isdigit():
        db = get_db()
        try:
            row = db.execute("SELECT tbl_name FROM custom_tables WHERE id=?", (int(tid_str),)).fetchone()
            if row:
                return (row[0], None)
        except Exception:
            return (None, None)
        return (None, None)
    return _TABLE_MAP.get(tid_str, (None, None))


def _is_safe_ident(s):
    import re as _re
    return bool(s and _re.match(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$', s))


# ─── Dynamic Configuration System ─────────────────────────────────────────
# Reads settings rows to remap table/column references across the app.
# Never raises — falls back to the caller-provided default if the settings
# row is missing or the DB is in an incomplete state.
def get_setting(page, component, default=''):
    try:
        db = get_db()
        row = db.execute(
            "SELECT value FROM settings WHERE page=? AND component=?",
            (page, component),
        ).fetchone()
        if row is None:
            return default
        v = row[0] if hasattr(row, '__getitem__') else None
        if v is None or v == '':
            return default
        return v
    except Exception:
        return default


def get_all_tables():
    """List every user-visible table in the live DB."""
    try:
        db = get_db()
        if USE_PG:
            rows = db.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_type='BASE TABLE' "
                "ORDER BY table_name"
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def get_table_columns(table_name):
    """List every column in the given table. Safe-name validated."""
    if not _is_safe_ident(table_name):
        return []
    try:
        db = get_db()
        rows = db.execute("PRAGMA table_info(" + table_name + ")").fetchall()
        return [r[1] for r in rows]
    except Exception:
        return []


@app.route('/api/settings', methods=['GET'])
@login_required
def api_settings_get():
    try:
        db = get_db()
        rows = db.execute(
            "SELECT page, component, label, value, value_type FROM settings "
            "ORDER BY page, id"
        ).fetchall()
        by_page = {}
        for r in rows:
            p = r[0] if hasattr(r, '__getitem__') else ''
            by_page.setdefault(p, []).append({
                "page": r[0],
                "component": r[1],
                "label": r[2],
                "value": r[3] or '',
                "value_type": r[4] or 'table_column',
            })
        return jsonify({"ok": True, "settings": by_page})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 500


@app.route('/api/settings', methods=['PATCH'])
@login_required
def api_settings_patch():
    d = request.get_json() or {}
    page = (d.get('page') or '').strip()
    component = (d.get('component') or '').strip()
    value = d.get('value')
    value = '' if value is None else str(value).strip()
    if not page or not component:
        return jsonify({"ok": False, "error": "page and component required"}), 400
    try:
        db = get_db()
        cur = db.execute(
            "UPDATE settings SET value=? WHERE page=? AND component=?",
            (value, page, component),
        )
        if cur.rowcount == 0:
            # Create if missing — label uses component name as fallback.
            db.execute(
                "INSERT INTO settings(page,component,label,value) VALUES(?,?,?,?)",
                (page, component, component, value),
            )
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400


# ─── Arabic display labels for tables / columns ─────────────────────
# LABELS RULE (see CLAUDE.md): users must NEVER see internal DB names
# like "students" or "group_name_student" in any dropdown, form, or
# table-edit modal. Every surface that renders a table or column name
# pulls its display label from table_labels / the per-table *_col_labels
# table, falling back to these built-in dicts, and only finally to the
# raw identifier.

BUILT_IN_TABLE_LABELS = {
    "students":          "قاعدة بيانات الطلبة",
    "student_groups":    "المجموعات",
    "attendance":        "سجل الغياب",
    "taqseet":           "جدول التقسيط",
    "evaluations":       "التقييمات",
    "payment_log":       "سجل الدفع",
    "student_payments":  "دفعات الطلبة",
    "session_durations": "مدة الحصص",
    "message_templates": "قوالب الرسائل",
    "message_log":       "سجل الرسائل",
    "message_reminders": "تذكيرات الرسائل",
    "users":             "المستخدمون",
    "settings":          "الإعدادات",
    "schema_migrations": "سجل الترقيات",
    "table_labels":      "تسميات الجداول",
    "column_labels":     "تسميات أعمدة الطلبة",
    "group_col_labels":  "تسميات أعمدة المجموعات",
    "att_col_labels":    "تسميات أعمدة الغياب",
    "eval_col_labels":   "تسميات أعمدة التقييمات",
    "paylog_col_labels": "تسميات أعمدة سجل الدفع",
    "taqseet_col_labels":"تسميات أعمدة التقسيط",
    "custom_tables":     "الجداول المخصّصة",
    "custom_table_cols": "أعمدة الجداول المخصّصة",
    "custom_table_rows": "صفوف الجداول المخصّصة",
}

# Common column identifier → Arabic label. Used for tables that have no
# dedicated *_col_labels row. Specific-column entries from the per-table
# labels table always win over this fallback.
BUILT_IN_COLUMN_LABELS = {
    "id":                "المعرّف",
    "created_at":        "تاريخ الإنشاء",
    "personal_id":       "الرقم الشخصي",
    "student_name":      "اسم الطالب",
    "student_whatsapp":  "واتساب الطالب",
    "whatsapp":          "هاتف الواتساب",
    "phone":             "الهاتف",
    "mother_phone":      "هاتف الأم",
    "father_phone":      "هاتف الأب",
    "other_phone":       "هاتف آخر",
    "class_name":        "الصف",
    "teacher_name":      "اسم المدرّس",
    "teacher_2026":      "المدرّس 2026",
    "group_name":        "المجموعة",
    "group_name_student":"مجموعة الطالب",
    "group_online":      "المجموعة (أونلاين)",
    "group_link":        "رابط المجموعة",
    "level_course":      "المستوى / المقرر",
    "last_reached":      "آخر نقطة تم الوصول لها",
    "study_time":        "وقت الدراسة",
    "study_days":        "أيام الدراسة",
    "ramadan_time":      "توقيت رمضان",
    "online_time":       "توقيت الأونلاين",
    "session_duration":  "مدة الحصة",
    "session_date":      "تاريخ الجلسة",
    "duration_minutes":  "المدة بالدقائق",
    "session_type":      "نوع الحصة",
    "attendance_date":   "تاريخ الغياب",
    "day_name":          "اليوم",
    "status":            "الحالة",
    "contact_number":    "رقم التواصل",
    "message":           "الرسالة",
    "message_status":    "حالة الرسالة",
    "study_status":      "حالة الدراسة",
    "course_amount":     "مبلغ الدورة",
    "num_installments":  "عدد الأقساط",
    "taqseet_method":    "طريقة التقسيط",
    "installment_type":  "نوع التقسيط",
    "total_paid":        "المدفوع",
    "total_remaining":   "المتبقي",
    "payment_status":    "حالة الدفع",
    "registration_status":"حالة التسجيل",
    "start_date":        "تاريخ البداية",
    "study_hours":       "ساعات الدراسة",
    "total_required_hours":"إجمالي الساعات المستحقة",
    "form_fill_date":    "تاريخ التقييم",
    "class_participation":"المشاركة الصفية",
    "general_behavior":  "السلوك العام",
    "behavior_notes":    "ملاحظات السلوك",
    "reading":           "القراءة",
    "dictation":         "الإملاء",
    "term_meanings":     "معاني المصطلحات",
    "conversation":      "المحادثة",
    "expression":        "التعبير",
    "grammar":           "القواعد",
    "notes":             "ملاحظات",
    "name":              "الاسم",
    "category":          "التصنيف",
    "content":           "المحتوى",
    "template_name":     "اسم القالب",
    "sent_at":           "وقت الإرسال",
    "username":          "اسم المستخدم",
    "password":          "كلمة المرور",
    "role":              "الصلاحية",
    "page":              "الصفحة",
    "component":         "المكوّن",
    "label":             "التسمية",
    "value":             "القيمة",
    "value_type":        "نوع القيمة",
    "tbl_name":          "اسم الجدول",
    "tbl_label":         "تسمية الجدول",
    "col_key":           "مفتاح العمود",
    "col_label":         "تسمية العمود",
    "col_order":         "ترتيب العمود",
    "col_type":          "نوع العمود",
    "col_options":       "خيارات العمود",
    "is_visible":        "مرئي",
    "applied_at":        "تاريخ التطبيق",
    "tag":               "الوسم",
    "student_id":        "معرّف الطالب",
    "inst_num":          "رقم القسط",
    "price":             "السعر",
    "paid":              "المدفوع",
    "level_reached_2026":"إلى أين وصل 2026",
    "suitable_level_2026":"مناسب للمستوى 2026",
    "books_received":    "استلام الكتب",
    "final_result":      "النتيجة النهائية",
    "residence":         "مكان السكن",
    "home_address":      "عنوان المنزل",
    "road":              "الطريق",
    "complex_name":      "المجمع",
    "old_new_2026":      "قديم/جديد 2026",
    "registration_term2_2026":"تسجيل الفصل الثاني 2026",
}

# taqseet has 36 numbered columns (inst1..inst12, paid1..paid12, date1..date12)
# that don't fit cleanly into a flat dict literal. Populate them
# programmatically so every taqseet column renders Arabic in /settings and
# تعديل الجدول even on a fresh DB where the taqseet_labels_seed_v1
# migration hasn't run yet.
for _n in range(1, 13):
    BUILT_IN_COLUMN_LABELS["inst" + str(_n)] = "القسط " + str(_n)
    BUILT_IN_COLUMN_LABELS["paid" + str(_n)] = "المبلغ المدفوع " + str(_n)
    BUILT_IN_COLUMN_LABELS["date" + str(_n)] = "تاريخ الاستحقاق " + str(_n)

_LABELS_TABLE_FOR = {
    "students":      "column_labels",
    "student_groups":"group_col_labels",
    "attendance":    "att_col_labels",
    "evaluations":   "eval_col_labels",
    "payment_log":   "paylog_col_labels",
    "taqseet":       "taqseet_col_labels",
}

def _decode_arabic_entities(s):
    """Convert HTML numeric entities like "&#x627;" to raw Arabic.
    Labels seeded earlier in the project were stored as entity-encoded
    strings; the UI now wants raw characters so _esc() doesn't double-
    encode the leading `&`."""
    if not s or "&#" not in s:
        return s
    try:
        import html as _html
        return _html.unescape(s)
    except Exception:
        return s

def _table_display_label(name):
    """Return the Arabic display label for a table, or the raw name."""
    if not name:
        return name
    try:
        db = get_db()
        row = db.execute(
            "SELECT tbl_label FROM table_labels WHERE tbl_name=?", (name,)
        ).fetchone()
        if row and row[0]:
            return _decode_arabic_entities(row[0])
    except Exception:
        pass
    return BUILT_IN_TABLE_LABELS.get(name, name)

def _column_label_map(table):
    """Return {col_key: col_label} for every column of the given table.

    Precedence: per-table labels table → BUILT_IN_COLUMN_LABELS → identity."""
    out = {}
    if not table or not _is_safe_ident(table):
        return out
    try:
        cols = get_table_columns(table)
    except Exception:
        cols = []
    for c in cols:
        out[c] = BUILT_IN_COLUMN_LABELS.get(c, c)
    lbl_tbl = _LABELS_TABLE_FOR.get(table)
    if lbl_tbl:
        try:
            db = get_db()
            rows = db.execute(
                "SELECT col_key, col_label FROM " + lbl_tbl
            ).fetchall()
            for r in rows:
                k = r[0]; v = _decode_arabic_entities(r[1])
                if k and v:
                    out[k] = v
        except Exception:
            pass
    return out


def _active_students_filter():
    """Return (sql_fragment, param) for an "active student" WHERE clause.

    Both the filter column and the value the column should match for a
    student to count as ACTIVE flow through get_setting(), so they can
    be changed from /settings without touching code:

      settings.students.active_column   default "registration_term2_2026"
      settings.students.active_value    default "تم التسجيل"

    If the configured column isn't a safe identifier or isn't on the
    live students table, this returns (None, None) and callers should
    skip the filter (i.e. count every student).
    """
    col = (get_setting("students", "active_column", "registration_term2_2026") or "").strip()
    val = (get_setting("students", "active_value",  "تم التسجيل") or "").strip()
    if not col or not val or not _is_safe_ident(col):
        return None, None
    try:
        live = set(get_table_columns("students"))
        if col not in live:
            return None, None
    except Exception:
        return None, None
    # Tolerate leading/trailing whitespace that imports sometimes leave in.
    return "TRIM(" + col + ") = ?", val


@app.route('/api/settings/tables', methods=['GET'])
@login_required
def api_settings_tables():
    names = get_all_tables()
    tables = [{"name": n, "label": _table_display_label(n)} for n in names]
    return jsonify({"ok": True, "tables": tables})


@app.route('/api/settings/columns/<table_name>', methods=['GET'])
@login_required
def api_settings_columns(table_name):
    if not _is_safe_ident(table_name):
        return jsonify({"ok": False, "error": "invalid table name"}), 400
    cols = get_table_columns(table_name)
    lbl_map = _column_label_map(table_name)
    out = [{"name": c, "label": lbl_map.get(c, c)} for c in cols]
    return jsonify({"ok": True, "columns": out})



@app.route('/api/custom-table/<tid>/columns', methods=['GET'])
@login_required
def api_unified_columns_get(tid):
    db_table, labels_table = _resolve_table(tid)
    if not db_table:
        return jsonify({"ok": False, "error": "table not found"}), 404
    db = get_db()
    live_cols = [r[1] for r in db.execute("PRAGMA table_info(" + db_table + ")").fetchall()]
    live_cols = [c for c in live_cols if c not in ("id", "created_at")]
    label_map = {}
    type_map = {}
    options_map = {}
    if labels_table:
        try:
            rows = db.execute(
                "SELECT col_key, col_label, col_type, col_options FROM " + labels_table
            ).fetchall()
            for r in rows:
                label_map[r[0]] = r[1]
                type_map[r[0]] = r[2] or "نص"
                options_map[r[0]] = r[3] or ""
        except Exception:
            try:
                for r in db.execute("SELECT col_key, col_label FROM " + labels_table).fetchall():
                    label_map[r[0]] = r[1]
            except Exception:
                pass
    default_type = "نص"
    out = [{
        "col_key": c,
        "col_label": _decode_arabic_entities(label_map.get(c)) or BUILT_IN_COLUMN_LABELS.get(c) or c,
        "col_type": type_map.get(c, default_type),
        "col_options": options_map.get(c, ""),
    } for c in live_cols]
    return jsonify({"ok": True, "columns": out, "db_table": db_table, "db_table_label": _table_display_label(db_table)})


def _derive_unique_col_key(col_label, existing_cols):
    """Produce a unique ASCII column key from a user-entered label.

    The label is the USER-FACING Arabic string (shown everywhere in the
    UI). The key is an internal DB identifier the user never sees.

    Rules:
      - Lowercase the label, replace spaces with underscore.
      - Keep only ASCII alnum + underscore.
      - If nothing alphanumeric remains (e.g. a purely Arabic label like
        "اسم الكتاب", which would strip to bare "_"), fall back to
        "col_<unix-ms mod 1e10>".
      - If the derived key starts with a digit, prefix with "col_".
      - If the derived key already exists in the table, append "_2",
        "_3", … until unique.
    """
    base = (col_label or "").lower().replace(" ", "_")
    base = "".join(ch for ch in base if ch.isascii() and (ch.isalnum() or ch == "_"))
    has_alnum = any(ch.isascii() and ch.isalnum() for ch in base)
    if not has_alnum:
        base = "col_" + str(int(__import__('time').time() * 1000) % 10_000_000_000)
    elif base[0].isdigit():
        base = "col_" + base
    # Clamp length so ALTER TABLE doesn't fail on DBs with an identifier cap.
    base = base[:60]
    if not _is_safe_ident(base):
        base = "col_" + str(int(__import__('time').time() * 1000) % 10_000_000_000)
    if base not in existing_cols:
        return base
    for i in range(2, 500):
        cand = (base + "_" + str(i))[:63]
        if cand not in existing_cols and _is_safe_ident(cand):
            return cand
    # Absolute fallback with nanosecond timestamp.
    return "col_" + str(int(__import__('time').time_ns()) % (10 ** 14))


@app.route('/api/custom-table/<tid>/add-column', methods=['POST'])
@login_required
def api_unified_add_column(tid):
    d = request.get_json() or {}
    col_key_raw = (d.get("col_key") or "").strip()
    col_label = (d.get("col_label") or "").strip()
    if not col_label:
        return jsonify({"ok": False, "error": "col_label required"}), 400
    db_table, labels_table = _resolve_table(tid)
    if not db_table:
        return jsonify({"ok": False, "error": "table not found"}), 404
    db = get_db()
    # Resolve the final column key BEFORE we ALTER TABLE: the derivation
    # now collision-checks against the live schema so an Arabic-only label
    # never lands as "_" and every add produces a distinct column.
    try:
        live_cols = {r[1] for r in db.execute("PRAGMA table_info(" + db_table + ")").fetchall()}
    except Exception:
        live_cols = set()
    if col_key_raw:
        # Caller forced a specific key: must be safe, must not collide.
        if not _is_safe_ident(col_key_raw):
            return jsonify({"ok": False, "error": "invalid column name"}), 400
        if col_key_raw in live_cols:
            return jsonify({"ok": False, "error": "column already exists"}), 400
    else:
        col_key_raw = _derive_unique_col_key(col_label, live_cols)
    if not _is_safe_ident(col_key_raw):
        return jsonify({"ok": False, "error": "invalid column name"}), 400
    try:
        db.execute('ALTER TABLE "' + db_table + '" ADD COLUMN "' + col_key_raw + '" TEXT')
    except Exception:
        # column may already exist — continue; the label write below still
        # needs to run so the Arabic display name is registered.
        pass
    col_type_val = (d.get("col_type") or "نص").strip()
    col_options_val = (d.get("col_options") or "").strip()
    if labels_table:
        # Walk the schema once so we pick the widest INSERT that will succeed
        # AND so we never silently drop the Arabic label on a narrow table
        # like the original taqseet_col_labels (id, col_key, col_label).
        try:
            lbl_cols = {r[1] for r in db.execute(
                "PRAGMA table_info(" + labels_table + ")"
            ).fetchall()}
        except Exception:
            lbl_cols = set()
        has_order = "col_order" in lbl_cols
        has_type  = "col_type"  in lbl_cols
        has_opts  = "col_options" in lbl_cols
        max_order = 0
        if has_order:
            try:
                max_order = db.execute(
                    "SELECT MAX(col_order) FROM " + labels_table
                ).fetchone()[0] or 0
            except Exception:
                max_order = 0

        def _upsert_label():
            cols, vals = ["col_key", "col_label"], [col_key_raw, col_label]
            if has_order: cols.append("col_order");   vals.append(max_order + 1)
            if has_type:  cols.append("col_type");    vals.append(col_type_val)
            if has_opts:  cols.append("col_options"); vals.append(col_options_val)
            placeholders = ",".join(["?"] * len(vals))
            try:
                db.execute(
                    "INSERT INTO " + labels_table + "(" + ",".join(cols) + ") VALUES(" + placeholders + ")",
                    tuple(vals),
                )
                return True
            except Exception:
                pass
            # Row already exists — UPDATE whatever columns we do have.
            set_cols, set_vals = ["col_label=?"], [col_label]
            if has_type:  set_cols.append("col_type=?");    set_vals.append(col_type_val)
            if has_opts:  set_cols.append("col_options=?"); set_vals.append(col_options_val)
            set_vals.append(col_key_raw)
            try:
                db.execute(
                    "UPDATE " + labels_table + " SET " + ",".join(set_cols) + " WHERE col_key=?",
                    tuple(set_vals),
                )
                return True
            except Exception:
                return False

        _upsert_label()
    db.commit()
    return jsonify({"ok": True, "col_key": col_key_raw, "col_label": col_label})


@app.route('/api/custom-table/<tid>/rename-column', methods=['PATCH'])
@login_required
def api_unified_rename_column(tid):
    d = request.get_json() or {}
    old_key = (d.get("old_name") or d.get("col_key") or "").strip()
    new_label = (d.get("new_label") or d.get("col_label") or "").strip()
    new_key = (d.get("new_key") or "").strip()  # optional schema-level rename
    if not old_key or not new_label:
        return jsonify({"ok": False, "error": "old_name and new_label required"}), 400
    db_table, labels_table = _resolve_table(tid)
    if not db_table:
        return jsonify({"ok": False, "error": "table not found"}), 404
    db = get_db()
    # If old_key isn't a safe identifier, treat it as an Arabic display
    # label and resolve via the same ladder as delete-column: normalised
    # labels_table lookup → BUILT_IN_COLUMN_LABELS reverse → schema scan.
    if not _is_safe_ident(old_key):
        def _norm_lbl(s):
            s = "" if s is None else str(s)
            s = _decode_arabic_entities(s)
            return " ".join(s.split())
        target = _norm_lbl(old_key)
        resolved = None
        if labels_table and target:
            try:
                for r in db.execute(
                    "SELECT col_key, col_label FROM " + labels_table
                ).fetchall():
                    if r[0] and _is_safe_ident(r[0]) and _norm_lbl(r[1]) == target:
                        resolved = r[0]; break
            except Exception:
                pass
        if not resolved and target:
            for _k, _v in BUILT_IN_COLUMN_LABELS.items():
                if _norm_lbl(_v) == target and _is_safe_ident(_k):
                    resolved = _k; break
        if not resolved:
            try:
                for r in db.execute(
                    "PRAGMA table_info(" + db_table + ")"
                ).fetchall():
                    if _norm_lbl(r[1]) == target and _is_safe_ident(r[1]):
                        resolved = r[1]; break
            except Exception:
                pass
        if not resolved:
            return jsonify({
                "ok": False, "error": "invalid column name",
                "received": old_key,
                "hint": "could not map display label to an internal column identifier",
            }), 400
        old_key = resolved
    try:
        if new_key and new_key != old_key:
            if not _is_safe_ident(new_key):
                return jsonify({"ok": False, "error": "invalid new_key"}), 400
            try:
                db.execute('ALTER TABLE "' + db_table + '" RENAME COLUMN "' + old_key + '" TO "' + new_key + '"')
            except Exception as ex:
                return jsonify({"ok": False, "error": "rename column failed: " + str(ex)}), 400
            if labels_table:
                try:
                    db.execute("UPDATE " + labels_table + " SET col_key=?, col_label=? WHERE col_key=?",
                               (new_key, new_label, old_key))
                except Exception:
                    pass
        else:
            if labels_table:
                try:
                    cur = db.execute("UPDATE " + labels_table + " SET col_label=? WHERE col_key=?",
                                     (new_label, old_key))
                    if cur.rowcount == 0:
                        max_order = db.execute("SELECT MAX(col_order) FROM " + labels_table).fetchone()[0] or 0
                        db.execute("INSERT INTO " + labels_table + "(col_key, col_label, col_order) VALUES(?,?,?)",
                                   (old_key, new_label, max_order + 1))
                except Exception:
                    pass
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400


@app.route('/api/custom-table/<tid>/column-type', methods=['PATCH'])
@login_required
def api_unified_set_column_type(tid):
    d = request.get_json() or {}
    col_key = (d.get("col_key") or "").strip()
    col_type_val = (d.get("col_type") or "نص").strip()
    col_options_val = (d.get("col_options") or "").strip()
    if not col_key:
        return jsonify({"ok": False, "error": "col_key required"}), 400
    db_table, labels_table = _resolve_table(tid)
    if not db_table:
        return jsonify({"ok": False, "error": "table not found"}), 404
    if not labels_table:
        # Tables without a labels table (taqseet) cannot store col_type.
        return jsonify({"ok": False, "error": "table does not support column types"}), 400
    db = get_db()
    try:
        cur = db.execute(
            "UPDATE " + labels_table + " SET col_type=?, col_options=? WHERE col_key=?",
            (col_type_val, col_options_val, col_key),
        )
        if cur.rowcount == 0:
            # Row didn't exist — create it so the type sticks.
            max_order = db.execute("SELECT MAX(col_order) FROM " + labels_table).fetchone()[0] or 0
            db.execute(
                "INSERT INTO " + labels_table + "(col_key, col_label, col_order, col_type, col_options) VALUES(?,?,?,?,?)",
                (col_key, col_key, max_order + 1, col_type_val, col_options_val),
            )
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400


@app.route('/api/custom-table/<tid>/delete-column/<col_name>', methods=['DELETE'])
@login_required
def api_unified_delete_column(tid, col_name):
    """Drop a column from a table and clean up its label row.

    Sequence (per spec):
      1. Resolve col_name to an internal safe identifier — if the client
         sent an Arabic display label, look it up in labels_table.
      2. Confirm the column actually exists in the live schema.
      3. Snapshot + delete the label row.
      4. Run ALTER TABLE … DROP COLUMN. If it raises, re-insert the
         snapshotted label row (our best approximation of a rollback
         since the psycopg2 connection runs in autocommit) and return
         the DB error so the UI can surface it.
    """
    db_table, labels_table = _resolve_table(tid)
    if not db_table:
        return jsonify({"ok": False, "error": "table not found"}), 404
    db = get_db()

    # ---- 1) Resolve col_name to an internal safe identifier ----
    # Multi-stage Arabic-label → internal-key lookup. The client SHOULD
    # always pass the internal key via /mx-helpers.js, but we guard
    # against label leakage by running the same ladder the paylog
    # lookup uses: normalise whitespace, decode HTML entities, fuzzy
    # match against the labels table, then the built-in dict, then
    # information_schema as a last resort.
    def _norm_label(s):
        s = "" if s is None else str(s)
        s = _decode_arabic_entities(s)
        return " ".join(s.split())
    if not _is_safe_ident(col_name):
        target = _norm_label(col_name)
        resolved = None
        # (a) labels_table.col_label exact match (normalised both sides)
        if labels_table and target:
            try:
                rows = db.execute(
                    "SELECT col_key, col_label FROM " + labels_table
                ).fetchall()
                for r in rows:
                    if r[0] and _is_safe_ident(r[0]) and _norm_label(r[1]) == target:
                        resolved = r[0]; break
            except Exception:
                pass
        # (b) BUILT_IN_COLUMN_LABELS reverse lookup — covers rows that
        # never got a row in labels_table but have a hard-coded Arabic
        # display name (e.g. the numbered taqseet columns).
        if not resolved and target:
            for k, v in BUILT_IN_COLUMN_LABELS.items():
                if _norm_label(v) == target and _is_safe_ident(k):
                    resolved = k; break
        # (c) information_schema scan — catch the edge case where a
        # column's internal name is literally the Arabic target (not a
        # safe ident by our regex but technically present in the DB).
        if not resolved:
            try:
                for r in db.execute(
                    "PRAGMA table_info(" + db_table + ")"
                ).fetchall():
                    name = r[1]
                    if _norm_label(name) == target and _is_safe_ident(name):
                        resolved = name; break
            except Exception:
                pass
        if not resolved:
            return jsonify({
                "ok": False,
                "error": "invalid column name",
                "received": col_name,
                "hint": "could not map display label to an internal column identifier",
            }), 400
        col_name = resolved

    # ---- 2) Confirm the column exists on the live table ----
    try:
        live_cols = {r[1] for r in db.execute(
            "PRAGMA table_info(" + db_table + ")"
        ).fetchall()}
    except Exception as ex:
        return jsonify({"ok": False, "error": "could not read schema: " + str(ex)}), 500
    if col_name not in live_cols:
        # Already gone — treat as success but make sure no stale label row
        # remains that would otherwise re-appear as a ghost column.
        if labels_table:
            try:
                db.execute("DELETE FROM " + labels_table + " WHERE col_key=?", (col_name,))
            except Exception:
                pass
        db.commit()
        return jsonify({"ok": True, "col_key": col_name, "note": "column already absent"})

    # ---- 3) Snapshot + delete label row ----
    label_snapshot = None
    if labels_table:
        try:
            lbl_cols = [r[1] for r in db.execute(
                "PRAGMA table_info(" + labels_table + ")"
            ).fetchall()]
            if "col_key" in lbl_cols:
                select_cols = [c for c in lbl_cols if c != "id"]
                row = db.execute(
                    "SELECT " + ",".join(select_cols) + " FROM " + labels_table + " WHERE col_key=?",
                    (col_name,),
                ).fetchone()
                if row:
                    # Row may be a sqlite3.Row / psycopg2 row — pull by index.
                    label_snapshot = (select_cols, [row[i] for i in range(len(select_cols))])
                db.execute(
                    "DELETE FROM " + labels_table + " WHERE col_key=?",
                    (col_name,),
                )
        except Exception:
            pass  # No labels table or no row — nothing to snapshot.

    # ---- 4) Run ALTER TABLE DROP COLUMN ----
    try:
        db.execute('ALTER TABLE "' + db_table + '" DROP COLUMN "' + col_name + '"')
    except Exception as ex:
        # Roll back the label deletion by re-inserting the snapshot.
        if label_snapshot is not None and labels_table:
            cols, vals = label_snapshot
            try:
                db.execute(
                    "INSERT INTO " + labels_table + "(" + ",".join(cols) + ") "
                    "VALUES(" + ",".join(["?"] * len(cols)) + ")",
                    tuple(vals),
                )
            except Exception:
                pass
        return jsonify({
            "ok": False,
            "error": "could not drop column from database: " + str(ex),
            "col_key": col_name,
        }), 500

    # ---- 5) Confirm the column is really gone (catch silent Postgres no-ops) ----
    try:
        after_cols = {r[1] for r in db.execute(
            "PRAGMA table_info(" + db_table + ")"
        ).fetchall()}
        if col_name in after_cols:
            # The ALTER reported success but the column is still there (shouldn't
            # happen, but guard against a driver quirk). Restore the label and error.
            if label_snapshot is not None and labels_table:
                cols, vals = label_snapshot
                try:
                    db.execute(
                        "INSERT INTO " + labels_table + "(" + ",".join(cols) + ") "
                        "VALUES(" + ",".join(["?"] * len(cols)) + ")",
                        tuple(vals),
                    )
                except Exception:
                    pass
            return jsonify({
                "ok": False,
                "error": "column still present after DROP — database did not accept the change",
                "col_key": col_name,
            }), 500
    except Exception:
        pass

    db.commit()
    return jsonify({"ok": True, "col_key": col_name})


@app.route('/api/custom-table/<tid>/rename', methods=['PATCH'])
@login_required
def api_unified_rename_table(tid):
    d = request.get_json() or {}
    new_name = (d.get("new_name") or "").strip()
    new_label = (d.get("new_label") or "").strip()
    db_table, labels_table = _resolve_table(tid)
    if not db_table:
        return jsonify({"ok": False, "error": "table not found"}), 404
    db = get_db()
    # For custom tables (numeric id), actually ALTER TABLE RENAME.
    if str(tid).isdigit() and new_name:
        if not _is_safe_ident(new_name):
            return jsonify({"ok": False, "error": "invalid table name"}), 400
        try:
            db.execute('ALTER TABLE "' + db_table + '" RENAME TO "' + new_name + '"')
            db.execute("UPDATE custom_tables SET tbl_name=? WHERE id=?", (new_name, int(tid)))
            db.commit()
            return jsonify({"ok": True, "new_name": new_name})
        except Exception as ex:
            return jsonify({"ok": False, "error": str(ex)}), 400
    # For built-in tables: no-op (names are fixed). Accept the request so the
    # unified modal can call this endpoint uniformly.
    return jsonify({"ok": True, "new_label": new_label})


# --- Evaluations (التقييمات) ---------------------------------------------

def _evaluations_writable_cols(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(evaluations)").fetchall()]
    return [c for c in cols if c not in ("id", "created_at")]

@app.route("/api/evaluations", methods=["GET"])
@login_required
def api_evaluations_get():
    db = get_db()
    rows = db.execute("SELECT * FROM evaluations ORDER BY id ASC").fetchall()
    return jsonify({"rows": [dict(r) for r in rows]})

@app.route("/api/evaluations", methods=["POST"])
@login_required
def api_evaluations_add():
    d = request.get_json() or {}
    db = get_db()
    try:
        cols = _evaluations_writable_cols(db)
        placeholders = ",".join(["?"] * len(cols))
        values = tuple(d.get(c) for c in cols)
        db.execute("INSERT INTO evaluations (" + ",".join(cols) + ") VALUES (" + placeholders + ")", values)
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/evaluations/<int:rid>", methods=["PUT"])
@login_required
def api_evaluations_update(rid):
    d = request.get_json() or {}
    db = get_db()
    try:
        cols = [c for c in _evaluations_writable_cols(db) if c in d]
        if not cols:
            return jsonify({"ok": True})
        set_clause = ",".join([c + "=?" for c in cols])
        values = tuple(d.get(c) for c in cols) + (rid,)
        db.execute("UPDATE evaluations SET " + set_clause + " WHERE id=?", values)
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/evaluations/<int:rid>", methods=["DELETE"])
@login_required
def api_evaluations_delete(rid):
    try:
        db = get_db()
        db.execute("DELETE FROM evaluations WHERE id=?", (rid,))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/eval-columns", methods=["GET"])
@login_required
def api_eval_columns_get():
    db = get_db()
    rows = db.execute("SELECT col_key,col_label,col_order,is_visible FROM eval_col_labels ORDER BY col_order").fetchall()
    return jsonify({"columns": [dict(r) for r in rows]})

@app.route("/api/eval-columns", methods=["POST"])
@login_required
def api_eval_columns_add():
    d = request.get_json()
    col_key = d.get("col_key","").strip().replace(" ","_").lower()
    col_label = d.get("col_label","").strip()
    position = d.get("position","end")
    after_col = d.get("after_col","")
    if not col_key or not col_label:
        return jsonify({"ok":False,"error":"missing data"}),400
    safe_key = "".join(c for c in col_key if c.isalnum() or c == "_")
    if not safe_key or safe_key != col_key:
        return jsonify({"ok":False,"error":"invalid column name"}),400
    db = get_db()
    try:
        all_cols = db.execute("SELECT col_key,col_order FROM eval_col_labels ORDER BY col_order").fetchall()
        if position == "start":
            new_order = 0
            for row in all_cols:
                db.execute("UPDATE eval_col_labels SET col_order=col_order+1 WHERE col_key=?", (row[0],))
        elif position == "after" and after_col:
            after_row = db.execute("SELECT col_order FROM eval_col_labels WHERE col_key=?", (after_col,)).fetchone()
            if after_row:
                new_order = after_row[0] + 1
                for row in all_cols:
                    if row[1] >= new_order:
                        db.execute("UPDATE eval_col_labels SET col_order=col_order+1 WHERE col_key=?", (row[0],))
            else:
                max_order = db.execute("SELECT MAX(col_order) FROM eval_col_labels").fetchone()[0] or 0
                new_order = max_order + 1
        else:
            max_order = db.execute("SELECT MAX(col_order) FROM eval_col_labels").fetchone()[0] or 0
            new_order = max_order + 1
        db.execute("INSERT INTO eval_col_labels(col_key,col_label,col_order) VALUES(?,?,?)",(col_key,col_label,new_order))
        db.execute("ALTER TABLE evaluations ADD COLUMN "+col_key+" TEXT")
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400

@app.route("/api/eval-columns/<col_key>", methods=["DELETE"])
@login_required
def api_eval_columns_delete(col_key):
    safe_key = "".join(c for c in col_key if c.isalnum() or c == "_")
    if not safe_key or safe_key != col_key:
        return jsonify({"ok": False, "error": "invalid column name"}), 400
    db = get_db()
    try:
        db.execute('ALTER TABLE evaluations DROP COLUMN "' + safe_key + '"')
    except Exception:
        pass
    db.execute("DELETE FROM eval_col_labels WHERE col_key=?", (col_key,))
    db.commit()
    return jsonify({"ok": True})

@app.route("/api/eval-columns/<col_key>", methods=["PUT"])
@login_required
def api_eval_columns_update(col_key):
    d = request.get_json()
    new_label = d.get("col_label","").strip()
    if not new_label:
        return jsonify({"ok":False,"error":"missing label"}),400
    db = get_db()
    try:
        db.execute("UPDATE eval_col_labels SET col_label=? WHERE col_key=?",(new_label,col_key))
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400


@app.route('/api/attendance', methods=['GET'])
@login_required
def api_attendance_get():
    db = get_db()
    rows = db.execute("SELECT * FROM attendance ORDER BY id ASC").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/attendance', methods=['POST'])
@login_required
def api_attendance_add():
    d = request.get_json()
    db = get_db()
    try:
        attendance_date = d.get('attendance_date','')
        group_name = d.get('group_name','')
        student_name = d.get('student_name','')
        existing = db.execute(
            "SELECT id FROM attendance WHERE student_name=? AND attendance_date=? AND group_name=?",
            (student_name, attendance_date, group_name)
        ).fetchone()
        if existing:
            db.execute("""UPDATE attendance SET day_name=?,contact_number=?,status=?,message=?,message_status=?,study_status=? WHERE id=?""",
                (d.get('day_name',''), d.get('contact_number',''), d.get('status',''),
                 d.get('message',''), d.get('message_status',''), d.get('study_status',''), existing[0]))
            db.commit()
            return jsonify({"ok": True, "id": existing[0], "updated": True})
        else:
            db.execute("""INSERT INTO attendance(attendance_date,day_name,group_name,student_name,contact_number,status,message,message_status,study_status)
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (attendance_date, d.get('day_name',''), group_name,
                 student_name, d.get('contact_number',''), d.get('status',''),
                 d.get('message',''), d.get('message_status',''), d.get('study_status','')))
            db.commit()
            rid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            return jsonify({"ok": True, "id": rid, "updated": False})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route('/api/attendance/<int:rid>', methods=['PUT'])
@login_required
def api_attendance_update(rid):
    d = request.get_json()
    db = get_db()
    try:
        db.execute("""UPDATE attendance SET attendance_date=?,day_name=?,group_name=?,student_name=?,contact_number=?,status=?,message=?,message_status=?,study_status=? WHERE id=?""",
            (d.get('attendance_date',''), d.get('day_name',''), d.get('group_name',''),
             d.get('student_name',''), d.get('contact_number',''), d.get('status',''),
             d.get('message',''), d.get('message_status',''), d.get('study_status',''), rid))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route('/api/attendance/<int:rid>', methods=['DELETE'])
@login_required
def api_attendance_delete(rid):
    db = get_db()
    try:
        db.execute("DELETE FROM attendance WHERE id=?", (rid,))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route('/api/attendance/by-date-group', methods=['GET'])
@login_required
def api_attendance_by_date_group():
    date = request.args.get('date', '')
    group = request.args.get('group', '')
    # date or group (or both) may be the sentinel '__all__' meaning "drop that
    # filter". Empty group is treated like __all__ for backwards-compatibility.
    all_dates  = (date  == '__all__')
    all_groups = (group == '__all__' or group == '')
    if not date and not all_dates:
        return jsonify({"rows": []})
    db = get_db()
    base = (
        "SELECT a.id, a.attendance_date, a.group_name, a.student_name, a.status, "
        "       a.message_status, s.whatsapp, ml.last_sent "
        "  FROM attendance a "
        "  LEFT JOIN students s ON s.student_name = a.student_name "
        "  LEFT JOIN ( "
        "      SELECT student_name, MAX(sent_at) AS last_sent "
        "        FROM message_log "
        "       GROUP BY student_name "
        "  ) ml ON ml.student_name = a.student_name "
    )
    # Cap the result so "all dates + all groups" doesn't ship the entire
    # attendance history in one response.
    tail = " ORDER BY a.attendance_date DESC, a.group_name, a.student_name LIMIT 1000"
    if all_dates and all_groups:
        rows = db.execute(base + tail).fetchall()
    elif all_dates:
        rows = db.execute(base + "WHERE a.group_name=?" + tail, (group,)).fetchall()
    elif all_groups:
        rows = db.execute(base + "WHERE a.attendance_date=?" + tail, (date,)).fetchall()
    else:
        rows = db.execute(base + "WHERE a.attendance_date=? AND a.group_name=?" + tail,
                          (date, group)).fetchall()
    return jsonify({"rows": [dict(r) for r in rows]})

@app.route('/api/attendance/<int:rid>/mark-sent', methods=['POST'])
@login_required
def api_attendance_mark_sent(rid):
    db = get_db()
    try:
        db.execute("UPDATE attendance SET message_status=? WHERE id=?",
                   ("تم الإرسال", rid))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route('/api/attendance/<int:rid>/unmark-sent', methods=['POST'])
@login_required
def api_attendance_unmark_sent(rid):
    db = get_db()
    try:
        db.execute("UPDATE attendance SET message_status=? WHERE id=?", ('', rid))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route('/api/attendance/general-stats', methods=['GET'])
@login_required
def api_attendance_general_stats():
    today = (request.args.get('today') or '').strip()
    if not today:
        from datetime import date as _date
        today = _date.today().isoformat()
    db = get_db()
    absent_today = db.execute(
        "SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status=?",
        (today, 'غائب')
    ).fetchone()[0]
    late_today = db.execute(
        "SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status=?",
        (today, 'متأخر')
    ).fetchone()[0]
    sent_ever = db.execute(
        "SELECT COUNT(DISTINCT student_name) FROM message_log "
        "WHERE student_name IS NOT NULL AND student_name != ''"
    ).fetchone()[0]
    total_students = db.execute(
        "SELECT COUNT(*) FROM students "
        "WHERE student_name IS NOT NULL AND student_name != ''"
    ).fetchone()[0]
    never_sent = max(0, total_students - sent_ever)
    return jsonify({
        "today": today,
        "absent_today": absent_today,
        "late_today": late_today,
        "sent_ever": sent_ever,
        "never_sent": never_sent,
    })



# &#x2500;&#x2500;&#x2500; Attendance Column Labels API &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;

ATT_DEFAULT_COLS = [
    ("attendance_date","&#x62A;&#x627;&#x631;&#x64A;&#x62E; &#x623;&#x62E;&#x630; &#x627;&#x644;&#x62D;&#x636;&#x648;&#x631;",1),
    ("day_name","&#x627;&#x644;&#x64A;&#x648;&#x645;",2),
    ("group_name","&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;",3),
    ("student_name","&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;",4),
    ("contact_number","&#x631;&#x642;&#x645; &#x627;&#x644;&#x62A;&#x648;&#x627;&#x635;&#x644;",5),
    ("status","&#x627;&#x644;&#x62D;&#x627;&#x644;&#x629;",6),
    ("message","&#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;",7),
    ("message_status","&#x62D;&#x627;&#x644;&#x629; &#x625;&#x631;&#x633;&#x627;&#x644; &#x627;&#x644;&#x631;&#x633;&#x627;&#x644;&#x629;",8),
    ("study_status","&#x62D;&#x627;&#x644;&#x629; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;",9),
]

@app.route('/api/att-columns', methods=['GET'])
@login_required
def api_att_columns_get():
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM att_col_labels").fetchone()[0] == 0:
        for key, label, order in ATT_DEFAULT_COLS:
            try:
                db.execute("INSERT INTO att_col_labels(col_key,col_label,col_order) VALUES(?,?,?)", (key, label, order))
            except:
                pass
        db.commit()
    cols = db.execute("SELECT * FROM att_col_labels ORDER BY col_order").fetchall()
    return jsonify([dict(c) for c in cols])

@app.route('/api/att-columns', methods=['POST'])
@login_required
def api_att_columns_add():
    d = request.get_json()
    col_label = d.get('col_label','').strip()
    position = d.get('position','end')
    after_key = d.get('after_key','')
    if not col_label:
        return jsonify({'ok':False,'error':'missing label'}),400
    db = get_db()
    try:
        import re, time
        col_key = 'att_col_' + str(int(time.time()*1000))[-6:]
        max_order = db.execute("SELECT MAX(col_order) FROM att_col_labels").fetchone()[0] or 0
        if position == 'start':
            db.execute("UPDATE att_col_labels SET col_order=col_order+1")
            new_order = 1
        elif position == 'after' and after_key:
            ao = db.execute("SELECT col_order FROM att_col_labels WHERE col_key=?", (after_key,)).fetchone()
            ao = ao[0] if ao else max_order
            db.execute("UPDATE att_col_labels SET col_order=col_order+1 WHERE col_order>?", (ao,))
            new_order = ao + 1
        else:
            new_order = max_order + 1
        db.execute("INSERT INTO att_col_labels(col_key,col_label,col_order) VALUES(?,?,?)", (col_key, col_label, new_order))
        db.commit()
        # Add column to attendance table
        try:
            db.execute("ALTER TABLE attendance ADD COLUMN " + col_key + " TEXT")
            db.commit()
        except:
            pass
        return jsonify({'ok':True})
    except Exception as ex:
        return jsonify({'ok':False,'error':str(ex)}),400

@app.route('/api/att-columns/<col_key>', methods=['DELETE'])
@login_required
def api_att_columns_delete(col_key):
    # Only allow deleting custom columns (not the 9 default ones)
    default_keys = [c[0] for c in ATT_DEFAULT_COLS]
    if col_key in default_keys:
        return jsonify({'ok':False,'error':'&#x644;&#x627; &#x64A;&#x645;&#x643;&#x646; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x623;&#x639;&#x645;&#x62F;&#x629; &#x627;&#x644;&#x623;&#x633;&#x627;&#x633;&#x64A;&#x629;'}),400
    db = get_db()
    try:
        db.execute("DELETE FROM att_col_labels WHERE col_key=?", (col_key,))
        db.commit()
        return jsonify({'ok':True})
    except Exception as ex:
        return jsonify({'ok':False,'error':str(ex)}),400

@app.route('/api/att-columns/<col_key>', methods=['PUT'])
@login_required
def api_att_columns_rename(col_key):
    d = request.get_json()
    new_label = d.get('col_label','').strip()
    if not new_label:
        return jsonify({'ok':False,'error':'missing label'}),400
    db = get_db()
    try:
        db.execute("UPDATE att_col_labels SET col_label=? WHERE col_key=?", (new_label, col_key))
        db.commit()
        return jsonify({'ok':True})
    except Exception as ex:
        return jsonify({'ok':False,'error':str(ex)}),400


# &#x2500;&#x2500;&#x2500; Custom Tables API &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;

@app.route('/api/custom-tables', methods=['GET'])
@login_required
def api_custom_tables_get():
    db = get_db()
    tables = db.execute("SELECT * FROM custom_tables ORDER BY id").fetchall()
    result = []
    for t in tables:
        cols = db.execute("SELECT * FROM custom_table_cols WHERE table_id=? ORDER BY col_order", (t['id'],)).fetchall()
        rows = db.execute("SELECT * FROM custom_table_rows WHERE table_id=? ORDER BY id", (t['id'],)).fetchall()
        result.append({
            'id': t['id'],
            'tbl_name': t['tbl_name'],
            'created_at': t['created_at'],
            'cols': [dict(c) for c in cols],
            'rows': [{'id': r['id'], 'row_data': json.loads(r['row_data'] or '{}')} for r in rows]
        })
    return jsonify(result)

@app.route('/api/custom-tables', methods=['POST'])
@login_required
def api_custom_tables_create():
    d = request.get_json()
    tbl_name = d.get('tbl_name','').strip()
    cols = d.get('cols', [])
    row_count = int(d.get('row_count', 0))
    if not tbl_name:
        return jsonify({'ok': False, 'error': 'missing name'}), 400
    db = get_db()
    try:
        db.execute("INSERT INTO custom_tables(tbl_name) VALUES(?)", (tbl_name,))
        db.commit()
        tid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        for i, col_label in enumerate(cols):
            col_key = 'col_' + str(i+1)
            db.execute("INSERT INTO custom_table_cols(table_id,col_key,col_label,col_order) VALUES(?,?,?,?)", (tid, col_key, col_label, i+1))
        for _ in range(row_count):
            db.execute("INSERT INTO custom_table_rows(table_id,row_data) VALUES(?,?)", (tid, '{}'))
        db.commit()
        return jsonify({'ok': True, 'id': tid})
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 400

@app.route('/api/custom-tables/<int:tid>', methods=['DELETE'])
@login_required
def api_custom_tables_delete(tid):
    db = get_db()
    try:
        db.execute("DELETE FROM custom_table_rows WHERE table_id=?", (tid,))
        db.execute("DELETE FROM custom_table_cols WHERE table_id=?", (tid,))
        db.execute("DELETE FROM custom_tables WHERE id=?", (tid,))
        db.commit()
        return jsonify({'ok': True})
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 400

@app.route('/api/custom-tables/<int:tid>/rows', methods=['POST'])
@login_required
def api_custom_table_row_add(tid):
    d = request.get_json()
    row_data = d.get('row_data', {})
    db = get_db()
    try:
        db.execute("INSERT INTO custom_table_rows(table_id,row_data) VALUES(?,?)", (tid, json.dumps(row_data, ensure_ascii=False)))
        db.commit()
        rid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        return jsonify({'ok': True, 'id': rid})
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 400

@app.route('/api/custom-tables/<int:tid>/rows/<int:rid>', methods=['PUT'])
@login_required
def api_custom_table_row_update(tid, rid):
    d = request.get_json()
    row_data = d.get('row_data', {})
    db = get_db()
    try:
        db.execute("UPDATE custom_table_rows SET row_data=? WHERE id=? AND table_id=?", (json.dumps(row_data, ensure_ascii=False), rid, tid))
        db.commit()
        return jsonify({'ok': True})
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 400

@app.route('/api/custom-tables/<int:tid>/rows/<int:rid>', methods=['DELETE'])
@login_required
def api_custom_table_row_delete(tid, rid):
    db = get_db()
    try:
        db.execute("DELETE FROM custom_table_rows WHERE id=? AND table_id=?", (rid, tid))
        db.commit()
        return jsonify({'ok': True})
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 400

@app.route('/api/custom-tables/<int:tid>/cols', methods=['POST'])
@login_required
def api_custom_table_col_add(tid):
    d = request.get_json()
    col_label = d.get('col_label','').strip()
    position = d.get('position','end')
    after_key = d.get('after_key','')
    if not col_label:
        return jsonify({'ok': False, 'error': 'missing label'}), 400
    db = get_db()
    try:
        max_order = db.execute("SELECT MAX(col_order) FROM custom_table_cols WHERE table_id=?", (tid,)).fetchone()[0] or 0
        count = db.execute("SELECT COUNT(*) FROM custom_table_cols WHERE table_id=?", (tid,)).fetchone()[0]
        col_key = 'col_' + str(int(max_order) + 1)
        if position == 'start':
            db.execute("UPDATE custom_table_cols SET col_order=col_order+1 WHERE table_id=?", (tid,))
            new_order = 1
        elif position == 'after' and after_key:
            after_order = db.execute("SELECT col_order FROM custom_table_cols WHERE table_id=? AND col_key=?", (tid, after_key)).fetchone()
            after_order = after_order[0] if after_order else max_order
            db.execute("UPDATE custom_table_cols SET col_order=col_order+1 WHERE table_id=? AND col_order>?", (tid, after_order))
            new_order = after_order + 1
        else:
            new_order = max_order + 1
        db.execute("INSERT INTO custom_table_cols(table_id,col_key,col_label,col_order) VALUES(?,?,?,?)", (tid, col_key, col_label, new_order))
        db.commit()
        return jsonify({'ok': True})
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 400

@app.route('/api/custom-tables/<int:tid>/cols/<col_key>', methods=['DELETE'])
@login_required
def api_custom_table_col_delete(tid, col_key):
    db = get_db()
    try:
        db.execute("DELETE FROM custom_table_cols WHERE table_id=? AND col_key=?", (tid, col_key))
        db.commit()
        return jsonify({'ok': True})
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 400

@app.route('/api/custom-tables/<int:tid>/cols/<col_key>', methods=['PUT'])
@login_required
def api_custom_table_col_rename(tid, col_key):
    d = request.get_json()
    new_label = d.get('col_label','').strip()
    if not new_label:
        return jsonify({'ok': False, 'error': 'missing label'}), 400
    db = get_db()
    try:
        db.execute("UPDATE custom_table_cols SET col_label=? WHERE table_id=? AND col_key=?", (new_label, tid, col_key))
        db.commit()
        return jsonify({'ok': True})
    except Exception as ex:
        return jsonify({'ok': False, 'error': str(ex)}), 400


GROUPS_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>&#x645;&#x639;&#x644;&#x648;&#x645;&#x627;&#x62A; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A; - Mindex</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Tahoma,Arial,sans-serif;}
body{background:#f5f3ff;min-height:100vh;direction:rtl;}
.topbar{background:linear-gradient(135deg,#00BCD4,#0097A7);color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;}
.topbar h1{font-size:20px;font-weight:800;}
.btn-back{background:rgba(255,255,255,.18);color:#fff;border:1.5px solid rgba(255,255,255,.5);padding:8px 18px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;}
.btn-back:hover{background:rgba(255,255,255,.3);}
.main{padding:24px 28px;}
.page-title{font-size:22px;font-weight:800;color:#0097A7;margin-bottom:20px;}
.stats{display:flex;gap:14px;margin-bottom:22px;}
.stat-card{background:#fff;border-radius:12px;padding:14px 22px;box-shadow:0 2px 10px rgba(0,150,180,.1);display:flex;flex-direction:column;align-items:center;min-width:120px;}
.stat-num{font-size:28px;font-weight:800;color:#00BCD4;}
.stat-label{font-size:12px;color:#888;margin-top:2px;}
.btn-add{background:linear-gradient(135deg,#00BCD4,#0097A7);color:#fff;border:none;padding:11px 26px;border-radius:11px;font-size:15px;font-weight:700;cursor:pointer;margin-bottom:20px;display:inline-flex;align-items:center;gap:8px;}
.btn-add:hover{opacity:.9;}
.search-bar{display:flex;gap:10px;margin-bottom:18px;}
.search-bar input{flex:1;padding:10px 16px;border:1.5px solid #b2ebf2;border-radius:10px;font-size:14px;outline:none;background:#fff;}
.search-bar input:focus{border-color:#00BCD4;}
.btn-search{background:#00BCD4;color:#fff;border:none;padding:10px 20px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;}
.table-wrap{background:#fff;border-radius:14px;box-shadow:0 2px 14px rgba(0,150,180,.1);overflow-x:auto;}
table{width:100%;border-collapse:collapse;min-width:1200px;}
thead tr{background:linear-gradient(135deg,#00BCD4,#0097A7);color:#fff;}
th{padding:13px 12px;font-size:13px;font-weight:700;text-align:center;white-space:nowrap;}
tbody tr{border-bottom:1px solid #e0f7fa;transition:background .15s;}
tbody tr:hover{background:#e0f7fa;}
td{padding:11px 12px;font-size:13px;text-align:center;color:#444;}
td.name-cell{font-weight:600;color:#0097A7;text-align:right;}
td.link-cell a{color:#00BCD4;text-decoration:none;font-weight:600;}
td.link-cell a:hover{text-decoration:underline;}
.no-data{text-align:center;padding:48px;color:#bbb;font-size:16px;}
.action-btn{background:none;border:none;cursor:pointer;padding:4px 8px;border-radius:6px;font-size:15px;}
.btn-edit{color:#0097A7;}
.btn-edit:hover{background:#e0f7fa;}
.btn-del{color:#e53935;}
.btn-del:hover{background:#fce4ec;}
.modal-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:1000;align-items:center;justify-content:center;}
.modal-bg.open{display:flex;}
.modal{background:#fff;border-radius:18px;padding:30px 28px;width:720px;max-width:96vw;max-height:90vh;overflow-y:auto;box-shadow:0 10px 40px rgba(0,150,180,.2);}
.modal h2{font-size:20px;font-weight:800;color:#0097A7;margin-bottom:22px;text-align:center;}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.form-grid .full{grid-column:1/-1;}
.field label{display:block;font-size:13px;color:#0097A7;font-weight:600;margin-bottom:5px;}
.field input{width:100%;padding:10px 13px;border:1.5px solid #b2ebf2;border-radius:9px;font-size:14px;outline:none;background:#f0fdff;direction:rtl;}
.field input:focus{border-color:#00BCD4;background:#fff;}
.field input.ltr{direction:ltr;text-align:left;}
.modal-actions{display:flex;gap:12px;justify-content:center;margin-top:22px;}
.btn-save{background:linear-gradient(135deg,#00BCD4,#0097A7);color:#fff;border:none;padding:11px 34px;border-radius:11px;font-size:15px;font-weight:700;cursor:pointer;}
.btn-cancel{background:#e0f7fa;color:#0097A7;border:none;padding:11px 28px;border-radius:11px;font-size:15px;font-weight:600;cursor:pointer;}
.btn-cancel:hover{background:#b2ebf2;}
.toast{position:fixed;bottom:28px;right:28px;background:#00BCD4;color:#fff;padding:13px 24px;border-radius:12px;font-size:14px;font-weight:600;z-index:9999;display:none;box-shadow:0 4px 20px rgba(0,188,212,.3);}
.toast.show{display:block;}
.confirm-bg{display:none;position:fixed;inset:0;background:rgba(0,0,0,.4);z-index:2000;align-items:center;justify-content:center;}
.confirm-bg.open{display:flex;}
.confirm-box{background:#fff;border-radius:16px;padding:28px 32px;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,.2);max-width:380px;width:94%;}
.confirm-box h3{font-size:18px;font-weight:800;color:#c62828;margin-bottom:12px;}
.confirm-box p{color:#555;margin-bottom:22px;font-size:14px;}
.confirm-actions{display:flex;gap:12px;justify-content:center;}
.btn-confirm-del{background:#e53935;color:#fff;border:none;padding:10px 26px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;}
.btn-confirm-cancel{background:#f5f5f5;color:#444;border:none;padding:10px 22px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;}
</style>
</head>
<body>
<div class="topbar">
  <h1>&#128101; &#x645;&#x639;&#x644;&#x648;&#x645;&#x627;&#x62A; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</h1>
  <a href="/database" class="btn-back">&larr; &#x642;&#x627;&#x639;&#x62F;&#x629; &#x627;&#x644;&#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;</a>
</div>
<div class="main">
  <div class="page-title">&#x62C;&#x62F;&#x648;&#x644; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</div>
  <div class="stats">
    <div class="stat-card">
      <span class="stat-num" id="totalCount">0</span>
      <span class="stat-label">&#x625;&#x62C;&#x645;&#x627;&#x644;&#x64A; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</span>
    </div>
  </div>
  <button class="btn-add" onclick="openAddModal()">+ &#x625;&#x636;&#x627;&#x641;&#x629; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</button>
  <div class="search-bar">
    <input type="text" id="searchInput" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x623;&#x648; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;..." oninput="filterTable()">
    <button class="btn-search" onclick="filterTable()">&#x628;&#x62D;&#x62B;</button>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</th>
          <th>&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;</th>
          <th>&#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; / &#x627;&#x644;&#x645;&#x642;&#x631;&#x631;</th>
          <th>&#x627;&#x644;&#x645;&#x642;&#x631;&#x631; &#x627;&#x644;&#x630;&#x64A; &#x62A;&#x645; &#x627;&#x644;&#x648;&#x635;&#x648;&#x644; &#x627;&#x644;&#x64A;&#x647; &#x627;&#x644;&#x641;&#x635;&#x644; &#x627;&#x644;&#x641;&#x627;&#x626;&#x62A;</th>
          <th>&#x648;&#x642;&#x62A; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;</th>
          <th>&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x634;&#x647;&#x631; &#x631;&#x645;&#x636;&#x627;&#x646;</th>
          <th>&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646; (&#x627;&#x644;&#x639;&#x627;&#x62F;&#x64A;)</th>
          <th>&#x631;&#x627;&#x628;&#x637; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</th>
          <th>&#x627;&#x644;&#x62D;&#x635;&#x629; &#x628;&#x627;&#x644;&#x62F;&#x642;&#x64A;&#x642;&#x629; (&#x64A;&#x62F;&#x648;&#x64A;)</th>
          <th>&#x627;&#x62C;&#x631;&#x627;&#x621;&#x627;&#x62A;</th>
        </tr>
      </thead>
      <tbody id="groupsBody">
        <tr><td colspan="11" class="no-data">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x60C; &#x627;&#x636;&#x641; &#x627;&#x648;&#x644; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</td></tr>
      </tbody>
    </table>
  </div>
</div>
<div class="modal-bg" id="modal">
  <div class="modal">
    <h2 id="modalTitle">&#x625;&#x636;&#x627;&#x641;&#x629; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x62C;&#x62F;&#x64A;&#x62F;&#x629;</h2>
    <input type="hidden" id="editId">
    <div class="form-grid">
      <div class="field"><label>&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; *</label><input id="f_group_name" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;"></div>
      <div class="field"><label>&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633; *</label><input id="f_teacher_name" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62F;&#x631;&#x633;"></div>
      <div class="field"><label>&#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; / &#x627;&#x644;&#x645;&#x642;&#x631;&#x631;</label><input id="f_level_course" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x627;&#x644;&#x645;&#x633;&#x62A;&#x648;&#x649; 3 - &#x643;&#x62A;&#x627;&#x628; A"></div>
      <div class="field"><label>&#x627;&#x644;&#x645;&#x642;&#x631;&#x631; &#x627;&#x644;&#x630;&#x64A; &#x62A;&#x645; &#x627;&#x644;&#x648;&#x635;&#x648;&#x644; &#x627;&#x644;&#x64A;&#x647; &#x627;&#x644;&#x641;&#x635;&#x644; &#x627;&#x644;&#x641;&#x627;&#x626;&#x62A;</label><input id="f_last_reached" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x627;&#x644;&#x648;&#x62D;&#x62F;&#x629; 5 - &#x627;&#x644;&#x62F;&#x631;&#x633; 3"></div>
      <div class="field"><label>&#x648;&#x642;&#x62A; &#x627;&#x644;&#x62F;&#x631;&#x627;&#x633;&#x629;</label><input id="f_study_time" placeholder="&#x645;&#x62B;&#x627;&#x644;: &#x627;&#x644;&#x633;&#x628;&#x62A; &#x648;&#x627;&#x644;&#x627;&#x62B;&#x646;&#x64A;&#x646; 4-5 &#x645;&#x633;&#x627;&#x621;&#x64B;"></div>
      <div class="field"><label>&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x634;&#x647;&#x631; &#x631;&#x645;&#x636;&#x627;&#x646;</label><input id="f_ramadan_time" placeholder="&#x645;&#x62B;&#x627;&#x644;: 8-9 &#x645;&#x633;&#x627;&#x621;&#x64B;"></div>
      <div class="field"><label>&#x62A;&#x648;&#x642;&#x64A;&#x62A; &#x627;&#x644;&#x627;&#x648;&#x646;&#x644;&#x627;&#x64A;&#x646; (&#x627;&#x644;&#x639;&#x627;&#x62F;&#x64A;)</label><input id="f_online_time" placeholder="&#x645;&#x62B;&#x627;&#x644;: 5-6 &#x645;&#x633;&#x627;&#x621;&#x64B;"></div>
      <div class="field"><label>&#x631;&#x627;&#x628;&#x637; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label><input id="f_group_link" placeholder="https://..." class="ltr"></div>
      <div class="field full"><label>&#x627;&#x644;&#x62D;&#x635;&#x629; &#x628;&#x627;&#x644;&#x62F;&#x642;&#x64A;&#x642;&#x629; (&#x64A;&#x62F;&#x648;&#x64A;)</label><input id="f_session_duration" placeholder="&#x645;&#x62B;&#x627;&#x644;: 60 &#x62F;&#x642;&#x64A;&#x642;&#x629;"></div>
    </div>
    <div class="modal-actions">
      <button class="btn-save" onclick="saveGroup()">&#x62D;&#x641;&#x638;</button>
      <button class="btn-cancel" onclick="closeModal()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<div class="confirm-bg" id="confirmModal">
  <div class="confirm-box">
    <h3>&#x62A;&#x627;&#x643;&#x64A;&#x62F; &#x627;&#x644;&#x62D;&#x630;&#x641;</h3>
    <p>&#x647;&#x644; &#x627;&#x646;&#x62A; &#x645;&#x62A;&#x627;&#x643;&#x62F; &#x627;&#x646;&#x643; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; &#x647;&#x630;&#x647; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;&#x61F;</p>
    <div class="confirm-actions">
      <button class="btn-confirm-del" id="confirmDelBtn">&#x62D;&#x630;&#x641;</button>
      <button class="btn-confirm-cancel" onclick="closeConfirm()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
let allGroups=[];
let deleteTargetId=null;
async function loadGroups(){
  const res=await fetch('/api/groups');
  const data=await res.json();
  allGroups=data.groups||[];
  renderTable(allGroups);
  document.getElementById('totalCount').textContent=allGroups.length;
}
function renderTable(list){
  const body=document.getElementById('groupsBody');
  if(!list.length){body.innerHTML='<tr><td colspan="11" class="no-data">&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;&#x60C; &#x627;&#x636;&#x641; &#x627;&#x648;&#x644; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</td></tr>';return;}
  body.innerHTML=list.map((g,i)=>{
    const link=g.group_link?'<a href="'+g.group_link+'" target="_blank">&#x641;&#x62A;&#x62D; &#x627;&#x644;&#x631;&#x627;&#x628;&#x637;</a>':'-';
    return '<tr><td>'+(i+1)+'</td><td class="name-cell">'+(g.group_name||'-')+'</td><td>'+(g.teacher_name||'-')+'</td><td>'+(g.level_course||'-')+'</td><td>'+(g.last_reached||'-')+'</td><td>'+(g.study_time||'-')+'</td><td>'+(g.ramadan_time||'-')+'</td><td>'+(g.online_time||'-')+'</td><td class="link-cell">'+link+'</td><td>'+(g.session_duration||'-')+'</td><td><button class="action-btn btn-edit" onclick="openEdit('+g.id+')">&#9998;</button><button class="action-btn btn-del" onclick="askDelete('+g.id+')">&#128465;</button></td></tr>';
  }).join('');
}
function filterTable(){
  const q=document.getElementById('searchInput').value.toLowerCase();
  renderTable(allGroups.filter(g=>(g.group_name||'').toLowerCase().includes(q)||(g.teacher_name||'').toLowerCase().includes(q)));
}
function clearForm(){
  ['group_name','teacher_name','level_course','last_reached','study_time','ramadan_time','online_time','group_link','session_duration'].forEach(k=>{const el=document.getElementById('f_'+k);if(el)el.value='';});
  document.getElementById('editId').value='';
}
function openAddModal(){clearForm();document.getElementById('modalTitle').innerHTML='&#x625;&#x636;&#x627;&#x641;&#x629; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x62C;&#x62F;&#x64A;&#x62F;&#x629;';document.getElementById('modal').classList.add('open');}
function openEdit(id){
  const g=allGroups.find(x=>x.id===id);if(!g)return;
  document.getElementById('editId').value=id;
  document.getElementById('modalTitle').innerHTML='&#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;';
  document.getElementById('f_group_name').value=g.group_name||'';
  document.getElementById('f_teacher_name').value=g.teacher_name||'';
  document.getElementById('f_level_course').value=g.level_course||'';
  document.getElementById('f_last_reached').value=g.last_reached||'';
  document.getElementById('f_study_time').value=g.study_time||'';
  document.getElementById('f_ramadan_time').value=g.ramadan_time||'';
  document.getElementById('f_online_time').value=g.online_time||'';
  document.getElementById('f_group_link').value=g.group_link||'';
  document.getElementById('f_session_duration').value=g.session_duration||'';
  document.getElementById('modal').classList.add('open');
}
function closeModal(){document.getElementById('modal').classList.remove('open');}
async function saveGroup(){
  const editId=document.getElementById('editId').value;
  const body={
    group_name:document.getElementById('f_group_name').value.trim(),
    teacher_name:document.getElementById('f_teacher_name').value.trim(),
    level_course:document.getElementById('f_level_course').value.trim(),
    last_reached:document.getElementById('f_last_reached').value.trim(),
    study_time:document.getElementById('f_study_time').value.trim(),
    ramadan_time:document.getElementById('f_ramadan_time').value.trim(),
    online_time:document.getElementById('f_online_time').value.trim(),
    group_link:document.getElementById('f_group_link').value.trim(),
    session_duration:document.getElementById('f_session_duration').value.trim(),
  };
  if(!body.group_name){showToast('&#x627;&#x633;&#x645; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x645;&#x637;&#x644;&#x648;&#x628;','#e53935');return;}
  const url=editId?'/api/groups/'+editId:'/api/groups';
  const method=editId?'PUT':'POST';
  const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(body)});
  const data=await res.json();
  if(data.ok){closeModal();showToast(editId?'&#x62A;&#x645; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x628;&#x646;&#x62C;&#x627;&#x62D;':'&#x62A;&#x645; &#x625;&#x636;&#x627;&#x641;&#x629; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x628;&#x646;&#x62C;&#x627;&#x62D;');loadGroups();}
  else{showToast(data.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');}
}
function askDelete(id){deleteTargetId=id;document.getElementById('confirmModal').classList.add('open');document.getElementById('confirmDelBtn').onclick=confirmDelete;}
async function confirmDelete(){
  if(!deleteTargetId)return;
  const res=await fetch('/api/groups/'+deleteTargetId,{method:'DELETE',credentials:'include'});
  const data=await res.json();
  closeConfirm();
  if(data.ok){showToast('&#x62A;&#x645; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x628;&#x646;&#x62C;&#x627;&#x62D;');loadGroups();}
  else{showToast(data.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');}
  deleteTargetId=null;
}
function closeConfirm(){document.getElementById('confirmModal').classList.remove('open');}
function showToast(msg,bg='#00BCD4'){const t=document.getElementById('toast');t.textContent=msg;t.style.background=bg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3000);}
loadGroups();
</script>
</body>
</html>"""

@app.route("/groups")
@login_required
def groups():
    return GROUPS_HTML

@app.route("/api/groups", methods=["GET"])
@login_required
def api_groups_get():
    db = get_db()
    rows = db.execute("SELECT * FROM student_groups ORDER BY id ASC").fetchall()
    return jsonify({"groups": [dict(r) for r in rows]})

def _student_groups_writable_cols(db):
    # Reflect the live schema so a user who has deleted a column via the UI
    # (e.g. session_duration) doesn't break every subsequent add/update.
    cols = [r[1] for r in db.execute("PRAGMA table_info(student_groups)").fetchall()]
    return [c for c in cols if c not in ("id", "created_at")]

@app.route("/api/groups", methods=["POST"])
@login_required
def api_groups_add():
    d = request.get_json() or {}
    db = get_db()
    try:
        cols = _student_groups_writable_cols(db)
        placeholders = ",".join(["?"] * len(cols))
        values = tuple(d.get(c) for c in cols)
        db.execute("INSERT INTO student_groups (" + ",".join(cols) + ") VALUES (" + placeholders + ")", values)
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/groups/<int:gid>", methods=["PUT"])
@login_required
def api_groups_update(gid):
    d = request.get_json() or {}
    db = get_db()
    try:
        cols = _student_groups_writable_cols(db)
        set_clause = ",".join([c + "=?" for c in cols])
        values = tuple(d.get(c) for c in cols) + (gid,)
        db.execute("UPDATE student_groups SET " + set_clause + " WHERE id=?", values)
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/groups/<int:gid>", methods=["DELETE"])
@login_required
def api_groups_delete(gid):
    try:
        db = get_db()
        db.execute("DELETE FROM student_groups WHERE id=?", (gid,))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/groups/cleanup-empty", methods=["POST"])
@login_required
def api_groups_cleanup_empty():
    try:
        db = get_db()
        cur = db.execute("DELETE FROM student_groups WHERE group_name IS NULL OR TRIM(group_name) = ''")
        deleted = cur.rowcount if cur.rowcount is not None else 0
        db.commit()
        return jsonify({"ok": True, "deleted": deleted})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/groups-students", methods=["GET"])
@login_required
def api_groups_students():
    """Group → student roster. By default, only ACTIVE students are
    returned. Pass ?include_inactive=1 to get every student regardless
    of registration status."""
    db = get_db()
    include_inactive = (request.args.get("include_inactive") or "") in ("1", "true", "yes")
    act_frag, act_val = _active_students_filter()

    groups_sql = ("SELECT DISTINCT group_name_student FROM students "
                  "WHERE group_name_student IS NOT NULL AND group_name_student <> ''")
    students_sql = ("SELECT id, student_name, personal_id, whatsapp FROM students "
                    "WHERE group_name_student = ?")
    params_for_student = []
    if act_frag and not include_inactive:
        groups_sql += " AND " + act_frag
        students_sql += " AND " + act_frag
        params_for_student = [act_val]
    groups_sql += " ORDER BY group_name_student"
    students_sql += " ORDER BY student_name"

    if act_frag and not include_inactive:
        rows = db.execute(groups_sql, (act_val,)).fetchall()
    else:
        rows = db.execute(groups_sql).fetchall()

    out = {}
    for row in rows:
        gname = row[0]
        students = db.execute(students_sql, tuple([gname] + params_for_student)).fetchall()
        out[gname] = [dict(s) for s in students]
    return jsonify(out)

def _att_normalize_date(s):
    """Normalise any date representation the app has ever stored to ISO
    YYYY-MM-DD. Handles:
      - already ISO: "2026-04-01"
      - D/M/YYYY:   "9/2/2026"
      - mixed sep:  "31/1-2026" (slash then dash)
      - D-M-YYYY:   "09-02-2026"
      - Y/M/D:      "2026/02/09"
      - trailing Arabic era marker like "م" or Latin punctuation
    Any value the parser cannot interpret is returned unchanged so we
    never lose data on a surprise format; use _att_normalize_ar on free
    text."""
    import re as _re_local
    if not s:
        return ""
    s = str(s).strip()
    if not s:
        return ""
    nums = _re_local.findall(r"\d+", s)
    if len(nums) < 3:
        return s
    if len(nums[0]) == 4:
        y, m, d = nums[0], nums[1], nums[2]
    elif len(nums[-1]) == 4:
        d, m, y = nums[0], nums[1], nums[-1]
    else:
        d, m, y = nums[0], nums[1], nums[2]
        if len(y) == 2:
            y = ("20" + y) if int(y) < 70 else ("19" + y)
    try:
        iy, im, id_ = int(y), int(m), int(d)
        if not (1 <= im <= 12 and 1 <= id_ <= 31):
            return s
        return "%04d-%02d-%02d" % (iy, im, id_)
    except Exception:
        return s


def _att_normalize_ar(s):
    """Loose Arabic string normalisation used to match imported roster names
    against attendance rows: trim, collapse whitespace runs, lowercase,
    fold alef/yeh/teh-marbouta variants, drop tashkeel."""
    if not s:
        return ""
    s = str(s).strip().lower()
    # alef family -> bare alef
    for ch in ("أ", "إ", "آ", "ٱ"):
        s = s.replace(ch, "ا")
    s = s.replace("ة", "ه")  # teh marbouta -> heh
    s = s.replace("ى", "ي")  # alef maksura -> yeh
    out = []
    prev_space = False
    for ch in s:
        c = ord(ch)
        if 0x064B <= c <= 0x065F:   # strip tashkeel
            continue
        if ch.isspace():
            if prev_space:
                continue
            prev_space = True
            out.append(" ")
        else:
            prev_space = False
            out.append(ch)
    return "".join(out).strip()


@app.route("/api/attendance/check", methods=["GET"])
@login_required
def api_attendance_check():
    group_name = request.args.get("group", "").strip()
    att_date = request.args.get("date", "").strip()
    if not group_name or not att_date:
        return jsonify({"exists": False, "records": []})
    db = get_db()

    # Loose match: fetch every row for the trimmed group name, then filter
    # in Python by normalised date + normalised name. This tolerates every
    # date format the table has ever held (D/M/YYYY, D/M-YYYYم, ISO, ...)
    # without requiring a full DB rewrite. The one-time migration runs at
    # start-up, but this still guards against stray legacy values.
    all_rows = db.execute(
        "SELECT * FROM attendance WHERE TRIM(group_name)=TRIM(?) ORDER BY id ASC",
        (group_name,),
    ).fetchall()
    target_date = _att_normalize_date(att_date)
    records = []
    for r in all_rows:
        if _att_normalize_date(r["attendance_date"]) == target_date:
            records.append(dict(r))

    # Enrich each record with personal_id looked up from the students table,
    # first by exact name inside the group, then by normalised-name fallback.
    student_rows = db.execute(
        "SELECT student_name, personal_id FROM students "
        "WHERE TRIM(group_name_student)=TRIM(?)",
        (group_name,),
    ).fetchall()
    name_to_pid = {}
    norm_to_pid = {}
    for s in student_rows:
        nm = (s["student_name"] or "").strip()
        pid = (s["personal_id"] or "").strip() if "personal_id" in s.keys() else ""
        if not nm:
            continue
        if pid:
            name_to_pid.setdefault(nm, pid)
            norm_to_pid.setdefault(_att_normalize_ar(nm), pid)
    # Fallback scan across all students when a group-local match fails.
    if records:
        all_rows = db.execute(
            "SELECT student_name, personal_id FROM students"
        ).fetchall()
        for s in all_rows:
            nm = (s["student_name"] or "").strip()
            pid = (s["personal_id"] or "").strip() if "personal_id" in s.keys() else ""
            if nm and pid:
                name_to_pid.setdefault(nm, pid)
                norm_to_pid.setdefault(_att_normalize_ar(nm), pid)

    for rec in records:
        nm = (rec.get("student_name") or "").strip()
        pid = name_to_pid.get(nm) or norm_to_pid.get(_att_normalize_ar(nm), "")
        rec["personal_id"] = pid
        rec["student_name_norm"] = _att_normalize_ar(nm)

    return jsonify({"exists": len(records) > 0, "records": records})

@app.route("/api/dashboard/stats", methods=["GET"])
@login_required
def api_dashboard_stats():
    db = get_db()

    def _cfg(page, comp, default):
        v = get_setting(page, comp, default)
        return v if _is_safe_ident(v) else default

    def _safe_int(sql, params=()):
        try:
            row = db.execute(sql, params).fetchone()
            return (row[0] if row else 0) or 0
        except Exception:
            return 0

    students_tbl      = _cfg("dashboard", "students_table", "students")
    groups_tbl        = _cfg("dashboard", "groups_table", "student_groups")
    attendance_tbl    = _cfg("dashboard", "attendance_table", "attendance")
    subject_col       = _cfg("dashboard", "students_subject_column", "class_name")
    class_col         = _cfg("dashboard", "students_class_column", "class_name")
    teacher_col       = _cfg("dashboard", "students_teacher_column", "teacher_2026")
    group_col         = _cfg("attendance", "student_group_column", "group_name_student")
    status_col        = _cfg("dashboard", "attendance_status_column", "status")
    level_col         = _cfg("groups", "level_column", "level_course")
    group_teacher_col = _cfg("groups", "teacher_column", "teacher_name")

    student_cols_all = set(get_table_columns(students_tbl))
    group_cols_all   = set(get_table_columns(groups_tbl))
    att_cols_all     = set(get_table_columns(attendance_tbl))

    subject_cand = [c for c in {subject_col, class_col, teacher_col, group_col, "group_online"}
                    if c and _is_safe_ident(c) and c in student_cols_all]

    english_kws = ["english",
                   "إنجليزي",
                   "انجليزي",
                   "إنجليز"]
    math_kws    = ["math",
                   "رياضيات",
                   "رياضي"]

    # Per user request: english/math student counts reflect ACTIVE students
    # only (registration_term2_2026 = "تم التسجيل" by default, configurable
    # via settings → students.active_column / active_value).
    _act_frag, _act_val = _active_students_filter()

    def _count_any(cols, keywords):
        if not cols or not keywords:
            return 0
        clauses, params = [], []
        for kw in keywords:
            pattern = "%" + kw.lower() + "%"
            for col in cols:
                clauses.append("lower(COALESCE(" + col + ",'')) LIKE ?")
                params.append(pattern)
        where = "(" + " OR ".join(clauses) + ")"
        if _act_frag:
            where = "(" + _act_frag + ") AND " + where
            params = [_act_val] + params
        sql = "SELECT COUNT(DISTINCT id) FROM " + students_tbl + " WHERE " + where
        return _safe_int(sql, tuple(params))

    english_students = _count_any(subject_cand, english_kws)
    math_students    = _count_any(subject_cand, math_kws)

    groups = _safe_int("SELECT COUNT(*) FROM " + groups_tbl)

    # Teachers = union of distinct names across students and groups tables.
    teacher_names = set()
    if group_teacher_col in group_cols_all:
        try:
            for r in db.execute(
                "SELECT DISTINCT " + group_teacher_col + " FROM " + groups_tbl +
                " WHERE " + group_teacher_col + " IS NOT NULL AND " + group_teacher_col + "<>''"
            ).fetchall():
                v = (r[0] or "").strip()
                if v:
                    teacher_names.add(v)
        except Exception:
            pass
    if teacher_col in student_cols_all:
        try:
            for r in db.execute(
                "SELECT DISTINCT " + teacher_col + " FROM " + students_tbl +
                " WHERE " + teacher_col + " IS NOT NULL AND " + teacher_col + "<>''"
            ).fetchall():
                v = (r[0] or "").strip()
                if v:
                    teacher_names.add(v)
        except Exception:
            pass
    teachers = len(teacher_names)

    # Staff: every user that is not an admin (reception, coordinators, media, etc.).
    staff = _safe_int(
        "SELECT COUNT(*) FROM users WHERE role IS NOT NULL AND role<>'' AND role<>'admin'"
    )

    # English levels: keyword match on the level column, fall back to distinct levels.
    english_levels = 0
    if level_col in group_cols_all:
        english_levels = _safe_int(
            "SELECT COUNT(DISTINCT " + level_col + ") FROM " + groups_tbl +
            " WHERE " + level_col + " IS NOT NULL AND " + level_col + "<>'' AND (" +
            "lower(" + level_col + ") LIKE ? OR " + level_col + " LIKE ? OR " + level_col + " LIKE ?)",
            ("%english%",
             "%إنجليزي%",
             "%انجليزي%")
        )
        if english_levels == 0:
            english_levels = _safe_int(
                "SELECT COUNT(DISTINCT " + level_col + ") FROM " + groups_tbl +
                " WHERE " + level_col + " IS NOT NULL AND " + level_col + "<>''"
            )

    STATUS_PRESENT = "حاضر"
    STATUS_ABSENT  = "غائب"
    STATUS_LATE    = "متأخر"
    attendance_rate = 0.0
    violations = 0
    if status_col in att_cols_all:
        total_att = _safe_int(
            "SELECT COUNT(*) FROM " + attendance_tbl + " WHERE " + status_col + " IN (?,?,?)",
            (STATUS_PRESENT, STATUS_ABSENT, STATUS_LATE),
        )
        present_att = _safe_int(
            "SELECT COUNT(*) FROM " + attendance_tbl + " WHERE " + status_col + "=?",
            (STATUS_PRESENT,),
        )
        violations = _safe_int(
            "SELECT COUNT(*) FROM " + attendance_tbl + " WHERE " + status_col + " IN (?,?)",
            (STATUS_ABSENT, STATUS_LATE),
        )
        late_att = _safe_int(
            "SELECT COUNT(*) FROM " + attendance_tbl + " WHERE " + status_col + "=?",
            (STATUS_LATE,),
        )
        # ATTENDANCE RULE: late counts as attended.
        attendance_rate = round((present_att + late_att) / total_att * 100, 1) if total_att else 0.0

    return jsonify({
        "ok": True,
        "english_students": english_students,
        "math_students": math_students,
        "groups": groups,
        "teachers": teachers,
        "staff": staff,
        "english_levels": english_levels,
        "attendance_rate": attendance_rate,
        "violations": violations,
    })

@app.route("/api/attendance/student-stats", methods=["GET"])
@login_required
def api_attendance_student_stats():
    """Per-student attendance stats.

    ATTENDANCE RULE: total_sessions is the count of *distinct*
    (attendance_date, group_name) pairs the student appears in — not a
    raw row count — so duplicate imports don't double-count. The
    attendance_rate formula is (attended + late) / total_sessions * 100
    (late students were physically present, just late).
    """
    group_name = request.args.get("group", "").strip()
    db = get_db()
    if group_name:
        rows = db.execute(
            "SELECT student_name, attendance_date, group_name, status FROM attendance "
            "WHERE group_name=? AND student_name IS NOT NULL AND student_name<>\'\'",
            (group_name,)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT student_name, attendance_date, group_name, status FROM attendance "
            "WHERE student_name IS NOT NULL AND student_name<>\'\'"
        ).fetchall()
    STATUS_PRESENT = "\u062D\u0627\u0636\u0631"
    STATUS_ABSENT  = "\u063A\u0627\u0626\u0628"
    STATUS_LATE    = "\u0645\u062A\u0623\u062E\u0631"
    # per-student sessions set and status counters
    stats = {}
    for r in rows:
        name = r["student_name"]
        if not name:
            continue
        d = _att_normalize_date(r["attendance_date"])
        g = (r["group_name"] or "").strip()
        bucket = stats.setdefault(name, {
            "present": 0, "absent": 0, "late": 0, "total": 0, "_sessions": set(),
        })
        bucket["_sessions"].add((d, g))
        st = (r["status"] or "").strip()
        if st == STATUS_PRESENT:
            bucket["present"] += 1
        elif st == STATUS_ABSENT:
            bucket["absent"] += 1
        elif st == STATUS_LATE:
            bucket["late"] += 1
    out = {}
    for name, s in stats.items():
        total = len(s["_sessions"])
        s["total"] = total
        s["pct"] = round((s["present"] + s["late"]) / total * 100, 1) if total else 0.0
        s.pop("_sessions", None)
        out[name] = s
    return jsonify({"ok": True, "stats": out})


@app.route("/api/attendance/summary", methods=["GET"])
@login_required
def api_attendance_summary():
    """Unified attendance-summary endpoint for the ملخص الحصص modal.

    Joins attendance rows with session_durations on (group_name,
    attendance_date → session_date) to compute hours alongside counts.

    ATTENDANCE RULE:
      - total_sessions per student = COUNT(DISTINCT (date, group))
      - total_sessions per group   = COUNT(DISTINCT date)
      - attendance_rate = (attended + late) / total_sessions * 100
      - hours_total_min   = sum of duration over all of the student's sessions
      - hours_present_min = sum where status in (حاضر, متأخر)
      - hours_absent_min  = sum where status = غائب
    """
    view = (request.args.get("view") or "").strip().lower()
    db = get_db()
    PRESENT = "حاضر"
    ABSENT  = "غائب"
    LATE    = "متأخر"

    def _rate(attended, late, total):
        return round((attended + late) / total * 100, 1) if total else 0.0

    # Pre-build a (group, normalised date) -> duration_minutes map so we
    # can look up each attendance row in O(1).
    def _load_duration_map():
        try:
            rows = db.execute("SELECT group_name, session_date, duration_minutes FROM session_durations").fetchall()
            m = {}
            for r in rows:
                g = (r[0] or "").strip()
                d = _att_normalize_date(r[1])
                m[(g, d)] = int(r[2] or 0)
            return m
        except Exception:
            return {}

    if view == "init" or view == "":
        rows = db.execute(
            "SELECT DISTINCT group_name FROM attendance "
            "WHERE group_name IS NOT NULL AND group_name <> \'\' "
            "ORDER BY group_name"
        ).fetchall()
        return jsonify({"groups": [r[0] for r in rows]})

    if view == "groups":
        raw = request.args.getlist("g") or []
        # Tolerate comma-separated fallback: ?g=A,B,C
        if len(raw) == 1 and "," in raw[0]:
            raw = raw[0].split(",")
        gnames = [g.strip() for g in raw if (g and g.strip())]
        if not gnames:
            return jsonify({"ok": False, "error": "at least one group required"}), 400
        placeholders = ",".join(["?"] * len(gnames))
        sql = (
            "SELECT attendance_date, group_name, student_name, status FROM attendance "
            "WHERE TRIM(group_name) IN (" + placeholders + ") "
            "AND student_name IS NOT NULL AND student_name<>\'\'"
        )
        rows = db.execute(sql, tuple(gnames)).fetchall()
        dur_map = _load_duration_map()
        per_student = {}
        sessions = set()   # distinct (date, group) pairs across selected groups
        for r in rows:
            d = _att_normalize_date(r["attendance_date"])
            g = (r["group_name"] or "").strip()
            n = (r["student_name"] or "").strip()
            st = (r["status"] or "").strip()
            if not n:
                continue
            sessions.add((d, g))
            s = per_student.setdefault(n, {
                "student_name": n, "present": 0, "absent": 0, "late": 0,
                "_dg": set(), "_groups": set(), "_counted_dur": set(),
                "hours_total_min": 0, "hours_present_min": 0, "hours_absent_min": 0,
            })
            s["_dg"].add((d, g))
            if g:
                s["_groups"].add(g)
            key = (g, d)
            dur = dur_map.get(key, 0)
            if key not in s["_counted_dur"]:
                s["_counted_dur"].add(key)
                s["hours_total_min"] += dur
                if st == PRESENT or st == LATE:
                    s["hours_present_min"] += dur
                elif st == ABSENT:
                    s["hours_absent_min"] += dur
            if st == PRESENT:
                s["present"] += 1
            elif st == ABSENT:
                s["absent"] += 1
            elif st == LATE:
                s["late"] += 1
        students = []
        rates = []
        for n in sorted(per_student.keys()):
            s = per_student[n]
            total = len(s["_dg"])
            r_pct = _rate(s["present"], s["late"], total)
            rates.append(r_pct)
            students.append({
                "student_name": n,
                "group_name": ", ".join(sorted(s["_groups"])) or "",
                "total_sessions": total,
                "present": s["present"], "absent": s["absent"], "late": s["late"],
                "rate_pct": r_pct,
                "hours_total_min":   s["hours_total_min"],
                "hours_present_min": s["hours_present_min"],
                "hours_absent_min":  s["hours_absent_min"],
            })
        total_minutes = sum(dur_map.get((g, d), 0) for (d, g) in sessions)
        avg_rate = round(sum(rates) / len(rates), 1) if rates else 0.0
        return jsonify({
            "groups": gnames,
            "total_sessions": len(sessions),
            "total_minutes": total_minutes,
            "students_count": len(per_student),
            "avg_attendance_rate": avg_rate,
            "students": students,
        })

    if view == "group":
        gname = (request.args.get("group") or "").strip()
        if not gname:
            return jsonify({"ok": False, "error": "group required"}), 400
        rows = db.execute(
            "SELECT attendance_date, student_name, status FROM attendance "
            "WHERE TRIM(group_name)=TRIM(?) AND student_name IS NOT NULL AND student_name<>\'\'",
            (gname,)
        ).fetchall()
        dur_map = _load_duration_map()
        group_sessions = set()
        group_total_minutes = 0
        per_student = {}
        for r in rows:
            d = _att_normalize_date(r["attendance_date"])
            n = (r["student_name"] or "").strip()
            st = (r["status"] or "").strip()
            if not n:
                continue
            group_sessions.add(d)
            s = per_student.setdefault(n, {
                "student_name": n, "present": 0, "absent": 0, "late": 0,
                "_dates": set(), "_counted_dur": set(),
                "hours_total_min": 0, "hours_present_min": 0, "hours_absent_min": 0,
            })
            s["_dates"].add(d)
            dur = dur_map.get((gname.strip(), d), 0)
            if (d,) not in s["_counted_dur"]:
                s["_counted_dur"].add((d,))
                s["hours_total_min"] += dur
                if st == PRESENT or st == LATE:
                    s["hours_present_min"] += dur
                elif st == ABSENT:
                    s["hours_absent_min"] += dur
            if st == PRESENT:
                s["present"] += 1
            elif st == ABSENT:
                s["absent"] += 1
            elif st == LATE:
                s["late"] += 1
        # Group total_minutes = sum of duration_minutes over its distinct dates
        for d in group_sessions:
            group_total_minutes += dur_map.get((gname.strip(), d), 0)
        students = []
        for n in sorted(per_student.keys()):
            s = per_student[n]
            total = len(s["_dates"])
            students.append({
                "student_name": n,
                "group_name": gname,
                "total_sessions": total,
                "present": s["present"], "absent": s["absent"], "late": s["late"],
                "rate_pct": _rate(s["present"], s["late"], total),
                "hours_total_min":   s["hours_total_min"],
                "hours_present_min": s["hours_present_min"],
                "hours_absent_min":  s["hours_absent_min"],
            })
        return jsonify({
            "group_name": gname,
            "total_sessions": len(group_sessions),
            "total_minutes": group_total_minutes,
            "students": students,
        })

    if view == "all":
        rows = db.execute(
            "SELECT attendance_date, group_name, student_name, status FROM attendance "
            "WHERE student_name IS NOT NULL AND student_name<>\'\'"
        ).fetchall()
        dur_map = _load_duration_map()
        per_student = {}
        global_sessions = set()
        for r in rows:
            d = _att_normalize_date(r["attendance_date"])
            g = (r["group_name"] or "").strip()
            n = (r["student_name"] or "").strip()
            st = (r["status"] or "").strip()
            if not n:
                continue
            global_sessions.add((d, g))
            s = per_student.setdefault(n, {
                "student_name": n, "present": 0, "absent": 0, "late": 0,
                "_dg": set(), "_groups": set(), "_counted_dur": set(),
                "hours_total_min": 0, "hours_present_min": 0, "hours_absent_min": 0,
            })
            s["_dg"].add((d, g))
            if g:
                s["_groups"].add(g)
            key = (g, d)
            dur = dur_map.get(key, 0)
            if key not in s["_counted_dur"]:
                s["_counted_dur"].add(key)
                s["hours_total_min"] += dur
                if st == PRESENT or st == LATE:
                    s["hours_present_min"] += dur
                elif st == ABSENT:
                    s["hours_absent_min"] += dur
            if st == PRESENT:
                s["present"] += 1
            elif st == ABSENT:
                s["absent"] += 1
            elif st == LATE:
                s["late"] += 1
        students = []
        for n in sorted(per_student.keys()):
            s = per_student[n]
            total = len(s["_dg"])
            students.append({
                "student_name": n,
                "group_name": ", ".join(sorted(s["_groups"])) or "",
                "total_sessions": total,
                "present": s["present"], "absent": s["absent"], "late": s["late"],
                "rate_pct": _rate(s["present"], s["late"], total),
                "hours_total_min":   s["hours_total_min"],
                "hours_present_min": s["hours_present_min"],
                "hours_absent_min":  s["hours_absent_min"],
            })
        # Total minutes across every distinct (date, group) in attendance.
        # dur_map keys are (group, date); global_sessions stores (date, group).
        total_minutes = sum(dur_map.get((g, d), 0) for (d, g) in global_sessions)
        return jsonify({
            "total_sessions": len(global_sessions),
            "total_minutes": total_minutes,
            "students": students,
        })

    if view == "student":
        q_raw = (request.args.get("q") or "").strip()
        if not q_raw:
            return jsonify({"ok": False, "error": "q required"}), 400
        q_norm = _att_normalize_ar(q_raw)
        rows = db.execute(
            "SELECT attendance_date, group_name, student_name, status FROM attendance "
            "WHERE student_name IS NOT NULL AND student_name<>\'\'"
        ).fetchall()
        dur_map = _load_duration_map()
        matches_map = {}
        for r in rows:
            n = (r["student_name"] or "").strip()
            if not n:
                continue
            n_norm = _att_normalize_ar(n)
            if q_norm not in n_norm:
                continue
            d = _att_normalize_date(r["attendance_date"])
            g = (r["group_name"] or "").strip()
            st = (r["status"] or "").strip()
            bucket = matches_map.setdefault(n_norm, {
                "student_name": n,
                "_dg": set(), "_groups": set(), "_counted_dur": set(),
                "present": 0, "absent": 0, "late": 0,
                "hours_total_min": 0, "hours_present_min": 0, "hours_absent_min": 0,
            })
            bucket["_dg"].add((d, g))
            if g:
                bucket["_groups"].add(g)
            key = (g, d)
            dur = dur_map.get(key, 0)
            if key not in bucket["_counted_dur"]:
                bucket["_counted_dur"].add(key)
                bucket["hours_total_min"] += dur
                if st == PRESENT or st == LATE:
                    bucket["hours_present_min"] += dur
                elif st == ABSENT:
                    bucket["hours_absent_min"] += dur
            if st == PRESENT:
                bucket["present"] += 1
            elif st == ABSENT:
                bucket["absent"] += 1
            elif st == LATE:
                bucket["late"] += 1
        matches = []
        for bucket in matches_map.values():
            total = len(bucket["_dg"])
            matches.append({
                "student_name": bucket["student_name"],
                "group_name": ", ".join(sorted(bucket["_groups"])) or "",
                "total_sessions": total,
                "present": bucket["present"], "absent": bucket["absent"], "late": bucket["late"],
                "rate_pct": _rate(bucket["present"], bucket["late"], total),
                "hours_total_min":   bucket["hours_total_min"],
                "hours_present_min": bucket["hours_present_min"],
                "hours_absent_min":  bucket["hours_absent_min"],
            })
        matches.sort(key=lambda m: (-m["total_sessions"], m["student_name"]))
        return jsonify({"matches": matches})

    if view == "all_groups":
        # One row per group: sessions, total duration, distinct students,
        # and the mean of per-student attendance_rate inside that group.
        rows = db.execute(
            "SELECT attendance_date, group_name, student_name, status FROM attendance "
            "WHERE group_name IS NOT NULL AND group_name<>\'\'"
        ).fetchall()
        dur_map = _load_duration_map()
        per_group = {}
        for r in rows:
            g = (r["group_name"] or "").strip()
            if not g:
                continue
            d = _att_normalize_date(r["attendance_date"])
            n = (r["student_name"] or "").strip()
            st = (r["status"] or "").strip()
            gb = per_group.setdefault(g, {
                "group_name": g,
                "_dates": set(), "_students": {}, "total_minutes": 0,
                "_counted_dur": set(),
            })
            gb["_dates"].add(d)
            if (g, d) not in gb["_counted_dur"]:
                gb["_counted_dur"].add((g, d))
                gb["total_minutes"] += dur_map.get((g, d), 0)
            if n:
                sb = gb["_students"].setdefault(n, {"present":0,"absent":0,"late":0,"_dates":set()})
                sb["_dates"].add(d)
                if st == PRESENT:
                    sb["present"] += 1
                elif st == ABSENT:
                    sb["absent"] += 1
                elif st == LATE:
                    sb["late"] += 1
        groups = []
        total_sessions_all = 0
        total_minutes_all  = 0
        student_rates_all  = []
        all_students_set   = set()
        for g in sorted(per_group.keys()):
            gb = per_group[g]
            sessions = len(gb["_dates"])
            mins     = gb["total_minutes"]
            students_n = len(gb["_students"])
            rates = []
            for sname, sb in gb["_students"].items():
                t = len(sb["_dates"])
                r_pct = _rate(sb["present"], sb["late"], t)
                rates.append(r_pct)
                student_rates_all.append(r_pct)
                all_students_set.add(sname)
            avg_rate = round(sum(rates)/len(rates), 1) if rates else 0.0
            groups.append({
                "group_name": g,
                "total_sessions": sessions,
                "total_minutes": mins,
                "students_count": students_n,
                "avg_attendance_rate": avg_rate,
            })
            total_sessions_all += sessions
            total_minutes_all  += mins
        overall = {
            "total_sessions": total_sessions_all,
            "total_minutes":  total_minutes_all,
            "students_count": len(all_students_set),
            "avg_attendance_rate": round(sum(student_rates_all)/len(student_rates_all), 1) if student_rates_all else 0.0,
        }
        return jsonify({"groups": groups, "overall": overall})

    return jsonify({"ok": False, "error": "unknown view"}), 400


@app.route("/api/logout", methods=["POST", "GET"])
def api_logout():
    session.clear()
    return redirect("/")

# v2

# &#x2500;&#x2500;&#x2500; Taqseet (Payment Plans) API &#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;&#x2500;

@app.route('/api/taqseet', methods=['GET'])
@login_required
def api_taqseet_get():
    db = get_db()
    rows = db.execute("SELECT * FROM taqseet ORDER BY id").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/taqseet', methods=['POST'])
@login_required
def api_taqseet_post():
    d = request.get_json()
    db = get_db()
    db.execute("""INSERT INTO taqseet (
        taqseet_method, student_name, course_amount, num_installments,
        inst1, paid1, date1, inst2, paid2, date2, inst3, paid3, date3, inst4, paid4, date4,
        inst5, paid5, date5, inst6, paid6, date6, inst7, paid7, date7, inst8, paid8, date8,
        inst9, paid9, date9, inst10, paid10, date10, inst11, paid11, date11, inst12, paid12, date12,
        study_hours, start_date
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
    (d.get('taqseet_method',''), d.get('student_name',''), d.get('course_amount',''),
     d.get('num_installments',''),
     d.get('inst1',''), d.get('paid1',''), d.get('date1',''), d.get('inst2',''), d.get('paid2',''), d.get('date2',''),
     d.get('inst3',''), d.get('paid3',''), d.get('date3',''), d.get('inst4',''), d.get('paid4',''), d.get('date4',''),
     d.get('inst5',''), d.get('paid5',''), d.get('date5',''), d.get('inst6',''), d.get('paid6',''), d.get('date6',''),
     d.get('inst7',''), d.get('paid7',''), d.get('date7',''), d.get('inst8',''), d.get('paid8',''), d.get('date8',''),
     d.get('inst9',''), d.get('paid9',''), d.get('date9',''), d.get('inst10',''), d.get('paid10',''), d.get('date10',''),
     d.get('inst11',''), d.get('paid11',''), d.get('date11',''), d.get('inst12',''), d.get('paid12',''), d.get('date12',''),
     d.get('study_hours',''), d.get('start_date','')))
    db.commit()
    return jsonify({"ok": True, "id": db.execute("SELECT last_insert_rowid()").fetchone()[0]})

@app.route('/api/taqseet/<int:row_id>', methods=['PUT'])
@login_required
def api_taqseet_put(row_id):
    d = request.get_json() or {}
    db = get_db()
    # Reflect live schema so columns auto-added via Excel import also persist.
    cols = [r[1] for r in db.execute("PRAGMA table_info(taqseet)").fetchall()]
    writable = [c for c in cols if c != "id" and c in d]
    if not writable:
        return jsonify({"ok": True})
    set_clause = ",".join([c + "=?" for c in writable])
    values = tuple(d.get(c, '') for c in writable) + (row_id,)
    db.execute("UPDATE taqseet SET " + set_clause + " WHERE id=?", values)
    db.commit()
    return jsonify({"ok": True})

@app.route('/api/taqseet/<int:row_id>', methods=['DELETE'])
@login_required
def api_taqseet_delete(row_id):
    db = get_db()
    db.execute("DELETE FROM taqseet WHERE id=?", (row_id,))
    db.commit()
    return jsonify({"ok": True})

@app.route('/api/taqseet-labels', methods=['GET'])
@login_required
def api_taqseet_labels_get():
    db = get_db()
    try:
        rows = db.execute("SELECT col_key,col_label FROM taqseet_col_labels").fetchall()
        return jsonify({r[0]: r[1] for r in rows})
    except Exception:
        return jsonify({})


@app.route('/api/payments/<int:student_id>/<int:inst_num>', methods=['PUT'])
@login_required
def api_payment_put(student_id, inst_num):
    db = get_db()
    data = request.get_json()
    db.execute("""INSERT INTO student_payments(student_id,inst_num,inst_type,price,paid) VALUES(?,?,?,?,?)
        ON CONFLICT(student_id,inst_num) DO UPDATE SET inst_type=EXCLUDED.inst_type, price=EXCLUDED.price, paid=EXCLUDED.paid""",
        (student_id, inst_num, data.get('inst_type',''), data.get('price',0), data.get('paid',0)))
    db.commit()
    # Sync paid amount to taqseet table
    paid_val = data.get('paid', 0)
    student_row = db.execute("SELECT installment_type FROM students WHERE id=?", (student_id,)).fetchone()
    if student_row and student_row[0]:
        paid_col = "paid" + str(inst_num)
        db.execute("UPDATE taqseet SET " + paid_col + "=? WHERE taqseet_method=?",
                   (str(paid_val), str(student_row[0])))
        db.commit()
    return jsonify({"ok": True})

IMPORT_TABLE_FIELDS = {
    "students": [
        "personal_id","student_name","whatsapp","class_name","old_new_2026",
        "registration_term2_2026","group_name_student","group_online","final_result",
        "level_reached_2026","suitable_level_2026","books_received","teacher_2026",
        "installment1","installment2","installment3","installment4","installment5",
        "mother_phone","father_phone","other_phone","residence","home_address",
        "road","complex_name","installment_type",
    ],
    "student_groups": [
        "group_name","teacher_name","level_course","last_reached","study_time",
        "ramadan_time","online_time","group_link","session_duration",
        "session_minutes_normal",
        "hours_in_person_auto","hours_online_only","hours_all_online",
        "total_required_hours",
    ],
    "attendance": [
        "attendance_date","day_name","group_name","student_name","contact_number",
        "status","message","message_status","study_status",
    ],
    "taqseet": [
        "taqseet_method","student_name","course_amount","num_installments",
        "inst1","paid1","date1","inst2","paid2","date2","inst3","paid3","date3",
        "inst4","paid4","date4","inst5","paid5","date5","inst6","paid6","date6",
        "inst7","paid7","date7","inst8","paid8","date8","inst9","paid9","date9",
        "inst10","paid10","date10","inst11","paid11","date11","inst12","paid12","date12",
        "study_hours","start_date",
    ],
    "evaluations": [
        "form_fill_date","group_name","student_name","class_participation",
        "general_behavior","behavior_notes","reading","dictation",
        "term_meanings","conversation","expression","grammar","notes",
    ],
    "payment_log": [
        "student_name","personal_id","registration_status","course_amount",
        "inst1","msg1","inst2","msg2","inst3","msg3","inst4","msg4","inst5","msg5",
        "total_paid","total_remaining","payment_status",
    ],
}

# Natural unique key(s) per table used to decide insert-vs-update during
# Excel import. When every key column in an incoming row is non-empty AND
# matches an existing row, UPDATE the non-key columns. Otherwise INSERT.
IMPORT_TABLE_KEYS = {
    "students":       ["personal_id"],
    "student_groups": ["group_name"],
    "attendance":     ["group_name", "attendance_date", "student_name"],
    "taqseet":        ["taqseet_method", "student_name"],
    "evaluations":    ["form_fill_date", "group_name", "student_name"],
    "payment_log":    ["personal_id"],
}

# Label table each data table stores its column types in. Column types come
# from the /settings-configured typed-column system (نص / رقم / تاريخ / ...).
IMPORT_LABEL_TABLES = {
    "students":       "column_labels",
    "student_groups": "group_col_labels",
    "attendance":     "att_col_labels",
    "evaluations":    "eval_col_labels",
    "payment_log":    "paylog_col_labels",
    "taqseet":        "taqseet_col_labels",
}

# Canonical attendance status values. Any incoming variant folds to the
# canonical form so the dashboard, per-student stats, and reporting all
# count the row correctly regardless of how the Excel spelt it.
STATUS_REMAP = {
    "غياب":  "غائب",
    "تأخير": "متأخر",
    "حضور":  "حاضر",
    # Also fold common whitespace/casing variants users paste in.
    "absent":  "غائب",
    "late":    "متأخر",
    "present": "حاضر",
}


def _import_fold_whitespace(s):
    """Collapse leading/trailing + internal whitespace runs to a single
    space. Applied to every incoming text value so Excel cells that got an
    extra tab or NBSP don't break downstream equality checks."""
    if s is None:
        return ""
    s = str(s).replace(" ", " ").replace("\t", " ")
    if not s.strip():
        return ""
    return " ".join(s.split())


# Field names known to hold dates. Any value written to one of these is
# coerced to ISO YYYY-MM-DD on import so the attendance page (and anything
# else joining on date) always compares like-for-like.
DATE_FIELD_NAMES = {
    "attendance_date", "start_date", "form_fill_date",
    "date1", "date2", "date3", "date4", "date5", "date6",
    "date7", "date8", "date9", "date10", "date11", "date12",
}


def _import_normalize_value(table, field, value):
    s = _import_fold_whitespace(value)
    if not s:
        return s
    if field in DATE_FIELD_NAMES:
        iso = _att_normalize_date(s)
        if iso:
            s = iso
    if table == "attendance" and field == "status":
        # Fold canonical Arabic status variants (exact match or lowercased).
        s_key = s.strip()
        if s_key in STATUS_REMAP:
            return STATUS_REMAP[s_key]
        low = s_key.lower()
        if low in STATUS_REMAP:
            return STATUS_REMAP[low]
    return s


def _import_get_col_types(table):
    """Return {col_key: col_type} from the label table that tracks the data
    table's typed columns. Empty dict on any error — validation is best-effort
    and never blocks an import when the schema is absent."""
    lbl = IMPORT_LABEL_TABLES.get(table)
    if not lbl:
        return {}
    try:
        db = get_db()
        rows = db.execute(
            "SELECT col_key, col_type FROM " + lbl
        ).fetchall()
        out = {}
        for r in rows:
            k = r[0] if hasattr(r, "__getitem__") else None
            t = r[1] if hasattr(r, "__getitem__") else None
            if k:
                out[k] = (t or "").strip()
        return out
    except Exception:
        return {}


def _import_coerce_by_type(value, col_type):
    """Return (ok, coerced_value, reason). Best-effort coercion based on the
    typed-column setting. Unknown/empty types always pass through unchanged."""
    if value is None or value == "":
        return True, value, ""
    t = (col_type or "").strip()
    if not t or t == "نص":
        return True, value, ""
    if t == "رقم":
        s = str(value).strip().replace(",", ".")
        # Accept "1.5", "1", "-2.3". Reject anything else.
        try:
            float(s)
            return True, s, ""
        except Exception:
            return False, value, "ليس رقمًا"
    if t == "تاريخ":
        import re as _re_local
        s = str(value).strip()
        if _re_local.match(r"^\d{4}-\d{1,2}-\d{1,2}", s):
            return True, s[:10], ""
        m = _re_local.match(r"^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$", s)
        if m:
            d, mo, y = m.group(1), m.group(2), m.group(3)
            return True, "%s-%s-%s" % (y, mo.zfill(2), d.zfill(2)), ""
        return False, value, "تنسيق تاريخ غير صالح"
    if t == "نعم/لا":
        s = str(value).strip().lower()
        if s in ("1", "true", "yes", "y", "نعم"):
            return True, "1", ""
        if s in ("0", "false", "no", "n", "لا", ""):
            return True, "0", ""
        return False, value, "قيمة منطقية غير صالحة"
    # قائمة منسدلة and تقييم etc. — accept as text.
    return True, value, ""


IMPORT_TABLE_SQL = {
    "students": "INSERT INTO students",
    "student_groups": "INSERT INTO student_groups",
    "attendance": "INSERT INTO attendance",
    "taqseet": "INSERT INTO taqseet",
    "evaluations": "INSERT INTO evaluations",
    "payment_log": "INSERT INTO payment_log",
}

@app.route('/api/import', methods=['POST'])
@login_required
def api_import():
    """Generic Excel-import endpoint used by every table on the database page.

    Behaviour:
      - Every incoming text value is whitespace-folded.
      - Attendance status values are mapped to canonical Arabic
        (غياب→غائب, تأخير→متأخر, حضور→حاضر) so downstream matching works.
      - If all natural-key columns (IMPORT_TABLE_KEYS[table]) are non-empty
        and an existing row has the same key tuple, the row is UPDATED
        (non-key columns only, and only where the incoming value is non-empty
        so we don't overwrite existing data with blanks).
      - Otherwise the row is INSERTED.
      - Typed columns (نص/رقم/تاريخ/نعم-لا) are validated; on failure the
        row is skipped with a reason added to skip_reasons.

    Response includes: inserted, updated, skipped, errors, received,
    skip_reasons (up to 20), last_error, fields_used.
    """
    d = request.get_json() or {}
    table = d.get('table', '')
    rows = d.get('rows', [])
    auto_create = bool(d.get('auto_create', False))
    column_labels = d.get('column_labels') or {}
    fields = IMPORT_TABLE_FIELDS.get(table)
    if not fields:
        return jsonify({"ok": False, "error": "unknown table"}), 400
    db = get_db()
    live_cols = {r[1] for r in db.execute("PRAGMA table_info(" + table + ")").fetchall()}

    if auto_create:
        import re as _re_local
        safe_rx = _re_local.compile(r'^[A-Za-z_][A-Za-z0-9_]{0,63}$')
        incoming = set()
        for r in rows:
            if isinstance(r, dict):
                incoming.update(r.keys())
        candidates = set(fields) | {k for k in incoming if safe_rx.match(k or '')}
        missing = candidates - live_cols - {"id"}
        for col in sorted(missing):
            try:
                db.execute("ALTER TABLE " + table + " ADD COLUMN " + col + " TEXT")
                live_cols.add(col)
            except Exception:
                pass
        db.commit()
        fields = [c for c in candidates if c in live_cols]
        if table == 'taqseet' and isinstance(column_labels, dict) and column_labels:
            try:
                for key, label in column_labels.items():
                    if not key or not isinstance(key, str) or not safe_rx.match(key):
                        continue
                    lbl = str(label or '').strip()
                    if not lbl:
                        continue
                    db.execute(
                        "INSERT INTO taqseet_col_labels(col_key,col_label) VALUES(?,?) "
                        "ON CONFLICT(col_key) DO UPDATE SET col_label=EXCLUDED.col_label",
                        (key, lbl),
                    )
                db.commit()
            except Exception:
                pass
    else:
        fields = [f for f in fields if f in live_cols]

    if not fields:
        return jsonify({"ok": False, "error": "no matching columns in table " + table}), 400

    key_cols = [k for k in IMPORT_TABLE_KEYS.get(table, []) if k in live_cols and _is_safe_ident(k)]
    col_types = _import_get_col_types(table)

    inserted = 0
    updated  = 0
    skipped  = 0
    errors   = 0
    skip_reasons = []   # up to 20 entries
    last_error = ""

    cols = ",".join(fields)
    placeholders = ",".join(["?"] * len(fields))
    sql_insert = IMPORT_TABLE_SQL[table] + " (" + cols + ") VALUES (" + placeholders + ")"

    def _remember_skip(idx, reason):
        if len(skip_reasons) < 20:
            skip_reasons.append({"row": idx + 1, "reason": reason})

    for idx, r in enumerate(rows):
        if not isinstance(r, dict):
            skipped += 1
            _remember_skip(idx, "row is not an object")
            continue
        norm = {}
        for f in fields:
            norm[f] = _import_normalize_value(table, f, r.get(f))
        has_any = any(v for v in norm.values())
        if not has_any:
            skipped += 1
            _remember_skip(idx, "empty row")
            continue

        # Typed-column validation.
        bad_type_reason = ""
        for f in fields:
            t = col_types.get(f, "")
            if not t:
                continue
            ok, coerced, why = _import_coerce_by_type(norm[f], t)
            if not ok:
                bad_type_reason = f + ": " + why
                break
            norm[f] = coerced
        if bad_type_reason:
            skipped += 1
            _remember_skip(idx, bad_type_reason)
            continue

        # Upsert: if every key column is non-empty AND a row with that tuple
        # exists, UPDATE non-key columns; else INSERT.
        existing_id = None
        if key_cols and all((norm.get(k) or "").strip() for k in key_cols):
            where = " AND ".join([k + "=?" for k in key_cols])
            try:
                row = db.execute(
                    "SELECT id FROM " + table + " WHERE " + where,
                    tuple(norm[k] for k in key_cols),
                ).fetchone()
                if row:
                    existing_id = row[0] if not hasattr(row, "keys") else row["id"]
            except Exception:
                existing_id = None

        try:
            if existing_id:
                set_cols = [f for f in fields if f not in key_cols and (norm.get(f) or "").strip()]
                if not set_cols:
                    skipped += 1
                    _remember_skip(idx, "duplicate key with no new data")
                    continue
                sql_up = ("UPDATE " + table + " SET " +
                          ",".join([c + "=?" for c in set_cols]) +
                          " WHERE id=?")
                db.execute(sql_up, tuple([norm[c] for c in set_cols] + [existing_id]))
                updated += 1
            else:
                values = [norm.get(f, "") for f in fields]
                # Empty personal_id -> NULL so UNIQUE(personal_id) treats
                # blank-ID rows as distinct. Only matters for students here.
                for i2, f in enumerate(fields):
                    if f == "personal_id" and not (values[i2] or "").strip():
                        values[i2] = None
                cur = db.execute(sql_insert, tuple(values))
                if cur.rowcount > 0:
                    inserted += 1
                else:
                    skipped += 1
                    _remember_skip(idx, "insert suppressed (UNIQUE?)")
        except Exception as ex:
            errors += 1
            last_error = str(ex)
            _remember_skip(idx, "error: " + last_error[:80])

    db.commit()
    return jsonify({
        "ok": True,
        "table": table,
        "inserted": inserted,
        "updated":  updated,
        "skipped":  skipped,
        "errors":   errors,
        "received": len(rows),
        "skip_reasons": skip_reasons,
        "last_error": last_error,
        "fields_used": fields,
        # Backwards-compat aliases (existing front-end reads d.imported/d.ignored).
        "imported": inserted,
        "ignored":  skipped,
    })

@app.route('/api/attendance/sessions', methods=['GET'])
@login_required
def api_attendance_sessions():
    db = get_db()
    rows = db.execute(
        "SELECT a.group_name, COUNT(DISTINCT a.attendance_date) AS sessions, "
        "COALESCE((SELECT SUM(duration_minutes) FROM session_durations sd "
        "          WHERE sd.group_name = a.group_name), 0) AS total_minutes "
        "FROM attendance a "
        "WHERE a.group_name IS NOT NULL AND a.group_name != '' "
        "AND a.attendance_date IS NOT NULL AND a.attendance_date != '' "
        "GROUP BY a.group_name ORDER BY a.group_name"
    ).fetchall()
    return jsonify([
        {"group_name": r[0], "sessions": r[1], "total_minutes": int(r[2] or 0)}
        for r in rows
    ])

@app.route('/api/attendance/groups', methods=['GET'])
@login_required
def api_attendance_groups():
    # Configurable via /settings → attendance.groups_table / groups_column.
    tbl = get_setting('attendance', 'groups_table', 'attendance')
    col = get_setting('attendance', 'groups_column', 'group_name')
    if not _is_safe_ident(tbl) or not _is_safe_ident(col):
        tbl, col = 'attendance', 'group_name'
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT " + col + " FROM " + tbl + " "
        "WHERE " + col + " IS NOT NULL AND " + col + " != '' "
        "ORDER BY " + col
    ).fetchall()
    return jsonify([r[0] for r in rows])

@app.route('/api/attendance/group-dates', methods=['GET'])
@login_required
def api_attendance_group_dates():
    group = request.args.get('group', '')
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT a.attendance_date, "
        "COALESCE(sd.duration_minutes, 0) AS duration, "
        "COALESCE(sd.session_type, '') AS session_type "
        "FROM attendance a "
        "LEFT JOIN session_durations sd "
        "  ON sd.group_name = a.group_name AND sd.session_date = a.attendance_date "
        "WHERE a.group_name = ? AND a.attendance_date IS NOT NULL AND a.attendance_date != '' "
        "ORDER BY a.attendance_date",
        (group,)
    ).fetchall()
    return jsonify([
        {"session_date": r[0], "duration_minutes": int(r[1] or 0), "session_type": r[2] or ""}
        for r in rows
    ])

@app.route('/api/session-durations', methods=['POST'])
@login_required
def api_session_durations_save():
    d = request.get_json() or {}
    group = d.get('group_name', '')
    items = d.get('items', [])
    if not group:
        return jsonify({"ok": False, "error": "group_name required"}), 400
    db = get_db()
    try:
        for it in items:
            date = it.get('session_date', '')
            mins = int(it.get('duration_minutes') or 0)
            stype = (it.get('session_type') or '').strip()
            if not date:
                continue
            db.execute(
                "INSERT INTO session_durations(group_name, session_date, duration_minutes, session_type) "
                "VALUES(?,?,?,?) "
                "ON CONFLICT(group_name, session_date) DO UPDATE SET "
                "  duration_minutes=excluded.duration_minutes, "
                "  session_type=excluded.session_type",
                (group, date, mins, stype)
            )
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route('/api/session-summary', methods=['GET'])
@login_required
def api_session_summary():
    db = get_db()
    HUDOOR = '\u062D\u0636\u0648\u0631'
    ONLINE = '\u0623\u0648\u0646\u0644\u0627\u064A\u0646'

    groups = db.execute(
        "SELECT group_name, COALESCE(total_required_hours,'') "
        "FROM student_groups "
        "WHERE group_name IS NOT NULL AND group_name != '' "
        "ORDER BY group_name"
    ).fetchall()

    known = set()
    result = []
    for g in groups:
        name = g[0]
        try:
            req_hours = float(str(g[1]).strip()) if str(g[1]).strip() else 0.0
        except Exception:
            req_hours = 0.0
        totals = db.execute(
            "SELECT COALESCE(session_type,'') AS st, COALESCE(SUM(duration_minutes),0) "
            "FROM session_durations WHERE group_name=? GROUP BY st",
            (name,)
        ).fetchall()
        pres_m = 0
        onl_m = 0
        other_m = 0
        for t in totals:
            st = (t[0] or '').strip()
            mins = int(t[1] or 0)
            if st == HUDOOR:
                pres_m += mins
            elif st == ONLINE:
                onl_m += mins
            else:
                other_m += mins
        total_m = pres_m + onl_m + other_m
        total_h = round(total_m / 60.0, 2)
        pres_h = round(pres_m / 60.0, 2)
        onl_h = round(onl_m / 60.0, 2)
        remaining_h = round(req_hours - total_h, 2)
        if req_hours > 0:
            pct = max(0.0, min(100.0, round((total_h / req_hours) * 100.0, 1)))
        else:
            pct = 0.0
        result.append({
            "group_name": name,
            "required_hours": req_hours,
            "present_hours": pres_h,
            "online_hours": onl_h,
            "total_hours": total_h,
            "remaining_hours": remaining_h,
            "completion_pct": pct,
        })
        known.add(name)

    extra = db.execute(
        "SELECT DISTINCT group_name FROM session_durations "
        "WHERE group_name IS NOT NULL AND group_name != ''"
    ).fetchall()
    for e in extra:
        name = e[0]
        if name in known:
            continue
        totals = db.execute(
            "SELECT COALESCE(session_type,'') AS st, COALESCE(SUM(duration_minutes),0) "
            "FROM session_durations WHERE group_name=? GROUP BY st",
            (name,)
        ).fetchall()
        pres_m = 0
        onl_m = 0
        other_m = 0
        for t in totals:
            st = (t[0] or '').strip()
            mins = int(t[1] or 0)
            if st == HUDOOR:
                pres_m += mins
            elif st == ONLINE:
                onl_m += mins
            else:
                other_m += mins
        total_m = pres_m + onl_m + other_m
        result.append({
            "group_name": name,
            "required_hours": 0.0,
            "present_hours": round(pres_m / 60.0, 2),
            "online_hours": round(onl_m / 60.0, 2),
            "total_hours": round(total_m / 60.0, 2),
            "remaining_hours": round(-total_m / 60.0, 2),
            "completion_pct": 0.0,
        })

    result.sort(key=lambda r: r["group_name"] or "")
    return jsonify(result)

@app.route('/api/payments/group')
@login_required
def api_payments_group():
    db = get_db()
    group = request.args.get('group','')
    students = db.execute("SELECT id,student_name,installment_type FROM students WHERE group_name_student=? ORDER BY student_name", (group,)).fetchall()
    result = []
    for s in students:
        row = {"id": s[0], "name": s[1]}
        tq = db.execute("SELECT inst1,inst2,inst3,inst4,inst5,inst6,inst7,inst8,inst9,inst10,inst11,inst12 FROM taqseet WHERE taqseet_method=?", (str(s[2] or ''),)).fetchone()
        if tq:
            for n in range(1,13):
                row["tq_inst"+str(n)] = tq[n-1] if tq[n-1] else ''
        payments = db.execute("SELECT inst_num,inst_type,price,paid FROM student_payments WHERE student_id=?", (s[0],)).fetchall()
        for p in payments:
            row["inst_"+str(p[0])] = {"inst_type": p[1], "price": p[2], "paid": p[3]}
        result.append(row)
    return jsonify(result)

@app.route('/api/message-templates', methods=['GET'])
@login_required
def api_message_templates_list():
    db = get_db()
    rows = db.execute(
        "SELECT id, name, category, content, created_at FROM message_templates ORDER BY category, name"
    ).fetchall()
    return jsonify({"templates": [dict(r) for r in rows]})

@app.route('/api/message-templates', methods=['POST'])
@login_required
def api_message_templates_add():
    d = request.get_json() or {}
    name = (d.get('name') or '').strip()
    category = (d.get('category') or '').strip()
    content = d.get('content') or ''
    if not name or not content:
        return jsonify({"ok": False, "error": "missing name or content"}), 400
    db = get_db()
    db.execute(
        "INSERT INTO message_templates(name, category, content) VALUES(?,?,?)",
        (name, category, content)
    )
    db.commit()
    return jsonify({"ok": True})

@app.route('/api/message-templates/<int:tid>', methods=['DELETE'])
@login_required
def api_message_templates_delete(tid):
    db = get_db()
    db.execute("DELETE FROM message_templates WHERE id=?", (tid,))
    db.commit()
    return jsonify({"ok": True})

@app.route('/api/message-log', methods=['GET'])
@login_required
def api_message_log_list():
    db = get_db()
    rows = db.execute(
        "SELECT id, student_name, student_whatsapp, template_name, sent_at FROM message_log ORDER BY sent_at DESC LIMIT 500"
    ).fetchall()
    return jsonify({"log": [dict(r) for r in rows]})

@app.route('/api/message-log', methods=['POST'])
@login_required
def api_message_log_add():
    d = request.get_json() or {}
    db = get_db()
    db.execute(
        "INSERT INTO message_log(student_name, student_whatsapp, template_name) VALUES(?,?,?)",
        (d.get('student_name') or '', d.get('student_whatsapp') or '', d.get('template_name') or '')
    )
    db.commit()
    # Return the new row id so callers (e.g. undo toasts) can remove exactly
    # the log entry they created if the user changes their mind.
    new_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return jsonify({"ok": True, "id": new_id})

@app.route('/api/message-log/<int:lid>', methods=['DELETE'])
@login_required
def api_message_log_delete(lid):
    db = get_db()
    try:
        db.execute("DELETE FROM message_log WHERE id=?", (lid,))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route('/api/message-reminders', methods=['GET'])
@login_required
def api_message_reminders_list():
    db = get_db()
    rows = db.execute(
        "SELECT id, name, day_of_week, time_of_day, template_id, group_name, enabled FROM message_reminders ORDER BY day_of_week, time_of_day"
    ).fetchall()
    return jsonify({"reminders": [dict(r) for r in rows]})

@app.route('/api/message-reminders', methods=['POST'])
@login_required
def api_message_reminders_add():
    d = request.get_json() or {}
    name = (d.get('name') or '').strip()
    day = d.get('day_of_week')
    tod = (d.get('time_of_day') or '').strip()
    template_id = d.get('template_id')
    group_name = (d.get('group_name') or '').strip()
    if not name or day is None or not tod or not template_id or not group_name:
        return jsonify({"ok": False, "error": "missing fields"}), 400
    try:
        day_i = int(day)
        template_i = int(template_id)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "bad types"}), 400
    db = get_db()
    db.execute(
        "INSERT INTO message_reminders(name, day_of_week, time_of_day, template_id, group_name) VALUES(?,?,?,?,?)",
        (name, day_i, tod, template_i, group_name)
    )
    db.commit()
    return jsonify({"ok": True})

@app.route('/api/message-reminders/<int:rid>', methods=['DELETE'])
@login_required
def api_message_reminders_delete(rid):
    db = get_db()
    db.execute("DELETE FROM message_reminders WHERE id=?", (rid,))
    db.commit()
    return jsonify({"ok": True})


@app.route('/settings')
@login_required
def settings_page():
    return SETTINGS_HTML


MX_HELPERS_JS = r'''/* mx-helpers.js - Mindex shared UI helpers */
(function(){
  var css = [
    /* ================================================================
     * MOBILE RESPONSIVENESS
     * Applied globally so every page/modal collapses gracefully on
     * phones. Uses !important to override the inline styles scattered
     * across HOME_HTML / DATABASE_HTML / ATTENDANCE_HTML without having
     * to touch each one. 768px = tablet; 480px = phone.
     * ================================================================ */
    '@media (max-width:768px){',
      'html,body{overflow-x:hidden;}',
      'body{padding:10px !important;}',

      /* Topbar / navbar: wrap links under the title, shrink padding */
      '.topbar,.dh-topbar{padding:10px 14px !important;flex-wrap:wrap !important;gap:8px !important;}',
      '.topbar h1,.dh-topbar-title{font-size:1rem !important;line-height:1.2 !important;flex:1 1 100%;min-width:0;}',
      '.topbar-links{gap:6px !important;flex-wrap:wrap !important;}',
      '.topbar a,.btn-home,.btn-back{padding:10px 12px !important;font-size:12px !important;min-height:40px;display:inline-flex;align-items:center;}',

      /* Dashboard stats + actions — 2-col on tablet */
      '.dh-stats{grid-template-columns:repeat(2,1fr) !important;}',
      '.dh-actions{grid-template-columns:1fr 1fr !important;gap:10px !important;}',
      '.dh-stat-card{padding:12px !important;}',
      '.dh-stat-num{font-size:1.6rem !important;}',
      '.dh-action-card{padding:14px !important;min-height:auto !important;font-size:14px !important;}',
      '.dh-action-title{font-size:14px !important;}',
      '.dh-action-desc{font-size:11px !important;}',

      /* Database page main container */
      '.main{padding:12px 10px !important;}',
      '.page-title{font-size:17px !important;}',
      '.db-nav{padding:8px !important;gap:6px !important;overflow-x:auto;flex-wrap:nowrap !important;}',
      '.db-nav-btn{font-size:12px !important;padding:7px 12px !important;min-height:40px;white-space:nowrap;}',
      '.db-section,.custom-table-section{padding:12px !important;margin-bottom:16px !important;}',
      '.db-section-title{font-size:15px !important;}',

      /* Action bars already wrap via existing rule — tighten buttons */
      '.btn-add,.btn-save,.btn-cancel,.btn-delete-table,.btn-bulk-del,.btn-search,.action-btn{min-height:44px;padding:10px 14px !important;font-size:13px !important;}',
      '.mx-btn-add,.mx-btn-edit,.mx-btn-delete,.mx-btn-import,.mx-btn-freeze,.mx-btn-search{min-height:44px;font-size:13px !important;}',

      /* Tables — horizontal scroll only inside the wrap, compact cells */
      '.table-wrap,.att-table-wrap{max-height:65vh !important;}',
      'table th,table td{padding:8px 6px !important;font-size:12px !important;}',
      '.mx-filter-btn{font-size:11px !important;padding:1px 3px !important;}',
      '.stats{gap:8px !important;flex-wrap:wrap !important;}',
      '.stat-card{min-width:100px !important;padding:10px 14px !important;}',
      '.stat-num{font-size:22px !important;}',

      /* Modals → full-screen on narrow widths */
      '.modal-bg,.confirm-bg,.mx-confirm-bg,.srm-type-bg,.srm-log-bg{align-items:stretch !important;}',
      '.modal,.confirm-box,.mx-confirm-box,.srm-type-box,.srm-log-box{max-width:100% !important;width:100% !important;min-height:auto !important;border-radius:0 !important;margin:0 !important;}',
      '#sr-modal > div,#ss-modal > div,#sd-modal > div,#ss-modal > div > div,#pay-modal > div,.msg-modal > div,.msg-box{max-width:100% !important;width:100% !important;min-height:100vh !important;border-radius:0 !important;margin:0 !important;}',
      '.form-grid,.srm-grid{grid-template-columns:1fr !important;gap:10px !important;}',
      '.srm-totals{grid-template-columns:1fr !important;}',

      /* Form controls — comfortable for touch */
      'input[type=text],input[type=number],input[type=date],input[type=email],input[type=password],input[type=tel],textarea,select{min-height:44px !important;font-size:14px !important;}',
      '.field input,.field select{font-size:14px !important;}',
      '.search-bar{flex-direction:column !important;gap:6px !important;}',
      '.search-bar input{width:100% !important;}',
      '.search-bar button{width:100% !important;}',

      /* Attendance page: stack controls, sticky save footer */
      '.controls-row{flex-direction:column !important;align-items:stretch !important;gap:10px !important;}',
      '.controls-row > *{width:100% !important;}',
      'select.group-select,input.date-input{width:100% !important;min-height:44px !important;}',
      '.att-footer-btns{position:sticky !important;bottom:0 !important;background:#fff !important;padding:12px !important;z-index:50 !important;box-shadow:0 -4px 16px rgba(0,0,0,.12) !important;flex-direction:column !important;gap:8px !important;margin:16px -10px -10px !important;}',
      '.att-footer-btns button,.btn-save-all,.btn-cancel-att{width:100% !important;justify-content:center;}',

      /* ملخص الحصص modal: controls stack, multi-picker full width */
      '#ss-modal > div > div[style*="grid-template-columns"]{grid-template-columns:1fr !important;}',
      '.ss-groups-panel{max-width:calc(100vw - 20px) !important;left:10px !important;right:10px !important;}',

      /* Student search: single-column sections */
      '.srm-card .srm-section{padding:12px 14px !important;}',
      '.srm-actions{flex-direction:column !important;gap:8px !important;}',
      '.srm-actions button{width:100% !important;}',

      /* Payment modal header controls stack */
      '#pay-modal div[style*="display:flex"][style*="flex-wrap"]{gap:10px !important;}',
      '#pay-modal select,#pay-modal input{min-width:0 !important;width:100% !important;}',

      /* Login box */
      '.box{width:95% !important;max-width:95% !important;padding:28px 22px !important;}',

      /* Column filter panel — stay inside viewport */
      '.mx-filter-panel{max-width:calc(100vw - 20px) !important;min-width:0 !important;}',
      '.mx-filter-banner{font-size:12px !important;padding:7px 10px !important;}',
      '.mx-filter-banner .mx-fb-tag{font-size:11px !important;}',

      /* Toast */
      '.mx-toast{max-width:90vw !important;font-size:13px !important;padding:11px 18px !important;}',

      /* Settings two-panel layout collapses to single column on narrow */
      '.workspace{grid-template-columns:1fr !important;gap:10px !important;}',
      '.tabs{padding:6px !important;gap:4px !important;}',
      '.tab{padding:7px 10px !important;font-size:12.5px !important;}',

      /* Touch target spacing inside button groups */
      '.modal-actions{flex-direction:column !important;gap:8px !important;}',
      '.modal-actions button{width:100% !important;}',

      /* Generic Excel/import modal */
      '#genericExcelModal > div,#attendanceExcelModal > div,#freezeModal > div,#universalTableEditModal > div{max-width:100% !important;width:100% !important;min-height:100vh !important;border-radius:0 !important;margin:0 !important;}',
    '}',

    /* ================================================================
     * PHONE (≤480px) — tighter grids, smaller fonts
     * ================================================================ */
    '@media (max-width:480px){',
      '.dh-stats{grid-template-columns:1fr 1fr !important;}',
      '.dh-actions{grid-template-columns:1fr !important;}',
      '.dh-stat-num{font-size:1.4rem !important;}',
      '.dh-stat-label{font-size:12px !important;}',
      '.topbar h1,.dh-topbar-title{font-size:0.92rem !important;}',
      '.topbar a,.btn-home,.btn-back{font-size:11px !important;padding:8px 10px !important;}',
      '.page-title{font-size:15px !important;}',
      '.db-section-title{font-size:14px !important;}',
      'table th,table td{padding:7px 5px !important;font-size:11.5px !important;}',
      '.stat-card{min-width:90px !important;}',
      '.stat-num{font-size:20px !important;}',
      '.stat-label{font-size:10.5px !important;}',
      '.srm-stat-num{font-size:1.1em !important;}',
      '.srm-stat-lbl{font-size:0.72em !important;}',
      /* Column filter panel even narrower */
      '.mx-filter-panel{font-size:12px !important;}',
      '.mx-filter-panel label{font-size:12px !important;}',
    '}',

    /* Global touch-target minimum (applies on all sizes, not just mobile) */
    '@media (pointer:coarse){',
      'button,a.btn-home,a.btn-back,.action-btn,.dh-action-card,.db-nav-btn{min-height:44px;}',
      'input[type=checkbox],input[type=radio]{min-width:18px;min-height:18px;}',
    '}',

    /* Column-filter system (applies to every .table-wrap table) */
    '.mx-filter-btn{background:transparent;border:none;color:inherit;opacity:.55;font-size:10px;cursor:pointer;padding:2px 4px;margin-right:4px;border-radius:4px;vertical-align:middle;transition:opacity .15s ease,background .15s ease;}',
    '.mx-filter-btn:hover{opacity:1;background:rgba(255,255,255,.2);}',
    '.mx-filter-btn.active{opacity:1;color:#fff;background:#2196F3;box-shadow:0 0 0 2px rgba(33,150,243,.35);}',
    /* Column-delete ✕ button — hidden until the header is hovered. */
    '.mx-col-del-btn{background:transparent;border:none;color:#ffb3b3;opacity:0;font-size:12px;font-weight:900;cursor:pointer;padding:2px 6px;margin-right:3px;border-radius:4px;vertical-align:middle;transition:opacity .15s ease,background .15s ease,color .15s ease;line-height:1;}',
    'th:hover .mx-col-del-btn{opacity:1;}',
    '.mx-col-del-btn:hover{background:#e74c3c !important;color:#fff !important;opacity:1 !important;box-shadow:0 0 0 2px rgba(231,76,60,.35);}',
    '@media (pointer:coarse){.mx-col-del-btn{opacity:.65;}}',
    '.mx-filter-panel{position:absolute;z-index:10050;background:#fff;border:1.5px solid #2196F3;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.18);padding:10px;min-width:220px;max-width:320px;max-height:360px;overflow:auto;direction:rtl;font-size:13px;}',
    '.mx-filter-panel h4{font-size:12.5px;font-weight:800;color:#0d47a1;margin-bottom:6px;}',
    '.mx-filter-panel label{display:flex;align-items:center;gap:6px;padding:4px 2px;cursor:pointer;font-weight:600;color:#333;}',
    '.mx-filter-panel input[type=text],.mx-filter-panel input[type=number],.mx-filter-panel input[type=date]{width:100%;padding:6px 10px;border:1.3px solid #90caf9;border-radius:7px;font-size:13px;background:#fafafa;direction:rtl;margin-bottom:6px;}',
    '.mx-filter-panel input:focus{background:#fff;outline:none;border-color:#1976D2;}',
    '.mx-filter-panel .mx-f-clear{margin-top:8px;width:100%;padding:7px;background:#eceff1;color:#455a64;border:none;border-radius:7px;font-weight:700;cursor:pointer;font-size:12.5px;}',
    '.mx-filter-panel .mx-f-clear:hover{background:#cfd8dc;}',
    '.mx-filter-banner{background:linear-gradient(135deg,#e3f2fd,#bbdefb);border:1.5px solid #64b5f6;border-radius:10px;padding:8px 12px;margin:0 0 10px 0;display:none;flex-wrap:wrap;gap:8px;align-items:center;font-size:13px;}',
    '.mx-filter-banner.show{display:flex;}',
    '.mx-filter-banner .mx-fb-count{font-weight:800;color:#0d47a1;margin-left:auto;}',
    '.mx-filter-banner .mx-fb-clear-all{background:#e53935;color:#fff;border:none;padding:5px 12px;border-radius:999px;font-weight:700;cursor:pointer;font-size:12px;}',
    '.mx-filter-banner .mx-fb-tag{background:#fff;border:1px solid #90caf9;color:#0d47a1;padding:3px 10px;border-radius:999px;font-weight:700;font-size:12px;display:inline-flex;align-items:center;gap:5px;}',
    '.mx-filter-banner .mx-fb-tag .mx-fb-x{cursor:pointer;color:#c62828;font-weight:900;}',
    '.mx-row-count{font-size:12px;color:#555;font-weight:700;margin-bottom:6px;}',

    /* P2: button bar wrap */
    '.db-section > div[style*="display:flex"],.custom-table-section > div[style*="display:flex"],.db-section > div[style*="display: flex"],.custom-table-section > div[style*="display: flex"],.db-nav{flex-wrap:wrap !important;row-gap:10px !important;}',
    '.db-section > div[style*="display:flex"] > *,.custom-table-section > div[style*="display:flex"] > *{flex-shrink:0;}',

    /* P6: standardized button classes */
    '.mx-btn-add,button.mx-btn-add{background:#27ae60 !important;background-color:#27ae60 !important;color:#fff !important;border:none !important;}',
    '.mx-btn-add:hover{background:#229954 !important;}',
    '.mx-btn-edit,button.mx-btn-edit{background:#e67e22 !important;background-color:#e67e22 !important;color:#fff !important;border:none !important;}',
    '.mx-btn-edit:hover{background:#d35400 !important;}',
    '.mx-btn-delete,button.mx-btn-delete{background:#e74c3c !important;background-color:#e74c3c !important;color:#fff !important;border:none !important;}',
    '.mx-btn-delete:hover{background:#c0392b !important;}',
    '.mx-btn-import,button.mx-btn-import{background:#2980b9 !important;background-color:#2980b9 !important;color:#fff !important;border:none !important;}',
    '.mx-btn-import:hover{background:#21618c !important;}',
    '.mx-btn-freeze,button.mx-btn-freeze{background:#8e44ad !important;background-color:#8e44ad !important;color:#fff !important;border:none !important;}',
    '.mx-btn-freeze:hover{background:#7d3c98 !important;}',
    '.mx-btn-search,button.mx-btn-search{background:#2c3e50 !important;background-color:#2c3e50 !important;color:#fff !important;border:none !important;}',
    '.mx-btn-search:hover{background:#1b2631 !important;}',

    /* P4: scroll UX */
    '.table-wrap{overflow-x:auto;overflow-y:auto;max-height:75vh;scrollbar-width:thin;scrollbar-color:#c5b3e6 #f5f3ff;background:linear-gradient(to left,#fff,#fff) 0 0/20px 100% no-repeat local,linear-gradient(to left,#fff,#fff) 100% 0/20px 100% no-repeat local,linear-gradient(to right,rgba(107,63,160,.25),rgba(107,63,160,0)) 0 0/14px 100% no-repeat scroll,linear-gradient(to left,rgba(107,63,160,.25),rgba(107,63,160,0)) 100% 0/14px 100% no-repeat scroll,#fff;}',
    '.table-wrap::-webkit-scrollbar{height:12px;width:10px;}',
    '.table-wrap::-webkit-scrollbar-track{background:#f5f3ff;border-radius:6px;}',
    '.table-wrap::-webkit-scrollbar-thumb{background:#c5b3e6;border-radius:6px;}',
    '.table-wrap::-webkit-scrollbar-thumb:hover{background:#9575CD;}',
    '.table-wrap thead{position:sticky;top:0;z-index:5;}',
    '.table-wrap thead tr{box-shadow:0 2px 4px rgba(107,63,160,.15);}',
    '.mx-col-count{display:inline-block;background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;padding:4px 12px;border-radius:999px;font-size:12px;font-weight:700;margin:0 0 8px 0;}',

    /* P3: toast + confirm */
    '.mx-toast{position:fixed;bottom:28px;left:50%;transform:translateX(-50%) translateY(30px);padding:13px 28px;border-radius:12px;font-size:14px;font-weight:700;box-shadow:0 6px 24px rgba(0,0,0,.2);color:#fff;z-index:999999;opacity:0;pointer-events:none;transition:opacity .25s ease,transform .25s ease;max-width:90vw;text-align:center;}',
    '.mx-toast.show{opacity:1;transform:translateX(-50%) translateY(0);pointer-events:auto;}',
    '.mx-toast-success{background:#27ae60;}',
    '.mx-toast-error{background:#e74c3c;}',
    '.mx-toast-info{background:#2c3e50;}',
    '.mx-confirm-bg{position:fixed;inset:0;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;z-index:99998;direction:rtl;}',
    '.mx-confirm-bg.open{display:flex;}',
    '.mx-confirm-box{background:#fff;border-radius:16px;padding:30px 34px;max-width:420px;width:92%;box-shadow:0 16px 48px rgba(0,0,0,.3);text-align:center;}',
    '.mx-confirm-icon{font-size:54px;margin-bottom:12px;}',
    '.mx-confirm-title{font-size:20px;font-weight:800;color:#c62828;margin-bottom:10px;}',
    '.mx-confirm-msg{color:#555;margin-bottom:22px;font-size:14.5px;line-height:1.5;}',
    '.mx-confirm-actions{display:flex;gap:10px;justify-content:center;}',
    '.mx-confirm-yes{background:#e74c3c;color:#fff;border:none;padding:11px 26px;border-radius:10px;font-size:14px;font-weight:800;cursor:pointer;}',
    '.mx-confirm-yes:hover{background:#c0392b;}',
    '.mx-confirm-no{background:#ecf0f1;color:#2c3e50;border:none;padding:11px 22px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;}',
    '.mx-confirm-no:hover{background:#d0d7da;}',

    /* P7: search clear */
    '.mx-search-clear{background:transparent;color:#999;border:none;font-size:18px;padding:0 10px;cursor:pointer;display:none;align-items:center;}',
    '.mx-search-clear:hover{color:#e74c3c;}',
    '.mx-search-clear.show{display:inline-flex;}',
    '.mx-no-results td{text-align:center !important;padding:28px !important;color:#999 !important;font-weight:700 !important;font-size:14px !important;}',

    /* P5: attendance instruction card */
    '#attInstrCard{background:linear-gradient(135deg,#E0F7FA,#B2EBF2);border:2px dashed #00897B;border-radius:14px;padding:20px 24px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,137,123,.1);}',
    '#attInstrCard .att-intro-title{font-size:18px;font-weight:800;color:#00695C;margin-bottom:14px;display:flex;align-items:center;gap:8px;}',
    '#attInstrCard ol{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px;}',
    '#attInstrCard li{padding:8px 12px;font-size:14.5px;color:#004D40;font-weight:600;background:rgba(255,255,255,.6);border-radius:10px;display:flex;align-items:center;gap:10px;}',
    ''
  ].join('');
  var st = document.createElement('style');
  st.textContent = css;
  (document.head || document.documentElement).appendChild(st);

  /* mxToast */
  var toastEl=null, toastTimer=null;
  function getToastEl(){
    if (!toastEl){
      toastEl = document.createElement('div');
      toastEl.className = 'mx-toast';
      toastEl.id = 'mx-toast';
      document.body.appendChild(toastEl);
    }
    return toastEl;
  }
  window.mxToast = function(msg, kind){
    kind = kind || 'success';
    var prefix = kind === 'error' ? '❌ ' : (kind === 'info' ? 'ℹ️ ' : '✅ ');
    var el = getToastEl();
    el.textContent = prefix + String(msg == null ? '' : msg);
    el.className = 'mx-toast mx-toast-' + kind + ' show';
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(function(){ el.className = 'mx-toast mx-toast-' + kind; }, 3000);
  };

  /* mxConfirm */
  var confirmEl=null;
  function buildConfirm(){
    confirmEl = document.createElement('div');
    confirmEl.className = 'mx-confirm-bg';
    confirmEl.innerHTML =
      '<div class="mx-confirm-box">' +
        '<div class="mx-confirm-icon">⚠️</div>' +
        '<h3 class="mx-confirm-title">هل أنت متأكد من الحذف؟</h3>' +
        '<p class="mx-confirm-msg">لا يمكن التراجع عن هذا الإجراء</p>' +
        '<div class="mx-confirm-actions">' +
          '<button class="mx-confirm-yes" type="button">نعم، احذف</button>' +
          '<button class="mx-confirm-no"  type="button">إلغاء</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(confirmEl);
    return confirmEl;
  }
  window.mxConfirm = function(opts, onYes, onNo){
    if (typeof opts === 'string') opts = { title: opts };
    opts = opts || {};
    var el = confirmEl || buildConfirm();
    el.querySelector('.mx-confirm-title').textContent = opts.title || 'هل أنت متأكد من الحذف؟';
    el.querySelector('.mx-confirm-msg').textContent  = opts.message || 'لا يمكن التراجع عن هذا الإجراء';
    el.querySelector('.mx-confirm-yes').textContent  = opts.yesText || 'نعم، احذف';
    el.querySelector('.mx-confirm-no').textContent   = opts.noText  || 'إلغاء';
    el.classList.add('open');
    var yes = el.querySelector('.mx-confirm-yes');
    var no  = el.querySelector('.mx-confirm-no');
    function cleanup(){ el.classList.remove('open'); yes.onclick = null; no.onclick = null; }
    yes.onclick = function(){ cleanup(); if (typeof onYes === 'function') onYes(); };
    no.onclick  = function(){ cleanup(); if (typeof onNo  === 'function') onNo();  };
  };

  /* Bridge existing showToast to mxToast (color hint -> kind) */
  window.showToast = function(msg, bg){
    var kind = 'success';
    if (typeof bg === 'string'){
      var low = bg.toLowerCase();
      if (low.indexOf('e53') >= 0 || low.indexOf('c62') >= 0 || low.indexOf('e74') >= 0 || low.indexOf('error') >= 0 || low.indexOf('f44') >= 0) kind = 'error';
      else if (low === '#888' || low.indexOf('888') >= 0 || low.indexOf('info') >= 0 || low.indexOf('777') >= 0) kind = 'info';
    }
    window.mxToast(msg, kind);
  };

  /* Button classifier (P6) */
  var RULES = [
    { kw: 'حذف',            cls: 'mx-btn-delete' },
    { kw: 'Excel',                         cls: 'mx-btn-import' },
    { kw: 'excel',                         cls: 'mx-btn-import' },
    { kw: 'استيراد', cls: 'mx-btn-import' },
    { kw: 'تجميد', cls: 'mx-btn-freeze' },
    { kw: 'بحث',             cls: 'mx-btn-search' },
    { kw: 'تعديل', cls: 'mx-btn-edit' },
    { kw: 'إضافة', cls: 'mx-btn-add' },
    { kw: 'اضافة', cls: 'mx-btn-add' },
    { kw: 'حفظ',             cls: 'mx-btn-add' }
  ];
  function classifyButton(el){
    if (!el || el.hasAttribute('data-mxb')) return;
    if (el.classList && (el.classList.contains('db-nav-btn') || el.classList.contains('btn-tab') || el.classList.contains('bulk-cb'))) return;
    var text = (el.textContent || '').trim();
    if (!text) return;
    for (var i=0; i<RULES.length; i++){
      if (text.indexOf(RULES[i].kw) >= 0){
        el.classList.add(RULES[i].cls);
        el.setAttribute('data-mxb', '1');
        return;
      }
    }
  }
  function scanButtons(){
    document.querySelectorAll('button, a.btn-save, a.btn-cancel, a.btn-home, a.btn-back').forEach(classifyButton);
  }

  /* Column count badges (P4) */
  function addColumnCounts(){
    document.querySelectorAll('.table-wrap').forEach(function(wrap){
      if (wrap.hasAttribute('data-mxcc')) return;
      var table = wrap.querySelector('table');
      if (!table) return;
      var theadRow = table.querySelector('thead tr');
      if (!theadRow) return;
      wrap.setAttribute('data-mxcc', '1');
      var badge = document.createElement('div');
      badge.className = 'mx-col-count';
      badge.textContent = 'عدد الأعمدة: ' + theadRow.children.length;
      wrap.parentNode.insertBefore(badge, wrap);
    });
  }

  /* Universal search (P7) */
  function mxFilterTable(tbody, q){
    q = (q || '').trim().toLowerCase();
    var rows = tbody.querySelectorAll('tr');
    var shown = 0;
    for (var i=0; i<rows.length; i++){
      var tr = rows[i];
      if (tr.classList.contains('mx-no-results')) continue;
      var text = (tr.textContent || '').toLowerCase();
      var match = !q || text.indexOf(q) >= 0;
      tr.style.display = match ? '' : 'none';
      if (match) shown++;
    }
    var empty = tbody.querySelector('tr.mx-no-results');
    if (q && shown === 0){
      if (!empty){
        empty = document.createElement('tr');
        empty.className = 'mx-no-results';
        var cols = (tbody.parentNode.querySelector('thead tr') || {}).children || [];
        var td = document.createElement('td');
        td.colSpan = cols.length || 20;
        td.textContent = 'لا توجد نتائج';
        empty.appendChild(td);
        tbody.appendChild(empty);
      } else {
        empty.style.display = '';
      }
    } else if (empty){
      empty.style.display = 'none';
    }
  }
  window.mxFilterTable = mxFilterTable;

  function wireSearchFor(input){
    if (!input || input.hasAttribute('data-mxs')) return;
    var section = input.closest('.db-section, .custom-table-section');
    var wrap = section ? section.querySelector('.table-wrap') : null;
    if (!wrap){
      /* Attendance page uses .att-table-wrap */
      wrap = (section || document).querySelector('.table-wrap, .att-table-wrap');
    }
    if (!wrap) return;
    var tbody = wrap.querySelector('tbody');
    if (!tbody) return;
    input.setAttribute('data-mxs', '1');
    input.addEventListener('input', function(){
      setTimeout(function(){ mxFilterTable(tbody, input.value); }, 0);
    });
    var wrapSearch = input.parentNode;
    if (wrapSearch && !wrapSearch.querySelector('.mx-search-clear')){
      var clearBtn = document.createElement('button');
      clearBtn.type = 'button';
      clearBtn.className = 'mx-search-clear';
      clearBtn.innerHTML = '✕';
      clearBtn.title = 'مسح';
      clearBtn.onclick = function(){
        input.value = '';
        try { input.dispatchEvent(new Event('input', { bubbles:true })); } catch(e){}
        mxFilterTable(tbody, '');
        clearBtn.classList.remove('show');
        input.focus();
      };
      input.addEventListener('input', function(){
        if (input.value) clearBtn.classList.add('show');
        else clearBtn.classList.remove('show');
      });
      wrapSearch.insertBefore(clearBtn, input.nextSibling);
    }
  }
  function wireTableSearches(){
    document.querySelectorAll('.search-bar input, input[id$="SearchInput"], input#searchInput').forEach(wireSearchFor);
  }

  /* P5: attendance instruction card show/hide */
  function wireAttendanceIntro(){
    var card = document.getElementById('attInstrCard');
    var sel  = document.getElementById('groupSelect');
    if (!card || !sel || sel.hasAttribute('data-mxa')) return;
    sel.setAttribute('data-mxa', '1');
    function upd(){ card.style.display = sel.value ? 'none' : ''; }
    sel.addEventListener('change', upd);
    upd();
  }

  /* ========================================================================
   * Column filter system — adds a 🔽 button above every column header in
   * every .table-wrap table. Inference picks a filter UI per column type:
   *    text / number / date / select / yesno / rating.
   * State lives on each table element (table._mxFilters), so re-renders
   * (innerHTML = ...) drop state gracefully and the next MutationObserver
   * pass re-wires headers. Active filters cause the 🔽 to turn blue, and
   * a banner above the table lists each filter as a removable chip with
   * "عرض X من أصل Y صف" and a "مسح الكل" button.
   * ====================================================================== */
  function _mxColInferType(tbody, idx){
    var rows = tbody.querySelectorAll('tr');
    var vals = [];
    for (var i=0; i<rows.length && vals.length<50; i++){
      if (rows[i].classList.contains('mx-no-results')) continue;
      var cell = rows[i].children[idx];
      if (!cell) continue;
      var t = (cell.textContent || '').trim();
      if (t && t !== '—' && t !== '-') vals.push(t);
    }
    if (!vals.length) return 'text';
    var allNum = vals.every(function(v){ return /^-?\d+(\.\d+)?$/.test(v); });
    if (allNum) {
      var nums = vals.map(parseFloat);
      var inRating = nums.every(function(n){ return n >= 1 && n <= 10; });
      if (inRating) return 'rating';
      return 'number';
    }
    var allDate = vals.every(function(v){ return /^\d{4}-\d{1,2}-\d{1,2}/.test(v); });
    if (allDate) return 'date';
    var uniqueSet = {};
    vals.forEach(function(v){ uniqueSet[v] = 1; });
    var uniques = Object.keys(uniqueSet);
    if (uniques.length === 2 && uniques.every(function(v){ return v==='نعم' || v==='لا'; })) return 'yesno';
    if (uniques.length >= 2 && uniques.length <= 10) return 'select';
    return 'text';
  }
  function _mxGetUniqueValues(tbody, idx){
    var rows = tbody.querySelectorAll('tr');
    var seen = {}; var out = [];
    for (var i=0; i<rows.length; i++){
      if (rows[i].classList.contains('mx-no-results')) continue;
      var cell = rows[i].children[idx];
      if (!cell) continue;
      var t = (cell.textContent || '').trim();
      if (t && !seen[t]) { seen[t] = 1; out.push(t); }
    }
    out.sort();
    return out;
  }
  function _mxGetColumnLabel(table, idx){
    var th = table.querySelectorAll('thead tr th')[idx];
    if (!th) return 'عمود';
    var clone = th.cloneNode(true);
    // Strip every chrome button we add so the label reflects only the
    // real column name. Omitting .mx-col-del-btn here was the root
    // cause of the ✕-button "invalid column name" error — the ✕ text
    // bled into the label, no map key matched it, and the server fell
    // through to the safe-ident check.
    clone.querySelectorAll('.mx-filter-btn,.mx-col-del-btn').forEach(function(b){ b.remove(); });
    return (clone.textContent || '').replace(/\s+/g, ' ').trim() || 'عمود';
  }
  function _mxApplyFilters(table){
    var filters = table._mxFilters || {};
    var tbody = table.querySelector('tbody');
    if (!tbody) return;
    var rows = tbody.querySelectorAll('tr');
    var total = 0, shown = 0;
    for (var i=0; i<rows.length; i++){
      var tr = rows[i];
      if (tr.classList.contains('mx-no-results')) { tr.style.display = 'none'; continue; }
      total++;
      var keep = true;
      for (var idxStr in filters){
        if (!keep) break;
        var f = filters[idxStr];
        if (!f) continue;
        var idx = Number(idxStr);
        var cell = tr.children[idx];
        var val = cell ? (cell.textContent || '').trim() : '';
        if (f.type === 'text' && f.text){
          if (val.toLowerCase().indexOf(f.text.toLowerCase()) < 0) keep = false;
        } else if (f.type === 'number' || f.type === 'rating'){
          var n = parseFloat(val);
          if (isNaN(n)) { keep = false; }
          else {
            if (f.min !== '' && f.min != null && n < parseFloat(f.min)) keep = false;
            if (f.max !== '' && f.max != null && n > parseFloat(f.max)) keep = false;
          }
        } else if (f.type === 'date'){
          if (f.from && val < f.from) keep = false;
          if (f.to   && val > f.to  ) keep = false;
        } else if (f.type === 'select' && f.values && f.values.length){
          if (f.values.indexOf(val) < 0) keep = false;
        } else if (f.type === 'yesno'){
          var allowed = [];
          if (f.yes) allowed.push('نعم');
          if (f.no)  allowed.push('لا');
          if (allowed.length && allowed.indexOf(val) < 0) keep = false;
        }
      }
      tr.style.display = keep ? '' : 'none';
      if (keep) shown++;
    }
    _mxRenderFilterBanner(table, shown, total);
  }
  function _mxRenderFilterBanner(table, shown, total){
    var wrap = table.closest('.table-wrap, .att-table-wrap') || table.parentNode;
    if (!wrap) return;
    var banner = wrap.previousElementSibling;
    if (!banner || !banner.classList || !banner.classList.contains('mx-filter-banner')){
      banner = document.createElement('div');
      banner.className = 'mx-filter-banner';
      wrap.parentNode.insertBefore(banner, wrap);
    }
    var filters = table._mxFilters || {};
    var active = Object.keys(filters).filter(function(k){
      var f = filters[k];
      if (!f) return false;
      if (f.type === 'text')   return !!f.text;
      if (f.type === 'number' || f.type === 'rating') return (f.min !== '' && f.min != null) || (f.max !== '' && f.max != null);
      if (f.type === 'date')   return !!(f.from || f.to);
      if (f.type === 'select') return !!(f.values && f.values.length);
      if (f.type === 'yesno')  return !!(f.yes || f.no);
      return false;
    });
    if (!active.length){
      banner.classList.remove('show');
      banner.innerHTML = '';
      // Still update the count row above the table (if rendered).
      _mxUpdateRowCount(wrap, shown, total, false);
      return;
    }
    banner.classList.add('show');
    var html = '<span style="font-weight:800;color:#0d47a1;">الفلاتر النشطة (' + active.length + ')</span>';
    active.forEach(function(idxStr){
      var f = filters[idxStr];
      var lbl = _mxGetColumnLabel(table, Number(idxStr));
      var summary = '';
      if (f.type === 'text')   summary = f.text;
      else if (f.type === 'number' || f.type === 'rating') summary = ((f.min!=null&&f.min!==''?f.min:'…') + ' → ' + (f.max!=null&&f.max!==''?f.max:'…'));
      else if (f.type === 'date') summary = ((f.from||'…') + ' → ' + (f.to||'…'));
      else if (f.type === 'select') summary = (f.values || []).join(', ');
      else if (f.type === 'yesno') summary = [f.yes?'نعم':null, f.no?'لا':null].filter(Boolean).join(', ');
      html += '<span class="mx-fb-tag" data-col="' + idxStr + '">' + lbl + ': ' + _mxEsc(summary) + ' <span class="mx-fb-x" data-col="' + idxStr + '">✕</span></span>';
    });
    html += '<span class="mx-fb-count">عرض ' + shown + ' من أصل ' + total + ' صف</span>';
    html += '<button class="mx-fb-clear-all" type="button">مسح الكل</button>';
    banner.innerHTML = html;
    banner.querySelectorAll('.mx-fb-x').forEach(function(x){
      x.addEventListener('click', function(){
        delete table._mxFilters[x.getAttribute('data-col')];
        _mxMarkHeaderIcons(table);
        _mxApplyFilters(table);
      });
    });
    var clearAll = banner.querySelector('.mx-fb-clear-all');
    if (clearAll) clearAll.addEventListener('click', function(){
      table._mxFilters = {};
      _mxMarkHeaderIcons(table);
      _mxApplyFilters(table);
    });
    _mxUpdateRowCount(wrap, shown, total, true);
  }
  function _mxUpdateRowCount(wrap, shown, total, active){
    var counter = wrap.previousElementSibling;
    // Re-find; wrap.previousElementSibling is the banner now.
    var row = wrap.parentNode.querySelector(':scope > .mx-row-count');
    if (!row){
      row = document.createElement('div');
      row.className = 'mx-row-count';
      wrap.parentNode.insertBefore(row, wrap);
    }
    if (active){
      row.textContent = 'عرض ' + shown + ' من أصل ' + total + ' صف';
      row.style.display = '';
    } else {
      row.style.display = 'none';
    }
  }
  function _mxEsc(s){ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }
  function _mxMarkHeaderIcons(table){
    var filters = table._mxFilters || {};
    var ths = table.querySelectorAll('thead tr th');
    for (var i=0; i<ths.length; i++){
      var btn = ths[i].querySelector('.mx-filter-btn');
      if (!btn) continue;
      var f = filters[String(i)];
      var active = false;
      if (f){
        if (f.type === 'text')   active = !!f.text;
        else if (f.type === 'number' || f.type === 'rating') active = (f.min !== '' && f.min != null) || (f.max !== '' && f.max != null);
        else if (f.type === 'date') active = !!(f.from || f.to);
        else if (f.type === 'select') active = !!(f.values && f.values.length);
        else if (f.type === 'yesno') active = !!(f.yes || f.no);
      }
      btn.classList[active ? 'add' : 'remove']('active');
    }
  }
  function _mxClosePanels(){
    document.querySelectorAll('.mx-filter-panel').forEach(function(p){ p.remove(); });
  }
  function _mxOpenFilterPanel(table, idx, btn){
    _mxClosePanels();
    var tbody = table.querySelector('tbody');
    if (!tbody) return;
    var type = _mxColInferType(tbody, idx);
    var filters = table._mxFilters || (table._mxFilters = {});
    var current = filters[String(idx)] || {type: type};
    if (current.type !== type && !(current.type==='rating' && type==='number')){
      current = {type: type};
    }
    var lbl = _mxGetColumnLabel(table, idx);
    var panel = document.createElement('div');
    panel.className = 'mx-filter-panel';
    var body = '<h4>🔽 ' + _mxEsc(lbl) + '</h4>';
    if (type === 'text'){
      body += '<input class="mx-f-text" type="text" placeholder="ابحث في هذا العمود..." value="' + _mxEsc(current.text || '') + '"/>';
    } else if (type === 'number'){
      body += '<label>من: <input class="mx-f-min" type="number" step="any" value="' + _mxEsc(current.min == null ? '' : current.min) + '"/></label>';
      body += '<label>إلى: <input class="mx-f-max" type="number" step="any" value="' + _mxEsc(current.max == null ? '' : current.max) + '"/></label>';
    } else if (type === 'rating'){
      body += '<label>من (1-10): <input class="mx-f-min" type="number" min="1" max="10" step="1" value="' + _mxEsc(current.min == null ? '' : current.min) + '"/></label>';
      body += '<label>إلى (1-10): <input class="mx-f-max" type="number" min="1" max="10" step="1" value="' + _mxEsc(current.max == null ? '' : current.max) + '"/></label>';
    } else if (type === 'date'){
      body += '<label>من تاريخ: <input class="mx-f-from" type="date" value="' + _mxEsc(current.from || '') + '"/></label>';
      body += '<label>إلى تاريخ: <input class="mx-f-to" type="date" value="' + _mxEsc(current.to || '') + '"/></label>';
    } else if (type === 'select'){
      var values = _mxGetUniqueValues(tbody, idx);
      var checkedSet = {};
      (current.values || []).forEach(function(v){ checkedSet[v] = 1; });
      if (!values.length){
        body += '<div style="color:#999;">لا توجد قيم</div>';
      } else {
        body += '<div style="max-height:200px;overflow:auto;">';
        values.forEach(function(v){
          body += '<label><input type="checkbox" class="mx-f-check" value="' + _mxEsc(v) + '"' + (checkedSet[v] ? ' checked' : '') + '/> ' + _mxEsc(v) + '</label>';
        });
        body += '</div>';
      }
    } else if (type === 'yesno'){
      body += '<label><input type="checkbox" class="mx-f-yes"' + (current.yes ? ' checked' : '') + '/> نعم</label>';
      body += '<label><input type="checkbox" class="mx-f-no"'  + (current.no  ? ' checked' : '') + '/> لا</label>';
    }
    body += '<button class="mx-f-clear" type="button">مسح الفلتر</button>';
    panel.innerHTML = body;
    document.body.appendChild(panel);
    // Position below the button (viewport coords).
    var r = btn.getBoundingClientRect();
    panel.style.top  = (r.bottom + window.scrollY + 4) + 'px';
    panel.style.left = Math.max(4, (r.left + window.scrollX - 100)) + 'px';
    // Prevent click-outside closing when clicking inside panel
    panel.addEventListener('click', function(ev){ ev.stopPropagation(); });
    // Commit helper
    function commit(){
      var f = {type: type};
      if (type === 'text'){
        f.text = (panel.querySelector('.mx-f-text').value || '').trim();
      } else if (type === 'number' || type === 'rating'){
        var mn = panel.querySelector('.mx-f-min').value;
        var mx = panel.querySelector('.mx-f-max').value;
        f.min = mn;
        f.max = mx;
      } else if (type === 'date'){
        f.from = panel.querySelector('.mx-f-from').value;
        f.to   = panel.querySelector('.mx-f-to').value;
      } else if (type === 'select'){
        var checks = panel.querySelectorAll('.mx-f-check:checked');
        var arr = [];
        for (var i=0; i<checks.length; i++) arr.push(checks[i].value);
        f.values = arr;
      } else if (type === 'yesno'){
        f.yes = panel.querySelector('.mx-f-yes').checked;
        f.no  = panel.querySelector('.mx-f-no').checked;
      }
      filters[String(idx)] = f;
      _mxMarkHeaderIcons(table);
      _mxApplyFilters(table);
    }
    panel.querySelectorAll('input').forEach(function(inp){
      var ev = (inp.type === 'checkbox') ? 'change' : 'input';
      inp.addEventListener(ev, commit);
    });
    var clearBtn = panel.querySelector('.mx-f-clear');
    if (clearBtn) clearBtn.addEventListener('click', function(){
      delete filters[String(idx)];
      _mxMarkHeaderIcons(table);
      _mxApplyFilters(table);
      _mxClosePanels();
    });
  }
  /* Column-delete helpers ─────────────────────────────────────────
   * Resolve a table to its "tid" (the key used by
   * /api/custom-table/<tid>/*) by scanning the enclosing section for
   * any onclick="openUniversalTableEditModal('<tid>')" — works for
   * built-in ('students', 'groups', 'taqseet', 'attendance',
   * 'evaluations', 'payment_log') and custom (numeric id) tables
   * alike, since every section that permits column editing carries
   * that button.
   */
  function _mxResolveTid(table){
    var section = table.closest('.db-section, .custom-table-section');
    if (!section) return null;
    var el = section.querySelector('[onclick*="openUniversalTableEditModal"]');
    if (!el) return null;
    var m = (el.getAttribute('onclick') || '').match(/openUniversalTableEditModal\(['"]([^'"]+)['"]\)/);
    return m ? m[1] : null;
  }
  var _MX_COLKEY_CACHE = {};   /* tid -> {label → col_key} */
  function _mxResolveColKey(tid, label, cb){
    label = (label || '').replace(/\s+/g, ' ').trim();
    if (!tid || !label) { cb(null); return; }
    var cache = _MX_COLKEY_CACHE[tid];
    if (cache && label in cache) { cb(cache[label]); return; }
    fetch('/api/custom-table/' + encodeURIComponent(tid) + '/columns', {credentials:'include'})
      .then(function(r){ return r.json(); })
      .then(function(d){
        if (!d || !d.ok || !d.columns) { cb(null); return; }
        var map = {};
        d.columns.forEach(function(c){
          var lbl = (c.col_label || '').replace(/\s+/g, ' ').trim();
          if (lbl) map[lbl] = c.col_key;
          map[c.col_key] = c.col_key;   /* allow fallback lookup by key */
        });
        _MX_COLKEY_CACHE[tid] = map;
        cb(map[label] || null);
      })
      .catch(function(){ cb(null); });
  }

  /* Map table key → page-level reload function, to refresh the DOM
     after a successful column drop. Custom tables have no known
     loader here, so we remove the column out-of-band below. */
  var _MX_TABLE_RELOADERS = {
    'students':       ['loadStudents'],
    'groups':         ['loadGroups2', 'loadGroups'],
    'student_groups': ['loadGroups2', 'loadGroups'],
    'attendance':     ['loadAttendance'],
    'taqseet':        ['loadTaqseet'],
    'evaluations':    ['loadEvals', 'loadEvaluations'],
    'evals':          ['loadEvals', 'loadEvaluations'],
    'payment_log':    ['loadPaylog', 'loadPaymentLog'],
    'paylog':         ['loadPaylog', 'loadPaymentLog']
  };
  function _mxTriggerReload(tid){
    var fns = _MX_TABLE_RELOADERS[tid] || [];
    for (var i=0;i<fns.length;i++){
      var f = window[fns[i]];
      if (typeof f === 'function'){ try { f(); return true; } catch(e){} }
    }
    return false;
  }
  function _mxRemoveColumnFromDom(table, colIdx){
    /* Rip the <th> and every cell at that index out of the table. A
       best-effort fallback for custom tables that don't have a named
       page loader. */
    var headerRow = table.querySelector('thead tr');
    if (headerRow && headerRow.children[colIdx]) headerRow.children[colIdx].remove();
    var rows = table.querySelectorAll('tbody tr');
    for (var i=0;i<rows.length;i++){
      if (rows[i].children[colIdx]) rows[i].children[colIdx].remove();
    }
  }

  function _mxHandleColumnDelete(table, colIdx, th){
    var label = _mxGetColumnLabel(table, colIdx);
    var tid = _mxResolveTid(table);
    if (!tid){
      if (typeof window.mxToast === 'function') window.mxToast('تعذّر تحديد الجدول', 'error');
      return;
    }
    function doDelete(){
      _mxResolveColKey(tid, label, function(colKey){
        var keyForDelete = colKey || label;  /* server falls back to label→key lookup */
        fetch('/api/custom-table/' + encodeURIComponent(tid) +
              '/delete-column/' + encodeURIComponent(keyForDelete), {
          method:'DELETE', credentials:'include'
        }).then(function(r){ return r.json(); })
          .then(function(d){
            if (d && d.ok){
              if (typeof window.mxToast === 'function') window.mxToast('تم حذف العمود بنجاح', 'success');
              delete _MX_COLKEY_CACHE[tid];
              /* Refresh the table contents; fall back to surgical DOM
                 removal if the page has no named reloader. */
              if (!_mxTriggerReload(tid)) _mxRemoveColumnFromDom(table, colIdx);
            } else {
              if (typeof window.mxToast === 'function')
                window.mxToast((d && d.error) || 'تعذّر حذف العمود', 'error');
            }
          }).catch(function(){
            if (typeof window.mxToast === 'function') window.mxToast('خطأ في الاتصال', 'error');
          });
      });
    }
    if (typeof window.mxConfirm === 'function'){
      window.mxConfirm({
        title: 'تأكيد حذف العمود',
        message: 'هل أنت متأكد من حذف عمود "' + label + '"؟ سيتم حذف جميع البيانات في هذا العمود نهائياً ولا يمكن التراجع.',
        yesText: 'نعم، احذف',
        noText:  'إلغاء'
      }, doDelete);
    } else {
      if (confirm('هل أنت متأكد من حذف عمود "' + label + '"؟')) doDelete();
    }
  }

  function wireColumnFilters(){
    document.querySelectorAll('.table-wrap table, .att-table-wrap table').forEach(function(table){
      var thead = table.querySelector('thead');
      var tbody = table.querySelector('tbody');
      if (!thead || !tbody) return;
      var headerRow = thead.querySelector('tr');
      if (!headerRow) return;
      var ths = headerRow.children;
      for (var i=0; i<ths.length; i++){
        var th = ths[i];
        if (th.classList.contains('bulk-col')) continue;
        // Skip columns whose content is purely action buttons
        // (identify by checking for an "إجراءات / Actions" heading).
        var txt = (th.textContent || '').replace(/🔽|✕/g, '').trim();
        var isSkipCol = /^(إجراءات|actions|Actions)$/.test(txt) || txt === '#';
        // --- Filter button ---
        if (!th.querySelector('.mx-filter-btn') && !isSkipCol){
          var fbtn = document.createElement('button');
          fbtn.type = 'button';
          fbtn.className = 'mx-filter-btn';
          fbtn.title = 'فلتر';
          fbtn.textContent = '🔽';
          fbtn.setAttribute('data-col-idx', i);
          (function(tableRef, idxCap, btnRef){
            btnRef.addEventListener('click', function(ev){
              ev.stopPropagation();
              _mxOpenFilterPanel(tableRef, idxCap, btnRef);
            });
          })(table, i, fbtn);
          th.appendChild(fbtn);
        }
        // --- Delete ✕ button (hover-reveal) ---
        if (!th.querySelector('.mx-col-del-btn') && !isSkipCol){
          var dbtn = document.createElement('button');
          dbtn.type = 'button';
          dbtn.className = 'mx-col-del-btn';
          dbtn.title = 'حذف العمود';
          dbtn.textContent = '✕';
          dbtn.setAttribute('data-col-idx', i);
          (function(tableRef, idxCap, thRef, btnRef){
            btnRef.addEventListener('click', function(ev){
              ev.stopPropagation();
              ev.preventDefault();
              _mxHandleColumnDelete(tableRef, idxCap, thRef);
            });
          })(table, i, th, dbtn);
          th.appendChild(dbtn);
        }
      }
      _mxMarkHeaderIcons(table);
      // Re-apply any sticky filter state after a table re-render.
      if (table._mxFilters) _mxApplyFilters(table);
    });
  }
  // Close panel on outside click / Escape.
  //
  // BUG FIX: the previous version registered this listener in the capture
  // phase, so any click inside the panel closed it *before* the text-
  // input / checkbox / date-picker could register a focus or change event.
  // Select checkboxes and text-input clicks became no-ops because the
  // panel was ripped out of the DOM the instant the user clicked it.
  //
  // Now: bubbling phase, skip the close when the target is inside a panel
  // or on the 🔽 trigger. The button's own click handler still calls
  // stopPropagation() so opening the panel doesn't immediately close it.
  document.addEventListener('click', function(ev){
    var t = ev.target;
    if (!t) return;
    if (t.closest && (t.closest('.mx-filter-panel') || t.closest('.mx-filter-btn'))) return;
    _mxClosePanels();
  });
  document.addEventListener('keydown', function(ev){ if (ev.key === 'Escape') _mxClosePanels(); });

  /* Unify existing delete-confirm text so the wording matches spec. */
  function unifyConfirmText(){
    document.querySelectorAll('.confirm-box h3').forEach(function(h){
      h.textContent = 'هل أنت متأكد من الحذف؟';
    });
    document.querySelectorAll('.confirm-box p').forEach(function(p){
      if ((p.textContent || '').indexOf('لا يمكن التراجع') < 0){
        p.textContent = 'لا يمكن التراجع عن هذا الإجراء';
      }
    });
  }

  /* Global post-import refresh hook.
     The server returns {table, inserted, updated, skipped, errors, ...} and
     both the generic Excel modal and the attendance modal dispatch a
     `mx-imported` custom event on window. Pages that want to react call
     window.mxOnImport(table, fn). This helper also:
       - fires any <page>_refresh functions matching the imported table
       - shows a summary toast via mxToast
  */
  var TABLE_REFRESH_HOOKS = {
    'students':       ['loadStudents'],
    'student_groups': ['loadGroups2', 'loadGroups'],
    'attendance':     ['loadAttendance', 'loadGroups', 'loadAttendanceGroups'],
    'taqseet':        ['loadTaqseet'],
    'evaluations':    ['loadEvals', 'loadEvaluations'],
    'payment_log':    ['loadPaylog', 'loadPaymentLog']
  };
  window.mxOnImport = function(table, fn){
    window.addEventListener('mx-imported', function(ev){
      var d = (ev && ev.detail) || {};
      if (!table || d.table === table) {
        try { fn(d); } catch(e){}
      }
    });
  };
  window.addEventListener('mx-imported', function(ev){
    var d = (ev && ev.detail) || {};
    var hooks = TABLE_REFRESH_HOOKS[d.table] || [];
    for (var i=0; i<hooks.length; i++){
      var fn = window[hooks[i]];
      if (typeof fn === 'function') { try { fn(); } catch(e){} }
    }
    var ins = d.inserted || 0, upd = d.updated || 0, skp = d.skipped || 0, err = d.errors || 0;
    var parts = ['✅ ' + (d.table || 'import') + ' — أُدرج: ' + ins];
    if (upd) parts.push('محدّث: ' + upd);
    if (skp) parts.push('متجاهل: ' + skp);
    if (err) parts.push('أخطاء: ' + err);
    if (typeof window.mxToast === 'function') window.mxToast(parts.join(' — '), err ? 'error' : 'success');
  });

  function init(){
    scanButtons();
    addColumnCounts();
    wireTableSearches();
    wireAttendanceIntro();
    unifyConfirmText();
    wireColumnFilters();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  if (window.MutationObserver){
    var mo = new MutationObserver(function(muts){
      var touchedBtn=false, touchedTable=false, touchedSearch=false, touchedConfirm=false, touchedTbody=false, touchedThead=false;
      for (var i=0;i<muts.length;i++){
        var m = muts[i];
        // When a tbody's rows change (common — every table re-renders via
        // innerHTML), re-wire column filters so new row content picks up
        // the inferred column type and any sticky state re-applies. Same
        // when a thead rebuilds (evaluations + paylog fetch their header
        // labels from /api/*-columns after DOMContentLoaded).
        if (m.target){
          if (m.target.tagName === 'TBODY') touchedTbody = true;
          if (m.target.tagName === 'THEAD' || m.target.tagName === 'TR') touchedThead = true;
        }
        for (var j=0;j<m.addedNodes.length;j++){
          var n = m.addedNodes[j];
          if (!n || n.nodeType !== 1) continue;
          if (n.matches){
            if (n.matches('button') || (n.querySelector && n.querySelector('button'))) touchedBtn = true;
            if (n.matches('.table-wrap') || (n.querySelector && n.querySelector('.table-wrap, .att-table-wrap'))) touchedTable = true;
            if (n.matches('.search-bar') || n.matches('input') || (n.querySelector && n.querySelector('.search-bar input'))) touchedSearch = true;
            if (n.matches('.confirm-box') || (n.querySelector && n.querySelector('.confirm-box'))) touchedConfirm = true;
            if (n.matches('tr') || (n.querySelector && n.querySelector('tr'))) touchedTbody = true;
            if (n.matches('th') || (n.querySelector && n.querySelector('th'))) touchedThead = true;
          }
        }
      }
      if (touchedBtn) scanButtons();
      if (touchedTable) addColumnCounts();
      if (touchedSearch) wireTableSearches();
      if (touchedConfirm) unifyConfirmText();
      if (touchedTable || touchedTbody || touchedThead) wireColumnFilters();
    });
    mo.observe(document.body, { childList:true, subtree:true });
  }
})();
'''

@app.route('/mx-helpers.js')
def mx_helpers_js():
    return Response(MX_HELPERS_JS, mimetype='application/javascript; charset=utf-8')

for _mxh_name in ('HOME_HTML', 'DATABASE_HTML', 'ATTENDANCE_HTML', 'GROUPS_HTML', 'SETTINGS_HTML', 'LOGIN_HTML'):
    _mxh_val = globals().get(_mxh_name)
    if isinstance(_mxh_val, str) and '</body>' in _mxh_val and '/mx-helpers.js' not in _mxh_val:
        globals()[_mxh_name] = _mxh_val.replace('</body>', '<script src="/mx-helpers.js"></script>\n</body>')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
