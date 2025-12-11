import csv
import io
from datetime import datetime
from flask import Blueprint, render_template, request, Response, jsonify

from models.database import get_db
from models.project import ProjectRecord
from models.component import RAMUnit, SSDUnit, ComponentHistory, COMPONENT_STATUS
from models.repotentiation import RepotentiationRecord
from models.destruction import DiskDestruction, DESTRUCTION_STATUS
from config import PROJECT_PHASES, get_phase_from_category
from utils.decorators import login_required, admin_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reportes')


@reports_bp.route("/")
@login_required
def index():
    """Vista principal de reportes"""
    db = get_db()

    # Resumen de componentes
    ram_summary = RAMUnit.get_summary(db)
    ssd_summary = SSDUnit.get_summary(db)
    repot_summary = RepotentiationRecord.get_summary(db)
    destruction_summary = DiskDestruction.get_summary(db)

    # Conteo por fase
    records = ProjectRecord.query_records(db, {})
    phase_counts = {}
    for record in records:
        fase = get_phase_from_category(record["categoria_trab"])
        if fase:
            phase_counts[fase] = phase_counts.get(fase, 0) + 1

    return render_template(
        "reports/index.html",
        ram_summary=ram_summary,
        ssd_summary=ssd_summary,
        repot_summary=repot_summary,
        destruction_summary=destruction_summary,
        phase_counts=phase_counts,
        project_phases=PROJECT_PHASES,
        component_status=COMPONENT_STATUS,
        destruction_status=DESTRUCTION_STATUS,
    )


