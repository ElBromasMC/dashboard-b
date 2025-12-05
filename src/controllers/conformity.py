import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, send_file, abort

from config import MAX_ACTA_SIZE
from models.database import get_db
from models.conformity import ConformityRecord, UPLOADS_DIR
from utils.decorators import login_required, admin_required

conformity_bp = Blueprint('conformity', __name__, url_prefix='/actas')


@conformity_bp.route("/")
@login_required
def index():
    """Vista principal de actas de conformidad"""
    db = get_db()
    equipo_filter = request.args.get("equipo", "").strip()
    records = ConformityRecord.get_all(db, equipo_serial=equipo_filter if equipo_filter else None)
    summary = ConformityRecord.get_summary(db)
    return render_template(
        "conformity/index.html",
        records=records,
        summary=summary,
        equipo_filter=equipo_filter,
    )


@conformity_bp.route("/subir", methods=["GET", "POST"])
@login_required
@admin_required
def upload():
    """Subir nueva acta de conformidad"""
    db = get_db()

    # Obtener lista de equipos para el selector
    equipos = db.execute("""
        SELECT serial_num, hostname, nombre_completo
        FROM project_records
        WHERE serial_num IS NOT NULL AND serial_num != ''
        ORDER BY hostname
    """).fetchall()

    if request.method == "POST":
        equipo_serial = request.form.get("equipo_serial", "").strip()
        notas = request.form.get("notas", "").strip()
        file = request.files.get("archivo")

        if not equipo_serial:
            flash("Debes seleccionar un equipo", "danger")
            return render_template("conformity/upload.html", equipos=equipos)

        if not file or not file.filename:
            flash("Debes seleccionar un archivo", "danger")
            return render_template("conformity/upload.html", equipos=equipos)

        # Validar tamaño del archivo (50MB max)
        file.seek(0, 2)  # Ir al final
        file_size = file.tell()
        file.seek(0)  # Volver al inicio
        if file_size > MAX_ACTA_SIZE:
            flash(f"El archivo excede el limite de 50MB (tamaño: {file_size // (1024*1024)}MB)", "danger")
            return render_template("conformity/upload.html", equipos=equipos)

        # Obtener datos del equipo
        equipo = db.execute("""
            SELECT serial_num, hostname, nombre_completo
            FROM project_records WHERE serial_num = ?
        """, (equipo_serial,)).fetchone()

        if not equipo:
            flash("Equipo no encontrado", "danger")
            return render_template("conformity/upload.html", equipos=equipos)

        # Guardar archivo
        safe_name, file_path, file_type = ConformityRecord.save_file(file, equipo_serial)

        if not safe_name:
            flash("Tipo de archivo no permitido. Solo se aceptan PDF y MSG.", "danger")
            return render_template("conformity/upload.html", equipos=equipos)

        # Crear registro
        ConformityRecord.create(db, {
            "equipo_serial": equipo_serial,
            "equipo_hostname": equipo["hostname"],
            "usuario_nombre": equipo["nombre_completo"],
            "tipo_archivo": file_type,
            "nombre_archivo": safe_name,
            "ruta_archivo": file_path,
            "subido_por": g.user["username"] if g.user else None,
            "notas": notas,
        })

        flash(f"Acta de conformidad subida correctamente para {equipo['hostname']}", "success")
        return redirect(url_for("conformity.index"))

    return render_template("conformity/upload.html", equipos=equipos)


@conformity_bp.route("/ver/<int:id>")
@login_required
def view(id):
    """Ver/descargar acta de conformidad"""
    db = get_db()
    record = ConformityRecord.get_by_id(db, id)

    if not record:
        flash("Acta no encontrada", "danger")
        return redirect(url_for("conformity.index"))

    file_path = record["ruta_archivo"]
    if not os.path.exists(file_path):
        flash("El archivo no existe en el servidor", "danger")
        return redirect(url_for("conformity.index"))

    # Para PDF, mostrar en el navegador; para MSG, descargar
    if record["tipo_archivo"] == "PDF":
        return send_file(file_path, mimetype='application/pdf')
    else:
        return send_file(file_path, as_attachment=True, download_name=record["nombre_archivo"])


@conformity_bp.route("/descargar/<int:id>")
@login_required
def download(id):
    """Descargar acta de conformidad"""
    db = get_db()
    record = ConformityRecord.get_by_id(db, id)

    if not record:
        flash("Acta no encontrada", "danger")
        return redirect(url_for("conformity.index"))

    file_path = record["ruta_archivo"]
    if not os.path.exists(file_path):
        flash("El archivo no existe en el servidor", "danger")
        return redirect(url_for("conformity.index"))

    return send_file(file_path, as_attachment=True, download_name=record["nombre_archivo"])


@conformity_bp.route("/eliminar/<int:id>", methods=["POST"])
@login_required
@admin_required
def delete(id):
    """Eliminar acta de conformidad"""
    db = get_db()
    if ConformityRecord.delete(db, id):
        flash("Acta eliminada correctamente", "success")
    else:
        flash("No se pudo eliminar el acta", "danger")
    return redirect(url_for("conformity.index"))


@conformity_bp.route("/equipo/<serial>")
@login_required
def by_equipment(serial):
    """Ver actas de un equipo específico"""
    db = get_db()
    records = ConformityRecord.get_by_equipment(db, serial)

    equipo = db.execute("""
        SELECT serial_num, hostname, nombre_completo
        FROM project_records WHERE serial_num = ?
    """, (serial,)).fetchone()

    return render_template(
        "conformity/equipment.html",
        records=records,
        equipo=equipo,
        serial=serial,
    )


# API Endpoints
@conformity_bp.route("/api/summary")
@login_required
def api_summary():
    """Resumen de actas para el dashboard"""
    db = get_db()
    summary = ConformityRecord.get_summary(db)
    return jsonify(summary)


@conformity_bp.route("/api/equipo/<serial>")
@login_required
def api_by_equipment(serial):
    """API para obtener actas de un equipo"""
    db = get_db()
    records = ConformityRecord.get_by_equipment(db, serial)
    return jsonify([dict(r) for r in records])
