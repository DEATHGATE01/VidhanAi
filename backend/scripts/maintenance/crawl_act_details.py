"""Crawl the reachable web for the Act details PRS does not publish.

For every Act that is still missing an Act number or an in-force status, run
`services/web_lookup.crawl_act` (Wikipedia API, India Code, the Act's own PDF,
eGazette, and a note on the walled search engines) and write the RESULT of that
search onto the Act:

    acts.lookup_note      <- the per-source trail, so the UI can show what was
                             actually checked instead of a bare "not found"
    acts.details_checked_at
    acts.act_number       <- ONLY when two independent sources agree, or when the
                             Act's own document carries a Gazette header
    acts.status           <- ONLY when a source states repeal; otherwise untouched

Usage (from `backend/`):

    python scripts/maintenance/crawl_act_details.py --dry-run --limit 3
    python scripts/maintenance/crawl_act_details.py                 # missing only
    python scripts/maintenance/crawl_act_details.py --all           # re-check every Act

Being honest about the outcome is the deliverable: on the 2026 set today this
finds no corroborated number, because PRS never publishes numbers, India Code has
not ingested 2026, and the eGazette search is session-gated. The trail says so
per Act, and a later re-run fills the number in automatically once a source knows.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import requests  # noqa: E402

from app import create_app  # noqa: E402
from models import Act, db  # noqa: E402
from services.web_lookup import USER_AGENT, crawl_act, format_trail  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(description="Crawl the reachable web for missing Act details.")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--act-ids", type=str, default=None)
    p.add_argument("--all", action="store_true", help="re-check Acts that already have a number")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--delay", type=float, default=1.5)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    with app.app_context():
        query = Act.query
        if args.act_ids:
            ids = [int(x) for x in args.act_ids.split(",") if x.strip()]
            query = query.filter(Act.id.in_(ids))
        elif not args.all:
            query = query.filter(db.or_(Act.act_number.is_(None),
                                        Act.status.is_(None),
                                        Act.status == "unknown"))
        acts = query.order_by(Act.year.desc(), Act.id).all()
        if args.limit:
            acts = acts[: args.limit]
        print(f"acts to crawl: {len(acts)}")

        stats = {"number_found": 0, "status_found": 0, "nothing": 0}
        for act in acts:
            result = crawl_act(act, session)
            number = result["corroborated_number"]
            trail = format_trail(result)

            got_number = bool(number) and act.act_number != number
            if got_number:
                stats["number_found"] += 1
            else:
                stats["nothing"] += 1

            print(f"  {act.id:3d} {str(act.title)[:44]:44s} | number: "
                  f"{('No. %d' % number) if number else 'not corroborated':16s} | "
                  f"sources: {len(result['trail'])}")

            if args.dry_run:
                continue
            act.lookup_note = trail[:4000]
            act.details_checked_at = datetime.utcnow()
            if got_number:
                act.act_number = number
                from services.act_dossier import append_evidence
                append_evidence(act, f"Act number No. {number} corroborated by "
                                     f"{sorted(set(sum(result['corroborated_by'].values(), [])))}")
            db.session.commit()
            time.sleep(args.delay)

        print("\nSUMMARY " + " ".join(f"{k}={v}" for k, v in stats.items()))
        print("acts still without a number:", db.session.execute(db.text(
            "SELECT COUNT(*) FROM acts WHERE act_number IS NULL")).scalar(), "/50")
        print("acts with a recorded lookup trail:", db.session.execute(db.text(
            "SELECT COUNT(*) FROM acts WHERE lookup_note LIKE 'Web lookup%'")).scalar(), "/50")
    return 0


if __name__ == "__main__":
    sys.exit(main())
