# Mindex Portal - v4 Extended Fields
from flask import Flask, render_template_string, request, jsonify, session, redirect, g
import sqlite3, hashlib, os, urllib.request, csv, io
from datetime import date
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mindx2026secret")
DB = os.environ.get("DB_PATH", "mindx.db")

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db: db.close()

def hp(p): return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    db = sqlite3.connect(DB)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,name TEXT,role TEXT,department TEXT);
    CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,name TEXT,group_name TEXT,teacher TEXT,whatsapp TEXT,level TEXT,zoom_link TEXT,monthly_fee REAL DEFAULT 35,status TEXT DEFAULT 'active',group_name2 TEXT,schedule_time TEXT,schedule_time_ramadan TEXT,schedule_days TEXT,group_online TEXT,schedule_time_online TEXT,schedule_days_online TEXT,zoom_link_online TEXT,attendance_summary TEXT,absence_rate TEXT,delay_rate TEXT,teacher_name TEXT,next_level TEXT,final_result TEXT,student_progress TEXT,level_suitable TEXT,book_received TEXT,notes_2026 TEXT,registration_status TEXT,old_new_2026 TEXT,final_result_2026 TEXT,installment1 TEXT,installment2 TEXT,installment3 TEXT,installment4 TEXT,installment5 TEXT,total_paid TEXT,remaining_amount TEXT,mother_phone TEXT,father_phone TEXT,other_phone TEXT,residence TEXT,home_address TEXT,road TEXT,complex_name TEXT);
    CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY,student_name TEXT,group_name TEXT,date TEXT,status TEXT);
    CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,student_name TEXT,amount REAL,status TEXT DEFAULT 'pending',date TEXT,notes TEXT);
    CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,title TEXT,department TEXT,assigned_to TEXT,status TEXT DEFAULT 'pending',priority TEXT DEFAULT 'medium',due_date TEXT,created_date TEXT,notes TEXT);
    CREATE TABLE IF NOT EXISTS violations(id INTEGER PRIMARY KEY,student_name TEXT,title TEXT,description TEXT,points INTEGER DEFAULT 1,status TEXT DEFAULT 'open',date TEXT);
    CREATE TABLE IF NOT EXISTS points(id INTEGER PRIMARY KEY,student_name TEXT,reason TEXT,points INTEGER DEFAULT 5,date TEXT);
    CREATE TABLE IF NOT EXISTS faq(id INTEGER PRIMARY KEY,question TEXT,answer TEXT,department TEXT);
    CREATE TABLE IF NOT EXISTS groups_tbl(id INTEGER PRIMARY KEY,name TEXT,teacher TEXT,subject TEXT,level TEXT,zoom_link TEXT,schedule TEXT);
