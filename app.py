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
        final_result TEXT,
        level_reached_2026 TEXT,
        teacher_2026 TEXT,
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
        final_result TEXT,
        level_reached_2026 TEXT,
        teacher_2026 TEXT,
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
table{width:100%;border-collapse:collapse;min-width:1400px;}
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
  <button class="btn-add" onclick="openAddModal()">+ إضافة طالب</button>
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
          <th>النتيجة النهائية (تحديد المستوى 2026)</th>
          <th>الى اين وصل الطالب 2026</th>
          <th>المدرس 2026</th>
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
        <tr><td colspan="15" class="no-data">لا توجد بيانات، اضف اول طالب</td></tr>
      </tbody>
    </table>
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
      <div class="field"><label>النتيجة النهائية (تحديد المستوى 2026)</label>
        <select id="f_final_result">
          <option value="">-- اختر --</option>
          <option>ناجح</option>
          <option>راسب</option>
          <option>قيد التقييم</option>
          <option>غائب</option>
        </select>
      </div>
      <div class="field"><label>الى اين وصل الطالب 2026</label><input id="f_level_reached" placeholder="مثال: الوحدة 5 / المستوى 3"></div>
      <div class="field"><label>المدرس 2026</label><input id="f_teacher" placeholder="اسم المدرس"></div>
      <div class="field"><label>هاتف الام</label><input id="f_mother_phone" placeholder="+973 XXXX XXXX" class="ltr"></div>
      <div class="field"><label>هاتف الاب</label><input id="f_father_phone" placeholder="+973 XXXX XXXX" class="ltr"></div>
      <div class="field"><label>هاتف اخر</label><input id="f_other_phone" placeholder="+973 XXXX XXXX" class="ltr"></div>
      <div class="field"><label>مكان السكن</label><input id="f_residence" placeholder="المنطقة / المدينة"></div>
      <div class="field full"><label>عنوان المنزل</label><input id="f_home_address" placeholder="عنوان المنزل التفصيلي"></div>
      <div class="field"><label>الطريق</label><input id="f_road" placeholder="رقم الطريق او اسمه"></div>
      <div class="field"><label>المجمع</label><input id="f_complex" placeholder="اسم المجمع"></div>
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
<div class="toast" id="toast"></div>
<!-- ========== GROUPS TABLE SECTION ========== -->
<div style="margin-top:40px;">
  <div class="page-title" style="color:#0097A7;font-size:20px;font-weight:800;margin-bottom:16px;">&#128101; معلومات المجموعات (يدوي)</div>
  <div class="stats" id="groupsStats">
    <div class="stat-card">
      <span class="stat-num" id="groupsTotalCount">0</span>
      <span class="stat-label">إجمالي المجموعات</span>
    </div>
  </div>
  <button class="btn-add" style="background:linear-gradient(135deg,#00BCD4,#0097A7);" onclick="openAddGroupModal()">+ إضافة مجموعة</button>
  <div class="search-bar">
    <input type="text" id="groupSearchInput" placeholder="ابحث باسم المجموعة أو المدرس..." oninput="filterGroupTable()">
    <button class="btn-search" style="background:#0097A7;" onclick="filterGroupTable()">بحث</button>
  </div>
  <div class="table-wrap" style="border-radius:14px;overflow-x:auto;">
    <table style="min-width:1300px;">
      <thead>
        <tr style="background:linear-gradient(135deg,#00BCD4,#0097A7);">
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

<!-- Groups Add/Edit Modal -->
<div class="modal-bg" id="groupModal">
  <div class="modal" style="border-top:4px solid #00BCD4;">
    <h2 id="groupModalTitle" style="color:#0097A7;">اضافة مجموعة جديدة</h2>
    <input type="hidden" id="groupEditId">
    <div class="form-grid">
      <div class="field"><label style="color:#0097A7;">اسم المجموعة *</label><input id="gf_group_name" placeholder="اسم المجموعة" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">اسم المدرس *</label><input id="gf_teacher_name" placeholder="اسم المدرس" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">المستوى / المقرر</label><input id="gf_level_course" placeholder="مثال: المستوى 3 - كتاب A" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">المقرر الذي تم الوصول اليه الفصل الفائت</label><input id="gf_last_reached" placeholder="مثال: الوحدة 5 - الدرس 3" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">وقت الدراسة</label><input id="gf_study_time" placeholder="مثال: السبت والاثنين 4-5 مساء" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">توقيت شهر رمضان</label><input id="gf_ramadan_time" placeholder="مثال: 8-9 مساء" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">توقيت الاونلاين (العادي)</label><input id="gf_online_time" placeholder="مثال: 5-6 مساء" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field"><label style="color:#0097A7;">رابط المجموعة</label><input id="gf_group_link" placeholder="https://..." class="ltr" style="border-color:#b2ebf2;background:#f0fdff;"></div>
      <div class="field full"><label style="color:#0097A7;">الحصة بالدقيقة (يدوي)</label><input id="gf_session_duration" placeholder="مثال: 60 دقيقة" style="border-color:#b2ebf2;background:#f0fdff;"></div>
    </div>
    <div class="modal-actions">
      <button class="btn-save" style="background:linear-gradient(135deg,#00BCD4,#0097A7);" onclick="saveGroup()">حفظ</button>
      <button class="btn-cancel" style="background:#e0f7fa;color:#0097A7;" onclick="closeGroupModal()">الغاء</button>
    </div>
  </div>
