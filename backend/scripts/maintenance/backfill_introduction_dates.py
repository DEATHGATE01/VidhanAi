"""Backfill bills.introduction_date from sourced lifecycle events.

WHY
`ai_service._format_header` prints "**Introduced:** <date>" on every summary. It
used to fall back to `date_scraped` when a bill had no introduction date, which
printed the date THIS system fetched the bill as if it were a legislative fact
("Introduced: August 18, 2026" on a 2023 bill). That fallback is gone, and
`bills.introduction_date` is NULL for all 140 bills -- so without this backfill
the line simply disappears.

The date is already in the database, sourced: every bill PRS publishes a
timeline for has a `lifecycle_events` row with `event_type='introduced'`,
`source='prs_billtrack'` and the real date (e.g. bill 1 -> 2026-08-10). This
copies the earliest such event into `bills.introduction_date`.

HONESTY CONTRACT
- The value is copied from a sourced event; nothing is inferred or guessed.
- Only the EARLIEST 'introduced' event is used (a bill can be reintroduced).
- Bills with no such event keep NULL -- the summary then omits the line.
- Rows already set are left alone (idempotent); --overwrite replaces them from the
  same sourced events.
- Each filled bill is printed with its event id + source, so the value is
  auditable row by row.

Usage (from `backend/`):

    python scripts/maintenance/backfill_introduction_dates.py --dry-run
    python scripts/maintenance/backfill_introduction_dates.py
    python scripts/maintenance/backfill_introduction_dates.py --overwrite
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402
from models import Bill, LifecycleEvent, db  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(description="Backfill bills.introduction_date from sourced lifecycle events.")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--overwrite", action="store_true", help="also replace an existing introduction_date")
    p.add_argument("--limit", type=int, default=None)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    app = create_app()
    with app.app_context():
        # Earliest sourced 'introduced' event per bill, with its provenance.
        rows = db.session.execute(db.text("""
            SELECT bill_id, MIN(event_date) AS first_date, COUNT(*) AS n
            FROM lifecycle_events
            WHERE event_type = 'introduced' AND event_date IS NOT NULL
            GROUP BY bill_id
        """)).all()
        by_bill = {r.bill_id: r.first_date for r in rows}
        print(f"bills with a sourced 'introduced' event: {len(by_bill)}")

        bills = Bill.query.order_by(Bill.id).all()
        if args.limit:
            bills = bills[: args.limit]

        filled = skipped_has_date = still_unknown = 0
        for bill in bills:
            date = by_bill.get(bill.id)
            if bill.introduction_date and not args.overwrite:
                skipped_has_date += 1
                continue
            if not date:
                still_unknown += 1
                continue
            # The event row that supplies the value, so it can be checked.
            ev = LifecycleEvent.query.filter(
                LifecycleEvent.bill_id == bill.id,
                LifecycleEvent.event_type == 'introduced',
                LifecycleEvent.event_date == date,
            ).first()
            if isinstance(date, str):
                date = datetime.fromisoformat(date[:19])
            print(f"  bill {bill.id:4d} -> {date.date() if hasattr(date, 'date') else date}"
                  f"  (event {getattr(ev, 'id', '?')}, source {getattr(ev, 'source', '?')})"
                  f"  {str(bill.title)[:44]}")
            if not args.dry_run:
                bill.introduction_date = date
            filled += 1

        if not args.dry_run:
            db.session.commit()

        total_set = db.session.execute(db.text(
            "SELECT COUNT(*) FROM bills WHERE introduction_date IS NOT NULL")).scalar()
        print(f"\nSUMMARY filled={filled} kept_existing={skipped_has_date} "
              f"no_sourced_event={still_unknown}")
        print(f"bills.introduction_date set now: {total_set}/140"
              + (f" (was {total_set - filled})" if not args.dry_run else " (dry run: unchanged)"))
        if still_unknown:
            print("NOTE: bills with no 'introduced' event keep NULL -- their summary "
                  "omits the Introduced line rather than showing a guessed date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
