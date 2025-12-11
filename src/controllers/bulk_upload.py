import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory

from models.database import get_db
from models.project import ProjectRecord
from models.component import RAMUnit, SSDUnit, COMPONENT_STATUS
from models.repotentiation import RepotentiationRecord
from models.destruction import DiskDestruction, DESTRUCTION_STATUS
from config import CSV_FIELD_MAP, BASE_DIR
from utils.decorators import login_required, admin_required
from utils.helpers import normalize_header, normalize_date

bulk_upload_bp = Blueprint('bulk_upload', __name__, url_prefix='/carga-masiva')


# ============================================================================
# CARGA DE AVANCES (project_records)
# ============================================================================

@bulk_upload_bp.route("/")
@login_required
@admin_required
def index():
    """Vista principal de carga masiva"""
    return render_template("bulk_upload/index.html")


@bulk_upload_bp.route("/avances", methods=["GET", "POST"])
@login_required
@admin_required
def upload_progress():
    """Carga masiva de avances del proyecto"""
    summary = None
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Selecciona un archivo CSV", "danger")
            return render_template("bulk_upload/avances.html", summary=summary)
        if not file.filename.lower().endswith(".csv"):
            flash("El archivo debe tener formato .csv", "danger")
            return render_template("bulk_upload/avances.html", summary=summary)

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        except UnicodeDecodeError:
            flash("No se pudo decodificar el archivo. Usa UTF-8.", "danger")
            return render_template("bulk_upload/avances.html", summary=summary)

        reader = csv.DictReader(stream)
        mapped_rows = []
        for raw_row in reader:
            normalized_row = {}
            for header, value in raw_row.items():
                key = CSV_FIELD_MAP.get(normalize_header(header))
                if not key:
                    continue
                if isinstance(value, str):
                    value = value.strip()
                normalized_row[key] = value
            if not normalized_row.get("record_id"):
                continue
            for field in ("estado", "estado_coordinacion", "estado_upgrade"):
                if field in normalized_row and isinstance(normalized_row[field], str):
                    normalized_row[field] = normalized_row[field].upper()
            for field in ("fecha_estado", "fecha_programada", "fecha_ejecucion"):
                if field in normalized_row:
                    normalized_row[field] = normalize_date(normalized_row[field])
            mapped_rows.append(normalized_row)

        if not mapped_rows:
            flash("No se encontraron registros validos en el CSV.", "warning")
            return render_template("bulk_upload/avances.html", summary=summary)

        db = get_db()
        inserted = 0
        updated = 0
        for row in mapped_rows:
            rowcount = ProjectRecord.upsert_record(db, row)
            if rowcount == 1:
                inserted += 1
            else:
                updated += 1
        db.commit()
        summary = {"inserted": inserted, "updated": updated, "total": inserted + updated}
        flash("Carga procesada correctamente", "success")
    return render_template("bulk_upload/avances.html", summary=summary)


@bulk_upload_bp.route("/avances/plantilla")
@login_required
@admin_required
def download_progress_template():
    """Descarga plantilla CSV para avances"""
    template_path = BASE_DIR / "static" / "templates" / "avance_template.csv"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "id", "ubicacion", "nom_sede", "categoria_trab", "nombre_completo",
            "perfil_imagen", "marca", "modelo", "serial_num", "hostname",
            "ip_equipo", "email_trabajo", "fecha_estado", "estado",
            "estado_coordinacion", "estado_upgrade", "fecha_programada",
            "fecha_ejecucion", "notas",
        ])
        writer.writerow([
            "001", "SEDE PRINCIPAL", "Centro Corporativo", "UPGRADE + WIN11",
            "Nombre Ejemplo", "OFICINA PRINCIPAL ADMINISTRATIVO", "HP",
            "EliteBook 840", "5CD3051HBZ", "BANCAINMOBIOP01", "10.10.2.15",
            "usuario@banbif.com", "2025-09-29", "REALIZADO", "REALIZADO",
            "PROGRAMADO", "2025-09-27", "2025-09-29", "Observaciones",
        ])
    return send_from_directory(template_path.parent, template_path.name, as_attachment=True)


# ============================================================================
# CARGA DE RAM
# ============================================================================

RAM_CSV_FIELDS = {
    "serial_num": "serial_num",
    "serial": "serial_num",
    "marca": "marca",
    "brand": "marca",
    "capacidad_gb": "capacidad_gb",
    "capacidad": "capacidad_gb",
    "gb": "capacidad_gb",
    "tipo": "tipo",
    "type": "tipo",
    "velocidad_mhz": "velocidad_mhz",
    "velocidad": "velocidad_mhz",
    "mhz": "velocidad_mhz",
    "estado": "estado",
    "status": "estado",
    "notas": "notas",
    "notes": "notas",
}


