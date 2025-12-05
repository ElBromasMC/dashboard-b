import sqlite3
from flask import g, current_app


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    from models.user import User
    from models.project import ProjectRecord
    from models.component import Component
    from models.conformity import ConformityRecord
    from models.repotentiation import RepotentiationRecord
    from models.destruction import DiskDestruction

    db = get_db()

    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            role TEXT NOT NULL DEFAULT 'standard'
        );
        """
    )

    User.ensure_role_column(db)
    ProjectRecord.ensure_schema(db)
    Component.ensure_tables(db)
    ConformityRecord.ensure_table(db)
    RepotentiationRecord.ensure_table(db)
    DiskDestruction.ensure_table(db)
    User.ensure_initial_admin(db)
