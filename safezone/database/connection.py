"""SafeZone database layer.

SQLite implementation that mirrors the PRD's MySQL schema (safezone_db) so the
application runs without a database server. The same tables, columns and
constraints are preserved as closely as SQLite allows. Swap in MySQL via
DATABASE_URL per the PRD if a MySQL server is available.
"""

import json
import os
import sqlite3
from contextlib import contextmanager

from config import Config


def get_db_path():
    db_url = Config.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        return db_url[len("sqlite:///"):]
    return None


def get_connection():
    """Return a SQLite connection with row factory and foreign keys enabled."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_transaction():
    """Context manager that commits on success and rolls back on exception."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def query_one(sql, params=()):
    with db_transaction() as conn:
        cur = conn.execute(sql, params)
        return cur.fetchone()


def query_all(sql, params=()):
    with db_transaction() as conn:
        cur = conn.execute(sql, params)
        return cur.fetchall()


def execute(sql, params=()):
    with db_transaction() as conn:
        cur = conn.execute(sql, params)
        return cur


def last_insert_id():
    """Return the last inserted row id using a fresh connection."""
    conn = get_connection()
    try:
        cur = conn.execute("SELECT last_insert_rowid() AS id")
        row = cur.fetchone()
        return row["id"] if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Schema (mirrors PRD MySQL schema, adapted for SQLite)
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(190) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(25) NULL,
    role TEXT NOT NULL DEFAULT 'USER' CHECK (role IN ('USER','ADMIN')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shelters (
    shelter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shelter_code VARCHAR(30) NOT NULL UNIQUE,
    name VARCHAR(160) NOT NULL,
    description TEXT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(15) NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    shelter_type TEXT NOT NULL DEFAULT 'OTHER' CHECK (shelter_type IN ('COMMUNITY_HALL','SCHOOL','GOVERNMENT_CENTRE','HEALTH_CENTRE','OTHER')),
    total_capacity INTEGER UNSIGNED NOT NULL DEFAULT 0,
    available_capacity INTEGER UNSIGNED NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','FULL','CLOSED')),
    verification_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (verification_status IN ('PENDING','VERIFIED','REJECTED')),
    contact_name VARCHAR(120) NULL,
    contact_phone VARCHAR(25) NULL,
    has_food INTEGER NOT NULL DEFAULT 0,
    has_drinking_water INTEGER NOT NULL DEFAULT 0,
    has_medical_support INTEGER NOT NULL DEFAULT 0,
    has_accessibility INTEGER NOT NULL DEFAULT 0,
    last_verified_at DATETIME NULL,
    created_by BIGINT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_shelters_created_by FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT chk_shelter_capacity CHECK (available_capacity <= total_capacity)
);

CREATE TABLE IF NOT EXISTS disaster_events (
    disaster_id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_code VARCHAR(30) NOT NULL UNIQUE,
    title VARCHAR(180) NOT NULL,
    disaster_type TEXT NOT NULL CHECK (disaster_type IN ('FLOOD','FIRE','EARTHQUAKE','LANDSLIDE','CYCLONE','STORM','OTHER')),
    severity TEXT NOT NULL CHECK (severity IN ('LOW','MODERATE','HIGH','CRITICAL')),
    description TEXT NOT NULL,
    affected_area VARCHAR(180) NULL,
    source_name VARCHAR(120) NOT NULL DEFAULT 'ADMIN DEMO ENTRY',
    source_url VARCHAR(500) NULL,
    event_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (event_status IN ('ACTIVE','RESOLVED','EXPIRED')),
    starts_at DATETIME NOT NULL,
    ends_at DATETIME NULL,
    created_by BIGINT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_disaster_created_by FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS hazard_zones (
    hazard_zone_id INTEGER PRIMARY KEY AUTOINCREMENT,
    disaster_id BIGINT NULL,
    zone_name VARCHAR(160) NOT NULL,
    description TEXT NULL,
    polygon_geojson TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('LOW','MODERATE','HIGH','CRITICAL')),
    zone_status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (zone_status IN ('ACTIVE','INACTIVE')),
    source_name VARCHAR(120) NOT NULL DEFAULT 'ADMIN DEMO ENTRY',
    last_verified_at DATETIME NULL,
    created_by BIGINT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_hazard_disaster FOREIGN KEY (disaster_id) REFERENCES disaster_events(disaster_id) ON DELETE SET NULL,
    CONSTRAINT fk_hazard_created_by FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    disaster_id BIGINT NULL,
    title VARCHAR(180) NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('INFO','LOW','MODERATE','HIGH','CRITICAL')),
    area_text VARCHAR(180) NULL,
    source_name VARCHAR(120) NOT NULL DEFAULT 'ADMIN DEMO ENTRY',
    alert_status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (alert_status IN ('DRAFT','PUBLISHED','EXPIRED')),
    published_at DATETIME NULL,
    expires_at DATETIME NULL,
    created_by BIGINT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_alert_disaster FOREIGN KEY (disaster_id) REFERENCES disaster_events(disaster_id) ON DELETE SET NULL,
    CONSTRAINT fk_alert_created_by FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS shelter_updates (
    update_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shelter_id BIGINT NOT NULL,
    updated_by BIGINT NULL,
    available_capacity INTEGER UNSIGNED NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('OPEN','FULL','CLOSED')),
    note VARCHAR(500) NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_update_shelter FOREIGN KEY (shelter_id) REFERENCES shelters(shelter_id) ON DELETE CASCADE,
    CONSTRAINT fk_update_user FOREIGN KEY (updated_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS emergency_contacts (
    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    agency_name VARCHAR(160) NOT NULL,
    category VARCHAR(80) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    area_text VARCHAR(180) NULL,
    source_name VARCHAR(120) NOT NULL DEFAULT 'ADMIN DEMO ENTRY',
    is_verified INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    last_verified_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id BIGINT NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(80) NOT NULL,
    entity_id BIGINT NULL,
    details TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_shelter_location ON shelters(city, state, status, verification_status);
CREATE INDEX IF NOT EXISTS idx_shelter_coordinates ON shelters(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_disaster_status ON disaster_events(event_status, severity, starts_at);
CREATE INDEX IF NOT EXISTS idx_hazard_status ON hazard_zones(zone_status, severity);
CREATE INDEX IF NOT EXISTS idx_alert_status ON alerts(alert_status, severity, published_at);
CREATE INDEX IF NOT EXISTS idx_update_shelter_time ON shelter_updates(shelter_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id, created_at);
"""


# ---------------------------------------------------------------------------
# Seed data (mirrors SafeZone_Sample_Database.sql)
# ---------------------------------------------------------------------------

def _bool(val):
    return 1 if val else 0


SEED_SHELTERS = [
    {
        "shelter_code": "DEMO-SH-001",
        "name": "Demo Community Relief Hall",
        "description": "Fictional shelter record for interface testing.",
        "address": "Demo Road, Central Area",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560001",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "shelter_type": "COMMUNITY_HALL",
        "total_capacity": 150,
        "available_capacity": 85,
        "status": "OPEN",
        "verification_status": "VERIFIED",
        "contact_name": "Demo Coordinator",
        "contact_phone": "0000000000",
        "has_food": 1,
        "has_drinking_water": 1,
        "has_medical_support": 0,
        "has_accessibility": 1,
        "last_verified_at": "2026-11-01 10:00:00",
    },
    {
        "shelter_code": "DEMO-SH-002",
        "name": "Demo School Relief Centre",
        "description": "Fictional shelter record for interface testing.",
        "address": "Demo Street, East Area",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560038",
        "latitude": 12.978,
        "longitude": 77.606,
        "shelter_type": "SCHOOL",
        "total_capacity": 200,
        "available_capacity": 40,
        "status": "OPEN",
        "verification_status": "VERIFIED",
        "contact_name": "Demo Coordinator",
        "contact_phone": "0000000000",
        "has_food": 1,
        "has_drinking_water": 1,
        "has_medical_support": 1,
        "has_accessibility": 1,
        "last_verified_at": "2026-11-01 09:30:00",
    },
    {
        "shelter_code": "DEMO-SH-003",
        "name": "Demo Sports Complex Shelter",
        "description": "Fictional shelter record for interface testing.",
        "address": "Demo Layout, South Area",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560004",
        "latitude": 12.96,
        "longitude": 77.58,
        "shelter_type": "GOVERNMENT_CENTRE",
        "total_capacity": 100,
        "available_capacity": 0,
        "status": "FULL",
        "verification_status": "VERIFIED",
        "contact_name": "Demo Coordinator",
        "contact_phone": "0000000000",
        "has_food": 0,
        "has_drinking_water": 1,
        "has_medical_support": 1,
        "has_accessibility": 0,
        "last_verified_at": "2026-11-01 08:45:00",
    },
    {
        "shelter_code": "DEMO-SH-004",
        "name": "Demo Health and Relief Point",
        "description": "Fictional shelter record for interface testing.",
        "address": "Demo Avenue, West Area",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560020",
        "latitude": 12.985,
        "longitude": 77.57,
        "shelter_type": "HEALTH_CENTRE",
        "total_capacity": 80,
        "available_capacity": 55,
        "status": "OPEN",
        "verification_status": "PENDING",
        "contact_name": "Demo Coordinator",
        "contact_phone": "0000000000",
        "has_food": 1,
        "has_drinking_water": 1,
        "has_medical_support": 1,
        "has_accessibility": 1,
        "last_verified_at": None,
    },
    {
        "shelter_code": "DEMO-SH-005",
        "name": "Demo Ward Shelter",
        "description": "Fictional shelter record for interface testing.",
        "address": "Demo Cross, South-East Area",
        "city": "Bengaluru",
        "state": "Karnataka",
        "postal_code": "560011",
        "latitude": 12.948,
        "longitude": 77.61,
        "shelter_type": "OTHER",
        "total_capacity": 120,
        "available_capacity": 25,
        "status": "OPEN",
        "verification_status": "VERIFIED",
        "contact_name": "Demo Coordinator",
        "contact_phone": "0000000000",
        "has_food": 1,
        "has_drinking_water": 1,
        "has_medical_support": 0,
        "has_accessibility": 1,
        "last_verified_at": "2026-10-31 16:00:00",
    },
]

SEED_DISASTERS = [
    {
        "event_code": "DEMO-EV-001",
        "title": "DEMO ONLY - Sample Flood Advisory",
        "disaster_type": "FLOOD",
        "severity": "HIGH",
        "description": "Fictional event used to test alert cards and hazard-zone overlays. Not a real warning.",
        "affected_area": "Demo Central Area, Bengaluru",
        "source_name": "DEMO DATA - NOT OFFICIAL",
        "source_url": None,
        "event_status": "ACTIVE",
        "starts_at": "2026-11-02 08:00:00",
        "ends_at": None,
    },
    {
        "event_code": "DEMO-EV-002",
        "title": "DEMO ONLY - Sample Road Closure",
        "disaster_type": "OTHER",
        "severity": "MODERATE",
        "description": "Fictional event used to test routing checks. Not a real road closure.",
        "affected_area": "Demo East Area, Bengaluru",
        "source_name": "DEMO DATA - NOT OFFICIAL",
        "source_url": None,
        "event_status": "ACTIVE",
        "starts_at": "2026-11-02 09:00:00",
        "ends_at": None,
    },
]

SEED_HAZARD_ZONES = [
    {
        "disaster_id": 1,
        "zone_name": "DEMO HAZARD ZONE A - Central",
        "description": "Fictional polygon for testing route intersection. Not a real affected area.",
        "polygon_geojson": json.dumps({
            "type": "Polygon",
            "coordinates": [[
                [77.59, 12.97], [77.599, 12.97],
                [77.599, 12.976], [77.59, 12.976],
                [77.59, 12.97],
            ]],
        }),
        "severity": "HIGH",
        "zone_status": "ACTIVE",
        "source_name": "DEMO DATA - NOT OFFICIAL",
    },
    {
        "disaster_id": 2,
        "zone_name": "DEMO HAZARD ZONE B - East",
        "description": "Fictional polygon for testing map styling. Not a real affected area.",
        "polygon_geojson": json.dumps({
            "type": "Polygon",
            "coordinates": [[
                [77.603, 12.975], [77.611, 12.975],
                [77.611, 12.981], [77.603, 12.981],
                [77.603, 12.975],
            ]],
        }),
        "severity": "MODERATE",
        "zone_status": "ACTIVE",
        "source_name": "DEMO DATA - NOT OFFICIAL",
    },
]

SEED_ALERTS = [
    {
        "disaster_id": 1,
        "title": "DEMO ONLY: Flood advisory sample",
        "message": "This is fictional sample content for testing the SafeZone alert interface. Do not treat it as a real warning.",
        "severity": "HIGH",
        "area_text": "Demo Central Area, Bengaluru",
        "source_name": "DEMO DATA - NOT OFFICIAL",
        "alert_status": "PUBLISHED",
        "published_at": "2026-11-02 08:15:00",
        "expires_at": "2027-06-01 00:00:00",
    },
    {
        "disaster_id": 2,
        "title": "DEMO ONLY: Road closure sample",
        "message": "This is fictional sample content for testing hazard-aware route checks. Do not treat it as a real closure.",
        "severity": "MODERATE",
        "area_text": "Demo East Area, Bengaluru",
        "source_name": "DEMO DATA - NOT OFFICIAL",
        "alert_status": "PUBLISHED",
        "published_at": "2026-11-02 09:15:00",
        "expires_at": "2027-06-01 00:00:00",
    },
]

SEED_EMERGENCY_CONTACTS = [
    {
        "agency_name": "DEMO ONLY - Replace with verified authority",
        "category": "EMERGENCY",
        "phone": "0000000000",
        "area_text": "Bengaluru",
        "source_name": "DEMO DATA - NOT OFFICIAL",
        "is_verified": 0,
        "is_active": 1,
    },
    {
        "agency_name": "DEMO ONLY - Replace with verified medical contact",
        "category": "MEDICAL",
        "phone": "0000000000",
        "area_text": "Bengaluru",
        "source_name": "DEMO DATA - NOT OFFICIAL",
        "is_verified": 0,
        "is_active": 1,
    },
]


def init_db(create_admin=True):
    """Initialize the database schema and seed sample data.

    Idempotent: safe to run on an existing database.
    """
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)

        # Seed shelters only if the table is empty
        count = conn.execute("SELECT COUNT(*) AS c FROM shelters").fetchone()["c"]
        if count == 0:
            admin_id = None
            if create_admin:
                admin_id = _ensure_admin(conn)
            for s in SEED_SHELTERS:
                conn.execute(
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
                        s["shelter_code"], s["name"], s["description"], s["address"],
                        s["city"], s["state"], s["postal_code"], s["latitude"],
                        s["longitude"], s["shelter_type"], s["total_capacity"],
                        s["available_capacity"], s["status"], s["verification_status"],
                        s["contact_name"], s["contact_phone"], s["has_food"],
                        s["has_drinking_water"], s["has_medical_support"],
                        s["has_accessibility"], s["last_verified_at"], admin_id,
                    ),
                )

        # Seed disaster events
        count = conn.execute("SELECT COUNT(*) AS c FROM disaster_events").fetchone()["c"]
        if count == 0:
            admin_id = _admin_user_id(conn)
            for d in SEED_DISASTERS:
                conn.execute(
                    """
                    INSERT INTO disaster_events
                    (event_code, title, disaster_type, severity, description, affected_area,
                     source_name, source_url, event_status, starts_at, ends_at, created_by,
                     created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                    """,
                    (
                        d["event_code"], d["title"], d["disaster_type"], d["severity"],
                        d["description"], d["affected_area"], d["source_name"],
                        d["source_url"], d["event_status"], d["starts_at"], d["ends_at"],
                        admin_id,
                    ),
                )

        # Seed hazard zones
        count = conn.execute("SELECT COUNT(*) AS c FROM hazard_zones").fetchone()["c"]
        if count == 0:
            admin_id = _admin_user_id(conn)
            for z in SEED_HAZARD_ZONES:
                conn.execute(
                    """
                    INSERT INTO hazard_zones
                    (disaster_id, zone_name, description, polygon_geojson, severity,
                     zone_status, source_name, created_by, created_at, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
                    """,
                    (
                        z["disaster_id"], z["zone_name"], z["description"],
                        z["polygon_geojson"], z["severity"], z["zone_status"],
                        z["source_name"], admin_id,
                    ),
                )

        # Seed alerts
        count = conn.execute("SELECT COUNT(*) AS c FROM alerts").fetchone()["c"]
        if count == 0:
            admin_id = _admin_user_id(conn)
            for a in SEED_ALERTS:
                conn.execute(
                    """
                    INSERT INTO alerts
                    (disaster_id, title, message, severity, area_text, source_name,
                     alert_status, published_at, expires_at, created_by, created_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                    """,
                    (
                        a["disaster_id"], a["title"], a["message"], a["severity"],
                        a["area_text"], a["source_name"], a["alert_status"],
                        a["published_at"], a["expires_at"], admin_id,
                    ),
                )

        # Seed emergency contacts
        count = conn.execute("SELECT COUNT(*) AS c FROM emergency_contacts").fetchone()["c"]
        if count == 0:
            for c in SEED_EMERGENCY_CONTACTS:
                conn.execute(
                    """
                    INSERT INTO emergency_contacts
                    (agency_name, category, phone, area_text, source_name,
                     is_verified, is_active, created_at)
                    VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                    """,
                    (
                        c["agency_name"], c["category"], c["phone"], c["area_text"],
                        c["source_name"], c["is_verified"], c["is_active"],
                    ),
                )

        conn.commit()
    finally:
        conn.close()


def _ensure_admin(conn):
    """Create a default admin account if none exists. Returns the user_id."""
    row = conn.execute(
        "SELECT user_id FROM users WHERE role = 'ADMIN' LIMIT 1"
    ).fetchone()
    if row:
        return row["user_id"]
    from werkzeug.security import generate_password_hash
    cur = conn.execute(
        """
        INSERT INTO users (full_name, email, password_hash, role, is_active, created_at, updated_at)
        VALUES (?, ?, ?, 'ADMIN', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (
            "SafeZone Administrator",
            "admin@safezone.demo",
            generate_password_hash("admin123"),
        ),
    )
    return cur.lastrowid


def _admin_user_id(conn):
    row = conn.execute("SELECT user_id FROM users WHERE role = 'ADMIN' ORDER BY user_id LIMIT 1").fetchone()
    if row:
        return row["user_id"]
    return _ensure_admin(conn)
