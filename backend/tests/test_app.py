"""Basic import and smoke tests for VidhanAI backend."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_app_creation():
    """Test that Flask app can be created without errors."""
    from app import create_app
    app = create_app()
    assert app is not None
    # App should be created successfully (TESTING config may be False by default)
    assert hasattr(app, 'config')

def test_imports():
    """Test that all core modules can be imported."""
    # Core modules
    import models
    import db_service
    import ai_service
    import routes
    import config
    import scheduler
    assert True

def test_agents_import():
    """Test that agent modules can be imported."""
    from agents import run_research, get_tool_inventory
    from agents import orchestrator
    assert True
