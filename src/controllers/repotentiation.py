from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g

from models.database import get_db
from models.repotentiation import RepotentiationRecord
from utils.decorators import login_required, admin_required

repotentiation_bp = Blueprint('repotentiation', __name__, url_prefix='/repotenciacion')


@repotentiation_bp.route("/")
@login_required
def index():
    """Vista principal del historial de repotenciación"""
    db = get_db()
    serial_filter = request.args.get("serial", "").strip()

    if serial_filter:
        records = RepotentiationRecord.search_by_serial(db, serial_filter)
    else:
        records = RepotentiationRecord.get_all(db)

    summary = RepotentiationRecord.get_summary(db)

    return render_template(
        "repotentiation/index.html",
        records=records,
        summary=summary,
        serial_filter=serial_filter,
    )


@repotentiation_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    """Registrar nueva repotenciación"""
    db = get_db()

    # Obtener lista de equipos para el selector
    equipos = db.execute("""
        SELECT serial_num, hostname, nombre_completo
        FROM project_records
        WHERE serial_num IS NOT NULL AND serial_num != ''
        ORDER BY hostname
    """).fetchall()

    if request.method == "POST":
        data = {
            "equipo_serial": request.form.get("equipo_serial", "").strip(),
            "equipo_hostname": request.form.get("equipo_hostname", "").strip(),
            "fecha_repotenciacion": request.form.get("fecha_repotenciacion", "").strip(),

            "ram_antes_gb": int(request.form.get("ram_antes_gb") or 0) or None,
            "ram_antes_tipo": request.form.get("ram_antes_tipo", "").strip() or None,
            "ram_antes_serial": request.form.get("ram_antes_serial", "").strip() or None,

            "ram_despues_gb": int(request.form.get("ram_despues_gb") or 0) or None,
            "ram_despues_tipo": request.form.get("ram_despues_tipo", "").strip() or None,
            "ram_despues_serial": request.form.get("ram_despues_serial", "").strip() or None,

            "disco_antes_tipo": request.form.get("disco_antes_tipo", "").strip() or None,
            "disco_antes_capacidad_gb": int(request.form.get("disco_antes_capacidad_gb") or 0) or None,
            "disco_antes_serial": request.form.get("disco_antes_serial", "").strip() or None,

            "disco_despues_tipo": request.form.get("disco_despues_tipo", "").strip() or None,
            "disco_despues_capacidad_gb": int(request.form.get("disco_despues_capacidad_gb") or 0) or None,
            "disco_despues_serial": request.form.get("disco_despues_serial", "").strip() or None,

            "ram_extraida_serial": request.form.get("ram_extraida_serial", "").strip() or None,
            "ram_extraida_estado": request.form.get("ram_extraida_estado", "").strip() or None,
            "disco_extraido_serial": request.form.get("disco_extraido_serial", "").strip() or None,
            "disco_extraido_estado": request.form.get("disco_extraido_estado", "").strip() or None,
            "disco_extraido_destruido": 1 if request.form.get("disco_extraido_destruido") else 0,

            "tecnico": request.form.get("tecnico", "").strip() or g.user["username"],
            "notas": request.form.get("notas", "").strip() or None,
        }

        if not data["equipo_serial"]:
            flash("Debes seleccionar un equipo", "danger")
            return render_template("repotentiation/form.html", data=data, equipos=equipos)

        if not data["fecha_repotenciacion"]:
            flash("La fecha de repotenciación es obligatoria", "danger")
            return render_template("repotentiation/form.html", data=data, equipos=equipos)

        RepotentiationRecord.create(db, data)
        flash("Repotenciación registrada correctamente", "success")
        return redirect(url_for("repotentiation.index"))

    return render_template("repotentiation/form.html", data={}, equipos=equipos)


