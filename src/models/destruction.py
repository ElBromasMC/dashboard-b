import sqlite3
import os
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path
from config import BASE_DIR

# Directorio para almacenar informes de destrucción (PDFs)
INFORMES_DIR = BASE_DIR / "uploads" / "destruccion" / "informes"
INFORMES_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_INFORME_EXTENSIONS = {'pdf'}

# Estados de destrucción
DESTRUCTION_STATUS = {
    "PENDIENTE": "Pendiente de destrucción",
    "PROGRAMADO": "Programado para destrucción",
    "EN_PROCESO": "En proceso de destrucción",
    "DESTRUIDO": "Destruido",
    "CERTIFICADO": "Destruido y certificado",
}


class DiskDestruction:
    """Modelo para gestionar la destrucción de discos"""

    @staticmethod
    def ensure_table(db: sqlite3.Connection) -> None:
        """Crea la tabla de destrucción de discos si no existe"""
        db.execute("""
            CREATE TABLE IF NOT EXISTS disk_destructions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                disco_serial TEXT NOT NULL,
                disco_marca TEXT,
                disco_modelo TEXT,
                disco_capacidad_gb INTEGER,
                disco_tipo TEXT,

                equipo_origen_serial TEXT,
                equipo_origen_hostname TEXT,
                sede TEXT,

                estado TEXT NOT NULL DEFAULT 'PENDIENTE',
                fecha_extraccion TEXT,
                fecha_destruccion TEXT,
                metodo_destruccion TEXT,

                video_url TEXT,

                informe_nombre TEXT,
                informe_ruta TEXT,

                certificado_numero TEXT,
                certificado_fecha TEXT,

                responsable TEXT,
                notas TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (equipo_origen_serial) REFERENCES project_records(serial_num)
            )
        """)
        db.commit()

        # Migrar columnas si la tabla ya existe (para bases de datos existentes)
        DiskDestruction._migrate_columns(db)

    @staticmethod
    def _migrate_columns(db: sqlite3.Connection) -> None:
        """Agrega columnas nuevas si no existen (migración)"""
        cursor = db.execute("PRAGMA table_info(disk_destructions)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        migrations = [
            ("sede", "TEXT"),
            ("video_url", "TEXT"),
            ("informe_nombre", "TEXT"),
            ("informe_ruta", "TEXT"),
        ]

        for col_name, col_type in migrations:
            if col_name not in existing_columns:
                db.execute(f"ALTER TABLE disk_destructions ADD COLUMN {col_name} {col_type}")

        db.commit()

    @staticmethod
    def get_all(db: sqlite3.Connection, estado: str = None) -> List[sqlite3.Row]:
        query = """
            SELECT dd.*, pr.nombre_completo, pr.hostname as hostname_actual
            FROM disk_destructions dd
            LEFT JOIN project_records pr ON dd.equipo_origen_serial = pr.serial_num
        """
        params = []
        if estado:
            query += " WHERE dd.estado = ?"
            params.append(estado)
        query += " ORDER BY dd.fecha_registro DESC"
        return db.execute(query, params).fetchall()

    @staticmethod
    def get_by_id(db: sqlite3.Connection, id: int) -> Optional[sqlite3.Row]:
        return db.execute("""
            SELECT dd.*, pr.nombre_completo, pr.hostname as hostname_actual
            FROM disk_destructions dd
            LEFT JOIN project_records pr ON dd.equipo_origen_serial = pr.serial_num
            WHERE dd.id = ?
        """, (id,)).fetchone()

    @staticmethod
    def get_by_serial(db: sqlite3.Connection, serial: str) -> Optional[sqlite3.Row]:
        return db.execute("""
            SELECT * FROM disk_destructions WHERE disco_serial = ?
        """, (serial,)).fetchone()

    @staticmethod
    def create(db: sqlite3.Connection, data: Dict) -> int:
        cursor = db.execute("""
            INSERT INTO disk_destructions (
                disco_serial, disco_marca, disco_modelo, disco_capacidad_gb, disco_tipo,
                equipo_origen_serial, equipo_origen_hostname, sede,
                estado, fecha_extraccion, fecha_destruccion, metodo_destruccion,
                video_url,
                informe_nombre, informe_ruta,
                certificado_numero, certificado_fecha,
                responsable, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("disco_serial"),
            data.get("disco_marca"),
            data.get("disco_modelo"),
            data.get("disco_capacidad_gb"),
            data.get("disco_tipo"),
            data.get("equipo_origen_serial"),
            data.get("equipo_origen_hostname"),
            data.get("sede"),
            data.get("estado", "PENDIENTE"),
            data.get("fecha_extraccion"),
            data.get("fecha_destruccion"),
            data.get("metodo_destruccion"),
            data.get("video_url"),
            data.get("informe_nombre"),
            data.get("informe_ruta"),
            data.get("certificado_numero"),
            data.get("certificado_fecha"),
            data.get("responsable"),
            data.get("notas"),
        ))
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def update(db: sqlite3.Connection, id: int, data: Dict) -> bool:
        db.execute("""
            UPDATE disk_destructions SET
                disco_marca = ?, disco_modelo = ?, disco_capacidad_gb = ?, disco_tipo = ?,
                sede = ?,
                estado = ?, fecha_extraccion = ?, fecha_destruccion = ?, metodo_destruccion = ?,
                video_url = ?,
                informe_nombre = ?, informe_ruta = ?,
                certificado_numero = ?, certificado_fecha = ?,
                responsable = ?, notas = ?
            WHERE id = ?
        """, (
            data.get("disco_marca"),
            data.get("disco_modelo"),
            data.get("disco_capacidad_gb"),
            data.get("disco_tipo"),
            data.get("sede"),
            data.get("estado"),
            data.get("fecha_extraccion"),
            data.get("fecha_destruccion"),
            data.get("metodo_destruccion"),
            data.get("video_url"),
            data.get("informe_nombre"),
            data.get("informe_ruta"),
            data.get("certificado_numero"),
            data.get("certificado_fecha"),
            data.get("responsable"),
            data.get("notas"),
            id,
        ))
        db.commit()
        return True

    @staticmethod
    def delete(db: sqlite3.Connection, id: int) -> bool:
        record = DiskDestruction.get_by_id(db, id)
        if record and record["informe_ruta"]:
            try:
                informe_path = Path(record["informe_ruta"])
                if informe_path.exists():
                    informe_path.unlink()
            except Exception:
                pass

        db.execute("DELETE FROM disk_destructions WHERE id = ?", (id,))
        db.commit()
        return True

    @staticmethod
    def get_summary(db: sqlite3.Connection) -> Dict:
        """Obtiene resumen de destrucción de discos"""
        by_status = db.execute("""
            SELECT estado, COUNT(*) as count
            FROM disk_destructions GROUP BY estado
        """).fetchall()

        total = db.execute("SELECT COUNT(*) FROM disk_destructions").fetchone()[0]

        destruidos = db.execute("""
            SELECT COUNT(*) FROM disk_destructions
            WHERE estado IN ('DESTRUIDO', 'CERTIFICADO')
        """).fetchone()[0]

        con_video = db.execute("""
            SELECT COUNT(*) FROM disk_destructions
            WHERE video_url IS NOT NULL AND video_url != ''
        """).fetchone()[0]

        con_informe = db.execute("""
            SELECT COUNT(*) FROM disk_destructions
            WHERE informe_ruta IS NOT NULL AND informe_ruta != ''
        """).fetchone()[0]

        certificados = db.execute("""
            SELECT COUNT(*) FROM disk_destructions
            WHERE estado = 'CERTIFICADO'
        """).fetchone()[0]

        return {
            "total": total,
            "por_estado": {row["estado"]: row["count"] for row in by_status},
            "destruidos": destruidos,
            "con_video": con_video,
            "con_informe": con_informe,
            "certificados": certificados,
        }

    @staticmethod
    def allowed_informe(filename: str) -> bool:
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in ALLOWED_INFORME_EXTENSIONS

    @staticmethod
    def save_informe(file, disco_serial: str) -> tuple:
        """Guarda un informe PDF y retorna (nombre_seguro, ruta_completa)"""
        if not file or not file.filename:
            return None, None

        filename = file.filename
        if not DiskDestruction.allowed_informe(filename):
            return None, None

        ext = filename.rsplit('.', 1)[1].lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"informe_{disco_serial}_{timestamp}.{ext}"

        file_path = INFORMES_DIR / safe_filename
        file.save(str(file_path))

        return safe_filename, str(file_path)
