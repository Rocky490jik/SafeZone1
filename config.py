import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """SafeZone application configuration.

    The PRD specifies MySQL 8.0+, but this project ships with SQLite as the
    default database so it runs immediately without a database server. To use
    MySQL (as the PRD intends), set DATABASE_URL to a MySQL connection string
    and install mysql-connector-python.
    """
    SECRET_KEY = os.environ.get("SECRET_KEY", "safezone-dev-secret-change-me")
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = os.environ.get("WTF_CSRF_SECRET_KEY", "safezone-csrf-dev-change-me")

    # Database: SQLite by default (runs out of the box). Set DATABASE_URL to
    # a MySQL URI to switch per the PRD (e.g. mysql+connector://user:pass@host/db).
    DATABASE_URL = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "safezone.db")
    )

    # External services
    OSRM_BASE_URL = os.environ.get("OSRM_BASE_URL", "https://router.project-osrm.org")
    OSRM_TIMEOUT = int(os.environ.get("OSRM_TIMEOUT", "15"))

    # Map tile layer (OpenStreetMap)
    MAP_TILE_URL = os.environ.get(
        "MAP_TILE_URL",
        "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    )
    MAP_ATTRIBUTION = (
        '&copy; <a href="https://www.openstreetmap.org/copyright">'
        'OpenStreetMap contributors</a>'
    )

    # Default search radius (km) and demo center (Bengaluru, per sample data)
    DEFAULT_RADIUS_KM = float(os.environ.get("DEFAULT_RADIUS_KM", "10"))
    DEFAULT_LAT = float(os.environ.get("DEFAULT_LAT", "12.9716"))
    DEFAULT_LON = float(os.environ.get("DEFAULT_LON", "77.5946"))

    # Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("SESSION_LIFETIME", "3600"))  # seconds

    # Safety / demo disclaimer
    DISCLAIMER = (
        "SafeZone is a student project prototype. It is NOT a certified emergency "
        "response or life-safety system. Shelter availability, map data and hazard "
        "information may be incomplete, delayed or incorrect. Always follow official "
        "emergency instructions and local authorities."
    )
