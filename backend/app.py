"""
VidhanAI Flask application factory.

Run with:  python app.py   (from the backend/ directory)
Gunicorn:  gunicorn -w 4 -b 0.0.0.0:5000 app:create_app()

The factory pattern (``create_app``) is required because several setup scripts
already do ``from app import create_app`` (e.g. fetch_all_bill_data.py), so
this module's public contract is the ``create_app`` callable.

Configuration precedence (later wins):
    1. baked-in defaults below
    2. backend/config.py  (if it ever gets populated - currently empty)
    3. environment variables
    4. backend/.env  (loaded by python-dotenv if present)
"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

# Load backend/.env (GROQ_API_KEY, SECRET_KEY, DATABASE_URI, ...) if present.
# The pipeline scripts and the Flask app rely on these; silently skipping the
# load means the Groq summarizer never gets a key and silently degrades.
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - python-dotenv is in requirements
    load_dotenv = None

_BACKEND_ENV = Path(__file__).resolve().parent / ".env"
if load_dotenv is not None and _BACKEND_ENV.exists():
    load_dotenv(_BACKEND_ENV)

try:
    import models
    from models import db
except ImportError:  # pragma: no cover - only matters if cwd is wrong
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import models  # type: ignore
    from models import db  # type: ignore


BACKEND_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = BACKEND_DIR / "instance" / "regulation_alert.db"


def create_app(config_overrides: dict | None = None) -> Flask:
    """Create and configure the VidhanAI Flask application."""
    app = Flask(__name__)

    # ------------------------------------------------------------------ #
    # Configuration
    # ------------------------------------------------------------------ #
    db_path = os.environ.get("VIDHANAI_DB_PATH", str(DEFAULT_DB_PATH))
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URI", f"sqlite:///{db_path}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
            "pool_recycle": 3600,
            "pool_timeout": 30,
        },
        SECRET_KEY=os.environ.get("SECRET_KEY", "vidhanai-dev-secret-change-me"),
        JSON_SORT_KEYS=False,
        JSONIFY_PRETTYPRINT_REGULAR=False,
    )

    if config_overrides:
        app.config.update(config_overrides)

    # ------------------------------------------------------------------ #
    # Security: Request size limits to prevent DoS
    # ------------------------------------------------------------------ #
    app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB max request body

    @app.before_request
    def limit_request_size():
        """Enforce request size limits on all endpoints."""
        if request.content_length and request.content_length > app.config['MAX_CONTENT_LENGTH']:
            return jsonify({
                "error": f"Request body too large. Maximum size: {app.config['MAX_CONTENT_LENGTH'] // (1024*1024)} MB"
            }), 413

    # ------------------------------------------------------------------ #
    # Extensions
    # ------------------------------------------------------------------ #
    db.init_app(app)

    # CORS so the Vite dev server (localhost:5173/3000) can call the API.
    cors_origins = os.environ.get(
        "VIDHANAI_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173",
    )
    CORS(app, resources={r"/api/*": {"origins": cors_origins.split(",")}},
         supports_credentials=True)

    # ------------------------------------------------------------------ #
    # Blueprint + routes
    # ------------------------------------------------------------------ #
    from routes import api  # noqa: WPS433 - late import to avoid circulars

    app.register_blueprint(api, url_prefix="/api")

    # Convenience health route at the root.
    @app.get("/")
    def index_root():
        return jsonify({
            "service": "VidhanAI",
            "status": "running",
            "api_root": "/api",
            "docs": "GET /api/health",
        })

    @app.get("/health")
    def root_health():
        return jsonify({"status": "healthy"}), 200

    # ------------------------------------------------------------------ #
    # Auto-create tables on first run if the DB file is missing.
    # ------------------------------------------------------------------ #
    with app.app_context():
        # Importing the models module registers every model class with
        # SQLAlchemy's metadata so db.create_all() will see all 11 tables.
        import models as _models  # noqa: F401
        if not Path(db_path).exists():
            print(f"[app] Database not found at {db_path}; creating schema.")
            db.create_all()
        else:
            # Ensure the schema exists even if the file is empty, but don't
            # wipe existing data - create_all() is idempotent.
            db.create_all()

        # Enable SQLite WAL mode and foreign keys for better concurrency and integrity
        if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
            with db.engine.connect() as conn:
                conn.execute(db.text("PRAGMA journal_mode=WAL;"))
                conn.execute(db.text("PRAGMA foreign_keys=ON;"))
                conn.execute(db.text("PRAGMA synchronous=NORMAL;"))
                conn.execute(db.text("PRAGMA cache_size=-32768;"))  # 32MB cache
                conn.commit()

    # ------------------------------------------------------------------ #
    # Error handlers
    # ------------------------------------------------------------------ #
    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"success": False, "error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):  # pragma: no cover - defensive
        # Avoid leaking internal tracebacks; Flask logs them already.
        return jsonify({"success": False, "error": "Internal server error"}), 500

    print(f"[app] VidhanAI backend ready. DB: {db_path}")
    print(f"[app] CORS origins: {cors_origins}")
    return app


# Exposed for ``python app.py`` and ``gunicorn app:create_app``.
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV") == "development"
    print(f"[app] Starting VidhanAI on http://127.0.0.1:{port} (debug={debug})")
    app.run(host="0.0.0.0", port=port, debug=debug)
