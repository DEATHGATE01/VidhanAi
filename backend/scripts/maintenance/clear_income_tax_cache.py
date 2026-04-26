"""Check and clear cached content for Income Tax Bill"""
from app import create_app
from models import db, Bill, BillContent, BillSummary

app = create_app()

with app.app_context():
    # Find the Income Tax bill
    tax_bill = Bill.query.filter(Bill.title.like('%Income-Tax%No.2%')).first()
    
    if tax_bill:
        print(f"Found bill: {tax_bill.title} (ID: {tax_bill.id})")
        print(f"Current ministry: {tax_bill.ministry}")
        print(f"Current introduction_date: {tax_bill.introduction_date}")
        print(f"URL: {tax_bill.url}")
        
        # Delete cached content
        cached_content = BillContent.query.filter_by(bill_id=tax_bill.id).first()
        if cached_content:
            print(f"\n✅ Found cached content (full_text: {len(cached_content.full_text or '')} chars)")
            print("Deleting cached content...")
            db.session.delete(cached_content)
        else:
            print("\nℹ️ No cached content found")
        
        # Delete cached summary
        cached_summary = BillSummary.query.filter_by(bill_id=tax_bill.id).first()
        if cached_summary:
            print(f"✅ Found cached summary (generated {cached_summary.generated_at})")
            print("Deleting cached summary...")
            db.session.delete(cached_summary)
        else:
            print("ℹ️ No cached summary found")
        
        db.session.commit()
        print("\n✅ Cache cleared! Click the bill in frontend to re-scrape with new code.")
    else:
        print("❌ Income Tax Bill not found in database")
        print("\nSearching for similar bills:")
        similar = Bill.query.filter(Bill.title.like('%tax%')).all()
        for bill in similar[:5]:
            print(f"  - {bill.title}")