@bulk_upload_bp.route("/ram", methods=["GET", "POST"])
@login_required
@admin_required
def upload_ram():
    """Carga masiva de memorias RAM"""
    summary = None
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Selecciona un archivo CSV", "danger")
            return render_template("bulk_upload/ram.html", summary=summary, estados=COMPONENT_STATUS)
        if not file.filename.lower().endswith(".csv"):
            flash("El archivo debe tener formato .csv", "danger")
            return render_template("bulk_upload/ram.html", summary=summary, estados=COMPONENT_STATUS)

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        except UnicodeDecodeError:
            flash("No se pudo decodificar el archivo. Usa UTF-8.", "danger")
            return render_template("bulk_upload/ram.html", summary=summary, estados=COMPONENT_STATUS)

        reader = csv.DictReader(stream)
        db = get_db()
        inserted = 0
        updated = 0
        errors = []

        for row_num, raw_row in enumerate(reader, start=2):
            normalized_row = {}
            for header, value in raw_row.items():
                key = RAM_CSV_FIELDS.get(normalize_header(header))
                if key and value:
                    normalized_row[key] = value.strip()

            serial = normalized_row.get("serial_num")
            if not serial:
                errors.append(f"Fila {row_num}: Serial requerido")
                continue

            # Validar capacidad
            try:
                capacidad = int(normalized_row.get("capacidad_gb", 0))
                if capacidad <= 0:
                    errors.append(f"Fila {row_num}: Capacidad invalida")
                    continue
                normalized_row["capacidad_gb"] = capacidad
            except ValueError:
                errors.append(f"Fila {row_num}: Capacidad debe ser numero")
                continue

            # Validar estado
            estado = normalized_row.get("estado", "POR_ENTREGAR").upper().replace(" ", "_")
            if estado not in COMPONENT_STATUS:
                estado = "POR_ENTREGAR"
            normalized_row["estado"] = estado

            # Velocidad opcional
            if normalized_row.get("velocidad_mhz"):
                try:
                    normalized_row["velocidad_mhz"] = int(normalized_row["velocidad_mhz"])
                except ValueError:
                    normalized_row["velocidad_mhz"] = None

            # Verificar si existe
            existing = RAMUnit.get_by_serial(db, serial)
            if existing:
                RAMUnit.update(db, existing["id"], normalized_row)
                updated += 1
            else:
                RAMUnit.create(db, normalized_row)
                inserted += 1

        summary = {"inserted": inserted, "updated": updated, "total": inserted + updated, "errors": errors}
        if errors:
            flash(f"Carga completada con {len(errors)} errores", "warning")
        else:
            flash("Carga procesada correctamente", "success")

    return render_template("bulk_upload/ram.html", summary=summary, estados=COMPONENT_STATUS)


@bulk_upload_bp.route("/ram/plantilla")
@login_required
@admin_required
def download_ram_template():
    """Descarga plantilla CSV para RAM"""
    template_path = BASE_DIR / "static" / "templates" / "ram_template.csv"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["serial_num", "marca", "capacidad_gb", "tipo", "velocidad_mhz", "estado", "notas"])
        writer.writerow(["RAM001ABC", "Kingston", "16", "DDR4", "3200", "POR_ENTREGAR", "Lote Enero 2025"])
        writer.writerow(["RAM002DEF", "Crucial", "8", "DDR4", "2666", "POR_ASIGNAR", ""])
    return send_from_directory(template_path.parent, template_path.name, as_attachment=True)


# ============================================================================
# CARGA DE SSD
# ============================================================================

SSD_CSV_FIELDS = {
    "serial_num": "serial_num",
    "serial": "serial_num",
    "marca": "marca",
    "brand": "marca",
    "modelo": "modelo",
    "model": "modelo",
    "capacidad_gb": "capacidad_gb",
    "capacidad": "capacidad_gb",
    "gb": "capacidad_gb",
    "tipo": "tipo",
    "type": "tipo",
    "estado": "estado",
    "status": "estado",
    "notas": "notas",
    "notes": "notas",
}


