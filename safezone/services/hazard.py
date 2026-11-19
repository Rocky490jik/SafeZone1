"""SafeZone hazard-zone and route-intersection service.

Pure-Python computational geometry (no Shapely dependency) so the app runs
out of the box. Checks whether an OSRM route LineString intersects any active
hazard polygon stored in the database.

Coordinates throughout are (longitude, latitude) to match GeoJSON and OSRM.
"""

import json
import math

from safezone.database.connection import query_all


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------

def _orientation(p, q, r):
    """Return orientation of ordered triplet (p, q, r).
    0 -> collinear, 1 -> clockwise, 2 -> counterclockwise.
    p, q, r are (x, y) = (lon, lat).
    """
    val = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
    if abs(val) < 1e-12:
        return 0
    return 1 if val > 0 else 2


def _on_segment(p, q, r):
    """Check if point q lies on segment pr (assuming collinear)."""
    return (
        min(p[0], r[0]) - 1e-12 <= q[0] <= max(p[0], r[0]) + 1e-12
        and min(p[1], r[1]) - 1e-12 <= q[1] <= max(p[1], r[1]) + 1e-12
    )


def _segments_intersect(p1, q1, p2, q2):
    """True if segment p1q1 intersects segment p2q2."""
    o1 = _orientation(p1, q1, p2)
    o2 = _orientation(p1, q1, q2)
    o3 = _orientation(p2, q2, p1)
    o4 = _orientation(p2, q2, q1)

    if o1 != o2 and o3 != o4:
        return True

    # Special collinear cases
    if o1 == 0 and _on_segment(p1, q1, p2):
        return True
    if o2 == 0 and _on_segment(p1, q1, q2):
        return True
    if o3 == 0 and _on_segment(p2, q2, p1):
        return True
    if o4 == 0 and _on_segment(p2, q2, q1):
        return True
    return False


def _point_in_ring(point, ring):
    """Ray-casting point-in-polygon test for a single ring.
    point: (lon, lat); ring: list of (lon, lat) with first == last.
    Returns True if point is strictly inside or on the boundary.
    """
    x, y = point
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        # Check if point lies on an edge
        if _segments_intersect((x, y), (x, y), (xi, yi), (xj, yj)):
            return True
        intersect = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / (yj - yi + 1e-18) + xi
        )
        if intersect:
            inside = not inside
        j = i
    return inside


def _point_in_polygon(point, polygon):
    """point in (multi)polygon.
    polygon: GeoJSON Polygon or MultiPolygon dict.
    """
    coords = polygon.get("coordinates", [])
    if polygon.get("type") == "Polygon":
        rings = coords
    elif polygon.get("type") == "MultiPolygon":
        rings = [ring for poly in coords for ring in poly]
    else:
        return False
    # Even-odd rule across rings: inside outer ring and not inside any hole.
    if not rings:
        return False
    if not _point_in_ring(point, rings[0]):
        return False
    for hole in rings[1:]:
        if _point_in_ring(point, hole):
            return False
    return True


def _parse_geojson(geojson_text):
    """Parse a polygon_geojson TEXT column into a Python dict."""
    if not geojson_text:
        return None
    if isinstance(geojson_text, dict):
        return geojson_text
    try:
        return json.loads(geojson_text)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def route_intersects_hazard(route_coords, polygon):
    """Return True if the route (list of [lon, lat]) intersects polygon."""
    if not route_coords or len(route_coords) < 2:
        return False
    poly = _parse_geojson(polygon)
    if poly is None:
        return False

    # 1) Any route vertex inside the polygon?
    for pt in route_coords:
        if _point_in_polygon(tuple(pt), poly):
            return True

    # 2) Any route segment crossing any polygon ring edge?
    rings = []
    if poly.get("type") == "Polygon":
        rings = poly["coordinates"]
    elif poly.get("type") == "MultiPolygon":
        rings = [ring for part in poly["coordinates"] for ring in part]

    for i in range(len(route_coords) - 1):
        p1 = tuple(route_coords[i])
        p2 = tuple(route_coords[i + 1])
        for ring in rings:
            ring_pts = [tuple(p) for p in ring]
            for j in range(len(ring_pts) - 1):
                if _segments_intersect(p1, p2, ring_pts[j], ring_pts[j + 1]):
                    return True
    return False


def get_active_hazard_zones():
    """Return all active hazard zones as dicts with parsed geometry."""
    rows = query_all(
        """
        SELECT hazard_zone_id, zone_name, description, polygon_geojson,
               severity, zone_status, source_name, last_verified_at,
               disaster_id
        FROM hazard_zones
        WHERE zone_status = 'ACTIVE'
        """
    )
    zones = []
    for r in rows:
        zones.append(
            {
                "hazard_zone_id": r["hazard_zone_id"],
                "zone_name": r["zone_name"],
                "description": r["description"],
                "polygon": _parse_geojson(r["polygon_geojson"]),
                "severity": r["severity"],
                "zone_status": r["zone_status"],
                "source_name": r["source_name"],
                "last_verified_at": r["last_verified_at"],
                "disaster_id": r["disaster_id"],
            }
        )
    return zones


def check_route_against_hazards(route_coords):
    """Check a route against all active hazard zones.

    Returns a dict:
        {
          "safe": bool,                 # True if no intersection
          "intersecting_zones": [zone dicts...],
          "message": str,
        }
    """
    zones = get_active_hazard_zones()
    intersecting = []
    for zone in zones:
        if route_intersects_hazard(route_coords, zone["polygon"]):
            intersecting.append(zone)
    return {
        "safe": len(intersecting) == 0,
        "intersecting_zones": intersecting,
        "message": (
            "Route avoids recorded hazard zones."
            if not intersecting
            else "Route crosses one or more recorded hazard zones."
        ),
    }
