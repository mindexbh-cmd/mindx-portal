from flask import Flask, request, session, redirect, g, jsonify
import sqlite3, hashlib, os, json
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
    if db:
        db.close()

def hp(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    db = sqlite3.connect(DB)
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
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    db.execute("""CREATE TABLE IF NOT EXISTS student_groups(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_name TEXT,
        teacher_name TEXT,
        level_course TEXT,
        last_reached TEXT,
        study_time TEXT,
        ramadan_time TEXT,
        online_time TEXT,
        group_link TEXT,
        session_duration TEXT,
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
    db.commit()
    db.close()

if not os.path.exists(DB):
    init_db()
else:
    db2 = sqlite3.connect(DB)
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
        ramadan_time TEXT,
        online_time TEXT,
        group_link TEXT,
        session_duration TEXT,
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
            ("personal_id","الرقم الشخصي",1),("student_name","اسم الطالب",2),("whatsapp","هاتف الواتساب المعتمد",3),
            ("class_name","الصف",4),("old_new_2026","قديم جديد 2026",5),("registration_term2_2026","تسجيل الفصل الثاني 2026",6),
            ("group_name_student","المجموعة",7),("group_online","المجموعة (الاونلاين)",8),("final_result","النتيجة النهائية (تحديد المستوى 2026)",9),
            ("level_reached_2026","الى اين وصل الطالب 2026",10),("suitable_level_2026","هل الطالب مناسب لهذا المستوى 2026؟",11),
            ("books_received","استلام الكتب",12),("teacher_2026","المدرس 2026",13),
            ("installment1","القسط الاول 2026",14),("installment2","القسط الثاني",15),("installment3","القسط الثالث",16),
            ("installment4","القسط الرابع",17),("installment5","القسط الخامس",18),
            ("mother_phone","هاتف الام",19),("father_phone","هاتف الاب",20),("other_phone","هاتف اخر",21),
            ("residence","مكان السكن",22),("home_address","عنوان المنزل",23),("road","الطريق",24),("complex_name","المجمع",25),
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
        ("suitable_level_2026", "TEXT"),
        ("books_received", "TEXT"),
        ("installment1", "TEXT"),
        ("installment2", "TEXT"),
        ("installment3", "TEXT"),
        ("installment4", "TEXT"),
        ("installment5", "TEXT"),
    ]
    existing = [row[1] for row in db2.execute("PRAGMA table_info(students)").fetchall()]
    for col, coltype in new_cols:
        if col not in existing:
            db2.execute("ALTER TABLE students ADD COLUMN " + col + " " + coltype)
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
<label>اسم المستخدم</label>
<input type="text" name="username" placeholder="username" required>
<label>كلمة المرور</label>
<input type="password" name="password" placeholder="password" required>
<button type="submit">دخول &larr;</button>
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
body{background:#fff;display:flex;align-items:center;justify-content:center;min-height:100vh;}
.btn{display:inline-block;padding:18px 48px;background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;border:none;border-radius:14px;font-size:18px;font-weight:700;cursor:pointer;text-decoration:none;letter-spacing:0.5px;}
.btn:hover{opacity:0.9;}
</style>
</head>
<body>
<a href="/database" class="btn">قاعدة البيانات</a>
<button class="btn-attend" onclick="document.getElementById('attModal').classList.add('open')">تسجيل الغياب &#128197;</button>
<div class="att-modal-bg" id="attModal">
  <div class="att-modal">
    <h2>رسالة الغياب ⚠️ تسجيل</h2>
    <div class="att-form-grid">
      <div class="att-field">
        <label>تاريخ أخذ الحضور</label>
        <input type="date" id="hm_att_date">
      </div>
      <div class="att-field">
        <label>اليوم</label>
        <input type="text" id="hm_att_day" placeholder="مثال: الأحد">
      </div>
      <div class="att-field">
        <label>المجموعة</label>
        <input type="text" id="hm_att_group" placeholder="اسم المجموعة">
      </div>
      <div class="att-field">
        <label>اسم الطالب</label>
        <input type="text" id="hm_att_student" placeholder="اسم الطالب">
      </div>
      <div class="att-field">
        <label>رقم التواصل</label>
        <input type="text" id="hm_att_contact" placeholder="رقم الواتسآب">
      </div>
      <div class="att-field">
        <label>الحالة</label>
        <select id="hm_att_status">
          <option value="">-- اختر --</option>
          <option>حاضر</option>
          <option>غائب</option>
          <option>متأخر</option>
          <option>معتذر</option>
        </select>
      </div>
      <div class="att-field full">
        <label>الرسالة</label>
        <textarea id="hm_att_message" rows="3" placeholder="نص الرسالة"></textarea>
      </div>
      <div class="att-field">
        <label>حالة إرسال الرسالة</label>
        <select id="hm_att_msg_status">
          <option value="">-- اختر --</option>
          <option>تم الإرسال</option>
          <option>لم يُرسل</option>
          <option>فشل الإرسال</option>
        </select>
      </div>
      <div class="att-field">
        <label>حالة الدراسة</label>
        <select id="hm_att_study_status">
          <option value="">-- اختر --</option>
          <option>مستمر</option>
          <option>منقطع</option>
          <option>موقوف</option>
        </select>
      </div>
    </div>
    <div class="att-modal-actions">
      <button class="att-btn-cancel" onclick="closeAttModal()">إلغاء</button>
      <button class="att-btn-save" onclick="saveAttRecord()">حفظ</button>
    </div>
  </div>
</div>
<div class="att-toast" id="attToast"></div>
<script>
function closeAttModal(){
  document.getElementById('attModal').classList.remove('open');
  ['hm_att_date','hm_att_day','hm_att_group','hm_att_student','hm_att_contact','hm_att_status','hm_att_message','hm_att_msg_status','hm_att_study_status'].forEach(function(id){
    var el=document.getElementById(id); if(el) el.value='';
  });
}
function showAttToast(msg,bg){
  var t=document.getElementById('attToast');
  t.textContent=msg; t.style.background=bg||'#00897B'; t.classList.add('show');
  setTimeout(function(){t.classList.remove('show');},3000);
}
function saveAttRecord(){
  var d={
    attendance_date:document.getElementById('hm_att_date').value,
    day_name:document.getElementById('hm_att_day').value,
    group_name:document.getElementById('hm_att_group').value,
    student_name:document.getElementById('hm_att_student').value,
    contact_number:document.getElementById('hm_att_contact').value,
    status:document.getElementById('hm_att_status').value,
    message:document.getElementById('hm_att_message').value,
    message_status:document.getElementById('hm_att_msg_status').value,
    study_status:document.getElementById('hm_att_study_status').value
  };
  fetch('/api/attendance',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)})
  .then(function(r){return r.json();})
  .then(function(res){
    if(res.ok){closeAttModal();showAttToast('تم حفظ سجل الغياب بنجاح ✅');}
    else{showAttToast('حدث خطأ. تأكد من تسجيل الدخول','#e53935');}
  }).catch(function(){showAttToast('حدث خطأ. تأكد من تسجيل الدخول','#e53935');});
}
document.getElementById('attModal').addEventListener('click',function(e){if(e.target===this)closeAttModal();});
</script>
</body>
</html>"""

DATABASE_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>قاعدة البيانات - Mindex</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Segoe UI',Tahoma,Arial,sans-serif;}
body{background:#f5f3ff;min-height:100vh;direction:rtl;}
.topbar{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between;}
.topbar h1{font-size:20px;font-weight:800;}
.btn-home{background:rgba(255,255,255,.18);color:#fff;border:1.5px solid rgba(255,255,255,.5);padding:8px 18px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;text-decoration:none;}
.btn-home:hover{background:rgba(255,255,255,.3);}
.main{padding:24px 28px;}
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
.table-wrap{background:#fff;border-radius:14px;box-shadow:0 2px 14px rgba(107,63,160,.1);overflow-x:auto;}
table{width:100%;border-collapse:collapse;min-width:2800px;}
thead tr{background:linear-gradient(135deg,#6B3FA0,#8B5CC8);color:#fff;}
th{padding:13px 12px;font-size:13px;font-weight:700;text-align:center;white-space:nowrap;}
tbody tr{border-bottom:1px solid #f0ebff;transition:background .15s;}
tbody tr:hover{background:#faf7ff;}
td{padding:11px 12px;font-size:13px;text-align:center;color:#444;} td.phone-cell{direction:ltr;unicode-bidi:embed;}
td.name-cell{font-weight:600;color:#6B3FA0;text-align:right;}
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
.btn-new-table{background:linear-gradient(135deg,#1976D2,#42A5F5);color:#fff;border:none;padding:10px 18px;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:6px;}
.btn-new-table:hover{opacity:0.9;}
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
</style>
</head>
<body>
<div class="topbar">
  <h1>الصفحة الرئيسية لمعلومات الطلبة</h1>
  <a href="/dashboard" class="btn-home">&larr; الرئيسية</a>
</div>
<div class="main">
  <div class="page-title-bar" style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;">
    <div class="page-title" style="margin-bottom:0;">قاعدة بيانات الطلبة</div>
    <a href="/groups" class="btn-groups" style="background:linear-gradient(135deg,#00BCD4,#0097A7);color:#fff;padding:11px 26px;border-radius:11px;font-size:15px;font-weight:700;text-decoration:none;display:inline-flex;align-items:center;gap:8px;">&#128101; معلومات المجموعات</a>
  </div>
  <div class="stats">
    <div class="stat-card">
      <span class="stat-num" id="totalCount">0</span>
      <span class="stat-label">إجمالي الطلبة</span>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:20px;"><button class="btn-add" style="margin-bottom:0;" onclick="openAddModal()">+ إضافة طالب</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#43A047,#2E7D32);" onclick="openStudentExcelModal()">&#128196; اضافة جدول</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openTableEditModal()">&#9881; تعديل الجدول</button>
  <button class="btn-new-table" onclick="openNewTableWizard()">&#10010; إضافة جدول جديد</button></div>
  <div class="search-bar">
    <input type="text" id="searchInput" placeholder="ابحث بالاسم أو الرقم الشخصي..." oninput="filterTable()">
    <button class="btn-search" onclick="filterTable()">بحث</button>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>الرقم الشخصي</th>
          <th>اسم الطالب</th>
          <th>هاتف الواتساب المعتمد</th>
          <th>الصف</th>
          <th>قديم جديد 2026</th>
          <th>تسجيل الفصل الثاني 2026</th>
          <th>المجموعة</th>
          <th>المجموعة (الاونلاين)</th>
          <th>النتيجة النهائية (تحديد المستوى 2026)</th>
          <th>الى اين وصل الطالب 2026</th>
          <th>هل الطالب مناسب لهذا المستوى 2026؟</th>
          <th>استلام الكتب</th>
          <th>المدرس 2026</th>
          <th>القسط الاول 2026</th>
          <th>القسط الثاني</th>
          <th>القسط الثالث</th>
          <th>القسط الرابع</th>
          <th>القسط الخامس</th>
          <th>هاتف الام</th>
          <th>هاتف الاب</th>
          <th>هاتف اخر</th>
          <th>مكان السكن</th>
          <th>عنوان المنزل</th>
          <th>الطريق</th>
          <th>المجمع</th>
          <th>اجراءات</th>
        </tr>
      </thead>
      <tbody id="studentsBody">
        <tr><td colspan="27" class="no-data">لا توجد بيانات، اضف اول طالب</td></tr>
      </tbody>
    </table>
  </div>

<!-- ===== GROUPS TABLE SECTION ===== -->
<div style="margin-top:40px;">
  <div style="font-size:20px;font-weight:800;color:#0097A7;margin-bottom:16px;">&#128101; معلومات المجموعات (يدوي)</div>
  <div class="stats">
    <div class="stat-card" style="border-top:3px solid #00BCD4;">
      <span class="stat-num" id="groupsTotalCount" style="color:#00BCD4;">0</span>
      <span class="stat-label">إجمالي المجموعات</span>
    </div>
  </div>
  <div style="display:flex;gap:10px;align-items:center;margin-bottom:20px;"><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#00BCD4,#0097A7);" onclick="openAddGroupModal2()">+ إضافة مجموعة</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#43A047,#2E7D32);" onclick="openGroupExcelModal()">&#128196; اضافة جدول</button><button class="btn-add" style="margin-bottom:0;background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="openGroupTableEditModal()">&#9881; تعديل الجدول</button></div>
  <div class="search-bar">
    <input type="text" id="groupSearchInput" placeholder="ابحث باسم المجموعة أو المدرس..." oninput="filterGroupTable2()">
    <button class="btn-search" style="background:#0097A7;" onclick="filterGroupTable2()">بحث</button>
  </div>
  <div class="table-wrap">
    <table style="min-width:1300px;">
      <thead>
        <tr id="groupsTheadRow" style="background:linear-gradient(135deg,#00BCD4,#0097A7);">
          <th>#</th><th>اسم المجموعة</th><th>اسم المدرس</th><th>المستوى / المقرر</th>
          <th>المقرر الذي تم الوصول اليه الفصل الفائت</th><th>وقت الدراسة</th>
          <th>توقيت شهر رمضان</th><th>توقيت الاونلاين (العادي)</th>
          <th>رابط المجموعة</th><th>الحصة بالدقيقة (يدوي)</th><th>اجراءات</th>
        </tr>
      </thead>
      <tbody id="groupsBody2">
        <tr><td colspan="11" class="no-data">لا توجد بيانات، اضف اول مجموعة</td></tr>
      </tbody>
    </table>
  </div>
</div>
</div>
<div class="modal-bg" id="modal">
  <div class="modal">
    <h2 id="modalTitle">اضافة طالب جديد</h2>
    <input type="hidden" id="editId">
    <div class="form-grid">
<div class="field"><label>الرقم الشخصي *</label><input id="f_personal_id" placeholder="الرقم الشخصي"></div>
<div class="field"><label>اسم الطالب *</label><input id="f_student_name" placeholder="الاسم الكامل"></div>
<div class="field"><label>هاتف الواتساب المعتمد</label><input id="f_whatsapp" placeholder="+973 XXXX XXXX" class="ltr"></div>
<div class="field"><label>الصف</label><input id="f_class_name" placeholder="مثال: صف A"></div>
<div class="field"><label>قديم جديد 2026</label><input id="f_old_new_2026" placeholder="قديم أو جديد"></div>
<div class="field"><label>تسجيل الفصل الثاني 2026</label><input id="f_registration_term2_2026" placeholder="نعم / لا"></div>
<div class="field"><label>المجموعة</label><input id="f_group_name_student" placeholder="اسم المجموعة"></div>
<div class="field"><label>المجموعة (الاونلاين)</label><input id="f_group_online" placeholder="مجموعة الاونلاين"></div>
<div class="field"><label>النتيجة النهائية (تحديد المستوى 2026)</label><select id="f_final_result"><option value="">-- اختر --</option><option>ناجح</option><option>راسب</option><option>قيد التقييم</option><option>غائب</option></select></div>
<div class="field"><label>الى اين وصل الطالب 2026</label><input id="f_level_reached" placeholder="مثال: الوحدة 5"></div>
<div class="field"><label>هل الطالب مناسب لهذا المستوى 2026؟</label><input id="f_suitable_level" placeholder="نعم / لا"></div>
<div class="field"><label>استلام الكتب</label><input id="f_books_received" placeholder="نعم / لا"></div>
<div class="field"><label>المدرس 2026</label><input id="f_teacher" placeholder="اسم المدرس"></div>
<div class="field"><label>القسط الاول 2026</label><input id="f_installment1" placeholder="مدفوع / غير مدفوع"></div>
<div class="field"><label>القسط الثاني</label><input id="f_installment2" placeholder="مدفوع / غير مدفوع"></div>
<div class="field"><label>القسط الثالث</label><input id="f_installment3" placeholder="مدفوع / غير مدفوع"></div>
<div class="field"><label>القسط الرابع</label><input id="f_installment4" placeholder="مدفوع / غير مدفوع"></div>
<div class="field"><label>القسط الخامس</label><input id="f_installment5" placeholder="مدفوع / غير مدفوع"></div>
<div class="field"><label>هاتف الام</label><input id="f_mother_phone" placeholder="+973 XXXX XXXX" class="ltr"></div>
<div class="field"><label>هاتف الاب</label><input id="f_father_phone" placeholder="+973 XXXX XXXX" class="ltr"></div>
<div class="field"><label>هاتف اخر</label><input id="f_other_phone" placeholder="+973 XXXX XXXX" class="ltr"></div>
<div class="field"><label>مكان السكن</label><input id="f_residence" placeholder="المنطقة"></div>
<div class="field full"><label>عنوان المنزل</label><input id="f_home_address" placeholder="عنوان المنزل"></div>
<div class="field"><label>الطريق</label><input id="f_road" placeholder="رقم الطريق"></div>
<div class="field"><label>المجمع</label><input id="f_complex" placeholder="اسم المجمع"></div>
</div>
    v>
    </div>
    <div class="modal-actions">
      <button class="btn-save" onclick="saveStudent()">حفظ</button>
      <button class="btn-cancel" onclick="closeModal()">الغاء</button>
    </div>
  </div>
</div>
<div class="confirm-bg" id="confirmModal">
  <div class="confirm-box">
    <h3>تاكيد الحذف</h3>
    <p>هل انت متاكد انك تريد حذف هذا الطالب؟ لا يمكن التراجع عن هذا الاجراء.</p>
    <div class="confirm-actions">
      <button class="btn-confirm-del" id="confirmDelBtn">حذف</button>
      <button class="btn-confirm-cancel" onclick="closeConfirm()">الغاء</button>
    </div>
  </div>
</div>
<!-- TABLE EDIT MODAL -->
<div class="modal-bg" id="tableEditModal">
<div class="modal" style="border-top:4px solid #FF6B35;max-width:560px;">
<h2 style="color:#E55A2B;">&#9881; تعديل الجدول</h2>
<div style="display:flex;gap:8px;margin-bottom:20px;border-bottom:2px solid #f0ebff;padding-bottom:10px;">
<button id="tab-add-col" onclick="switchTab('add-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#FF6B35;color:#fff;font-weight:700;cursor:pointer;font-size:13px;">➕ إضافة عمود</button>
<button id="tab-del-col" onclick="switchTab('del-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#f0ebff;color:#6B3FA0;font-weight:700;cursor:pointer;font-size:13px;">❌ حذف عمود</button>
<button id="tab-edit-col" onclick="switchTab('edit-col')" style="padding:8px 16px;border-radius:8px;border:none;background:#f0ebff;color:#6B3FA0;font-weight:700;cursor:pointer;font-size:13px;">&#9998; تعديل عنوان</button>
</div>
<!-- Tab: Add Column -->
<div id="panel-add-col">
<div class="field" style="margin-bottom:14px;"><label style="color:#E55A2B;">عنوان العمود الجديد *</label><input id="new_col_label" placeholder="مثال: ملاحظات" style="width:100%;padding:10px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;"></div>
<div class="field" style="margin-bottom:14px;">
  <label style="color:#E55A2B;">موقع العمود الجديد</label>
  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
    <select id="new_col_position" onchange="togglePositionCol()" style="padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:0 0 auto;">
      <option value="end">في النهاية</option>
      <option value="start">في البداية</option>
      <option value="after">بعد عمود:</option>
    </select>
    <select id="new_col_after" style="display:none;padding:9px 12px;border:1.5px solid #ffd4c2;border-radius:9px;font-size:14px;background:#fff9f7;flex:1;">
      <option value="">— اختر العمود —</option>
    </select>
  </div>
</div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:linear-gradient(135deg,#FF6B35,#E55A2B);" onclick="addColumn()">إضافة عمود</button>
</div>
</div>
<!-- Tab: Delete Column -->
<div id="panel-del-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#e53935;">اختر العمود للحذف *</label>
<select id="del_col_key" style="width:100%;padding:10px;border:1.5px solid #fce4ec;border-radius:9px;font-size:14px;background:#fff9f9;"><option value="">— اختر عمود —</option></select></div>
<div style="background:#fff3f3;border-radius:8px;padding:10px;font-size:12px;color:#c62828;margin-bottom:12px;">⚠️ تحذير: حذف العمود يحذف جميع بياناته من كل الطلبة. لا يمكن التراجع.</div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" style="background:#e53935;" onclick="deleteColumn()">حذف العمود</button>
</div>
</div>
<!-- Tab: Edit Column Label -->
<div id="panel-edit-col" style="display:none;">
<div class="field" style="margin-bottom:14px;"><label style="color:#6B3FA0;">اختر العمود *</label>
<select id="edit_col_key" onchange="fillEditLabel()" style="width:100%;padding:10px;border:1.5px solid #E0D5F0;border-radius:9px;font-size:14px;background:#faf7ff;"><option value="">— اختر عمود —</option></select></div>
<div class="field" style="margin-bottom:14px;"><label style="color:#6B3FA0;">الاسم الجديد *</label><input id="edit_col_label" placeholder="اسم العمود" style="width:100%;padding:10px;border:1.5px solid #E0D5F0;border-radius:9px;font-size:14px;background:#faf7ff;"></div>
<div class="modal-actions" style="justify-content:flex-start;margin-top:10px;">
<button class="btn-save" onclick="updateColumnLabel()">حفظ العنوان</button>
</div>
</div>
<div class="modal-actions" style="margin-top:18px;justify-content:center;">
<button class="btn-cancel" onclick="closeTableEditModal()">إغلاق</button>
</div>
</div>
</div>
<!-- STUDENT EXCEL IMPORT MODAL --><div class="modal-bg" id="studentExcelModal"><div class="modal" style="border-top:4px solid #43A047;max-width:500px;"><h2 style="color:#2E7D32;">&#128196; استيراد طلبة من Excel</h2><div style="margin-bottom:16px;background:#f1f8e9;border-radius:10px;padding:14px;font-size:13px;color:#33691e;direction:rtl;"><b>تعليمات:</b> يجب أن يكون ملف Excel يحتوي على الأعمدة بهذا الترتيب:<br>الرقم الشخصي، اسم الطالب، الواتساب، النتيجة، المستوى 2026، المدرس 2026، هاتف الام، هاتف الاب، هاتف اخر، السكن، العنوان، الطريق، المجمع</div><div style="text-align:center;margin:20px 0;"><input type="file" id="studentExcelFile" accept=".xlsx,.xls,.csv" style="display:none;"><button onclick="document.getElementById('studentExcelFile').click();" style="background:#43A047;color:#fff;border:none;padding:12px 28px;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;">&#128193; اختر ملف Excel</button><div id="studentExcelFileName" style="margin-top:10px;font-size:13px;color:#666;">لم يتم اختيار ملف</div></div><div id="studentExcelPreview" style="display:none;margin-bottom:14px;"><div style="font-size:13px;color:#2E7D32;font-weight:700;margin-bottom:6px;" id="studentExcelCount"></div></div><div class="modal-actions"><button class="btn-save" id="studentExcelImportBtn" style="background:linear-gradient(135deg,#43A047,#2E7D32);display:none;" onclick="importStudentsFromExcel()">استيراد</button><button class="btn-cancel" onclick="closeStudentExcelModal()">الغاء</button></div></div></div><!-- GROUP EXCEL IMPORT MODAL --><div class="modal-bg" id="groupExcelModal"><div class="modal" style="border-top:4px solid #43A047;max-width:500px;"><h2 style="color:#2E7D32;">&#128196; استيراد مجموعات من Excel</h2><div style="margin-bottom:16px;background:#f1f8e9;border-radius:10px;padding:14px;font-size:13px;color:#33691e;direction:rtl;"><b>تعليمات:</b> يجب أن يكون ملف Excel يحتوي على الأعمدة بهذا الترتيب:<br>اسم المجموعة، اسم المدرس، المستوى، المقرر الفائت، وقت الدراسة، توقيت رمضان، توقيت الاونلاين، رابط المجموعة، الحصة بالدقيقة</div><div style="text-align:center;margin:20px 0;"><input type="file" id="groupExcelFile" accept=".xlsx,.xls,.csv" style="display:none;"><button onclick="document.getElementById('groupExcelFile').click();" style="background:#43A047;color:#fff;border:none;padding:12px 28px;border-radius:10px;font-size:15px;font-weight:700;cursor:pointer;">&#128193; اختر ملف Excel</button><div id="groupExcelFileName" style="margin-top:10px;font-size:13px;color:#666;">لم يتم اختيار ملف</div></div><div id="groupExcelPreview" style="display:none;margin-bottom:14px;"><div style="font-size:13px;color:#2E7D32;font-weight:700;margin-bottom:6px;" id="groupExcelCount"></div></div><div class="modal-actions"><button class="btn-save" id="groupExcelImportBtn" style="background:linear-gradient(135deg,#43A047,#2E7D32);display:none;" onclick="importGroupsFromExcel()">استيراد</button><button class="btn-cancel" onclick="closeGroupExcelModal()">الغاء</button></div></div></div><div style="margin:30px 0 0 0;">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
    <span style="font-size:1.3em;font-weight:700;color:#6c3fa0;">&#128197; سجل الغياب</span>
  </div>
  <div class="stats" style="margin-bottom:10px;">
    <div class="stat-card">
      <span class="stat-num" id="attendanceTotalCount">0</span>
      <span class="stat-label">إجمالي السجلات</span>
    </div>
  </div>
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
    <button class="btn-add" onclick="openAttendanceAddModal()">+ إضافة سجل</button>
  
  <button class="btn-add" style="background:linear-gradient(135deg,#388E3C,#66BB6A);" onclick="openAttendanceExcelModal()">&#128196; اضافة جدول</button>
  <button class="btn-add" style="background:linear-gradient(135deg,#E65100,#FFA726);" onclick="openAttendanceTableEditModal()">&#9881; تعديل الجدول</button></div>
  <div class="search-bar">
    <input type="text" id="attendanceSearchInput" placeholder="ابحث في سجل الغياب..." oninput="filterAttendanceTable()">
    <button class="btn-search" onclick="filterAttendanceTable()">بحث</button>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>تاريخ أخذ الحضور</th>
          <th>اليوم</th>
          <th>المجموعة</th>
          <th>اسم الطالب</th>
          <th>رقم التواصل</th>
          <th>الحالة</th>
          <th>الرسالة</th>
          <th>حالة إرسال الرسالة</th>
          <th>حالة الدراسة</th>
          <th>إجراءات</th>
        </tr>
      </thead>
      <tbody id="attendanceBody"></tbody>
    </table>
  </div>
</div>
<!-- ATTENDANCE ADD/EDIT MODAL -->
<div class="modal-bg" id="attendanceModal" style="display:none">
  <div class="modal" style="max-width:520px;width:95%">
    <h2 id="attendanceModalTitle" style="margin-bottom:16px;color:#6c3fa0;">إضافة سجل غياب</h2>
    <div style="display:flex;flex-direction:column;gap:10px;">
      <div style="display:flex;gap:10px;">
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">تاريخ أخذ الحضور</label>
          <input type="date" id="att_date" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">اليوم</label>
          <input type="text" id="att_day" placeholder="مثال: الأحد" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">المجموعة</label>
          <input type="text" id="att_group" placeholder="اسم المجموعة" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">اسم الطالب</label>
          <input type="text" id="att_student" placeholder="اسم الطالب" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
      </div>
      <div style="display:flex;gap:10px;">
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">رقم التواصل</label>
          <input type="text" id="att_contact" placeholder="رقم الواتساب" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
        </div>
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">الحالة</label>
          <select id="att_status" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
            <option value="">-- اختر --</option>
            <option>حاضر</option>
            <option>غائب</option>
            <option>متأخر</option>
            <option>معتذر</option>
          </select>
        </div>
      </div>
      <div>
        <label style="font-size:.85em;color:#555;">الرسالة</label>
        <textarea id="att_message" rows="3" placeholder="نص الرسالة" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;resize:vertical;"></textarea>
      </div>
      <div style="display:flex;gap:10px;">
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">حالة إرسال الرسالة</label>
          <select id="att_msg_status" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
            <option value="">-- اختر --</option>
            <option>تم الإرسال</option>
            <option>لم يُرسل</option>
            <option>فشل الإرسال</option>
          </select>
        </div>
        <div style="flex:1">
          <label style="font-size:.85em;color:#555;">حالة الدراسة</label>
          <select id="att_study_status" style="width:100%;padding:7px;border:1px solid #ccc;border-radius:6px;">
            <option value="">-- اختر --</option>
            <option>مستمر</option>
            <option>منقطع</option>
            <option>موقوف</option>
          </select>
        </div>
      </div>
    </div>
    <div style="display:flex;gap:10px;margin-top:16px;justify-content:flex-end;">
      <button class="btn-cancel" onclick="closeAttendanceModal()">الغاء</button>
      <button class="btn-save" onclick="saveAttendanceRecord()">حفظ</button>
    </div>
  </div>
</div>
<!-- ATTENDANCE CONFIRM DELETE MODAL -->
<div class="confirm-bg" id="attendanceConfirmModal" style="display:none">
  <div class="confirm-box">
    <p>هل تريد حذف هذا السجل؟</p>
    <div style="display:flex;gap:10px;justify-content:center;">
      <button class="btn-cancel" onclick="closeAttendanceConfirm()">الغاء</button>
      <button class="btn-delete" onclick="confirmAttendanceDelete()">حذف</button>
    </div>
  </div>
</div>
<!-- ATTENDANCE EXCEL IMPORT MODAL -->
<div class="modal-bg" id="attendanceExcelModal" style="display:none">
  <div class="modal" style="max-width:480px;width:95%">
    <h2 style="margin-bottom:14px;color:#388E3C;">&#128196; استيراد سجل غياب من Excel</h2>
    <div style="background:#f1f8e9;border-radius:8px;padding:12px;margin-bottom:14px;font-size:.88em;color:#2E7D32;line-height:1.7;">
      <b>تعليمات:</b> يجب أن يحتوي ملف Excel على الأعمدة بهذا الترتيب:<br>
      تاريخ أخذ الحضور، اليوم، المجموعة، اسم الطالب، رقم التواصل، الحالة، الرسالة، حالة إرسال الرسالة، حالة الدراسة
    </div>
    <button class="btn-add" style="width:100%;justify-content:center;" onclick="document.getElementById('attendanceExcelFileInput').click()">&#128194; اختر ملف Excel</button>
    <input type="file" id="attendanceExcelFileInput" accept=".xlsx,.xls,.csv" style="display:none" onchange="readAttendanceExcelFile(this)">
    <div id="attendanceExcelStatus" style="margin-top:10px;font-size:.9em;color:#555;text-align:center;"></div>
    <div style="display:flex;gap:10px;margin-top:14px;justify-content:flex-end;">
      <button class="btn-cancel" onclick="closeAttendanceExcelModal()">الغاء</button>
      <button class="btn-save" id="attendanceExcelImportBtn" onclick="importAttendanceFromExcel()" style="display:none">استيراد</button>
    </div>
  </div>
</div>

<!-- ATTENDANCE TABLE EDIT MODAL -->
<div class="modal-bg" id="attendanceTableEditModal" style="display:none">
  <div class="modal" style="max-width:460px;width:95%">
    <h2 style="margin-bottom:12px;color:#E65100;font-size:1.1em;">&#9881; تعديل جدول سجل الغياب</h2>
    <div style="display:flex;gap:6px;margin-bottom:14px;">
      <button class="btn-tab active" id="attTab1" onclick="switchAttTab('add')">إضافة عمود</button>
      <button class="btn-tab" id="attTab2" onclick="switchAttTab('del')">حذف عمود</button>
      <button class="btn-tab" id="attTab3" onclick="switchAttTab('rename')">تعديل عنوان</button>
    </div>
    <!-- Add column panel -->
    <div id="attTabPanelAdd">
      <label style="font-size:.85em;color:#555;display:block;margin-bottom:4px;">اسم العمود الجديد</label>
      <input type="text" id="att_new_col_name" placeholder="اسم العمود" class="col-name-input">
      <div style="margin:8px 0 4px 0;font-size:.85em;color:#555;">مكان الإضافة:</div>
      <select id="att_col_position" class="col-name-input" onchange="toggleAttPosition()">
        <option value="end">في النهاية</option>
        <option value="start">في البداية</option>
        <option value="after">بعد عمود:</option>
      </select>
      <select id="att_after_col" class="col-name-input" style="display:none;margin-top:6px;"></select>
      <button class="btn-save" style="margin-top:10px;width:100%;" onclick="addAttendanceColumn()">إضافة</button>
    </div>
    <!-- Delete column panel -->
    <div id="attTabPanelDel" style="display:none">
      <label style="font-size:.85em;color:#555;display:block;margin-bottom:4px;">اختر العمود للحذف</label>
      <select id="att_del_col" class="col-name-input"></select>
      <button style="margin-top:10px;width:100%;padding:10px;border:none;border-radius:8px;font-weight:700;cursor:pointer;background:#e53935;color:#fff;" onclick="deleteAttendanceColumn()">حذف العمود</button>
    </div>
    <!-- Rename column panel -->
    <div id="attTabPanelRename" style="display:none">
      <label style="font-size:.85em;color:#555;display:block;margin-bottom:4px;">اختر العمود</label>
      <select id="att_rename_col" class="col-name-input" onchange="fillAttRenameLabel()"></select>
      <label style="font-size:.85em;color:#555;display:block;margin-top:8px;margin-bottom:4px;">الاسم الجديد</label>
      <input type="text" id="att_rename_label" class="col-name-input" placeholder="الاسم الجديد">
      <button class="btn-save" style="margin-top:10px;width:100%;" onclick="updateAttendanceColumnLabel()">حفظ</button>
    </div>
    <div style="margin-top:14px;text-align:left;">
      <button class="btn-cancel" onclick="closeAttendanceTableEditModal()">إغلاق</button>
    </div>
  </div>
</div>
<!-- DYNAMIC CUSTOM TABLES CONTAINER -->
<div id="customTablesContainer"></div>

<!-- NEW TABLE WIZARD MODAL -->
<div class="modal-bg" id="newTableWizardModal" style="display:none">
  <div class="modal" style="max-width:540px;width:96%">
    <h2 style="margin-bottom:6px;color:#1565C0;">&#10010; إنشاء جدول جديد</h2>
    <div class="step-indicator">
      <div class="step-dot active" id="wizDot1"></div>
      <div class="step-dot" id="wizDot2"></div>
    </div>
    <!-- Step 1: Name + cols/rows count -->
    <div class="wizard-step active" id="wizStep1">
      <div style="margin-bottom:12px;">
        <label style="font-size:.87em;color:#555;display:block;margin-bottom:4px;">اسم الجدول</label>
        <input type="text" id="wiz_tbl_name" placeholder="مثال: سجل التقدم" class="col-name-input">
      </div>
      <div style="display:flex;gap:12px;">
        <div style="flex:1">
          <label style="font-size:.87em;color:#555;display:block;margin-bottom:4px;">عدد الأعمدة</label>
          <input type="number" id="wiz_col_count" min="1" max="20" value="3" class="col-name-input" style="width:100%;">
        </div>
        <div style="flex:1">
          <label style="font-size:.87em;color:#555;display:block;margin-bottom:4px;">عدد الصفوف الابتدائية</label>
          <input type="number" id="wiz_row_count" min="0" max="100" value="0" class="col-name-input" style="width:100%;">
        </div>
      </div>
      <div class="wizard-nav">
        <button class="btn-cancel" onclick="closeNewTableWizard()">إلغاء</button>
        <button class="btn-save" onclick="wizardStep1Next()">التالي &#8594;</button>
      </div>
    </div>
    <!-- Step 2: Column names -->
    <div class="wizard-step" id="wizStep2">
      <p style="font-size:.9em;color:#555;margin-bottom:10px;">أدخل أسماء الأعمدة:</p>
      <div id="wizColNamesContainer"></div>
      <div class="wizard-nav">
        <button class="btn-cancel" onclick="wizardGoBack()">&#8592; رجوع</button>
        <button class="btn-save" onclick="wizardCreateTable()">&#10003; إنشاء الجدول</button>
      </div>
    </div>
  </div>
</div>

<!-- CUSTOM TABLE EDIT MODAL (add/delete/rename cols) -->
<div class="modal-bg" id="customTableEditModal" style="display:none">
  <div class="modal" style="max-width:480px;width:96%">
    <h2 id="customTableEditTitle" style="margin-bottom:12px;color:#1565C0;font-size:1.1em;">⚙ تعديل الجدول</h2>
    <div style="display:flex;gap:6px;margin-bottom:14px;" id="customTblTabBtns">
      <button class="btn-tab active" id="ctab1" onclick="switchCustomTab('add')">إضافة عمود</button>
      <button class="btn-tab" id="ctab2" onclick="switchCustomTab('del')">حذف عمود</button>
      <button class="btn-tab" id="ctab3" onclick="switchCustomTab('rename')">تعديل عنوان</button>
    </div>
    <div id="ctabPanelAdd">
      <input type="text" id="ctbl_new_col_name" placeholder="اسم العمود الجديد" class="col-name-input">
      <div style="margin:8px 0 4px 0;font-size:.85em;color:#555;">مكان الإضافة:</div>
      <select id="ctbl_position" class="col-name-input" onchange="toggleCustomPosition()">
        <option value="end">في النهاية</option>
        <option value="start">في البداية</option>
        <option value="after">بعد عمود:</option>
      </select>
      <select id="ctbl_after_col" class="col-name-input" style="display:none;margin-top:6px;"></select>
      <button class="btn-save" style="margin-top:10px;width:100%;" onclick="addCustomColumn()">إضافة</button>
    </div>
    <div id="ctabPanelDel" style="display:none">
      <select id="ctbl_del_col" class="col-name-input"></select>
      <button class="btn-delete" style="margin-top:10px;width:100%;padding:10px;border:none;border-radius:8px;font-weight:700;cursor:pointer;background:#e53935;color:#fff;" onclick="deleteCustomColumn()">حذف العمود</button>
    </div>
    <div id="ctabPanelRename" style="display:none">
      <select id="ctbl_rename_col" class="col-name-input" onchange="fillCustomRenameLabel()"></select>
      <input type="text" id="ctbl_rename_label" placeholder="الاسم الجديد" class="col-name-input" style="margin-top:8px;">
      <button class="btn-save" style="margin-top:10px;width:100%;" onclick="updateCustomColumnLabel()">حفظ التعديل</button>
    </div>
    <div style="margin-top:14px;text-align:left;">
      <button class="btn-cancel" onclick="closeCustomTableEditModal()">إغلاق</button>
    </div>
  </div>
</div>

<!-- ADD ROW MODAL FOR CUSTOM TABLE -->
<div class="modal-bg" id="customRowModal" style="display:none">
  <div class="modal" style="max-width:500px;width:96%">
    <h2 id="customRowModalTitle" style="margin-bottom:14px;color:#1565C0;font-size:1.1em;">إضافة صف</h2>
    <div id="customRowFormFields" style="display:flex;flex-direction:column;gap:10px;"></div>
    <div style="display:flex;gap:10px;margin-top:16px;justify-content:flex-end;">
      <button class="btn-cancel" onclick="closeCustomRowModal()">إلغاء</button>
      <button class="btn-save" onclick="saveCustomRow()">حفظ</button>
    </div>
  </div>
</div>

<!-- CONFIRM DELETE CUSTOM TABLE -->
<div class="confirm-bg" id="customTableDeleteConfirm" style="display:none">
  <div class="confirm-box">
    <p id="customTableDeleteMsg">هل تريد حذف هذا الجدول؟</p>
    <div style="display:flex;gap:10px;justify-content:center;">
      <button class="btn-cancel" onclick="closeCustomTableDeleteConfirm()">إلغاء</button>
      <button style="background:#e53935;color:#fff;border:none;padding:10px 22px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;" onclick="confirmCustomTableDelete()">حذف</button>
    </div>
  </div>
</div>
<div class="toast" id="toast"></div>
<div class="modal-bg" id="groupModal2">
  <div class="modal" style="border-top:4px solid #00BCD4;">
    <h2 id="groupModalTitle2" style="color:#0097A7;">اضافة مجموعة جديدة</h2>
    <input type="hidden" id="groupEditId2">
    <div class="form-grid">
      <div class="field"><label style="color:#0097A7;">اسم المجموعة *</label><input id="gf2_group_name" placeholder="اسم المجموعة" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">اسم المدرس</label><input id="gf2_teacher_name" placeholder="اسم المدرس" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">المستوى / المقرر</label><input id="gf2_level_course" placeholder="مثال: المستوى 3" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">المقرر الذي تم الوصول اليه الفصل الفائت</label><input id="gf2_last_reached" placeholder="مثال: الوحدة 5" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">وقت الدراسة</label><input id="gf2_study_time" placeholder="مثال: السبت 4-5 مساء" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">توقيت شهر رمضان</label><input id="gf2_ramadan_time" placeholder="مثال: 8-9 مساء" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">توقيت الاونلاين (العادي)</label><input id="gf2_online_time" placeholder="مثال: 5-6 مساء" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">رابط المجموعة</label><input id="gf2_group_link" placeholder="https://..." class="ltr" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field full"><label style="color:#0097A7;">الحصة بالدقيقة (يدوي)</label><input id="gf2_session_duration" placeholder="مثال: 60 دقيقة" style="border-color:#b2ebf2;background:#f0fdff;"></div>
    </div>
    <div class="modal-actions">
      <button class="btn-save" style="background:linear-gradient(135deg,#00BCD4,#0097A7);" onclick="saveGroup2()">حفظ</button>
      <button class="btn-cancel" style="background:#e0f7fa;color:#0097A7;" onclick="closeGroupModal2()">الغاء</button>
    </div>
  </div>
</div>
<div class="confirm-bg" id="groupConfirmModal2">
  <div class="confirm-box">
    <h3>تاكيد الحذف</h3>
    <p>هل انت متاكد من حذف هذه المجموعة؟</p>
    <div class="confirm-actions">
      <button class="btn-confirm-del" id="groupConfirmDelBtn2">حذف</button>
      <button class="btn-confirm-cancel" onclick="closeGroupConfirm2()">الغاء</button>
    </div>
  </div>
</div>
<!-- GROUP TABLE EDIT MODAL -->
<div class="modal-bg" id="groupTableEditModal">
<div class="modal" style="border-top:4px solid #FF6B35;max-width:560px;">
<h2 style="color:#E55A2B;">&#9881; تعديل جدول المجموعات</h2>
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
<script src="https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js"></script>
<script>
let allStudents=[];
let deleteTargetId=null;
var allColumns=[];
async function loadStudents(){
const [sRes,cRes]=await Promise.all([fetch('/api/students'),fetch('/api/columns')]);
const sData=await sRes.json(); const cData=await cRes.json();
allStudents=sData.students||[]; allColumns=cData.columns||[];
renderTable(allStudents);
document.getElementById('totalCount').textContent=allStudents.length;
buildTableHeader();
}
function buildTableHeader(){
var thead=document.querySelector('#studentsBody').closest('table').querySelector('thead tr');
if(!thead)return;
var html='<th>#</th>';
for(var i=0;i<allColumns.length;i++){html+='<th>'+allColumns[i].col_label+'</th>';}
html+='<th>اجراءات</th>';
thead.innerHTML=html;
}
function renderTable(list){
var body=document.getElementById('studentsBody');
var colCount=allColumns.length+2;
if(!list.length){body.innerHTML='<tr><td colspan="'+colCount+'" class="no-data">لا توجد بيانات، اضف اول طالب</td></tr>';return;}
var html='';
for(var i=0;i<list.length;i++){
var s2=list[i];
var row='<tr><td>'+(i+1)+'</td>';
for(var j=0;j<allColumns.length;j++){
var key=allColumns[j].col_key;
var val=s2[key]||'';
if(key==='personal_id'){row+='<td><b>'+val+'</b></td>';}
else if(key==='student_name'){row+='<td class="name-cell">'+val+'</td>';}
else if(key==='final_result'){
var badge=val==='ناجح'?'badge-pass':val==='راسب'?'badge-fail':'badge-pend';
row+='<td>'+(val?'<span class="badge '+badge+'">'+val+'</span>':'-')+'</td>';
}else{row+='<td>'+(val||'-')+'</td>';}
}
row+='<td><button class="action-btn btn-edit" onclick="openEdit('+s2.id+')">&#9998;</button><button class="action-btn btn-del" onclick="askDelete('+s2.id+')">&#128465;</button></td></tr>';
html+=row;
}
body.innerHTML=html;
}
function filterTable(){
  const q=document.getElementById('searchInput').value.toLowerCase();
  renderTable(allStudents.filter(s=>(s.student_name||'').toLowerCase().includes(q)||(s.personal_id||'').toLowerCase().includes(q)));
}
function clearForm(){ ['personal_id','student_name','whatsapp','class_name','old_new_2026','registration_term2_2026','group_name_student','group_online','final_result','level_reached','suitable_level','books_received','teacher','installment1','installment2','installment3','installment4','installment5','mother_phone','father_phone','other_phone','residence','home_address','road','complex'].forEach(k=>{const el=document.getElementById('f_'+k);if(el)el.value='';}); document.getElementById('editId').value=''; } function openAddModal(){clearForm();document.getElementById('modalTitle').textContent='اضافة طالب جديد';document.getElementById('modal').classList.add('open');}
function openEdit(id){ const s=allStudents.find(x=>x.id===id);if(!s)return; document.getElementById('editId').value=id; document.getElementById('modalTitle').textContent='تعديل بيانات الطالب'; document.getElementById('f_personal_id').value=s.personal_id||''; document.getElementById('f_student_name').value=s.student_name||''; document.getElementById('f_whatsapp').value=s.whatsapp||''; document.getElementById('f_class_name').value=s.class_name||''; document.getElementById('f_old_new_2026').value=s.old_new_2026||''; document.getElementById('f_registration_term2_2026').value=s.registration_term2_2026||''; document.getElementById('f_group_name_student').value=s.group_name_student||''; document.getElementById('f_group_online').value=s.group_online||''; document.getElementById('f_final_result').value=s.final_result||''; document.getElementById('f_level_reached').value=s.level_reached_2026||''; document.getElementById('f_suitable_level').value=s.suitable_level_2026||''; document.getElementById('f_books_received').value=s.books_received||''; document.getElementById('f_teacher').value=s.teacher_2026||''; document.getElementById('f_installment1').value=s.installment1||''; document.getElementById('f_installment2').value=s.installment2||''; document.getElementById('f_installment3').value=s.installment3||''; document.getElementById('f_installment4').value=s.installment4||''; document.getElementById('f_installment5').value=s.installment5||''; document.getElementById('f_mother_phone').value=s.mother_phone||''; document.getElementById('f_father_phone').value=s.father_phone||''; document.getElementById('f_other_phone').value=s.other_phone||''; document.getElementById('f_residence').value=s.residence||''; document.getElementById('f_home_address').value=s.home_address||''; document.getElementById('f_road').value=s.road||''; document.getElementById('f_complex').value=s.complex_name||''; document.getElementById('modal').classList.add('open'); } function closeModal(){document.getElementById('modal').classList.remove('open');}
async function saveStudent(){ const editId=document.getElementById('editId').value; const body={ personal_id:document.getElementById('f_personal_id').value.trim(), student_name:document.getElementById('f_student_name').value.trim(), whatsapp:document.getElementById('f_whatsapp').value.trim(), class_name:document.getElementById('f_class_name').value.trim(), old_new_2026:document.getElementById('f_old_new_2026').value.trim(), registration_term2_2026:document.getElementById('f_registration_term2_2026').value.trim(), group_name_student:document.getElementById('f_group_name_student').value.trim(), group_online:document.getElementById('f_group_online').value.trim(), final_result:document.getElementById('f_final_result').value, level_reached_2026:document.getElementById('f_level_reached').value.trim(), suitable_level_2026:document.getElementById('f_suitable_level').value.trim(), books_received:document.getElementById('f_books_received').value.trim(), teacher_2026:document.getElementById('f_teacher').value.trim(), installment1:document.getElementById('f_installment1').value.trim(), installment2:document.getElementById('f_installment2').value.trim(), installment3:document.getElementById('f_installment3').value.trim(), installment4:document.getElementById('f_installment4').value.trim(), installment5:document.getElementById('f_installment5').value.trim(), mother_phone:document.getElementById('f_mother_phone').value.trim(), father_phone:document.getElementById('f_father_phone').value.trim(), other_phone:document.getElementById('f_other_phone').value.trim(), residence:document.getElementById('f_residence').value.trim(), home_address:document.getElementById('f_home_address').value.trim(), road:document.getElementById('f_road').value.trim(), complex_name:document.getElementById('f_complex').value.trim(), }; if(!body.personal_id||!body.student_name){showToast('الرقم الشخصي واسم الطالب مطلوبان','#e53935');return;} const url=editId?'/api/students/'+editId:'/api/students'; const method=editId?'PUT':'POST'; const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); const data=await res.json(); if(data.ok){closeModal();showToast(editId?'تم تعديل بيانات الطالب بنجاح':'تم اضافة الطالب بنجاح');loadStudents();} else{showToast(data.error||'حدث خطا','#e53935');} } function askDelete(id){deleteTargetId=id;document.getElementById('confirmModal').classList.add('open');document.getElementById('confirmDelBtn').onclick=confirmDelete;}
async function confirmDelete(){
  if(!deleteTargetId)return;
  const res=await fetch('/api/students/'+deleteTargetId,{method:'DELETE'});
  const data=await res.json();
  closeConfirm();
  if(data.ok){showToast('تم حذف الطالب بنجاح');loadStudents();}
  else{showToast(data.error||'حدث خطا في الحذف','#e53935');}
  deleteTargetId=null;
}
function closeConfirm(){document.getElementById('confirmModal').classList.remove('open');}
function showToast(msg,bg='#6B3FA0'){const t=document.getElementById('toast');t.textContent=msg;t.style.background=bg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3000);}
loadStudents();
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
  }).catch(function(){});
}
function buildGroupTableHeader(){
  var thead=document.getElementById('groupsTheadRow');
  if(!thead)return;
  var html='<th>#</th>';
  for(var i=0;i<allGroupColumns.length;i++){html+='<th>'+allGroupColumns[i].col_label+'</th>';}
  html+='<th>&#1575;&#1580;&#1585;&#1575;&#1569;&#1575;&#1578;</th>';
  thead.innerHTML=html;
}
function renderGroupTable2(list){
  var body=document.getElementById('groupsBody2');
  var colCount=allGroupColumns.length+2;
  if(!list.length){body.innerHTML='<tr><td colspan="'+colCount+'" class="no-data">&#1604;&#1575; &#1578;&#1608;&#1580;&#1583; &#1576;&#1610;&#1575;&#1606;&#1575;&#1578;&#1548; &#1575;&#1590;&#1601; &#1575;&#1608;&#1604; &#1605;&#1580;&#1605;&#1608;&#1593;&#1577;</td></tr>';return;}
  var html='';
  for(var i=0;i<list.length;i++){
    var g=list[i];
    var row='<tr><td>'+(i+1)+'</td>';
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
}
function filterGroupTable2(){
  var q=document.getElementById('groupSearchInput').value.toLowerCase();
  renderGroupTable2(allGroups2.filter(function(g){return (g.group_name||'').toLowerCase().indexOf(q)>-1||(g.teacher_name||'').toLowerCase().indexOf(q)>-1;}));
}
function clearGroupForm2(){
  var ids=['group_name','teacher_name','level_course','last_reached','study_time','ramadan_time','online_time','group_link','session_duration'];
  for(var x=0;x<ids.length;x++){var el=document.getElementById('gf2_'+ids[x]);if(el)el.value='';}
  document.getElementById('groupEditId2').value='';
}
function openAddGroupModal2(){clearGroupForm2();document.getElementById('groupModalTitle2').textContent='اضافة مجموعة جديدة';document.getElementById('groupModal2').classList.add('open');}
function openGroupEdit2(id){
  var g=null;
  for(var x=0;x<allGroups2.length;x++){if(allGroups2[x].id===id){g=allGroups2[x];break;}}
  if(!g)return;
  document.getElementById('groupEditId2').value=id;
  document.getElementById('groupModalTitle2').textContent='تعديل بيانات المجموعة';
  document.getElementById('gf2_group_name').value=g.group_name||'';
  document.getElementById('gf2_teacher_name').value=g.teacher_name||'';
  document.getElementById('gf2_level_course').value=g.level_course||'';
  document.getElementById('gf2_last_reached').value=g.last_reached||'';
  document.getElementById('gf2_study_time').value=g.study_time||'';
  document.getElementById('gf2_ramadan_time').value=g.ramadan_time||'';
  document.getElementById('gf2_online_time').value=g.online_time||'';
  document.getElementById('gf2_group_link').value=g.group_link||'';
  document.getElementById('gf2_session_duration').value=g.session_duration||'';
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
    session_duration:document.getElementById('gf2_session_duration').value.trim()
  };
  if(!bd.group_name){showToast('اسم المجموعة مطلوب','#e53935');return;}
  var url=editId?'/api/groups/'+editId:'/api/groups';
  var method=editId?'PUT':'POST';
  fetch(url,{method:method,headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(bd)}).then(function(r){return r.json();}).then(function(data){
    if(data.ok){closeGroupModal2();showToast(editId?'تم تعديل المجموعة':'تم اضافة المجموعة','#00BCD4');loadGroups2();}
    else{showToast(data.error||'حدث خطا','#e53935');}
  }).catch(function(){showToast('حدث خطا','#e53935');});
}
function askGroupDelete2(id){groupDeleteTargetId2=id;document.getElementById('groupConfirmModal2').classList.add('open');document.getElementById('groupConfirmDelBtn2').onclick=confirmGroupDelete2;}
function confirmGroupDelete2(){
  if(!groupDeleteTargetId2)return;
  fetch('/api/groups/'+groupDeleteTargetId2,{method:'DELETE',credentials:'include'}).then(function(r){return r.json();}).then(function(data){
    closeGroupConfirm2();
    if(data.ok){showToast('تم حذف المجموعة','#00BCD4');loadGroups2();}
    else{showToast(data.error||'حدث خطا','#e53935');}
    groupDeleteTargetId2=null;
  }).catch(function(){closeGroupConfirm2();});
}
function closeGroupConfirm2(){document.getElementById('groupConfirmModal2').classList.remove('open');}
var studentExcelData=[];function openStudentExcelModal(){studentExcelData=[];document.getElementById("studentExcelFile").value="";document.getElementById("studentExcelFileName").textContent="لم يتم اختيار ملف";document.getElementById("studentExcelPreview").style.display="none";document.getElementById("studentExcelImportBtn").style.display="none";document.getElementById("studentExcelModal").classList.add("open");}function closeStudentExcelModal(){document.getElementById("studentExcelModal").classList.remove("open");}document.addEventListener("DOMContentLoaded",function(){var sf=document.getElementById("studentExcelFile");if(sf){sf.addEventListener("change",function(e){var file=e.target.files[0];if(!file)return;document.getElementById("studentExcelFileName").textContent=file.name;var reader=new FileReader();reader.onload=function(ev){var data=ev.target.result;var rows=data.split(String.fromCharCode(10)).filter(function(r){return r.trim()!="";});if(rows.length<2){showToast("الملف فارغ","#e53935");return;}var sep=rows[0].indexOf(String.fromCharCode(9))>-1?"\t":",",parsed=[];for(var i=1;i<rows.length;i++){var cols=rows[i].split(sep);if(cols.length<2)continue;parsed.push({personal_id:(cols[0]||"").trim(),student_name:(cols[1]||"").trim(),whatsapp:(cols[2]||"").trim(),final_result:(cols[3]||"").trim(),level_reached_2026:(cols[4]||"").trim(),teacher_2026:(cols[5]||"").trim(),mother_phone:(cols[6]||"").trim(),father_phone:(cols[7]||"").trim(),other_phone:(cols[8]||"").trim(),residence:(cols[9]||"").trim(),home_address:(cols[10]||"").trim(),road:(cols[11]||"").trim(),complex_name:(cols[12]||"").trim()});}studentExcelData=parsed;document.getElementById("studentExcelCount").textContent="تم قراءة "+parsed.length+" طالب. اضغط استيراد.";document.getElementById("studentExcelPreview").style.display="block";document.getElementById("studentExcelImportBtn").style.display="inline-block";};reader.readAsText(file,"UTF-8");});}var gf=document.getElementById("groupExcelFile");if(gf){gf.addEventListener("change",function(e){var file=e.target.files[0];if(!file)return;document.getElementById("groupExcelFileName").textContent=file.name;var reader=new FileReader();reader.onload=function(ev){var data=ev.target.result;var rows=data.split(String.fromCharCode(10)).filter(function(r){return r.trim()!="";});if(rows.length<2){showToast("الملف فارغ","#e53935");return;}var sep=rows[0].indexOf(String.fromCharCode(9))>-1?"\t":",",parsed=[];for(var i=1;i<rows.length;i++){var cols=rows[i].split(sep);if(cols.length<2)continue;parsed.push({group_name:(cols[0]||"").trim(),teacher_name:(cols[1]||"").trim(),level_course:(cols[2]||"").trim(),last_reached:(cols[3]||"").trim(),study_time:(cols[4]||"").trim(),ramadan_time:(cols[5]||"").trim(),online_time:(cols[6]||"").trim(),group_link:(cols[7]||"").trim(),session_duration:(cols[8]||"").trim()});}groupExcelData=parsed;document.getElementById("groupExcelCount").textContent="تم قراءة "+parsed.length+" مجموعة. اضغط استيراد.";document.getElementById("groupExcelPreview").style.display="block";document.getElementById("groupExcelImportBtn").style.display="inline-block";};reader.readAsText(file,"UTF-8");});}});function importStudentsFromExcel(){if(!studentExcelData.length){showToast("لا توجد بيانات","#e53935");return;}var btn=document.getElementById("studentExcelImportBtn");btn.disabled=true;btn.textContent="جاري الاستيراد...";fetch("/api/students/bulk",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({rows:studentExcelData})}).then(function(r){return r.text();}).then(function(txt){var data;try{data=JSON.parse(txt);}catch(e){showToast("انتهت الجلسة، سجل الدخول مجددا","#e53935");btn.disabled=false;btn.textContent="استيراد";return;}if(data.ok){closeStudentExcelModal();showToast("تم استيراد "+data.imported+" طالب بنجاح");loadStudents();}else{showToast("حدث خطا","#e53935");}btn.disabled=false;btn.textContent="استيراد";}).catch(function(){showToast("حدث خطا في الاستيراد","#e53935");btn.disabled=false;btn.textContent="استيراد";});}var groupExcelData=[];function openGroupExcelModal(){groupExcelData=[];document.getElementById("groupExcelFile").value="";document.getElementById("groupExcelFileName").textContent="لم يتم اختيار ملف";document.getElementById("groupExcelPreview").style.display="none";document.getElementById("groupExcelImportBtn").style.display="none";document.getElementById("groupExcelModal").classList.add("open");}function closeGroupExcelModal(){document.getElementById("groupExcelModal").classList.remove("open");}function importGroupsFromExcel(){if(!groupExcelData.length){showToast("لا توجد بيانات","#e53935");return;}var btn=document.getElementById("groupExcelImportBtn");btn.disabled=true;btn.textContent="جاري الاستيراد...";fetch("/api/groups/bulk",{method:"POST",headers:{"Content-Type":"application/json"},credentials:"include",body:JSON.stringify({rows:groupExcelData})}).then(function(r){return r.text();}).then(function(txt){var data;try{data=JSON.parse(txt);}catch(e){showToast("انتهت الجلسة، سجل الدخول مجددا","#e53935");btn.disabled=false;btn.textContent="استيراد";return;}if(data.ok){closeGroupExcelModal();showToast("تم استيراد "+data.imported+" مجموعة بنجاح","#00BCD4");loadGroups2();}else{showToast("حدث خطا","#e53935");}btn.disabled=false;btn.textContent="استيراد";}).catch(function(){showToast("حدث خطا في الاستيراد","#e53935");btn.disabled=false;btn.textContent="استيراد";});}
loadGroups2();
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
    delSel.innerHTML='<option value="">— اختر عمود —</option>';
    editSel.innerHTML='<option value="">— اختر عمود —</option>';
    afterSel.innerHTML='<option value="">— اختر العمود —</option>';
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
  if(!label){showToast('ادخل عنوان العمود','#e53935');return;}
  var posVal=document.getElementById('new_col_position').value;
  var afterCol=document.getElementById('new_col_after').value;
  var key='col_'+Date.now();
  var payload={col_key:key,col_label:label,position:posVal};
  if(posVal==='after'&&afterCol){payload.after_col=afterCol;}
  fetch('/api/columns',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(payload)}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('انتهت الجلسة، سجل الدخول مجددا','#e53935');return;}
    if(d.ok){document.getElementById('new_col_label').value='';document.getElementById('new_col_position').value='end';togglePositionCol();closeTableEditModal();showToast('تم إضافة العمود بنجاح');loadStudents();}
    else{showToast(d.error||'حدث خطا','#e53935');}
  });
}
function deleteColumn(){
  var key=document.getElementById('del_col_key').value;
  if(!key){showToast('اختر عمودا','#e53935');return;}
  if(!confirm('هل أنت متأكد من حذف هذا العمود؟ سيتم حذف جميع بياناته.'))return;
  fetch('/api/columns/'+key,{method:'DELETE',credentials:'include'}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('انتهت الجلسة، سجل الدخول مجددا','#e53935');return;}
    if(d.ok){closeTableEditModal();showToast('تم حذف العمود');loadStudents();}
    else{showToast(d.error||'حدث خطا','#e53935');}
  });
}
function updateColumnLabel(){
  var key=document.getElementById('edit_col_key').value;
  var label=document.getElementById('edit_col_label').value.trim();
  if(!key||!label){showToast('اختر عمودا وادخل الاسم','#e53935');return;}
  fetch('/api/columns/'+key,{method:'PUT',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({col_label:label})}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('انتهت الجلسة، سجل الدخول مجددا','#e53935');return;}
    if(d.ok){closeTableEditModal();showToast('تم تعديل العنوان');loadStudents();}
    else{showToast(d.error||'حدث خطا','#e53935');}
  });
}


