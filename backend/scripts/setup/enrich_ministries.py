"""Enrich bills with a ministry when PRS does not publish one.

Usage (run from `backend/` or anywhere -- paths are resolved from this file):

    python scripts/setup/enrich_ministries.py --offline --limit 20   # text tier only, no network
    python scripts/setup/enrich_ministries.py                        # all tiers, whole database
    python scripts/setup/enrich_ministries.py --bill-ids 10,32,119   # a few bills (demo prep)
    python scripts/setup/enrich_ministries.py --dry-run              # print, write nothing

Tiers, cheapest first: PRS page (network) -> bill's own text (offline) -> Groq
from a closed list of Union ministries. Every result records how it was obtained
(`ministry_source`) plus confidence and evidence, and a scraped value is never
replaced by a derived one. A bill that no tier can resolve keeps `Unknown` --
nothing is invented.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from app import create_app  # noqa: E402
from models import Bill, db  # noqa: E402
from services.ministry_resolver import apply_resolution, resolve_ministry  # noqa: E402


def parse_args():
    p = argparse.ArgumentParser(description="Resolve missing Bill ministries with provenance.")
    p.add_argument("--limit", type=int, default=None, help="max bills to process")
    p.add_argument("--bill-ids", type=str, default=None, help="comma-separated Bill.id values")
    p.add_argument("--offline", action="store_true", help="skip network tiers (PRS + LLM)")
    p.add_argument("--no-llm", action="store_true", help="use PRS + text tiers, skip the LLM")
    p.add_argument("--dry-run", action="store_true", help="print results, write nothing")
    p.add_argument("--delay", type=float, default=0.4, help="seconds between network calls")
    p.add_argument("--refresh", action="store_true", help="also revisit bills already resolved")
    p.add_argument(
        "--renormalise",
        action="store_true",
        help="offline: re-map already-scraped 'prs' labels onto full ministry names, no network",
    )
    return p.parse_args()


def renormalise_existing(dry_run: bool = False) -> int:
    """Fix up 'prs' rows whose stored value is still PRS's short label.

    PRS publishes a taxonomy label ("Finance", "Personnel, Grievances and
    Pensions"). Rows written before ``canonical_from_short`` existed therefore
    read oddly in the UI. This rewrites only the display name -- the source stays
    'prs' and confidence stays 1.0, and the raw scraped string is preserved in
    the evidence column, so nothing about provenance changes. No network calls.
    """
    from services.ministry_resolver import canonical_from_short

    rows = Bill.query.filter(Bill.ministry_source == "prs").all()
    changed = 0
    for bill in rows:
        canonical = canonical_from_short(bill.ministry or "")
        if not canonical or canonical == bill.ministry:
            continue
        print(f"  {bill.id:4d} {bill.ministry!r:46s} -> {canonical}")
        if not dry_run:
            bill.ministry = canonical
        changed += 1
    if not dry_run:
        db.session.commit()
    print(f"renormalised {changed}/{len(rows)} scraped rows"
          + (" (dry run, nothing written)" if dry_run else ""))
    return 0


def main() -> int:
    args = parse_args()
    app = create_app()

    with app.app_context():
        if args.renormalise:
            return renormalise_existing(dry_run=args.dry_run)

        query = Bill.query
        if args.bill_ids:
            ids = [int(x) for x in args.bill_ids.split(",") if x.strip()]
            query = query.filter(Bill.id.in_(ids))
        elif not args.refresh:
            query = query.filter(
                (Bill.ministry == None)  # noqa: E711
                | (Bill.ministry == "")
                | (Bill.ministry == "Unknown")
            )
        bills = query.order_by(Bill.id).limit(args.limit).all() if args.limit else query.order_by(Bill.id).all()
        print(f"bills to process: {len(bills)}")

        stats = {"prs": 0, "bill_text": 0, "llm_inferred": 0, "unresolved": 0, "skipped": 0}
        for idx, bill in enumerate(bills, 1):
            try:
                resolution = resolve_ministry(
                    bill,
                    allow_network=not args.offline,
                    allow_llm=not (args.offline or args.no_llm),
                )
                if not resolution:
                    stats["unresolved"] += 1
                    print(f"  [--] {bill.id:4d} {bill.title[:58]:58s} no tier resolved it")
                else:
                    stats[resolution["source"]] = stats.get(resolution["source"], 0) + 1
                    print(
                        f"  [{resolution['source']:12s}] {bill.id:4d} "
                        f"{resolution['ministry'][:46]:46s} conf={resolution['confidence']}"
                    )
                    if not args.dry_run:
                        apply_resolution(bill, resolution)
                if not args.dry_run and idx % 25 == 0:
                    db.session.commit()
                    print(f"  ... committed {idx}/{len(bills)}")
            except Exception as exc:
                stats["skipped"] += 1
                print(f"  [!!] bill {bill.id} failed: {exc}")
            finally:
                if not args.offline:
                    time.sleep(args.delay)

        if not args.dry_run:
            db.session.commit()

        print("\nSUMMARY " + " ".join(f"{k}={v}" for k, v in stats.items()))
        rows = db.session.execute(
            db.text("SELECT COALESCE(ministry_source,'(null)') s, COUNT(*) n FROM bills GROUP BY s ORDER BY n DESC")
        ).all()
        print("coverage now: " + ", ".join(f"{s}={n}" for s, n in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
