"""Idempotent migration: add ministry provenance columns to `bills`.

Adds ``ministry_source``, ``ministry_confidence`` and ``ministry_evidence`` so a
derived ministry can be told apart from a scraped one (see
``services/ministry_resolver.py``). Additive only -- no table is dropped and no
existing value is touched, so it is safe against the live database.

Run once:  python backend/scripts/maintenance/add_ministry_source_columns.py
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
    ("ministry_source", "VARCHAR(30) DEFAULT 'unknown'"),
    ("ministry_confidence", "FLOAT"),
    ("ministry_evidence", "TEXT"),
)


def run(db_path: str = DB_PATH) -> int:
    if not os.path.exists(db_path):
        print(f"database not found: {db_path}")
        return 1
    con = sqlite3.connect(db_path)
    try:
        existing = {row[1] for row in con.execute("PRAGMA table_info(bills)")}
        added = []
        for name, ddl in COLUMNS:
            if name in existing:
                continue
            con.execute(f"ALTER TABLE bills ADD COLUMN {name} {ddl}")
            added.append(name)
        # Backfill: bills that somehow carry a real ministry but no provenance
        # are treated as scraped; everything else stays 'unknown'.
        if added:
            con.execute(
                "UPDATE bills SET ministry_source = 'prs', ministry_confidence = 1.0 "
                "WHERE ministry_source IS NULL AND ministry IS NOT NULL "
                "AND TRIM(ministry) <> '' AND LOWER(TRIM(ministry)) <> 'unknown'"
            )
            con.execute("UPDATE bills SET ministry_source = 'unknown' WHERE ministry_source IS NULL")
        con.commit()
        print(f"added: {added or 'nothing (already present)'}")
        counts = con.execute(
            "SELECT COALESCE(ministry_source,'(null)') s, COUNT(*) n FROM bills GROUP BY s"
        ).fetchall()
        for src, n in counts:
            print(f"  {src:14s} {n}")
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(run())