</div>

<!-- Groups Confirm Delete Modal -->
<div class="confirm-bg" id="groupConfirmModal">
  <div class="confirm-box">
    <h3>تاكيد الحذف</h3>
    <p>هل انت متاكد انك تريد حذف هذه المجموعة؟ لا يمكن التراجع عن هذا الاجراء.</p>
    <div class="confirm-actions">
      <button class="btn-confirm-del" id="groupConfirmDelBtn">حذف</button>
      <button class="btn-confirm-cancel" onclick="closeGroupConfirm()">الغاء</button>
    </div>
  </div>
</div>
<script>
let allStudents=[];
let deleteTargetId=null;
async function loadStudents(){
  const res=await fetch('/api/students');
  const data=await res.json();
  allStudents=data.students||[];
  renderTable(allStudents);
  document.getElementById('totalCount').textContent=allStudents.length;
}
function renderTable(list){
  const body=document.getElementById('studentsBody');
  if(!list.length){body.innerHTML='<tr><td colspan="15" class="no-data">لا توجد بيانات، اضف اول طالب</td></tr>';return;}
  body.innerHTML=list.map((s,i)=>{
    const badge=s.final_result=='ناجح'?'badge-pass':s.final_result=='راسب'?'badge-fail':'badge-pend';
    const res=s.final_result?'<span class="badge '+badge+'">'+s.final_result+'</span>':'-';
    return '<tr><td>'+(i+1)+'</td><td><b>'+(s.personal_id||'-')+'</b></td><td class="name-cell">'+(s.student_name||'-')+'</td><td dir="ltr">'+(s.whatsapp||'-')+'</td><td>'+res+'</td><td>'+(s.level_reached_2026||'-')+'</td><td>'+(s.teacher_2026||'-')+'</td><td dir="ltr">'+(s.mother_phone||'-')+'</td><td dir="ltr">'+(s.father_phone||'-')+'</td><td dir="ltr">'+(s.other_phone||'-')+'</td><td>'+(s.residence||'-')+'</td><td>'+(s.home_address||'-')+'</td><td>'+(s.road||'-')+'</td><td>'+(s.complex_name||'-')+'</td><td><button class="action-btn btn-edit" onclick="openEdit('+s.id+')">&#9998;</button><button class="action-btn btn-del" onclick="askDelete('+s.id+')">&#128465;</button></td></tr>';
  }).join('');
}
function filterTable(){
  const q=document.getElementById('searchInput').value.toLowerCase();
  renderTable(allStudents.filter(s=>(s.student_name||'').toLowerCase().includes(q)||(s.personal_id||'').toLowerCase().includes(q)));
}
function clearForm(){
  ['personal_id','student_name','whatsapp','final_result','level_reached','teacher','mother_phone','father_phone','other_phone','residence','home_address','road','complex'].forEach(k=>{const el=document.getElementById('f_'+k);if(el)el.value='';});
  document.getElementById('editId').value='';
}
function openAddModal(){clearForm();document.getElementById('modalTitle').textContent='اضافة طالب جديد';document.getElementById('modal').classList.add('open');}
function openEdit(id){
  const s=allStudents.find(x=>x.id===id);if(!s)return;
  document.getElementById('editId').value=id;
  document.getElementById('modalTitle').textContent='تعديل بيانات الطالب';
  document.getElementById('f_personal_id').value=s.personal_id||'';
  document.getElementById('f_student_name').value=s.student_name||'';
  document.getElementById('f_whatsapp').value=s.whatsapp||'';
  document.getElementById('f_final_result').value=s.final_result||'';
  document.getElementById('f_level_reached').value=s.level_reached_2026||'';
  document.getElementById('f_teacher').value=s.teacher_2026||'';
  document.getElementById('f_mother_phone').value=s.mother_phone||'';
  document.getElementById('f_father_phone').value=s.father_phone||'';
  document.getElementById('f_other_phone').value=s.other_phone||'';
  document.getElementById('f_residence').value=s.residence||'';
  document.getElementById('f_home_address').value=s.home_address||'';
  document.getElementById('f_road').value=s.road||'';
  document.getElementById('f_complex').value=s.complex_name||'';
  document.getElementById('modal').classList.add('open');
}
function closeModal(){document.getElementById('modal').classList.remove('open');}
async function saveStudent(){
  const editId=document.getElementById('editId').value;
  const body={
    personal_id:document.getElementById('f_personal_id').value.trim(),
    student_name:document.getElementById('f_student_name').value.trim(),
    whatsapp:document.getElementById('f_whatsapp').value.trim(),
    final_result:document.getElementById('f_final_result').value,
    level_reached_2026:document.getElementById('f_level_reached').value.trim(),
    teacher_2026:document.getElementById('f_teacher').value.trim(),
    mother_phone:document.getElementById('f_mother_phone').value.trim(),
    father_phone:document.getElementById('f_father_phone').value.trim(),
    other_phone:document.getElementById('f_other_phone').value.trim(),
    residence:document.getElementById('f_residence').value.trim(),
    home_address:document.getElementById('f_home_address').value.trim(),
    road:document.getElementById('f_road').value.trim(),
    complex_name:document.getElementById('f_complex').value.trim(),
  };
  if(!body.personal_id||!body.student_name){showToast('الرقم الشخصي واسم الطالب مطلوبان','#e53935');return;}
  const url=editId?'/api/students/'+editId:'/api/students';
  const method=editId?'PUT':'POST';
  const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await res.json();
  if(data.ok){closeModal();showToast(editId?'تم تعديل بيانات الطالب بنجاح':'تم اضافة الطالب بنجاح');loadStudents();}
  else{showToast(data.error||'حدث خطا','#e53935');}
}
function askDelete(id){deleteTargetId=id;document.getElementById('confirmModal').classList.add('open');document.getElementById('confirmDelBtn').onclick=confirmDelete;}
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
            (personal_id,student_name,whatsapp,final_result,level_reached_2026,
             teacher_2026,mother_phone,father_phone,other_phone,residence,
             home_address,road,complex_name)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (d.get("personal_id"), d.get("student_name"), d.get("whatsapp"),
             d.get("final_result"), d.get("level_reached_2026"), d.get("teacher_2026"),
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
            personal_id=?,student_name=?,whatsapp=?,final_result=?,level_reached_2026=?,
            teacher_2026=?,mother_phone=?,father_phone=?,other_phone=?,residence=?,
            home_address=?,road=?,complex_name=?
            WHERE id=?""",
            (d.get("personal_id"), d.get("student_name"), d.get("whatsapp"),
             d.get("final_result"), d.get("level_reached_2026"), d.get("teacher_2026"),
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
.stat-card{background:#fff;border-radius:12px;padding:14px 22px;box

// ===== Groups Table Logic =====
let allGroups=[];
let groupDeleteTargetId=null;
async function loadGroups(){
  const res=await fetch('/api/groups');
  const data=await res.json();
  allGroups=data.groups||[];
  renderGroupTable(allGroups);
  document.getElementById('groupsTotalCount').textContent=allGroups.length;
}
function renderGroupTable(list){
  const body=document.getElementById('groupsBody');
  if(!list.length){body.innerHTML='<tr><td colspan="11" class="no-data">لا توجد بيانات، اضف اول مجموعة</td></tr>';return;}
  body.innerHTML=list.map((g,i)=>{
    const link=g.group_link?'<a href="'+g.group_link+'" target="_blank" style="color:#00BCD4;font-weight:600;">فتح الرابط</a>':'-';
    return '<tr><td>'+(i+1)+'</td><td style="font-weight:600;color:#0097A7;text-align:right;">'+(g.group_name||'-')+'</td><td>'+(g.teacher_name||'-')+'</td><td>'+(g.level_course||'-')+'</td><td>'+(g.last_reached||'-')+'</td><td>'+(g.study_time||'-')+'</td><td>'+(g.ramadan_time||'-')+'</td><td>'+(g.online_time||'-')+'</td><td>'+link+'</td><td>'+(g.session_duration||'-')+'</td><td><button class="action-btn btn-edit" style="color:#0097A7;" onclick="openGroupEdit('+g.id+')">&#9998;</button><button class="action-btn btn-del" onclick="askGroupDelete('+g.id+')">&#128465;</button></td></tr>';
  }).join('');
}
function filterGroupTable(){
  const q=document.getElementById('groupSearchInput').value.toLowerCase();
  renderGroupTable(allGroups.filter(g=>(g.group_name||'').toLowerCase().includes(q)||(g.teacher_name||'').toLowerCase().includes(q)));
}
function clearGroupForm(){
  ['group_name','teacher_name','level_course','last_reached','study_time','ramadan_time','online_time','group_link','session_duration'].forEach(k=>{const el=document.getElementById('gf_'+k);if(el)el.value='';});
  document.getElementById('groupEditId').value='';
}
function openAddGroupModal(){clearGroupForm();document.getElementById('groupModalTitle').textContent='اضافة مجموعة جديدة';document.getElementById('groupModal').classList.add('open');}
function openGroupEdit(id){
  const g=allGroups.find(x=>x.id===id);if(!g)return;
  document.getElementById('groupEditId').value=id;
  document.getElementById('groupModalTitle').textContent='تعديل بيانات المجموعة';
  document.getElementById('gf_group_name').value=g.group_name||'';
  document.getElementById('gf_teacher_name').value=g.teacher_name||'';
  document.getElementById('gf_level_course').value=g.level_course||'';
  document.getElementById('gf_last_reached').value=g.last_reached||'';
  document.getElementById('gf_study_time').value=g.study_time||'';
  document.getElementById('gf_ramadan_time').value=g.ramadan_time||'';
  document.getElementById('gf_online_time').value=g.online_time||'';
  document.getElementById('gf_group_link').value=g.group_link||'';
  document.getElementById('gf_session_duration').value=g.session_duration||'';
  document.getElementById('groupModal').classList.add('open');
}
function closeGroupModal(){document.getElementById('groupModal').classList.remove('open');}
async function saveGroup(){
  const editId=document.getElementById('groupEditId').value;
  const body={
    group_name:document.getElementById('gf_group_name').value.trim(),
    teacher_name:document.getElementById('gf_teacher_name').value.trim(),
    level_course:document.getElementById('gf_level_course').value.trim(),
    last_reached:document.getElementById('gf_last_reached').value.trim(),
    study_time:document.getElementById('gf_study_time').value.trim(),
    ramadan_time:document.getElementById('gf_ramadan_time').value.trim(),
    online_time:document.getElementById('gf_online_time').value.trim(),
    group_link:document.getElementById('gf_group_link').value.trim(),
    session_duration:document.getElementById('gf_session_duration').value.trim(),
  };
  if(!body.group_name){showToast('اسم المجموعة مطلوب','#e53935');return;}
  const url=editId?'/api/groups/'+editId:'/api/groups';
  const method=editId?'PUT':'POST';
  const res=await fetch(url,{method,headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify(body)});
  const data=await res.json();
  if(data.ok){closeGroupModal();showToast(editId?'تم تعديل المجموعة بنجاح':'تم اضافة المجموعة بنجاح','#00BCD4');loadGroups();}
  else{showToast(data.error||'حدث خطا','#e53935');}
}
function askGroupDelete(id){groupDeleteTargetId=id;document.getElementById('groupConfirmModal').classList.add('open');document.getElementById('groupConfirmDelBtn').onclick=confirmGroupDelete;}
async function confirmGroupDelete(){
  if(!groupDeleteTargetId)return;
  const res=await fetch('/api/groups/'+groupDeleteTargetId,{method:'DELETE',credentials:'include'});
  const data=await res.json();
  closeGroupConfirm();
  if(data.ok){showToast('تم حذف المجموعة بنجاح','#00BCD4');loadGroups();}
  else{showToast(data.error||'حدث خطا في الحذف','#e53935');}
  groupDeleteTargetId=null;
}
function closeGroupConfirm(){document.getElementById('groupConfirmModal').classList.remove('open');}
loadGroups();-shadow:0 2px 10px rgba(0,150,180,.1);display:flex;flex-direction:column;align-items:center;min-width:120px;}
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
