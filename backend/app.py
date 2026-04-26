"""
Flask Application for Regulation Alert System
Main app with CORS, database, and API routes
"""
from flask import Flask
from flask_cors import CORS
from models import db
from routes import api
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def create_app():
    """Create and configure Flask application"""
    
    app = Flask(__name__)
    
    # Configuration
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'regulation_alert.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JSON_SORT_KEYS'] = False
    
    # Secret key for sessions (change in production!)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)  # Enable CORS for frontend
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    return app


if __name__ == '__main__':
    app = create_app()
    print("🚀 Starting Regulation Alert System API...")
    print("📍 Database: backend/instance/regulation_alert.db")
    print("🌐 API available at: http://127.0.0.1:5000/api/")
    print("📊 Endpoints:")
    print("   - GET  /api/health")
    print("   - GET  /api/search?keyword=<keyword>")
    print("   - GET  /api/bills/<bill_id>")
    print("   - GET  /api/bills")
    print("   - POST /api/users/register")
    print("   - GET  /api/users/<user_id>")
    print("   - GET  /api/users/<user_id>/analytics")
    print("   - GET  /api/users/<user_id>/favorites")
    print("   - POST /api/users/<user_id>/favorites")
    print("   - GET  /api/users/<user_id>/history")
    print("   - GET  /api/analytics/trending")
    print("   - GET  /api/analytics/ministry")
    print("   - GET  /api/analytics/heatmap")
    print("   - GET  /api/analytics/stats")
    print("\n✅ Server ready! Press Ctrl+C to stop.")
    print("🔄 Auto-reload enabled - server will restart on code changes\n")
    
    # Enable auto-reload for development
    app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)
