"""
Comprehensive Bill Data Fetcher
=================================
Pre-fetches ALL bill data (content, ministry, dates) and stores in database.
Run this script to populate the database with complete bill information.

Usage:
    python fetch_all_bill_data.py
    python fetch_all_bill_data.py --batch-size 50 --delay 0.5
"""

import sys
import os
import time
import argparse
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db, Bill
from src.scraping.prs_billtrack_scraper import PRSBillTrackScraper

def fetch_all_bill_data(batch_size=50, delay=0.5, update_existing=False):
    """
    Fetch complete data for all bills in database.
    
    Args:
        batch_size: Number of bills to process before committing
        delay: Delay in seconds between requests (to avoid overloading server)
        update_existing: If True, re-fetch data even for bills with content
    """
    from models import BillContent
    
    app = create_app()
    scraper = PRSBillTrackScraper()
    
    with app.app_context():
        # Query bills that need data fetching
        if update_existing:
            bills_to_fetch = Bill.query.all()
            print(f"🔄 Fetching data for ALL {len(bills_to_fetch)} bills (update mode)")
        else:
            # Get bills without content or missing ministry/dates
            bills_to_fetch = Bill.query.outerjoin(BillContent).filter(
                (BillContent.id == None) |
                (Bill.ministry == None) | (Bill.ministry == '') | (Bill.ministry == 'Unknown') |
                (Bill.introduction_date == None)
            ).all()
            print(f"📥 Found {len(bills_to_fetch)} bills needing data fetch")
        
        if not bills_to_fetch:
            print("✅ All bills already have complete data!")
            return
        
        print(f"⚙️  Settings: batch_size={batch_size}, delay={delay}s")
        print("="*70)
        
        total_processed = 0
        total_updated = 0
        total_errors = 0
        start_time = time.time()
        
        for i, bill in enumerate(bills_to_fetch, 1):
            try:
                print(f"\n[{i}/{len(bills_to_fetch)}] Processing: {bill.title[:60]}...")
                
                # Fetch complete bill data
                bill_data = scraper.fetch_bill_details(bill.url)
                
                if bill_data:
                    # Update bill fields
                    updated = False
                    
                    if bill_data.get('ministry') and bill_data['ministry'] != 'Unknown':
                        if not bill.ministry or bill.ministry == 'Unknown':
                            bill.ministry = bill_data['ministry']
                            print(f"   ✅ Ministry: {bill_data['ministry']}")
                            updated = True
                    
                    if bill_data.get('introduction_date'):
                        if not bill.introduction_date:
                            bill.introduction_date = bill_data['introduction_date']
                            print(f"   ✅ Date: {bill_data['introduction_date']}")
                            updated = True
                    
                    if bill_data.get('content'):
                        # Check if BillContent exists
                        bill_content = BillContent.query.filter_by(bill_id=bill.id).first()
                        if not bill_content or update_existing:
                            if not bill_content:
                                bill_content = BillContent(bill_id=bill.id)
                                db.session.add(bill_content)
                            
                            bill_content.full_text = bill_data['content']
                            content_len = len(bill_data['content'])
                            print(f"   ✅ Content: {content_len} characters")
                            updated = True
                    
                    if bill_data.get('pdf_url'):
                        bill_content = BillContent.query.filter_by(bill_id=bill.id).first()
                        if not bill_content:
                            bill_content = BillContent(bill_id=bill.id)
                            db.session.add(bill_content)
                        
                        if not bill_content.pdf_link:
                            bill_content.pdf_link = bill_data['pdf_url']
                            print(f"   ✅ PDF URL: {bill_data['pdf_url'][:50]}...")
                            updated = True
                    
                    if updated:
                        total_updated += 1
                        print(f"   💾 Updated bill data")
                    else:
                        print(f"   ℹ️  No new data to update")
                
                else:
                    print(f"   ⚠️  Could not fetch data (might be unavailable on PRS)")
                
                total_processed += 1
                
                # Commit in batches
                if i % batch_size == 0:
                    db.session.commit()
                    elapsed = time.time() - start_time
                    rate = total_processed / elapsed if elapsed > 0 else 0
                    print(f"\n{'='*70}")
                    print(f"💾 Batch commit: {i}/{len(bills_to_fetch)} bills processed")
                    print(f"📊 Updated: {total_updated} | Errors: {total_errors}")
                    print(f"⏱️  Rate: {rate:.2f} bills/sec | Elapsed: {elapsed:.1f}s")
                    print(f"{'='*70}")
                
                # Throttle requests
                time.sleep(delay)
                
            except Exception as e:
                total_errors += 1
                print(f"   ❌ Error: {str(e)}")
                continue
        
        # Final commit
        db.session.commit()
        
        # Summary
        elapsed = time.time() - start_time
        print("\n" + "="*70)
        print("🏁 DATA FETCH COMPLETE!")
        print("="*70)
        print(f"📊 Statistics:")
        print(f"   • Total processed: {total_processed}")
        print(f"   • Successfully updated: {total_updated}")
        print(f"   • Errors: {total_errors}")
        print(f"   • Time elapsed: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
        print(f"   • Average rate: {total_processed/elapsed:.2f} bills/sec")
        print("="*70)

def show_database_stats():
    """Display current database statistics."""
    from models import BillContent
    
    app = create_app()
    
    with app.app_context():
        total_bills = Bill.query.count()
        
        # Count bills with content (has relationship to BillContent)
        bills_with_content = db.session.query(Bill).join(BillContent).count()
        
        bills_with_ministry = Bill.query.filter(
            Bill.ministry != None, 
            Bill.ministry != '', 
            Bill.ministry != 'Unknown'
        ).count()
        bills_with_dates = Bill.query.filter(Bill.introduction_date != None).count()
        
        print("\n" + "="*70)
        print("📊 DATABASE STATISTICS")
        print("="*70)
        print(f"Total Bills: {total_bills}")
        print(f"Bills with Content: {bills_with_content} ({bills_with_content/total_bills*100:.1f}%)")
        print(f"Bills with Known Ministry: {bills_with_ministry} ({bills_with_ministry/total_bills*100:.1f}%)")
        print(f"Bills with Introduction Date: {bills_with_dates} ({bills_with_dates/total_bills*100:.1f}%)")
        
        completeness = (bills_with_content + bills_with_ministry + bills_with_dates) / (total_bills * 3) * 100
        print(f"\n📈 Overall Data Completeness: {completeness:.1f}%")
        print("="*70 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch complete data for all bills')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for commits (default: 50)')
    parser.add_argument('--delay', type=float, default=0.5, help='Delay between requests in seconds (default: 0.5)')
    parser.add_argument('--update-existing', action='store_true', help='Re-fetch data for bills that already have content')
    parser.add_argument('--stats', action='store_true', help='Show database statistics only')
    
    args = parser.parse_args()
    
    if args.stats:
        show_database_stats()
    else:
        print("\n" + "="*70)
        print("🚀 COMPREHENSIVE BILL DATA FETCHER")
        print("="*70)
        print(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        fetch_all_bill_data(
            batch_size=args.batch_size,
            delay=args.delay,
            update_existing=args.update_existing
        )
        
        # Show final stats
        show_database_stats()
