# Mindex Portal - v5 Full Sheets DB
from flask import Flask, render_template_string, request, jsonify, session, redirect, g
import sqlite3, hashlib, os, urllib.request, csv, io, re
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

SHEET_ID = '1lZIi00wDbPSGT-Sl0prYg6-tmKAPNymbDfRITbTyPe4'

def init_db():
    db = sqlite3.connect(DB)
    db.executescript("""
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE,password TEXT,name TEXT,role TEXT,department TEXT);
CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,
    serial_no TEXT,personal_id TEXT,name TEXT,whatsapp TEXT,level TEXT,
    old_new_2026 TEXT,registration_status TEXT,
    group_name TEXT,group_name2 TEXT,
    schedule_time TEXT,schedule_time_ramadan TEXT,schedule_days TEXT,
    group_online TEXT,schedule_time_online TEXT,schedule_days_online TEXT,zoom_link_online TEXT,
    attendance_days TEXT,absence_rate TEXT,delay_rate TEXT,
    teacher_name TEXT,next_level TEXT,final_result TEXT,student_progress TEXT,
    level_suitable TEXT,book_received TEXT,teacher2 TEXT,whatsapp_group TEXT,
    installment1 TEXT,installment2 TEXT,installment3 TEXT,installment4 TEXT,installment5 TEXT,
    total_paid TEXT,remaining_amount TEXT,
    mother_phone TEXT,father_phone TEXT,other_phone TEXT,
    residence TEXT,home_address TEXT,road TEXT,complex_name TEXT,
    teacher TEXT,zoom_link TEXT,monthly_fee REAL DEFAULT 35,status TEXT DEFAULT 'active',
    notes_2026 TEXT,final_result_2026 TEXT);
CREATE TABLE IF NOT EXISTS groups_tbl(id INTEGER PRIMARY KEY,name TEXT,teacher TEXT,subject TEXT,level TEXT,zoom_link TEXT,schedule TEXT,prev_book TEXT,days TEXT,time TEXT,time_ramadan TEXT,online_days TEXT,online_time TEXT,online_time_ramadan TEXT,sessions_count TEXT,session_duration TEXT,total_hours TEXT,max_students INTEGER DEFAULT 20);
CREATE TABLE IF NOT EXISTS attendance_log(id INTEGER PRIMARY KEY,
    attendance_date TEXT,day_name TEXT,group_name TEXT,student_name TEXT,
    contact TEXT,status TEXT,message TEXT,whatsapp_link TEXT,send_status TEXT);
CREATE TABLE IF NOT EXISTS payments_detail(id INTEGER PRIMARY KEY,
    student_name TEXT,personal_id TEXT,registration_status TEXT,total_amount TEXT,
    installment1 TEXT,installment1_msg TEXT,installment2 TEXT,installment2_msg TEXT,
    installment3 TEXT,installment3_msg TEXT,installment4 TEXT,installment4_msg TEXT,
    installment5 TEXT,installment5_msg TEXT,
    total_paid TEXT,remaining TEXT,payment_status TEXT,payment_message TEXT,
    send_link TEXT,send_status TEXT);
CREATE TABLE IF NOT EXISTS evaluations_log(id INTEGER PRIMARY KEY,
    eval_date TEXT,group_name TEXT,student_name TEXT,
    participation TEXT,behavior TEXT,behavior_notes TEXT,
    reading TEXT,dictation TEXT,vocab TEXT,conversation TEXT,
    expression TEXT,grammar TEXT,notes TEXT);
CREATE TABLE IF NOT EXISTS violations_log(id INTEGER PRIMARY KEY,
    student_name TEXT,group_name TEXT,violation_date TEXT,record_time TEXT,location TEXT,
    violation_title TEXT,description TEXT,action_taken TEXT,notes TEXT,points TEXT,recorder TEXT);
CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY,student_name TEXT,group_name TEXT,date TEXT,status TEXT,contact TEXT,day_name TEXT,notes TEXT,whatsapp_link TEXT,send_status TEXT);
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,student_name TEXT,amount REAL,status TEXT DEFAULT 'pending',date TEXT,notes TEXT);
CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,title TEXT,department TEXT,assigned_to TEXT,status TEXT DEFAULT 'pending',priority TEXT DEFAULT 'medium',due_date TEXT,created_date TEXT,notes TEXT);
CREATE TABLE IF NOT EXISTS violations(id INTEGER PRIMARY KEY,student_name TEXT,title TEXT,description TEXT,points INTEGER DEFAULT 1,status TEXT DEFAULT 'open',date TEXT);
CREATE TABLE IF NOT EXISTS points(id INTEGER PRIMARY KEY,student_name TEXT,reason TEXT,points INTEGER DEFAULT 5,date TEXT);
CREATE TABLE IF NOT EXISTS faq(id INTEGER PRIMARY KEY,question TEXT,answer TEXT,department TEXT);
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

def auto_import_on_startup():
    def do_import():
        time.sleep(5)
        try:
            db2 = sqlite3.connect(DB)
            cnt = db2.execute("SELECT COUNT(*) FROM groups_tbl").fetchone()[0]
            if cnt > 0:
                db2.close()
                return
            print("Startup: Auto-importing data from Google Sheets...")
            SHEET_ID_V = SHEET_ID
            gid_map = [
                ('648031063', 'groups'),
                ('942035800', 'students'),
                ('608231213', 'attendance_log'),
                ('537129565', 'payments_detail'),
                ('1121376693', 'evaluations_log'),
            ]
            for gid, kind in gid_map:
                try:
                    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID_V}/export?format=csv&gid={gid}'
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    resp = urllib.request.urlopen(req, timeout=60)
                    raw = resp.read().decode('utf-8')
                    reader = list(csv.reader(io.StringIO(raw)))
                    if len(reader) < 2:
                        continue
                    added = 0
                    if kind == 'groups':
                        for row in reader[1:]:
                            if not row or not row[1].strip(): continue
                            n,t,l = row[1].strip(), (row[2].strip() if len(row)>2 else ''), (row[3].strip() if len(row)>3 else '')
                            try:
                                db2.execute("INSERT OR IGNORE INTO groups_tbl(name,teacher,level) VALUES(?,?,?)", (n,t,l)); added+=1
                            except: pass
                    elif kind == 'students':
                        for row in reader[2:]:
                            if not row or not row[2].strip(): continue
                            n=row[2].strip(); w=row[3].strip() if len(row)>3 else ''; g=row[7].strip() if len(row)>7 else ''
                            try:
                                db2.execute("INSERT OR IGNORE INTO students(name,whatsapp,group_name) VALUES(?,?,?)", (n,w,g)); added+=1
                            except: pass
                    elif kind == 'attendance_log':
                        for row in reader[1:]:
                            if not row or not row[0].strip() or len(row)<5: continue
                            try:
                                vals = tuple((row[i].strip() if len(row)>i else '') for i in range(9))
                                db2.execute("""INSERT OR IGNORE INTO attendance_log
                                    (attendance_date,day_name,group_name,student_name,contact,status,message,whatsapp_link,send_status)
                                    VALUES(?,?,?,?,?,?,?,?,?)""", vals); added+=1
                            except: pass
                    elif kind == 'payments_detail':
                        for row in reader[1:]:
                            if not row or not row[0].strip(): continue
                            try:
                                db2.execute("INSERT OR IGNORE INTO payments_detail(student_name,personal_id,registration_status) VALUES(?,?,?)",
                                    (row[0].strip(), row[1].strip() if len(row)>1 else '', row[2].strip() if len(row)>2 else '')); added+=1
                            except: pass
                    elif kind == 'evaluations_log':
                        for row in reader[1:]:
                            if not row or not row[0].strip(): continue
                            try:
                                db2.execute("INSERT OR IGNORE INTO evaluations_log(evaluation_date,group_name,student_name) VALUES(?,?,?)",
                                    (row[0].strip(), row[1].strip() if len(row)>1 else '', row[2].strip() if len(row)>2 else '')); added+=1
                            except: pass
                    db2.commit()
                    print(f"  {kind}: {added} records")
                except Exception as ex:
                    print(f"  {kind} error: {ex}")
            db2.close()
            print("Startup auto-import completed")
        except Exception as e:
            print(f"Auto-import error: {e}")
    threading.Thread(target=do_import, daemon=True).start()

def migrate_students_db():
    db = sqlite3.connect(DB)
    cols = [
        ("serial_no","TEXT"),("personal_id","TEXT"),("old_new_2026","TEXT"),
        ("registration_status","TEXT"),("group_name2","TEXT"),("schedule_time","TEXT"),
        ("schedule_time_ramadan","TEXT"),("schedule_days","TEXT"),("group_online","TEXT"),
        ("schedule_time_online","TEXT"),("schedule_days_online","TEXT"),("zoom_link_online","TEXT"),
        ("attendance_days","TEXT"),("absence_rate","TEXT"),("delay_rate","TEXT"),
        ("teacher_name","TEXT"),("next_level","TEXT"),("final_result","TEXT"),
        ("student_progress","TEXT"),("level_suitable","TEXT"),("book_received","TEXT"),
        ("teacher2","TEXT"),("whatsapp_group","TEXT"),
        ("installment1","TEXT"),("installment2","TEXT"),("installment3","TEXT"),
        ("installment4","TEXT"),("installment5","TEXT"),("total_paid","TEXT"),
        ("remaining_amount","TEXT"),("mother_phone","TEXT"),("father_phone","TEXT"),
        ("other_phone","TEXT"),("residence","TEXT"),("home_address","TEXT"),
        ("road","TEXT"),("complex_name","TEXT"),("notes_2026","TEXT"),("final_result_2026","TEXT"),
    ]
    for col, typ in cols:
        try: db.execute(f"ALTER TABLE students ADD COLUMN {col} {typ}")
        except: pass
    db.commit(); db.close()

def migrate_groups_db():
    db = sqlite3.connect(DB)
    for col, typ in [("prev_book","TEXT"),("days","TEXT"),("time","TEXT"),("time_ramadan","TEXT"),
        ("online_days","TEXT"),("online_time","TEXT"),("online_time_ramadan","TEXT"),
        ("sessions_count","TEXT"),("session_duration","TEXT"),("total_hours","TEXT"),("max_students","INTEGER")]:
        try: db.execute(f"ALTER TABLE groups_tbl ADD COLUMN {col} {typ}")
        except: pass
    db.commit(); db.close()

def migrate_new_tables():
    db = sqlite3.connect(DB)
    db.executescript("""
CREATE TABLE IF NOT EXISTS attendance_log(id INTEGER PRIMARY KEY,
    attendance_date TEXT,day_name TEXT,group_name TEXT,student_name TEXT,
    contact TEXT,status TEXT,message TEXT,whatsapp_link TEXT,send_status TEXT);
CREATE TABLE IF NOT EXISTS payments_detail(id INTEGER PRIMARY KEY,
    student_name TEXT,personal_id TEXT,registration_status TEXT,total_amount TEXT,
    installment1 TEXT,installment1_msg TEXT,installment2 TEXT,installment2_msg TEXT,
    installment3 TEXT,installment3_msg TEXT,installment4 TEXT,installment4_msg TEXT,
    installment5 TEXT,installment5_msg TEXT,
    total_paid TEXT,remaining TEXT,payment_status TEXT,payment_message TEXT,
    send_link TEXT,send_status TEXT);
CREATE TABLE IF NOT EXISTS evaluations_log(id INTEGER PRIMARY KEY,
    eval_date TEXT,group_name TEXT,student_name TEXT,
    participation TEXT,behavior TEXT,behavior_notes TEXT,
    reading TEXT,dictation TEXT,vocab TEXT,conversation TEXT,
    expression TEXT,grammar TEXT,notes TEXT);
CREATE TABLE IF NOT EXISTS violations_log(id INTEGER PRIMARY KEY,
    student_name TEXT,group_name TEXT,violation_date TEXT,record_time TEXT,location TEXT,
    violation_title TEXT,description TEXT,action_taken TEXT,notes TEXT,points TEXT,recorder TEXT);
""")
    db.commit(); db.close()

migrate_students_db()
migrate_groups_db()
migrate_new_tables()

def gc(row, i): return row[i].strip() if len(row) > i else ""

def fetch_sheet_csv(gid):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8-sig', errors='replace')
def auto_import_groups():
    try:
        db  = sqlite3.connect(DB)
        count = db.execute('SELECT COUNT(*) FROM groups_tbl').fetchone()[0]
        if count > 0:
            db.close(); return
        raw = fetch_sheet_csv('648031063')
        reader = csv.reader(io.StringIO(raw))
        rows = list(reader)
        added = 0
        for row in rows[1:]:
            name = gc(row, 1)
            if not name: continue
            try:
                teacher = gc(row,2); level = gc(row,3); prev_book = gc(row,4)
                days = gc(row,6); time_val = gc(row,7); time_ramadan = gc(row,8)
                online_days = gc(row,9); online_time_ramadan = gc(row,10); online_time = gc(row,11)
                zoom_link = gc(row,12)
                db.execute('INSERT OR IGNORE INTO groups_tbl(name,teacher,level,zoom_link,days,time,time_ramadan,online_days,online_time_ramadan,online_time) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (name,teacher,level,zoom_link,days,time_val,time_ramadan,online_days,online_time_ramadan,online_time))
                added += 1
            except: pass
        db.commit(); db.close()
        print(f'[auto-import] Added {added} groups')
    except Exception as e:
        print(f'[auto-import] Groups error: {e}')


def auto_import_students():
    try:
        db = sqlite3.connect(DB)
        count = db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
        if count > 0:
            db.close(); return
        raw = fetch_sheet_csv('942035800')
        reader = csv.reader(io.StringIO(raw))
        rows = list(reader)
        added = 0
        for row in rows[2:]:
            name = gc(row, 2)
            if not name: continue
            try:
                db.execute('INSERT OR IGNORE INTO students(name,group_name,whatsapp,level,monthly_fee,status)VALUES(?,?,?,?,?,?)',
                    (name, gc(row,7), gc(row,3), gc(row,4), 35, 'active'))
                added += 1
            except: pass
        db.commit(); db.close()
        print(f'[auto-import] Added {added} students')
    except Exception as e:
        print(f'[auto-import] Error: {e}')

auto_import_groups()
auto_import_students()

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

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "GET":
        if "user" in session: return redirect("/dashboard")
        return LOGIN_HTML.replace("{% if error %}","<!--").replace("{% endif %}","-->").replace("{{ error }}","")
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
        role_labels = {"admin":"الإدارة العامة","reception":"الاستقبال","students":"شؤون الطلاب",
            "teacher":"المعلمات","media":"الإعلام","curriculum":"المناهج",
            "ideas":"الأفكار","secretary":"أمانة السر","premises":"شؤون المقر","parent":"ولي أمر"}
        role_label = role_labels.get(role, role)
        all_pages = ["dashboard","students","groups","attendance","payments","tasks","curriculum","evaluations","violations","points","events","faq","whatsapp","ai","database","payments_detail","attendance_log","evaluations_log","violations_log"]
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
        return f"<h2>مرحباً {u.get('name','')}</h2><p>خطأ: {str(e)}</p><a href='/api/logout'>خروج</a>"

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
    groups = [dict(g) for g in raw_groups]
    return jsonify({"total_students":total_students,"absent_today":absent_today,"pending_tasks":pending_tasks,
        "pending_pay":pending_pay,"recent_tasks":recent_tasks,"open_violations":open_violations,
        "recent_absent":recent_absent,"groups":groups,"user_name":user.get("name",""),
        "user_role":role,"user_dept":dept})

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
        query += " AND teacher_name=?"
        params.append(user.get("name",""))
    if q:
        query += " AND (name LIKE ? OR group_name LIKE ? OR personal_id LIKE ?)"
        params += [f"%{q}%", f"%{q}%", f"%{q}%"]
    if group:
        query += " AND group_name=?"
        params.append(group)
    query += " ORDER BY name"
    rows = db.execute(query, params).fetchall()
    return jsonify({"students":[dict(r) for r in rows]})

@app.route("/api/students/groups")
@login_required
def api_student_groups():
    db = get_db()
    rows = db.execute("SELECT DISTINCT group_name FROM students WHERE status='active' AND group_name IS NOT NULL AND group_name != '' ORDER BY group_name").fetchall()
    return jsonify({"groups": [r["group_name"] for r in rows]})

@app.route("/api/students/import", methods=["POST"])
@login_required
def api_import_students():
    user = session.get("user", {})
    if user.get("role") not in ["admin", "reception", "students"]:
        return jsonify({"ok": False, "msg": "غير مصرح"}), 403
    d = request.json or {}
    sheet_url = d.get("sheet_url", "")
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sheet_url)
    if not m: return jsonify({"ok": False, "msg": "رابط غير صحيح"})
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
    if len(rows) < 3: return jsonify({"ok": False, "msg": "لا توجد بيانات"})
    db = get_db()
    added = 0; updated = 0; errors = []
    for row in rows[2:]:
        name = gc(row, 2)
        if not name or name == 'اسم الطالب': continue
        # Map all 41 columns (row index = sheet column - 1, data starts row 3 = index 2)
        serial_no      = gc(row, 0)
        personal_id    = gc(row, 1)
        # col 2 = name (already got)
        whatsapp       = gc(row, 3)
        level          = gc(row, 4)
        old_new_2026   = gc(row, 5)
        reg_status     = gc(row, 6)
        group_name     = gc(row, 7)
        group_name2    = gc(row, 8)
        sched_time     = gc(row, 9)
        sched_time_ram = gc(row, 10)
        sched_days     = gc(row, 11)
        group_online   = gc(row, 12)
        sched_time_on  = gc(row, 13)
        sched_days_on  = gc(row, 14)
        zoom_online    = gc(row, 15)
        att_days       = gc(row, 16)
        abs_rate       = gc(row, 17)
        delay_rate     = gc(row, 18)
        teacher_name   = gc(row, 19)
        next_level     = gc(row, 20)
        final_result   = gc(row, 21)
        progress       = gc(row, 22)
        suitable       = gc(row, 23)
        book_received  = gc(row, 24)
        teacher2       = gc(row, 25)
        wa_group       = gc(row, 26)
        inst1          = gc(row, 27)
        inst2          = gc(row, 28)
        inst3          = gc(row, 29)
        inst4          = gc(row, 30)
        inst5          = gc(row, 31)
        total_paid     = gc(row, 32)
        remaining      = gc(row, 33)
        mother_phone   = gc(row, 34)
        father_phone   = gc(row, 35)
        other_phone    = gc(row, 36)
        residence      = gc(row, 37)
        home_addr      = gc(row, 38)
        road           = gc(row, 39)
        complex_name   = gc(row, 40)
        existing = db.execute("SELECT id FROM students WHERE name=? AND status='active'", (name,)).fetchone()
        vals = (personal_id,serial_no,whatsapp,level,old_new_2026,reg_status,group_name,group_name2,
            sched_time,sched_time_ram,sched_days,group_online,sched_time_on,sched_days_on,zoom_online,
            att_days,abs_rate,delay_rate,teacher_name,next_level,final_result,progress,suitable,
            book_received,teacher2,wa_group,inst1,inst2,inst3,inst4,inst5,total_paid,remaining,
            mother_phone,father_phone,other_phone,residence,home_addr,road,complex_name)
        if existing:
            try:
                db.execute("""UPDATE students SET personal_id=?,serial_no=?,whatsapp=?,level=?,
                    old_new_2026=?,registration_status=?,group_name=?,group_name2=?,
                    schedule_time=?,schedule_time_ramadan=?,schedule_days=?,
                    group_online=?,schedule_time_online=?,schedule_days_online=?,zoom_link_online=?,
                    attendance_days=?,absence_rate=?,delay_rate=?,teacher_name=?,next_level=?,
                    final_result=?,student_progress=?,level_suitable=?,book_received=?,
                    teacher2=?,whatsapp_group=?,
                    installment1=?,installment2=?,installment3=?,installment4=?,installment5=?,
                    total_paid=?,remaining_amount=?,
                    mother_phone=?,father_phone=?,other_phone=?,
                    residence=?,home_address=?,road=?,complex_name=?
                    WHERE id=?""", vals + (existing["id"],))
                updated += 1
            except Exception as e:
                errors.append(str(e))
        else:
            try:
                db.execute("""INSERT INTO students(personal_id,serial_no,name,whatsapp,level,
                    old_new_2026,registration_status,group_name,group_name2,
                    schedule_time,schedule_time_ramadan,schedule_days,
                    group_online,schedule_time_online,schedule_days_online,zoom_link_online,
                    attendance_days,absence_rate,delay_rate,teacher_name,next_level,
                    final_result,student_progress,level_suitable,book_received,
                    teacher2,whatsapp_group,
                    installment1,installment2,installment3,installment4,installment5,
                    total_paid,remaining_amount,
                    mother_phone,father_phone,other_phone,
                    residence,home_address,road,complex_name,
                    monthly_fee,status)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,35,'active')""",
                    (personal_id,serial_no,name) + vals[2:])
                added += 1
            except Exception as e:
                errors.append(str(e))
    db.commit()
    return jsonify({"ok": True, "added": added, "updated": updated, "errors": errors[:5]})

@app.route("/api/students", methods=["POST"])
@login_required
def api_add_student():
    d = request.json or {}
    db = get_db()
    db.execute("INSERT INTO students(name,group_name,teacher_name,whatsapp,level,monthly_fee,registration_status)VALUES(?,?,?,?,?,?,?)",
        (d["name"],d.get("group_name",""),d.get("teacher_name",""),d.get("whatsapp",""),
         d.get("level",""),d.get("monthly_fee",35),d.get("registration_status","مستجد")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/students/<int:sid>", methods=["GET","PUT","DELETE"])
@login_required
def api_student(sid):
    db = get_db()
    if request.method == "GET":
        row = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
        if not row: return jsonify({"error": "not found"}), 404
        s = dict(row)
        att = db.execute("SELECT status, COUNT(*) as n FROM attendance WHERE student_name=? GROUP BY status", (s['name'],)).fetchall()
        att_map = {r['status']: r['n'] for r in att}
        s['total_sessions'] = sum(att_map.values())
        s['absent_count'] = att_map.get('absent', 0)
        s['absence_pct'] = round(s['absent_count'] / s['total_sessions'] * 100) if s['total_sessions'] > 0 else 0
        pts = db.execute("SELECT SUM(points) as total FROM points WHERE student_name=?", (s['name'],)).fetchone()
        s['total_points'] = pts['total'] or 0
        return jsonify({"student": s})
    elif request.method == "PUT":
        d = request.json or {}
        db.execute("""UPDATE students SET name=?,group_name=?,teacher_name=?,whatsapp=?,level=?,
            old_new_2026=?,registration_status=?,group_name2=?,schedule_time=?,
            schedule_time_ramadan=?,schedule_days=?,notes_2026=?,personal_id=? WHERE id=?""",
            (d.get("name",""),d.get("group_name",""),d.get("teacher_name",""),d.get("whatsapp",""),
             d.get("level",""),d.get("old_new_2026",""),d.get("registration_status",""),
             d.get("group_name2",""),d.get("schedule_time",""),d.get("schedule_time_ramadan",""),
             d.get("schedule_days",""),d.get("notes_2026",""),d.get("personal_id",""),sid))
        db.commit()
        return jsonify({"ok":True})
    else:
        db.execute("UPDATE students SET status='inactive' WHERE id=?",(sid,))
        db.commit()
        return jsonify({"ok":True})

@app.route("/api/groups")
@login_required
def api_groups():
    db = get_db()
    user = session["user"]
    role = user.get("role","")
    if role == "teacher":
        rows = db.execute("SELECT *, (SELECT COUNT(*) FROM students s WHERE s.group_name=g.name AND s.status='active') as student_count FROM groups_tbl g WHERE g.teacher=?",(user.get("name",""),)).fetchall()
    else:
        rows = db.execute("SELECT *, (SELECT COUNT(*) FROM students s WHERE s.group_name=g.name AND s.status='active') as student_count FROM groups_tbl g ORDER BY g.name").fetchall()
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

@app.route("/api/groups/import", methods=["POST"])
@login_required
def api_import_groups():
    user = session.get("user", {})
    if user.get("role") not in ["admin", "reception"]:
        return jsonify({"ok": False, "msg": "غير مصرح"}), 403
    d = request.json or {}
    sheet_url = d.get("sheet_url", "")
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sheet_url)
    if not m: return jsonify({"ok": False, "msg": "رابط غير صحيح"})
    sheet_id = m.group(1)
    gid = d.get("gid", "648031063")
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8-sig", errors="replace")
    except Exception as e:
        return jsonify({"ok": False, "msg": f"فشل جلب البيانات: {str(e)}"})
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if len(rows) < 2: return jsonify({"ok": False, "msg": "لا توجد بيانات"})
    db = get_db()
    added = 0; updated = 0
    for row in rows[1:]:
        name = gc(row, 1)
        if not name: continue
        teacher=gc(row,2); level=gc(row,3); prev_book=gc(row,4)
        days=gc(row,6); time=gc(row,7); time_ramadan=gc(row,8)
        online_days=gc(row,9); online_time_ramadan=gc(row,10); online_time=gc(row,11)
        zoom_link=gc(row,12); sessions_count=gc(row,13)
        session_duration=gc(row,14); total_hours=gc(row,15)
        existing = db.execute("SELECT id FROM groups_tbl WHERE name=?", (name,)).fetchone()
        if existing:
            db.execute("""UPDATE groups_tbl SET teacher=?,subject=?,level=?,zoom_link=?,days=?,time=?,time_ramadan=?,
                online_days=?,online_time=?,online_time_ramadan=?,prev_book=?,sessions_count=?,session_duration=?,total_hours=?
                WHERE id=?""", (teacher,level,level,zoom_link,days,time,time_ramadan,online_days,online_time,
                online_time_ramadan,prev_book,sessions_count,session_duration,total_hours,existing["id"]))
            updated += 1
        else:
            db.execute("""INSERT INTO groups_tbl(name,teacher,subject,level,zoom_link,days,time,time_ramadan,
                online_days,online_time,online_time_ramadan,prev_book,sessions_count,session_duration,total_hours)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name,teacher,level,level,zoom_link,days,time,time_ramadan,online_days,
                online_time,online_time_ramadan,prev_book,sessions_count,session_duration,total_hours))
            added += 1
    db.commit()
    return jsonify({"ok": True, "added": added, "updated": updated})

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
    present = sum(1 for r in records if r.get("status") in ("present","حاضر"))
    absent = sum(1 for r in records if r.get("status") in ("absent","غائب","متأخر","عذر"))
    return jsonify({"attendance": records, "records": records, "present": present, "absent": absent})

