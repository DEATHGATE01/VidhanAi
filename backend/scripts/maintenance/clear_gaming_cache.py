"""Clear cached content for gaming bill to force re-scrape"""
from app import create_app
from models import db, Bill, BillContent

app = create_app()

with app.app_context():
    # Find the gaming bill
    gaming_bill = Bill.query.filter(Bill.title.like('%gaming%')).first()
    
    if gaming_bill:
        print(f"Found gaming bill: {gaming_bill.title} (ID: {gaming_bill.id})")
        print(f"Current ministry: {gaming_bill.ministry}")
        print(f"Current date: {gaming_bill.introduction_date}")
        
        # Delete cached content
        cached_content = BillContent.query.filter_by(bill_id=gaming_bill.id).first()
        if cached_content:
            print(f"\nDeleting cached content (full_text: {len(cached_content.full_text or '')} chars)...")
            db.session.delete(cached_content)
            db.session.commit()
            print("✅ Cached content deleted. Click the bill in frontend to re-scrape.")
        else:
            print("ℹ️ No cached content found for this bill.")
    else:
        print("❌ Gaming bill not found in database")
