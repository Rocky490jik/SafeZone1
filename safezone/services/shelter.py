"""SafeZone shelter search service."""

import math

from safezone.database.connection import query_all, query_one, db_transaction


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in kilometres."""
    R = 6371.0088  # Earth radius, km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def _row_to_dict(row):
    if row is None:
        return None
    return dict(row)


def get_shelter(shelter_id):
    row = query_one("SELECT * FROM shelters WHERE shelter_id = ?", (shelter_id,))
    return _row_to_dict(row)


def get_shelter_by_code(shelter_code):
    row = query_one(
        "SELECT * FROM shelters WHERE shelter_code = ?", (shelter_code,)
    )
    return _row_to_dict(row)


def search_shelters(lat, lon, radius_km=None, status=None, capacity_min=None,
                    facilities=None, limit=50):
    """Find shelters within radius_km of (lat, lon), with optional filters.

    facilities: list of facility keys among
        has_food, has_drinking_water, has_medical_support, has_accessibility
    Returns list of dicts with an added 'distance_km' key.
    """
    if radius_km is None:
        radius_km = 10.0

    sql = """
        SELECT shelter_id, shelter_code, name, description, address, city, state,
               postal_code, latitude, longitude, shelter_type, total_capacity,
               available_capacity, status, verification_status, contact_name,
               contact_phone, has_food, has_drinking_water, has_medical_support,
               has_accessibility, last_verified_at, created_at, updated_at
        FROM shelters
        WHERE verification_status = 'VERIFIED'
    """
    params = []

    if status:
        sql += " AND status = ?"
        params.append(status)

    if facilities:
        for f in facilities:
            if f in ("has_food", "has_drinking_water", "has_medical_support",
                     "has_accessibility"):
                sql += f" AND {f} = 1"

    rows = query_all(sql, tuple(params))

    results = []
    for r in rows:
        d = haversine_km(lat, lon, r["latitude"], r["longitude"])
        if d <= radius_km:
            item = dict(r)
            item["distance_km"] = round(d, 2)
            results.append(item)

    results.sort(key=lambda x: x["distance_km"])

    if capacity_min is not None:
        try:
            cap = int(capacity_min)
            results = [x for x in results if x["available_capacity"] >= cap]
        except (ValueError, TypeError):
            pass

    return results[:limit]


def list_all_shelters(limit=200):
    rows = query_all(
        """
        SELECT * FROM shelters
        ORDER BY verification_status DESC, status, name
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in rows]


def update_shelter_capacity(shelter_id, available_capacity, status, note, updated_by):
    """Update shelter capacity/status and log a shelter_update row."""
    with _transaction() as conn:
        conn.execute(
            """
            UPDATE shelters
            SET available_capacity = ?, status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE shelter_id = ?
            """,
            (available_capacity, status, shelter_id),
        )
        conn.execute(
            """
            INSERT INTO shelter_updates
            (shelter_id, updated_by, available_capacity, status, note, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (shelter_id, updated_by, available_capacity, status, note),
        )


def _transaction():
    from contextlib import contextmanager

    @contextmanager
    def cm():
        from safezone.database.connection import db_transaction
        with db_transaction() as conn:
            yield conn

    return cm()


def create_shelter(data, created_by):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO shelters
            (shelter_code, name, description, address, city, state, postal_code,
             latitude, longitude, shelter_type, total_capacity, available_capacity,
             status, verification_status, contact_name, contact_phone,
             has_food, has_drinking_water, has_medical_support, has_accessibility,
             last_verified_at, created_by, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            """,
            (
                data.get("shelter_code"), data.get("name"), data.get("description"),
                data.get("address"), data.get("city"), data.get("state"),
                data.get("postal_code"), data.get("latitude"), data.get("longitude"),
                data.get("shelter_type", "OTHER"),
                int(data.get("total_capacity") or 0),
                int(data.get("available_capacity") or 0),
                data.get("status", "OPEN"),
                data.get("verification_status", "PENDING"),
                data.get("contact_name"), data.get("contact_phone"),
                1 if data.get("has_food") else 0,
                1 if data.get("has_drinking_water") else 0,
                1 if data.get("has_medical_support") else 0,
                1 if data.get("has_accessibility") else 0,
                data.get("last_verified_at"), created_by,
            ),
        )
        return cur.lastrowid


def update_shelter(shelter_id, data, updated_by):
    fields = []
    params = []
    allowed = {
        "name": "name", "description": "description", "address": "address",
        "city": "city", "state": "state", "postal_code": "postal_code",
        "latitude": "latitude", "longitude": "longitude",
        "shelter_type": "shelter_type", "total_capacity": "total_capacity",
        "available_capacity": "available_capacity", "status": "status",
        "verification_status": "verification_status",
        "contact_name": "contact_name", "contact_phone": "contact_phone",
        "has_food": "has_food", "has_drinking_water": "has_drinking_water",
        "has_medical_support": "has_medical_support",
        "has_accessibility": "has_accessibility",
        "last_verified_at": "last_verified_at",
    }
    for key, col in allowed.items():
        if key in data:
            val = data[key]
            if key in ("has_food", "has_drinking_water", "has_medical_support",
                       "has_accessibility"):
                val = 1 if val else 0
            if key in ("total_capacity", "available_capacity"):
                val = int(val) if val not in (None, "") else 0
            fields.append(f"{col} = ?")
            params.append(val)
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(shelter_id)
    with db_transaction() as conn:
        conn.execute(
            f"UPDATE shelters SET {', '.join(fields)} WHERE shelter_id = ?",
            tuple(params),
        )


def delete_shelter(shelter_id):
    with db_transaction() as conn:
        conn.execute("DELETE FROM shelters WHERE shelter_id = ?", (shelter_id,))


# ---- audit helper ----------------------------------------------------------

def audit(user_id, action, entity_type, entity_id, details=None):
    with db_transaction() as conn:
        conn.execute(
            """
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details, created_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (user_id, action, entity_type, entity_id, details),
        )
