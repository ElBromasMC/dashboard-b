#!/usr/bin/env python3
"""
Script de migracion de esquema de base de datos para BanBif Dashboard.

Este script actualiza una base de datos existente al nuevo esquema,
agregando las tablas nuevas si no existen:
- ram_units, ssd_units, component_history (Inventario)
- conformity_records (Actas de conformidad)
- repotentiation_history (Historial de repotenciacion)
- disk_destructions (Destruccion de discos)

Uso:
    python scripts/migrate_db.py [--db PATH]

Por defecto:
    db: /home/runner/src/data/dashboard.db
"""

import sqlite3
import sys
from pathlib import Path

# Rutas por defecto
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "data" / "dashboard.db"


def get_existing_tables(conn: sqlite3.Connection) -> set:
    """Obtiene las tablas existentes en la base de datos"""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return {row[0] for row in cursor.fetchall()}


def migrate_schema(db_path: Path, verbose: bool = True) -> dict:
    """
    Migra el esquema de la base de datos agregando tablas nuevas.

    Returns:
        dict con estadisticas de migracion
    """
    stats = {
        "tables_created": [],
        "tables_existed": [],
        "status": "success",
        "message": ""
    }

    if not db_path.exists():
        stats["status"] = "skipped"
        stats["message"] = f"No existe BD en {db_path}"
        if verbose:
            print(f"[INFO] {stats['message']}")
        return stats

    try:
        conn = sqlite3.connect(str(db_path))

        # Obtener tablas existentes
        existing = get_existing_tables(conn)
        if verbose:
            print(f"[INFO] Tablas existentes: {', '.join(sorted(existing)) or 'ninguna'}")

        # Definir nuevas tablas
        new_tables = {
            "ram_units": """
                CREATE TABLE IF NOT EXISTS ram_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial_num TEXT UNIQUE,
                    marca TEXT,
                    capacidad_gb INTEGER,
                    tipo TEXT,
                    velocidad_mhz INTEGER,
                    estado TEXT NOT NULL DEFAULT 'POR_ENTREGAR',
                    equipo_serial TEXT,
                    fecha_instalacion TEXT,
                    fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                    notas TEXT
                )
            """,
            "ssd_units": """
                CREATE TABLE IF NOT EXISTS ssd_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    serial_num TEXT UNIQUE,
                    marca TEXT,
                    modelo TEXT,
                    capacidad_gb INTEGER,
                    tipo TEXT DEFAULT 'SATA',
                    estado TEXT NOT NULL DEFAULT 'POR_ENTREGAR',
                    equipo_serial TEXT,
                    fecha_instalacion TEXT,
                    fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                    notas TEXT
                )
            """,
            "component_history": """
                CREATE TABLE IF NOT EXISTS component_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_type TEXT NOT NULL,
                    component_id INTEGER NOT NULL,
                    accion TEXT NOT NULL,
                    estado_anterior TEXT,
                    estado_nuevo TEXT,
                    equipo_serial TEXT,
                    fecha TEXT DEFAULT CURRENT_TIMESTAMP,
                    usuario TEXT,
                    notas TEXT
                )
            """,
            "conformity_records": """
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
            """,
            "repotentiation_history": """
                CREATE TABLE IF NOT EXISTS repotentiation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    equipo_serial TEXT NOT NULL,
                    equipo_hostname TEXT,
                    fecha_repotenciacion TEXT,
                    ram_antes_gb INTEGER,
                    ram_antes_tipo TEXT,
                    ram_antes_serial TEXT,
                    ram_despues_gb INTEGER,
                    ram_despues_tipo TEXT,
                    ram_despues_serial TEXT,
                    disco_antes_capacidad_gb INTEGER,
                    disco_antes_tipo TEXT,
                    disco_antes_serial TEXT,
                    disco_despues_capacidad_gb INTEGER,
                    disco_despues_tipo TEXT,
                    disco_despues_serial TEXT,
                    ram_extraida_serial TEXT,
                    ram_extraida_estado TEXT,
                    disco_extraido_serial TEXT,
                    disco_extraido_estado TEXT,
                    disco_extraido_destruido INTEGER DEFAULT 0,
                    tecnico TEXT,
                    notas TEXT,
                    fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (equipo_serial) REFERENCES project_records(serial_num)
                )
            """,
            "disk_destructions": """
                CREATE TABLE IF NOT EXISTS disk_destructions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    disco_serial TEXT NOT NULL,
                    disco_marca TEXT,
                    disco_modelo TEXT,
                    disco_capacidad_gb INTEGER,
                    disco_tipo TEXT,
                    equipo_origen_serial TEXT,
                    equipo_origen_hostname TEXT,
                    estado TEXT NOT NULL DEFAULT 'PENDIENTE',
                    fecha_extraccion TEXT,
                    fecha_destruccion TEXT,
                    metodo_destruccion TEXT,
                    video_nombre TEXT,
                    video_ruta TEXT,
                    certificado_numero TEXT,
                    certificado_fecha TEXT,
                    responsable TEXT,
                    notas TEXT,
                    fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (equipo_origen_serial) REFERENCES project_records(serial_num)
                )
            """
        }

        # Crear tablas que no existen
        for table_name, create_sql in new_tables.items():
            if table_name in existing:
                stats["tables_existed"].append(table_name)
                if verbose:
                    print(f"  [OK] {table_name} ya existe")
            else:
                conn.execute(create_sql)
                stats["tables_created"].append(table_name)
                if verbose:
                    print(f"  [NEW] {table_name} creada")

        conn.commit()
        conn.close()

        # Resumen
        if stats["tables_created"]:
            stats["message"] = f"Tablas creadas: {', '.join(stats['tables_created'])}"
        else:
            stats["message"] = "Esquema ya actualizado, no se requieren cambios"

        if verbose:
            print(f"\n[OK] {stats['message']}")

    except Exception as e:
        stats["status"] = "error"
        stats["message"] = str(e)
        if verbose:
            print(f"[ERROR] {stats['message']}")

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Migrar esquema de base de datos BanBif Dashboard"
    )
    parser.add_argument(
        "--db", type=Path, default=DEFAULT_DB,
        help=f"Ruta de la base de datos (default: {DEFAULT_DB})"
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Modo silencioso"
    )

    args = parser.parse_args()

    if not args.quiet:
        print("=" * 50)
        print("BanBif Dashboard - Migracion de Esquema")
        print("=" * 50)
        print(f"Base de datos: {args.db}")
        print("-" * 50)

    stats = migrate_schema(args.db, verbose=not args.quiet)

    if stats["status"] == "error":
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
