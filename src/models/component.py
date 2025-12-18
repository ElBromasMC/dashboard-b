import sqlite3
from typing import List, Dict, Optional
from datetime import datetime


# Estados de componentes
COMPONENT_STATUS = {
    "POR_ENTREGAR": "Por entregar",
    "INSTALADO": "Instalado",
    "POR_ASIGNAR": "Por asignar",
    "DEFECTUOSO": "Defectuoso",
}

# Colores para el dashboard
COMPONENT_STATUS_COLORS = {
    "POR_ENTREGAR": "#6c757d",  # plomo/gris
    "INSTALADO": "#198754",      # verde
    "POR_ASIGNAR": "#ffc107",    # amarillo
    "DEFECTUOSO": "#dc3545",     # rojo
}


class Component:
    """Clase base para componentes (RAM y SSD)"""

    @staticmethod
    def ensure_tables(db: sqlite3.Connection) -> None:
        """Crea las tablas de componentes si no existen"""

        # Tabla de memorias RAM
        db.execute("""
            CREATE TABLE IF NOT EXISTS ram_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_num TEXT UNIQUE NOT NULL,
                marca TEXT,
                capacidad_gb INTEGER NOT NULL,
                tipo TEXT,
                velocidad_mhz INTEGER,
                estado TEXT NOT NULL DEFAULT 'POR_ENTREGAR',
                equipo_serial TEXT,
                fecha_instalacion TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                notas TEXT,
                FOREIGN KEY (equipo_serial) REFERENCES project_records(serial_num)
            )
        """)

        # Tabla de discos sólidos (SSD)
        db.execute("""
            CREATE TABLE IF NOT EXISTS ssd_units (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                serial_num TEXT UNIQUE NOT NULL,
                marca TEXT,
                modelo TEXT,
                capacidad_gb INTEGER NOT NULL,
                tipo TEXT,
                estado TEXT NOT NULL DEFAULT 'POR_ENTREGAR',
                equipo_serial TEXT,
                fecha_instalacion TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                notas TEXT,
                FOREIGN KEY (equipo_serial) REFERENCES project_records(serial_num)
            )
        """)

        # Historial de movimientos de componentes
        db.execute("""
            CREATE TABLE IF NOT EXISTS component_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_componente TEXT NOT NULL,
                componente_id INTEGER NOT NULL,
                componente_serial TEXT NOT NULL,
                accion TEXT NOT NULL,
                equipo_serial_anterior TEXT,
                equipo_serial_nuevo TEXT,
                estado_anterior TEXT,
                estado_nuevo TEXT,
                capacidad_anterior_gb INTEGER,
                capacidad_nueva_gb INTEGER,
                usuario TEXT,
                fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                notas TEXT
            )
        """)

        db.commit()


