"""
Acts Sync Script
================
Populates the Acts data spine: acts, lifecycle_events (real PRS status dates),
and bill_act_links. Follows fetch_all_bill_data.py conventions (argparse,
create_app(), batching, --delay between requests, progress prints, idempotent).

Usage:
    python scripts/setup/sync_acts.py --limit 50            # acts + timeline + links
    python scripts/setup/sync_acts.py --bills-only          # refresh status timelines
    python scripts/setup/sync_acts.py --dry-run             # print, write nothing

Steps:
    1. Upsert Acts from the PRS acts listing (deduped by PDF href).
    2. For every bill, fetch its status timeline and upsert LifecycleEvent rows
       with real dates only -- anything unsourced stays NULL.
    3. Run the deterministic linker (services/act_linker.py).
    4. Print a summary.
"""
import sys
import os
import time
import argparse

# Make backend/ importable (same pattern as fetch_all_bill_data.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db, Bill, BillContent, Act, LifecycleEvent
from src.scraping.prs_acts_scraper import PRSActsScraper
from services.act_linker import run_linker, ACT_IMPLYING_STATUSES, normalize


def upsert_acts_from_prs(scraper, limit=None, dry_run=False):
    """Upsert Acts from the PRS acts listing. Returns (new, total)."""
    items = scraper.fetch_acts_list(max_items=limit)
    new = 0
    for item in items:
        act_id = item['act_id']
        # short_title = normalized title (no leading "The"/year, head noun
        # mapped bill->act) per plan §3 — computed from the scraped title only.
        short_title = normalize(item['title'])[:300]
        existing = Act.query.filter_by(act_id=act_id).first()
        if existing:
            # India Code enrichment (enrich_indiacode.py) repoints source/source_url
            # to the India Code item record for enriched acts; a PRS re-sync must
            # never clobber that provenance back to 'prs_acts'.
            enriched = existing.source == 'indiacode'
            changed = (existing.title != item['title']
                       or existing.year != item['year']
                       or existing.pdf_url != item['pdf_url']
                       or existing.short_title != short_title)
            url_changed = (not enriched
                           and existing.source_url != item['source_url'])
            if (changed or url_changed) and not dry_run:
                existing.title = item['title']
                existing.year = item['year']
                existing.pdf_url = item['pdf_url']
                existing.short_title = short_title
                if not enriched:
                    existing.source = 'prs_acts'
                    existing.source_url = item['source_url']
            continue

        new += 1
        if dry_run:
            continue
        act = Act(
            act_id=act_id,
            title=item['title'],
            # short_title: normalized (no leading "The"/year) per plan §3, from
            # the scraped title only.
            short_title=short_title,
            year=item['year'],
            pdf_url=item['pdf_url'],
            source='prs_acts',
            source_url=item['source_url'],
            # act_number / assent_date / commencement_date stay NULL: they are
            # not on the acts listing and are P2 enrichment (India Code), never
            # invented.
            status='unknown',
        )
        db.session.add(act)
    if not dry_run:
        db.session.commit()
    return new, len(items)


