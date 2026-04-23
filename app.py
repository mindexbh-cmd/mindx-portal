from flask import Flask, request, session, redirect, g, jsonify
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
        is_visible INTEGER DEFAULT 1)""")
    db.execute("""CREATE TABLE IF NOT EXISTS group_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1)""")

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
        is_visible INTEGER DEFAULT 1)""")
    db.execute("""CREATE TABLE IF NOT EXISTS custom_tables(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tbl_name TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now')))""")
    db.execute("""CREATE TABLE IF NOT EXISTS custom_table_cols(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER,
        col_key TEXT,
        col_label TEXT,
        col_order INTEGER DEFAULT 0)""")
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
    db.execute("""CREATE TABLE IF NOT EXISTS payment_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER UNIQUE,
        student_name TEXT,
        group_name TEXT,
        pay_date TEXT,
        day_name TEXT,
        inst_type TEXT,
        price REAL DEFAULT 0,
        paid REAL DEFAULT 0,
        remaining REAL DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS paylog_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1)""")
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
        is_visible INTEGER DEFAULT 1)""")
    db2.execute("""CREATE TABLE IF NOT EXISTS group_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1)""")
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
        is_visible INTEGER DEFAULT 1)""")
    db2.execute("""CREATE TABLE IF NOT EXISTS custom_tables(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tbl_name TEXT UNIQUE,
        created_at TEXT DEFAULT (datetime('now')))""")
    db2.execute("""CREATE TABLE IF NOT EXISTS custom_table_cols(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_id INTEGER,
        col_key TEXT,
        col_label TEXT,
        col_order INTEGER DEFAULT 0)""")
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
    db2.execute("""CREATE TABLE IF NOT EXISTS payment_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER UNIQUE,
        student_name TEXT,
        group_name TEXT,
        pay_date TEXT,
        day_name TEXT,
        inst_type TEXT,
        price REAL DEFAULT 0,
        paid REAL DEFAULT 0,
        remaining REAL DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    db2.execute("""CREATE TABLE IF NOT EXISTS paylog_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1)""")
    if "paylog_labels_v1" not in applied:
        seed_paylog_labels = [
            ("student_name", "&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;", 1),
            ("group_name",   "&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;", 2),
            ("pay_date",     "&#x627;&#x644;&#x62A;&#x627;&#x631;&#x64A;&#x62E;", 3),
            ("day_name",     "&#x627;&#x644;&#x64A;&#x648;&#x645;", 4),
            ("inst_type",    "&#x646;&#x648;&#x639; &#x627;&#x644;&#x642;&#x633;&#x637;", 5),
            ("price",        "&#x627;&#x644;&#x633;&#x639;&#x631;", 6),
            ("paid",         "&#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639;", 7),
            ("remaining",    "&#x627;&#x644;&#x645;&#x62A;&#x628;&#x642;&#x64A;", 8),
        ]
        for key, label, order in seed_paylog_labels:
            try:
                db2.execute("INSERT INTO paylog_col_labels(col_key,col_label,col_order) VALUES(?,?,?)", (key, label, order))
            except Exception:
                pass
        try:
            db2.execute("INSERT INTO schema_migrations(tag) VALUES(?)", ("paylog_labels_v1",))
        except Exception:
            pass
    db2.commit()
    db2.close()

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
</style>
</head>
<body>
<div class="dh-topbar">
  <div class="dh-topbar-title">&#x1F393; MINDEX EDUCATION &amp; TRAINING CENTRE</div>
  <div class="dh-topbar-right">
    <span>&#x645;&#x631;&#x62D;&#x628;&#x627;&#x64B; <b>USER_PLACEHOLDER</b></span>
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

<div id="ss-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:9999;overflow:auto;"><div style="background:#fff;margin:40px auto;border-radius:14px;max-width:780px;width:94%;padding:0;overflow:hidden;box-shadow:0 8px 32px rgba(230,81,0,0.25);"><div style="background:linear-gradient(135deg,#E65100,#FB8C00);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#fff;font-size:1.2rem;font-weight:bold;">&#x1F4CA; &#x645;&#x644;&#x62E;&#x635; &#x627;&#x644;&#x62D;&#x635;&#x635;</span><span onclick="document.getElementById('ss-modal').style.display='none'" style="color:#fff;font-size:1.8rem;cursor:pointer;line-height:1;">&times;</span></div><div id="ss-body" style="padding:18px 22px;max-height:70vh;overflow:auto;font-size:1.05rem;color:#333;"></div></div></div>

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
function ssOpen(){
  document.getElementById("ss-modal").style.display="block";
  var body=document.getElementById("ss-body");
  body.innerHTML="\u062C\u0627\u0631\u064A \u0627\u0644\u062A\u062D\u0645\u064A\u0644...";
  fetch("/api/session-summary").then(r=>r.json()).then(function(rows){
    if(!rows||!rows.length){body.innerHTML="\u0644\u0627 \u062A\u0648\u062C\u062F \u0645\u062C\u0645\u0648\u0639\u0627\u062A";return;}
    var html="";
    rows.forEach(function(r){
      var pct=parseFloat(r.completion_pct||0);
      var barColor=pct>=100?"#2E7D32":(pct>=50?"#F9A825":"#E65100");
      var remColor=(parseFloat(r.remaining_hours||0)<0)?"#c62828":"#2E7D32";
      html+="<div style='margin-bottom:14px;padding:12px 14px;background:#fff8f0;border:1px solid #ffe0b2;border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,0.04);'>"
          + "<div style='font-weight:800;color:#4a148c;font-size:1.05rem;margin-bottom:8px;border-bottom:1px dashed #ffcc80;padding-bottom:6px;'>"+(r.group_name||"")+"</div>"
          + "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px;margin-bottom:10px;font-size:0.92rem;'>"
          +   "<div style='background:#fff;border:1px solid #eee;border-radius:8px;padding:7px 9px;'><div style='color:#777;font-size:0.8rem;'>\u0625\u062C\u0645\u0627\u0644\u064A \u0627\u0644\u0645\u0633\u062A\u062D\u0642\u0629</div><div style='font-weight:800;color:#1565C0;'>"+_ssFmtH(r.required_hours)+" \u0633\u0627\u0639\u0629</div></div>"
          +   "<div style='background:#fff;border:1px solid #eee;border-radius:8px;padding:7px 9px;'><div style='color:#777;font-size:0.8rem;'>\u0633\u0627\u0639\u0627\u062A \u0627\u0644\u062D\u0636\u0648\u0631</div><div style='font-weight:800;color:#2E7D32;'>"+_ssFmtH(r.present_hours)+" \u0633\u0627\u0639\u0629</div></div>"
          +   "<div style='background:#fff;border:1px solid #eee;border-radius:8px;padding:7px 9px;'><div style='color:#777;font-size:0.8rem;'>\u0633\u0627\u0639\u0627\u062A \u0627\u0644\u0623\u0648\u0646\u0644\u0627\u064A\u0646</div><div style='font-weight:800;color:#6A1B9A;'>"+_ssFmtH(r.online_hours)+" \u0633\u0627\u0639\u0629</div></div>"
          +   "<div style='background:#fff;border:1px solid #eee;border-radius:8px;padding:7px 9px;'><div style='color:#777;font-size:0.8rem;'>\u0627\u0644\u0633\u0627\u0639\u0627\u062A \u0627\u0644\u0645\u0623\u062E\u0648\u0630\u0629</div><div style='font-weight:800;color:#E65100;'>"+_ssFmtH(r.total_hours)+" \u0633\u0627\u0639\u0629</div></div>"
          +   "<div style='background:#fff;border:1px solid #eee;border-radius:8px;padding:7px 9px;'><div style='color:#777;font-size:0.8rem;'>\u0627\u0644\u0633\u0627\u0639\u0627\u062A \u0627\u0644\u0645\u062A\u0628\u0642\u064A\u0629</div><div style='font-weight:800;color:"+remColor+";'>"+_ssFmtH(r.remaining_hours)+" \u0633\u0627\u0639\u0629</div></div>"
          + "</div>"
          + "<div style='background:#eee;border-radius:8px;overflow:hidden;height:16px;position:relative;'>"
          +   "<div style='background:"+barColor+";height:100%;width:"+pct+"%;transition:width 0.4s;'></div>"
          +   "<div style='position:absolute;top:0;right:0;left:0;text-align:center;font-size:0.8rem;font-weight:700;color:#222;line-height:16px;'>"+pct+"%</div>"
          + "</div>"
          + "</div>";
    });
    body.innerHTML=html;
  }).catch(function(){body.innerHTML="\u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u062A\u062D\u0645\u064A\u0644";});
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
  scored.sort(function(a,b){ return b.score - a.score; });
  scored = scored.slice(0, 10);
  if (!scored.length) { results.innerHTML = '<div style="padding:12px;color:#888;">\u0644\u0627 \u062A\u0648\u062C\u062F \u0646\u062A\u0627\u0626\u062C</div>'; return; }
  var html = '';
  for (var i=0; i<scored.length; i++) {
    var s = scored[i].s;
    html += '<div class="srm-result" onclick="srPick('+s.id+')">'
         +  '<div class="srm-result-name">'+(s.student_name||'-')+'</div>'
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
function _srField(id, label, value, readonly){
  var v = value == null ? '' : String(value);
  v = v.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
  return '<div class="srm-field"><label>'+label+'</label><input id="'+id+'" value="'+v+'"'+(readonly?' readonly class="srm-readonly"':'')+'></div>';
}
function _srRenderCard(d){
  var s = d.student || {};
  var att = d.attendance || {};
  var tot = d.payment_totals || {};
  var html = '<div class="srm-card">';
  // BASIC
  html += '<div class="srm-section"><div class="srm-section-title">\U0001F464 \u0627\u0644\u0628\u064A\u0627\u0646\u0627\u062A \u0627\u0644\u0623\u0633\u0627\u0633\u064A\u0629</div><div class="srm-grid">';
  html += _srField('sr_personal_id','\u0627\u0644\u0631\u0642\u0645 \u0627\u0644\u0634\u062E\u0635\u064A', s.personal_id);
  html += _srField('sr_student_name','\u0627\u0633\u0645 \u0627\u0644\u0637\u0627\u0644\u0628', s.student_name);
  html += _srField('sr_whatsapp','\u0627\u0644\u0648\u0627\u062A\u0633\u0627\u0628', s.whatsapp);
  html += _srField('sr_class_name','\u0627\u0644\u0635\u0641', s.class_name);
  html += _srField('sr_group_name_student','\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629', s.group_name_student);
  html += _srField('sr_group_online','\u0627\u0644\u0645\u062C\u0645\u0648\u0639\u0629 (\u0627\u0644\u0627\u0648\u0646\u0644\u0627\u064A\u0646)', s.group_online);
  html += _srField('sr_old_new_2026','\u0642\u062F\u064A\u0645 \u062C\u062F\u064A\u062F 2026', s.old_new_2026);
  html += _srField('sr_registration_term2_2026','\u062A\u0633\u062C\u064A\u0644 \u0627\u0644\u0641\u0635\u0644 \u0627\u0644\u062B\u0627\u0646\u064A 2026', s.registration_term2_2026);
  html += _srField('sr_teacher_2026','\u0627\u0644\u0645\u062F\u0631\u0633 2026', s.teacher_2026);
  html += _srField('sr_books_received','\u0627\u0633\u062A\u0644\u0627\u0645 \u0627\u0644\u0643\u062A\u0628', s.books_received);
  html += _srField('sr_final_result','\u0627\u0644\u0646\u062A\u064A\u062C\u0629 \u0627\u0644\u0646\u0647\u0627\u0626\u064A\u0629', s.final_result);
  html += _srField('sr_level_reached_2026','\u0627\u0644\u0649 \u0627\u064A\u0646 \u0648\u0635\u0644 2026', s.level_reached_2026);
  html += _srField('sr_suitable_level_2026','\u0645\u0646\u0627\u0633\u0628 \u0644\u0644\u0645\u0633\u062A\u0648\u0649 2026\u061F', s.suitable_level_2026);
  html += '</div></div>';
  // CONTACT
  html += '<div class="srm-section"><div class="srm-section-title">\U0001F4DE \u0627\u0644\u0627\u062A\u0635\u0627\u0644 \u0648\u0627\u0644\u0633\u0643\u0646</div><div class="srm-grid">';
  html += _srField('sr_mother_phone','\u0647\u0627\u062A\u0641 \u0627\u0644\u0623\u0645', s.mother_phone);
  html += _srField('sr_father_phone','\u0647\u0627\u062A\u0641 \u0627\u0644\u0623\u0628', s.father_phone);
  html += _srField('sr_other_phone','\u0647\u0627\u062A\u0641 \u0622\u062E\u0631', s.other_phone);
  html += _srField('sr_residence','\u0645\u0643\u0627\u0646 \u0627\u0644\u0633\u0643\u0646', s.residence);
  html += _srField('sr_home_address','\u0627\u0644\u0639\u0646\u0648\u0627\u0646', s.home_address);
  html += _srField('sr_road','\u0627\u0644\u0637\u0631\u064A\u0642', s.road);
  html += _srField('sr_complex_name','\u0627\u0644\u0645\u062C\u0645\u0639', s.complex_name);
  html += '</div></div>';
  // PAYMENTS
  html += '<div class="srm-section"><div class="srm-section-title">\U0001F4B3 \u062A\u0641\u0627\u0635\u064A\u0644 \u0627\u0644\u062F\u0641\u0639</div><div class="srm-grid">';
  html += _srField('sr_installment_type','\u0646\u0648\u0639 \u0627\u0644\u062A\u0642\u0633\u064A\u0637', s.installment_type);
  html += _srField('sr_installment1','\u0627\u0644\u0642\u0633\u0637 1', s.installment1);
  html += _srField('sr_installment2','\u0627\u0644\u0642\u0633\u0637 2', s.installment2);
  html += _srField('sr_installment3','\u0627\u0644\u0642\u0633\u0637 3', s.installment3);
  html += _srField('sr_installment4','\u0627\u0644\u0642\u0633\u0637 4', s.installment4);
  html += _srField('sr_installment5','\u0627\u0644\u0642\u0633\u0637 5', s.installment5);
  html += '</div>';
  html += '<div class="srm-totals">'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+(tot.paid||0)+'</div><div class="srm-stat-lbl">\u0627\u0644\u0645\u062F\u0641\u0648\u0639</div></div>'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+(tot.price||0)+'</div><div class="srm-stat-lbl">\u0627\u0644\u0633\u0639\u0631 \u0627\u0644\u0625\u062C\u0645\u0627\u0644\u064A</div></div>'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+(tot.remaining||0)+'</div><div class="srm-stat-lbl">\u0627\u0644\u0645\u062A\u0628\u0642\u064A</div></div>'
       + '</div></div>';
  // ATTENDANCE
  var pct = function(v){ return (v||0)+'%'; };
  var bar = function(v){ return '<div class="srm-pct-bar"><div class="srm-pct-bar-inner" style="width:'+(Math.min(100,v||0))+'%"></div></div>'; };
  html += '<div class="srm-section"><div class="srm-section-title">\U0001F4C5 \u0625\u062D\u0635\u0627\u0626\u064A\u0627\u062A \u0627\u0644\u062D\u0636\u0648\u0631 ('+att.total+' \u062C\u0644\u0633\u0629)</div>';
  html += '<div class="srm-totals">'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+pct(att.present_rate)+'</div><div class="srm-stat-lbl">\u0646\u0633\u0628\u0629 \u0627\u0644\u062D\u0636\u0648\u0631 ('+att.present+')</div>'+bar(att.present_rate)+'</div>'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+pct(att.absent_rate)+'</div><div class="srm-stat-lbl">\u0646\u0633\u0628\u0629 \u0627\u0644\u063A\u064A\u0627\u0628 ('+att.absent+')</div>'+bar(att.absent_rate)+'</div>'
       +  '<div class="srm-stat"><div class="srm-stat-num">'+pct(att.late_rate)+'</div><div class="srm-stat-lbl">\u0646\u0633\u0628\u0629 \u0627\u0644\u062A\u0623\u062E\u064A\u0631 ('+att.late+')</div>'+bar(att.late_rate)+'</div>'
       + '</div></div>';
  // ACTIONS
  html += '<div class="srm-actions">'
       +  '<button class="srm-save" onclick="srSave()">\U0001F4BE \u062D\u0641\u0638</button>'
       +  '<button class="srm-cancel" onclick="srClose()">\u0625\u063A\u0644\u0627\u0642</button>'
       +  '</div>';
  html += '</div>';
  document.getElementById('sr-details').innerHTML = html;
}
function srSave(){
  if (!_srCurrentId) return;
  var ids = ['personal_id','student_name','whatsapp','class_name','group_name_student','group_online','old_new_2026','registration_term2_2026','teacher_2026','books_received','final_result','level_reached_2026','suitable_level_2026','mother_phone','father_phone','other_phone','residence','home_address','road','complex_name','installment_type','installment1','installment2','installment3','installment4','installment5'];
  var body = {};
  for (var i=0; i<ids.length; i++) {
    var el = document.getElementById('sr_'+ids[i]);
    if (el) body[ids[i]] = el.value;
  }
  fetch('/api/students/'+_srCurrentId, { method:'PUT', headers:{'Content-Type':'application/json'}, credentials:'include', body: JSON.stringify(body) })
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d.ok) {
        // Refresh the card with the latest details.
        srPick(_srCurrentId);
        // Also refresh our local students cache so the result list stays accurate.
        fetch('/api/students').then(function(r){return r.json();}).then(function(data){ _srStudents = data.students || []; });
      } else {
        alert(d.error || '\u062D\u062F\u062B \u062E\u0637\u0623');
      }
    })
    .catch(function(){ alert('\u062D\u062F\u062B \u062E\u0637\u0623 \u0641\u064A \u0627\u0644\u0627\u062A\u0635\u0627\u0644'); });
}
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

<div id="pay-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.6);z-index:9999;overflow:auto;"><div style="background:#fff;margin:20px auto;border-radius:14px;max-width:99%;padding:0;overflow:hidden;box-shadow:0 8px 32px rgba(107,63,160,0.25);"><div style="background:linear-gradient(135deg,#6B3FA0,#8B5CC8);padding:14px 20px;display:flex;justify-content:space-between;align-items:center;"><span style="color:#fff;font-size:1.2rem;font-weight:bold;">&#x1F4B3; &#x645;&#x62A;&#x627;&#x628;&#x639;&#x629; &#x627;&#x644;&#x62F;&#x641;&#x639;</span><span onclick="document.getElementById('pay-modal').style.display='none'" style="color:#fff;font-size:1.8rem;cursor:pointer;line-height:1;">&times;</span></div><div style="padding:14px 16px;background:#f8f4ff;border-bottom:1px solid #e0d0f8;"><div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;"><div><label style="display:block;font-weight:bold;color:#4a148c;margin-bottom:4px;">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label><select id="pm-group" onchange="pmLoadGroup()" style="padding:7px 12px;border-radius:8px;border:1.5px solid #8B5CC8;min-width:160px;font-size:0.95rem;"><option value="">&mdash; &#x627;&#x62E;&#x62A;&#x631; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &mdash;</option></select></div><div><label style="display:block;font-weight:bold;color:#4a148c;margin-bottom:4px;">&#x627;&#x644;&#x62A;&#x627;&#x631;&#x64A;&#x62E;</label><input type="date" id="pm-date" onchange="pmSetDay()" style="padding:7px 12px;border-radius:8px;border:1.5px solid #8B5CC8;font-size:0.95rem;"></div><div><label style="display:block;font-weight:bold;color:#4a148c;margin-bottom:4px;">&#x627;&#x644;&#x64A;&#x648;&#x645;</label><input type="text" id="pm-day" readonly style="padding:7px 12px;border-radius:8px;border:1.5px solid #ccc;background:#f0f0f0;min-width:90px;font-size:0.95rem;"></div><div><label style="display:block;font-weight:bold;color:#4a148c;margin-bottom:4px;">&#x628;&#x62D;&#x62B;</label><input type="text" id="pm-search" oninput="pmFilter()" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x644;&#x627;&#x633;&#x645;..." style="padding:7px 12px;border-radius:8px;border:1.5px solid #8B5CC8;min-width:170px;font-size:0.95rem;"></div></div></div><div style="overflow-x:auto;"><table id="pm-tbl" style="border-collapse:collapse;width:100%;min-width:400px;font-size:0.76rem;"><thead><tr style="background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;text-align:center;"><th rowspan="2" style="padding:8px 14px;border:1px solid #9b6fd4;position:sticky;right:0;background:linear-gradient(135deg,#6B3FA0,#8B5CC8);z-index:2;min-width:140px;">&#x627;&#x644;&#x627;&#x633;&#x645;</th><th colspan="4" style="padding:7px 4px;border:1px solid #9b6fd4;">&#x642;&#x633;&#x637; 1</th></tr><tr style="background:#ede7f6;color:#4a148c;text-align:center;"><th style="padding:5px 3px;border:1px solid #c5b3e6;white-space:nowrap;">&#x646;&#x648;&#x639; &#x627;&#x644;&#x623;&#x642;&#x633;&#x627;&#x637;</th><th style="padding:5px 3px;border:1px solid #c5b3e6;white-space:nowrap;">&#x627;&#x644;&#x633;&#x639;&#x631;</th><th style="padding:5px 3px;border:1px solid #c5b3e6;white-space:nowrap;">&#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639;</th><th style="padding:5px 3px;border:1px solid #c5b3e6;white-space:nowrap;">&#x627;&#x644;&#x645;&#x62A;&#x628;&#x642;&#x64A;</th></tr></thead><tbody id="pm-tbody"></tbody></table></div></div></div>
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
  var d=document.getElementById("pm-date").value;if(!d)return;
  var days=["\u0627\u0644\u0623\u062d\u062f","\u0627\u0644\u0627\u062b\u0646\u064a\u0646","\u0627\u0644\u062b\u0644\u0627\u062b\u0627\u0621","\u0627\u0644\u0623\u0631\u0628\u0639\u0627\u0621","\u0627\u0644\u062e\u0645\u064a\u0633","\u0627\u0644\u062c\u0645\u0639\u0629","\u0627\u0644\u0633\u0628\u062a"];
  document.getElementById("pm-day").value=days[new Date(d).getDay()];
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
  var body={inst_type:((tr.querySelector(".pm-type[data-inst='"+inst+"']")||{}).value||""),
    price:parseFloat(((tr.querySelector(".pm-price[data-inst='"+inst+"']")||{}).value))||0,
    paid:parseFloat(((tr.querySelector(".pm-paid[data-inst='"+inst+"']")||{}).value))||0,
    pay_date:(document.getElementById("pm-date")||{}).value||"",
    day_name:(document.getElementById("pm-day")||{}).value||""};
  fetch("/api/payments/"+sid+"/"+inst,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}).then(r=>r.json()).then(function(d){btn.textContent=d.ok?"\u2713":"\u274c";setTimeout(function(){btn.textContent="\u062d\u0641\u0638";},1800);});
}
function pmFilter(){
  var q=_norm(document.getElementById("pm-search").value.toLowerCase());
  document.querySelectorAll("#pm-tbody tr").forEach(function(tr){var n=_norm((tr.dataset.name||"").toLowerCase());tr.style.display=n.includes(q)?"":"none";});
}
</script>
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
  <a href="/dashboard" class="btn-back">&larr; &#x627;&#x644;&#x631;&#x626;&#x64A;&#x633;&#x64A;&#x629;</a>
</div>
<div class="main">
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
          existingRecords[data.records[i].student_name] = data.records[i];
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

function renderTable(students, existingList, stats) {
  stats = stats || {};
  var statusMap = {}; var msgStatusMap = {};
  for(var i=0; i<existingList.length; i++) {
    statusMap[existingList[i].student_name] = existingList[i].status || ''; msgStatusMap[existingList[i].student_name] = existingList[i].message_status || '';
  }

  var html = '';
  if(!students.length) {
    html = '<tr><td colspan="9" class="empty-state">\u0644\u0627 \u064a\u0648\u062c\u062f \u0637\u0644\u0627\u0628 \u0641\u064a \u0647\u0630\u0647 \u0627\u0644\u0645\u062c\u0645\u0648\u0639\u0629</td></tr>';
  } else {
    for(var i=0; i<students.length; i++) {
      var name = students[i].student_name || '-';
      var savedStatus = statusMap[name] || ''; var savedMsgStatus = msgStatusMap[name] || '';
      var cssClass = 'status-select';
      if(savedStatus === '\u062d\u0627\u0636\u0631') cssClass += ' present';
      else if(savedStatus === '\u063a\u0627\u0626\u0628') cssClass += ' absent';
      else if(savedStatus === '\u0645\u062a\u0623\u062e\u0631') cssClass += ' late';

      html += '<tr>';
      html += '<td>' + (i+1) + '</td>';
      html += '<td class="student-name-cell">' + name + '</td>';
      html += '<td><select class="' + cssClass + '" data-name="' + name.replace(/"/g, '&quot;') + '" onchange="onStatusChange(this)">';
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

    if(currentMode === 'exists' && existingRecords[name]) {
      // Update existing record
      updates.push({ id: existingRecords[name].id, status: status,
        attendance_date: existingRecords[name].attendance_date,
        day_name: existingRecords[name].day_name,
        group_name: existingRecords[name].group_name,
        student_name: existingRecords[name].student_name,
        contact_number: existingRecords[name].contact_number || '',
        message: existingRecords[name].message || '',
        message_status: (tr.querySelector('.sent-check') && tr.querySelector('.sent-check').checked) ? '1' : (existingRecords[name].message_status || ''),
        study_status: existingRecords[name].study_status || ''
      });
    } else if(currentMode === 'new') {
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
  <a href="/dashboard" class="btn-home">&larr; &#x627;&#x644;&#x631;&#x626;&#x64A;&#x633;&#x64A;&#x629;</a>
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
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:20px;"><button class="btn-add" style="margin-bottom:0;" onclick="openAddModal()">+ &#x625;&#x636;&#x627;&#x641;&#x629; &#x637;&#x627;&#x644;&#x628;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#43A047,#2E7D32);" onclick="openStudentExcelModal()">&#128196; &#x627;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openTableEditModal()">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
  <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#3F51B5,#5C6BC0);" onclick="openGenericExcelModal()">&#x1F4E5; &#x625;&#x636;&#x627;&#x641;&#x629; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x645;&#x646; Excel</button><button class="btn-delete-table" onclick="openDeleteTableModal()">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal('students')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button><button id="bulkDelBtn_students" class="btn-bulk-del" onclick="_bulkDelete('studentsBody',function(id){return '/api/students/'+id;},loadStudents,'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x637;&#x627;&#x644;&#x628;&#x61F;')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button></div>
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
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:20px;"><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00BCD4,#0097A7);" onclick="openAddGroupModal2()">+ &#x625;&#x636;&#x627;&#x641;&#x629; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#43A047,#2E7D32);" onclick="openGenericExcelModal('student_groups')">&#128196; &#x627;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openGroupTableEditModal()">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal('groups')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button><button id="bulkDelBtn_groups" class="btn-bulk-del" onclick="_bulkDelete('groupsBody2',function(id){return '/api/groups/'+id;},loadGroups2,'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;&#x61F;')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#c0392b,#e74c3c);" onclick="cleanupEmptyGroups()">&#x1F9F9; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x635;&#x641;&#x648;&#x641; &#x627;&#x644;&#x641;&#x627;&#x631;&#x63A;&#x629;</button></div>
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
    <button onclick="openAddTaqseet()" style="padding:8px 16px;border-radius:8px;border:none;background:linear-gradient(135deg,#1976D2,#42A5F5);color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#43; &#x625;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button>
    <button onclick="openTaqseetColModal()" style="padding:8px 16px;border-radius:8px;border:none;background:#FF6B35;color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#10133; &#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F;</button>
    <button onclick="openTaqseetEditModal()" style="padding:8px 16px;border-radius:8px;border:none;background:#9C27B0;color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
    <button onclick="openFreezeModal('taqseet')" style="padding:8px 16px;border-radius:8px;border:none;background:linear-gradient(135deg,#1565C0,#1E88E5);color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button>
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
  <button class="btn-add" style="background:linear-gradient(135deg,#388E3C,#66BB6A);" onclick="openAttendanceExcelModal()">&#128196; &#x627;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button>
  <button class="btn-add" style="background:linear-gradient(135deg,#E65100,#FFA726);" onclick="openAttendanceTableEditModal()">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
  <button class="btn-add" style="background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal('attendance')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button>
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
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#43A047,#2E7D32);" onclick="openGenericExcelModal('payment_log')">&#128196; &#x627;&#x636;&#x627;&#x641;&#x629; &#x62C;&#x62F;&#x648;&#x644;</button>
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openPaylogTableEditModal()">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</button>
    <button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#1565C0,#1E88E5);" onclick="openFreezeModal('paylog')">&#x1F4CC; &#x62A;&#x62C;&#x645;&#x64A;&#x62F;</button>
    <button id="bulkDelBtn_paylog" class="btn-bulk-del" onclick="_bulkDelete('paylogBody',function(id){return '/api/payment-log/'+id;},loadPaymentLog,'&#x647;&#x644; &#x62A;&#x631;&#x64A;&#x62F; &#x62D;&#x630;&#x641; {n} &#x633;&#x62C;&#x644;&#x61F;')">&#x1F5D1; &#x62D;&#x630;&#x641; &#x627;&#x644;&#x645;&#x62D;&#x62F;&#x62F;</button>
  </div>
  <div class="search-bar">
    <input type="text" id="paylogSearchInput" placeholder="&#x627;&#x628;&#x62D;&#x62B; &#x628;&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x623;&#x648; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;..." oninput="filterPaylogTable()">
    <button class="btn-search" style="background:#00897B;" onclick="filterPaylogTable()">&#x628;&#x62D;&#x62B;</button>
  </div>
  <div class="table-wrap">
    <table style="min-width:1100px;">
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
    <h2 id="modalTitle">&#x627;&#x636;&#x627;&#x641;&#x629; &#x637;&#x627;&#x644;&#x628; &#x62C;&#x62F;&#x64A;&#x62F;</h2>
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
    <h2 style="color:#3F51B5;">&#x1F4E5; &#x625;&#x636;&#x627;&#x641;&#x629; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x645;&#x646; Excel</h2>
    <div style="margin-bottom:14px;">
      <label style="display:block;font-size:13px;color:#3F51B5;font-weight:600;margin-bottom:6px;">&#x627;&#x62E;&#x62A;&#x631; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644;</label>
      <select id="genExcelTable" onchange="onGenExcelTableChange()" style="width:100%;padding:10px;border:1.5px solid #C5CAE9;border-radius:9px;font-size:14px;background:#fafafa;">
        <option value="">&mdash; &#x627;&#x62E;&#x62A;&#x631; &mdash;</option>
        <option value="students">&#x642;&#x627;&#x639;&#x62F;&#x629; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x644;&#x628;&#x629;</option>
        <option value="student_groups">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x627;&#x62A;</option>
        <option value="attendance">&#x633;&#x62C;&#x644; &#x627;&#x644;&#x63A;&#x64A;&#x627;&#x628;</option>
        <option value="taqseet">&#x62C;&#x62F;&#x648;&#x644; &#x627;&#x644;&#x62A;&#x642;&#x633;&#x64A;&#x637;</option>
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
    <h2 id="groupModalTitle2" style="color:#0097A7;">&#x627;&#x636;&#x627;&#x641;&#x629; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x62C;&#x62F;&#x64A;&#x62F;&#x629;</h2>
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
  <div class="modal" style="border-top:4px solid #00897B;max-width:600px;">
    <h2 id="paylogModalTitle" style="color:#00695C;">&#x1F4B0; &#x625;&#x636;&#x627;&#x641;&#x629; &#x633;&#x62C;&#x644; &#x62F;&#x641;&#x639;</h2>
    <input type="hidden" id="paylogEditId">
    <div class="form-grid">
      <div class="field"><label style="color:#00695C;">&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; *</label><input id="pl_student_name" placeholder="&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;</label><input id="pl_group_name" placeholder="&#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x62A;&#x627;&#x631;&#x64A;&#x62E;</label><input type="date" id="pl_pay_date" onchange="plFillDay()" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x64A;&#x648;&#x645;</label><input id="pl_day_name" readonly placeholder="&#x627;&#x644;&#x64A;&#x648;&#x645;" style="border-color:#b2dfdb;background:#f5f5f5;"></div>
      <div class="field"><label style="color:#00695C;">&#x646;&#x648;&#x639; &#x627;&#x644;&#x642;&#x633;&#x637;</label><input id="pl_inst_type" placeholder="&#x645;&#x62B;&#x627;&#x644;: 1" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x633;&#x639;&#x631;</label><input type="number" id="pl_price" oninput="plCalcRemaining()" placeholder="0" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x645;&#x62F;&#x641;&#x648;&#x639;</label><input type="number" id="pl_paid" oninput="plCalcRemaining()" placeholder="0" style="border-color:#b2dfdb;background:#f0fdfb;"></div>
      <div class="field"><label style="color:#00695C;">&#x627;&#x644;&#x645;&#x62A;&#x628;&#x642;&#x64A;</label><input type="number" id="pl_remaining" readonly placeholder="0" style="border-color:#b2dfdb;background:#f5f5f5;"></div>
    </div>
    <div class="modal-actions">
      <button class="btn-save" style="background:linear-gradient(135deg,#00897B,#00695C);" onclick="savePaylog()">&#x62D;&#x641;&#x638;</button>
      <button class="btn-cancel" style="background:#e0f2f1;color:#00695C;" onclick="closePaylogModal()">&#x627;&#x644;&#x63A;&#x627;&#x621;</button>
    </div>
  </div>
</div>
<!-- PAYMENT LOG TABLE EDIT MODAL -->
<div class="modal-bg" id="paylogTableEditModal">
<div class="modal" style="border-top:4px solid #FF6B35;max-width:560px;">
<h2 style="color:#E55A2B;">&#9881; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x62C;&#x62F;&#x648;&#x644; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x641;&#x639;</h2>
<div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:2px solid #e0f2f1;padding-bottom:10px;">
<button id="pltab-add-col" onclick="switchPaylogTab('add-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#FF6B35;color:#fff;font-weight:700;cursor:pointer;font-size:13px;">&#43; &#1573;&#1590;&#1575;&#1601;&#1577; &#1593;&#1605;&#1608;&#1583;</button>
<button id="pltab-del-col" onclick="switchPaylogTab('del-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#e0f2f1;color:#00695C;font-weight:700;cursor:pointer;font-size:13px;">&#10060; &#1581;&#1584;&#1601; &#1593;&#1605;&#1608;&#1583;</button>
<button id="pltab-edit-col" onclick="switchPaylogTab('edit-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#e0f2f1;color:#00695C;font-weight:700;cursor:pointer;font-size:13px;">&#9998; &#1578;&#1593;&#1583;&#1610;&#1604; &#1593;&#1606;&#1608;&#1575;&#1606;</button>
</div>
<div id="plpanel-add-col">
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">&#1593;&#1606;&#1608;&#1575;&#1606; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#1575;&#1604;&#1580;&#1583;&#1610;&#1583; *</label><input id="pl_new_col_label" placeholder="&#1605;&#1579;&#1575;&#1604;: &#1605;&#1604;&#1575;&#1581;&#1592;&#1575;&#1578;" style="width:100%;padding:10px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;"></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">&#1605;&#1608;&#1602;&#1593; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#1575;&#1604;&#1580;&#1583;&#1610;&#1583;</label>
<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
<select id="pl_new_col_position" onchange="togglePaylogPositionCol()" style="padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:0 0 auto;">
<option value="end">&#1601;&#1610; &#1575;&#1604;&#1606;&#1607;&#1575;&#1610;&#1577;</option>
<option value="start">&#1601;&#1610; &#1575;&#1604;&#1576;&#1583;&#1575;&#1610;&#1577;</option>
<option value="after">&#1576;&#1593;&#1583; &#1593;&#1605;&#1608;&#1583;:</option>
</select>
<select id="pl_new_col_after" style="display:none;padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:1;"><option value="">&#8212; &#1575;&#1582;&#1578;&#1585; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#8212;</option></select>
</div></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="addPaylogColumn()">&#1573;&#1590;&#1575;&#1601;&#1577; &#1593;&#1605;&#1608;&#1583;</button>
</div></div>
<div id="plpanel-del-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#e53935;">&#1575;&#1582;&#1578;&#1585; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#1604;&#1604;&#1581;&#1584;&#1601; *</label>
<select id="pl_del_col_key" style="width:100%;padding:10px;border:1.5px solid #fce4ec;border-radius:9px;font-size:14px;background:#fff9f9;"><option value="">&#8212; &#1575;&#1582;&#1578;&#1585; &#1593;&#1605;&#1608;&#1583; &#8212;</option></select></div>
<div style="background:#fff3f3;border-radius:8px;padding:10px;font-size:12px;color:#c62828;margin-bottom:12px;">&#9888; &#1578;&#1581;&#1584;&#1610;&#1585;: &#1581;&#1584;&#1601; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#1610;&#1581;&#1584;&#1601; &#1580;&#1605;&#1610;&#1593; &#1576;&#1610;&#1575;&#1606;&#1575;&#1578;&#1607;. &#1604;&#1575; &#1610;&#1605;&#1603;&#1606; &#1575;&#1604;&#1578;&#1585;&#1575;&#1580;&#1593;.</div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:#e53935;" onclick="deletePaylogColumn()">&#1581;&#1584;&#1601; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583;</button>
</div></div>
<div id="plpanel-edit-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#00695C;">&#1575;&#1582;&#1578;&#1585; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; *</label>
<select id="pl_edit_col_key" onchange="fillPaylogEditLabel()" style="width:100%;padding:10px;border:1.5px solid #b2dfdb;border-radius:9px;font-size:14px;background:#f0fdfb;"><option value="">&#8212; &#1575;&#1582;&#1578;&#1585; &#1593;&#1605;&#1608;&#1583; &#8212;</option></select></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#00695C;">&#1575;&#1604;&#1575;&#1587;&#1605; &#1575;&#1604;&#1580;&#1583;&#1610;&#1583; *</label><input id="pl_edit_col_label" placeholder="&#1575;&#1587;&#1605; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583;" style="width:100%;padding:10px;border:1.5px solid #b2dfdb;border-radius:9px;font-size:14px;background:#f0fdfb;"></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#00897B,#00695C);" onclick="updatePaylogColumnLabel()">&#1581;&#1601;&#1592; &#1575;&#1604;&#1593;&#1606;&#1608;&#1575;&#1606;</button>
</div></div>
<div class="modal-actions" style="margin-top:18px;justify-content:center;">
<button class="btn-cancel" style="background:#e0f2f1;color:#00695C;" onclick="closePaylogTableEditModal()">&#1573;&#1594;&#1604;&#1575;&#1602;</button>
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
  var tbodyIds = { students:'studentsBody', groups:'groupsBody2', taqseet:'taqseetBody', attendance:'attendanceBody', paylog:'paylogBody' };
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

function loadTaqseet() {
  fetch('/api/taqseet').then(function(r){return r.json();}).then(function(data){
    allTaqseet = data;
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
  var fields = ['taqseet_method','student_name','course_amount','num_installments',
    'inst1','paid1','date1','inst2','paid2','date2','inst3','paid3','date3','inst4','paid4','date4',
    'inst5','paid5','date5','inst6','paid6','date6','inst7','paid7','date7','inst8','paid8','date8',
    'inst9','paid9','date9','inst10','paid10','date10','inst11','paid11','date11','inst12','paid12','date12',
    'study_hours','start_date'];
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

function openTaqseetColModal() {
  showToast('&#x645;&#x64A;&#x632;&#x629; &#x625;&#x636;&#x627;&#x641;&#x629; &#x639;&#x645;&#x648;&#x62F; &#x645;&#x62E;&#x635;&#x635; &#x642;&#x64A;&#x62F; &#x627;&#x644;&#x62A;&#x637;&#x648;&#x64A;&#x631;', '#FF6B35');
}

function openTaqseetEditModal() {
  showToast('&#x645;&#x64A;&#x632;&#x629; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x62C;&#x62F;&#x648;&#x644; &#x642;&#x64A;&#x62F; &#x627;&#x644;&#x62A;&#x637;&#x648;&#x64A;&#x631;', '#9C27B0');
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
function clearForm(){ ['personal_id','student_name','whatsapp','class_name','old_new_2026','registration_term2_2026','group_name_student','group_online','final_result','level_reached','suitable_level','books_received','teacher','installment1','installment2','installment3','installment4','installment5','mother_phone','father_phone','other_phone','residence','home_address','road','complex'].forEach(k=>{const el=document.getElementById('f_'+k);if(el)el.value='';}); document.getElementById('editId').value=''; } function openAddModal(){clearForm();document.getElementById('modalTitle').innerHTML='&#x627;&#x636;&#x627;&#x641;&#x629; &#x637;&#x627;&#x644;&#x628; &#x62C;&#x62F;&#x64A;&#x62F;';document.getElementById('modal').classList.add('open');}
function openEdit(id){ const s=allStudents.find(x=>x.id===id);if(!s)return; document.getElementById('editId').value=id; document.getElementById('modalTitle').innerHTML='&#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628;'; document.getElementById('f_personal_id').value=s.personal_id||''; document.getElementById('f_student_name').value=s.student_name||''; document.getElementById('f_whatsapp').value=s.whatsapp||''; document.getElementById('f_class_name').value=s.class_name||''; document.getElementById('f_old_new_2026').value=s.old_new_2026||''; document.getElementById('f_registration_term2_2026').value=s.registration_term2_2026||''; document.getElementById('f_group_name_student').value=s.group_name_student||''; document.getElementById('f_group_online').value=s.group_online||''; document.getElementById('f_final_result').value=s.final_result||''; document.getElementById('f_level_reached').value=s.level_reached_2026||''; document.getElementById('f_suitable_level').value=s.suitable_level_2026||''; document.getElementById('f_books_received').value=s.books_received||''; document.getElementById('f_teacher').value=s.teacher_2026||''; document.getElementById('f_installment1').value=s.installment1||''; document.getElementById('f_installment2').value=s.installment2||''; document.getElementById('f_installment3').value=s.installment3||''; document.getElementById('f_installment4').value=s.installment4||''; document.getElementById('f_installment5').value=s.installment5||''; document.getElementById('f_mother_phone').value=s.mother_phone||''; document.getElementById('f_father_phone').value=s.father_phone||''; document.getElementById('f_other_phone').value=s.other_phone||''; document.getElementById('f_residence').value=s.residence||''; document.getElementById('f_home_address').value=s.home_address||''; document.getElementById('f_road').value=s.road||''; document.getElementById('f_complex').value=s.complex_name||''; document.getElementById('f_installment_type').value=s.installment_type||''; populateEditInstallmentSelect(s.installment_type||''); document.getElementById('modal').classList.add('open'); } function closeModal(){document.getElementById('modal').classList.remove('open');}
async function saveStudent(){ const editId=document.getElementById('editId').value; const body={ personal_id:document.getElementById('f_personal_id').value.trim(), student_name:document.getElementById('f_student_name').value.trim(), whatsapp:document.getElementById('f_whatsapp').value.trim(), class_name:document.getElementById('f_class_name').value.trim(), old_new_2026:document.getElementById('f_old_new_2026').value.trim(), registration_term2_2026:document.getElementById('f_registration_term2_2026').value.trim(), group_name_student:document.getElementById('f_group_name_student').value.trim(), group_online:document.getElementById('f_group_online').value.trim(), final_result:document.getElementById('f_final_result').value, level_reached_2026:document.getElementById('f_level_reached').value.trim(), suitable_level_2026:document.getElementById('f_suitable_level').value.trim(), books_received:document.getElementById('f_books_received').value.trim(), teacher_2026:document.getElementById('f_teacher').value.trim(), installment1:document.getElementById('f_installment1').value.trim(), installment2:document.getElementById('f_installment2').value.trim(), installment3:document.getElementById('f_installment3').value.trim(), installment4:document.getElementById('f_installment4').value.trim(), installment5:document.getElementById('f_installment5').value.trim(), mother_phone:document.getElementById('f_mother_phone').value.trim(), father_phone:document.getElementById('f_father_phone').value.trim(), other_phone:document.getElementById('f_other_phone').value.trim(), residence:document.getElementById('f_residence').value.trim(), home_address:document.getElementById('f_home_address').value.trim(), road:document.getElementById('f_road').value.trim(), complex_name:document.getElementById('f_complex').value.trim(), installment_type:document.getElementById('f_installment_type').value.trim(), }; if(!body.personal_id||!body.student_name){showToast('&#x627;&#x644;&#x631;&#x642;&#x645; &#x627;&#x644;&#x634;&#x62E;&#x635;&#x64A; &#x648;&#x627;&#x633;&#x645; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x645;&#x637;&#x644;&#x648;&#x628;&#x627;&#x646;','#e53935');return;} const url=editId?'/api/students/'+editId:'/api/students'; const method=editId?'PUT':'POST'; const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); const data=await res.json(); if(data.ok){closeModal();showToast(editId?'&#x62A;&#x645; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x628;&#x646;&#x62C;&#x627;&#x62D;':'&#x62A;&#x645; &#x627;&#x636;&#x627;&#x641;&#x629; &#x627;&#x644;&#x637;&#x627;&#x644;&#x628; &#x628;&#x646;&#x62C;&#x627;&#x62D;');loadStudents();} else{showToast(data.error||'&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;','#e53935');} } function askDelete(id){deleteTargetId=id;document.getElementById('confirmModal').classList.add('open');document.getElementById('confirmDelBtn').onclick=confirmDelete;}
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
    if(data.ok){closeGroupModal2();showToast(editId?'&#x62A;&#x645; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;':'&#x62A;&#x645; &#x627;&#x636;&#x627;&#x641;&#x629; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;','#00BCD4');loadGroups2();}
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
var studentExcelData=[];function openStudentExcelModal(){studentExcelData=[];document.getElementById("studentExcelFile").value="";document.getElementById("studentExcelFileName").textContent="&#x644;&#x645; &#x64A;&#x62A;&#x645; &#x627;&#x62E;&#x62A;&#x64A;&#x627;&#x631; &#x645;&#x644;&#x641;";document.getElementById("studentExcelPreview").style.display="none";document.getElementById("studentExcelImportBtn").style.display="none";document.getElementById("studentExcelModal").classList.add("open");}function closeStudentExcelModal(){document.getElementById("studentExcelModal").classList.remove("open");}document.addEventListener("DOMContentLoaded",function(){var sf=document.getElementById("studentExcelFile");if(sf){sf.addEventListener("change",function(e){var file=e.target.files[0];if(!file)return;document.getElementById("studentExcelFileName").textContent=file.name;var reader=new FileReader();reader.onload=function(ev){var data=ev.target.result;var rows=data.split(String.fromCharCode(10)).filter(function(r){return r.trim()!="";});if(rows.length<2){showToast("&#x627;&#x644;&#x645;&#x644;&#x641; &#x641;&#x627;&#x631;&#x63A;","#e53935");return;}var sep=rows[0].indexOf(String.fromCharCode(9))>-1?"\t":",",parsed=[];for(var i=1;i<rows.length;i++){var cols=rows[i].split(sep);if(cols.length<2)continue;parsed.push({personal_id:(cols[0]||"").trim(),student_name:(cols[1]||"").trim(),whatsapp:(cols[2]||"").trim(),final_result:(cols[3]||"").trim(),level_reached_2026:(cols[4]||"").trim(),teacher_2026:(cols[5]||"").trim(),mother_phone:(cols[6]||"").trim(),father_phone:(cols[7]||"").trim(),other_phone:(cols[8]||"").trim(),residence:(cols[9]||"").trim(),home_address:(cols[10]||"").trim(),road:(cols[11]||"").trim(),complex_name:(cols[12]||"").trim()});}studentExcelData=parsed;document.getElementById("studentExcelCount").textContent="&#x62A;&#x645; &#x642;&#x631;&#x627;&#x621;&#x629; "+parsed.length+" &#x637;&#x627;&#x644;&#x628;. &#x627;&#x636;&#x63A;&#x637; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;.";document.getElementById("studentExcelPreview").style.display="block";document.getElementById("studentExcelImportBtn").style.display="inline-block";};reader.readAsText(file,"UTF-8");});}var gf=document.getElementById("groupExcelFile");if(gf){gf.addEventListener("change",function(e){var file=e.target.files[0];if(!file)return;document.getElementById("groupExcelFileName").textContent=file.name;var reader=new FileReader();reader.onload=function(ev){var data=ev.target.result;var rows=data.split(String.fromCharCode(10)).filter(function(r){return r.trim()!="";});if(rows.length<2){showToast("&#x627;&#x644;&#x645;&#x644;&#x641; &#x641;&#x627;&#x631;&#x63A;","#e53935");return;}var sep=rows[0].indexOf(String.fromCharCode(9))>-1?"\t":",",parsed=[];for(var i=1;i<rows.length;i++){var cols=rows[i].split(sep);if(cols.length<2)continue;parsed.push({group_name:(cols[0]||"").trim(),teacher_name:(cols[1]||"").trim(),level_course:(cols[2]||"").trim(),last_reached:(cols[3]||"").trim(),study_time:(cols[4]||"").trim(),ramadan_time:(cols[5]||"").trim(),online_time:(cols[6]||"").trim(),group_link:(cols[7]||"").trim(),session_duration:(cols[8]||"").trim()});}groupExcelData=parsed;document.getElementById("groupExcelCount").textContent="&#x62A;&#x645; &#x642;&#x631;&#x627;&#x621;&#x629; "+parsed.length+" &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629;. &#x627;&#x636;&#x63A;&#x637; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;.";document.getElementById("groupExcelPreview").style.display="block";document.getElementById("groupExcelImportBtn").style.display="inline-block";};reader.readAsText(file,"UTF-8");});}});function importStudentsFromExcel(){if(!studentExcelData.length){showToast("&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;","#e53935");return;}var btn=document.getElementById("studentExcelImportBtn");btn.disabled=true;btn.textContent="&#x62C;&#x627;&#x631;&#x64A; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;...";fetch("/api/students/bulk",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({rows:studentExcelData})}).then(function(r){return r.text();}).then(function(txt){var data;try{data=JSON.parse(txt);}catch(e){showToast("&#x627;&#x646;&#x62A;&#x647;&#x62A; &#x627;&#x644;&#x62C;&#x644;&#x633;&#x629;&#x60C; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x62E;&#x648;&#x644; &#x645;&#x62C;&#x62F;&#x62F;&#x627;","#e53935");btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";return;}if(data.ok){closeStudentExcelModal();showToast("&#x62A;&#x645; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; "+data.imported+" &#x637;&#x627;&#x644;&#x628; &#x628;&#x646;&#x62C;&#x627;&#x62D;");loadStudents();}else{showToast("&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;","#e53935");}btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";}).catch(function(){showToast("&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627; &#x641;&#x64A; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;","#e53935");btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";});}var groupExcelData=[];function openGroupExcelModal(){groupExcelData=[];document.getElementById("groupExcelFile").value="";document.getElementById("groupExcelFileName").textContent="&#x644;&#x645; &#x64A;&#x62A;&#x645; &#x627;&#x62E;&#x62A;&#x64A;&#x627;&#x631; &#x645;&#x644;&#x641;";document.getElementById("groupExcelPreview").style.display="none";document.getElementById("groupExcelImportBtn").style.display="none";document.getElementById("groupExcelModal").classList.add("open");}function closeGroupExcelModal(){document.getElementById("groupExcelModal").classList.remove("open");}function importGroupsFromExcel(){if(!groupExcelData.length){showToast("&#x644;&#x627; &#x62A;&#x648;&#x62C;&#x62F; &#x628;&#x64A;&#x627;&#x646;&#x627;&#x62A;","#e53935");return;}var btn=document.getElementById("groupExcelImportBtn");btn.disabled=true;btn.textContent="&#x62C;&#x627;&#x631;&#x64A; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;...";fetch("/api/groups/bulk",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({rows:groupExcelData})}).then(function(r){return r.text();}).then(function(txt){var data;try{data=JSON.parse(txt);}catch(e){showToast("&#x627;&#x646;&#x62A;&#x647;&#x62A; &#x627;&#x644;&#x62C;&#x644;&#x633;&#x629;&#x60C; &#x633;&#x62C;&#x644; &#x627;&#x644;&#x62F;&#x62E;&#x648;&#x644; &#x645;&#x62C;&#x62F;&#x62F;&#x627;","#e53935");btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";return;}if(data.ok){closeGroupExcelModal();showToast("&#x62A;&#x645; &#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F; "+data.imported+" &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x628;&#x646;&#x62C;&#x627;&#x62D;","#00BCD4");loadGroups2();}else{showToast("&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627;","#e53935");}btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";}).catch(function(){showToast("&#x62D;&#x62F;&#x62B; &#x62E;&#x637;&#x627; &#x641;&#x64A; &#x627;&#x644;&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;","#e53935");btn.disabled=false;btn.textContent="&#x627;&#x633;&#x62A;&#x64A;&#x631;&#x627;&#x62F;";});}
loadGroups2();
// --- Payment Log (sijjil addaf3) -------------------------------------
var allPaylog = [];
var allPaylogColumns = [];
function loadPaymentLog(){
  Promise.all([fetch('/api/payment-log',{credentials:'include'}),fetch('/api/paylog-columns',{credentials:'include'})]).then(function(rs){
    return Promise.all([rs[0].json(),rs[1].json()]);
  }).then(function(results){
    allPaylog = results[0].rows || [];
    allPaylogColumns = results[1].columns || [];
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
function _paylogFmt(val,key){
  if(val==null || val==='') return '-';
  if(key==='price' || key==='paid' || key==='remaining'){
    var n = parseFloat(val); if(isNaN(n)) return val;
    return n.toFixed(2);
  }
  return val;
}
function renderPaylogTable(list){
  var body = document.getElementById('paylogBody');
  if(!body) return;
  var colCount = allPaylogColumns.length + 3;
  if(!list || !list.length){
    body.innerHTML = '<tr><td colspan="'+colCount+'" class="no-data">\u0644\u0627 \u062a\u0648\u062c\u062f \u0633\u062c\u0644\u0627\u062a</td></tr>';
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
      else if(key==='remaining'){
        var num = parseFloat(val)||0; var color = num>0 ? '#c62828' : '#2E7D32';
        html += '<td style="font-weight:700;color:'+color+';text-align:center;">'+_paylogFmt(val,key)+'</td>';
      }
      else { html += '<td>'+_paylogFmt(val,key)+'</td>'; }
    }
    html += '<td><button class="action-btn btn-edit" style="color:#00695C;" onclick="openPaylogEdit('+r.id+')">✎</button><button class="action-btn btn-del" onclick="askPaylogDelete('+r.id+')">🗑</button></td></tr>';
  }
  body.innerHTML = html;
  applyFreezeToTable('paylog');
}
function filterPaylogTable(){
  var q = (document.getElementById('paylogSearchInput').value || '').toLowerCase();
  if(!q){ renderPaylogTable(allPaylog); return; }
  renderPaylogTable(allPaylog.filter(function(r){
    return (String(r.student_name||'').toLowerCase().indexOf(q) > -1) ||
           (String(r.group_name||'').toLowerCase().indexOf(q) > -1);
  }));
}
function plClearForm(){
  var ids = ['student_name','group_name','pay_date','day_name','inst_type','price','paid','remaining'];
  for(var i=0;i<ids.length;i++){ var el=document.getElementById('pl_'+ids[i]); if(el) el.value=''; }
  document.getElementById('paylogEditId').value = '';
}
function plFillDay(){
  var d = document.getElementById('pl_pay_date').value; if(!d) return;
  var days=["\u0627\u0644\u0623\u062d\u062f","\u0627\u0644\u0627\u062b\u0646\u064a\u0646","\u0627\u0644\u062b\u0644\u0627\u062b\u0627\u0621","\u0627\u0644\u0623\u0631\u0628\u0639\u0627\u0621","\u0627\u0644\u062e\u0645\u064a\u0633","\u0627\u0644\u062c\u0645\u0639\u0629","\u0627\u0644\u0633\u0628\u062a"];
  document.getElementById('pl_day_name').value = days[new Date(d).getDay()];
}
function plCalcRemaining(){
  var p = parseFloat(document.getElementById('pl_price').value)||0;
  var pd = parseFloat(document.getElementById('pl_paid').value)||0;
  document.getElementById('pl_remaining').value = (p-pd).toFixed(2);
}
function openAddPaylogModal(){
  plClearForm();
  document.getElementById('paylogModalTitle').textContent = '\u0625\u0636\u0627\u0641\u0629 \u0633\u062c\u0644 \u062f\u0641\u0639';
  document.getElementById('paylogModal').classList.add('open');
}
function openPaylogEdit(id){
  var r = null;
  for(var i=0;i<allPaylog.length;i++){ if(allPaylog[i].id===id){ r = allPaylog[i]; break; } }
  if(!r) return;
  document.getElementById('paylogEditId').value = id;
  document.getElementById('paylogModalTitle').textContent = '\u062a\u0639\u062f\u064a\u0644 \u0633\u062c\u0644 \u0627\u0644\u062f\u0641\u0639';
  document.getElementById('pl_student_name').value = r.student_name || '';
  document.getElementById('pl_group_name').value   = r.group_name   || '';
  document.getElementById('pl_pay_date').value     = r.pay_date     || '';
  document.getElementById('pl_day_name').value     = r.day_name     || '';
  document.getElementById('pl_inst_type').value    = r.inst_type    || '';
  document.getElementById('pl_price').value        = (r.price!=null ? r.price : '');
  document.getElementById('pl_paid').value         = (r.paid!=null ? r.paid : '');
  document.getElementById('pl_remaining').value    = (r.remaining!=null ? r.remaining : '');
  document.getElementById('paylogModal').classList.add('open');
}
function closePaylogModal(){ document.getElementById('paylogModal').classList.remove('open'); }
function savePaylog(){
  var editId = document.getElementById('paylogEditId').value;
  var price = parseFloat(document.getElementById('pl_price').value) || 0;
  var paid  = parseFloat(document.getElementById('pl_paid').value) || 0;
  var body = {
    student_name: document.getElementById('pl_student_name').value.trim(),
    group_name:   document.getElementById('pl_group_name').value.trim(),
    pay_date:     document.getElementById('pl_pay_date').value.trim(),
    day_name:     document.getElementById('pl_day_name').value.trim(),
    inst_type:    document.getElementById('pl_inst_type').value.trim(),
    price: price, paid: paid, remaining: price - paid
  };
  if(!body.student_name){ showToast('\u0627\u0633\u0645 \u0627\u0644\u0637\u0627\u0644\u0628 \u0645\u0637\u0644\u0648\u0628','#e53935'); return; }
  var url = editId ? '/api/payment-log/'+editId : '/api/payment-log';
  var method = editId ? 'PUT' : 'POST';
  fetch(url,{method:method,headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(body)})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closePaylogModal(); showToast(editId?'\u062a\u0645 \u062a\u0639\u062f\u064a\u0644 \u0627\u0644\u0633\u062c\u0644':'\u062a\u0645 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0633\u062c\u0644','#00897B'); loadPaymentLog(); }
      else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
    }).catch(function(){ showToast('\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); });
}
var _paylogDelId = null;
function askPaylogDelete(id){
  if(!confirm('\u0647\u0644 \u062a\u0631\u064a\u062f \u062d\u0630\u0641 \u0647\u0630\u0627 \u0627\u0644\u0633\u062c\u0644\u061f')) return;
  fetch('/api/payment-log/'+id,{method:'DELETE',credentials:'include'}).then(function(r){return r.json();}).then(function(d){
    if(d.ok){ showToast('\u062a\u0645 \u0627\u0644\u062d\u0630\u0641','#e53935'); loadPaymentLog(); }
    else { showToast(d.error||'\u062d\u062f\u062b \u062e\u0637\u0623','#e53935'); }
  });
}
// ---- Paylog column management ----
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
    if(tabs[i]===tab){
      if(b){ b.style.background = '#FF6B35'; b.style.color = '#fff'; }
      if(p) p.style.display = 'block';
    } else {
      if(b){ b.style.background = '#e0f2f1'; b.style.color = '#00695C'; }
      if(p) p.style.display = 'none';
    }
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
  var base = label.replace(/\s+/g,'_').toLowerCase();
  var key = base.replace(/[^a-z0-9_]/g,'');
  if(!/^[a-z_][a-z0-9_]*$/.test(key)){ key = 'col_' + Date.now(); }
  var position = document.getElementById('pl_new_col_position').value;
  var after_col = document.getElementById('pl_new_col_after').value;
  fetch('/api/paylog-columns',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({col_key:key,col_label:label,position:position,after_col:after_col})})
    .then(function(r){return r.json();}).then(function(d){
      if(d.ok){ closePaylogTableEditModal(); showToast('\u062a\u0645 \u0625\u0636\u0627\u0641\u0629 \u0627\u0644\u0639\u0645\u0648\u062f \u0628\u0646\u062c\u0627\u062d','#00897B'); loadPaymentLog(); }
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
  var done = 0;
  var total = batch.length;
  var statusEl = document.getElementById('attendanceExcelStatus');
  function sendNext(idx) {
    if(idx >= total) {
      statusEl.textContent = '\u062A\u0645 \u0627\u0633\u062A\u064A\u0631\u0627\u062F ' + done + ' \u0633\u062C\u0644 \u0628\u0646\u062C\u0627\u062D!';
      loadAttendance();
      setTimeout(closeAttendanceExcelModal, 1500);
      return;
    }
    fetch('/api/attendance', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(batch[idx])})
      .then(function(r){ return r.json(); }).then(function(d){
        if(d.ok) done++;
        statusEl.textContent = '\u062C\u0627\u0631\u064A \u0627\u0644\u0627\u0633\u062A\u064A\u0631\u0627\u062F... ' + (idx+1) + ' / ' + total;
        sendNext(idx+1);
      }).catch(function(){ sendNext(idx+1); });
  }
  sendNext(0);
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
      {key:"start_date", ar:"\u062A\u0627\u0631\u064A\u062E \u0627\u0644\u0628\u062F\u0621"}
    ]
  },
  payment_log: {
    title: "\u0633\u062c\u0644 \u0627\u0644\u062f\u0641\u0639",
    refresh: "loadPaymentLog",
    fields: [
      {key:"student_name", ar:"\u0627\u0633\u0645 \u0627\u0644\u0637\u0627\u0644\u0628"},
      {key:"group_name", ar:"\u0627\u0644\u0645\u062c\u0645\u0648\u0639\u0629"},
      {key:"pay_date", ar:"\u0627\u0644\u062a\u0627\u0631\u064a\u062e"},
      {key:"day_name", ar:"\u0627\u0644\u064a\u0648\u0645"},
      {key:"inst_type", ar:"\u0646\u0648\u0639 \u0627\u0644\u0642\u0633\u0637"},
      {key:"price", ar:"\u0627\u0644\u0633\u0639\u0631"},
      {key:"paid", ar:"\u0627\u0644\u0645\u062f\u0641\u0648\u0639"},
      {key:"remaining", ar:"\u0627\u0644\u0645\u062a\u0628\u0642\u064a"}
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
    .replace(/[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06ED]/g,'')
    .replace(/[\u200B-\u200F\u202A-\u202E\u2060\uFEFF]/g,'')
    .replace(/[\u0623\u0625\u0622\u0671]/g,'\u0627')
    .replace(/\u0629/g,'\u0647')
    .replace(/\u0649/g,'\u064A')
    .replace(/\s+/g,' ')
    .trim();
}
function mapGenericRow(headers, row, defs) {
  var result = {};
  for(var i=0; i<headers.length; i++){
    var h = _arNorm(headers[i]); if(!h) continue;
    for(var j=0; j<defs.fields.length; j++){
      var f = defs.fields[j];
      if(h === f.key || h === _arNorm(f.ar)){
        result[f.key] = String(row[i]==null?'':row[i]);
        break;
      }
    }
  }
  return result;
}
function importGenericFromExcel() {
  var tbl = document.getElementById('genExcelTable').value;
  var defs = IMPORT_DEFS[tbl];
  if(!defs || !genExcelRows.length) return;
  var mapped = genExcelRows.map(function(r){ return mapGenericRow(genExcelHeaders, r, defs); });
  var btn = document.getElementById('genExcelImportBtn');
  var statusEl = document.getElementById('genExcelStatus');
  btn.disabled = true;
  btn.textContent = "\u062C\u0627\u0631\u064A \u0627\u0644\u0627\u0633\u062A\u064A\u0631\u0627\u062F...";
  fetch('/api/import', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({table: tbl, rows: mapped})})
    .then(function(r){ return r.json(); })
    .then(function(d){
      btn.disabled = false;
      btn.textContent = "\u0627\u0633\u062A\u064A\u0631\u0627\u062F";
      if(d && d.ok){
        var ins = d.imported || 0, ign = d.ignored || 0, err = d.errors || 0;
        var parts = ["\u062A\u0645 \u0627\u0644\u0625\u062F\u0631\u0627\u062C: " + ins];
        if(ign) parts.push("\u0645\u062A\u062C\u0627\u0647\u0644: " + ign);
        if(err) parts.push("\u062E\u0637\u0623: " + err);
        statusEl.textContent = parts.join(" \u2014 ");
        if(defs.refresh && typeof window[defs.refresh] === 'function') { try { window[defs.refresh](); } catch(e) {} }
        if(typeof showToast === 'function') showToast(parts.join(" \u2014 "));
        if(ins > 0 && ign === 0 && err === 0) {
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
    db = get_db()
    rows = db.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    return jsonify({"students": [dict(r) for r in rows]})

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
        is_visible INTEGER DEFAULT 1)""")
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