CREATE TABLE IF NOT EXISTS evaluations(id INTEGER PRIMARY KEY,student_name TEXT,group_name TEXT,teacher TEXT,subject TEXT,score INTEGER DEFAULT 0,max_score INTEGER DEFAULT 100,notes TEXT,date TEXT);
CREATE TABLE IF NOT EXISTS curriculum(id INTEGER PRIMARY KEY,group_name TEXT,teacher TEXT,subject TEXT,week TEXT,topic TEXT,status TEXT DEFAULT 'pending',date TEXT,notes TEXT);
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,title TEXT,description TEXT,date TEXT,time TEXT,location TEXT,target TEXT DEFAULT 'all',created_by TEXT);
    """)
    users = [
        ("admin","admin123","محمد إبراهيم","admin","الإدارة العامة"),
        ("reception","rec123","أحمد يونس","reception","الاستقبال"),
        ("students_dept","stu123","أحمد إبراهيم","students","شؤون الطلاب"),
        ("teacher1","tea123","كوثر شعبان","teacher","المعلمات"),
        ("teacher2","tea456","زهراء نوح","teacher","المعلمات"),
        ("media","med123","زينب إبراهيم","media","الإعلام"),
        ("curriculum","cur123","فاطمة إبراهيم","curriculum","المناهج"),
        ("ideas","ide123","إبراهيم عبدالرسول","ideas","الأفكار"),
        ("secretary","sec123","وفاء شاكر","secretary","أمانة السر"),
        ("premises","pre123","رائد الحايكي","premises","شؤون المقر"),
        ("parent1","par123","ولي أمر","parent","أولياء الأمور"),
    ]
    for u,p,n,r,d in users:
        try: db.execute("INSERT INTO users(username,password,name,role,department)VALUES(?,?,?,?,?)",(u,hp(p),n,r,d))
        except: pass
    db.commit(); db.close()

if not os.path.exists(DB): init_db()
def auto_import_students():
    """Auto-import students from Google Sheets on startup if DB is empty."""
    SHEET_ID = '1lZIi00wDbPSGT-Sl0prYg6-tmKAPNymbDfRITbTyPe4'
    GID = '942035800'
    try:
        db = sqlite3.connect(DB)
        count = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
        if count > 0:
            db.close()
            return
        csv_url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}'
        req = urllib.request.Request(csv_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8-sig')
        reader = csv.reader(io.StringIO(raw))
        rows = list(reader)
        header_idx = next((i for i, r in enumerate(rows) if any('اسم' in str(c) for c in r)), 1)
        headers = rows[header_idx]
        name_col = next((i for i, h in enumerate(headers) if 'اسم' in str(h)), 2)
        wa_col = next((i for i, h in enumerate(headers) if 'واتس' in str(h) or 'هاتف' in str(h)), 3)
        level_col = next((i for i, h in enumerate(headers) if 'صف' in str(h)), 4)
        group_col = next((i for i, h in enumerate(headers) if 'مجموعة' in str(h)), 7)
        added = 0
        for row in rows[header_idx + 1:]:
            if len(row) <= name_col: continue
            name = row[name_col].strip()
            if not name: continue
            wa = row[wa_col].strip() if len(row) > wa_col else ''
            level = row[level_col].strip() if len(row) > level_col else ''
            group = row[group_col].strip() if len(row) > group_col else ''
            exists = db.execute('SELECT id FROM students WHERE name=?', (name,)).fetchone()
            if exists: continue
            db.execute('INSERT INTO students (name, group_name, whatsapp, level, monthly_fee, status) VALUES (?,?,?,?,?,?)',
                       (name, group, wa, level, 35, 'active'))
            added += 1
        db.commit()
        db.close()
        print(f'[auto-import] Added {added} students from Google Sheets')
    except Exception as e:
        print(f'[auto-import] Error: {e}')

auto_import_students()
def migrate_db():
    """Add new columns to existing students table."""
    db = sqlite3.connect(DB)
    new_cols = [
        ("group_name2","TEXT"),("schedule_time","TEXT"),("schedule_time_ramadan","TEXT"),
        ("schedule_days","TEXT"),("group_online","TEXT"),("schedule_time_online","TEXT"),
        ("schedule_days_online","TEXT"),("zoom_link_online","TEXT"),("attendance_summary","TEXT"),
        ("absence_rate","TEXT"),("delay_rate","TEXT"),("teacher_name","TEXT"),
        ("next_level","TEXT"),("final_result","TEXT"),("student_progress","TEXT"),
        ("level_suitable","TEXT"),("book_received","TEXT"),("notes_2026","TEXT"),("registration_status","TEXT"),("old_new_2026","TEXT"),("final_result_2026","TEXT"),("installment1","TEXT"),("installment2","TEXT"),("installment3","TEXT"),("installment4","TEXT"),("installment5","TEXT"),("total_paid","TEXT"),("remaining_amount","TEXT"),("mother_phone","TEXT"),("father_phone","TEXT"),("other_phone","TEXT"),("residence","TEXT"),("home_address","TEXT"),("road","TEXT"),("complex_name","TEXT")
    ]
    for col, typ in new_cols:
        try:
            db.execute(f"ALTER TABLE students ADD COLUMN {col} {typ}")
        except: pass
    db.commit(); db.close()

migrate_db()

def login_required(f):
    @wraps(f)
    def dec(*a,**k):
        if "user" not in session: return redirect("/")
        return f(*a,**k)
    return dec

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mindex — تسجيل الدخول</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Tahoma,Arial,sans-serif;}
body{background:linear-gradient(135deg,#f3eeff 0%,#e8f8fb 100%);display:flex;align-items:center;justify-content:center;min-height:100vh;}
.box{background:#fff;border:1px solid #E0D5F0;border-radius:20px;padding:40px 36px;width:400px;box-shadow:0 8px 40px rgba(107,63,160,0.13);}
.logo-area{display:flex;flex-direction:column;align-items:center;gap:6px;margin-bottom:28px;}
.logo-circle{width:110px;height:110px;border-radius:50%;border:3px solid #6B3FA0;background:#fff;display:flex;align-items:center;justify-content:center;overflow:hidden;}
.logo-circle svg{width:90px;height:90px;}
.centre-name{font-size:15px;font-weight:800;color:#6B3FA0;text-align:center;letter-spacing:0.5px;line-height:1.4;}
.centre-slogan{font-size:12px;color:#00BCD4;font-weight:600;text-align:center;letter-spacing:1px;}
.roles{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-bottom:20px;}
.role-btn{padding:6px 14px;border-radius:20px;border:1.5px solid #6B3FA0;background:#fff;color:#6B3FA0;font-size:12px;cursor:pointer;transition:.2s;}
.role-btn:hover,.role-btn.active{background:#6B3FA0;color:#fff;}
label{display:block;text-align:right;font-size:13px;color:#6B3FA0;margin-bottom:6px;font-weight:600;}
input{width:100%;padding:12px 14px;border:1.5px solid #E0D5F0;border-radius:10px;font-size:14px;margin-bottom:16px;outline:none;transition:.2s;background:#faf7ff;}
input:focus{border-color:#6B3FA0;background:#fff;}
button.login-btn{width:100%;padding:13px;background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border:none;border-radius:12px;font-size:16px;font-weight:700;cursor:pointer;}
.err{background:#fee;color:#c00;padding:10px;border-radius:8px;margin-bottom:12px;text-align:center;font-size:13px;}
.hint{text-align:center;font-size:11px;color:#B0A0CC;margin-top:14px;}
</style>
</head>
<body>
<div class="box">
<div class="logo-area">
<div class="logo-circle">
<svg viewBox="0 0 90 90" xmlns="http://www.w3.org/2000/svg">
<rect x="12" y="48" width="66" height="30" rx="4" fill="#00BCD4"/>
<rect x="15" y="50" width="29" height="26" rx="2" fill="#00ACC1"/>
<rect x="46" y="50" width="29" height="26" rx="2" fill="#00ACC1"/>
<rect x="43" y="48" width="4" height="30" rx="2" fill="#006064"/>
<ellipse cx="45" cy="36" rx="18" ry="16" fill="#9C5BB5"/>
<ellipse cx="36" cy="33" rx="8" ry="10" fill="#B07AC8"/>
<ellipse cx="54" cy="33" rx="8" ry="10" fill="#B07AC8"/>
<ellipse cx="45" cy="36" rx="9" ry="11" fill="#9C5BB5"/>
<line x1="45" y1="25" x2="45" y2="47" stroke="#7B3FA0" stroke-width="1.5"/>
<ellipse cx="38" cy="38" rx="3" ry="4" fill="#8B4BAF"/>
<ellipse cx="52" cy="38" rx="3" ry="4" fill="#8B4BAF"/>
<polygon points="33,18 38,10 45,16 52,10 57,18 33,18" fill="#FFD700"/>
<polygon points="33,18 57,18 55,24 35,24" fill="#FFC107"/>
<circle cx="38" cy="10" r="2" fill="#FF8F00"/>
<circle cx="45" cy="16" r="2" fill="#FF8F00"/>
<circle cx="52" cy="10" r="2" fill="#FF8F00"/>
<path d="M40 42 Q45 47 50 42" stroke="#7B3FA0" stroke-width="1.5" fill="none" stroke-linecap="round"/>
<circle cx="41" cy="39" r="1.5" fill="#7B3FA0"/>
<circle cx="49" cy="39" r="1.5" fill="#7B3FA0"/>
</svg>
</div>
<div class="centre-name">MINDEX EDUCATION<br>&amp; TRAINING CENTRE</div>
<div class="centre-slogan">Play &middot; Enjoy &middot; Learn</div>
</div>
<div class="roles" id="roles">
<button class="role-btn active" onclick="setRole(this,'admin','admin123')">الإدارة</button>
<button class="role-btn" onclick="setRole(this,'reception','rec123')">الاستقبال</button>
<button class="role-btn" onclick="setRole(this,'teacher1','tea123')">كوثر شعبان</button>
<button class="role-btn" onclick="setRole(this,'teacher2','tea456')">زهراء نوح</button>
<button class="role-btn" onclick="setRole(this,'media','med123')">الإعلام</button>
<button class="role-btn" onclick="setRole(this,'curriculum','cur123')">المناهج</button>
<button class="role-btn" onclick="setRole(this,'parent1','par123')">ولي أمر</button>
</div>
{% if error %}<div class="err">{{ error }}</div>{% endif %}
<form method="POST" action="/login">
<label>اسم المستخدم</label>
<input type="text" name="username" id="uname" placeholder="username" required>
<label>كلمة المرور</label>
<input type="password" name="password" id="upass" placeholder="password" required>
<button type="submit" class="login-btn">دخول &larr;</button>
</form>
<div class="hint">اختر دوراً أعلاه للدخول السريع</div>
</div>
<script>
function setRole(el,u,p){
  document.querySelectorAll('.role-btn').forEach(b=>b.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('uname').value=u;
  document.getElementById('upass').value=p;
}
document.getElementById('uname').value='admin';
document.getElementById('upass').value='admin123';
</script>
</body>
</html>"""

