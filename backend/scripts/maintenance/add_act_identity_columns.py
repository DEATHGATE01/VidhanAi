"""Idempotent migration: give Acts an identity when the Act number is not published.

`acts.bill_number`  the Bill number the Act came from, read from the Act's own PDF
                    ("Bill No. 105-F of 2026"). This is the identifier we DO have
                    while the gazetted Act number is unpublished — showing it is
                    far better than a bare "Act No.: not found", because it is the
                    same law under its earlier name.

`acts.status_basis` how an in-force status was arrived at, when it was not read
                    from an authoritative record (India Code) but derived from the
                    Act's own assent date. Stored so the UI can label a derived
                    status as derived instead of passing it off as sourced.

Additive and safe against the live database.

Run once:  python backend/scripts/maintenance/add_act_identity_columns.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "instance",
    "regulation_alert.db",
)

COLUMNS = (
    ("bill_number", "VARCHAR(50)"),
    ("status_basis", "TEXT"),
)


def run(db_path: str = DB_PATH) -> int:
    if not os.path.exists(db_path):
        print(f"database not found: {db_path}")
        return 1
    con = sqlite3.connect(db_path)
    try:
        existing = {r[1] for r in con.execute("PRAGMA table_info(acts)")}
        added = []
        for name, ddl in COLUMNS:
            if name in existing:
                continue
            con.execute(f"ALTER TABLE acts ADD COLUMN {name} {ddl}")
            added.append(name)
        con.commit()
        print("acts columns added:", added or "nothing (already present)")
        total = con.execute("SELECT COUNT(*) FROM acts").fetchone()[0]
        with_bill = con.execute(
            "SELECT COUNT(*) FROM acts WHERE bill_number IS NOT NULL").fetchone()[0]
        print(f"acts: {total} | with a stored bill number: {with_bill}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(run())
