"""SafeZone alert service."""

from safezone.database.connection import query_all, query_one, execute, db_transaction


def get_active_alerts():
    """Return published, non-expired alerts ordered by severity and time."""
    rows = query_all(
        """
        SELECT a.*, d.title AS disaster_title, d.disaster_type, d.severity AS disaster_severity
        FROM alerts a
        LEFT JOIN disaster_events d ON a.disaster_id = d.disaster_id
        WHERE a.alert_status = 'PUBLISHED'
          AND (a.expires_at IS NULL OR a.expires_at > CURRENT_TIMESTAMP)
        ORDER BY
          CASE a.severity WHEN 'CRITICAL' THEN 4 WHEN 'HIGH' THEN 3
               WHEN 'MODERATE' THEN 2 WHEN 'LOW' THEN 1 ELSE 0 END DESC,
          a.published_at DESC
        """
    )
    return [dict(r) for r in rows]


def get_all_alerts():
    rows = query_all(
        """
        SELECT a.*, d.title AS disaster_title
        FROM alerts a
        LEFT JOIN disaster_events d ON a.disaster_id = d.disaster_id
        ORDER BY a.created_at DESC
        """
    )
    return [dict(r) for r in rows]


def get_alert(alert_id):
    row = query_one("SELECT * FROM alerts WHERE alert_id = ?", (alert_id,))
    return dict(row) if row else None


def create_alert(data, created_by):
    with db_transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO alerts
            (disaster_id, title, message, severity, area_text, source_name,
             alert_status, published_at, expires_at, created_by, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            """,
            (
                data.get("disaster_id"), data.get("title"), data.get("message"),
                data.get("severity", "INFO"), data.get("area_text"),
                data.get("source_name", "ADMIN"),
                data.get("alert_status", "DRAFT"),
                data.get("published_at"), data.get("expires_at"), created_by,
            ),
        )
        return cur.lastrowid


def update_alert(alert_id, data, updated_by):
    fields = []
    params = []
    allowed = {
        "disaster_id": "disaster_id", "title": "title", "message": "message",
        "severity": "severity", "area_text": "area_text", "source_name": "source_name",
        "alert_status": "alert_status", "published_at": "published_at",
        "expires_at": "expires_at",
    }
    for key, col in allowed.items():
        if key in data:
            fields.append(f"{col} = ?")
            params.append(data[key])
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(alert_id)
    with db_transaction() as conn:
        conn.execute(
            f"UPDATE alerts SET {', '.join(fields)} WHERE alert_id = ?",
            tuple(params),
        )


def delete_alert(alert_id):
    with db_transaction() as conn:
        conn.execute("DELETE FROM alerts WHERE alert_id = ?", (alert_id,))
