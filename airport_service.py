"""
airport_service.py

Handles everything related to static airport information: name, city,
country, coordinates, and elevation.

This data barely changes over time (an airport's elevation doesn't move),
so instead of hitting a paid airport-info API on every request, we load a
small curated JSON file bundled with the app. This keeps the project fully
runnable offline for airport metadata and removes one more point of
failure from the pipeline.

If a requested airport isn't in our local file, we still return a minimal
object so the rest of the app can keep working gracefully.
"""

import json
import os

# Path to the bundled airport dataset (static/data/airports.json)
AIRPORTS_FILE = os.path.join(
    os.path.dirname(__file__), "static", "data", "airports.json"
)


def _load_airport_data():
    """Read the airports.json file once and return it as a dictionary."""
    with open(AIRPORTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# Load the dataset a single time when this module is imported,
# rather than re-reading the file on every request.
_AIRPORT_DATA = _load_airport_data()


def get_airport_info(icao_code):
    """
    Look up a single airport by its 4-letter ICAO code (e.g. "KJFK").

    Returns a dictionary with name, city, country, lat, lon, and
    elevation_ft. If the code isn't found in our local dataset, returns
    a placeholder dictionary so the app can still continue (instead of
    crashing the whole request).
    """
    code = icao_code.strip().upper()
    airport = _AIRPORT_DATA.get(code)

    if airport is None:
        # Airport not in our curated list - return a safe fallback object.
        # This keeps the calling code simple (it never has to check for None).
        return {
            "icao": code,
            "name": "Unknown airport (not in local dataset)",
            "city": "Unknown",
            "country": "Unknown",
            "lat": None,
            "lon": None,
            "elevation_ft": None,
            "found": False,
        }

    # Merge the ICAO code into the returned dict for convenience.
    return {"icao": code, "found": True, **airport}


def is_known_airport(icao_code):
    """Quick boolean check used by the frontend/backend for validation."""
    return icao_code.strip().upper() in _AIRPORT_DATA