# --- Payment Log (سجل الدفع) ----------------------------------------------

def _payment_log_writable_cols(db):
    cols = [r[1] for r in db.execute("PRAGMA table_info(payment_log)").fetchall()]
    return [c for c in cols if c not in ("id", "created_at")]

@app.route("/api/payment-log", methods=["GET"])
@login_required
def api_payment_log_get():
    db = get_db()
    rows = db.execute("SELECT * FROM payment_log ORDER BY id DESC").fetchall()
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
        cols = _payment_log_writable_cols(db)
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


@app.route('/api/attendance', methods=['GET'])
@login_required
def api_attendance_get():
    db = get_db()
    rows = db.execute("SELECT * FROM attendance ORDER BY id DESC").fetchall()
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
    <h2 id="modalTitle">&#x627;&#x636;&#x627;&#x641;&#x629; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x62C;&#x62F;&#x64A;&#x62F;&#x629;</h2>
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
function openAddModal(){clearForm();document.getElementById('modalTitle').innerHTML='&#x627;&#x636;&#x627;&#x641;&#x629; &#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x62C;&#x62F;&#x64A;&#x62F;&#x629;';document.getElementById('modal').classList.add('open');}
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
  if(data.ok){closeModal();showToast(editId?'&#x62A;&#x645; &#x62A;&#x639;&#x62F;&#x64A;&#x644; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x628;&#x646;&#x62C;&#x627;&#x62D;':'&#x62A;&#x645; &#x627;&#x636;&#x627;&#x641;&#x629; &#x627;&#x644;&#x645;&#x62C;&#x645;&#x648;&#x639;&#x629; &#x628;&#x646;&#x62C;&#x627;&#x62D;');loadGroups();}
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
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT group_name_student FROM students WHERE group_name_student IS NOT NULL AND group_name_student != '' ORDER BY group_name_student"
    ).fetchall()
    groups = {}
    for row in rows:
        gname = row[0]
        students = db.execute(
            "SELECT id, student_name, personal_id, whatsapp FROM students WHERE group_name_student=? ORDER BY student_name",
            (gname,)
        ).fetchall()
        groups[gname] = [dict(s) for s in students]
    return jsonify(groups)

