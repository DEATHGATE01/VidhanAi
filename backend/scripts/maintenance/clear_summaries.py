from app import create_app, db
from models import BillSummary

app = create_app()
with app.app_context():
    deleted = BillSummary.query.delete()
    db.session.commit()
    print(f'✅ Cleared {deleted} old summaries - ready for improved format!')
