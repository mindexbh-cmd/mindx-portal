# Mindex Portal - Fixed & Enhanced Version
from flask import Flask, render_template_string, request, jsonify, session, redirect, g
import sqlite3, hashlib, os
from datetime import date
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mindx2026")
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
    CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,name TEXT,group_name TEXT,teacher TEXT,whatsapp TEXT,level TEXT,zoom_link TEXT,monthly_fee REAL DEFAULT 35,status TEXT DEFAULT 'active');
    CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY,student_name TEXT,group_name TEXT,date TEXT,status TEXT);
    CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,student_name TEXT,amount REAL,status TEXT DEFAULT 'pending',date TEXT,notes TEXT);
    CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY,title TEXT,department TEXT,assigned_to TEXT,status TEXT DEFAULT 'pending',priority TEXT DEFAULT 'medium',due_date TEXT,created_date TEXT,notes TEXT);
    CREATE TABLE IF NOT EXISTS violations(id INTEGER PRIMARY KEY,student_name TEXT,title TEXT,description TEXT,points INTEGER DEFAULT 1,status TEXT DEFAULT 'open',date TEXT);
    CREATE TABLE IF NOT EXISTS points(id INTEGER PRIMARY KEY,student_name TEXT,reason TEXT,points INTEGER DEFAULT 5,date TEXT);
    CREATE TABLE IF NOT EXISTS faq(id INTEGER PRIMARY KEY,question TEXT,answer TEXT,department TEXT);
    CREATE TABLE IF NOT EXISTS groups_tbl(id INTEGER PRIMARY KEY,name TEXT,teacher TEXT,subject TEXT,level TEXT,zoom_link TEXT,schedule TEXT,max_students INTEGER DEFAULT 15);
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

def login_required(f):
    @wraps(f)
    def dec(*a,**k):
        if "user" not in session: return redirect("/")
        return f(*a,**k)
    return dec

@app.route("/")
def index():
    if "user" in session: return redirect("/dashboard")
    return render_template_string(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"login.html")).read())

@app.route("/api/login", methods=["POST"])
def api_login():
    d = request.json
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?",(d["username"],hp(d["password"]))).fetchone()
    if not user: return jsonify({"ok":False,"msg":"اسم المستخدم أو كلمة المرور غلط"})
    session["user"] = dict(user)
    return jsonify({"ok":True,"user":dict(user)})

@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.clear()
    return jsonify({"ok":True})

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template_string(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),"app.html")).read(),user=session["user"])

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
    if role == "admin":
        pending_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'").fetchone()[0]
        recent_tasks = [dict(r) for r in db.execute("SELECT * FROM tasks WHERE status!='done' ORDER BY rowid DESC LIMIT 6").fetchall()]
    else:
        pending_tasks = db.execute("SELECT COUNT(*) FROM tasks WHERE status='pending' AND department=?",(dept,)).fetchone()[0]
        recent_tasks = [dict(r) for r in db.execute("SELECT * FROM tasks WHERE status!='done' AND department=? ORDER BY rowid DESC LIMIT 6",(dept,)).fetchall()]
    pending_pay = db.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
    return jsonify({"total_students":total_students,"absent_today":absent_today,"pending_tasks":pending_tasks,"pending_pay":pending_pay,"recent_tasks":recent_tasks,"user_name":user.get("name",""),"user_role":role})

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
    d = request.json
    db = get_db()
    db.execute("INSERT INTO students(name,group_name,teacher,whatsapp,level,zoom_link,monthly_fee)VALUES(?,?,?,?,?,?,?)",
               (d["name"],d.get("group_name",""),d.get("teacher",""),d.get("whatsapp",""),d.get("level",""),d.get("zoom_link",""),d.get("monthly_fee",35)))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/students/<int:sid>", methods=["PUT"])
@login_required
def api_update_student(sid):
    d = request.json
    db = get_db()
    db.execute("UPDATE students SET name=?,group_name=?,teacher=?,whatsapp=?,level=?,zoom_link=?,monthly_fee=? WHERE id=?",
               (d["name"],d.get("group_name",""),d.get("teacher",""),d.get("whatsapp",""),d.get("level",""),d.get("zoom_link",""),d.get("monthly_fee",35),sid))
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
    return jsonify({"attendance":[dict(r) for r in rows]})

@app.route("/api/attendance", methods=["POST"])
@login_required
def api_attendance():
    d = request.json
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
    d = request.json
    db = get_db()
    db.execute("INSERT INTO tasks(title,department,assigned_to,priority,due_date,created_date,notes)VALUES(?,?,?,?,?,?,?)",
               (d["title"],d.get("department",""),d.get("assigned_to",""),d.get("priority","medium"),d.get("due_date",""),date.today().isoformat(),d.get("notes","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/tasks/<int:tid>", methods=["PUT"])
@login_required
def api_update_task(tid):
    d = request.json
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
    return jsonify({"violations":[dict(r) for r in rows]})

@app.route("/api/violations", methods=["POST"])
@login_required
def api_add_violation():
    d = request.json
    db = get_db()
    db.execute("INSERT INTO violations(student_name,title,description,points,date)VALUES(?,?,?,?,?)",
               (d["student_name"],d["title"],d.get("description",""),d.get("points",1),date.today().isoformat()))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/violations/<int:vid>", methods=["PUT"])
@login_required
def api_update_violation(vid):
    d = request.json
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
    return jsonify({"points":[dict(r) for r in rows]})

@app.route("/api/points", methods=["POST"])
@login_required
def api_add_points():
    d = request.json
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
    d = request.json
    db = get_db()
    db.execute("INSERT INTO payments(student_name,amount,status,date,notes)VALUES(?,?,?,?,?)",
               (d["student_name"],d.get("amount",35),d.get("status","pending"),d.get("date",date.today().isoformat()),d.get("notes","")))
    db.commit()
    return jsonify({"ok":True})

@app.route("/api/payments/<int:pid>", methods=["PUT"])
@login_required
def api_update_payment(pid):
    d = request.json
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
    d = request.json
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
    d = request.json
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
