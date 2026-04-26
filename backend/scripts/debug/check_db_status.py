from app import create_app, db
from models import Bill, BillContent, BillSummary, User, UserReadingHistory

app = create_app()
with app.app_context():
    print('\n📊 DATABASE STATUS')
    print('=' * 50)
    print(f'Bills: {Bill.query.count()}')
    print(f'Bill Contents: {BillContent.query.count()}')
    print(f'Bill Summaries: {BillSummary.query.count()}')
    print(f'Users: {User.query.count()}')
    print(f'Reading History: {UserReadingHistory.query.count()}')
    
    print('\n🔍 SUMMARIES DETAILS:')
    print('=' * 50)
    summaries = BillSummary.query.all()
    if summaries:
        for s in summaries:
            bill = Bill.query.get(s.bill_id)
            print(f'\nBill ID: {s.bill_id}')
            print(f'  Title: {bill.title if bill else "Unknown"}')
            print(f'  Type: {s.summary_type}')
            print(f'  Confidence: {s.confidence}')
            print(f'  Generated: {s.generated_at}')
            print(f'  Model: {s.model_version}')
            if s.summary:
                word_count = len(s.summary.split())
                print(f'  Words: {word_count}')
                print(f'\n  📝 SUMMARY PREVIEW:')
                print('  ' + '-' * 45)
                lines = s.summary.split('\n')[:20]  # First 20 lines
                for line in lines:
                    print(f'  {line}')
                if len(s.summary.split('\n')) > 20:
                    print(f'  ... ({len(s.summary.split("\n")) - 20} more lines)')
    else:
        print('No summaries in database')
    
    print('\n' + '=' * 50)
