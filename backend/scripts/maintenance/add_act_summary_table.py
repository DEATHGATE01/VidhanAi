"""Idempotent migration: create `act_summaries` and add `acts.commencement_note`.

`act_summaries` mirrors `bill_summaries`' provenance fields (model_version,
summary_type) but keys on an Act and records the PDF the text came from, because an
Act is summarized from the Act's own document, not from PRS bill content.

`acts.commencement_note` holds how an Act commences when it fixes no date (e.g.
"by Central Government notification") — a sourced fact from the Act's text that is
more useful than an empty date field.

Additive and safe against the live database.

Run once:  python backend/scripts/maintenance/add_act_summary_table.py
"""
import os
import sqlite3
import sys

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "instance",
    "regulation_alert.db",
)

CREATE_ACT_SUMMARIES = """
CREATE TABLE IF NOT EXISTS act_summaries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    act_id         INTEGER NOT NULL UNIQUE REFERENCES acts(id),
    summary        TEXT,
    summary_type   VARCHAR(50),
    confidence     FLOAT,
    model_version  VARCHAR(80),
    source_url     VARCHAR(500),
    text_chars     INTEGER,
    generated_at   DATETIME
)
"""

ACT_COLUMNS = (
    ("commencement_note", "TEXT"),
)


def run(db_path: str = DB_PATH) -> int:
    if not os.path.exists(db_path):
        print(f"database not found: {db_path}")
        return 1
    con = sqlite3.connect(db_path)
    try:
        existing_tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "act_summaries" in existing_tables:
            print("act_summaries: already present")
        else:
            con.execute(CREATE_ACT_SUMMARIES)
            print("act_summaries: created")

        existing_cols = {r[1] for r in con.execute("PRAGMA table_info(acts)")}
        added = []
        for name, ddl in ACT_COLUMNS:
            if name in existing_cols:
                continue
            con.execute(f"ALTER TABLE acts ADD COLUMN {name} {ddl}")
            added.append(name)
        con.commit()
        print("acts columns added:", added or "nothing (already present)")
        print("acts:", con.execute("SELECT COUNT(*) FROM acts").fetchone()[0],
              "| act_summaries rows:", con.execute(
                  "SELECT COUNT(*) FROM act_summaries").fetchone()[0])
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(run())
