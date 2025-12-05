import csv
import io
from pathlib import Path

from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory

from models.database import get_db
from models.user import User
from models.project import ProjectRecord
from config import CSV_FIELD_MAP, BASE_DIR
from utils.decorators import login_required, admin_required
from utils.helpers import normalize_header, normalize_date

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route("/usuarios/nuevo", methods=["GET", "POST"])
@login_required
@admin_required
def new_user():
    selected_role = request.form.get("role", "standard")
    if request.method == "POST":
        success, error = User.create(
            db=get_db(),
            username=request.form.get("username", ""),
            password=request.form.get("password", ""),
            confirm=request.form.get("confirm", ""),
            role=selected_role,
        )
        if success:
            flash("Usuario creado correctamente", "success")
            return redirect(url_for("admin.new_user"))
        flash(error, "danger")
    return render_template(
        "register.html",
        admin_mode=True,
        selected_role=selected_role,
    )


@admin_bp.route("/upload", methods=["GET", "POST"])
@login_required
@admin_required
def upload():
    summary = None
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("Selecciona un archivo CSV", "danger")
            return render_template("upload.html", summary=summary)
        if not file.filename.lower().endswith(".csv"):
            flash("El archivo debe tener formato .csv", "danger")
            return render_template("upload.html", summary=summary)

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
        except UnicodeDecodeError:
            flash("No se pudo decodificar el archivo. Usa UTF-8.", "danger")
            return render_template("upload.html", summary=summary)

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
            return render_template("upload.html", summary=summary)

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
    return render_template("upload.html", summary=summary)


@admin_bp.route("/download-template")
@login_required
@admin_required
def download_template():
    template_path = BASE_DIR / "static" / "templates" / "avance_template.csv"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    with open(template_path, "w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "id",
            "ubicacion",
            "nom_sede",
            "categoria_trab",
            "nombre_completo",
            "perfil_imagen",
            "marca",
            "modelo",
            "serial_num",
            "hostname",
            "ip_equipo",
            "email_trabajo",
            "fecha_estado",
            "estado",
            "estado_coordinacion",
            "estado_upgrade",
            "fecha_programada",
            "fecha_ejecucion",
            "notas",
        ])
        writer.writerow([
            "001",
            "SEDE PRINCIPAL",
            "Centro Corporativo",
            "UPGRADE + WIN11",
            "Nombre Ejemplo",
            "OFICINA PRINCIPAL ADMINISTRATIVO",
            "HP",
            "EliteBook 840",
            "5CD3051HBZ",
            "BANCAINMOBIOP01",
            "10.10.2.15",
            "usuario@banbif.com",
            "2025-09-29",
            "REALIZADO",
            "REALIZADO",
            "PROGRAMADO",
            "2025-09-27",
            "2025-09-29",
            "Observaciones",
        ])
    return send_from_directory(template_path.parent, template_path.name, as_attachment=True)
