"""SafeZone routing service using OSRM (Open Source Routing Machine)."""

import requests

from config import Config


def get_route(start_lat, start_lon, end_lat, end_lon):
    """Request a driving route from OSRM.

    OSRM expects coordinates as longitude,latitude. Returns a dict with the
    best route and any alternatives, or an error dict on failure.

    Return shape on success:
        {
          "ok": True,
          "routes": [
            {
              "distance_m": float,
              "duration_s": float,
              "distance_km": float,
              "duration_min": float,
              "geometry": [[lon, lat], ...],   # GeoJSON LineString coords
              "index": int,
            },
            ...
        ]
    On failure:
        {"ok": False, "error": str, "code": str}
    """
    # OSRM expects longitude,latitude in the URL.
    urls = [
        f"{Config.OSRM_BASE_URL}/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}",
        # HTTP fallback for environments where the public HTTPS endpoint
        # cannot be reached (e.g. older TLS stacks).
        f"http://router.project-osrm.org/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}",
    ]
    params = {
        "alternatives": "true",
        "overview": "full",
        "geometries": "geojson",
    }
    last_error = None
    for url in urls:
        try:
            resp = requests.get(url, params=params, timeout=Config.OSRM_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as exc:
            last_error = str(exc)
            continue
        except ValueError:
            last_error = "Invalid response from routing service"
            continue

        code = data.get("code")
        if code == "Ok" and data.get("routes"):
            routes = []
            for idx, route in enumerate(data["routes"]):
                geometry = route.get("geometry", {})
                coords = geometry.get("coordinates", [])  # already [lon, lat]
                routes.append(
                    {
                        "index": idx,
                        "distance_m": float(route.get("distance", 0)),
                        "duration_s": float(route.get("duration", 0)),
                        "distance_km": round(float(route.get("distance", 0)) / 1000.0, 2),
                        "duration_min": round(float(route.get("duration", 0)) / 60.0, 1),
                        "geometry": [[float(c[0]), float(c[1])] for c in coords],
                    }
                )
            routes.sort(key=lambda r: r["distance_m"])
            return {"ok": True, "routes": routes}
        last_error = data.get("message", "No route found")

    return {"ok": False, "error": last_error or "No route found", "code": "routing_failed"}
