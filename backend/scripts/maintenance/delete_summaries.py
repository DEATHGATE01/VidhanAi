from app import create_app, db
from models import BillSummary

app = create_app()
with app.app_context():
    # Delete all summaries to force regeneration
    count = BillSummary.query.delete()
    db.session.commit()
    print(f'✅ Deleted {count} summaries - they will regenerate with new format!')
