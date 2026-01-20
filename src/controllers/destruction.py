import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g, send_file

from config import MAX_ACTA_SIZE
from models.database import get_db
from models.destruction import DiskDestruction, DESTRUCTION_STATUS, INFORMES_DIR
from utils.decorators import login_required, admin_required

destruction_bp = Blueprint('destruction', __name__, url_prefix='/destruccion')


@destruction_bp.route("/")
@login_required
def index():
    """Vista principal del panel de destrucción de discos"""
    db = get_db()
    estado_filter = request.args.get("estado", "").strip()

    records = DiskDestruction.get_all(db, estado=estado_filter if estado_filter else None)
    summary = DiskDestruction.get_summary(db)

    return render_template(
        "destruction/index.html",
        records=records,
        summary=summary,
        status_options=DESTRUCTION_STATUS,
        estado_filter=estado_filter,
    )


@destruction_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    """Registrar nuevo disco para destrucción"""
    db = get_db()

    if request.method == "POST":
        data = {
            "disco_serial": request.form.get("disco_serial", "").strip(),
            "disco_marca": request.form.get("disco_marca", "").strip() or None,
            "disco_modelo": request.form.get("disco_modelo", "").strip() or None,
            "disco_capacidad_gb": int(request.form.get("disco_capacidad_gb") or 0) or None,
            "disco_tipo": request.form.get("disco_tipo", "").strip() or None,
            "equipo_origen_serial": request.form.get("equipo_origen_serial", "").strip() or None,
            "equipo_origen_hostname": request.form.get("equipo_origen_hostname", "").strip() or None,
            "sede": request.form.get("sede", "").strip() or None,
            "estado": request.form.get("estado", "PENDIENTE"),
            "fecha_extraccion": request.form.get("fecha_extraccion", "").strip() or None,
            "video_url": request.form.get("video_url", "").strip() or None,
            "responsable": request.form.get("responsable", "").strip() or g.user["username"],
            "notas": request.form.get("notas", "").strip() or None,
        }

        if not data["disco_serial"]:
            flash("El serial del disco es obligatorio", "danger")
            return render_template("destruction/form.html", data=data, status_options=DESTRUCTION_STATUS)

        existing = DiskDestruction.get_by_serial(db, data["disco_serial"])
        if existing:
            flash("Ya existe un registro para este disco", "danger")
            return render_template("destruction/form.html", data=data, status_options=DESTRUCTION_STATUS)

        DiskDestruction.create(db, data)
        flash("Disco registrado para destrucción", "success")
        return redirect(url_for("destruction.index"))

    return render_template("destruction/form.html", data={}, status_options=DESTRUCTION_STATUS)


@destruction_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def edit(id):
    """Editar registro de destrucción"""
    db = get_db()
    record = DiskDestruction.get_by_id(db, id)

    if not record:
        flash("Registro no encontrado", "danger")
        return redirect(url_for("destruction.index"))

    if request.method == "POST":
        data = {
            "disco_marca": request.form.get("disco_marca", "").strip() or None,
            "disco_modelo": request.form.get("disco_modelo", "").strip() or None,
            "disco_capacidad_gb": int(request.form.get("disco_capacidad_gb") or 0) or None,
            "disco_tipo": request.form.get("disco_tipo", "").strip() or None,
            "sede": request.form.get("sede", "").strip() or None,
            "estado": request.form.get("estado", record["estado"]),
            "fecha_extraccion": request.form.get("fecha_extraccion", "").strip() or None,
            "fecha_destruccion": request.form.get("fecha_destruccion", "").strip() or None,
            "metodo_destruccion": request.form.get("metodo_destruccion", "").strip() or None,
            "video_url": request.form.get("video_url", "").strip() or None,
            "informe_nombre": record["informe_nombre"] if record["informe_nombre"] else None,
            "informe_ruta": record["informe_ruta"] if record["informe_ruta"] else None,
            "certificado_numero": request.form.get("certificado_numero", "").strip() or None,
            "certificado_fecha": request.form.get("certificado_fecha", "").strip() or None,
            "responsable": request.form.get("responsable", "").strip() or None,
            "notas": request.form.get("notas", "").strip() or None,
        }

        # Procesar informe PDF si se subió uno nuevo
        informe = request.files.get("informe")
        if informe and informe.filename:
            # Validar tamaño del informe (50MB max)
            informe.seek(0, 2)
            informe_size = informe.tell()
            informe.seek(0)
            if informe_size > MAX_ACTA_SIZE:
                flash(f"El informe excede el límite de 50MB (tamaño: {informe_size // (1024*1024)}MB)", "warning")
            else:
                informe_name, informe_path = DiskDestruction.save_informe(informe, record["disco_serial"])
                if informe_name:
                    # Eliminar informe anterior si existe
                    if record["informe_ruta"]:
                        try:
                            old_path = record["informe_ruta"]
                            if os.path.exists(old_path):
                                os.unlink(old_path)
                        except Exception:
                            pass
                    data["informe_nombre"] = informe_name
                    data["informe_ruta"] = informe_path
                else:
                    flash("Tipo de archivo no permitido. Solo se permiten archivos PDF.", "warning")

        DiskDestruction.update(db, id, data)
        flash("Registro actualizado correctamente", "success")
        return redirect(url_for("destruction.index"))

    return render_template("destruction/form.html", data=dict(record), status_options=DESTRUCTION_STATUS, editing=True)


