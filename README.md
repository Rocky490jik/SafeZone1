# SafeZone - Disaster Safe Shelter Locator

A responsive Flask web application for locating registered emergency shelters,
viewing administrator-published alerts, mapped hazard zones and hazard-aware
routing. Built per the SafeZone Detailed PRD.

## Stack
- Python 3, Flask 2.2.5
- SQLite (default, runs out of the box) — swap to MySQL per the PRD via DATABASE_URL
- Bootstrap 5, Leaflet.js, OpenStreetMap tiles
- OSRM public routing API
- Pure-Python route-vs-hazard intersection (no Shapely required)

## Quick start

1. Create a virtual environment and install dependencies:

```bash
cd SafeZone
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

2. Copy the example env file (optional):

```bash
copy .env.example .env       # Windows
# or: cp .env.example .env   # macOS/Linux
```

3. Run the app:

```bash
python app.py
```

4. Open http://127.0.0.1:5000 in your browser.

## Demo accounts

- **Administrator:** email `admin@safezone.demo`, password `admin123`
- **Regular user:** register a new account via the Create account page

The database (`safezone.db`) is created automatically on first run with the
fictional Bengaluru sample data from `SafeZone_Sample_Database.sql`.

## Key features (P1 from PRD)

- User registration / login / logout with server-side role authorization
- Browser geolocation with manual location fallback
- Nearby shelter search with distance, status, capacity and facility filters
- Shelter detail pages (capacity, facilities, contact, verification time)
- Interactive Leaflet map with shelter markers and hazard overlays
- OSRM driving routes with route-vs-hazard polygon intersection checks
- Published alerts (severity-labelled)
- Admin dashboard: shelter CRUD, disaster events, hazard zones, alerts,
  emergency contacts, users, activity log
- Responsive, mobile-friendly UI ("Calm, clear, ready")

## Safety notice

SafeZone is a student project prototype. All sample shelters, coordinates,
hazard zones, alerts and contacts are **fictional demo data**. It is NOT a
certified emergency response or life-safety system. Always follow official
emergency instructions and local authorities.

## Project structure

```
SafeZone/
  app.py                 # Flask application factory & entry point
  config.py              # Configuration
  requirements.txt       # Python dependencies
  .env.example           # Example environment variables
  safezone/              # Python package
    routes/              # Blueprint route modules (auth, user, admin, api)
    services/            # Business logic (shelter, routing, hazard, alert, admin)
    database/            # SQLite connection, schema & seed data
    utils/               # Validation & security helpers
  templates/             # Jinja2 HTML templates
  static/css/style.css   # Custom styles (PRD design tokens)
  static/js/             # (Leaflet logic is inline in templates)
  safezone.db            # SQLite database (created on first run)
```

## Switching to MySQL (per PRD)

The PRD specifies MySQL 8.0+. To use MySQL instead of SQLite:

1. Install a MySQL server and create the `safezone_db` database.
2. Install `pip install mysql-connector-python`.
3. Set `DATABASE_URL` in `.env` to your MySQL connection string.
4. Adjust `safezone/database/connection.py` to connect via MySQL Connector/Python
   (the schema SQL can be reused with minor dialect tweaks).