var allGroupColumns=[];
function openGroupTableEditModal(){
  loadGroupColumnsForEdit();
  document.getElementById('groupTableEditModal').classList.add('open');
  switchGroupTab('add-col');
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
  fetch('/api/group-columns',{credentials:'include'}).then(function(r){return r.json();}).then(function(data){
    var cols=data.columns||[];
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
  if(!label){showToast('&#1575;&#1583;&#1582;&#1604; &#1593;&#1606;&#1608;&#1575;&#1606; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583;','#e53935');return;}
  var posVal=document.getElementById('g_new_col_position').value;
  var afterCol=document.getElementById('g_new_col_after').value;
  var key='gcol_'+Date.now();
  var payload={col_key:key,col_label:label,position:posVal};
  if(posVal==='after'&&afterCol){payload.after_col=afterCol;}
  fetch('/api/group-columns',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(payload)}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('&#1575;&#1606;&#1578;&#1607;&#1578; &#1575;&#1604;&#1580;&#1604;&#1587;&#1577;&#1548; &#1587;&#1580;&#1604; &#1575;&#1604;&#1583;&#1582;&#1608;&#1604; &#1605;&#1580;&#1583;&#1583;&#1575;','#e53935');return;}
    if(d.ok){document.getElementById('g_new_col_label').value='';document.getElementById('g_new_col_position').value='end';toggleGroupPositionCol();closeGroupTableEditModal();showToast('&#1578;&#1605; &#1573;&#1590;&#1575;&#1601;&#1577; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583; &#1576;&#1606;&#1580;&#1575;&#1581;','#00BCD4');loadGroups2();}
    else{showToast(d.error||'&#1581;&#1583;&#1579; &#1582;&#1591;&#1575;','#e53935');}
  });
}
function deleteGroupColumn(){
  var key=document.getElementById('g_del_col_key').value;
  if(!key){showToast('&#1575;&#1582;&#1578;&#1585; &#1593;&#1605;&#1608;&#1583;&#1575;','#e53935');return;}
  if(!confirm('&#1607;&#1604; &#1571;&#1606;&#1578; &#1605;&#1578;&#1571;&#1603;&#1583; &#1605;&#1606; &#1581;&#1584;&#1601; &#1607;&#1584;&#1575; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583;&#1567;'))return;
  fetch('/api/group-columns/'+key,{method:'DELETE',credentials:'include'}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('&#1575;&#1606;&#1578;&#1607;&#1578; &#1575;&#1604;&#1580;&#1604;&#1587;&#1577;&#1548; &#1587;&#1580;&#1604; &#1575;&#1604;&#1583;&#1582;&#1608;&#1604; &#1605;&#1580;&#1583;&#1583;&#1575;','#e53935');return;}
    if(d.ok){closeGroupTableEditModal();showToast('&#1578;&#1605; &#1581;&#1584;&#1601; &#1575;&#1604;&#1593;&#1605;&#1608;&#1583;','#00BCD4');loadGroups2();}
    else{showToast(d.error||'&#1581;&#1583;&#1579; &#1582;&#1591;&#1575;','#e53935');}
  });
}
function updateGroupColumnLabel(){
  var key=document.getElementById('g_edit_col_key').value;
  var label=document.getElementById('g_edit_col_label').value.trim();
  if(!key||!label){showToast('&#1575;&#1582;&#1578;&#1585; &#1593;&#1605;&#1608;&#1583;&#1575; &#1608;&#1575;&#1583;&#1582;&#1604; &#1575;&#1604;&#1575;&#1587;&#1605;','#e53935');return;}
  fetch('/api/group-columns/'+key,{method:'PUT',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({col_label:label})}).then(function(r){return r.text();}).then(function(txt){
    var d;try{d=JSON.parse(txt);}catch(e){showToast('&#1575;&#1606;&#1578;&#1607;&#1578; &#1575;&#1604;&#1580;&#1604;&#1587;&#1577;&#1548; &#1587;&#1580;&#1604; &#1575;&#1604;&#1583;&#1582;&#1608;&#1604; &#1605;&#1580;&#1583;&#1583;&#1575;','#e53935');return;}
    if(d.ok){closeGroupTableEditModal();showToast('&#1578;&#1605; &#1578;&#1593;&#1583;&#1610;&#1604; &#1575;&#1604;&#1593;&#1606;&#1608;&#1575;&#1606;','#00BCD4');loadGroups2();}
    else{showToast(d.error||'&#1581;&#1583;&#1579; &#1582;&#1591;&#1575;','#e53935');}
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
    tbody.innerHTML = '<tr><td colspan="11" class="no-data">لا توجد سجلات، اضف أول سجل</td></tr>';
    return;
  }
  var html = '';
  for(var i=0; i<data.length; i++) {
    var r = data[i];
    html += '<tr>';
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
  document.getElementById('attendanceModalTitle').textContent = 'إضافة سجل غياب';
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
      if(d.ok){ closeAttendanceModal(); showToast('تم الحفظ','#4CAF50'); loadAttendance(); }
      else { showToast(d.error||'حدث خطأ','#e53935'); }
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
    'status': ['','حاضر','غائب','متأخر','معتذر'],
    'message_status': ['','تم الإرسال','لم يُرسل','فشل الإرسال'],
    'study_status': ['','مستمر','منقطع','موقوف']
  };
  if(selectOptions[field]) {
    input = document.createElement('select');
    input.style.cssText = 'width:100%;padding:4px;border:1px solid #aaa;border-radius:4px;';
    selectOptions[field].forEach(function(v){
      var o = document.createElement('option');
      o.value = v; o.textContent = v||'-- اختر --';
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
        if(d.ok){ showToast('تم التحديث','#4CAF50'); loadAttendance(); }
        else { showToast(d.error||'حدث خطأ','#e53935'); loadAttendance(); }
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
      if(d.ok){ showToast('تم الحذف','#e53935'); loadAttendance(); }
      else { showToast(d.error||'حدث خطأ','#e53935'); }
    });
}

loadAttendance();

// ─── Custom Tables JS ────────────────────────────────────────────────────────
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
}

function buildCustomTableHTML(t) {
  var cols = t.cols || [];
  var rows = t.rows || [];
  var headerCells = '<th>#</th>';
  for(var i=0; i<cols.length; i++) {
    headerCells += '<th>' + (cols[i].col_label||'') + '</th>';
  }
  headerCells += '<th>&#128465;</th>';

  var bodyRows = '';
  if(rows.length === 0) {
    bodyRows = '<tr><td colspan="' + (cols.length+2) + '" class="no-data">لا توجد بيانات، أضف أول صف</td></tr>';
  } else {
    for(var j=0; j<rows.length; j++) {
      var r = rows[j];
      var rd = r.row_data || {};
      bodyRows += '<tr>';
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

  return '<div class="custom-table-section" id="ctsec_' + t.id + '">' +
    '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:10px;">' +
    '<span class="custom-table-title">&#128203; ' + t.tbl_name + '</span>' +
    '<div style="display:flex;gap:8px;flex-wrap:wrap;">' +
    '<button class="btn-add" onclick="openCustomRowModal(' + t.id + ')">+ إضافة صف</button>' +
    '<button class="btn-add" style="background:linear-gradient(135deg,#E65100,#FFA726);" onclick="openCustomTableEditModal(' + t.id + ')">&#9881; تعديل الجدول</button>' +
    '<button class="btn-del-row" style="font-size:13px;padding:6px 12px;border-radius:8px;" data-tid="' + t.id + '" onclick="openCustomTableDeleteConfirmById(this)">&#128465; حذف الجدول</button>' +
    '</div></div>' +
    '<div class="table-wrap"><table>' +
    '<thead><tr id="cthead_' + t.id + '">' + headerCells + '</tr></thead>' +
    '<tbody id="ctbody_' + t.id + '">' + bodyRows + '</tbody>' +
    '</table></div></div>';
}
// ── Wizard ────────────────────────────────────────────────────────────────────
function openNewTableWizard() {
  document.getElementById('wiz_tbl_name').value = '';
  document.getElementById('wiz_col_count').value = '3';
  document.getElementById('wiz_row_count').value = '0';
  document.getElementById('wizStep1').classList.add('active');
  document.getElementById('wizStep2').classList.remove('active');
  document.getElementById('wizDot1').classList.add('active');
  document.getElementById('wizDot2').classList.remove('active');
  document.getElementById('newTableWizardModal').style.display = 'flex';
}

function closeNewTableWizard() {
  document.getElementById('newTableWizardModal').style.display = 'none';
}

function wizardStep1Next() {
  var name = document.getElementById('wiz_tbl_name').value.trim();
  var cols = parseInt(document.getElementById('wiz_col_count').value) || 1;
  if(!name) { showToast('أدخل اسم الجدول','#e53935'); return; }
  if(cols < 1 || cols > 20) { showToast('عدد الأعمدة يجب أن يكون 1-20','#e53935'); return; }
  var container = document.getElementById('wizColNamesContainer');
  container.innerHTML = '';
  for(var i=0; i<cols; i++) {
    var inp = document.createElement('input');
    inp.type = 'text';
    inp.className = 'col-name-input';
    inp.placeholder = 'اسم العمود ' + (i+1);
    inp.id = 'wizCol_' + i;
    container.appendChild(inp);
  }
  document.getElementById('wizStep1').classList.remove('active');
  document.getElementById('wizStep2').classList.add('active');
  document.getElementById('wizDot1').classList.remove('active');
  document.getElementById('wizDot2').classList.add('active');
}

function wizardGoBack() {
  document.getElementById('wizStep2').classList.remove('active');
  document.getElementById('wizStep1').classList.add('active');
  document.getElementById('wizDot2').classList.remove('active');
  document.getElementById('wizDot1').classList.add('active');
}

function wizardCreateTable() {
  var name = document.getElementById('wiz_tbl_name').value.trim();
  var rowCount = parseInt(document.getElementById('wiz_row_count').value) || 0;
  var colInputs = document.querySelectorAll('[id^="wizCol_"]');
  var cols = [];
  for(var i=0; i<colInputs.length; i++) {
    var v = colInputs[i].value.trim();
    cols.push(v || ('عمود ' + (i+1)));
  }
  var payload = { tbl_name: name, cols: cols, row_count: rowCount };
  fetch('/api/custom-tables', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok) {
        closeNewTableWizard();
        showToast('تم إنشاء الجدول','#4CAF50');
        loadCustomTables();
      } else {
        showToast(d.error||'حدث خطأ','#e53935');
      }
    });
}

// ── Row add/edit ───────────────────────────────────────────────────────────────
function openCustomRowModal(tid) {
  currentCustomTableId = tid;
  editingCustomRowId = null;
  var t = null;
  for(var i=0; i<allCustomTables.length; i++) { if(allCustomTables[i].id===tid) { t=allCustomTables[i]; break; } }
  if(!t) return;
  document.getElementById('customRowModalTitle').textContent = 'إضافة صف - ' + t.tbl_name;
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
      if(d.ok) { closeCustomRowModal(); showToast('تم الحفظ','#4CAF50'); loadCustomTables(); }
      else { showToast(d.error||'حدث خطأ','#e53935'); }
    });
}