@app.route("/api/attendance/check", methods=["GET"])
@login_required
def api_attendance_check():
    group_name = request.args.get("group", "").strip()
    att_date = request.args.get("date", "").strip()
    if not group_name or not att_date:
        return jsonify({"exists": False, "records": []})
    db = get_db()
    rows = db.execute(
        "SELECT * FROM attendance WHERE group_name=? AND attendance_date=? ORDER BY id ASC",
        (group_name, att_date)
    ).fetchall()
    return jsonify({"exists": len(rows) > 0, "records": [dict(r) for r in rows]})

@app.route("/api/dashboard/stats", methods=["GET"])
@login_required
def api_dashboard_stats():
    db = get_db()
    def _count_any(cols, keywords, table="students"):
        if not keywords: return 0
        clauses, params = [], []
        for kw in keywords:
            pattern = "%" + kw.lower() + "%"
            for col in cols:
                clauses.append("lower(" + col + ") LIKE ?")
                params.append(pattern)
        sql = "SELECT COUNT(DISTINCT id) FROM " + table + " WHERE " + " OR ".join(clauses)
        try:
            return db.execute(sql, tuple(params)).fetchone()[0] or 0
        except Exception:
            return 0
    english_kws = ["\u0625\u0646\u062C\u0644\u064A\u0632\u064A", "\u0627\u0646\u062C\u0644\u064A\u0632\u064A", "english"]
    math_kws    = ["\u0631\u064A\u0627\u0636\u064A\u0627\u062A", "math"]
    student_cols = ("group_name_student", "class_name", "teacher_2026", "group_online")
    english_students = _count_any(student_cols, english_kws)
    math_students    = _count_any(student_cols, math_kws)
    try:
        groups = db.execute("SELECT COUNT(*) FROM student_groups").fetchone()[0] or 0
    except Exception:
        groups = 0
    try:
        teachers = db.execute(
            "SELECT COUNT(DISTINCT teacher_name) FROM student_groups "
            "WHERE teacher_name IS NOT NULL AND teacher_name<>''"
        ).fetchone()[0] or 0
    except Exception:
        teachers = 0
    try:
        staff = db.execute(
            "SELECT COUNT(*) FROM users WHERE role IS NOT NULL AND role<>'' "
            "AND role<>'admin' AND role<>'teacher'"
        ).fetchone()[0] or 0
    except Exception:
        staff = 0
    try:
        english_levels = db.execute(
            "SELECT COUNT(DISTINCT level_course) FROM student_groups "
            "WHERE level_course IS NOT NULL AND level_course<>'' AND ("
            "lower(level_course) LIKE ? OR level_course LIKE ? OR level_course LIKE ?)",
            ("%english%", "%\u0625\u0646\u062C\u0644\u064A\u0632\u064A%", "%\u0627\u0646\u062C\u0644\u064A\u0632\u064A%")
        ).fetchone()[0] or 0
    except Exception:
        english_levels = 0
    STATUS_PRESENT = "\u062D\u0627\u0636\u0631"
    STATUS_ABSENT  = "\u063A\u0627\u0626\u0628"
    STATUS_LATE    = "\u0645\u062A\u0623\u062E\u0631"
    try:
        total_att = db.execute(
            "SELECT COUNT(*) FROM attendance WHERE status IN (?,?,?)",
            (STATUS_PRESENT, STATUS_ABSENT, STATUS_LATE)
        ).fetchone()[0] or 0
        present_att = db.execute(
            "SELECT COUNT(*) FROM attendance WHERE status=?",
            (STATUS_PRESENT,)
        ).fetchone()[0] or 0
        violations = db.execute(
            "SELECT COUNT(*) FROM attendance WHERE status IN (?,?)",
            (STATUS_ABSENT, STATUS_LATE)
        ).fetchone()[0] or 0
    except Exception:
        total_att = present_att = violations = 0
    attendance_rate = round(present_att / total_att * 100, 1) if total_att else 0.0
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
    group_name = request.args.get("group", "").strip()
    db = get_db()
    if group_name:
        rows = db.execute(
            "SELECT student_name, status FROM attendance "
            "WHERE group_name=? AND student_name IS NOT NULL AND student_name<>''",
            (group_name,)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT student_name, status FROM attendance "
            "WHERE student_name IS NOT NULL AND student_name<>''"
        ).fetchall()
    STATUS_PRESENT = "\u062D\u0627\u0636\u0631"
    STATUS_ABSENT  = "\u063A\u0627\u0626\u0628"
    STATUS_LATE    = "\u0645\u062A\u0623\u062E\u0631"
    stats = {}
    for r in rows:
        name = r["student_name"]
        if not name:
            continue
        s = stats.setdefault(name, {"present": 0, "absent": 0, "late": 0, "total": 0})
        s["total"] += 1
        st = (r["status"] or "").strip()
        if st == STATUS_PRESENT:
            s["present"] += 1
        elif st == STATUS_ABSENT:
            s["absent"] += 1
        elif st == STATUS_LATE:
            s["late"] += 1
    for name, s in stats.items():
        s["pct"] = round(s["present"] / s["total"] * 100, 1) if s["total"] else 0.0
    return jsonify({"ok": True, "stats": stats})

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
    d = request.get_json()
    db = get_db()
    db.execute("""UPDATE taqseet SET
        taqseet_method=?, student_name=?, course_amount=?, num_installments=?,
        inst1=?, paid1=?, date1=?, inst2=?, paid2=?, date2=?, inst3=?, paid3=?, date3=?, inst4=?, paid4=?, date4=?,
        inst5=?, paid5=?, date5=?, inst6=?, paid6=?, date6=?, inst7=?, paid7=?, date7=?, inst8=?, paid8=?, date8=?,
        inst9=?, paid9=?, date9=?, inst10=?, paid10=?, date10=?, inst11=?, paid11=?, date11=?, inst12=?, paid12=?, date12=?,
        study_hours=?, start_date=?
        WHERE id=?""",
    (d.get('taqseet_method',''), d.get('student_name',''), d.get('course_amount',''),
     d.get('num_installments',''),
     d.get('inst1',''), d.get('paid1',''), d.get('date1',''), d.get('inst2',''), d.get('paid2',''), d.get('date2',''),
     d.get('inst3',''), d.get('paid3',''), d.get('date3',''), d.get('inst4',''), d.get('paid4',''), d.get('date4',''),
     d.get('inst5',''), d.get('paid5',''), d.get('date5',''), d.get('inst6',''), d.get('paid6',''), d.get('date6',''),
     d.get('inst7',''), d.get('paid7',''), d.get('date7',''), d.get('inst8',''), d.get('paid8',''), d.get('date8',''),
     d.get('inst9',''), d.get('paid9',''), d.get('date9',''), d.get('inst10',''), d.get('paid10',''), d.get('date10',''),
     d.get('inst11',''), d.get('paid11',''), d.get('date11',''), d.get('inst12',''), d.get('paid12',''), d.get('date12',''),
     d.get('study_hours',''), d.get('start_date',''), row_id))
    db.commit()
    return jsonify({"ok": True})

