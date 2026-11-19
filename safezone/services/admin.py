"""SafeZone admin service: disasters, hazard zones, contacts, users, audits."""

from safezone.database.connection import query_all, query_one, execute, db_transaction


# ---------------------------------------------------------------- disasters

def get_disasters(status=None):
    sql = "SELECT * FROM disaster_events"
    params = []
    if status:
        sql += " WHERE event_status = ?"
        params.append(status)
    sql += " ORDER BY starts_at DESC"
    rows = query_all(sql, tuple(params))
    return [dict(r) for r in rows]


def create_disaster(data, created_by):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO disaster_events
            (event_code, title, disaster_type, severity, description, affected_area,
             source_name, source_url, event_status, starts_at, ends_at, created_by,
             created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            """,
            (
                data.get("event_code"), data.get("title"), data.get("disaster_type"),
                data.get("severity"), data.get("description"), data.get("affected_area"),
                data.get("source_name", "ADMIN"), data.get("source_url"),
                data.get("event_status", "ACTIVE"), data.get("starts_at"),
                data.get("ends_at"), created_by,
            ),
        )
        return cur.lastrowid


def update_disaster(disaster_id, data, updated_by):
    fields = []
    params = []
    allowed = {
        "event_code": "event_code", "title": "title", "disaster_type": "disaster_type",
        "severity": "severity", "description": "description", "affected_area": "affected_area",
        "source_name": "source_name", "source_url": "source_url",
        "event_status": "event_status", "starts_at": "starts_at", "ends_at": "ends_at",
    }
    for key, col in allowed.items():
        if key in data:
            fields.append(f"{col} = ?")
            params.append(data[key])
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(disaster_id)
    with db_transaction() as conn:
        conn.execute(
            f"UPDATE disaster_events SET {', '.join(fields)} WHERE disaster_id = ?",
            tuple(params),
        )


def delete_disaster(disaster_id):
    with db_transaction() as conn:
        conn.execute("DELETE FROM disaster_events WHERE disaster_id = ?", (disaster_id,))


# ---------------------------------------------------------------- hazard zones

def get_hazard_zones(status=None):
    sql = "SELECT * FROM hazard_zones"
    params = []
    if status:
        sql += " WHERE zone_status = ?"
        params.append(status)
    sql += " ORDER BY created_at DESC"
    rows = query_all(sql, tuple(params))
    return [dict(r) for r in rows]


def create_hazard_zone(data, created_by):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO hazard_zones
            (disaster_id, zone_name, description, polygon_geojson, severity,
             zone_status, source_name, created_by, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            """,
            (
                data.get("disaster_id"), data.get("zone_name"), data.get("description"),
                data.get("polygon_geojson"), data.get("severity", "MODERATE"),
                data.get("zone_status", "ACTIVE"),
                data.get("source_name", "ADMIN"), created_by,
            ),
        )
        return cur.lastrowid


def update_hazard_zone(hazard_zone_id, data, updated_by):
    fields = []
    params = []
    allowed = {
        "disaster_id": "disaster_id", "zone_name": "zone_name",
        "description": "description", "polygon_geojson": "polygon_geojson",
        "severity": "severity", "zone_status": "zone_status",
        "source_name": "source_name",
    }
    for key, col in allowed.items():
        if key in data:
            fields.append(f"{col} = ?")
            params.append(data[key])
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(hazard_zone_id)
    with db_transaction() as conn:
        conn.execute(
            f"UPDATE hazard_zones SET {', '.join(fields)} WHERE hazard_zone_id = ?",
            tuple(params),
        )


def delete_hazard_zone(hazard_zone_id):
    with db_transaction() as conn:
        conn.execute("DELETE FROM hazard_zones WHERE hazard_zone_id = ?",
                     (hazard_zone_id,))


# ---------------------------------------------------------------- contacts

def get_emergency_contacts(active_only=True):
    sql = "SELECT * FROM emergency_contacts"
    params = []
    if active_only:
        sql += " WHERE is_active = 1"
    sql += " ORDER BY category, agency_name"
    rows = query_all(sql, tuple(params))
    return [dict(r) for r in rows]


def create_contact(data, created_by=None):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO emergency_contacts
            (agency_name, category, phone, area_text, source_name,
             is_verified, is_active, created_at)
            VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            """,
            (
                data.get("agency_name"), data.get("category"), data.get("phone"),
                data.get("area_text"), data.get("source_name", "ADMIN"),
                1 if data.get("is_verified") else 0,
                1 if data.get("is_active", True) else 0,
            ),
        )
        return cur.lastrowid


def update_contact(contact_id, data):
    fields = []
    params = []
    allowed = {
        "agency_name": "agency_name", "category": "category", "phone": "phone",
        "area_text": "area_text", "source_name": "source_name",
        "is_verified": "is_verified", "is_active": "is_active",
    }
    for key, col in allowed.items():
        if key in data:
            val = data[key]
            if key in ("is_verified", "is_active"):
                val = 1 if val else 0
            fields.append(f"{col} = ?")
            params.append(val)
    params.append(contact_id)
    with db_transaction() as conn:
        conn.execute(
            f"UPDATE emergency_contacts SET {', '.join(fields)} WHERE contact_id = ?",
            tuple(params),
        )


def delete_contact(contact_id):
    with db_transaction() as conn:
        conn.execute("DELETE FROM emergency_contacts WHERE contact_id = ?",
                     (contact_id,))


# ---------------------------------------------------------------- users / audit

def get_users():
    rows = query_all("SELECT * FROM users ORDER BY created_at DESC")
    return [dict(r) for r in rows]


def get_user(user_id):
    row = query_one("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return dict(row) if row else None


def get_user_by_email(email):
    row = query_one("SELECT * FROM users WHERE email = ?", (email,))
    return dict(row) if row else None


def create_user(full_name, email, password_hash, role="USER"):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, is_active,
                               created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """,
            (full_name, email, password_hash, role),
        )
        return cur.lastrowid


def update_user_role(user_id, role):
    with db_transaction() as conn:
        conn.execute(
            "UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (role, user_id),
        )


def deactivate_user(user_id):
    with db_transaction() as conn:
        conn.execute(
            "UPDATE users SET is_active = 0, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,),
        )


def get_audit_logs(limit=100):
    rows = query_all(
        """
        SELECT al.*, u.full_name AS actor_name
        FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.user_id
        ORDER BY al.created_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    return [dict(r) for r in rows]