@bulk_upload_bp.route("/ssd", methods=["GET", "POST"])
@login_required
@admin_required
def upload_ssd():
    """Carga masiva de discos SSD"""
    summary = None
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Selecciona un archivo CSV", "danger")
            return render_template("bulk_upload/ssd.html", summary=summary, estados=COMPONENT_STATUS)
        if not file.filename.lower().endswith(".csv"):
            flash("El archivo debe tener formato .csv", "danger")
            return render_template("bulk_upload/ssd.html", summary=summary, estados=COMPONENT_STATUS)

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        except UnicodeDecodeError:
            flash("No se pudo decodificar el archivo. Usa UTF-8.", "danger")
            return render_template("bulk_upload/ssd.html", summary=summary, estados=COMPONENT_STATUS)

        reader = csv.DictReader(stream)
        db = get_db()
        inserted = 0
        updated = 0
        errors = []

        for row_num, raw_row in enumerate(reader, start=2):
            normalized_row = {}
            for header, value in raw_row.items():
                key = SSD_CSV_FIELDS.get(normalize_header(header))
                if key and value:
                    normalized_row[key] = value.strip()

            serial = normalized_row.get("serial_num")
            if not serial:
                errors.append(f"Fila {row_num}: Serial requerido")
                continue

            # Validar capacidad
            try:
                capacidad = int(normalized_row.get("capacidad_gb", 0))
                if capacidad <= 0:
                    errors.append(f"Fila {row_num}: Capacidad invalida")
                    continue
                normalized_row["capacidad_gb"] = capacidad
            except ValueError:
                errors.append(f"Fila {row_num}: Capacidad debe ser numero")
                continue

            # Validar estado
            estado = normalized_row.get("estado", "POR_ENTREGAR").upper().replace(" ", "_")
            if estado not in COMPONENT_STATUS:
                estado = "POR_ENTREGAR"
            normalized_row["estado"] = estado

            # Verificar si existe
            existing = SSDUnit.get_by_serial(db, serial)
            if existing:
                SSDUnit.update(db, existing["id"], normalized_row)
                updated += 1
            else:
                SSDUnit.create(db, normalized_row)
                inserted += 1

        summary = {"inserted": inserted, "updated": updated, "total": inserted + updated, "errors": errors}
        if errors:
            flash(f"Carga completada con {len(errors)} errores", "warning")
        else:
            flash("Carga procesada correctamente", "success")

    return render_template("bulk_upload/ssd.html", summary=summary, estados=COMPONENT_STATUS)


@bulk_upload_bp.route("/ssd/plantilla")
@login_required
@admin_required
def download_ssd_template():
    """Descarga plantilla CSV para SSD"""
    template_path = BASE_DIR / "static" / "templates" / "ssd_template.csv"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["serial_num", "marca", "modelo", "capacidad_gb", "tipo", "estado", "notas"])
        writer.writerow(["SSD001ABC", "Samsung", "870 EVO", "500", "SATA", "POR_ENTREGAR", "Lote Enero 2025"])
        writer.writerow(["SSD002DEF", "Kingston", "A400", "480", "SATA", "POR_ASIGNAR", ""])
    return send_from_directory(template_path.parent, template_path.name, as_attachment=True)


# ============================================================================
# CARGA DE REPOTENCIACION
# ============================================================================

REPOT_CSV_FIELDS = {
    "equipo_serial": "equipo_serial",
    "serial_equipo": "equipo_serial",
    "equipo_hostname": "equipo_hostname",
    "hostname": "equipo_hostname",
    "fecha_repotenciacion": "fecha_repotenciacion",
    "fecha": "fecha_repotenciacion",
    "ram_antes_gb": "ram_antes_gb",
    "ram_antes_tipo": "ram_antes_tipo",
    "ram_antes_serial": "ram_antes_serial",
    "ram_despues_gb": "ram_despues_gb",
    "ram_despues_tipo": "ram_despues_tipo",
    "ram_despues_serial": "ram_despues_serial",
    "disco_antes_tipo": "disco_antes_tipo",
    "disco_antes_capacidad_gb": "disco_antes_capacidad_gb",
    "disco_antes_serial": "disco_antes_serial",
    "disco_despues_tipo": "disco_despues_tipo",
    "disco_despues_capacidad_gb": "disco_despues_capacidad_gb",
    "disco_despues_serial": "disco_despues_serial",
    "ram_extraida_serial": "ram_extraida_serial",
    "ram_extraida_estado": "ram_extraida_estado",
    "disco_extraido_serial": "disco_extraido_serial",
    "disco_extraido_estado": "disco_extraido_estado",
    "disco_extraido_destruido": "disco_extraido_destruido",
    "tecnico": "tecnico",
    "notas": "notas",
}


