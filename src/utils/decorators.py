from functools import wraps
from flask import g, flash, redirect, url_for


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Inicia sesion para continuar", "warning")
            return redirect(url_for("auth.login"))
        return view(**kwargs)
    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user["role"] != "admin":
            flash("Requiere privilegios administrativos", "warning")
            return redirect(url_for("dashboard.index"))
        return view(**kwargs)
    return wrapped_view
