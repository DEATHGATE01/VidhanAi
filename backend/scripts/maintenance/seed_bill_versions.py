"""
Seed BillVersion entries for demo amendment diffs.
Creates v1 (draft/earlier) and v2 (passed/later) versions for bill pairs.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from models import db, Bill, BillContent, BillVersion

# Bill pairs for amendment diff demos (v1 -> v2)
# (bill_id_v1, bill_id_v2, v1_change_type, v2_change_type)
DEMO_PAIRS = [
    # Data Protection: 2022 Draft -> 2023 Passed
    ("draft-the-digital-personal-data-protection-bill-2022",
     "digital-personal-data-protection-bill-2023",
     "introduced", "passed"),

    # Telecom: 2022 Draft -> 2023 Passed
    ("draft-indian-telecommunication-bill-2022",
     "the-telecommunication-bill-2023",
     "introduced", "passed"),

    # Jan Vishwas: 2022 -> 2026 (multiple amendments)
    ("the-jan-vishwas-amendment-of-provisions-bill-2022",
     "the-jan-vishwas-amendment-of-provisions-bill-2026",
     "amended", "passed"),

    # Criminal Law Reform: Withdrawn 2023 -> Second 2023 (Passed)
    ("the-bharatiya-nyaya-sanhita-2023",
     "the-bharatiya-nyaya-second-sanhita-2023",
     "withdrawn", "passed"),

    ("the-bharatiya-nagarik-suraksha-sanhita-2023",
     "the-bharatiya-nagarik-suraksha-second-sanhita-2023",
     "withdrawn", "passed"),

    ("the-bharatiya-sakshya-bill-2023",
     "the-bharatiya-sakshya-second-bill-2023",
     "withdrawn", "passed"),

    # Central Universities: 2022 -> 2023
    ("the-central-universities-amendment-bill-2022",
     "the-central-universities-amendment-bill-2023",
     "amended", "passed"),
]


def seed_bill_versions():
    app = create_app()
    with app.app_context():
        created = 0
        skipped = 0

        for bill_id_v1, bill_id_v2, v1_type, v2_type in DEMO_PAIRS:
            # Find both bills
            b1 = Bill.query.filter_by(bill_id=bill_id_v1).first()
            b2 = Bill.query.filter_by(bill_id=bill_id_v2).first()

            if not b1 or not b2:
                print(f"SKIP: Bills not found - {bill_id_v1} or {bill_id_v2}")
                skipped += 1
                continue

            if not b1.content or not b1.content.full_text or not b2.content or not b2.content.full_text:
                print(f"SKIP: Missing content - {bill_id_v1} or {bill_id_v2}")
                skipped += 1
                continue

            # Check if versions already exist
            existing_v1 = BillVersion.query.filter_by(bill_id=b1.id, version_number=1).first()
            existing_v2 = BillVersion.query.filter_by(bill_id=b2.id, version_number=2).first()

            if existing_v1 and existing_v2:
                print(f"EXISTS: {b1.title[:50]}... v1 & v2 already seeded")
                skipped += 1
                continue

            # Create v1
            v1 = BillVersion(
                bill_id=b1.id,
                version_number=1,
                version_date=b1.introduction_date or datetime.utcnow(),
                change_type=v1_type,
                title=b1.title,
                status=b1.status,
                full_text=b1.content.full_text,
                sections=b1.content.sections,
                changes_summary=f"Initial version ({v1_type})"
            )

            # Create v2
            v2 = BillVersion(
                bill_id=b2.id,
                version_number=2,
                version_date=b2.introduction_date or datetime.utcnow(),
                change_type=v2_type,
                title=b2.title,
                status=b2.status,
                full_text=b2.content.full_text,
                sections=b2.content.sections,
                changes_summary=f"Amended version ({v2_type})"
            )

            db.session.add(v1)
            db.session.add(v2)
            created += 2
            print(f"CREATED: {b1.title[:50]}... v1({v1_type}) -> v2({v2_type})")

        db.session.commit()
        print(f"\n=== SEED COMPLETE ===")
        print(f"Created: {created} BillVersion entries")
        print(f"Skipped: {skipped} pairs")


def show_existing_versions():
    app = create_app()
    with app.app_context():
        versions = BillVersion.query.order_by(BillVersion.bill_id, BillVersion.version_number).all()
        if not versions:
            print("No BillVersion entries exist yet.")
            return

        print(f"Existing BillVersion entries: {len(versions)}")
        current_bill = None
        for v in versions:
            bill = Bill.query.get(v.bill_id)
            if bill:
                if current_bill != bill.title:
                    current_bill = bill.title
                    print(f"\n  Bill: {bill.title[:60]}...")
                print(f"    v{v.version_number} ({v.change_type}): {len(v.full_text or '')} chars, date={v.version_date}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Seed BillVersion demo data")
    parser.add_argument("--show", action="store_true", help="Show existing versions only")
    args = parser.parse_args()

    if args.show:
        show_existing_versions()
    else:
        seed_bill_versions()
        show_existing_versions()