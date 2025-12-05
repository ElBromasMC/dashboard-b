from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g, abort

from models.database import get_db
from models.user import User
from utils.decorators import login_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        db = get_db()
        g.user = db.execute(
            "SELECT id, username, role FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    abort(404)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = "Credenciales invalidas"
        user = User.get_by_username(get_db(), username)
        if user and User.verify_password(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("Bienvenido de nuevo", "success")
            return redirect(url_for("dashboard.index"))
        flash(error, "danger")
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Sesion finalizada", "info")
    return redirect(url_for("auth.login"))
