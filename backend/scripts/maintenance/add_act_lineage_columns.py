"""Add acts.amends / acts.amends_note — the statute lineage an Act declares.

WHY: the Act page could only show the history of the bill that produced THIS Act
(2026). A statute has a longer history, and the first half of it is stated in the
Act's own text: "An Act further to amend the Andhra Pradesh Reorganisation Act,
2014" and "In the Andhra Pradesh Reorganisation Act, 2014, in section 5, ...".
Those two clauses are authoritative and offline, so they are stored rather than
re-derived (and re-downloaded) on every page view.

- amends      : JSON list, one entry per parent statute
                [{title, year, sections[], cited_act_number, confidence, evidence}]
- amends_note : one-line human summary + the caveat, shown as the source trail

Idempotent: re-running only adds columns that are missing.
"""
import sqlite3
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app import create_app  # noqa: E402
from models import db  # noqa: E402

COLUMNS = {
    "amends": "TEXT",        # JSON: the statutes this Act says it amends
    "amends_note": "TEXT",   # how that was read, and any caveat
}


def main():
    app = create_app()
    with app.app_context():
        uri = str(db.engine.url)
        # SQLAlchemy percent-encodes a Windows path in sqlite URLs
        # ("sqlite:///D%3A%5C..."), so it must be decoded before use.
        path = unquote(uri.replace("sqlite:///", ""))
        if not path or path == uri:
            print(f"not a sqlite database ({uri}); use the project's migration path instead")
            return
        con = sqlite3.connect(path)
        existing = {r[1] for r in con.execute("PRAGMA table_info(acts)")}
        added = []
        for name, decl in COLUMNS.items():
            if name in existing:
                print(f"  acts.{name} already present")
                continue
            con.execute(f"ALTER TABLE acts ADD COLUMN {name} {decl}")
            added.append(name)
        con.commit()
        print(f"added: {added or 'nothing'}")
        cols = [r[1] for r in con.execute("PRAGMA table_info(acts)")]
        print(f"acts columns now: {len(cols)} ({', '.join(sorted(set(COLUMNS) & set(cols))) or 'none of ours'})")
        con.close()


if __name__ == "__main__":
    main()