function deleteCustomRow(tid, rid) {
  fetch('/api/custom-tables/' + tid + '/rows/' + rid, {method:'DELETE'})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok) { showToast('تم الحذف','#e53935'); loadCustomTables(); }
      else { showToast(d.error||'حدث خطأ','#e53935'); }
    });
}

// ── Inline cell edit ──────────────────────────────────────────────────────────
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
        if(d.ok){ showToast('تم التحديث','#4CAF50'); loadCustomTables(); }
        else{ showToast(d.error||'حدث خطأ','#e53935'); loadCustomTables(); }
      });
  }
  input.addEventListener('blur', saveCell);
  input.addEventListener('keydown', function(e){ if(e.key==='Enter') input.blur(); });
}

// ── Table edit modal (add/delete/rename cols) ─────────────────────────────────
function openCustomTableEditModal(tid) {
  currentCustomTableId = tid;
  var t = null;
  for(var i=0; i<allCustomTables.length; i++) { if(allCustomTables[i].id===tid) { t=allCustomTables[i]; break; } }
  if(!t) return;
  document.getElementById('customTableEditTitle').textContent = 'تعديل جدول: ' + t.tbl_name;
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
  if(!col_label) { showToast('أدخل اسم العمود','#e53935'); return; }
  var position = document.getElementById('ctbl_position').value;
  var after_key = document.getElementById('ctbl_after_col').value;
  var payload = { col_label: col_label, position: position, after_key: after_key };
  fetch('/api/custom-tables/' + tid + '/cols', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('تم إضافة العمود','#00BCD4'); loadCustomTables(); closeCustomTableEditModal(); }
      else{ showToast(d.error||'حدث خطأ','#e53935'); }
    });
}