@app.route("/")
def index():
    if "user" in session: return redirect("/dashboard")
    return LOGIN_HTML.replace("{% if error %}","<!--").replace("{% endif %}","-->").replace("{{ error }}","")

@app.route("/login", methods=["GET"])
def login_get():
    if "user" in session: return redirect("/dashboard")
    return LOGIN_HTML.replace("{% if error %}","<!--").replace("{% endif %}","-->").replace("{{ error }}","")

@app.route("/login", methods=["POST"])
def login_post():
    username = request.form.get("username","")
    password = request.form.get("password","")
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?",(username,hp(password))).fetchone()
    if not user:
        err_html = LOGIN_HTML.replace("{% if error %}","").replace("{% endif %}","").replace("{{ error }}","اسم المستخدم أو كلمة المرور غلط")
        return err_html, 401
    session["user"] = dict(user)
    return redirect("/dashboard")

@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.json or {}
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?",(d.get("username",""),hp(d.get("password","")))).fetchone()
    if not user: return jsonify({"ok":False,"msg":"بيانات الدخول غلط"})
    session["user"] = dict(user)
    return jsonify({"ok":True,"user":dict(user)})

@app.route("/api/logout", methods=["POST","GET"])
def api_logout():
    session.clear()
    return redirect("/")

@app.route("/dashboard")
@login_required
def dashboard():
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"app.html")) as f:
            html = f.read()
        u = session["user"]
        role = u.get("role","")
        role_labels = {
            "admin":"الإدارة العامة","reception":"الاستقبال",
            "students":"شؤون الطلاب","teacher":"المعلمات",
            "media":"الإعلام","curriculum":"المناهج",
            "ideas":"الأفكار","secretary":"أمانة السر",
            "premises":"شؤون المقر","parent":"ولي أمر"
        }
        role_label = role_labels.get(role, role)
        all_pages = ["dashboard","students","groups","attendance","payments","tasks","curriculum","evaluations","violations","points","events","faq","whatsapp","ai","database"]
        role_pages = {
            "admin": all_pages,
            "reception": ["dashboard","students","groups","attendance","payments","faq","whatsapp","ai"],
            "students": ["dashboard","students","attendance","violations","points","faq","ai"],
            "teacher": ["dashboard","students","groups","attendance","curriculum","evaluations","faq","ai"],
            "media": ["dashboard","events","faq","whatsapp","ai"],
            "curriculum": ["dashboard","curriculum","evaluations","faq","ai"],
            "ideas": ["dashboard","events","faq","ai"],
            "secretary": ["dashboard","tasks","faq","ai"],
            "premises": ["dashboard","tasks","faq","ai"],
            "parent": ["dashboard","students","attendance","payments","faq","ai"]
        }
        pages = role_pages.get(role, ["dashboard","faq","ai"])
        return render_template_string(html, user=u, role_label=role_label, pages=pages)
    except Exception as e:
        u = session.get("user",{})
        return f"<h2>مرحباً {u.get('name','')}</h2><p>دورك: {u.get('role','')}</p><p>خطأ: {str(e)}</p><a href='/api/logout'>خروج</a>"

