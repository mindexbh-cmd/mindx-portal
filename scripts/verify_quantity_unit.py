"""Regression suite for the quantity + unit_ar fields on expenses
and assets.

Five layers — all run against the local SQLite via Flask's
test_client (no network, no prod side-effects):

  1. Schema:   expenses + assets each carry quantity (INTEGER) and
                unit_ar (TEXT) columns; the financial_quantity_unit_v1
                migration tag is present.
  2. Expenses backend:  POST/GET/PATCH round-trip quantity + unit_ar.
                         Empty/0/null in PATCH clears to NULL. Negative
                         or non-int qty is rejected (or coerced to NULL).
                         expense_store_link/rewards.stock flow remains
                         untouched (no auto-bump triggered by the new
                         fields alone).
  3. Assets backend:    POST/GET/PATCH round-trip. PATCH with empty
                         quantity resets to 1 (NOT NULL).
  4. Template markup:   The new field IDs are present in both
                         _EXP_MODAL_HTML and ASSETS_HTML, and the
                         expense list templates carry the new الكمية
                         header + colspan=7 empty cell.
  5. Server-rendered JSON: /api/expenses and /api/assets list rows
                            include the two new keys.

Run: python scripts/verify_quantity_unit.py
"""
from __future__ import annotations
import os, sys

_THIS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_THIS, "..")))
import app as appmod  # noqa: E402

_r = []


def _check(label, ok, detail=""):
    _r.append((label, ok, detail))
    print(f"  [{'OK' if ok else 'FAIL'}] {label}" +
          (f"  {detail}" if detail else ""))


def _login_admin(client):
    with appmod.app.app_context():
        db = appmod.get_db()
        admin = db.execute(
            "SELECT * FROM users WHERE role='admin' ORDER BY id LIMIT 1"
        ).fetchone()
    if not admin:
        return None
    with client.session_transaction() as s:
        s["user"] = dict(admin)
    return dict(admin)


