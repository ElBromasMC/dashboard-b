import sqlite3
from typing import List, Dict, Optional
from datetime import datetime


class RepotentiationRecord:
    """Modelo para registrar el historial de repotenciación de equipos"""

    @staticmethod
    def ensure_table(db: sqlite3.Connection) -> None:
        """Crea la tabla de historial de repotenciación si no existe"""
        db.execute("""
            CREATE TABLE IF NOT EXISTS repotentiation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipo_serial TEXT NOT NULL,
                equipo_hostname TEXT,
                fecha_repotenciacion TEXT NOT NULL,

                -- RAM antes
                ram_antes_gb INTEGER,
                ram_antes_tipo TEXT,
                ram_antes_serial TEXT,

                -- RAM después
                ram_despues_gb INTEGER,
                ram_despues_tipo TEXT,
                ram_despues_serial TEXT,

                -- Disco antes (mecánico)
                disco_antes_tipo TEXT,
                disco_antes_capacidad_gb INTEGER,
                disco_antes_serial TEXT,

                -- Disco después (SSD)
                disco_despues_tipo TEXT,
                disco_despues_capacidad_gb INTEGER,
                disco_despues_serial TEXT,

                -- Componentes extraídos
                ram_extraida_serial TEXT,
                ram_extraida_estado TEXT,
                disco_extraido_serial TEXT,
                disco_extraido_estado TEXT,
                disco_extraido_destruido INTEGER DEFAULT 0,

                -- Metadatos
                tecnico TEXT,
                notas TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (equipo_serial) REFERENCES project_records(serial_num)
            )
        """)
        db.commit()

    @staticmethod
    def get_all(db: sqlite3.Connection, equipo_serial: str = None) -> List[sqlite3.Row]:
        query = """
            SELECT rh.*, pr.nombre_completo, pr.hostname as equipo_hostname_actual
            FROM repotentiation_history rh
            LEFT JOIN project_records pr ON rh.equipo_serial = pr.serial_num
        """
        params = []
        if equipo_serial:
            query += " WHERE rh.equipo_serial = ?"
            params.append(equipo_serial)
        query += " ORDER BY rh.fecha_repotenciacion DESC"
        return db.execute(query, params).fetchall()

    @staticmethod
    def get_by_id(db: sqlite3.Connection, id: int) -> Optional[sqlite3.Row]:
        return db.execute("""
            SELECT rh.*, pr.nombre_completo, pr.hostname as equipo_hostname_actual
            FROM repotentiation_history rh
            LEFT JOIN project_records pr ON rh.equipo_serial = pr.serial_num
            WHERE rh.id = ?
        """, (id,)).fetchone()

    @staticmethod
    def get_by_serial(db: sqlite3.Connection, equipo_serial: str) -> List[sqlite3.Row]:
        return db.execute("""
            SELECT * FROM repotentiation_history
            WHERE equipo_serial = ?
            ORDER BY fecha_repotenciacion DESC
        """, (equipo_serial,)).fetchall()

    @staticmethod
    def create(db: sqlite3.Connection, data: Dict) -> int:
        cursor = db.execute("""
            INSERT INTO repotentiation_history (
                equipo_serial, equipo_hostname, fecha_repotenciacion,
                ram_antes_gb, ram_antes_tipo, ram_antes_serial,
                ram_despues_gb, ram_despues_tipo, ram_despues_serial,
                disco_antes_tipo, disco_antes_capacidad_gb, disco_antes_serial,
                disco_despues_tipo, disco_despues_capacidad_gb, disco_despues_serial,
                ram_extraida_serial, ram_extraida_estado,
                disco_extraido_serial, disco_extraido_estado, disco_extraido_destruido,
                tecnico, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("equipo_serial"),
            data.get("equipo_hostname"),
            data.get("fecha_repotenciacion"),
            data.get("ram_antes_gb"),
            data.get("ram_antes_tipo"),
            data.get("ram_antes_serial"),
            data.get("ram_despues_gb"),
            data.get("ram_despues_tipo"),
            data.get("ram_despues_serial"),
            data.get("disco_antes_tipo"),
            data.get("disco_antes_capacidad_gb"),
            data.get("disco_antes_serial"),
            data.get("disco_despues_tipo"),
            data.get("disco_despues_capacidad_gb"),
            data.get("disco_despues_serial"),
            data.get("ram_extraida_serial"),
            data.get("ram_extraida_estado"),
            data.get("disco_extraido_serial"),
            data.get("disco_extraido_estado"),
            data.get("disco_extraido_destruido", 0),
            data.get("tecnico"),
            data.get("notas"),
        ))
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def update(db: sqlite3.Connection, id: int, data: Dict) -> bool:
        db.execute("""
            UPDATE repotentiation_history SET
                fecha_repotenciacion = ?,
                ram_antes_gb = ?, ram_antes_tipo = ?, ram_antes_serial = ?,
                ram_despues_gb = ?, ram_despues_tipo = ?, ram_despues_serial = ?,
                disco_antes_tipo = ?, disco_antes_capacidad_gb = ?, disco_antes_serial = ?,
                disco_despues_tipo = ?, disco_despues_capacidad_gb = ?, disco_despues_serial = ?,
                ram_extraida_serial = ?, ram_extraida_estado = ?,
                disco_extraido_serial = ?, disco_extraido_estado = ?, disco_extraido_destruido = ?,
                tecnico = ?, notas = ?
            WHERE id = ?
        """, (
            data.get("fecha_repotenciacion"),
            data.get("ram_antes_gb"),
            data.get("ram_antes_tipo"),
            data.get("ram_antes_serial"),
            data.get("ram_despues_gb"),
            data.get("ram_despues_tipo"),
            data.get("ram_despues_serial"),
            data.get("disco_antes_tipo"),
            data.get("disco_antes_capacidad_gb"),
            data.get("disco_antes_serial"),
            data.get("disco_despues_tipo"),
            data.get("disco_despues_capacidad_gb"),
            data.get("disco_despues_serial"),
            data.get("ram_extraida_serial"),
            data.get("ram_extraida_estado"),
            data.get("disco_extraido_serial"),
            data.get("disco_extraido_estado"),
            data.get("disco_extraido_destruido", 0),
            data.get("tecnico"),
            data.get("notas"),
            id,
        ))
        db.commit()
        return True

    @staticmethod
    def delete(db: sqlite3.Connection, id: int) -> bool:
        db.execute("DELETE FROM repotentiation_history WHERE id = ?", (id,))
        db.commit()
        return True

    @staticmethod
    def get_summary(db: sqlite3.Connection) -> Dict:
        """Obtiene resumen de repotenciaciones"""
        total = db.execute("SELECT COUNT(*) FROM repotentiation_history").fetchone()[0]

        # Total RAM agregada
        ram_added = db.execute("""
            SELECT SUM(ram_despues_gb - COALESCE(ram_antes_gb, 0))
            FROM repotentiation_history
            WHERE ram_despues_gb IS NOT NULL
        """).fetchone()[0] or 0

        # Total SSD instalados
        ssd_count = db.execute("""
            SELECT COUNT(*) FROM repotentiation_history
            WHERE disco_despues_serial IS NOT NULL
        """).fetchone()[0]

        # Discos destruidos
        discos_destruidos = db.execute("""
            SELECT COUNT(*) FROM repotentiation_history
            WHERE disco_extraido_destruido = 1
        """).fetchone()[0]

        # Por mes
        by_month = db.execute("""
            SELECT strftime('%Y-%m', fecha_repotenciacion) as mes, COUNT(*) as count
            FROM repotentiation_history
            WHERE fecha_repotenciacion IS NOT NULL
            GROUP BY mes
            ORDER BY mes DESC
            LIMIT 12
        """).fetchall()

        return {
            "total": total,
            "ram_agregada_gb": ram_added,
            "ssd_instalados": ssd_count,
            "discos_destruidos": discos_destruidos,
            "por_mes": {row["mes"]: row["count"] for row in by_month},
        }

    @staticmethod
    def search_by_serial(db: sqlite3.Connection, serial: str) -> List[sqlite3.Row]:
        """Busca repotenciaciones por serial de equipo o componente"""
        return db.execute("""
            SELECT rh.*, pr.nombre_completo
            FROM repotentiation_history rh
            LEFT JOIN project_records pr ON rh.equipo_serial = pr.serial_num
            WHERE rh.equipo_serial LIKE ?
               OR rh.ram_antes_serial LIKE ?
               OR rh.ram_despues_serial LIKE ?
               OR rh.disco_antes_serial LIKE ?
               OR rh.disco_despues_serial LIKE ?
            ORDER BY rh.fecha_repotenciacion DESC
        """, (f"%{serial}%",) * 5).fetchall()
