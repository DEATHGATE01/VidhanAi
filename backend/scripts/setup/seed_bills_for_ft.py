"""
Seed the SQLite database with bill content for fine-tuning dataset prep.

Why this exists (PHASE2_STATUS.md / PHASE1_STATUS.md):
    The dataset generator (ml_pipeline/1_generate_dataset.py) reads source bill
    text from the local SQLite DB. For Phase 2 we need >= 100 distinct bills
    with full text to feed the QLoRA fine-tune. This script:

        1. Fetches the bill list from PRS India BillTrack.
        2. For each bill, fetches the full detail page content.
        3. Persists metadata + content into the DB (idempotent: skips bills
           that already have content unless --refresh is passed).
        4. Reports how many usable bills (>= MIN_TEXT_CHARS) are available for
           the dataset generator.

Usage:
    python seed_bills_for_ft.py                       # seed up to --limit bills
    python seed_bills_for_ft.py --limit 200 --delay 0.8
    python seed_bills_for_ft.py --refresh             # re-fetch existing content
    python seed_bills_for_ft.py --stats               # report DB readiness only

Notes:
    - Respects PRS by defaulting to a 1.0s delay between detail-page fetches.
    - Resumable: bills that already have content are skipped, so an interrupted
      run can simply be restarted.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR.parent))  # for `src.scraping` import path

from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("vidhanai.seed")

MIN_TEXT_CHARS = 500  # Matches 1_generate_dataset.py's floor.


def build_app():
    from app import create_app
    return create_app()


def seed_bills(app, limit: int, delay: float, refresh: bool) -> dict:
    from models import db, Bill, BillContent

    scraper = PRSBillTrackScraper()
    stats = {"fetched_list": 0, "skipped_exists": 0, "added_content": 0,
             "updated_content": 0, "no_content": 0, "errors": 0}

    with app.app_context():
        # 1. Get the bill list.
        logger.info("Fetching bill list from PRS ...")
        prs_bills = scraper.fetch_bill_list(max_items=limit)
        stats["fetched_list"] = len(prs_bills)
        logger.info("Got %d bills in list.", len(prs_bills))

        for idx, bill_data in enumerate(prs_bills, start=1):
            url = bill_data.get("url", "")
            bill_id = url.rstrip("/").split("/")[-1] if url else bill_data.get("title", "")[:50]
            title = bill_data.get("title", "Unknown")
            if not bill_id or not title:
                continue

            try:
                bill = Bill.query.filter_by(bill_id=bill_id).first()
                if not bill:
                    bill = Bill(
                        bill_id=bill_id,
                        title=title,
                        ministry=bill_data.get("ministry"),
                        status=bill_data.get("status"),
                        url=url,
                        introduction_date=bill_data.get("introduction_date"),
                    )
                    db.session.add(bill)
                    db.session.flush()  # assign bill.id

                # Skip if content already present and we're not refreshing.
                has_content = bill.content and (bill.content.full_text or "").strip()
                if has_content and not refresh:
                    stats["skipped_exists"] += 1
                    continue

                details = scraper.fetch_bill_details(url)
                if not details:
                    stats["errors"] += 1
                    continue

                content_text = details.get("content") or ""
                if len(content_text.strip()) < MIN_TEXT_CHARS:
                    stats["no_content"] += 1
                    continue

                if bill.content:
                    bill.content.full_text = content_text
                    bill.content.pdf_link = details.get("pdf_url")
                    stats["updated_content"] += 1
                else:
                    bc = BillContent(
                        bill_id=bill.id,
                        full_text=content_text,
                        pdf_link=details.get("pdf_url"),
                    )
                    db.session.add(bc)
                    stats["added_content"] += 1

                # Commit every 10 bills to bound the transaction.
                if idx % 10 == 0:
                    db.session.commit()

                time.sleep(delay)
                if idx % 25 == 0:
                    logger.info("  ...%d/%d processed so far", idx, len(prs_bills))
            except Exception as exc:  # pragma: no cover - network/parse hiccup
                logger.warning("Error on %s (idx %d): %s", bill_id, idx, exc)
                stats["errors"] += 1
                continue

        db.session.commit()

        # 2. Report readiness.
        usable = (db.session.query(Bill)
                  .join(BillContent)
                  .filter(db.func.length(BillContent.full_text) >= MIN_TEXT_CHARS)
                  .count())
        stats["usable_bills_for_ft"] = usable
        stats["total_bills"] = db.session.query(Bill).count()
        stats["bills_with_content"] = db.session.query(Bill).join(BillContent).count()

    scraper.close()
    return stats


def show_stats(app) -> dict:
    from models import db, Bill, BillContent
    with app.app_context():
        total = db.session.query(Bill).count()
        with_content = db.session.query(Bill).join(BillContent).count()
        usable = (db.session.query(Bill)
                  .join(BillContent)
                  .filter(db.func.length(BillContent.full_text) >= MIN_TEXT_CHARS)
                  .count())
        return {
            "total_bills": total,
            "bills_with_content": with_content,
            "usable_bills_for_ft": usable,
            "min_text_chars": MIN_TEXT_CHARS,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=120,
                        help="Max bills to process from the PRS list (default 120).")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds to wait between detail-page fetches (default 1.0).")
    parser.add_argument("--refresh", action="store_true",
                        help="Re-fetch content even for bills that already have it.")
    parser.add_argument("--stats", action="store_true",
                        help="Only report DB readiness, then exit.")
    args = parser.parse_args()

    app = build_app()
    if args.stats:
        for k, v in show_stats(app).items():
            print(f"  {k}: {v}")
        return 0

    logger.info("Seeding up to %d bills (delay=%.1fs).", args.limit, args.delay)
    stats = seed_bills(app, limit=args.limit, delay=args.delay, refresh=args.refresh)
    print("\n===== SEED SUMMARY =====")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("=========================")

    if stats.get("usable_bills_for_ft", 0) >= 100:
        print("\n✅ DB is ready for dataset generation:")
        print("   cd backend/scripts/ml_pipeline && python 1_generate_dataset.py --num-samples 120")
    else:
        print("\n⚠️  Fewer than 100 usable bills. Increase --limit and re-run, or")
        print("   check PRS availability. Use `--stats` to re-check readiness.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())