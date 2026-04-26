"""Clear ALL cached content and summaries from database"""
from app import create_app
from models import db, BillContent, BillSummary

app = create_app()

with app.app_context():
    # Count existing records
    content_count = BillContent.query.count()
    summary_count = BillSummary.query.count()
    
    print(f"Found in database:")
    print(f"  - {content_count} cached bill contents")
    print(f"  - {summary_count} cached summaries")
    
    if content_count == 0 and summary_count == 0:
        print("\n✅ Database already clean!")
    else:
        print(f"\nClearing all cached data...")
        
        # Delete all cached content
        if content_count > 0:
            BillContent.query.delete()
            print(f"✅ Deleted {content_count} cached bill contents")
        
        # Delete all cached summaries
        if summary_count > 0:
            BillSummary.query.delete()
            print(f"✅ Deleted {summary_count} cached summaries")
        
        db.session.commit()
        print(f"\n✅ All cached data cleared!")
        print(f"Bills will be re-scraped with updated code when clicked in frontend.")
