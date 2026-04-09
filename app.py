from flask import Flask, request, session, redirect, g
import sqlite3, hashlib, os
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
        id INTEGER PRIMARY KEY, username TEXT UNIQUE,
        password TEXT, name TEXT, role TEXT, department TEXT)""")
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
    .btn{
      display:inline-block;
      padding:18px 48px;
      background:linear-gradient(135deg,#6B3FA0,#8B5CC8);
      color:#fff;
      border:none;
      border-radius:14px;
      font-size:18px;
      font-weight:700;
      cursor:pointer;
      text-decoration:none;
      letter-spacing:0.5px;
    }
    .btn:hover{opacity:0.9;}
  </style>
</head>
<body>
  <a href="/database" class="btn">قاعدة البيانات</a>
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
    user = db.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hp(password))).fetchone()
    if not user:
        return render_login("اسم المستخدم أو كلمة المرور غلط"), 401
    session["user"] = dict(user)
    return redirect("/dashboard")

@app.route("/dashboard")
@login_required
def dashboard():
    return HOME_HTML

@app.route("/database")
@login_required
def database():
    return "<h2>قاعدة البيانات</h2>"

@app.route("/api/logout", methods=["POST", "GET"])
def api_logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
