import sqlite3
import hashlib
import secrets
from typing import Tuple, Optional
from flask import current_app


class User:
    def __init__(self, id: int, username: str, role: str):
        self.id = id
        self.username = username
        self.role = role

    @staticmethod
    def hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000
        )
        return f"{salt}${hashed.hex()}"

    @staticmethod
    def verify_password(stored: str, password: str) -> bool:
        try:
            salt, hashed_hex = stored.split("$")
        except ValueError:
            return False
        new_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000
        )
        return secrets.compare_digest(hashed_hex, new_hash.hex())

    @staticmethod
    def ensure_role_column(db: sqlite3.Connection) -> None:
        columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
        if "role" not in columns:
            db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'standard'")
            db.commit()

    @staticmethod
    def ensure_initial_admin(db: sqlite3.Connection) -> None:
        password = current_app.config.get("INITIAL_ADMIN_PASSWORD")
        if not password:
            current_app.logger.warning(
                "BANBIF_ADMIN_CODE no esta definido; no se creo el administrador inicial."
            )
            return
        existing = db.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone()
        if existing:
            return
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            ("admin", User.hash_password(password), "admin"),
        )
        db.commit()
        current_app.logger.info("Usuario administrador inicial 'admin' creado.")

    @staticmethod
    def get_by_id(db: sqlite3.Connection, user_id: int) -> Optional['User']:
        row = db.execute(
            "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if row:
            return User(id=row["id"], username=row["username"], role=row["role"])
        return None

    @staticmethod
    def get_by_username(db: sqlite3.Connection, username: str) -> Optional[dict]:
        return db.execute(
            "SELECT id, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()

    @staticmethod
    def create(
        db: sqlite3.Connection, username: str, password: str, confirm: str, role: str
    ) -> Tuple[bool, str]:
        username = (username or "").strip()
        role = (role or "standard").strip()
        if not username:
            return False, "El usuario es obligatorio"
        if not password:
            return False, "La contrasena es obligatoria"
        if password != confirm:
            return False, "Las contrasenas no coinciden"
        if len(password) < 8:
            return False, "La contrasena debe tener al menos 8 caracteres"
        if role not in {"standard", "admin"}:
            return False, "Rol invalido"

        try:
            db.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                (username, User.hash_password(password), role),
            )
            db.commit()
        except sqlite3.IntegrityError:
            return False, "Este usuario ya existe"
        return True, ""
