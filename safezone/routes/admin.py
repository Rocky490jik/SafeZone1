"""Admin routes (dashboard, shelters, hazards, alerts, contacts, audit)."""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from safezone.services.admin import (
    get_disasters, create_disaster, update_disaster, delete_disaster,
    get_hazard_zones, create_hazard_zone, update_hazard_zone, delete_hazard_zone,
    get_emergency_contacts, create_contact, update_contact, delete_contact,
    get_users, get_user, update_user_role, deactivate_user,
    get_audit_logs,
)
from safezone.services.shelter import (
    list_all_shelters, create_shelter, update_shelter, delete_shelter,
    get_shelter, audit,
)
from safezone.services.alert import get_active_alerts, get_all_alerts, create_alert, update_alert, delete_alert

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _admin_required():
    if not current_user.is_authenticated or current_user.role != "ADMIN":
        flash("Administrator access required.", "danger")
        return False
    return True


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    shelters = list_all_shelters(limit=20)
    alerts = get_active_alerts()
    total = len(list_all_shelters(limit=10000))
    verified = sum(1 for s in shelters if s["verification_status"] == "VERIFIED")
    pending = sum(1 for s in shelters if s["verification_status"] == "PENDING")
    open_count = sum(1 for s in shelters if s["status"] == "OPEN")
    return render_template(
        "admin_dashboard.html",
        shelters=shelters,
        alerts=alerts,
        total=total, verified=verified, pending=pending, open_count=open_count,
    )


# ---------------------------------------------------------------- shelters

@admin_bp.route("/manage-shelters")
@login_required
def manage_shelters():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    shelters = list_all_shelters()
    return render_template("manage_shelters.html", shelters=shelters)


@admin_bp.route("/manage-shelters/add", methods=["GET", "POST"])
@login_required
def add_shelter():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    if request.method == "POST":
        data = {
            "shelter_code": request.form.get("shelter_code"),
            "name": request.form.get("name"),
            "description": request.form.get("description"),
            "address": request.form.get("address"),
            "city": request.form.get("city"),
            "state": request.form.get("state"),
            "postal_code": request.form.get("postal_code"),
            "latitude": request.form.get("latitude"),
            "longitude": request.form.get("longitude"),
            "shelter_type": request.form.get("shelter_type"),
            "total_capacity": request.form.get("total_capacity"),
            "available_capacity": request.form.get("available_capacity"),
            "status": request.form.get("status"),
            "verification_status": request.form.get("verification_status"),
            "contact_name": request.form.get("contact_name"),
            "contact_phone": request.form.get("contact_phone"),
            "has_food": request.form.get("has_food"),
            "has_drinking_water": request.form.get("has_drinking_water"),
            "has_medical_support": request.form.get("has_medical_support"),
            "has_accessibility": request.form.get("has_accessibility"),
            "last_verified_at": request.form.get("last_verified_at"),
        }
        try:
            sid = create_shelter(data, current_user.id)
            audit(current_user.id, "SHELTER_CREATED", "shelter", sid,
                  f"Created shelter {data['name']}")
            flash("Shelter added successfully.", "success")
            return redirect(url_for("admin.manage_shelters"))
        except Exception as exc:
            flash(f"Failed to add shelter: {exc}", "danger")
    return render_template("shelter_form.html", shelter=None, action="Add")


