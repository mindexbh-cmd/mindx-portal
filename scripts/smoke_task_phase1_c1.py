"""C1 smoke - departments table + 9 seeded rows."""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8',
                              errors='replace')
os.environ["DB_PATH"] = "mindx.db"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")
import app as A

with A.app.app_context():
    db = A.get_db()
    # Columns present
    cols = [r[1] for r in db.execute("PRAGMA table_info(departments)").fetchall()]
    print("[1] columns:", cols)
    assert cols == ['id', 'name_ar', 'icon', 'color', 'sort_order',
                    'is_active', 'created_at'], cols
    # 9 rows
    rows = db.execute("SELECT id, name_ar, icon, color, sort_order "
                       "FROM departments ORDER BY sort_order").fetchall()
    print("[2] row count:", len(rows))
    assert len(rows) == 9
    expected = [
        "الإدارة", "قسم المناهج والامتحانات", "قسم الجودة",
        "قسم الإعلام", "قسم الأفكار والتحفيز", "قسم الفعاليات",
        "قسم شؤون الطلاب", "قسم شؤون الاستقبال", "قسم شؤون المقر",
    ]
    for i, r in enumerate(rows):
        d = dict(r)
        print(" ", d["sort_order"], "|", d["name_ar"], "|", d["icon"],
              "|", d["color"])
        assert d["name_ar"] == expected[i], (d["name_ar"], expected[i])
    # Tag in schema_migrations
    tag_row = db.execute("SELECT 1 FROM schema_migrations "
                          "WHERE tag=?",
                          ("task_phase1_departments_seed_v1",)).fetchone()
    print("[3] migration tag present:", tag_row is not None)
    assert tag_row is not None

# Regression: existing routes still work
c = A.app.test_client()
def login(u, p):
    return c.post("/login", data={"username": u, "password": p},
                  follow_redirects=False).status_code
login("admin", "admin123")
for p in ["/parent", "/points/manage", "/dashboard", "/expenses",
          "/assets"]:
    rv = c.get(p)
    print("[reg] " + p + " ->", rv.status_code)
    assert rv.status_code == 200, p

print("\nC1 smoke passed.")
