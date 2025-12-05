import sqlite3
import os
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from config import BASE_DIR

# Directorio para almacenar archivos
UPLOADS_DIR = BASE_DIR / "uploads" / "actas"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'msg'}


class ConformityRecord:
    """Modelo para Actas de Conformidad"""

    @staticmethod
    def ensure_table(db: sqlite3.Connection) -> None:
        """Crea la tabla de actas de conformidad si no existe"""
        db.execute("""
            CREATE TABLE IF NOT EXISTS conformity_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipo_serial TEXT NOT NULL,
                equipo_hostname TEXT,
                usuario_nombre TEXT,
                tipo_archivo TEXT NOT NULL,
                nombre_archivo TEXT NOT NULL,
                ruta_archivo TEXT NOT NULL,
                fecha_subida TEXT DEFAULT CURRENT_TIMESTAMP,
                subido_por TEXT,
                notas TEXT,
                FOREIGN KEY (equipo_serial) REFERENCES project_records(serial_num)
            )
        """)
        db.commit()

    @staticmethod
    def get_all(db: sqlite3.Connection, equipo_serial: str = None) -> List[sqlite3.Row]:
        query = """
            SELECT cr.*, pr.nombre_completo, pr.hostname
            FROM conformity_records cr
            LEFT JOIN project_records pr ON cr.equipo_serial = pr.serial_num
        """
        params = []
        if equipo_serial:
            query += " WHERE cr.equipo_serial = ?"
            params.append(equipo_serial)
        query += " ORDER BY cr.fecha_subida DESC"
        return db.execute(query, params).fetchall()

    @staticmethod
    def get_by_id(db: sqlite3.Connection, id: int) -> Optional[sqlite3.Row]:
        return db.execute("""
            SELECT cr.*, pr.nombre_completo, pr.hostname
            FROM conformity_records cr
            LEFT JOIN project_records pr ON cr.equipo_serial = pr.serial_num
            WHERE cr.id = ?
        """, (id,)).fetchone()

    @staticmethod
    def get_by_equipment(db: sqlite3.Connection, equipo_serial: str) -> List[sqlite3.Row]:
        return db.execute("""
            SELECT * FROM conformity_records
            WHERE equipo_serial = ?
            ORDER BY fecha_subida DESC
        """, (equipo_serial,)).fetchall()

    @staticmethod
    def create(db: sqlite3.Connection, data: Dict) -> int:
        cursor = db.execute("""
            INSERT INTO conformity_records
            (equipo_serial, equipo_hostname, usuario_nombre, tipo_archivo,
             nombre_archivo, ruta_archivo, subido_por, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("equipo_serial"),
            data.get("equipo_hostname"),
            data.get("usuario_nombre"),
            data.get("tipo_archivo"),
            data.get("nombre_archivo"),
            data.get("ruta_archivo"),
            data.get("subido_por"),
            data.get("notas"),
        ))
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def delete(db: sqlite3.Connection, id: int) -> bool:
        record = ConformityRecord.get_by_id(db, id)
        if not record:
            return False

        # Eliminar archivo físico
        try:
            file_path = Path(record["ruta_archivo"])
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass

        db.execute("DELETE FROM conformity_records WHERE id = ?", (id,))
        db.commit()
        return True

    @staticmethod
    def get_summary(db: sqlite3.Connection) -> Dict:
        """Obtiene resumen de actas"""
        total = db.execute("SELECT COUNT(*) FROM conformity_records").fetchone()[0]
        by_type = db.execute("""
            SELECT tipo_archivo, COUNT(*) as count
            FROM conformity_records GROUP BY tipo_archivo
        """).fetchall()

        equipos_con_acta = db.execute("""
            SELECT COUNT(DISTINCT equipo_serial) FROM conformity_records
        """).fetchone()[0]

        return {
            "total": total,
            "por_tipo": {row["tipo_archivo"]: row["count"] for row in by_type},
            "equipos_con_acta": equipos_con_acta,
        }

    @staticmethod
    def allowed_file(filename: str) -> bool:
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @staticmethod
    def save_file(file, equipo_serial: str) -> tuple:
        """Guarda un archivo y retorna (nombre_seguro, ruta_completa, tipo)"""
        if not file or not file.filename:
            return None, None, None

        filename = file.filename
        if not ConformityRecord.allowed_file(filename):
            return None, None, None

        ext = filename.rsplit('.', 1)[1].lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{equipo_serial}_{timestamp}.{ext}"

        # Crear subdirectorio por equipo
        equipo_dir = UPLOADS_DIR / equipo_serial
        equipo_dir.mkdir(parents=True, exist_ok=True)

        file_path = equipo_dir / safe_filename
        file.save(str(file_path))

        return safe_filename, str(file_path), ext.upper()
