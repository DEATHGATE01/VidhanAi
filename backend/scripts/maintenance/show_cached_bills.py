from app import create_app, db
from models import Bill, BillContent

app = create_app()
with app.app_context():
    bills_with_content = [b for b in Bill.query.all() if b.content]
    
    print(f'\n✅ Bills with FULL CONTENT cached: {len(bills_with_content)}')
    print('=' * 70)
    
    for bill in bills_with_content:
        print(f'\n📄 {bill.title}')
        print(f'   Content fetched: {bill.content.fetched_at}')
        print(f'   Sections: {len(bill.content.sections) if bill.content.sections else 0}')
        print(f'   Paragraphs: {len(bill.content.paragraphs) if bill.content.paragraphs else 0}')
        print(f'   Full text length: {len(bill.content.full_text) if bill.content.full_text else 0} chars')
    
    print(f'\n📊 Bills WITHOUT content (will scrape on first view): {Bill.query.count() - len(bills_with_content)}')