@reports_bp.route("/exportar/dashboard")
@login_required
def export_dashboard():
    """Exporta datos del dashboard a CSV"""
    db = get_db()

    # Obtener filtros de la URL
    filters = {
        "ubicacion": request.args.get("ubicacion", "").strip() or None,
        "nom_sede": request.args.get("nom_sede", "").strip() or None,
        "categoria_trab": request.args.get("categoria_trab", "").strip() or None,
        "estado": request.args.get("estado", "").strip() or None,
        "fecha_inicio": request.args.get("fecha_inicio", "").strip() or None,
        "fecha_fin": request.args.get("fecha_fin", "").strip() or None,
        "nombre": request.args.get("nombre", "").strip() or None,
        "hostname": request.args.get("hostname", "").strip() or None,
        "fase": request.args.get("fase", "").strip() or None,
    }

    records = ProjectRecord.query_records(db, filters)

    # Generar CSV
    output = io.StringIO()
    writer = csv.writer(output)

    # Encabezados
    headers = [
        "ID", "Ubicacion", "Sede", "Categoria", "Fase", "Nombre Completo",
        "Perfil", "Marca", "Modelo", "Serial", "Hostname", "IP",
        "Email", "Fecha Estado", "Estado", "Estado Coordinacion",
        "Estado Upgrade", "Fecha Programada", "Fecha Ejecucion", "Notas"
    ]
    writer.writerow(headers)

    # Datos
    for r in records:
        fase = get_phase_from_category(r["categoria_trab"])
        fase_nombre = PROJECT_PHASES.get(fase, {}).get("nombre", "-") if fase else "-"
        writer.writerow([
            r["record_id"],
            r["ubicacion"],
            r["nom_sede"],
            r["categoria_trab"],
            fase_nombre,
            r["nombre_completo"],
            r["perfil_imagen"],
            r["marca"],
            r["modelo"],
            r["serial_num"],
            r["hostname"],
            r["ip_equipo"],
            r["email_trabajo"],
            r["fecha_estado"],
            r["estado"],
            r["estado_coordinacion"],
            r["estado_upgrade"],
            r["fecha_programada"],
            r["fecha_ejecucion"],
            r["notas"],
        ])

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"dashboard_export_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@reports_bp.route("/exportar/ram")
@login_required
def export_ram():
    """Exporta inventario de RAM a CSV"""
    db = get_db()
    estado = request.args.get("estado", "").strip() or None
    units = RAMUnit.get_all(db, estado)

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "ID", "Serial", "Marca", "Capacidad (GB)", "Tipo", "Velocidad (MHz)",
        "Estado", "Equipo Serial", "Fecha Instalacion", "Fecha Registro", "Notas"
    ]
    writer.writerow(headers)

    for u in units:
        estado_label = COMPONENT_STATUS.get(u["estado"], u["estado"])
        writer.writerow([
            u["id"],
            u["serial_num"],
            u["marca"],
            u["capacidad_gb"],
            u["tipo"],
            u["velocidad_mhz"],
            estado_label,
            u["equipo_serial"],
            u["fecha_instalacion"],
            u["fecha_registro"],
            u["notas"],
        ])

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"inventario_ram_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@reports_bp.route("/exportar/ssd")
@login_required
def export_ssd():
    """Exporta inventario de SSD a CSV"""
    db = get_db()
    estado = request.args.get("estado", "").strip() or None
    units = SSDUnit.get_all(db, estado)

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "ID", "Serial", "Marca", "Modelo", "Capacidad (GB)", "Tipo",
        "Estado", "Equipo Serial", "Fecha Instalacion", "Fecha Registro", "Notas"
    ]
    writer.writerow(headers)

    for u in units:
        estado_label = COMPONENT_STATUS.get(u["estado"], u["estado"])
        writer.writerow([
            u["id"],
            u["serial_num"],
            u["marca"],
            u["modelo"],
            u["capacidad_gb"],
            u["tipo"],
            estado_label,
            u["equipo_serial"],
            u["fecha_instalacion"],
            u["fecha_registro"],
            u["notas"],
        ])

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"inventario_ssd_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@reports_bp.route("/exportar/repotenciacion")
@login_required
def export_repotentiation():
    """Exporta historial de repotenciación a CSV"""
    db = get_db()
    records = RepotentiationRecord.get_all(db)

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "ID", "Equipo Serial", "Equipo Hostname", "Usuario", "Fecha Repotenciacion",
        "RAM Antes (GB)", "RAM Antes Tipo", "RAM Antes Serial",
        "RAM Despues (GB)", "RAM Despues Tipo", "RAM Despues Serial",
        "Disco Antes Tipo", "Disco Antes (GB)", "Disco Antes Serial",
        "Disco Despues Tipo", "Disco Despues (GB)", "Disco Despues Serial",
        "RAM Extraida Serial", "RAM Extraida Estado",
        "Disco Extraido Serial", "Disco Extraido Estado", "Disco Destruido",
        "Tecnico", "Notas"
    ]
    writer.writerow(headers)

    for r in records:
        writer.writerow([
            r["id"],
            r["equipo_serial"],
            r["equipo_hostname"],
            r["nombre_completo"],
            r["fecha_repotenciacion"],
            r["ram_antes_gb"],
            r["ram_antes_tipo"],
            r["ram_antes_serial"],
            r["ram_despues_gb"],
            r["ram_despues_tipo"],
            r["ram_despues_serial"],
            r["disco_antes_tipo"],
            r["disco_antes_capacidad_gb"],
            r["disco_antes_serial"],
            r["disco_despues_tipo"],
            r["disco_despues_capacidad_gb"],
            r["disco_despues_serial"],
            r["ram_extraida_serial"],
            r["ram_extraida_estado"],
            r["disco_extraido_serial"],
            r["disco_extraido_estado"],
            "Si" if r["disco_extraido_destruido"] else "No",
            r["tecnico"],
            r["notas"],
        ])

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"repotenciacion_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@reports_bp.route("/exportar/destruccion")
@login_required
def export_destruction():
    """Exporta registros de destrucción a CSV"""
    db = get_db()
    estado = request.args.get("estado", "").strip() or None
    records = DiskDestruction.get_all(db, estado)

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "ID", "Disco Serial", "Disco Marca", "Disco Modelo", "Capacidad (GB)",
        "Tipo Disco", "Equipo Origen Serial", "Equipo Origen Hostname", "Usuario",
        "Estado", "Fecha Extraccion", "Fecha Destruccion", "Metodo Destruccion",
        "Tiene Video", "Certificado Numero", "Certificado Fecha",
        "Responsable", "Notas"
    ]
    writer.writerow(headers)

    for r in records:
        estado_label = DESTRUCTION_STATUS.get(r["estado"], r["estado"])
        writer.writerow([
            r["id"],
            r["disco_serial"],
            r["disco_marca"],
            r["disco_modelo"],
            r["disco_capacidad_gb"],
            r["disco_tipo"],
            r["equipo_origen_serial"],
            r["equipo_origen_hostname"],
            r["nombre_completo"],
            estado_label,
            r["fecha_extraccion"],
            r["fecha_destruccion"],
            r["metodo_destruccion"],
            "Si" if r["video_ruta"] else "No",
            r["certificado_numero"],
            r["certificado_fecha"],
            r["responsable"],
            r["notas"],
        ])

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"destruccion_discos_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@reports_bp.route("/exportar/historial-componentes")
@login_required
def export_component_history():
    """Exporta historial de movimientos de componentes"""
    db = get_db()
    limit = request.args.get("limit", 500, type=int)
    records = ComponentHistory.get_recent(db, limit)

    output = io.StringIO()
    writer = csv.writer(output)

    headers = [
        "ID", "Tipo Componente", "Componente ID", "Componente Serial",
        "Accion", "Equipo Serial Anterior", "Equipo Serial Nuevo",
        "Estado Anterior", "Estado Nuevo", "Capacidad Anterior (GB)",
        "Capacidad Nueva (GB)", "Usuario", "Fecha", "Notas"
    ]
    writer.writerow(headers)

    for r in records:
        writer.writerow([
            r["id"],
            r["tipo_componente"],
            r["componente_id"],
            r["componente_serial"],
            r["accion"],
            r["equipo_serial_anterior"],
            r["equipo_serial_nuevo"],
            r["estado_anterior"],
            r["estado_nuevo"],
            r["capacidad_anterior_gb"],
            r["capacidad_nueva_gb"],
            r["usuario"],
            r["fecha"],
            r["notas"],
        ])

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"historial_componentes_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================================================
# RAW DATABASE TABLES VIEWER
# ============================================================================