class RAMUnit:
    """Modelo para unidades de memoria RAM"""

    def __init__(self, id: int, serial_num: str, marca: str, capacidad_gb: int,
                 tipo: str, velocidad_mhz: int, estado: str, equipo_serial: str,
                 fecha_instalacion: str, fecha_registro: str, notas: str):
        self.id = id
        self.serial_num = serial_num
        self.marca = marca
        self.capacidad_gb = capacidad_gb
        self.tipo = tipo
        self.velocidad_mhz = velocidad_mhz
        self.estado = estado
        self.equipo_serial = equipo_serial
        self.fecha_instalacion = fecha_instalacion
        self.fecha_registro = fecha_registro
        self.notas = notas

    @staticmethod
    def get_all(db: sqlite3.Connection, estado: str = None) -> List[sqlite3.Row]:
        query = "SELECT * FROM ram_units"
        params = []
        if estado:
            query += " WHERE estado = ?"
            params.append(estado)
        query += " ORDER BY fecha_registro DESC"
        return db.execute(query, params).fetchall()

    @staticmethod
    def get_by_id(db: sqlite3.Connection, id: int) -> Optional[sqlite3.Row]:
        return db.execute("SELECT * FROM ram_units WHERE id = ?", (id,)).fetchone()

    @staticmethod
    def get_by_serial(db: sqlite3.Connection, serial_num: str) -> Optional[sqlite3.Row]:
        return db.execute("SELECT * FROM ram_units WHERE serial_num = ?", (serial_num,)).fetchone()

    @staticmethod
    def create(db: sqlite3.Connection, data: Dict) -> int:
        cursor = db.execute("""
            INSERT INTO ram_units (serial_num, marca, capacidad_gb, tipo, velocidad_mhz, estado, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("serial_num"),
            data.get("marca"),
            data.get("capacidad_gb"),
            data.get("tipo"),
            data.get("velocidad_mhz"),
            data.get("estado", "POR_ENTREGAR"),
            data.get("notas"),
        ))
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def update(db: sqlite3.Connection, id: int, data: Dict) -> bool:
        db.execute("""
            UPDATE ram_units SET
                marca = ?, capacidad_gb = ?, tipo = ?, velocidad_mhz = ?,
                estado = ?, equipo_serial = ?, fecha_instalacion = ?, notas = ?
            WHERE id = ?
        """, (
            data.get("marca"),
            data.get("capacidad_gb"),
            data.get("tipo"),
            data.get("velocidad_mhz"),
            data.get("estado"),
            data.get("equipo_serial"),
            data.get("fecha_instalacion"),
            data.get("notas"),
            id,
        ))
        db.commit()
        return True

    @staticmethod
    def assign_to_equipment(db: sqlite3.Connection, ram_id: int, equipo_serial: str, usuario: str = None) -> bool:
        """Asigna una RAM a un equipo"""
        ram = RAMUnit.get_by_id(db, ram_id)
        if not ram:
            return False

        old_estado = ram["estado"]
        old_equipo = ram["equipo_serial"]
        fecha = datetime.now().isoformat()

        db.execute("""
            UPDATE ram_units SET estado = 'INSTALADO', equipo_serial = ?, fecha_instalacion = ?
            WHERE id = ?
        """, (equipo_serial, fecha, ram_id))

        # Registrar en historial
        db.execute("""
            INSERT INTO component_history
            (tipo_componente, componente_id, componente_serial, accion, equipo_serial_anterior,
             equipo_serial_nuevo, estado_anterior, estado_nuevo, usuario, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("RAM", ram_id, ram["serial_num"], "INSTALACION", old_equipo, equipo_serial,
              old_estado, "INSTALADO", usuario, f"Instalación en equipo {equipo_serial}"))

        db.commit()
        return True

    @staticmethod
    def unassign(db: sqlite3.Connection, ram_id: int, usuario: str = None, notas: str = None) -> bool:
        """Desasigna una RAM de un equipo"""
        ram = RAMUnit.get_by_id(db, ram_id)
        if not ram:
            return False

        old_equipo = ram["equipo_serial"]
        old_estado = ram["estado"]

        db.execute("""
            UPDATE ram_units SET estado = 'POR_ASIGNAR', equipo_serial = NULL, fecha_instalacion = NULL
            WHERE id = ?
        """, (ram_id,))

        db.execute("""
            INSERT INTO component_history
            (tipo_componente, componente_id, componente_serial, accion, equipo_serial_anterior,
             estado_anterior, estado_nuevo, usuario, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("RAM", ram_id, ram["serial_num"], "DESINSTALACION", old_equipo,
              old_estado, "POR_ASIGNAR", usuario, notas))

        db.commit()
        return True

    @staticmethod
    def get_summary(db: sqlite3.Connection) -> Dict:
        """Obtiene resumen de RAM por estado"""
        rows = db.execute("""
            SELECT estado, COUNT(*) as count, SUM(capacidad_gb) as total_gb
            FROM ram_units GROUP BY estado
        """).fetchall()

        summary = {
            "por_estado": {},
            "total": 0,
            "total_gb": 0,
        }

        for row in rows:
            summary["por_estado"][row["estado"]] = {
                "count": row["count"],
                "total_gb": row["total_gb"] or 0,
            }
            summary["total"] += row["count"]
            summary["total_gb"] += row["total_gb"] or 0

        return summary

    @staticmethod
    def delete(db: sqlite3.Connection, id: int) -> bool:
        """Elimina una unidad de RAM"""
        db.execute("DELETE FROM ram_units WHERE id = ?", (id,))
        db.commit()
        return True


class SSDUnit:
    """Modelo para unidades de disco sólido (SSD)"""

    @staticmethod
    def get_all(db: sqlite3.Connection, estado: str = None) -> List[sqlite3.Row]:
        query = "SELECT * FROM ssd_units"
        params = []
        if estado:
            query += " WHERE estado = ?"
            params.append(estado)
        query += " ORDER BY fecha_registro DESC"
        return db.execute(query, params).fetchall()

    @staticmethod
    def get_by_id(db: sqlite3.Connection, id: int) -> Optional[sqlite3.Row]:
        return db.execute("SELECT * FROM ssd_units WHERE id = ?", (id,)).fetchone()

    @staticmethod
    def get_by_serial(db: sqlite3.Connection, serial_num: str) -> Optional[sqlite3.Row]:
        return db.execute("SELECT * FROM ssd_units WHERE serial_num = ?", (serial_num,)).fetchone()

    @staticmethod
    def create(db: sqlite3.Connection, data: Dict) -> int:
        cursor = db.execute("""
            INSERT INTO ssd_units (serial_num, marca, modelo, capacidad_gb, tipo, estado, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("serial_num"),
            data.get("marca"),
            data.get("modelo"),
            data.get("capacidad_gb"),
            data.get("tipo"),
            data.get("estado", "POR_ENTREGAR"),
            data.get("notas"),
        ))
        db.commit()
        return cursor.lastrowid

    @staticmethod
    def update(db: sqlite3.Connection, id: int, data: Dict) -> bool:
        db.execute("""
            UPDATE ssd_units SET
                marca = ?, modelo = ?, capacidad_gb = ?, tipo = ?,
                estado = ?, equipo_serial = ?, fecha_instalacion = ?, notas = ?
            WHERE id = ?
        """, (
            data.get("marca"),
            data.get("modelo"),
            data.get("capacidad_gb"),
            data.get("tipo"),
            data.get("estado"),
            data.get("equipo_serial"),
            data.get("fecha_instalacion"),
            data.get("notas"),
            id,
        ))
        db.commit()
        return True

    @staticmethod
    def assign_to_equipment(db: sqlite3.Connection, ssd_id: int, equipo_serial: str, usuario: str = None) -> bool:
        """Asigna un SSD a un equipo"""
        ssd = SSDUnit.get_by_id(db, ssd_id)
        if not ssd:
            return False

        old_estado = ssd["estado"]
        old_equipo = ssd["equipo_serial"]
        fecha = datetime.now().isoformat()

        db.execute("""
            UPDATE ssd_units SET estado = 'INSTALADO', equipo_serial = ?, fecha_instalacion = ?
            WHERE id = ?
        """, (equipo_serial, fecha, ssd_id))

        db.execute("""
            INSERT INTO component_history
            (tipo_componente, componente_id, componente_serial, accion, equipo_serial_anterior,
             equipo_serial_nuevo, estado_anterior, estado_nuevo, usuario, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("SSD", ssd_id, ssd["serial_num"], "INSTALACION", old_equipo, equipo_serial,
              old_estado, "INSTALADO", usuario, f"Instalación en equipo {equipo_serial}"))

        db.commit()
        return True

    @staticmethod
    def unassign(db: sqlite3.Connection, ssd_id: int, usuario: str = None, notas: str = None) -> bool:
        """Desasigna un SSD de un equipo"""
        ssd = SSDUnit.get_by_id(db, ssd_id)
        if not ssd:
            return False

        old_equipo = ssd["equipo_serial"]
        old_estado = ssd["estado"]

        db.execute("""
            UPDATE ssd_units SET estado = 'POR_ASIGNAR', equipo_serial = NULL, fecha_instalacion = NULL
            WHERE id = ?
        """, (ssd_id,))

        db.execute("""
            INSERT INTO component_history
            (tipo_componente, componente_id, componente_serial, accion, equipo_serial_anterior,
             estado_anterior, estado_nuevo, usuario, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("SSD", ssd_id, ssd["serial_num"], "DESINSTALACION", old_equipo,
              old_estado, "POR_ASIGNAR", usuario, notas))

        db.commit()
        return True

    @staticmethod
    def get_summary(db: sqlite3.Connection) -> Dict:
        """Obtiene resumen de SSD por estado"""
        rows = db.execute("""
            SELECT estado, COUNT(*) as count, SUM(capacidad_gb) as total_gb
            FROM ssd_units GROUP BY estado
        """).fetchall()

        summary = {
            "por_estado": {},
            "total": 0,
            "total_gb": 0,
        }

        for row in rows:
            summary["por_estado"][row["estado"]] = {
                "count": row["count"],
                "total_gb": row["total_gb"] or 0,
            }
            summary["total"] += row["count"]
            summary["total_gb"] += row["total_gb"] or 0

        return summary

    @staticmethod
    def delete(db: sqlite3.Connection, id: int) -> bool:
        """Elimina una unidad de SSD"""
        db.execute("DELETE FROM ssd_units WHERE id = ?", (id,))
        db.commit()
        return True


class ComponentHistory:
    """Modelo para historial de movimientos de componentes"""

    @staticmethod
    def get_by_component(db: sqlite3.Connection, tipo: str, componente_id: int) -> List[sqlite3.Row]:
        return db.execute("""
            SELECT * FROM component_history
            WHERE tipo_componente = ? AND componente_id = ?
            ORDER BY fecha DESC
        """, (tipo, componente_id)).fetchall()

    @staticmethod
    def get_by_equipment(db: sqlite3.Connection, equipo_serial: str) -> List[sqlite3.Row]:
        return db.execute("""
            SELECT * FROM component_history
            WHERE equipo_serial_anterior = ? OR equipo_serial_nuevo = ?
            ORDER BY fecha DESC
        """, (equipo_serial, equipo_serial)).fetchall()

    @staticmethod
    def get_recent(db: sqlite3.Connection, limit: int = 20) -> List[sqlite3.Row]:
        return db.execute("""
            SELECT * FROM component_history ORDER BY fecha DESC LIMIT ?
        """, (limit,)).fetchall()

    @staticmethod
    def add_entry(db: sqlite3.Connection, data: Dict) -> int:
        cursor = db.execute("""
            INSERT INTO component_history
            (tipo_componente, componente_id, componente_serial, accion, equipo_serial_anterior,
             equipo_serial_nuevo, estado_anterior, estado_nuevo, capacidad_anterior_gb,
             capacidad_nueva_gb, usuario, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get("tipo_componente"),
            data.get("componente_id"),
            data.get("componente_serial"),
            data.get("accion"),
            data.get("equipo_serial_anterior"),
            data.get("equipo_serial_nuevo"),
            data.get("estado_anterior"),
            data.get("estado_nuevo"),
            data.get("capacidad_anterior_gb"),
            data.get("capacidad_nueva_gb"),
            data.get("usuario"),
            data.get("notas"),
        ))
        db.commit()
        return cursor.lastrowid
