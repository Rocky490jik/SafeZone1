"""User-facing routes (dashboard, shelter finder, details, route, alerts, contacts)."""

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, session
from flask_login import login_required, current_user

from safezone.services.shelter import (
    search_shelters, get_shelter, list_all_shelters,
    haversine_km, audit,
)
from safezone.services.routing import get_route
from safezone.services.hazard import check_route_against_hazards
from safezone.services.alert import get_active_alerts, get_all_alerts
from safezone.services.admin import get_emergency_contacts

user_bp = Blueprint("user", __name__, url_prefix="/user")


def get_user_location():
    """Get user location from session, with defaults."""
    lat = float(session.get("lat", 12.9716))
    lon = float(session.get("lon", 77.5946))
    return lat, lon


@user_bp.route("/dashboard")
@login_required
def dashboard():
    from safezone.services.shelter import search_shelters
    lat, lon = get_user_location()
    nearby = search_shelters(lat, lon, radius_km=5, limit=6)
    alerts = get_active_alerts()
    return render_template(
        "dashboard.html",
        nearby_shelters=nearby,
        alerts=alerts,
        lat=lat,
        lon=lon,
    )


@user_bp.route("/find-shelter", methods=["GET", "POST"])
@login_required
def find_shelter():
    lat, lon = get_user_location()
    radius = float(request.args.get("radius", 10))
    status = request.args.get("status") or None
    cap = request.args.get("capacity_min") or None
    facilities = request.args.getlist("facility")

    shelters = search_shelters(lat, lon, radius_km=radius, status=status,
                               capacity_min=cap, facilities=facilities)

    return render_template(
        "find_shelter.html",
        shelters=shelters,
        lat=lat,
        lon=lon,
        radius=radius,
        status=status or "",
        capacity_min=cap or "",
        facilities=facilities,
    )


@user_bp.route("/set-location", methods=["POST"])
@login_required
def set_location():
    data = request.get_json(silent=True) or {}
    try:
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid coordinates"}), 400
    session["lat"] = lat
    session["lon"] = lon
    return jsonify({"ok": True, "lat": lat, "lon": lon})


@user_bp.route("/shelter/<int:shelter_id>")
@login_required
def shelter_detail(shelter_id):
    shelter = get_shelter(shelter_id)
    if not shelter:
        flash("Shelter not found.", "danger")
        return redirect(url_for("user.find_shelter"))
    # Normalize booleans for template
    shelter["facilities"] = {
        "food": bool(shelter["has_food"]),
        "water": bool(shelter["has_drinking_water"]),
        "medical": bool(shelter["has_medical_support"]),
        "accessibility": bool(shelter["has_accessibility"]),
    }
    return render_template("shelter_detail.html", shelter=shelter)


@user_bp.route("/route", methods=["POST"])
@login_required
def route():
    """Compute a route from the user's current location to a shelter and
    check it against active hazard zones."""
    data = request.get_json(silent=True) or {}
    try:
        shelter_id = int(data.get("shelter_id"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Invalid shelter"}), 400

    # Get user's current location from request (sent by client via geolocation)
    # Fall back to session if not provided
    try:
        start_lat = float(data.get("lat", session.get("lat", 12.9716)))
        start_lon = float(data.get("lon", session.get("lon", 77.5946)))
    except (TypeError, ValueError):
        start_lat = float(session.get("lat", 12.9716))
        start_lon = float(session.get("lon", 77.5946))

    shelter = get_shelter(shelter_id)
    if not shelter:
        return jsonify({"ok": False, "error": "Shelter not found"}), 404

    end_lat = float(shelter["latitude"])
    end_lon = float(shelter["longitude"])

    route_result = get_route(start_lat, start_lon, end_lat, end_lon)
    if not route_result["ok"]:
        return jsonify({"ok": False, "error": route_result.get("error")}), 502

    best = route_result["routes"][0]
    hazard_check = check_route_against_hazards(best["geometry"])

    audit(current_user.id, "ROUTE_REQUESTED", "shelter", shelter_id,
          f"Route to {shelter['name']}; safe={hazard_check['safe']}")

    return jsonify({
        "ok": True,
        "shelter": {
            "shelter_id": shelter["shelter_id"],
            "name": shelter["name"],
            "address": shelter["address"],
            "city": shelter["city"],
            "latitude": shelter["latitude"],
            "longitude": shelter["longitude"],
            "status": shelter["status"],
            "verification_status": shelter["verification_status"],
            "available_capacity": shelter["available_capacity"],
            "total_capacity": shelter["total_capacity"],
        },
        "origin": {"lat": start_lat, "lon": start_lon},
        "destination": {"lat": end_lat, "lon": end_lon},
        "route": best,
        "hazard_check": hazard_check,
    })


@user_bp.route("/alerts")
@login_required
def alerts():
    alert_list = get_active_alerts()
    return render_template("alerts.html", alerts=alert_list)


@user_bp.route("/emergency-contacts")
@login_required
def emergency_contacts():
    contacts = get_emergency_contacts()
    return render_template("emergency_contacts.html", contacts=contacts)


@user_bp.route("/profile")
@login_required
def profile():
    from safezone.services.admin import get_user
    u = get_user(current_user.id)
    return render_template("profile.html", user=u)
