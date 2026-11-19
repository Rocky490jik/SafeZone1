"""JSON API routes used by the frontend map and AJAX calls."""

from flask import Blueprint, jsonify, request
from flask_login import login_required

from safezone.services.shelter import search_shelters

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/shelters.geojson")
@login_required
def shelters_geojson():
    """Return verified shelters as a GeoJSON FeatureCollection for the map."""
    try:
        lat = float(request.args.get("lat", 12.9716))
        lon = float(request.args.get("lon", 77.5946))
    except (TypeError, ValueError):
        lat, lon = 12.9716, 77.5946
    radius = float(request.args.get("radius", 10))
    shelters = search_shelters(lat, lon, radius_km=radius, limit=200)

    features = []
    for s in shelters:
        try:
            geometry = {
                "type": "Point",
                "coordinates": [float(s["longitude"]), float(s["latitude"])],
            }
        except (TypeError, ValueError):
            continue
        props = {
            "shelter_id": s["shelter_id"],
            "shelter_code": s["shelter_code"],
            "name": s["name"],
            "address": s["address"],
            "city": s["city"],
            "status": s["status"],
            "verification_status": s["verification_status"],
            "available_capacity": s["available_capacity"],
            "total_capacity": s["total_capacity"],
            "distance_km": s.get("distance_km"),
            "shelter_type": s["shelter_type"],
            "contact_phone": s["contact_phone"],
            "last_verified_at": s["last_verified_at"],
        }
        features.append({"type": "Feature", "geometry": geometry, "properties": props})

    return jsonify({"type": "FeatureCollection", "features": features})


@api_bp.route("/hazards.geojson")
@login_required
def hazards_geojson():
    """Return active hazard zones as GeoJSON for the map overlay."""
    from safezone.services.hazard import get_active_hazard_zones
    zones = get_active_hazard_zones()
    features = []
    for z in zones:
        poly = z.get("polygon")
        if not poly:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": poly,
                "properties": {
                    "hazard_zone_id": z["hazard_zone_id"],
                    "zone_name": z["zone_name"],
                    "severity": z["severity"],
                    "source_name": z["source_name"],
                    "description": z["description"],
                },
            }
        )
    return jsonify({"type": "FeatureCollection", "features": features})