@app.route('/api/taqseet/<int:row_id>', methods=['DELETE'])
@login_required
def api_taqseet_delete(row_id):
    db = get_db()
    db.execute("DELETE FROM taqseet WHERE id=?", (row_id,))
    db.commit()
    return jsonify({"ok": True})


@app.route('/api/payments/<int:student_id>/<int:inst_num>', methods=['PUT'])
@login_required
def api_payment_put(student_id, inst_num):
    db = get_db()
    data = request.get_json()
    inst_type = data.get('inst_type','')
    price = data.get('price', 0)
    paid = data.get('paid', 0)
    db.execute("""INSERT INTO student_payments(student_id,inst_num,inst_type,price,paid) VALUES(?,?,?,?,?)
        ON CONFLICT(student_id,inst_num) DO UPDATE SET inst_type=EXCLUDED.inst_type, price=EXCLUDED.price, paid=EXCLUDED.paid""",
        (student_id, inst_num, inst_type, price, paid))
    db.commit()
    # Sync paid amount to taqseet table
    student_row = db.execute("SELECT student_name,group_name_student,installment_type FROM students WHERE id=?", (student_id,)).fetchone()
    if student_row and student_row[2]:
        paid_col = "paid" + str(inst_num)
        db.execute("UPDATE taqseet SET " + paid_col + "=? WHERE taqseet_method=?",
                   (str(paid), str(student_row[2])))
        db.commit()
    # Mirror the saved payment into payment_log (سجل الدفع), one row per student.
    try:
        import datetime as _dt
        pay_date = (data.get('pay_date') or '').strip()
        day_name = (data.get('day_name') or '').strip()
        if not pay_date:
            pay_date = _dt.date.today().isoformat()
        if not day_name:
            ar_days = [
                "\u0627\u0644\u0627\u062b\u0646\u064a\u0646",
                "\u0627\u0644\u062b\u0644\u0627\u062b\u0627\u0621",
                "\u0627\u0644\u0623\u0631\u0628\u0639\u0627\u0621",
                "\u0627\u0644\u062e\u0645\u064a\u0633",
                "\u0627\u0644\u062c\u0645\u0639\u0629",
                "\u0627\u0644\u0633\u0628\u062a",
                "\u0627\u0644\u0623\u062d\u062f",
            ]
            try:
                day_name = ar_days[_dt.date.fromisoformat(pay_date).weekday()]
            except Exception:
                day_name = ""
        sname = (student_row[0] if student_row else "") or ""
        gname = (student_row[1] if student_row else "") or ""
        try:
            remaining = float(price or 0) - float(paid or 0)
        except Exception:
            remaining = 0
        db.execute("""INSERT INTO payment_log(student_id,student_name,group_name,pay_date,day_name,inst_type,price,paid,remaining)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(student_id) DO UPDATE SET
                student_name=EXCLUDED.student_name,
                group_name=EXCLUDED.group_name,
                pay_date=EXCLUDED.pay_date,
                day_name=EXCLUDED.day_name,
                inst_type=EXCLUDED.inst_type,
                price=EXCLUDED.price,
                paid=EXCLUDED.paid,
                remaining=EXCLUDED.remaining""",
            (student_id, sname, gname, pay_date, day_name, str(inst_type), price, paid, remaining))
        db.commit()
    except Exception:
        pass  # Log mirroring is best-effort; don't fail the core save.
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
    "payment_log": [
        "student_name","group_name","pay_date","day_name",
        "inst_type","price","paid","remaining",
    ],
}

