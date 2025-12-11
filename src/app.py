from flask import Flask, jsonify

from config import Config
from models.database import close_db, init_db
from controllers import (
    auth_bp, dashboard_bp, admin_bp, inventory_bp, conformity_bp,
    repotentiation_bp, destruction_bp, reports_bp, bulk_upload_bp
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Registrar blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(conformity_bp)
    app.register_blueprint(repotentiation_bp)
    app.register_blueprint(destruction_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(bulk_upload_bp)

    # Cerrar conexión de BD al terminar
    app.teardown_appcontext(close_db)

    # Health check endpoint
    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    # Rutas de compatibilidad con URLs antiguas
    @app.route("/upload", methods=["GET", "POST"])
    def upload_redirect():
        from flask import redirect, url_for
        return redirect(url_for("bulk_upload.upload_progress"), code=307)

    @app.route("/api/download-template")
    def download_template_redirect():
        from flask import redirect, url_for
        return redirect(url_for("bulk_upload.download_progress_template"))

    return app


app = create_app()


@app.cli.command("init-db")
def init_db_command():
    with app.app_context():
        init_db()
    print("Base de datos inicializada.")


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", debug=True, port=5000)
