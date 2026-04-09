from flask import Flask, render_template_string, request, jsonify, session, redirect, g
import sqlite3, hashlib, os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mindx2026secret")
DB = os.environ.get("DB_PATH", "mindx.db")

def get_db():
        # v2 - login only
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
                                                    department TEXT
                                                        )""")
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
    for u, p, n, r, d in users:
                try:
                                db.execute("INSERT INTO users(username,password,name,role,department) VALUES(?,?,?,?,?)",
                                                                  (u, hp(p), n, r, d))
                            except:
            pass
    db.commit()
    db.close()

if not os.path.exists(DB):
        init_db()

LOGIN_HTML = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
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

def render_login(error=""):
        html = LOGIN_HTML
    if error:
                html = html.replace("{% if error %}", "").replace("{% endif %}", "").replace("{{ error }}", error)
else:
        html = html.replace("{% if error %}", "<!--").replace("{% endif %}", "-->").replace("{{ error }}", "")
    return html

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
    user = db.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (username, hp(password))
    ).fetchone()
    if not user:
                return render_login("اسم المستخدم أو كلمة المرور غلط"), 401
            session["user"] = dict(user)
    return render_login()

@app.route("/api/logout", methods=["POST", "GET"])
def api_logout():
        session.clear()
    return redirect("/")

if __name__ == "__main__":
        app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
