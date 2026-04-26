"""Prefetch ministries for bills whose ministry is Unknown.

This script performs a lightweight page fetch per bill and updates the
Bill.ministry and Bill.introduction_date fields without fetching full bill content.
"""
import time
import sys
import os

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from app import create_app
from models import db, Bill
from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper

BATCH_SIZE = 50
SLEEP_BETWEEN_REQUESTS = 0.2  # seconds


def run():
    app = create_app()
    scraper = PRSBillTrackScraper()

    with app.app_context():
        query = Bill.query.filter((Bill.ministry == None) | (Bill.ministry == '') | (Bill.ministry == 'Unknown'))
        bills = query.all()
        total = len(bills)
        print(f"🔎 Found {total} bills with unknown ministry")

        updated = 0
        errors = 0

        for idx, bill in enumerate(bills, start=1):
            try:
                result = scraper.fetch_ministry_and_date(bill.url)
                ministry = result.get('ministry')
                intro_date = result.get('introduction_date')

                if ministry and ministry != 'Unknown' and ministry != bill.ministry:
                    bill.ministry = ministry
                if intro_date:
                    bill.introduction_date = intro_date

                db.session.add(bill)

                # Commit in batches
                if idx % BATCH_SIZE == 0:
                    db.session.commit()
                    print(f"  ✅ Committed {idx} / {total}")

                updated += 1
            except Exception as e:
                print(f"⚠️ Error updating bill {bill.bill_id}: {e}")
                errors += 1
            finally:
                time.sleep(SLEEP_BETWEEN_REQUESTS)

        # Final commit
        try:
            db.session.commit()
        except Exception as e:
            print(f"⚠️ Error committing final changes: {e}")

        print("\n🏁 Done")
        print(f"Total processed: {total}")
        print(f"Updated attempts: {updated}")
        print(f"Errors: {errors}")


if __name__ == '__main__':
    run()
