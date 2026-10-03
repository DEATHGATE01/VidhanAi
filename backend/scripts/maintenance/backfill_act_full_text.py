"""Backfill acts.full_text from each Act's own PDF.

WHY: the Act pipeline fetches the Act's PDF every time it needs the text
(bill number, commencement, amendment targets), which is slow and makes any
analysis unreproducible offline. The `full_text` column existed but was never
filled. Storing the text once means every later reader — the lineage extractor
today, news/sentiment matching tomorrow — works from the database, and a source
that goes offline stops being a point of failure.

Scope: the first PDF_MAX_PAGES pages via services.act_dossier.fetch_act_text, i.e.
exactly the text the other extractors see, so nothing downstream changes meaning.
The row is only written when the fetch actually returned text — a failed fetch is
counted and reported, never stored as an empty string that would later read as
"this Act has no text".

Usage:
    python scripts/maintenance/backfill_act_full_text.py [--refresh] [--delay 0.6] [--act-ids 4,9]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests  # noqa: E402

from app import create_app  # noqa: E402
from models import Act, db  # noqa: E402
from services.act_dossier import USER_AGENT, fetch_act_text  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-fetch even when text is already stored")
    ap.add_argument("--act-ids", help="comma-separated act ids (default: all)")
    ap.add_argument("--delay", type=float, default=0.6, help="seconds between PDF fetches")
    ap.add_argument("--limit", type=int, help="stop after N acts")
    args = ap.parse_args()

    app = create_app()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    with app.app_context():
        query = Act.query
        if args.act_ids:
            ids = [int(x) for x in args.act_ids.split(",") if x.strip()]
            query = query.filter(Act.id.in_(ids))
        acts = query.order_by(Act.id).all()
        if args.limit:
            acts = acts[:args.limit]

        stored = skipped = failed = notext = 0
        for i, act in enumerate(acts, 1):
            if (act.full_text or "").strip() and not args.refresh:
                skipped += 1
                continue
            text, note = fetch_act_text(act, session)
            if text and len(text.strip()) > 200:
                act.full_text = text
                db.session.commit()
                stored += 1
                print(f"  {i:3d} act {act.id:2d} {str(act.title)[:44]:44s} | stored {len(text):>7,} chars")
            elif text is None:
                failed += 1
                print(f"  {i:3d} act {act.id:2d} {str(act.title)[:44]:44s} | FETCH FAILED: {note}")
            else:
                notext += 1
                print(f"  {i:3d} act {act.id:2d} {str(act.title)[:44]:44s} | text too short ({note})")
            time.sleep(args.delay)

        print(f"\nSUMMARY stored={stored} skipped={skipped} fetch_failed={failed} too_short={notext}")
        have = Act.query.filter(Act.full_text.isnot(None)).count()
        print(f"acts with stored text: {have} / {Act.query.count()}")


if __name__ == "__main__":
    main()
