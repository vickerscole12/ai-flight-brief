"""
flight_plan.py

Basic flight-plan math between two airports: great-circle distance,
initial compass bearing, and a rough estimated flight time.

This becomes especially important content when NOTAMs aren't available
(e.g. for international airports) - it gives the AI briefing something
concrete and route-specific to talk about instead of just weather.
"""

import math

EARTH_RADIUS_NM = 3440.065  # Earth's radius in nautical miles

# Rough average cruise speed used only for a ballpark time estimate.
# Real flight times vary by aircraft type, winds, and routing -
# this is intentionally a simple estimate, not a dispatch-grade figure.
ASSUMED_CRUISE_SPEED_KTS = 480


def _to_radians(degrees):
    return degrees * math.pi / 180


def _to_degrees(radians):
    return radians * 180 / math.pi


def great_circle_distance_nm(lat1, lon1, lat2, lon2):
    """
    Calculate the great-circle distance between two coordinates using
    the haversine formula. Returns distance in nautical miles.
    """
    phi1, phi2 = _to_radians(lat1), _to_radians(lat2)
    d_phi = _to_radians(lat2 - lat1)
    d_lambda = _to_radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_NM * c


def initial_bearing_deg(lat1, lon1, lat2, lon2):
    """
    Calculate the initial compass bearing (in degrees, 0-360) needed to
    travel from point 1 to point 2 along the great-circle route.
    """
    phi1, phi2 = _to_radians(lat1), _to_radians(lat2)
    d_lambda = _to_radians(lon2 - lon1)

    x = math.sin(d_lambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(
        d_lambda
    )

    bearing = _to_degrees(math.atan2(x, y))
    return round((bearing + 360) % 360)


def estimate_flight_time(distance_nm):
    """
    Very rough flight time estimate based on an assumed average cruise
    speed. Returns a human-readable string like "4h 12m".

    This is meant to give the briefing a ballpark sense of trip length,
    not a precise dispatch calculation (real times depend on aircraft
    type, winds aloft, routing, and climb/descent profiles).
    """
    hours_decimal = distance_nm / ASSUMED_CRUISE_SPEED_KTS
    hours = int(hours_decimal)
    minutes = round((hours_decimal - hours) * 60)

    if minutes == 60:
        hours += 1
        minutes = 0

    return f"{hours}h {minutes}m"


def midpoint(lat1, lon1, lat2, lon2):
    """
    Calculate the approximate midpoint of the great-circle route between
    two coordinates. Returns (lat, lon) in degrees.

    This gives the AI briefing step a concrete geographic reference point
    to reason about - e.g. "the midpoint falls over the North Atlantic"
    or "the midpoint falls near the Rockies" - instead of just a distance
    and bearing number with nothing else to describe.
    """
    phi1, phi2 = _to_radians(lat1), _to_radians(lat2)
    lambda1, lambda2 = _to_radians(lon1), _to_radians(lon2)

    bx = math.cos(phi2) * math.cos(lambda2 - lambda1)
    by = math.cos(phi2) * math.sin(lambda2 - lambda1)

    mid_phi = math.atan2(
        math.sin(phi1) + math.sin(phi2),
        math.sqrt((math.cos(phi1) + bx) ** 2 + by ** 2),
    )
    mid_lambda = lambda1 + math.atan2(by, math.cos(phi1) + bx)

    return round(_to_degrees(mid_phi), 2), round(_to_degrees(mid_lambda), 2)


def build_route_summary(departure_airport, arrival_airport):
    """
    Given two airport dictionaries (as returned by airport_service),
    return a dictionary describing the route between them.

    If either airport is missing coordinates (i.e. it wasn't found in
    our local dataset), we return placeholder values rather than
    crashing - the AI briefing step is written to handle this gracefully.
    """
    dep_lat, dep_lon = departure_airport.get("lat"), departure_airport.get("lon")
    arr_lat, arr_lon = arrival_airport.get("lat"), arrival_airport.get("lon")

    if None in (dep_lat, dep_lon, arr_lat, arr_lon):
        return {
            "departure_icao": departure_airport["icao"],
            "arrival_icao": arrival_airport["icao"],
            "distance_nm": "unknown",
            "initial_bearing_deg": "unknown",
            "estimated_flight_time": "unknown (airport coordinates unavailable)",
            "midpoint_lat": "unknown",
            "midpoint_lon": "unknown",
        }

    distance = great_circle_distance_nm(dep_lat, dep_lon, arr_lat, arr_lon)
    bearing = initial_bearing_deg(dep_lat, dep_lon, arr_lat, arr_lon)
    mid_lat, mid_lon = midpoint(dep_lat, dep_lon, arr_lat, arr_lon)

    return {
        "departure_icao": departure_airport["icao"],
        "arrival_icao": arrival_airport["icao"],
        "distance_nm": round(distance),
        "initial_bearing_deg": bearing,
        "estimated_flight_time": estimate_flight_time(distance),
        "midpoint_lat": mid_lat,
        "midpoint_lon": mid_lon,
    }