function deleteCustomColumn() {
  var tid = currentCustomTableId;
  var col_key = document.getElementById('ctbl_del_col').value;
  if(!col_key) return;
  fetch('/api/custom-tables/' + tid + '/cols/' + col_key, {method:'DELETE'})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('تم الحذف','#e53935'); loadCustomTables(); closeCustomTableEditModal(); }
      else{ showToast(d.error||'حدث خطأ','#e53935'); }
    });
}

function updateCustomColumnLabel() {
  var tid = currentCustomTableId;
  var col_key = document.getElementById('ctbl_rename_col').value;
  var new_label = document.getElementById('ctbl_rename_label').value.trim();
  if(!new_label || !col_key) { showToast('أدخل الاسم الجديد','#e53935'); return; }
  fetch('/api/custom-tables/' + tid + '/cols/' + col_key, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({col_label: new_label})})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('تم تعديل العنوان','#00BCD4'); loadCustomTables(); closeCustomTableEditModal(); }
      else{ showToast(d.error||'حدث خطأ','#e53935'); }
    });
}

// ── Delete table ──────────────────────────────────────────────────────────────
function openCustomTableDeleteConfirmById(btn) {
  var tid = parseInt(btn.getAttribute('data-tid'));
  var t = null;
  for(var i=0; i<allCustomTables.length; i++) { if(allCustomTables[i].id===tid){ t=allCustomTables[i]; break; } }
  var name = t ? t.tbl_name : '';
  openCustomTableDeleteConfirm(tid, name);
}