@reports_bp.route("/tablas")
@login_required
@admin_required
def raw_tables():
    """Vista principal de tablas de base de datos"""
    db = get_db()

    # Obtener lista de tablas
    tables = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()

    table_info = []
    for t in tables:
        table_name = t["name"]
        count = db.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()["count"]
        table_info.append({
            "name": table_name,
            "count": count
        })

    return render_template("reports/tables.html", tables=table_info)


@reports_bp.route("/tablas/<table_name>")
@login_required
@admin_required
def view_table(table_name):
    """Muestra el contenido de una tabla específica"""
    db = get_db()

    # Validar que la tabla existe (prevenir SQL injection)
    valid_tables = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """).fetchall()
    valid_table_names = [t["name"] for t in valid_tables]

    if table_name not in valid_table_names:
        from flask import abort
        abort(404)

    # Obtener información de columnas
    columns_info = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    columns = [col["name"] for col in columns_info]

    # Paginación
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    per_page = min(per_page, 200)  # Máximo 200 registros por página
    offset = (page - 1) * per_page

    # Obtener total de registros
    total = db.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()["count"]
    total_pages = (total + per_page - 1) // per_page

    # Obtener registros
    rows = db.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (per_page, offset)).fetchall()

    # Convertir a lista de diccionarios
    records = [dict(row) for row in rows]

    return render_template(
        "reports/table_view.html",
        table_name=table_name,
        columns=columns,
        records=records,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        valid_tables=valid_table_names
    )


@reports_bp.route("/tablas/<table_name>/exportar")
@login_required
@admin_required
def export_raw_table(table_name):
    """Exporta una tabla completa a CSV"""
    db = get_db()

    # Validar tabla
    valid_tables = db.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """).fetchall()
    valid_table_names = [t["name"] for t in valid_tables]

    if table_name not in valid_table_names:
        from flask import abort
        abort(404)

    # Obtener columnas
    columns_info = db.execute(f"PRAGMA table_info({table_name})").fetchall()
    columns = [col["name"] for col in columns_info]

    # Obtener todos los registros
    rows = db.execute(f"SELECT * FROM {table_name}").fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)

    for row in rows:
        writer.writerow([row[col] for col in columns])

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{table_name}_{timestamp}.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