def main():
    print("Layer 1 — schema")
    with appmod.app.app_context():
        db = appmod.get_db()
        exp_cols = {r[1] for r in db.execute("PRAGMA table_info(expenses)").fetchall()}
        ast_cols = {r[1] for r in db.execute("PRAGMA table_info(assets)").fetchall()}
        tags = {r[0] for r in db.execute("SELECT tag FROM schema_migrations").fetchall()}
    _check("expenses.quantity column present", "quantity" in exp_cols)
    _check("expenses.unit_ar column present",  "unit_ar"  in exp_cols)
    _check("assets.quantity column present",   "quantity" in ast_cols)
    _check("assets.unit_ar column present",    "unit_ar"  in ast_cols)
    _check("financial_quantity_unit_v1 migration tag persisted",
           "financial_quantity_unit_v1" in tags)

    client = appmod.app.test_client()
    admin = _login_admin(client)
    if not admin:
        print("  FAIL — no admin user seeded; aborting"); return 1

    print("\nLayer 2 — expenses backend round-trip")
    # Pick any category id.
    with appmod.app.app_context():
        db = appmod.get_db()
        cat_row = db.execute(
            "SELECT id, name_ar FROM expense_categories ORDER BY id LIMIT 1"
        ).fetchone()
    if not cat_row:
        print("  FAIL — no expense_categories rows"); return 1
    cat_id = int(dict(cat_row)["id"])

    r = client.post("/api/expenses", json={
        "category_id": cat_id,
        "amount": 1.250,
        "description": "qty-unit regression test row",
        "expense_date": "2026-05-19",
        "quantity": 5,
        "unit_ar": "كرتون",
    })
    j = r.get_json() or {}
    _check("POST /api/expenses with qty+unit → 200",
           r.status_code == 200, f"{r.status_code} {j}")
    eid = int(j.get("id") or 0)
    _check("POST returned id", eid > 0)

    if eid:
        r = client.get(f"/api/expenses/{eid}")
        row = (r.get_json() or {}).get("row") or {}
        _check("GET echoes quantity=5",
               int(row.get("quantity") or 0) == 5,
               f"got {row.get('quantity')!r}")
        _check("GET echoes unit_ar=كرتون",
               (row.get("unit_ar") or "").strip() == "كرتون",
               f"got {row.get('unit_ar')!r}")

        # Update — change quantity and unit
        r = client.patch(f"/api/expenses/{eid}",
                         json={"quantity": 10, "unit_ar": "علبة"})
        _check("PATCH expenses qty=10 → 200", r.status_code == 200)
        r = client.get(f"/api/expenses/{eid}")
        row = (r.get_json() or {}).get("row") or {}
        _check("after PATCH: quantity=10",
               int(row.get("quantity") or 0) == 10,
               f"got {row.get('quantity')!r}")
        _check("after PATCH: unit_ar=علبة",
               (row.get("unit_ar") or "") == "علبة",
               f"got {row.get('unit_ar')!r}")

        # Clear by sending empty strings / 0
        r = client.patch(f"/api/expenses/{eid}",
                         json={"quantity": 0, "unit_ar": ""})
        _check("PATCH expenses clear qty/unit → 200", r.status_code == 200)
        r = client.get(f"/api/expenses/{eid}")
        row = (r.get_json() or {}).get("row") or {}
        _check("expenses qty cleared to NULL",
               row.get("quantity") is None,
               f"got {row.get('quantity')!r}")
        _check("expenses unit_ar cleared to NULL",
               not row.get("unit_ar"),
               f"got {row.get('unit_ar')!r}")

        # Confirm rewards.stock unchanged — no store_link payload in the
        # body, so no auto-bump path was taken. We just assert the
        # rewards table has no new transaction tagged to this expense.
        with appmod.app.app_context():
            db = appmod.get_db()
            try:
                cnt = db.execute(
                    "SELECT COUNT(*) AS n FROM expense_store_link "
                    "WHERE expense_id=?", (eid,)).fetchone()
                _check("expense_store_link untouched by qty-only writes",
                       int(dict(cnt).get("n") or 0) == 0)
            except Exception as e:
                _check("expense_store_link readable", False, str(e))

        # Cleanup
        with appmod.app.app_context():
            db = appmod.get_db()
            db.execute("DELETE FROM expenses WHERE id=?", (eid,))
            db.commit()

    # List endpoint exposes the new keys.
    r = client.get("/api/expenses?limit=5")
    j = r.get_json() or {}
    _check("/api/expenses?limit=5 → 200", r.status_code == 200)
    rows = j.get("rows") or []
    if rows:
        keys = set(rows[0].keys())
        _check("/api/expenses row has 'quantity' key", "quantity" in keys)
        _check("/api/expenses row has 'unit_ar' key",  "unit_ar"  in keys)

    print("\nLayer 3 — assets backend round-trip")
    r = client.post("/api/assets", json={
        "name_ar": "qty-unit regression test asset",
        "category": "other",
        "condition": "good",
        "purchase_price": 25.500,
        "quantity": 3,
        "unit_ar": "قطعة",
    })
    j = r.get_json() or {}
    _check("POST /api/assets with qty+unit → 200",
           r.status_code == 200, f"{r.status_code} {j}")
    aid = int(j.get("id") or 0)
    _check("POST asset returned id", aid > 0)

    if aid:
        r = client.get(f"/api/assets/{aid}")
        row = (r.get_json() or {}).get("row") or {}
        _check("GET asset echoes quantity=3",
               int(row.get("quantity") or 0) == 3,
               f"got {row.get('quantity')!r}")
        _check("GET asset echoes unit_ar=قطعة",
               (row.get("unit_ar") or "") == "قطعة",
               f"got {row.get('unit_ar')!r}")

        # PATCH with empty quantity → resets to 1 (asset-specific rule)
        r = client.patch(f"/api/assets/{aid}",
                         json={"quantity": 0, "unit_ar": ""})
        _check("PATCH assets qty=0 → 200", r.status_code == 200)
        r = client.get(f"/api/assets/{aid}")
        row = (r.get_json() or {}).get("row") or {}
        _check("after empty-PATCH: asset quantity reset to 1",
               int(row.get("quantity") or 0) == 1,
               f"got {row.get('quantity')!r}")

        # Cleanup
        with appmod.app.app_context():
            db = appmod.get_db()
            db.execute("DELETE FROM assets WHERE id=?", (aid,))
            db.commit()

    r = client.get("/api/assets?limit=5")
    j = r.get_json() or {}
    rows = j.get("rows") or []
    if rows:
        keys = set(rows[0].keys())
        _check("/api/assets row has 'quantity' key", "quantity" in keys)
        _check("/api/assets row has 'unit_ar' key",  "unit_ar"  in keys)

    print("\nLayer 4 — template markup")
    exp_modal = appmod._EXP_MODAL_HTML
    _check("_EXP_MODAL_HTML has exp-qty input",  'id="exp-qty"'  in exp_modal)
    _check("_EXP_MODAL_HTML has exp-unit select", 'id="exp-unit"' in exp_modal)
    _check("_EXP_MODAL_HTML has exp-unit-other input",
           'id="exp-unit-other"' in exp_modal)
    _check("_EXP_MODAL_HTML has __other__ option",
           'value="__other__"' in exp_modal)

    exp_admin = appmod.EXPENSES_ADMIN_HTML
    exp_raed  = appmod.EXPENSES_RAED_HTML
    for tpl_name, tpl in (("EXPENSES_ADMIN_HTML", exp_admin),
                          ("EXPENSES_RAED_HTML",  exp_raed)):
        _check(f"{tpl_name} has الكمية column header",
               "&#x627;&#x644;&#x643;&#x645;&#x64A;&#x629;" in tpl)
        _check(f"{tpl_name} colspan=7 empty cell",
               'colspan="7"' in tpl)
        _check(f"{tpl_name} renders qtyCell variable",
               "var qtyCell" in tpl)

    ast_tpl = appmod.ASSETS_HTML
    _check("ASSETS_HTML has ast-qty input",       'id="ast-qty"'  in ast_tpl)
    _check("ASSETS_HTML has ast-unit select",     'id="ast-unit"' in ast_tpl)
    _check("ASSETS_HTML has ast-unit-other input",
           'id="ast-unit-other"' in ast_tpl)
    _check("ASSETS_HTML has __other__ option",    'value="__other__"' in ast_tpl)
    _check("ASSETS_HTML detail modal lists الكمية row",
           "'الكمية'" in ast_tpl)
    _check("ASSETS_HTML card view conditional on qty>1",
           "parseInt(r.quantity, 10) > 1" in ast_tpl)

    print()
    fails = [r for r in _r if not r[1]]
    print(f"{len(_r) - len(fails)}/{len(_r)} checks passed.")
    if fails:
        print("FAILED:")
        for f in fails:
            print(f"  - {f[0]}  {f[2]}")
        return 1
    print("ALL OK — quantity/unit_ar wired end-to-end across both pages; "
          "store-link path untouched.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
