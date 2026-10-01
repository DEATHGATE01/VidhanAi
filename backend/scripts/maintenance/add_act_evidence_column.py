"""Idempotent migration: add the Act detail-provenance columns.

`bills` records why a derived/minstry value should be trusted
(`ministry_evidence`). Acts need the same: when an Act number or assent date is
taken from an official PDF or an India Code record, the exact matched text must
be storable so a reader can check it instead of trusting the pipeline.

Additive only -- safe against the live database.

Run once:  python backend/scripts/maintenance/add_act_evidence_column.py
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
    ("evidence", "TEXT"),
    # Which sources were consulted for a missing value, when, and what each
    # answered -- so the UI can show a search trail instead of a bare "Not
    # published by PRS". See enrich_act_details.py.
    ("lookup_note", "TEXT"),
    ("details_checked_at", "DATETIME"),
)


def run(db_path: str = DB_PATH) -> int:
    if not os.path.exists(db_path):
        print(f"database not found: {db_path}")
        return 1
    con = sqlite3.connect(db_path)
    try:
        existing = {row[1] for row in con.execute("PRAGMA table_info(acts)")}
        added = []
        for name, ddl in COLUMNS:
            if name in existing:
                continue
            con.execute(f"ALTER TABLE acts ADD COLUMN {name} {ddl}")
            added.append(name)
        con.commit()
        print("added:", added or "nothing (all present)")
        print("acts:", con.execute("SELECT COUNT(*) FROM acts").fetchone()[0],
              "| with a number:", con.execute(
                  "SELECT COUNT(*) FROM acts WHERE act_number IS NOT NULL").fetchone()[0])
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(run())