@app.route("/api/me")
@login_required
def api_me():
    return jsonify({"user": session["user"]})

@app.route("/api/dashboard")
@login_required
def api_dashboard():
    db = get_db()
    today = date.today().isoformat()
    user = session["user"]
    role = user.get("role","")
    dept = user.get("department","")
    total_students = db.execute("SELECT COUNT(*) FROM students WHERE status='active'").fetchone()[0]
    absent_today = db.execute("SELECT COUNT(*) FROM attendance WHERE date=? AND status='absent'",(today,)).fetchone()[0]
    recent_absent = [dict(r) for r in db.execute("SELECT * FROM attendance WHERE date=? AND status='absent' ORDER BY rowid DESC LIMIT 10",(today,)).fetchall()]
    open_violations = db.execute("SELECT COUNT(*) FROM violations WHERE status='open'").fetchone()[0]
    if role == "admin":
        pending_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'").fetchone()[0]
        recent_tasks = [dict(r) for r in db.execute("SELECT * FROM tasks WHERE status!='done' ORDER BY rowid DESC LIMIT 6").fetchall()]
    else:
        pending_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status='pending' AND department=?",(dept,)).fetchone()[0]
        recent_tasks = [dict(r) for r in db.execute("SELECT * FROM tasks WHERE status!='done' AND department=? ORDER BY rowid DESC LIMIT 6",(dept,)).fetchall()]
    pending_pay = db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    raw_groups = db.execute("SELECT g.*, (SELECT COUNT(*) FROM students s WHERE s.group_name=g.name AND s.status='active') as count FROM groups_tbl g ORDER BY g.name").fetchall()
    groups = []
    for g in raw_groups:
        gd = dict(g)
        sched = gd.get("schedule","")
        parts = sched.split(" ") if sched else []
        gd["course"] = gd.get("subject","")
        gd["days"] = parts[0] if len(parts)>0 else ""
        gd["time"] = " ".join(parts[1:]) if len(parts)>1 else ""
        groups.append(gd)
    return jsonify({"total_students":total_students,"absent_today":absent_today,"pending_tasks":pending_tasks,"pending_pay":pending_pay,"recent_tasks":recent_tasks,"open_violations":open_violations,"recent_absent":recent_absent,"groups":groups,"user_name":user.get("name",""),"user_role":role,"user_dept":dept})

@app.route("/api/students")
@login_required
def api_students():
    db = get_db()
    user = session["user"]
    role = user.get("role","")
    q = request.args.get("q","")
    group = request.args.get("group","")
    query = "SELECT * FROM students WHERE status='active'"
    params = []
    if role == "teacher":
        query += " AND teacher=?"
        params.append(user.get("name",""))
    if q:
        query += " AND (name LIKE ? OR group_name LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if group:
        query += " AND group_name=?"
        params.append(group)
    query += " ORDER BY name"
    rows = db.execute(query, params).fetchall()
    return jsonify({"students":[dict(r) for r in rows]})