function openCustomTableDeleteConfirm(tid, name) {
  deletingCustomTableId = tid;
  document.getElementById('customTableDeleteMsg').textContent = 'هل تريد حذف جدول "' + name + '"؟ سيتم حذف جميع البيانات.';
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
      if(d.ok){ showToast('تم حذف الجدول','#e53935'); loadCustomTables(); }
      else{ showToast(d.error||'حدث خطأ','#e53935'); }
    });
}

// ── Import stub (placeholder) ─────────────────────────────────────────────────
function openCustomImportModal(tid) {
  showToast('ميزة الاستيراد قريباً','#FF9800');
}

// Load custom tables on page load
loadCustomTables();

// ─── Attendance Excel Import ──────────────────────────────────────────────────
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
      document.getElementById('attendanceExcelStatus').textContent = 'تم قراءة ' + dataRows.length + ' صف. اضغط استيراد.';
      document.getElementById('attendanceExcelImportBtn').style.display = dataRows.length > 0 ? 'inline-flex' : 'none';
    } catch(err) {
      document.getElementById('attendanceExcelStatus').textContent = 'خطأ في قراءة الملف: ' + err.message;
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
      statusEl.textContent = 'تم استيراد ' + done + ' سجل بنجاح!';
      loadAttendance();
      setTimeout(closeAttendanceExcelModal, 1500);
      return;
    }
    fetch('/api/attendance', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(batch[idx])})
      .then(function(r){ return r.json(); }).then(function(d){
        if(d.ok) done++;
        statusEl.textContent = 'جاري الاستيراد... ' + (idx+1) + ' / ' + total;
        sendNext(idx+1);
      }).catch(function(){ sendNext(idx+1); });
  }
  sendNext(0);
}