IMPORT_TABLE_SQL = {
    "students": "INSERT OR IGNORE INTO students",
    "student_groups": "INSERT INTO student_groups",
    "attendance": "INSERT INTO attendance",
    "taqseet": "INSERT INTO taqseet",
    "payment_log": "INSERT INTO payment_log",
}

@app.route('/api/import', methods=['POST'])
@login_required
def api_import():
    d = request.get_json() or {}
    table = d.get('table', '')
    rows = d.get('rows', [])
    fields = IMPORT_TABLE_FIELDS.get(table)
    if not fields:
        return jsonify({"ok": False, "error": "unknown table"}), 400
    db = get_db()
    # Filter to columns that actually exist in the live table schema.
    # Prevents every row from failing when the hardcoded list drifts from
    # the deployed DB (e.g. a column was never migrated, or was dropped via the UI).
    live_cols = {r[1] for r in db.execute("PRAGMA table_info(" + table + ")").fetchall()}
    fields = [f for f in fields if f in live_cols]
    if not fields:
        return jsonify({"ok": False, "error": "no matching columns in table " + table}), 400
    imported = 0
    ignored = 0
    errors = 0
    last_error = ""
    cols = ",".join(fields)
    placeholders = ",".join(["?"] * len(fields))
    sql = IMPORT_TABLE_SQL[table] + " (" + cols + ") VALUES (" + placeholders + ")"
    for r in rows:
        try:
            values = tuple(str(r.get(f, "") or "") for f in fields)
            cur = db.execute(sql, values)
            if cur.rowcount > 0:
                imported += 1
            else:
                ignored += 1
        except Exception as ex:
            errors += 1
            last_error = str(ex)
    db.commit()
    return jsonify({
        "ok": True, "imported": imported, "ignored": ignored,
        "errors": errors, "received": len(rows), "last_error": last_error,
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
    db = get_db()
    rows = db.execute(
        "SELECT DISTINCT group_name FROM attendance "
        "WHERE group_name IS NOT NULL AND group_name != '' "
        "ORDER BY group_name"
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
