"""Idempotent migration: add bill_status column to bill_notifications.

Run once:  python scripts/maintenance/add_bill_status_column.py

The ORM column in models.py covers fresh databases (db.create_all()); this
script patches existing SQLite files so status-change alerting works.
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "instance", "regulation_alert.db"
)


def main():
    if not os.path.exists(DB_PATH):
        print(f"[skip] DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(bill_notifications)")
    cols = {row[1] for row in cur.fetchall()}

    if "bill_status" in cols:
        print("[ok] bill_status column already exists")
        conn.close()
        return

    cur.execute("ALTER TABLE bill_notifications ADD COLUMN bill_status VARCHAR(100)")
    conn.commit()
    print("[ok] added bill_status column to bill_notifications")
    conn.close()


if __name__ == "__main__":
    sys.exit(main())