// ─── Attendance Column Management ────────────────────────────────────────────
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
      var o1 = document.createElement('option'); o1.value = c.col_key; o1.textContent = c.col_label; delSel.appendChild(o1);
      var o2 = document.createElement('option'); o2.value = c.col_key; o2.textContent = c.col_label; renameSel.appendChild(o2);
      var o3 = document.createElement('option'); o3.value = c.col_key; o3.textContent = c.col_label; afterSel.appendChild(o3);
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
  if(!col_label){ showToast('أدخل اسم العمود','#e53935'); return; }
  var position = document.getElementById('att_col_position').value;
  var after_key = document.getElementById('att_after_col').value;
  fetch('/api/att-columns', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({col_label:col_label, position:position, after_key:after_key})})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('تم إضافة العمود','#00BCD4'); closeAttendanceTableEditModal(); loadAttendance(); }
      else { showToast(d.error||'حدث خطأ','#e53935'); }
    });
}

function deleteAttendanceColumn() {
  var col_key = document.getElementById('att_del_col').value;
  if(!col_key) return;
  fetch('/api/att-columns/' + col_key, {method:'DELETE'})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('تم الحذف','#e53935'); closeAttendanceTableEditModal(); loadAttendance(); }
      else { showToast(d.error||'حدث خطأ','#e53935'); }
    });
}

