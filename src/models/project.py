import sqlite3
from typing import Dict, List
from collections import Counter
from config import PROJECT_COLUMNS, DONE_STATUS, IN_PROGRESS_STATUS, PENDING_STATUS, PROJECT_PHASES


class ProjectRecord:
    @staticmethod
    def ensure_schema(db: sqlite3.Connection) -> None:
        existing = {row[1] for row in db.execute("PRAGMA table_info(project_records)")}
        expected = set(["id", *PROJECT_COLUMNS, "last_updated"])
        if existing != expected:
            db.execute("DROP TABLE IF EXISTS project_records")
            db.execute(
                """
                CREATE TABLE project_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id TEXT UNIQUE,
                    ubicacion TEXT,
                    nom_sede TEXT,
                    categoria_trab TEXT,
                    nombre_completo TEXT,
                    perfil_imagen TEXT,
                    marca TEXT,
                    modelo TEXT,
                    serial_num TEXT,
                    hostname TEXT,
                    ip_equipo TEXT,
                    email_trabajo TEXT,
                    fecha_estado TEXT,
                    estado TEXT,
                    estado_coordinacion TEXT,
                    estado_upgrade TEXT,
                    fecha_programada TEXT,
                    fecha_ejecucion TEXT,
                    notas TEXT,
                    last_updated TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            db.commit()

    @staticmethod
    def status_bucket(value: str) -> str:
        if not value:
            return "Sin estado"
        upper_value = value.strip().upper()
        if upper_value in DONE_STATUS:
            return "Completado"
        if upper_value in IN_PROGRESS_STATUS:
            return "En progreso"
        if upper_value in PENDING_STATUS:
            return "Pendiente"
        return "Otro"

    @staticmethod
    def get_filter_options(db: sqlite3.Connection, field: str) -> List[str]:
        rows = db.execute(
            f"SELECT DISTINCT {field} FROM project_records WHERE {field} IS NOT NULL AND {field} <> '' ORDER BY {field}"
        ).fetchall()
        return [row[0] for row in rows]

    @staticmethod
    def query_records(db: sqlite3.Connection, filters: dict) -> List[sqlite3.Row]:
        query = (
            "SELECT record_id, ubicacion, nom_sede, categoria_trab, nombre_completo, perfil_imagen, "
            "marca, modelo, serial_num, hostname, ip_equipo, email_trabajo, fecha_estado, estado, "
            "estado_coordinacion, estado_upgrade, fecha_programada, fecha_ejecucion, notas, last_updated "
            "FROM project_records"
        )
        conditions = []
        params: List[str] = []

        for key in ["ubicacion", "nom_sede", "categoria_trab"]:
            if filters.get(key):
                conditions.append(f"{key} = ?")
                params.append(filters[key])

        if filters.get("estado"):
            conditions.append("UPPER(estado) = UPPER(?)")
            params.append(filters["estado"])

        if filters.get("fecha_inicio"):
            conditions.append("fecha_estado >= ?")
            params.append(filters["fecha_inicio"])

        if filters.get("fecha_fin"):
            conditions.append("fecha_estado <= ?")
            params.append(filters["fecha_fin"])

        if filters.get("nombre"):
            conditions.append("UPPER(nombre_completo) LIKE UPPER(?)")
            params.append(f"%{filters['nombre']}%")

        if filters.get("hostname"):
            conditions.append("hostname LIKE ?")
            params.append(f"%{filters['hostname']}%")

        # Filtro por fase del proyecto
        if filters.get("fase"):
            fase_key = filters["fase"]
            if fase_key in PROJECT_PHASES:
                categorias = PROJECT_PHASES[fase_key]["categorias"]
                fase_conditions = []
                for cat in categorias:
                    fase_conditions.append("UPPER(categoria_trab) LIKE UPPER(?)")
                    params.append(f"%{cat}%")
                if fase_conditions:
                    conditions.append(f"({' OR '.join(fase_conditions)})")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY last_updated DESC"

        return db.execute(query, params).fetchall()

    @staticmethod
    def calculate_summary(records: List[sqlite3.Row]) -> Dict:
        total = len(records)
        status_counts: Dict[str, int] = {}
        bucket_counts: Dict[str, int] = {}
        schedule_map: Dict[str, int] = {}
        schedule_brands: Dict[str, List[str]] = {}
        recent_updates = []

        for row in records:
            estado = (row["estado"] or "").strip().upper() or "SIN ESTADO"
            status_counts[estado] = status_counts.get(estado, 0) + 1
            bucket = ProjectRecord.status_bucket(estado)
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

            if row["fecha_estado"]:
                schedule_map[row["fecha_estado"]] = schedule_map.get(row["fecha_estado"], 0) + 1
                schedule_brands.setdefault(row["fecha_estado"], []).append(row["marca"] or "")

            recent_updates.append({
                "record_id": row["record_id"],
                "nombre_completo": row["nombre_completo"],
                "ubicacion": row["ubicacion"],
                "nom_sede": row["nom_sede"],
                "hostname": row["hostname"],
                "categoria_trab": row["categoria_trab"],
                "estado": estado,
                "estado_coordinacion": row["estado_coordinacion"],
                "estado_upgrade": row["estado_upgrade"],
                "fecha_programada": row["fecha_programada"],
                "fecha_ejecucion": row["fecha_ejecucion"],
                "fecha_estado": row["fecha_estado"],
                "marca": row["marca"],
                "modelo": row["modelo"],
                "notas": row["notas"],
                "last_updated": row["last_updated"],
            })

        schedule_brands_counts = {
            date: {brand: count for brand, count in Counter(brands).items() if brand}
            for date, brands in schedule_brands.items()
        }

        return {
            "total": total,
            "status_counts": status_counts,
            "status_buckets": bucket_counts,
            "schedule": schedule_map,
            "schedule_brands": schedule_brands_counts,
            "recent_updates": recent_updates,
        }

    @staticmethod
    def upsert_record(db: sqlite3.Connection, row: Dict[str, str]) -> int:
        params = [row.get(column) for column in PROJECT_COLUMNS]
        cursor = db.execute(
            """
            INSERT INTO project_records (
                record_id, ubicacion, nom_sede, categoria_trab, nombre_completo,
                perfil_imagen, marca, modelo, serial_num, hostname, ip_equipo,
                email_trabajo, fecha_estado, estado, estado_coordinacion,
                estado_upgrade, fecha_programada, fecha_ejecucion, notas
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(record_id) DO UPDATE SET
                ubicacion=excluded.ubicacion,
                nom_sede=excluded.nom_sede,
                categoria_trab=excluded.categoria_trab,
                nombre_completo=excluded.nombre_completo,
                perfil_imagen=excluded.perfil_imagen,
                marca=excluded.marca,
                modelo=excluded.modelo,
                serial_num=excluded.serial_num,
                hostname=excluded.hostname,
                ip_equipo=excluded.ip_equipo,
                email_trabajo=excluded.email_trabajo,
                fecha_estado=excluded.fecha_estado,
                estado=excluded.estado,
                estado_coordinacion=excluded.estado_coordinacion,
                estado_upgrade=excluded.estado_upgrade,
                fecha_programada=excluded.fecha_programada,
                fecha_ejecucion=excluded.fecha_ejecucion,
                notas=excluded.notas,
                last_updated=CURRENT_TIMESTAMP
            """,
            params,
        )
        return cursor.rowcount