def sync_bill_timelines(scraper, dry_run=False, batch_size=25, delay=0.5):
    """Fetch every bill's real status timeline and upsert LifecycleEvent rows.

    Dates come only from the scraped timeline blocks; a bill with no timeline
    gets no events. Returns a counters dict.
    """
    bills = Bill.query.all()
    counters = {'bills': 0, 'fetched': 0, 'events': 0, 'dated_events': 0,
                'undated_events': 0, 'errors': 0}
    pending = 0

    for i, bill in enumerate(bills, 1):
        if not bill.url:
            continue
        counters['bills'] += 1
        events = scraper.fetch_bill_status_timeline(bill.url)
        counters['fetched'] += 1 if events else 0

        for ev in events:
            event_date = ev.get('date')  # datetime or None -- never guessed
            source_url = bill.url  # the PRS bill page the events came from
            notes = ev.get('raw_label') or None

            existing = LifecycleEvent.query.filter_by(
                bill_id=bill.id,
                event_type=ev['event_type'],
                event_date=event_date,
            ).first()
            if existing:
                # Idempotent: refresh source_url/notes only if changed.
                if existing.source_url != source_url or existing.notes != notes:
                    if not dry_run:
                        existing.source_url = source_url
                        existing.notes = notes
                continue

            counters['events'] += 1
            if event_date:
                counters['dated_events'] += 1
            else:
                counters['undated_events'] += 1
            if dry_run:
                continue

            db.session.add(LifecycleEvent(
                bill_id=bill.id,
                event_type=ev['event_type'],
                event_date=event_date,
                house=ev.get('house'),
                source='prs_billtrack',
                source_url=source_url,
                notes=notes,
                is_estimated=False,  # every date here is from scraped content
            ))
            pending += 1
            if pending >= batch_size:
                if not dry_run:
                    db.session.commit()
                pending = 0

        if i % 25 == 0:
            print(f"  [{i}/{len(bills)}] bills processed; events so far: {counters['events']}")
        if delay:
            time.sleep(delay)

    if not dry_run and pending:
        db.session.commit()
    return counters


def main():
    parser = argparse.ArgumentParser(description="Sync Acts, lifecycle events, and bill-act links from PRS")
    parser.add_argument('--limit', type=int, default=None,
                        help='Max acts to fetch (bounded runs keep PRS load low)')
    parser.add_argument('--bills-only', action='store_true',
                        help='Only refresh bill status timelines (skip acts + linker)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print what would happen, write nothing')
    parser.add_argument('--delay', type=float, default=0.5,
                        help='Seconds between HTTP requests (min 0.5s per charter)')
    args = parser.parse_args()
    delay = max(0.5, args.delay)

    print("=" * 70)
    print("Acts sync starting " + ("(DRY RUN)" if args.dry_run else ""))
    print("=" * 70)

    app = create_app()
    scraper = PRSActsScraper()

    with app.app_context():
        if not args.bills_only:
            acts_new, acts_total = upsert_acts_from_prs(scraper, limit=args.limit,
                                                        dry_run=args.dry_run)
            print(f"\n[acts] {acts_new} new / {acts_total} total")
        else:
            acts_total = Act.query.count()

        timeline = sync_bill_timelines(scraper, dry_run=args.dry_run, delay=delay)
        print(f"\n[timeline] bills: {timeline['bills']} with url | fetched: {timeline['fetched']} | "
              f"events: {timeline['events']} ({timeline['dated_events']} dated / "
              f"{timeline['undated_events']} undated)")

        if args.bills_only:
            links_summary = None
        else:
            links_summary = run_linker(dry_run=args.dry_run)
            # The linker only stages rows; commit them (dry-run stages nothing
            # and this call is a no-op).
            if not args.dry_run:
                db.session.commit()
            print(f"\n[links] verified: {links_summary['links_verified']} | "
                  f"candidate: {links_summary['links_candidate']} | "
                  f"pairs skipped (<0.60): {links_summary['pairs_skipped']} | "
                  f"bills considered: {links_summary['bills_considered']} | "
                  f"acts considered: {links_summary['acts_considered']}")

        # Final summary (plan §6 step 4).
        total_acts = Act.query.count()
        total_events = LifecycleEvent.query.count()
        print("\n" + "=" * 70)
        print(f"SUMMARY: acts: {acts_new if not args.bills_only else 0} new / {total_acts} total | "
              f"timeline events: {timeline['events']} new / {total_events} total | "
              + (f"links: {links_summary['links_verified']} verified / "
                 f"{links_summary['links_candidate']} candidate"
                 if links_summary else "links: skipped (--bills-only)"))
        print("=" * 70)


if __name__ == '__main__':
    sys.exit(main())