function updateAttendanceColumnLabel() {
  var col_key = document.getElementById('att_rename_col').value;
  var new_label = document.getElementById('att_rename_label').value.trim();
  if(!new_label||!col_key){ showToast('أدخل الاسم الجديد','#e53935'); return; }
  fetch('/api/att-columns/' + col_key, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({col_label:new_label})})
    .then(function(r){ return r.json(); }).then(function(d){
      if(d.ok){ showToast('تم تعديل العنوان','#00BCD4'); closeAttendanceTableEditModal(); loadAttendance(); }
      else { showToast(d.error||'حدث خطأ','#e53935'); }
    });
}
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
        return render_login("اسم المستخدم او كلمة المرور غلط"), 401
    session["user"] = dict(user)
    return redirect("/dashboard")

@app.route("/dashboard")
@login_required
def dashboard():
    return HOME_HTML

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
             installment5,mother_phone,father_phone,other_phone,residence,home_address,road,complex_name)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d.get("personal_id"), d.get("student_name"), d.get("whatsapp"),
             d.get("class_name"), d.get("old_new_2026"), d.get("registration_term2_2026"),
             d.get("group_name_student"), d.get("group_online"),
             d.get("final_result"), d.get("level_reached_2026"), d.get("suitable_level_2026"),
             d.get("books_received"), d.get("teacher_2026"),
             d.get("installment1"), d.get("installment2"), d.get("installment3"),
             d.get("installment4"), d.get("installment5"),
             d.get("mother_phone"), d.get("father_phone"), d.get("other_phone"),
             d.get("residence"), d.get("home_address"), d.get("road"), d.get("complex_name")))
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
            home_address=?,road=?,complex_name=?
            WHERE id=?""",
            (d.get("personal_id"), d.get("student_name"), d.get("whatsapp"),
             d.get("class_name"), d.get("old_new_2026"), d.get("registration_term2_2026"),
             d.get("group_name_student"), d.get("group_online"),
             d.get("final_result"), d.get("level_reached_2026"), d.get("suitable_level_2026"),
             d.get("books_received"), d.get("teacher_2026"),
             d.get("installment1"), d.get("installment2"), d.get("installment3"),
             d.get("installment4"), d.get("installment5"),
             d.get("mother_phone"), d.get("father_phone"), d.get("other_phone"),
             d.get("residence"), d.get("home_address"), d.get("road"), d.get("complex_name"), sid))
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
            ("personal_id","الرقم الشخصي",1),("student_name","اسم الطالب",2),("whatsapp","هاتف الواتساب المعتمد",3),
            ("class_name","الصف",4),("old_new_2026","قديم جديد 2026",5),("registration_term2_2026","تسجيل الفصل الثاني 2026",6),
            ("group_name_student","المجموعة",7),("group_online","المجموعة (الاونلاين)",8),
            ("final_result","النتيجة النهائية (تحديد المستوى 2026)",9),
            ("level_reached_2026","الى اين وصل الطالب 2026",10),("suitable_level_2026","هل الطالب مناسب لهذا المستوى 2026؟",11),
            ("books_received","استلام الكتب",12),("teacher_2026","المدرس 2026",13),
            ("installment1","القسط الاول 2026",14),("installment2","القسط الثاني",15),("installment3","القسط الثالث",16),
            ("installment4","القسط الرابع",17),("installment5","القسط الخامس",18),
            ("mother_phone","هاتف الام",19),("father_phone","هاتف الاب",20),("other_phone","هاتف اخر",21),
            ("residence","مكان السكن",22),("home_address","عنوان المنزل",23),("road","الطريق",24),("complex_name","المجمع",25),
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
        # SQLite doesn't support DROP COLUMN directly (before 3.35), rebuild table
        rows = db.execute("SELECT col_key FROM column_labels ORDER BY col_order").fetchall()
        remaining = [r[0] for r in rows if r[0] != col_key]
        # Get all columns in students table
        pragma = db.execute("PRAGMA table_info(students)").fetchall()
        all_cols = [r[1] for r in pragma]
        keep_cols = [c2 for c2 in all_cols if c2 != col_key]
        cols_str = ",".join(keep_cols)
        db.execute("CREATE TABLE students_backup AS SELECT "+cols_str+" FROM students")
        db.execute("DROP TABLE students")
        db.execute("ALTER TABLE students_backup RENAME TO students")
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
    db.execute("""CREATE TABLE IF NOT EXISTS group_col_labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        col_key TEXT UNIQUE,
        col_label TEXT,
        col_order INTEGER DEFAULT 0,
        is_visible INTEGER DEFAULT 1)""")
    if db.execute("SELECT COUNT(*) FROM group_col_labels").fetchone()[0] == 0:
        default_cols = [
            ("group_name","اسم المجموعة",1),("teacher_name","اسم المدرس",2),
            ("level_course","المستوى / المقرر",3),("last_reached","المقرر الذي تم الوصول اليه الفصل الفائت",4),
            ("study_time","وقت الدراسة",5),("ramadan_time","توقيت شهر رمضان",6),
            ("online_time","توقيت الاونلاين (العادي)",7),("group_link","رابط المجموعة",8),
            ("session_duration","الحصة بالدقيقة (يدوي)",9),
        ]
        for key,label,order in default_cols:
            try:
                db.execute("INSERT INTO group_col_labels(col_key,col_label,col_order) VALUES(?,?,?)",(key,label,order))
            except:
                pass
        db.commit()
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
    db = get_db()
    try:
        pragma = db.execute("PRAGMA table_info(student_groups)").fetchall()
        all_cols = [r[1] for r in pragma]
        keep_cols = [c for c in all_cols if c != col_key]
        cols_str = ",".join(keep_cols)
        db.execute("CREATE TABLE student_groups_backup AS SELECT "+cols_str+" FROM student_groups")
        db.execute("DROP TABLE student_groups")
        db.execute("ALTER TABLE student_groups_backup RENAME TO student_groups")
        db.execute("DELETE FROM group_col_labels WHERE col_key=?",(col_key,))
        db.commit()
        return jsonify({"ok":True})
    except Exception as ex:
        return jsonify({"ok":False,"error":str(ex)}),400

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
        db.execute("""INSERT INTO attendance(attendance_date,day_name,group_name,student_name,contact_number,status,message,message_status,study_status)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (d.get('attendance_date',''), d.get('day_name',''), d.get('group_name',''),
             d.get('student_name',''), d.get('contact_number',''), d.get('status',''),
             d.get('message',''), d.get('message_status',''), d.get('study_status','')))
        db.commit()
        rid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        return jsonify({"ok": True, "id": rid})
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



