"""
Clear and reset database to start fresh
Removes all data and recreates tables
"""
import os
import sys

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from models import db

def clear_database():
    """Clear all database files and recreate"""
    app = create_app()
    
    with app.app_context():
        print("🗑️  Dropping all tables...")
        db.drop_all()
        
        print("📦 Creating fresh tables...")
        db.create_all()
        
        print("✅ Database reset complete!")
        print("   - All bills cleared")
        print("   - All content cleared")
        print("   - All summaries cleared")
        print("   - All users cleared")
        print("   - All subscriptions cleared")
        print("\n🎯 Database is now empty and ready for fresh indexing!")

if __name__ == '__main__':
    confirm = input("⚠️  This will DELETE ALL DATA in the database. Continue? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_database()
    else:
        print("❌ Cancelled")
