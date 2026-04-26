"""
Database Initialization Script
Creates empty database with all tables
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, Bill, BillContent, SearchHistory

def init_database():
    """Initialize empty database"""
    
    # Create Flask app
    app = Flask(__name__)
    
    # Database configuration
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'regulation_alert.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        # Drop all tables (fresh start)
        print("🗑️  Dropping existing tables...")
        db.drop_all()
        
        # Create all tables
        print("📦 Creating tables...")
        db.create_all()
        
        # Verify tables created
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        
        print(f"\n✅ Database initialized successfully!")
        print(f"📍 Location: {db_path}")
        print(f"📊 Tables created: {', '.join(tables)}")
        print(f"\n💡 Database is empty - will populate on-demand when users search!")
        
        return app

if __name__ == '__main__':
    init_database()