# ─── Attendance Column Labels API ──────────────────────────────────────────────

ATT_DEFAULT_COLS = [
    ("attendance_date","تاريخ أخذ الحضور",1),
    ("day_name","اليوم",2),
    ("group_name","المجموعة",3),
    ("student_name","اسم الطالب",4),
    ("contact_number","رقم التواصل",5),
    ("status","الحالة",6),
    ("message","الرسالة",7),
    ("message_status","حالة إرسال الرسالة",8),
    ("study_status","حالة الدراسة",9),
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
        return jsonify({'ok':False,'error':'لا يمكن حذف الأعمدة الأساسية'}),400
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


# ─── Custom Tables API ────────────────────────────────────────────────────────

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
<title>معلومات المجموعات - Mindex</title>
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
  <h1>&#128101; معلومات المجموعات</h1>
  <a href="/database" class="btn-back">&larr; قاعدة البيانات</a>
</div>
<div class="main">
  <div class="page-title">جدول المجموعات</div>
  <div class="stats">
    <div class="stat-card">
      <span class="stat-num" id="totalCount">0</span>
      <span class="stat-label">إجمالي المجموعات</span>
    </div>
  </div>
  <button class="btn-add" onclick="openAddModal()">+ إضافة مجموعة</button>
  <div class="search-bar">
    <input type="text" id="searchInput" placeholder="ابحث باسم المجموعة أو المدرس..." oninput="filterTable()">
    <button class="btn-search" onclick="filterTable()">بحث</button>
  </div>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>#</th>
          <th>اسم المجموعة</th>
          <th>اسم المدرس</th>
          <th>المستوى / المقرر</th>
          <th>المقرر الذي تم الوصول اليه الفصل الفائت</th>
          <th>وقت الدراسة</th>
          <th>توقيت شهر رمضان</th>
          <th>توقيت الاونلاين (العادي)</th>
          <th>رابط المجموعة</th>
          <th>الحصة بالدقيقة (يدوي)</th>
          <th>اجراءات</th>
        </tr>
      </thead>
      <tbody id="groupsBody">
        <tr><td colspan="11" class="no-data">لا توجد بيانات، اضف اول مجموعة</td></tr>
      </tbody>
    </table>
  </div>
</div>
<div class="modal-bg" id="modal">
  <div class="modal">
    <h2 id="modalTitle">اضافة مجموعة جديدة</h2>
    <input type="hidden" id="editId">
    <div class="form-grid">
      <div class="field"><label>اسم المجموعة *</label><input id="f_group_name" placeholder="اسم المجموعة"></div>
      <div class="field"><label>اسم المدرس *</label><input id="f_teacher_name" placeholder="اسم المدرس"></div>
      <div class="field"><label>المستوى / المقرر</label><input id="f_level_course" placeholder="مثال: المستوى 3 - كتاب A"></div>
      <div class="field"><label>المقرر الذي تم الوصول اليه الفصل الفائت</label><input id="f_last_reached" placeholder="مثال: الوحدة 5 - الدرس 3"></div>
      <div class="field"><label>وقت الدراسة</label><input id="f_study_time" placeholder="مثال: السبت والاثنين 4-5 مساءً"></div>
      <div class="field"><label>توقيت شهر رمضان</label><input id="f_ramadan_time" placeholder="مثال: 8-9 مساءً"></div>
      <div class="field"><label>توقيت الاونلاين (العادي)</label><input id="f_online_time" placeholder="مثال: 5-6 مساءً"></div>
      <div class="field"><label>رابط المجموعة</label><input id="f_group_link" placeholder="https://..." class="ltr"></div>
      <div class="field full"><label>الحصة بالدقيقة (يدوي)</label><input id="f_session_duration" placeholder="مثال: 60 دقيقة"></div>
    </div>
    <div class="modal-actions">
      <button class="btn-save" onclick="saveGroup()">حفظ</button>
      <button class="btn-cancel" onclick="closeModal()">الغاء</button>
    </div>
  </div>
</div>
<div class="confirm-bg" id="confirmModal">
  <div class="confirm-box">
    <h3>تاكيد الحذف</h3>
    <p>هل انت متاكد انك تريد حذف هذه المجموعة؟</p>
    <div class="confirm-actions">
      <button class="btn-confirm-del" id="confirmDelBtn">حذف</button>
      <button class="btn-confirm-cancel" onclick="closeConfirm()">الغاء</button>
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
  if(!list.length){body.innerHTML='<tr><td colspan="11" class="no-data">لا توجد بيانات، اضف اول مجموعة</td></tr>';return;}
  body.innerHTML=list.map((g,i)=>{
    const link=g.group_link?'<a href="'+g.group_link+'" target="_blank">فتح الرابط</a>':'-';
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
function openAddModal(){clearForm();document.getElementById('modalTitle').textContent='اضافة مجموعة جديدة';document.getElementById('modal').classList.add('open');}
function openEdit(id){
  const g=allGroups.find(x=>x.id===id);if(!g)return;
  document.getElementById('editId').value=id;
  document.getElementById('modalTitle').textContent='تعديل بيانات المجموعة';
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
  if(!body.group_name){showToast('اسم المجموعة مطلوب','#e53935');return;}
  const url=editId?'/api/groups/'+editId:'/api/groups';
  const method=editId?'PUT':'POST';
  const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(body)});
  const data=await res.json();
  if(data.ok){closeModal();showToast(editId?'تم تعديل المجموعة بنجاح':'تم اضافة المجموعة بنجاح');loadGroups();}
  else{showToast(data.error||'حدث خطا','#e53935');}
}
function askDelete(id){deleteTargetId=id;document.getElementById('confirmModal').classList.add('open');document.getElementById('confirmDelBtn').onclick=confirmDelete;}
async function confirmDelete(){
  if(!deleteTargetId)return;
  const res=await fetch('/api/groups/'+deleteTargetId,{method:'DELETE',credentials:'include'});
  const data=await res.json();
  closeConfirm();
  if(data.ok){showToast('تم حذف المجموعة بنجاح');loadGroups();}
  else{showToast(data.error||'حدث خطا','#e53935');}
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
    rows = db.execute("SELECT * FROM student_groups ORDER BY id DESC").fetchall()
    return jsonify({"groups": [dict(r) for r in rows]})

@app.route("/api/groups", methods=["POST"])
@login_required
def api_groups_add():
    d = request.get_json()
    try:
        db = get_db()
        db.execute("""INSERT INTO student_groups
            (group_name,teacher_name,level_course,last_reached,study_time,
             ramadan_time,online_time,group_link,session_duration)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (d.get("group_name"), d.get("teacher_name"), d.get("level_course"),
             d.get("last_reached"), d.get("study_time"), d.get("ramadan_time"),
             d.get("online_time"), d.get("group_link"), d.get("session_duration")))
        db.commit()
        return jsonify({"ok": True})
    except Exception as ex:
        return jsonify({"ok": False, "error": str(ex)}), 400

@app.route("/api/groups/<int:gid>", methods=["PUT"])
@login_required
def api_groups_update(gid):
    d = request.get_json()
    try:
        db = get_db()
        db.execute("""UPDATE student_groups SET
            group_name=?,teacher_name=?,level_course=?,last_reached=?,study_time=?,
            ramadan_time=?,online_time=?,group_link=?,session_duration=?
            WHERE id=?""",
            (d.get("group_name"), d.get("teacher_name"), d.get("level_course"),
             d.get("last_reached"), d.get("study_time"), d.get("ramadan_time"),
             d.get("online_time"), d.get("group_link"), d.get("session_duration"), gid))
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

@app.route("/api/logout", methods=["POST", "GET"])
def api_logout():
    session.clear()
    return redirect("/")

# v2
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
