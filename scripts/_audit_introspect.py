"""READ-ONLY Postgres schema introspection for SCHEMA_AUDIT.md.

Pulls every public-schema table + columns + PK + FK + check + unique
constraint via information_schema and pg_catalog. Serializes to a JSON
working file under backups/. NO writes to the DB.
"""
import os, sys, json, time
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DB_URL = os.environ.get("DATABASE_URL", "").strip()
if not DB_URL:
    print("DATABASE_URL not set — aborting"); raise SystemExit(2)

import psycopg2
import psycopg2.extras

conn = psycopg2.connect(DB_URL)
conn.set_session(readonly=True)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def q(sql, params=()):
    cur.execute(sql, params)
    return cur.fetchall()


# 1. All tables in public schema
tables = [r["table_name"] for r in q(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='public' AND table_type='BASE TABLE' "
    "ORDER BY table_name"
)]
print(f"tables: {len(tables)}")

# 2. Columns per table
columns = {}
for t in tables:
    rows = q(
        "SELECT column_name, data_type, udt_name, is_nullable, "
        "column_default, character_maximum_length, numeric_precision, "
        "numeric_scale, ordinal_position "
        "FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name=%s "
        "ORDER BY ordinal_position", (t,)
    )
    columns[t] = [dict(r) for r in rows]

# 3. Primary keys
pks = {}
pk_rows = q("""
    SELECT tc.table_name, kcu.column_name, kcu.ordinal_position
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
    WHERE tc.table_schema='public'
      AND tc.constraint_type='PRIMARY KEY'
    ORDER BY tc.table_name, kcu.ordinal_position
""")
for r in pk_rows:
    pks.setdefault(r["table_name"], []).append(r["column_name"])

# 4. Foreign keys
fks = []
fk_rows = q("""
    SELECT tc.table_name AS src_table,
           kcu.column_name AS src_column,
           ccu.table_name AS tgt_table,
           ccu.column_name AS tgt_column,
           tc.constraint_name AS fk_name,
           rc.update_rule, rc.delete_rule
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage ccu
      ON ccu.constraint_name = tc.constraint_name
     AND ccu.table_schema = tc.table_schema
    JOIN information_schema.referential_constraints rc
      ON rc.constraint_name = tc.constraint_name
    WHERE tc.constraint_type='FOREIGN KEY'
      AND tc.table_schema='public'
    ORDER BY tc.table_name, kcu.column_name
""")
fks = [dict(r) for r in fk_rows]

# 5. Unique constraints (not PK)
uniques = []
uniq_rows = q("""
    SELECT tc.table_name, kcu.column_name, tc.constraint_name
    FROM information_schema.table_constraints tc
    JOIN information_schema.key_column_usage kcu
      ON tc.constraint_name = kcu.constraint_name
     AND tc.table_schema = kcu.table_schema
    WHERE tc.constraint_type='UNIQUE'
      AND tc.table_schema='public'
    ORDER BY tc.table_name, kcu.ordinal_position
""")
uniques = [dict(r) for r in uniq_rows]

# 6. Check constraints (via pg_catalog — information_schema doesn't expose the SQL)
checks = []
chk_rows = q("""
    SELECT c.conname  AS constraint_name,
           t.relname  AS table_name,
           pg_get_constraintdef(c.oid, true) AS def
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_namespace n ON n.oid = t.relnamespace
    WHERE c.contype = 'c' AND n.nspname = 'public'
    ORDER BY t.relname, c.conname
""")
checks = [dict(r) for r in chk_rows]

# 7. Row counts per table — useful to flag empty / heavily-used tables
counts = {}
for t in tables:
    try:
        cur.execute(f'SELECT COUNT(*) AS n FROM public."{t}"')
        counts[t] = cur.fetchone()["n"]
    except Exception as ex:
        counts[t] = f"ERR: {ex}"

# 8. Indexes (informational; helps identify de-facto uniqueness / lookups)
indexes = q("""
    SELECT schemaname, tablename, indexname, indexdef
    FROM pg_indexes
    WHERE schemaname='public'
    ORDER BY tablename, indexname
""")

out = {
    "captured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "table_count": len(tables),
    "tables": tables,
    "columns": columns,
    "primary_keys": pks,
    "foreign_keys": fks,
    "unique_constraints": uniques,
    "check_constraints": checks,
    "row_counts": counts,
    "indexes": [dict(r) for r in indexes],
}

# Make JSON-safe
def safe(v):
    if isinstance(v, (str, int, float, bool, type(None))): return v
    if isinstance(v, dict): return {k: safe(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)): return [safe(x) for x in v]
    return str(v)


path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "backups", "schema_introspect.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(safe(out), f, ensure_ascii=False, indent=2)

print(f"tables={len(tables)} columns_total={sum(len(c) for c in columns.values())} "
      f"pks={sum(len(v) for v in pks.values())} fks={len(fks)} "
      f"uniques={len(uniques)} checks={len(checks)} indexes={len(indexes)}")
print(f"written: {path}")

cur.close(); conn.close()
