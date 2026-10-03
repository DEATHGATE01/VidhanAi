"""Build the amendment history of every parent statute the tracked Acts amend.

For each Acts row that records a parent statute (acts.amends, read from the Act's own
text by extract_act_amendment_targets.py), ask India Code's catalogue what else has
been enacted against that statute, and store the chain once in statute_history.

This is the second half of a statute's history. The Act's own page shows the bill that
produced THAT Act; this shows the chapters before it — for the Andhra Pradesh
Reorganisation Act, 2014 those are Act 19 of 2014, the Removal of Difficulties order
of 2015 and Act 12 of 2015, each with the India Code handle it was read from.

Nothing is inferred: an India Code search that returns nothing usable stores an empty
chain WITH the reason, and the UI shows that reason.

Usage:
    python scripts/maintenance/build_statute_history.py [--refresh] [--delay 1.0] [--limit 5]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests  # noqa: E402

from app import create_app  # noqa: E402
from models import Act, StatuteHistory, db  # noqa: E402
from services.statute_history import USER_AGENT_FALLBACK, discover_parent_history, parent_key  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true", help="re-query even when a chain is already stored")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between India Code queries")
    ap.add_argument("--limit", type=int, help="stop after N parent statutes")
    args = ap.parse_args()

    app = create_app()
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT_FALLBACK})

    with app.app_context():
        # Collect the distinct parent statutes across all Acts.
        parents = {}
        for act in Act.query.order_by(Act.id).all():
            for parent in json.loads(act.amends or "[]"):
                key = parent_key(parent["title"], parent["year"])
                if key and key not in parents:
                    parents[key] = (parent["title"], str(parent["year"]), act.id)
        print(f"distinct parent statutes across the set: {len(parents)}")

        built = skipped = empty = failed = 0
        for i, (key, (title, year, act_id)) in enumerate(sorted(parents.items()), 1):
            if args.limit and (built + skipped) >= args.limit:
                break
            row = StatuteHistory.query.filter_by(parent_key=key).first()
            if row and not args.refresh:
                skipped += 1
                continue
            entries, note, url = discover_parent_history(title, year, session)
            if row is None:
                row = StatuteHistory(parent_key=key)
                db.session.add(row)
            row.parent_title, row.parent_year = title, year
            row.entries = json.dumps(entries, ensure_ascii=False) if entries else None
            row.note, row.source_url = note, url
            db.session.commit()
            if entries:
                built += 1
                print(f"  {i:3d} {title[:42]:42s} ({year}) | {len(entries)} chapter(s): "
                      f"{', '.join((e['act_number'] or e['year'] or '?') for e in entries[:5])}")
            else:
                empty += 1
                print(f"  {i:3d} {title[:42]:42s} ({year}) | no catalogued amendments: {note[:70]}")
            time.sleep(args.delay)

        print(f"\nSUMMARY chains_built={built} already_stored={skipped} empty={empty}")
        total = StatuteHistory.query.count()
        with_entries = StatuteHistory.query.filter(StatuteHistory.entries.isnot(None)).count()
        print(f"statute_history rows: {total} ({with_entries} carrying a chain)")


if __name__ == "__main__":
    main()