@admin_bp.route("/manage-shelters/edit/<int:shelter_id>", methods=["GET", "POST"])
@login_required
def edit_shelter(shelter_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    shelter = get_shelter(shelter_id)
    if not shelter:
        flash("Shelter not found.", "danger")
        return redirect(url_for("admin.manage_shelters"))
    if request.method == "POST":
        data = {
            "name": request.form.get("name"),
            "description": request.form.get("description"),
            "address": request.form.get("address"),
            "city": request.form.get("city"),
            "state": request.form.get("state"),
            "postal_code": request.form.get("postal_code"),
            "latitude": request.form.get("latitude"),
            "longitude": request.form.get("longitude"),
            "shelter_type": request.form.get("shelter_type"),
            "total_capacity": request.form.get("total_capacity"),
            "available_capacity": request.form.get("available_capacity"),
            "status": request.form.get("status"),
            "verification_status": request.form.get("verification_status"),
            "contact_name": request.form.get("contact_name"),
            "contact_phone": request.form.get("contact_phone"),
            "has_food": request.form.get("has_food"),
            "has_drinking_water": request.form.get("has_drinking_water"),
            "has_medical_support": request.form.get("has_medical_support"),
            "has_accessibility": request.form.get("has_accessibility"),
            "last_verified_at": request.form.get("last_verified_at"),
        }
        try:
            update_shelter(shelter_id, data, current_user.id)
            audit(current_user.id, "SHELTER_UPDATED", "shelter", shelter_id,
                  f"Updated shelter {data['name']}")
            flash("Shelter updated successfully.", "success")
            return redirect(url_for("admin.manage_shelters"))
        except Exception as exc:
            flash(f"Failed to update shelter: {exc}", "danger")
    return render_template("shelter_form.html", shelter=shelter, action="Edit")


@admin_bp.route("/manage-shelters/delete/<int:shelter_id>", methods=["POST"])
@login_required
def delete_shelter_route(shelter_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    try:
        delete_shelter(shelter_id)
        audit(current_user.id, "SHELTER_DELETED", "shelter", shelter_id,
              "Deleted shelter record")
        flash("Shelter deleted.", "info")
    except Exception as exc:
        flash(f"Failed to delete shelter: {exc}", "danger")
    return redirect(url_for("admin.manage_shelters"))


# ---------------------------------------------------------------- disasters

@admin_bp.route("/manage-disasters")
@login_required
def manage_disasters():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    disasters = get_disasters()
    return render_template("manage_disasters.html", disasters=disasters)


@admin_bp.route("/manage-disasters/add", methods=["POST"])
@login_required
def add_disaster():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    data = {
        "event_code": request.form.get("event_code"),
        "title": request.form.get("title"),
        "disaster_type": request.form.get("disaster_type"),
        "severity": request.form.get("severity"),
        "description": request.form.get("description"),
        "affected_area": request.form.get("affected_area"),
        "source_name": request.form.get("source_name"),
        "source_url": request.form.get("source_url"),
        "event_status": request.form.get("event_status"),
        "starts_at": request.form.get("starts_at"),
        "ends_at": request.form.get("ends_at"),
    }
    try:
        did = create_disaster(data, current_user.id)
        audit(current_user.id, "DISASTER_CREATED", "disaster", did,
              f"Created disaster {data['title']}")
        flash("Disaster event added.", "success")
    except Exception as exc:
        flash(f"Failed to add disaster: {exc}", "danger")
    return redirect(url_for("admin.manage_disasters"))


@admin_bp.route("/manage-disasters/edit/<int:disaster_id>", methods=["POST"])
@login_required
def edit_disaster(disaster_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    data = {
        "title": request.form.get("title"),
        "disaster_type": request.form.get("disaster_type"),
        "severity": request.form.get("severity"),
        "description": request.form.get("description"),
        "affected_area": request.form.get("affected_area"),
        "source_name": request.form.get("source_name"),
        "source_url": request.form.get("source_url"),
        "event_status": request.form.get("event_status"),
        "starts_at": request.form.get("starts_at"),
        "ends_at": request.form.get("ends_at"),
    }
    try:
        update_disaster(disaster_id, data, current_user.id)
        audit(current_user.id, "DISASTER_UPDATED", "disaster", disaster_id,
              "Updated disaster event")
        flash("Disaster event updated.", "success")
    except Exception as exc:
        flash(f"Failed to update disaster: {exc}", "danger")
    return redirect(url_for("admin.manage_disasters"))


@admin_bp.route("/manage-disasters/delete/<int:disaster_id>", methods=["POST"])
@login_required
def delete_disaster_route(disaster_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    try:
        delete_disaster(disaster_id)
        audit(current_user.id, "DISASTER_DELETED", "disaster", disaster_id,
              "Deleted disaster event")
        flash("Disaster event deleted.", "info")
    except Exception as exc:
        flash(f"Failed to delete disaster: {exc}", "danger")
    return redirect(url_for("admin.manage_disasters"))


# ---------------------------------------------------------------- hazard zones

@admin_bp.route("/manage-hazards")
@login_required
def manage_hazards():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    zones = get_hazard_zones()
    disasters = get_disasters()
    return render_template("manage_hazards.html", zones=zones, disasters=disasters)


@admin_bp.route("/manage-hazards/add", methods=["POST"])
@login_required
def add_hazard_zone():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    data = {
        "disaster_id": request.form.get("disaster_id") or None,
        "zone_name": request.form.get("zone_name"),
        "description": request.form.get("description"),
        "polygon_geojson": request.form.get("polygon_geojson"),
        "severity": request.form.get("severity"),
        "zone_status": request.form.get("zone_status"),
        "source_name": request.form.get("source_name"),
    }
    try:
        zid = create_hazard_zone(data, current_user.id)
        audit(current_user.id, "HAZARD_CREATED", "hazard_zone", zid,
              f"Created hazard zone {data['zone_name']}")
        flash("Hazard zone added.", "success")
    except Exception as exc:
        flash(f"Failed to add hazard zone: {exc}", "danger")
    return redirect(url_for("admin.manage_hazards"))


@admin_bp.route("/manage-hazards/edit/<int:hazard_zone_id>", methods=["POST"])
@login_required
def edit_hazard_zone(hazard_zone_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    data = {
        "disaster_id": request.form.get("disaster_id") or None,
        "zone_name": request.form.get("zone_name"),
        "description": request.form.get("description"),
        "polygon_geojson": request.form.get("polygon_geojson"),
        "severity": request.form.get("severity"),
        "zone_status": request.form.get("zone_status"),
        "source_name": request.form.get("source_name"),
    }
    try:
        update_hazard_zone(hazard_zone_id, data, current_user.id)
        audit(current_user.id, "HAZARD_UPDATED", "hazard_zone", hazard_zone_id,
              "Updated hazard zone")
        flash("Hazard zone updated.", "success")
    except Exception as exc:
        flash(f"Failed to update hazard zone: {exc}", "danger")
    return redirect(url_for("admin.manage_hazards"))


@admin_bp.route("/manage-hazards/delete/<int:hazard_zone_id>", methods=["POST"])
@login_required
def delete_hazard_zone_route(hazard_zone_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    try:
        delete_hazard_zone(hazard_zone_id)
        audit(current_user.id, "HAZARD_DELETED", "hazard_zone", hazard_zone_id,
              "Deleted hazard zone")
        flash("Hazard zone deleted.", "info")
    except Exception as exc:
        flash(f"Failed to delete hazard zone: {exc}", "danger")
    return redirect(url_for("admin.manage_hazards"))


# ---------------------------------------------------------------- alerts

@admin_bp.route("/manage-alerts")
@login_required
def manage_alerts():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    alerts = get_all_alerts()
    disasters = get_disasters()
    return render_template("manage_alerts.html", alerts=alerts, disasters=disasters)


@admin_bp.route("/manage-alerts/add", methods=["POST"])
@login_required
def add_alert():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    data = {
        "disaster_id": request.form.get("disaster_id") or None,
        "title": request.form.get("title"),
        "message": request.form.get("message"),
        "severity": request.form.get("severity"),
        "area_text": request.form.get("area_text"),
        "source_name": request.form.get("source_name"),
        "alert_status": request.form.get("alert_status"),
        "published_at": request.form.get("published_at"),
        "expires_at": request.form.get("expires_at"),
    }
    try:
        aid = create_alert(data, current_user.id)
        audit(current_user.id, "ALERT_CREATED", "alert", aid,
              f"Created alert {data['title']}")
        flash("Alert added.", "success")
    except Exception as exc:
        flash(f"Failed to add alert: {exc}", "danger")
    return redirect(url_for("admin.manage_alerts"))


@admin_bp.route("/manage-alerts/edit/<int:alert_id>", methods=["POST"])
@login_required
def edit_alert(alert_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    data = {
        "title": request.form.get("title"),
        "message": request.form.get("message"),
        "severity": request.form.get("severity"),
        "area_text": request.form.get("area_text"),
        "source_name": request.form.get("source_name"),
        "alert_status": request.form.get("alert_status"),
        "published_at": request.form.get("published_at"),
        "expires_at": request.form.get("expires_at"),
    }
    try:
        update_alert(alert_id, data, current_user.id)
        audit(current_user.id, "ALERT_UPDATED", "alert", alert_id,
              "Updated alert")
        flash("Alert updated.", "success")
    except Exception as exc:
        flash(f"Failed to update alert: {exc}", "danger")
    return redirect(url_for("admin.manage_alerts"))


@admin_bp.route("/manage-alerts/delete/<int:alert_id>", methods=["POST"])
@login_required
def delete_alert_route(alert_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    try:
        delete_alert(alert_id)
        audit(current_user.id, "ALERT_DELETED", "alert", alert_id,
              "Deleted alert")
        flash("Alert deleted.", "info")
    except Exception as exc:
        flash(f"Failed to delete alert: {exc}", "danger")
    return redirect(url_for("admin.manage_alerts"))


# ---------------------------------------------------------------- contacts

@admin_bp.route("/manage-contacts")
@login_required
def manage_contacts():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    contacts = get_emergency_contacts(active_only=False)
    return render_template("manage_contacts.html", contacts=contacts)


@admin_bp.route("/manage-contacts/add", methods=["POST"])
@login_required
def add_contact():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    data = {
        "agency_name": request.form.get("agency_name"),
        "category": request.form.get("category"),
        "phone": request.form.get("phone"),
        "area_text": request.form.get("area_text"),
        "source_name": request.form.get("source_name"),
        "is_verified": request.form.get("is_verified"),
        "is_active": request.form.get("is_active"),
    }
    try:
        create_contact(data, current_user.id)
        audit(current_user.id, "CONTACT_CREATED", "emergency_contact", 0,
              f"Created contact {data['agency_name']}")
        flash("Emergency contact added.", "success")
    except Exception as exc:
        flash(f"Failed to add contact: {exc}", "danger")
    return redirect(url_for("admin.manage_contacts"))


@admin_bp.route("/manage-contacts/edit/<int:contact_id>", methods=["POST"])
@login_required
def edit_contact(contact_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    data = {
        "agency_name": request.form.get("agency_name"),
        "category": request.form.get("category"),
        "phone": request.form.get("phone"),
        "area_text": request.form.get("area_text"),
        "source_name": request.form.get("source_name"),
        "is_verified": request.form.get("is_verified"),
        "is_active": request.form.get("is_active"),
    }
    try:
        update_contact(contact_id, data)
        audit(current_user.id, "CONTACT_UPDATED", "emergency_contact", contact_id,
              "Updated contact")
        flash("Contact updated.", "success")
    except Exception as exc:
        flash(f"Failed to update contact: {exc}", "danger")
    return redirect(url_for("admin.manage_contacts"))


@admin_bp.route("/manage-contacts/delete/<int:contact_id>", methods=["POST"])
@login_required
def delete_contact_route(contact_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    try:
        delete_contact(contact_id)
        audit(current_user.id, "CONTACT_DELETED", "emergency_contact", contact_id,
              "Deleted contact")
        flash("Contact deleted.", "info")
    except Exception as exc:
        flash(f"Failed to delete contact: {exc}", "danger")
    return redirect(url_for("admin.manage_contacts"))


# ---------------------------------------------------------------- users & audit

@admin_bp.route("/manage-users")
@login_required
def manage_users():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    users = get_users()
    return render_template("manage_users.html", users=users)


@admin_bp.route("/manage-users/role/<int:user_id>", methods=["POST"])
@login_required
def set_user_role(user_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    role = request.form.get("role", "USER")
    try:
        update_user_role(user_id, role)
        audit(current_user.id, "USER_ROLE_CHANGED", "user", user_id,
              f"Role set to {role}")
        flash("User role updated.", "success")
    except Exception as exc:
        flash(f"Failed to update role: {exc}", "danger")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/manage-users/deactivate/<int:user_id>", methods=["POST"])
@login_required
def deactivate_user_route(user_id):
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    try:
        deactivate_user(user_id)
        audit(current_user.id, "USER_DEACTIVATED", "user", user_id,
              "Deactivated user account")
        flash("User deactivated.", "info")
    except Exception as exc:
        flash(f"Failed to deactivate user: {exc}", "danger")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/activity-log")
@login_required
def activity_log():
    if not _admin_required():
        return redirect(url_for("user.dashboard"))
    logs = get_audit_logs(limit=200)
    return render_template("activity_log.html", logs=logs)
