from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, g

from models.database import get_db
from models.component import RAMUnit, SSDUnit, ComponentHistory, COMPONENT_STATUS, COMPONENT_STATUS_COLORS
from utils.decorators import login_required, admin_required

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventario')


@inventory_bp.route("/")
@login_required
def index():
    """Vista principal del inventario de componentes"""
    return render_template("inventory/index.html")


@inventory_bp.route("/ram")
@login_required
def ram_list():
    """Lista de memorias RAM"""
    db = get_db()
    estado_filter = request.args.get("estado", "").strip()
    rams = RAMUnit.get_all(db, estado=estado_filter if estado_filter else None)
    summary = RAMUnit.get_summary(db)
    return render_template(
        "inventory/ram_list.html",
        rams=rams,
        summary=summary,
        status_options=COMPONENT_STATUS,
        status_colors=COMPONENT_STATUS_COLORS,
        current_filter=estado_filter,
    )


@inventory_bp.route("/ram/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def ram_new():
    """Crear nueva RAM"""
    if request.method == "POST":
        data = {
            "serial_num": request.form.get("serial_num", "").strip(),
            "marca": request.form.get("marca", "").strip(),
            "capacidad_gb": int(request.form.get("capacidad_gb", 0) or 0),
            "tipo": request.form.get("tipo", "").strip(),
            "velocidad_mhz": int(request.form.get("velocidad_mhz", 0) or 0),
            "estado": request.form.get("estado", "POR_ENTREGAR"),
            "notas": request.form.get("notas", "").strip(),
        }

        if not data["serial_num"]:
            flash("El numero de serie es obligatorio", "danger")
            return render_template("inventory/ram_form.html", data=data, status_options=COMPONENT_STATUS)

        db = get_db()
        existing = RAMUnit.get_by_serial(db, data["serial_num"])
        if existing:
            flash("Ya existe una RAM con ese numero de serie", "danger")
            return render_template("inventory/ram_form.html", data=data, status_options=COMPONENT_STATUS)

        RAMUnit.create(db, data)
        flash("Memoria RAM registrada correctamente", "success")
        return redirect(url_for("inventory.ram_list"))

    return render_template("inventory/ram_form.html", data={}, status_options=COMPONENT_STATUS)


@inventory_bp.route("/ram/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def ram_edit(id):
    """Editar RAM"""
    db = get_db()
    ram = RAMUnit.get_by_id(db, id)
    if not ram:
        flash("RAM no encontrada", "danger")
        return redirect(url_for("inventory.ram_list"))

    if request.method == "POST":
        data = {
            "marca": request.form.get("marca", "").strip(),
            "capacidad_gb": int(request.form.get("capacidad_gb", 0) or 0),
            "tipo": request.form.get("tipo", "").strip(),
            "velocidad_mhz": int(request.form.get("velocidad_mhz", 0) or 0),
            "estado": request.form.get("estado", ram["estado"]),
            "equipo_serial": request.form.get("equipo_serial", "").strip() or None,
            "fecha_instalacion": request.form.get("fecha_instalacion", "").strip() or None,
            "notas": request.form.get("notas", "").strip(),
        }

        RAMUnit.update(db, id, data)
        flash("RAM actualizada correctamente", "success")
        return redirect(url_for("inventory.ram_list"))

    return render_template("inventory/ram_form.html", data=dict(ram), status_options=COMPONENT_STATUS, editing=True)


@inventory_bp.route("/ssd")
@login_required
def ssd_list():
    """Lista de discos SSD"""
    db = get_db()
    estado_filter = request.args.get("estado", "").strip()
    ssds = SSDUnit.get_all(db, estado=estado_filter if estado_filter else None)
    summary = SSDUnit.get_summary(db)
    return render_template(
        "inventory/ssd_list.html",
        ssds=ssds,
        summary=summary,
        status_options=COMPONENT_STATUS,
        status_colors=COMPONENT_STATUS_COLORS,
        current_filter=estado_filter,
    )


@inventory_bp.route("/ssd/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def ssd_new():
    """Crear nuevo SSD"""
    if request.method == "POST":
        data = {
            "serial_num": request.form.get("serial_num", "").strip(),
            "marca": request.form.get("marca", "").strip(),
            "modelo": request.form.get("modelo", "").strip(),
            "capacidad_gb": int(request.form.get("capacidad_gb", 0) or 0),
            "tipo": request.form.get("tipo", "").strip(),
            "estado": request.form.get("estado", "POR_ENTREGAR"),
            "notas": request.form.get("notas", "").strip(),
        }

        if not data["serial_num"]:
            flash("El numero de serie es obligatorio", "danger")
            return render_template("inventory/ssd_form.html", data=data, status_options=COMPONENT_STATUS)

        db = get_db()
        existing = SSDUnit.get_by_serial(db, data["serial_num"])
        if existing:
            flash("Ya existe un SSD con ese numero de serie", "danger")
            return render_template("inventory/ssd_form.html", data=data, status_options=COMPONENT_STATUS)

        SSDUnit.create(db, data)
        flash("Disco SSD registrado correctamente", "success")
        return redirect(url_for("inventory.ssd_list"))

    return render_template("inventory/ssd_form.html", data={}, status_options=COMPONENT_STATUS)


@inventory_bp.route("/ssd/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def ssd_edit(id):
    """Editar SSD"""
    db = get_db()
    ssd = SSDUnit.get_by_id(db, id)
    if not ssd:
        flash("SSD no encontrado", "danger")
        return redirect(url_for("inventory.ssd_list"))

    if request.method == "POST":
        data = {
            "marca": request.form.get("marca", "").strip(),
            "modelo": request.form.get("modelo", "").strip(),
            "capacidad_gb": int(request.form.get("capacidad_gb", 0) or 0),
            "tipo": request.form.get("tipo", "").strip(),
            "estado": request.form.get("estado", ssd["estado"]),
            "equipo_serial": request.form.get("equipo_serial", "").strip() or None,
            "fecha_instalacion": request.form.get("fecha_instalacion", "").strip() or None,
            "notas": request.form.get("notas", "").strip(),
        }

        SSDUnit.update(db, id, data)
        flash("SSD actualizado correctamente", "success")
        return redirect(url_for("inventory.ssd_list"))

    return render_template("inventory/ssd_form.html", data=dict(ssd), status_options=COMPONENT_STATUS, editing=True)


@inventory_bp.route("/historial")
@login_required
def history():
    """Historial de movimientos de componentes"""
    db = get_db()
    equipo = request.args.get("equipo", "").strip()

    if equipo:
        movements = ComponentHistory.get_by_equipment(db, equipo)
    else:
        movements = ComponentHistory.get_recent(db, limit=50)

    return render_template("inventory/history.html", movements=movements, equipo_filter=equipo)


# API Endpoints
@inventory_bp.route("/api/summary")
@login_required
def api_summary():
    """Resumen de inventario para el dashboard"""
    db = get_db()
    ram_summary = RAMUnit.get_summary(db)
    ssd_summary = SSDUnit.get_summary(db)

    return jsonify({
        "ram": ram_summary,
        "ssd": ssd_summary,
        "status_colors": COMPONENT_STATUS_COLORS,
        "status_labels": COMPONENT_STATUS,
    })


@inventory_bp.route("/api/ram")
@login_required
def api_ram_list():
    """API para listar RAMs"""
    db = get_db()
    estado = request.args.get("estado", "").strip()
    rams = RAMUnit.get_all(db, estado=estado if estado else None)
    return jsonify([dict(ram) for ram in rams])


@inventory_bp.route("/api/ssd")
@login_required
def api_ssd_list():
    """API para listar SSDs"""
    db = get_db()
    estado = request.args.get("estado", "").strip()
    ssds = SSDUnit.get_all(db, estado=estado if estado else None)
    return jsonify([dict(ssd) for ssd in ssds])
