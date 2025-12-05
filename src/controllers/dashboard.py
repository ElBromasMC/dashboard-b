from flask import Blueprint, render_template, request, jsonify, g, redirect, url_for

from models.database import get_db
from models.project import ProjectRecord
from config import STATUS_CHOICES, PROJECT_PHASES, get_phase_from_category
from utils.decorators import login_required
from utils.helpers import coerce_iso_date

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route("/")
def home():
    if g.user:
        return redirect(url_for("dashboard.index"))
    return redirect(url_for("auth.login"))


@dashboard_bp.route("/dashboard")
@login_required
def index():
    return render_template("dashboard.html")


@dashboard_bp.route("/api/summary")
@login_required
def api_summary():
    db = get_db()

    fase_filter = request.args.get("fase", "").strip() or None

    filters = {
        "ubicacion": request.args.get("ubicacion", "").strip() or None,
        "nom_sede": request.args.get("nom_sede", "").strip() or None,
        "categoria_trab": request.args.get("categoria_trab", "").strip() or None,
        "estado": request.args.get("estado", "").strip() or None,
        "fecha_inicio": coerce_iso_date(request.args.get("fecha_inicio", "").strip()) or None,
        "fecha_fin": coerce_iso_date(request.args.get("fecha_fin", "").strip()) or None,
        "nombre": request.args.get("nombre", "").strip() or None,
        "hostname": request.args.get("hostname", "").strip() or None,
        "fase": fase_filter,
    }

    records = ProjectRecord.query_records(db, filters)
    summary = ProjectRecord.calculate_summary(records)

    if not filters.get("nombre"):
        summary["recent_updates"] = summary["recent_updates"][:10]

    filters_payload = {}
    for field in ("ubicacion", "nom_sede", "categoria_trab"):
        options = ProjectRecord.get_filter_options(db, field)
        filters_payload[field] = {
            "options": options,
            "selected": filters.get(field) or "",
        }
    filters_payload["estado"] = {
        "options": STATUS_CHOICES,
        "selected": filters.get("estado") or "",
    }

    # Calcular resumen por fase
    phase_counts = {}
    for record in records:
        fase = get_phase_from_category(record["categoria_trab"])
        if fase:
            phase_counts[fase] = phase_counts.get(fase, 0) + 1

    data = {
        **summary,
        "status_catalog": STATUS_CHOICES,
        "filters": filters_payload,
        "date_filters": {
            "fecha_inicio": filters.get("fecha_inicio") or "",
            "fecha_fin": filters.get("fecha_fin") or "",
        },
        "hostname_filter": filters.get("hostname") or "",
        "name_filter": filters.get("nombre") or "",
        "estado_filter": filters.get("estado") or "",
        "estado_options": STATUS_CHOICES,
        "fase_filter": fase_filter or "",
        "fase_options": PROJECT_PHASES,
        "fase_counts": phase_counts,
    }

    return jsonify(data)


@dashboard_bp.app_context_processor
def inject_globals():
    return {"current_user": g.get("user")}
