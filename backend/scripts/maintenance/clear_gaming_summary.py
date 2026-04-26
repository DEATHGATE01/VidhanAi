"""Clear AI summary for gaming bill to force regeneration"""
from app import create_app
from models import db, Bill, BillSummary

app = create_app()

with app.app_context():
    # Find the gaming bill
    gaming_bill = Bill.query.filter(Bill.title.like('%gaming%')).first()
    
    if gaming_bill:
        print(f"Found gaming bill: {gaming_bill.title} (ID: {gaming_bill.id})")
        print(f"Ministry: {gaming_bill.ministry}")
        print(f"Introduction date: {gaming_bill.introduction_date}")
        
        # Delete cached summary
        cached_summary = BillSummary.query.filter_by(bill_id=gaming_bill.id).first()
        if cached_summary:
            print(f"\nDeleting cached AI summary (generated {cached_summary.generated_at})...")
            db.session.delete(cached_summary)
            db.session.commit()
            print("✅ Cached summary deleted. Generate new summary in frontend.")
        else:
            print("ℹ️ No cached summary found for this bill.")
    else:
        print("❌ Gaming bill not found in database")