@app.route("/api/attendance", methods=["POST"])
@login_required
def api_attendance():
    d = request.json or {}
    db = get_db()
    contact = d.get("contact","")
    if not contact:
        st = db.execute("SELECT whatsapp FROM students WHERE name=?",(d["student_name"],)).fetchone()
        if st: contact = st["whatsapp"] or ""
    db.execute("DELETE FROM attendance WHERE student_name=? AND date=?",(d["student_name"],d["date"]))
    db.execute("""INSERT INTO attendance(student_name,group_name,date,status,contact,day_name,notes,whatsapp_link,send_status)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        (d["student_name"],d.get("group_name",""),d["date"],d.get("status","حاضر"),
         contact,d.get("day_name",""),d.get("notes",""),d.get("whatsapp_link",""),d.get("send_status","")))
    db.commit()
    return jsonify({"ok":True,"contact":contact})

@app.route("/api/attendance_log")
@login_required
def api_attendance_log():
    db = get_db()
    group = request.args.get("group","")
    dt = request.args.get("date","")
    q = "SELECT * FROM attendance_log WHERE 1=1"
    params = []
    if group: q += " AND group_name=?"; params.append(group)
    if dt: q += " AND attendance_date=?"; params.append(dt)
    rows = db.execute(q + " ORDER BY attendance_date DESC, id DESC LIMIT 500", params).fetchall()
    return jsonify({"records":[dict(r) for r in rows]})

@app.route("/api/attendance_log/import", methods=["POST"])
@login_required
def api_import_attendance():
    user = session.get("user", {})
    if user.get("role") not in ["admin", "reception", "students", "teacher"]:
        return jsonify({"ok": False, "msg": "غير مصرح"}), 403
    d = request.json or {}
    sheet_url = d.get("sheet_url", "")
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sheet_url)
    if not m: return jsonify({"ok": False, "msg": "رابط غير صحيح"})
    sheet_id = m.group(1)
    gid = d.get("gid", "608231213")
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8-sig", errors="replace")
    except Exception as e:
        return jsonify({"ok": False, "msg": f"فشل جلب البيانات: {str(e)}"})
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if len(rows) < 2: return jsonify({"ok": False, "msg": "لا توجد بيانات"})
    db = get_db()
    added = 0; updated = 0
    for row in rows[1:]:
        att_date=gc(row,0); day_name=gc(row,1); group_name=gc(row,2)
        student_name=gc(row,3); contact=gc(row,4); status=gc(row,5)
        message=gc(row,6); wa_link=gc(row,7); send_status=gc(row,8)
        if not student_name or not att_date: continue
        existing = db.execute("SELECT id FROM attendance_log WHERE student_name=? AND attendance_date=? AND group_name=?",
            (student_name, att_date, group_name)).fetchone()
        if existing:
            db.execute("""UPDATE attendance_log SET day_name=?,contact=?,status=?,message=?,whatsapp_link=?,send_status=?
                WHERE id=?""", (day_name,contact,status,message,wa_link,send_status,existing["id"]))
            updated += 1
        else:
            db.execute("""INSERT INTO attendance_log(attendance_date,day_name,group_name,student_name,contact,status,message,whatsapp_link,send_status)
                VALUES(?,?,?,?,?,?,?,?,?)""", (att_date,day_name,group_name,student_name,contact,status,message,wa_link,send_status))
            added += 1
    db.commit()
    return jsonify({"ok": True, "added": added, "updated": updated})

@app.route("/api/payments_detail")
@login_required
def api_payments_detail():
    db = get_db()
    student = request.args.get("student","")
    status = request.args.get("status","")
    q = "SELECT * FROM payments_detail WHERE 1=1"
    params = []
    if student: q += " AND student_name LIKE ?"; params.append(f"%{student}%")
    if status: q += " AND payment_status=?"; params.append(status)
    rows = db.execute(q + " ORDER BY student_name", params).fetchall()
    return jsonify({"payments":[dict(r) for r in rows]})

@app.route("/api/payments_detail/import", methods=["POST"])
@login_required
def api_import_payments():
    user = session.get("user", {})
    if user.get("role") not in ["admin", "reception"]:
        return jsonify({"ok": False, "msg": "غير مصرح"}), 403
    d = request.json or {}
    sheet_url = d.get("sheet_url", "")
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sheet_url)
    if not m: return jsonify({"ok": False, "msg": "رابط غير صحيح"})
    sheet_id = m.group(1)
    gid = d.get("gid", "537129565")
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8-sig", errors="replace")
    except Exception as e:
        return jsonify({"ok": False, "msg": f"فشل جلب البيانات: {str(e)}"})
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if len(rows) < 2: return jsonify({"ok": False, "msg": "لا توجد بيانات"})
    db = get_db()
    added = 0; updated = 0
    for row in rows[1:]:
        student_name=gc(row,0); personal_id=gc(row,1); reg_status=gc(row,2)
        total_amount=gc(row,3)
        inst1=gc(row,4); inst1_msg=gc(row,5)
        inst2=gc(row,6); inst2_msg=gc(row,7)
        inst3=gc(row,8); inst3_msg=gc(row,9)
        inst4=gc(row,10); inst4_msg=gc(row,11)
        inst5=gc(row,12); inst5_msg=gc(row,13)
        total_paid=gc(row,14); remaining=gc(row,15)
        pay_status=gc(row,16); pay_msg=gc(row,17)
        send_link=gc(row,18); send_status=gc(row,19)
        if not student_name: continue
        existing = db.execute("SELECT id FROM payments_detail WHERE student_name=?", (student_name,)).fetchone()
        if existing:
            db.execute("""UPDATE payments_detail SET personal_id=?,registration_status=?,total_amount=?,
                installment1=?,installment1_msg=?,installment2=?,installment2_msg=?,
                installment3=?,installment3_msg=?,installment4=?,installment4_msg=?,
                installment5=?,installment5_msg=?,total_paid=?,remaining=?,
                payment_status=?,payment_message=?,send_link=?,send_status=? WHERE id=?""",
                (personal_id,reg_status,total_amount,inst1,inst1_msg,inst2,inst2_msg,
                inst3,inst3_msg,inst4,inst4_msg,inst5,inst5_msg,total_paid,remaining,
                pay_status,pay_msg,send_link,send_status,existing["id"]))
            updated += 1
        else:
            db.execute("""INSERT INTO payments_detail(student_name,personal_id,registration_status,total_amount,
                installment1,installment1_msg,installment2,installment2_msg,
                installment3,installment3_msg,installment4,installment4_msg,
                installment5,installment5_msg,total_paid,remaining,
                payment_status,payment_message,send_link,send_status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (student_name,personal_id,reg_status,total_amount,inst1,inst1_msg,inst2,inst2_msg,
                inst3,inst3_msg,inst4,inst4_msg,inst5,inst5_msg,total_paid,remaining,
                pay_status,pay_msg,send_link,send_status))
            added += 1
    db.commit()
    return jsonify({"ok": True, "added": added, "updated": updated})

@app.route("/api/evaluations_log")
@login_required
def api_evaluations_log():
    db = get_db()
    group = request.args.get("group","")
    student = request.args.get("student","")
    q = "SELECT * FROM evaluations_log WHERE 1=1"
    params = []
    if group: q += " AND group_name=?"; params.append(group)
    if student: q += " AND student_name LIKE ?"; params.append(f"%{student}%")
    rows = db.execute(q + " ORDER BY eval_date DESC, id DESC LIMIT 500", params).fetchall()
    return jsonify({"evaluations":[dict(r) for r in rows]})

@app.route("/api/evaluations_log/import", methods=["POST"])
@login_required
def api_import_evaluations():
    user = session.get("user", {})
    if user.get("role") not in ["admin", "teacher", "curriculum"]:
        return jsonify({"ok": False, "msg": "غير مصرح"}), 403
    d = request.json or {}
    sheet_url = d.get("sheet_url", "")
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sheet_url)
    if not m: return jsonify({"ok": False, "msg": "رابط غير صحيح"})
    sheet_id = m.group(1)
    gid = d.get("gid", "1121376693")
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8-sig", errors="replace")
    except Exception as e:
        return jsonify({"ok": False, "msg": f"فشل جلب البيانات: {str(e)}"})
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if len(rows) < 2: return jsonify({"ok": False, "msg": "لا توجد بيانات"})
    db = get_db()
    added = 0; updated = 0
    for row in rows[1:]:
        eval_date=gc(row,0); group_name=gc(row,3); student_name=gc(row,4)
        participation=gc(row,5); behavior=gc(row,6); behavior_notes=gc(row,7)
        reading=gc(row,9); dictation=gc(row,10); vocab=gc(row,11)
        conversation=gc(row,12); expression=gc(row,13); grammar=gc(row,14); notes=gc(row,15)
        if not student_name: continue
        existing = db.execute("SELECT id FROM evaluations_log WHERE student_name=? AND eval_date=? AND group_name=?",
            (student_name,eval_date,group_name)).fetchone()
        if existing:
            db.execute("""UPDATE evaluations_log SET participation=?,behavior=?,behavior_notes=?,
                reading=?,dictation=?,vocab=?,conversation=?,expression=?,grammar=?,notes=?
                WHERE id=?""", (participation,behavior,behavior_notes,reading,dictation,vocab,
                conversation,expression,grammar,notes,existing["id"]))
            updated += 1
        else:
            db.execute("""INSERT INTO evaluations_log(eval_date,group_name,student_name,participation,
                behavior,behavior_notes,reading,dictation,vocab,conversation,expression,grammar,notes)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (eval_date,group_name,student_name,participation,behavior,behavior_notes,
                reading,dictation,vocab,conversation,expression,grammar,notes))
            added += 1
    db.commit()
    return jsonify({"ok": True, "added": added, "updated": updated})

@app.route("/api/violations_log")
@login_required
def api_violations_log():
    db = get_db()
    student = request.args.get("student","")
    q = "SELECT * FROM violations_log WHERE 1=1"
    params = []
    if student: q += " AND student_name LIKE ?"; params.append(f"%{student}%")
    rows = db.execute(q + " ORDER BY violation_date DESC, id DESC LIMIT 500", params).fetchall()
    return jsonify({"violations":[dict(r) for r in rows]})

@app.route("/api/violations_log/import", methods=["POST"])
@login_required
def api_import_violations():
    user = session.get("user", {})
    if user.get("role") not in ["admin", "reception", "students"]:
        return jsonify({"ok": False, "msg": "غير مصرح"}), 403
    d = request.json or {}
    sheet_url = d.get("sheet_url", "")
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9_-]+)', sheet_url)
    if not m: return jsonify({"ok": False, "msg": "رابط غير صحيح"})
    sheet_id = m.group(1)
    gid = d.get("gid", "350578639")
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    try:
        req = urllib.request.Request(csv_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8-sig", errors="replace")
    except Exception as e:
        return jsonify({"ok": False, "msg": f"فشل جلب البيانات: {str(e)}"})
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if len(rows) < 2: return jsonify({"ok": False, "msg": "لا توجد بيانات"})
    db = get_db()
    added = 0; updated = 0
    for row in rows[1:]:
        student_name=gc(row,0); group_name=gc(row,1); viol_date=gc(row,2)
        record_time=gc(row,3); location=gc(row,4); viol_title=gc(row,5)
        description=gc(row,6); action_taken=gc(row,7); notes=gc(row,8)
        points=gc(row,9); recorder=gc(row,10)
        if not student_name: continue
        existing = db.execute("SELECT id FROM violations_log WHERE student_name=? AND violation_date=? AND violation_title=?",
            (student_name,viol_date,viol_title)).fetchone()
        if existing:
            db.execute("""UPDATE violations_log SET group_name=?,record_time=?,location=?,
                description=?,action_taken=?,notes=?,points=?,recorder=? WHERE id=?""",
                (group_name,record_time,location,description,action_taken,notes,points,recorder,existing["id"]))
            updated += 1
        else:
            db.execute("""INSERT INTO violations_log(student_name,group_name,violation_date,record_time,location,
                violation_title,description,action_taken,notes,points,recorder)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (student_name,group_name,viol_date,record_time,location,viol_title,description,action_taken,notes,points,recorder))
            added += 1
    db.commit()
    return jsonify({"ok": True, "added": added, "updated": updated})

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
        if params: query += " AND status=?"
        else: query += " WHERE status=?"
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
    stats = {"open": sum(1 for r in rows if r["status"]=="open"),
        "resolved": sum(1 for r in rows if r["status"]!="open"),
        "high": sum(1 for r in rows if r["points"]>=3),
        "total_pts": sum(r["points"] for r in rows)}
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
    if status_filter: conditions.append("status=?"); params.append(status_filter)
    if student: conditions.append("student_name LIKE ?"); params.append(f"%{student}%")
    if conditions: query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY rowid DESC"
    rows = db.execute(query, params).fetchall()
    return jsonify({"payments":[dict(r) for r in rows],
        "total_pending":db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0],
        "total_paid":db.execute("SELECT COUNT(*) FROM payments WHERE status='paid'").fetchone()[0]})

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
    db.execute("UPDATE payments SET status=?,date=?,notes=? WHERE id=?",
        (d["status"],d.get("date",date.today().isoformat()),d.get("notes",""),pid))
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
    if user.get("role") != "admin": return jsonify({"error":"unauthorized"}), 403
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
    return jsonify({"evaluations":[dict(r) for r in rows]})

