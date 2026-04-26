"""Check ministry status in database"""
from app import create_app
from models import db, Bill

app = create_app()

with app.app_context():
    total_bills = Bill.query.count()
    unknown_ministry = Bill.query.filter(
        (Bill.ministry == 'Unknown') | (Bill.ministry == None)
    ).count()
    
    print(f"📊 Total bills: {total_bills}")
    print(f"❌ Bills with Unknown/None ministry: {unknown_ministry}")
    print(f"✅ Bills with ministry: {total_bills - unknown_ministry}")
    
    # Show sample bills with Unknown ministry
    print("\n🔍 Sample bills with Unknown ministry:")
    unknown_bills = Bill.query.filter(
        (Bill.ministry == 'Unknown') | (Bill.ministry == None)
    ).limit(5).all()
    
    for bill in unknown_bills:
        print(f"  - {bill.title[:70]}")
        print(f"    URL: {bill.url}")
        print(f"    Ministry: {bill.ministry}")
        print()
    
    # Show sample bills WITH ministry
    print("\n✅ Sample bills WITH ministry:")
    known_bills = Bill.query.filter(
        (Bill.ministry != 'Unknown') & (Bill.ministry != None)
    ).limit(5).all()
    
    for bill in known_bills:
        print(f"  - {bill.title[:70]}")
        print(f"    Ministry: {bill.ministry}")
        print()