@repotentiation_bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def edit(id):
    """Editar registro de repotenciación"""
    db = get_db()
    record = RepotentiationRecord.get_by_id(db, id)

    if not record:
        flash("Registro no encontrado", "danger")
        return redirect(url_for("repotentiation.index"))

    equipos = db.execute("""
        SELECT serial_num, hostname, nombre_completo
        FROM project_records
        WHERE serial_num IS NOT NULL AND serial_num != ''
        ORDER BY hostname
    """).fetchall()

    if request.method == "POST":
        data = {
            "fecha_repotenciacion": request.form.get("fecha_repotenciacion", "").strip(),

            "ram_antes_gb": int(request.form.get("ram_antes_gb") or 0) or None,
            "ram_antes_tipo": request.form.get("ram_antes_tipo", "").strip() or None,
            "ram_antes_serial": request.form.get("ram_antes_serial", "").strip() or None,

            "ram_despues_gb": int(request.form.get("ram_despues_gb") or 0) or None,
            "ram_despues_tipo": request.form.get("ram_despues_tipo", "").strip() or None,
            "ram_despues_serial": request.form.get("ram_despues_serial", "").strip() or None,

            "disco_antes_tipo": request.form.get("disco_antes_tipo", "").strip() or None,
            "disco_antes_capacidad_gb": int(request.form.get("disco_antes_capacidad_gb") or 0) or None,
            "disco_antes_serial": request.form.get("disco_antes_serial", "").strip() or None,

            "disco_despues_tipo": request.form.get("disco_despues_tipo", "").strip() or None,
            "disco_despues_capacidad_gb": int(request.form.get("disco_despues_capacidad_gb") or 0) or None,
            "disco_despues_serial": request.form.get("disco_despues_serial", "").strip() or None,

            "ram_extraida_serial": request.form.get("ram_extraida_serial", "").strip() or None,
            "ram_extraida_estado": request.form.get("ram_extraida_estado", "").strip() or None,
            "disco_extraido_serial": request.form.get("disco_extraido_serial", "").strip() or None,
            "disco_extraido_estado": request.form.get("disco_extraido_estado", "").strip() or None,
            "disco_extraido_destruido": 1 if request.form.get("disco_extraido_destruido") else 0,

            "tecnico": request.form.get("tecnico", "").strip() or None,
            "notas": request.form.get("notas", "").strip() or None,
        }

        RepotentiationRecord.update(db, id, data)
        flash("Registro actualizado correctamente", "success")
        return redirect(url_for("repotentiation.index"))

    return render_template("repotentiation/form.html", data=dict(record), equipos=equipos, editing=True)


@repotentiation_bp.route("/<int:id>/eliminar", methods=["POST"])
@login_required
@admin_required
def delete(id):
    """Eliminar registro de repotenciación"""
    db = get_db()
    RepotentiationRecord.delete(db, id)
    flash("Registro eliminado", "success")
    return redirect(url_for("repotentiation.index"))


@repotentiation_bp.route("/equipo/<serial>")
@login_required
def by_equipment(serial):
    """Ver historial de repotenciación de un equipo"""
    db = get_db()
    records = RepotentiationRecord.get_by_serial(db, serial)

    equipo = db.execute("""
        SELECT serial_num, hostname, nombre_completo
        FROM project_records WHERE serial_num = ?
    """, (serial,)).fetchone()

    return render_template(
        "repotentiation/equipment.html",
        records=records,
        equipo=equipo,
        serial=serial,
    )


# API Endpoints
@repotentiation_bp.route("/api/summary")
@login_required
def api_summary():
    """Resumen de repotenciaciones para el dashboard"""
    db = get_db()
    summary = RepotentiationRecord.get_summary(db)
    return jsonify(summary)


@repotentiation_bp.route("/api/buscar")
@login_required
def api_search():
    """API para buscar por serial"""
    db = get_db()
    serial = request.args.get("serial", "").strip()
    if not serial:
        return jsonify([])
    records = RepotentiationRecord.search_by_serial(db, serial)
    return jsonify([dict(r) for r in records])
