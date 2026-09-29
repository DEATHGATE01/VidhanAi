"""Idempotent migration: create the Acts tracking tables (P0 data spine).

Run once:  python scripts/maintenance/migrate_acts_tables.py

The ORM models (Act, BillActLink, LifecycleEvent in models.py) cover fresh
databases via db.create_all(); this script additively creates just the three
new tables on existing SQLite files. Never drops data: if a table already
exists it is left untouched.
"""
import os
import sys

# Make backend/ importable (same pattern as scripts/setup/sync_acts.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from models import db, Act, BillActLink, LifecycleEvent  # noqa: F401 - imports register the tables

NEW_TABLES = ('acts', 'bill_act_links', 'lifecycle_events')


def main():
    app = create_app()
    with app.app_context():
        engine = db.engine
        existing = set(engine.dialect.get_table_names(engine.connect()))

        missing = [t for t in NEW_TABLES if t not in existing]
        if not missing:
            print(f"[ok] all Acts tables already exist: {', '.join(NEW_TABLES)}")
            return 0

        # db.create_all() is additive: it creates only tables that do not
        # exist yet and never touches existing rows.
        db.create_all()

        existing_after = set(engine.dialect.get_table_names(engine.connect()))
        created = [t for t in NEW_TABLES if t in existing_after and t not in existing]
        if created:
            print(f"[ok] created Acts tables: {', '.join(created)}")
        else:
            print("[warn] no tables were created (unexpected)")
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