@bulk_upload_bp.route("/repotenciacion", methods=["GET", "POST"])
@login_required
@admin_required
def upload_repotentiation():
    """Carga masiva de historial de repotenciacion"""
    summary = None
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Selecciona un archivo CSV", "danger")
            return render_template("bulk_upload/repotenciacion.html", summary=summary)
        if not file.filename.lower().endswith(".csv"):
            flash("El archivo debe tener formato .csv", "danger")
            return render_template("bulk_upload/repotenciacion.html", summary=summary)

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        except UnicodeDecodeError:
            flash("No se pudo decodificar el archivo. Usa UTF-8.", "danger")
            return render_template("bulk_upload/repotenciacion.html", summary=summary)

        reader = csv.DictReader(stream)
        db = get_db()
        inserted = 0
        errors = []

        for row_num, raw_row in enumerate(reader, start=2):
            normalized_row = {}
            for header, value in raw_row.items():
                key = REPOT_CSV_FIELDS.get(normalize_header(header))
                if key and value:
                    normalized_row[key] = value.strip()

            equipo_serial = normalized_row.get("equipo_serial")
            if not equipo_serial:
                errors.append(f"Fila {row_num}: Serial de equipo requerido")
                continue

            fecha = normalized_row.get("fecha_repotenciacion")
            if not fecha:
                errors.append(f"Fila {row_num}: Fecha de repotenciacion requerida")
                continue

            # Normalizar fecha
            normalized_row["fecha_repotenciacion"] = normalize_date(fecha)

            # Convertir campos numericos
            for field in ["ram_antes_gb", "ram_despues_gb", "disco_antes_capacidad_gb", "disco_despues_capacidad_gb"]:
                if normalized_row.get(field):
                    try:
                        normalized_row[field] = int(normalized_row[field])
                    except ValueError:
                        normalized_row[field] = None

            # Campo booleano
            destruido = normalized_row.get("disco_extraido_destruido", "").upper()
            normalized_row["disco_extraido_destruido"] = 1 if destruido in ("1", "SI", "YES", "TRUE") else 0

            RepotentiationRecord.create(db, normalized_row)
            inserted += 1

        summary = {"inserted": inserted, "total": inserted, "errors": errors}
        if errors:
            flash(f"Carga completada con {len(errors)} errores", "warning")
        else:
            flash("Carga procesada correctamente", "success")

    return render_template("bulk_upload/repotenciacion.html", summary=summary)


@bulk_upload_bp.route("/repotenciacion/plantilla")
@login_required
@admin_required
def download_repotentiation_template():
    """Descarga plantilla CSV para repotenciacion"""
    template_path = BASE_DIR / "static" / "templates" / "repotenciacion_template.csv"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "equipo_serial", "equipo_hostname", "fecha_repotenciacion",
            "ram_antes_gb", "ram_antes_tipo", "ram_antes_serial",
            "ram_despues_gb", "ram_despues_tipo", "ram_despues_serial",
            "disco_antes_tipo", "disco_antes_capacidad_gb", "disco_antes_serial",
            "disco_despues_tipo", "disco_despues_capacidad_gb", "disco_despues_serial",
            "ram_extraida_serial", "ram_extraida_estado",
            "disco_extraido_serial", "disco_extraido_estado", "disco_extraido_destruido",
            "tecnico", "notas"
        ])
        writer.writerow([
            "5CD3051HBZ", "BANCAINMOBIOP01", "2025-01-15",
            "8", "DDR4", "RAM-OLD-001",
            "16", "DDR4", "RAM-NEW-001",
            "HDD", "500", "HDD-OLD-001",
            "SSD", "500", "SSD-NEW-001",
            "RAM-OLD-001", "FUNCIONAL",
            "HDD-OLD-001", "PARA_DESTRUIR", "NO",
            "Juan Perez", "Repotenciacion completada"
        ])
    return send_from_directory(template_path.parent, template_path.name, as_attachment=True)


# ============================================================================
# CARGA DE DESTRUCCION
# ============================================================================

