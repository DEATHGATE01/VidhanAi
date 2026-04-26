"""Add introduction_date column to bills table"""
from app import create_app
from models import db
from sqlalchemy import text

app = create_app()

with app.app_context():
    try:
        # Add the introduction_date column
        print("Adding introduction_date column to bills table...")
        db.session.execute(text('ALTER TABLE bills ADD COLUMN introduction_date DATETIME'))
        db.session.commit()
        print("✅ Column added successfully!")
    except Exception as e:
        print(f"Error: {e}")
        print("ℹ️ Column might already exist or there's another issue")
