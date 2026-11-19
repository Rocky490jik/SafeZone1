"""SafeZone - Disaster Safe Shelter Locator.

Flask application factory. Entry point: run `python app.py`.
"""

import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_wtf.csrf import CSRFProtect

from config import Config
from safezone.database.connection import init_db, get_connection

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    csrf.init_app(app)

    # Initialize database (schema + seed data) on first run
    init_db(create_admin=True)

    # --- Flask-Login ---
    from safezone.routes.auth import init_login_manager, SafeZoneUser, get_user_by_id
    login_manager = init_login_manager(app)

    @login_manager.user_loader
    def load_user(user_id):
        row = get_user_by_id(int(user_id))
        if row:
            return SafeZoneUser(row)
        return None

    # --- Register blueprints ---
    from safezone.routes.auth import auth_bp
    from safezone.routes.user import user_bp
    from safezone.routes.admin import admin_bp
    from safezone.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # --- Make current user / role available in all templates ---
    @app.context_processor
    def inject_user():
        from flask_login import current_user
        return dict(
            current_user=current_user,
            disclaimer=Config.DISCLAIMER,
            app_name="SafeZone",
            config=Config,
        )

    # --- Public routes ---
    @app.route("/")
    def index():
        from safezone.services.shelter import list_all_shelters
        from safezone.services.alert import get_active_alerts
        shelters = list_all_shelters(limit=6)
        alerts = get_active_alerts()
        return render_template("index.html", shelters=shelters, alerts=alerts)

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/health")
    def health():
        try:
            get_connection().execute("SELECT 1")
            db_status = "connected"
        except Exception as exc:  # pragma: no cover
            db_status = f"error: {exc}"
        return {"status": "ok", "database": db_status}

    # --- Error handlers ---
    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404,
                               title="Page not found",
                               message="The page you are looking for does not exist."), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                               title="Forbidden",
                               message="You do not have permission to access this page."), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", code=500,
                               title="Server error",
                               message="Something went wrong on our end."), 500

    return app


app = create_app()

if __name__ == "__main__":
    # Debug on for development; disable in production.
    app.run(host="127.0.0.1", port=5000, debug=True)