@destruction_bp.route("/<int:id>/informe", methods=["POST"])
@login_required
@admin_required
def upload_informe(id):
    """Subir informe de destrucción (PDF)"""
    db = get_db()
    record = DiskDestruction.get_by_id(db, id)

    if not record:
        flash("Registro no encontrado", "danger")
        return redirect(url_for("destruction.index"))

    informe = request.files.get("informe")
    if not informe or not informe.filename:
        flash("Debes seleccionar un archivo PDF", "danger")
        return redirect(url_for("destruction.edit", id=id))

    # Validar tamaño del informe (50MB max)
    informe.seek(0, 2)
    informe_size = informe.tell()
    informe.seek(0)
    if informe_size > MAX_ACTA_SIZE:
        flash(f"El informe excede el límite de 50MB (tamaño: {informe_size // (1024*1024)}MB)", "danger")
        return redirect(url_for("destruction.edit", id=id))

    informe_name, informe_path = DiskDestruction.save_informe(informe, record["disco_serial"])

    if not informe_name:
        flash("Tipo de archivo no permitido. Solo se permiten archivos PDF.", "danger")
        return redirect(url_for("destruction.edit", id=id))

    # Eliminar informe anterior si existe
    if record["informe_ruta"]:
        try:
            if os.path.exists(record["informe_ruta"]):
                os.unlink(record["informe_ruta"])
        except Exception:
            pass

    # Actualizar registro
    data = dict(record)
    data["informe_nombre"] = informe_name
    data["informe_ruta"] = informe_path
    DiskDestruction.update(db, id, data)

    flash("Informe de destrucción subido correctamente", "success")
    return redirect(url_for("destruction.index"))


@destruction_bp.route("/<int:id>/ver-informe")
@login_required
def view_informe(id):
    """Ver informe de destrucción (PDF)"""
    db = get_db()
    record = DiskDestruction.get_by_id(db, id)

    if not record or not record["informe_ruta"]:
        flash("Informe no encontrado", "danger")
        return redirect(url_for("destruction.index"))

    if not os.path.exists(record["informe_ruta"]):
        flash("El archivo de informe no existe en el servidor", "danger")
        return redirect(url_for("destruction.index"))

    return send_file(record["informe_ruta"])


@destruction_bp.route("/<int:id>/eliminar", methods=["POST"])
@login_required
@admin_required
def delete(id):
    """Eliminar registro de destrucción"""
    db = get_db()
    DiskDestruction.delete(db, id)
    flash("Registro eliminado", "success")
    return redirect(url_for("destruction.index"))


@destruction_bp.route("/<int:id>/certificar", methods=["POST"])
@login_required
@admin_required
def certify(id):
    """Marcar disco como certificado"""
    db = get_db()
    record = DiskDestruction.get_by_id(db, id)

    if not record:
        flash("Registro no encontrado", "danger")
        return redirect(url_for("destruction.index"))

    cert_numero = request.form.get("certificado_numero", "").strip()
    cert_fecha = request.form.get("certificado_fecha", "").strip()

    from datetime import datetime
    data = {
        "disco_marca": record["disco_marca"],
        "disco_modelo": record["disco_modelo"],
        "disco_capacidad_gb": record["disco_capacidad_gb"],
        "disco_tipo": record["disco_tipo"],
        "sede": record["sede"] if record["sede"] else None,
        "estado": "CERTIFICADO",
        "fecha_extraccion": record["fecha_extraccion"],
        "fecha_destruccion": record["fecha_destruccion"],
        "metodo_destruccion": record["metodo_destruccion"],
        "video_url": record["video_url"] if record["video_url"] else None,
        "informe_nombre": record["informe_nombre"] if record["informe_nombre"] else None,
        "informe_ruta": record["informe_ruta"] if record["informe_ruta"] else None,
        "certificado_numero": cert_numero or f"CERT-{id:05d}",
        "certificado_fecha": cert_fecha or datetime.now().strftime("%Y-%m-%d"),
        "responsable": record["responsable"],
        "notas": record["notas"],
    }

    DiskDestruction.update(db, id, data)
    flash(f"Disco certificado como destruido (Cert: {data['certificado_numero']})", "success")
    return redirect(url_for("destruction.index"))


# API Endpoints
@destruction_bp.route("/api/summary")
@login_required
def api_summary():
    """Resumen de destrucción para el dashboard"""
    db = get_db()
    summary = DiskDestruction.get_summary(db)
    return jsonify(summary)
