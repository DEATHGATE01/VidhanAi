"""Rewrite commencement quotes whose text was corrupted by the PDF's two-column layout.

These Act PDFs are two-column, so the right column's text can bleed into the middle
of a commencement clause, producing evidence like:

    Commencement from the Act's own text: 'come into force on such date as the
    Central Government may, by 52 of 1962'

The extractor now cuts such a quote at the first stray "N of YYYY"
(`services.act_dossier.extract_commencement`). This repairs the few rows written
before that guard, by RECOMPUTING the quote from the Act's own document and
replacing the corrupted fragment in place (replace, not append — re-running this
script is idempotent).

Run once:  python backend/scripts/maintenance/repair_commencement_quotes.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import requests  # noqa: E402

from app import create_app  # noqa: E402
from models import Act, db  # noqa: E402
from services.act_dossier import USER_AGENT, extract_commencement, fetch_act_text  # noqa: E402

FRAGMENT = re.compile(r"Commencement from the Act's own text: '([^']*)'")
BLEED = re.compile(r"\b\d{1,3}\s+of\s+\d{4}\b")


def is_garbled(quote: str) -> bool:
    """A quote carrying a stray 'N of YYYY' bled in from the facing column."""
    return bool(BLEED.search(quote)) or len(quote.split()) > 40


def main() -> int:
    parser = argparse.ArgumentParser(description="De-bleed stored commencement quotes.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    app = create_app()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    with app.app_context():
        targets = []
        for act in Act.query.order_by(Act.id).all():
            for m in FRAGMENT.finditer(act.evidence or ""):
                if is_garbled(m.group(1)):
                    targets.append((act, m.group(1)))

        print(f"acts with a corrupted commencement quote: {len(targets)}")
        repaired = failed = 0
        for act, bad_quote in targets:
            text, note = fetch_act_text(act, session)
            if not text:
                failed += 1
                print(f"  act {act.id:3d}: PDF unreadable ({note}) — left as is")
                continue
            _when, _note, good_quote = extract_commencement(text)
            if not good_quote or good_quote == bad_quote:
                failed += 1
                print(f"  act {act.id:3d}: no cleaner quote available — left as is")
                continue
            print(f"  act {act.id:3d}: {bad_quote[:52]}...<br>  -> {good_quote[:52]}...".replace("<br>", "\n        "))
            if args.dry_run:
                continue
            act.evidence = (act.evidence or "").replace(
                f"Commencement from the Act's own text: '{bad_quote}'",
                f"Commencement from the Act's own text: '{good_quote}'",
            )[:2000]
            repaired += 1
            db.session.commit()

        if not args.dry_run:
            db.session.commit()

        remaining = sum(
            1 for act in Act.query.order_by(Act.id).all()
            for m in FRAGMENT.finditer(act.evidence or "") if is_garbled(m.group(1))
        )
        print(f"repaired: {repaired} | failed: {failed} | corrupted quotes remaining: {remaining}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