DESTRUCTION_CSV_FIELDS = {
    "disco_serial": "disco_serial",
    "serial_disco": "disco_serial",
    "serial": "disco_serial",
    "disco_marca": "disco_marca",
    "marca": "disco_marca",
    "disco_modelo": "disco_modelo",
    "modelo": "disco_modelo",
    "disco_capacidad_gb": "disco_capacidad_gb",
    "capacidad_gb": "disco_capacidad_gb",
    "capacidad": "disco_capacidad_gb",
    "disco_tipo": "disco_tipo",
    "tipo": "disco_tipo",
    "equipo_origen_serial": "equipo_origen_serial",
    "serial_equipo": "equipo_origen_serial",
    "equipo_origen_hostname": "equipo_origen_hostname",
    "hostname": "equipo_origen_hostname",
    "estado": "estado",
    "fecha_extraccion": "fecha_extraccion",
    "fecha_destruccion": "fecha_destruccion",
    "metodo_destruccion": "metodo_destruccion",
    "metodo": "metodo_destruccion",
    "certificado_numero": "certificado_numero",
    "certificado": "certificado_numero",
    "certificado_fecha": "certificado_fecha",
    "responsable": "responsable",
    "notas": "notas",
}


@bulk_upload_bp.route("/destruccion", methods=["GET", "POST"])
@login_required
@admin_required
def upload_destruction():
    """Carga masiva de registros de destruccion"""
    summary = None
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Selecciona un archivo CSV", "danger")
            return render_template("bulk_upload/destruccion.html", summary=summary, estados=DESTRUCTION_STATUS)
        if not file.filename.lower().endswith(".csv"):
            flash("El archivo debe tener formato .csv", "danger")
            return render_template("bulk_upload/destruccion.html", summary=summary, estados=DESTRUCTION_STATUS)

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        except UnicodeDecodeError:
            flash("No se pudo decodificar el archivo. Usa UTF-8.", "danger")
            return render_template("bulk_upload/destruccion.html", summary=summary, estados=DESTRUCTION_STATUS)

        reader = csv.DictReader(stream)
        db = get_db()
        inserted = 0
        updated = 0
        errors = []

        for row_num, raw_row in enumerate(reader, start=2):
            normalized_row = {}
            for header, value in raw_row.items():
                key = DESTRUCTION_CSV_FIELDS.get(normalize_header(header))
                if key and value:
                    normalized_row[key] = value.strip()

            disco_serial = normalized_row.get("disco_serial")
            if not disco_serial:
                errors.append(f"Fila {row_num}: Serial de disco requerido")
                continue

            # Validar estado
            estado = normalized_row.get("estado", "PENDIENTE").upper().replace(" ", "_")
            if estado not in DESTRUCTION_STATUS:
                estado = "PENDIENTE"
            normalized_row["estado"] = estado

            # Convertir capacidad
            if normalized_row.get("disco_capacidad_gb"):
                try:
                    normalized_row["disco_capacidad_gb"] = int(normalized_row["disco_capacidad_gb"])
                except ValueError:
                    normalized_row["disco_capacidad_gb"] = None

            # Normalizar fechas
            for field in ["fecha_extraccion", "fecha_destruccion", "certificado_fecha"]:
                if normalized_row.get(field):
                    normalized_row[field] = normalize_date(normalized_row[field])

            # Verificar si existe
            existing = DiskDestruction.get_by_serial(db, disco_serial)
            if existing:
                DiskDestruction.update(db, existing["id"], normalized_row)
                updated += 1
            else:
                DiskDestruction.create(db, normalized_row)
                inserted += 1

        summary = {"inserted": inserted, "updated": updated, "total": inserted + updated, "errors": errors}
        if errors:
            flash(f"Carga completada con {len(errors)} errores", "warning")
        else:
            flash("Carga procesada correctamente", "success")

    return render_template("bulk_upload/destruccion.html", summary=summary, estados=DESTRUCTION_STATUS)


@bulk_upload_bp.route("/destruccion/plantilla")
@login_required
@admin_required
def download_destruction_template():
    """Descarga plantilla CSV para destruccion"""
    template_path = BASE_DIR / "static" / "templates" / "destruccion_template.csv"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "disco_serial", "disco_marca", "disco_modelo", "disco_capacidad_gb", "disco_tipo",
            "equipo_origen_serial", "equipo_origen_hostname",
            "estado", "fecha_extraccion", "fecha_destruccion", "metodo_destruccion",
            "certificado_numero", "certificado_fecha", "responsable", "notas"
        ])
        writer.writerow([
            "HDD-001-ABC", "Seagate", "Barracuda", "500", "HDD",
            "5CD3051HBZ", "BANCAINMOBIOP01",
            "PENDIENTE", "2025-01-15", "", "",
            "", "", "Juan Perez", "Disco extraido de repotenciacion"
        ])
    return send_from_directory(template_path.parent, template_path.name, as_attachment=True)