@app.route("/api/students", methods=["POST"])
@login_required
def api_add_student():
    d = request.json or {}
    db = get_db()
    db.execute("INSERT INTO students(name,group_name,teacher,whatsapp,level,zoom_link,monthly_fee,group_name2,schedule_time,schedule_time_ramadan,schedule_days,group_online,schedule_time_online,schedule_days_online,zoom_link_online,attendance_summary,absence_rate,delay_rate,teacher_name,next_level,final_result,student_progress,level_suitable,book_received,notes_2026)VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
               (d["name"],d.get("group_name",""),d.get("teacher",""),d.get("whatsapp",""),d.get("level",""),d.get("zoom_link",""),d.get("monthly_fee",35),d.get("group_name2",""),d.get("schedule_time",""),d.get("schedule_time_ramadan",""),d.get("schedule_days",""),d.get("group_online",""),d.get("schedule_time_online",""),d.get("schedule_days_online",""),d.get("zoom_link_online",""),d.get("attendance_summary",""),d.get("absence_rate",""),d.get("delay_rate",""),d.get("teacher_name",""),d.get("next_level",""),d.get("final_result",""),d.get("student_progress",""),d.get("level_suitable",""),d.get("book_received",""),d.get("notes_2026","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/students/<int:sid>")
@login_required
def api_student_detail(sid):
    db = get_db()
    row = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
    if not row: return jsonify({"error": "not found"}), 404
    s = dict(row)
    # Get attendance stats
    att = db.execute("SELECT status, COUNT(*) as n FROM attendance WHERE student_name=? GROUP BY status", (s['name'],)).fetchall()
    att_map = {r['status']: r['n'] for r in att}
    s['total_sessions'] = sum(att_map.values())
    s['absent_count'] = att_map.get('absent', 0)
    s['absence_rate'] = round(s['absent_count'] / s['total_sessions'] * 100) if s['total_sessions'] > 0 else 0
    # Get payments
    pays = db.execute("SELECT * FROM payments WHERE student_name=? ORDER BY rowid DESC LIMIT 6", (s['name'],)).fetchall()
    s['payments'] = [dict(p) for p in pays]
    # Get points
    pts = db.execute("SELECT SUM(points) as total FROM points WHERE student_name=?", (s['name'],)).fetchone()
    s['total_points'] = pts['total'] or 0
    db.close()
    return jsonify({"student": s})

@app.route("/api/students/<int:sid>", methods=["PUT"])
@login_required
def api_update_student(sid):
    d = request.json or {}
    db = get_db()
    db.execute("UPDATE students SET name=?,group_name=?,teacher=?,whatsapp=?,level=?,zoom_link=?,monthly_fee=?,group_name2=?,schedule_time=?,schedule_time_ramadan=?,schedule_days=?,group_online=?,schedule_time_online=?,schedule_days_online=?,zoom_link_online=?,attendance_summary=?,absence_rate=?,delay_rate=?,teacher_name=?,next_level=?,final_result=?,student_progress=?,level_suitable=?,book_received=?,notes_2026=? WHERE id=?",
               (d["name"],d.get("group_name",""),d.get("teacher",""),d.get("whatsapp",""),d.get("level",""),d.get("zoom_link",""),d.get("monthly_fee",35),d.get("group_name2",""),d.get("schedule_time",""),d.get("schedule_time_ramadan",""),d.get("schedule_days",""),d.get("group_online",""),d.get("schedule_time_online",""),d.get("schedule_days_online",""),d.get("zoom_link_online",""),d.get("attendance_summary",""),d.get("absence_rate",""),d.get("delay_rate",""),d.get("teacher_name",""),d.get("next_level",""),d.get("final_result",""),d.get("student_progress",""),d.get("level_suitable",""),d.get("book_received",""),d.get("notes_2026",""),sid))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/students/<int:sid>", methods=["DELETE"])
@login_required
def api_delete_student(sid):
    db = get_db()
    db.execute("UPDATE students SET status='inactive' WHERE id=?",(sid,))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/attendance")
@login_required
def api_get_attendance():
    db = get_db()
    d = request.args.get("date", date.today().isoformat())
    g_name = request.args.get("group","")
    if g_name:
        rows = db.execute("SELECT * FROM attendance WHERE date=? AND group_name=?",(d,g_name)).fetchall()
    else:
        rows = db.execute("SELECT * FROM attendance WHERE date=?",(d,)).fetchall()
    records = [dict(r) for r in rows]
    present = sum(1 for r in records if r.get("status") == "present")
    absent = sum(1 for r in records if r.get("status") == "absent")
    return jsonify({"attendance": records, "records": records, "present": present, "absent": absent})

@app.route("/api/attendance", methods=["POST"])
@login_required
def api_attendance():
    d = request.json or {}
    db = get_db()
    db.execute("DELETE FROM attendance WHERE student_name=? AND date=?",(d["student_name"],d["date"]))
    db.execute("INSERT INTO attendance(student_name,group_name,date,status)VALUES(?,?,?,?)",
               (d["student_name"],d.get("group_name",""),d["date"],d["status"]))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/tasks")
@login_required
def api_tasks():
    db = get_db()
    user = session["user"]
    role = user.get("role","")
    dept = user.get("department","")
    status_filter = request.args.get("status","")
    if role == "admin":
        query = "SELECT * FROM tasks"
        params = []
    else:
        query = "SELECT * FROM tasks WHERE department=?"
        params = [dept]
    if status_filter:
        if params:
            query += " AND status=?"
        else:
            query += " WHERE status=?"
        params.append(status_filter)
    query += " ORDER BY rowid DESC"
    rows = db.execute(query, params).fetchall()
    return jsonify({"tasks":[dict(r) for r in rows]})

@app.route("/api/tasks", methods=["POST"])
@login_required
def api_add_task():
    d = request.json or {}
    db = get_db()
    db.execute("INSERT INTO tasks(title,department,assigned_to,priority,due_date,created_date,notes)VALUES(?,?,?,?,?,?,?)",
               (d["title"],d.get("department",""),d.get("assigned_to",""),d.get("priority","medium"),d.get("due_date",""),date.today().isoformat(),d.get("notes","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/tasks/<int:tid>", methods=["PUT"])
@login_required
def api_update_task(tid):
    d = request.json or {}
    db = get_db()
    db.execute("UPDATE tasks SET status=? WHERE id=?",(d["status"],tid))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/tasks/<int:tid>", methods=["DELETE"])
@login_required
def api_delete_task(tid):
    db = get_db()
    db.execute("DELETE FROM tasks WHERE id=?",(tid,))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/violations")
@login_required
def api_violations():
    db = get_db()
    student = request.args.get("student","")
    if student:
        rows = db.execute("SELECT * FROM violations WHERE student_name LIKE ? ORDER BY rowid DESC",(f"%{student}%",)).fetchall()
    else:
        rows = db.execute("SELECT * FROM violations ORDER BY rowid DESC").fetchall()
    stats = {"open": sum(1 for r in rows if r["status"]=="open"), "resolved": sum(1 for r in rows if r["status"]!="open"), "high": sum(1 for r in rows if r["points"]>=3), "total_pts": sum(r["points"] for r in rows)}
    return jsonify({"violations":[dict(r) for r in rows], "stats": stats})

@app.route("/api/violations", methods=["POST"])
@login_required
def api_add_violation():
    d = request.json or {}
    db = get_db()
    db.execute("INSERT INTO violations(student_name,title,description,points,date)VALUES(?,?,?,?,?)",
               (d["student_name"],d["title"],d.get("description",""),d.get("points",1),date.today().isoformat()))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/violations/<int:vid>", methods=["PUT"])
@login_required
def api_update_violation(vid):
    d = request.json or {}
    db = get_db()
    db.execute("UPDATE violations SET status=? WHERE id=?",(d["status"],vid))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/points")
@login_required
def api_points():
    db = get_db()
    student = request.args.get("student","")
    if student:
        rows = db.execute("SELECT * FROM points WHERE student_name LIKE ? ORDER BY rowid DESC",(f"%{student}%",)).fetchall()
    else:
        rows = db.execute("SELECT * FROM points ORDER BY rowid DESC").fetchall()
    top = db.execute("SELECT student_name, SUM(points) as total FROM points GROUP BY student_name ORDER BY total DESC LIMIT 10").fetchall()
    return jsonify({"points":[dict(r) for r in rows], "top":[dict(r) for r in top]})

@app.route("/api/points", methods=["POST"])
@login_required
def api_add_points():
    d = request.json or {}
    db = get_db()
    db.execute("INSERT INTO points(student_name,reason,points,date)VALUES(?,?,?,?)",
               (d["student_name"],d.get("reason",""),d.get("points",5),date.today().isoformat()))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/payments")
@login_required
def api_payments():
    db = get_db()
    status_filter = request.args.get("status","")
    student = request.args.get("student","")
    query = "SELECT * FROM payments"
    params = []
    conditions = []
    if status_filter:
        conditions.append("status=?")
        params.append(status_filter)
    if student:
        conditions.append("student_name LIKE ?")
        params.append(f"%{student}%")
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY rowid DESC"
    rows = db.execute(query, params).fetchall()
    return jsonify({"payments":[dict(r) for r in rows],"total_pending":db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0],"total_paid":db.execute("SELECT COUNT(*) FROM payments WHERE status='paid'").fetchone()[0]})

@app.route("/api/payments", methods=["POST"])
@login_required
def api_add_payment():
    d = request.json or {}
    db = get_db()
    db.execute("INSERT INTO payments(student_name,amount,status,date,notes)VALUES(?,?,?,?,?)",
               (d["student_name"],d.get("amount",35),d.get("status","pending"),d.get("date",date.today().isoformat()),d.get("notes","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/payments/<int:pid>", methods=["PUT"])
@login_required
def api_update_payment(pid):
    d = request.json or {}
    db = get_db()
    db.execute("UPDATE payments SET status=?,date=?,notes=? WHERE id=?",(d["status"],d.get("date",date.today().isoformat()),d.get("notes",""),pid))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/groups")
@login_required
def api_groups():
    db = get_db()
    user = session["user"]
    role = user.get("role","")
    if role == "teacher":
        rows = db.execute("SELECT * FROM groups_tbl WHERE teacher=?",(user.get("name",""),)).fetchall()
    else:
        rows = db.execute("SELECT * FROM groups_tbl ORDER BY name").fetchall()
    return jsonify({"groups":[dict(r) for r in rows]})

@app.route("/api/groups", methods=["POST"])
@login_required
def api_add_group():
    d = request.json or {}
    db = get_db()
    db.execute("INSERT INTO groups_tbl(name,teacher,subject,level,zoom_link,schedule)VALUES(?,?,?,?,?,?)",
               (d["name"],d.get("teacher",""),d.get("subject",""),d.get("level",""),d.get("zoom_link",""),d.get("schedule","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/faq")
@login_required
def api_faq():
    db = get_db()
    dept = request.args.get("department","")
    if dept:
        rows = db.execute("SELECT * FROM faq WHERE department=? OR department=''",(dept,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM faq").fetchall()
    return jsonify({"faqs":[dict(r) for r in rows]})

@app.route("/api/faq", methods=["POST"])
@login_required
def api_add_faq():
    d = request.json or {}
    db = get_db()
    db.execute("INSERT INTO faq(question,answer,department)VALUES(?,?,?)",(d["question"],d["answer"],d.get("department","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/users")
@login_required
def api_users():
    user = session["user"]
    if user.get("role") != "admin":
        return jsonify({"error":"unauthorized"}), 403
    db = get_db()
    rows = db.execute("SELECT id,username,name,role,department FROM users").fetchall()
    return jsonify({"users":[dict(r) for r in rows]})

@app.route("/api/evaluations")
@login_required
def api_evaluations():
    db = get_db()
    group = request.args.get("group","")
    student = request.args.get("student","")
    q = "SELECT * FROM evaluations WHERE 1=1"
    params = []
    if group: q += " AND group_name=?"; params.append(group)
    if student: q += " AND student_name LIKE ?"; params.append(f"%{student}%")
    rows = db.execute(q + " ORDER BY rowid DESC", params).fetchall()
    db.close()
    return jsonify({"evaluations":[dict(r) for r in rows]})

@app.route("/api/evaluations", methods=["POST"])
@login_required
def api_evaluations_post():
    data = request.json or {}
    db = get_db()
    db.execute("INSERT INTO evaluations (student_name,group_name,teacher,subject,score,max_score,notes,date) VALUES (?,?,?,?,?,?,?,?)",
        (data.get("student_name",""), data.get("group_name",""), data.get("teacher",""), data.get("subject",""),
         data.get("score",0), data.get("max_score",100), data.get("notes",""), data.get("date","")))
    db.commit(); db.close()
    return jsonify({"ok":True})

@app.route("/api/evaluations/<int:eid>", methods=["DELETE"])
@login_required
def api_evaluations_delete(eid):
    db = get_db()
    db.execute("DELETE FROM evaluations WHERE id=?", (eid,))
    db.commit(); db.close()
    return jsonify({"ok":True})

@app.route("/api/curriculum")
@login_required
def api_curriculum():
    db = get_db()
    group = request.args.get("group","")
    rows = db.execute("SELECT * FROM curriculum" + (" WHERE group_name=?" if group else "") + " ORDER BY rowid DESC", ([group] if group else [])).fetchall()
    db.close()
    return jsonify({"curriculum":[dict(r) for r in rows]})

@app.route("/api/curriculum", methods=["POST"])
@login_required
def api_curriculum_post():
    data = request.json or {}
    db = get_db()
    db.execute("INSERT INTO curriculum (group_name,teacher,subject,week,topic,status,date,notes) VALUES (?,?,?,?,?,?,?,?)",
        (data.get("group_name",""), data.get("teacher",""), data.get("subject",""), data.get("week",""),
         data.get("topic",""), data.get("status","pending"), data.get("date",""), data.get("notes","")))
    db.commit(); db.close()
    return jsonify({"ok":True})

@app.route("/api/curriculum/<int:cid>", methods=["PUT","DELETE"])
@login_required
def api_curriculum_update(cid):
    db = get_db()
    if request.method == "DELETE":
        db.execute("DELETE FROM curriculum WHERE id=?", (cid,))
    else:
        data = request.json or {}
        db.execute("UPDATE curriculum SET status=?,notes=? WHERE id=?", (data.get("status","pending"), data.get("notes",""), cid))
    db.commit(); db.close()
    return jsonify({"ok":True})

@app.route("/api/events")
@login_required
def api_events():
    db = get_db()
    rows = db.execute("SELECT * FROM events ORDER BY date DESC, rowid DESC").fetchall()
    db.close()
    return jsonify({"events":[dict(r) for r in rows]})

@app.route("/api/events", methods=["POST"])
@login_required
def api_events_post():
    data = request.json or {}
    db = get_db()
    user = session.get("user", {})
    db.execute("INSERT INTO events (title,description,date,time,location,target,created_by) VALUES (?,?,?,?,?,?,?)",
        (data.get("title",""), data.get("description",""), data.get("date",""), data.get("time",""),
         data.get("location",""), data.get("target","all"), user.get("name","")))
    db.commit(); db.close()
    return jsonify({"ok":True})

@app.route("/api/events/<int:eid>", methods=["DELETE"])
@login_required
def api_events_delete(eid):
    db = get_db()
    db.execute("DELETE FROM events WHERE id=?", (eid,))
    db.commit(); db.close()
    return jsonify({"ok":True})

@app.route("/api/students/import", methods=["POST"])
@login_required
def api_import_students():
    user = session.get("user", {})
    if user.get("role") not in ["admin", "reception", "students"]:
        return jsonify({"ok": False, "msg": "غير مصرح"}), 403
    d = request.json or {}
    sheet_url = d.get("sheet_url", "")
    import re
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sheet_url)
    if not m:
        return jsonify({"ok": False, "msg": "رابط غير صحيح"})
    sheet_id = m.group(1)
    gid = d.get("gid", "942035800")
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8-sig", errors="replace")
    except Exception as e:
        return jsonify({"ok": False, "msg": f"فشل جلب البيانات: {str(e)}"})
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    header_row_idx = 1
    for i, row in enumerate(rows[:5]):
        for cell in row:
            if 'اسم' in cell and 'طالب' in cell:
                header_row_idx = i
                break
    if header_row_idx >= len(rows):
        return jsonify({"ok": False, "msg": "لم يتم العثور على صف العناوين"})
    headers = [h.strip() for h in rows[header_row_idx]]
    col_name = 2
    col_whatsapp = 3
    col_level = 4
    col_group = 7
    for i, h in enumerate(headers):
        h_clean = h.strip()
        if 'اسم الطالب' in h_clean or ('اسم' in h_clean and 'طالب' in h_clean):
            col_name = i
        elif 'واتساب' in h_clean or 'هاتف' in h_clean:
            col_whatsapp = i
        elif 'صف' in h_clean or 'مستوى' in h_clean:
            col_level = i
        elif 'مجموع' in h_clean and i > 5:
            col_group = i
    db = get_db()
    added = 0
    skipped = 0
    errors = []
    data_rows = rows[header_row_idx + 1:]
    for row in data_rows:
        if len(row) <= col_name:
            continue
        name = row[col_name].strip() if len(row) > col_name else ""
        if not name or name in ['', 'اسم الطالب']:
            continue
        def gc(i): return row[i].strip() if len(row) > i else ""
        whatsapp = gc(3); level = gc(4); group_name = gc(7); group_name2 = gc(8)
        schedule_time = gc(9); schedule_time_ramadan = gc(10); schedule_days = gc(11)
        group_online = gc(12); schedule_time_online = gc(13); schedule_days_online = gc(14)
        zoom_link_online = gc(15); attendance_summary = gc(16); absence_rate = gc(17)
        delay_rate = gc(18); teacher_name = gc(19); next_level = gc(20)
        final_result = gc(21); student_progress = gc(22); level_suitable = gc(23)
        book_received = gc(24); notes_2026 = gc(25)
        old_new_2026 = gc(5); registration_status = gc(6)
        final_result_2026 = gc(21)
        installment1 = gc(27); installment2 = gc(28); installment3 = gc(29)
        installment4 = gc(30); installment5 = gc(31)
        total_paid = gc(32); remaining_amount = gc(33)
        mother_phone = gc(34); father_phone = gc(35); other_phone = gc(36)
        residence = gc(37); home_address = gc(38); road = gc(39); complex_name = gc(40)
        existing = db.execute("SELECT id FROM students WHERE name=? AND status='active'", (name,)).fetchone()
        if existing:
            try:
                db.execute("""UPDATE students SET group_name=?,whatsapp=?,level=?,group_name2=?,schedule_time=?,schedule_time_ramadan=?,schedule_days=?,group_online=?,schedule_time_online=?,schedule_days_online=?,zoom_link_online=?,attendance_summary=?,absence_rate=?,delay_rate=?,teacher_name=?,next_level=?,final_result=?,student_progress=?,level_suitable=?,book_received=?,notes_2026=?,registration_status=?,old_new_2026=?,final_result_2026=?,installment1=?,installment2=?,installment3=?,installment4=?,installment5=?,total_paid=?,remaining_amount=?,mother_phone=?,father_phone=?,other_phone=?,residence=?,home_address=?,road=?,complex_name=? WHERE id=?""",
                    (group_name,whatsapp,level,group_name2,schedule_time,schedule_time_ramadan,schedule_days,group_online,schedule_time_online,schedule_days_online,zoom_link_online,attendance_summary,absence_rate,delay_rate,teacher_name,next_level,final_result,student_progress,level_suitable,book_received,notes_2026,registration_status,old_new_2026,final_result_2026,installment1,installment2,installment3,installment4,installment5,total_paid,remaining_amount,mother_phone,father_phone,other_phone,residence,home_address,road,complex_name,existing['id']))
                skipped += 1
            except Exception as e: errors.append(str(e))
            continue
        try:
            db.execute("INSERT INTO students(name,group_name,teacher,whatsapp,level,zoom_link,monthly_fee,group_name2,schedule_time,schedule_time_ramadan,schedule_days,group_online,schedule_time_online,schedule_days_online,zoom_link_online,attendance_summary,absence_rate,delay_rate,teacher_name,next_level,final_result,student_progress,level_suitable,book_received,notes_2026) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (name, group_name, "", whatsapp, level, "", 35,group_name2,schedule_time,schedule_time_ramadan,schedule_days,group_online,schedule_time_online,schedule_days_online,zoom_link_online,attendance_summary,absence_rate,delay_rate,teacher_name,next_level,final_result,student_progress,level_suitable,book_received,notes_2026))
            added += 1
        except Exception as e:
            errors.append(str(e))
    db.commit()
    return jsonify({"ok": True, "added": added, "updated": skipped, "errors": errors[:5]})

@app.route("/api/db/tables")
@login_required
def api_db_tables():
    user = session.get("user", {})
    if user.get("role") != "admin":
        return jsonify({"error": "unauthorized"}), 403
    db = get_db()
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    result = []
    for t in tables:
        tname = t["name"]
        count = db.execute(f"SELECT COUNT(*) as n FROM {tname}").fetchone()["n"]
        cols = db.execute(f"PRAGMA table_info({tname})").fetchall()
        result.append({"name": tname, "count": count, "columns": [c["name"] for c in cols]})
    return jsonify({"tables": result})

@app.route("/api/db/query")
@login_required
def api_db_query():
    user = session.get("user", {})
    if user.get("role") != "admin":
        return jsonify({"error": "unauthorized"}), 403
    table = request.args.get("table", "students")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    search = request.args.get("search", "")
    col = request.args.get("col", "")
    db = get_db()
    valid = [r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if table not in valid:
        return jsonify({"error": "invalid table"}), 400
    cols = [c["name"] for c in db.execute(f"PRAGMA table_info({table})").fetchall()]
    offset = (page - 1) * per_page
    where = ""
    params = []
    if search and col and col in cols:
        where = f" WHERE CAST({col} AS TEXT) LIKE ?"
        params.append(f"%{search}%")
    elif search:
        conds = [f"CAST({c} AS TEXT) LIKE ?" for c in cols[:6]]
        where = " WHERE " + " OR ".join(conds)
        params = [f"%{search}%"] * len(conds)
    total = db.execute(f"SELECT COUNT(*) as n FROM {table}" + where, params).fetchone()["n"]
    rows = db.execute(f"SELECT * FROM {table}" + where + f" LIMIT {per_page} OFFSET {offset}", params).fetchall()
    return jsonify({"table": table, "columns": cols, "rows": [dict(r) for r in rows],
        "total": total, "page": page, "per_page": per_page, "pages": (total + per_page - 1) // per_page})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
