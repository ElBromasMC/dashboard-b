from flask import Blueprint, render_template, request, redirect, url_for, flash

from models.database import get_db
from models.user import User
from utils.decorators import login_required, admin_required

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
    """Redirige a la nueva ubicación de carga de avances"""
    return redirect(url_for("bulk_upload.upload_progress"), code=307)


@admin_bp.route("/download-template")
@login_required
@admin_required
def download_template():
    """Redirige a la nueva ubicación de descarga de plantilla"""
    return redirect(url_for("bulk_upload.download_progress_template"))
