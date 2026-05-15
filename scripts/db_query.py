"""Read-only DB query helper.

Connects to local SQLite (DB_PATH or mindx.db) by default; pass
DATABASE_URL=postgres://... in the env to target prod.

Refuses to run any statement that isn't a SELECT, EXPLAIN, or PRAGMA.
Use --force-write only when you've *really* thought about it.

Usage:
    python scripts/db_query.py "SELECT COUNT(*) FROM students"
    python scripts/db_query.py --tables
    python scripts/db_query.py --schema students
    python scripts/db_query.py --csv "SELECT id, student_name FROM students LIMIT 10"
"""
from __future__ import annotations
import argparse
import csv
import os
import sys


def _connect():
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if url:
        import psycopg2  # type: ignore
        return ("pg", psycopg2.connect(url))
    import sqlite3
    db_path = os.environ.get("DB_PATH", "mindx.db")
    if not os.path.exists(db_path):
        raise SystemExit(f"local DB not found at {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return ("sqlite", conn)


_ALLOWED_PREFIXES = ("select", "explain", "pragma", "with")


def _is_readonly(sql: str) -> bool:
    head = sql.lstrip().lower()
    return any(head.startswith(p) for p in _ALLOWED_PREFIXES)


def list_tables(kind: str, cur) -> None:
    if kind == "pg":
        cur.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' ORDER BY table_name")
    else:
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "ORDER BY name")
    for row in cur.fetchall():
        name = row[0]
        print(name)


def show_schema(kind: str, cur, table: str) -> None:
    if kind == "pg":
        cur.execute(
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_name=%s ORDER BY ordinal_position", (table,))
    else:
        # PRAGMA can't be parameterised — sanitise.
        if not table.replace("_", "").isalnum():
            raise SystemExit(f"refusing PRAGMA on suspicious table name: {table!r}")
        cur.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        print("\t".join(str(c) for c in row))


def run_query(kind: str, cur, sql: str, as_csv: bool) -> None:
    cur.execute(sql)
    if cur.description is None:
        print(f"(no result set; rowcount={cur.rowcount})")
        return
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if as_csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(cols)
        for r in rows:
            writer.writerow(list(r))
    else:
        widths = [max(len(c), 4) for c in cols]
        for r in rows:
            for i, v in enumerate(r):
                widths[i] = max(widths[i], len(str(v)))
        line = "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
        print(line)
        print("  ".join("-" * w for w in widths))
        for r in rows:
            print("  ".join(str(v).ljust(widths[i])
                            for i, v in enumerate(r)))
        print(f"\n({len(rows)} row(s))")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("sql", nargs="?",
                    help="SQL to execute (read-only)")
    ap.add_argument("--tables", action="store_true",
                    help="list all tables")
    ap.add_argument("--schema", metavar="TABLE",
                    help="show columns for TABLE")
    ap.add_argument("--csv", action="store_true",
                    help="output as CSV instead of aligned columns")
    ap.add_argument("--force-write", action="store_true",
                    help="lift the read-only safety check (be careful!)")
    args = ap.parse_args()

    kind, conn = _connect()
    cur = conn.cursor()

    try:
        if args.tables:
            list_tables(kind, cur)
            return 0
        if args.schema:
            show_schema(kind, cur, args.schema)
            return 0
        if not args.sql:
            ap.print_help()
            return 1
        if not args.force_write and not _is_readonly(args.sql):
            print("[db_query] refusing non-SELECT/EXPLAIN/PRAGMA. "
                  "Use --force-write if you mean it.", file=sys.stderr)
            return 2
        run_query(kind, cur, args.sql, args.csv)
        return 0
    finally:
        try: conn.close()
        except Exception: pass


if __name__ == "__main__":
    sys.exit(main())