@app.route("/api/evaluations", methods=["POST"])
@login_required
def api_evaluations_post():
    data = request.json or {}
    db = get_db()
    db.execute("INSERT INTO evaluations(student_name,group_name,teacher,subject,score,max_score,notes,date)VALUES(?,?,?,?,?,?,?,?)",
        (data.get("student_name",""),data.get("group_name",""),data.get("teacher",""),data.get("subject",""),
         data.get("score",0),data.get("max_score",100),data.get("notes",""),data.get("date","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/evaluations/<int:eid>", methods=["DELETE"])
@login_required
def api_evaluations_delete(eid):
    db = get_db()
    db.execute("DELETE FROM evaluations WHERE id=?", (eid,))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/curriculum")
@login_required
def api_curriculum():
    db = get_db()
    group = request.args.get("group","")
    rows = db.execute("SELECT * FROM curriculum" + (" WHERE group_name=?" if group else "") + " ORDER BY rowid DESC",
        ([group] if group else [])).fetchall()
    return jsonify({"curriculum":[dict(r) for r in rows]})

@app.route("/api/curriculum", methods=["POST"])
@login_required
def api_curriculum_post():
    data = request.json or {}
    db = get_db()
    db.execute("INSERT INTO curriculum(group_name,teacher,subject,week,topic,status,date,notes)VALUES(?,?,?,?,?,?,?,?)",
        (data.get("group_name",""),data.get("teacher",""),data.get("subject",""),data.get("week",""),
         data.get("topic",""),data.get("status","pending"),data.get("date",""),data.get("notes","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/curriculum/<int:cid>", methods=["PUT","DELETE"])
@login_required
def api_curriculum_update(cid):
    db = get_db()
    if request.method == "DELETE":
        db.execute("DELETE FROM curriculum WHERE id=?", (cid,))
    else:
        data = request.json or {}
        db.execute("UPDATE curriculum SET status=?,notes=? WHERE id=?",
            (data.get("status","pending"),data.get("notes",""),cid))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/events")
@login_required
def api_events():
    db = get_db()
    rows = db.execute("SELECT * FROM events ORDER BY date DESC, rowid DESC").fetchall()
    return jsonify({"events":[dict(r) for r in rows]})

@app.route("/api/events", methods=["POST"])
@login_required
def api_events_post():
    data = request.json or {}
    db = get_db()
    user = session.get("user", {})
    db.execute("INSERT INTO events(title,description,date,time,location,target,created_by)VALUES(?,?,?,?,?,?,?)",
        (data.get("title",""),data.get("description",""),data.get("date",""),data.get("time",""),
         data.get("location",""),data.get("target","all"),user.get("name","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/events/<int:eid>", methods=["DELETE"])
@login_required
def api_events_delete(eid):
    db = get_db()
    db.execute("DELETE FROM events WHERE id=?", (eid,))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/db/tables")
@login_required
def api_db_tables():
    user = session.get("user", {})
    if user.get("role") != "admin": return jsonify({"error": "unauthorized"}), 403
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
    if user.get("role") != "admin": return jsonify({"error": "unauthorized"}), 403
    table = request.args.get("table", "students")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 50))
    search = request.args.get("search", "")
    col = request.args.get("col", "")
    db = get_db()
    valid = [r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if table not in valid: return jsonify({"error": "invalid table"}), 400
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
