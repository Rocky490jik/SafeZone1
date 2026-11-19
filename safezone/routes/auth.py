"""Authentication routes (register, login, logout)."""

from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from safezone.database.connection import query_one
from safezone.services.admin import create_user, get_user_by_email
from safezone.services.shelter import audit

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Flask-Login is configured in app.py; this blueprint relies on login_manager
# being attached to the app. We expose a small helper used by app.py.


def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "info"
    login_manager.session_protection = None

    @login_manager.user_loader
    def load_user(user_id):
        u = get_user_by_id(int(user_id))
        if u:
            return SafeZoneUser(u)
        return None

    return login_manager


# Minimal user model for Flask-Login
class SafeZoneUser:
    def __init__(self, row):
        self.id = row["user_id"]
        self.email = row["email"]
        self.full_name = row["full_name"]
        self.role = row["role"]
        self.is_active = bool(row["is_active"])

    def is_authenticated(self):
        return True

    def is_active_prop(self):
        return self.is_active

    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.role == "ADMIN"


def get_user_by_id(user_id):
    from safezone.database.connection import query_one
    return query_one("SELECT * FROM users WHERE user_id = ?", (user_id,))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("user.dashboard"))
    if request.method == "POST":
        full_name = (request.form.get("full_name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        confirm = request.form.get("confirm_password") or ""

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not email or "@" not in email:
            errors.append("A valid email is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if get_user_by_email(email):
            errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        try:
            user_id = create_user(full_name, email, password_hash, role="USER")
            audit(user_id, "ACCOUNT_REGISTERED", "user", user_id,
                 f"Registered email {email}")
            flash("Account created successfully. Please sign in.", "success")
            return redirect(url_for("auth.login"))
        except Exception as exc:  # pragma: no cover - defensive
            flash(f"Registration failed: {exc}", "danger")
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("user.dashboard"))
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        row = get_user_by_email(email)
        if not row or not check_password_hash(row["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html")
        if not row["is_active"]:
            flash("This account is deactivated. Contact an administrator.", "danger")
            return render_template("login.html")
        user = SafeZoneUser(row)
        login_user(user, remember=True)
        session["role"] = user.role
        audit(user.id, "USER_LOGIN", "user", user.id, f"Signed in from {request.remote_addr}")
        flash(f"Welcome back, {user.full_name}!", "success")
        next_url = request.args.get("next")
        if current_user.is_admin:
            return redirect(next_url or url_for("admin.dashboard"))
        return redirect(next_url or url_for("user.dashboard"))
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    audit(current_user.id, "USER_LOGOUT", "user", current_user.id, "Signed out")
    logout_user()
    session.pop("role", None)
    flash("You have been signed out.", "info")
    return redirect(url_for("index"))
