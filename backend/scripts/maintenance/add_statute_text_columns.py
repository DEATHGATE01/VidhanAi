"""Add statute_history.full_text + provenance — the parent statute's own text.

WHY: the diff screen could resolve a Bill and the Act it became, but not the
statute an Act amends, so "compare the 2026 Act with the 2014 Act it changes"
answered with an apology. The parent's text was the missing half.

Where it comes from: India Code's catalogue holds each principal Act as an "ACT"
record with the Act's own PDF attached (the amendment records are separate). The
record is found by title, the PDF is fetched through the DSpace bitstream API, and
pdftotext gives the text — the same reading of the same source the statute-history
chain already uses, so parent text and parent chain agree by construction.

Provenance is stored with the text, because "this is the statute, as India Code
holds it" is a claim the page must be able to back up:
- full_text         : the statute's text (bounded; char count is what was read)
- text_source_url   : the India Code record the text was read from
- text_source_label : human-readable source name
- text_checked_at   : when it was read

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
    "full_text": "TEXT",
    "text_source_url": "VARCHAR(500)",
    "text_source_label": "VARCHAR(200)",
    "text_checked_at": "DATETIME",
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
        existing = {r[1] for r in con.execute("PRAGMA table_info(statute_history)")}
        added = []
        for name, decl in COLUMNS.items():
            if name in existing:
                print(f"  statute_history.{name} already present")
                continue
            con.execute(f"ALTER TABLE statute_history ADD COLUMN {name} {decl}")
            added.append(name)
        con.commit()
        print(f"added: {added or 'nothing'}")
        cols = [r[1] for r in con.execute("PRAGMA table_info(statute_history)")]
        print(f"statute_history columns now: {len(cols)}")
        con.close()


if __name__ == "__main__":
    main()
