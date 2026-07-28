"""
notam_service.py

NOTAMs (Notices to Air Missions) flag temporary hazards or changes:
closed runways, out-of-service equipment, airspace restrictions, etc.

Unlike weather, there isn't one free, globally-reliable, no-key NOTAM API.
The FAA does publish an official NOTAM API, but it requires registering
for a developer account/API key, and coverage is strongest for U.S.
airports. International NOTAM coverage through free/open sources is
much less consistent.

Design decision for this project:
- If a NOTAM_API_KEY is configured (see .env.example), we attempt a live
  fetch.
- If no key is configured, or the request fails, or the airport simply
  has no matching NOTAMs, we return an empty result rather than an error.
- The calling code (ai_briefing.py) is written to handle "no NOTAMs"
  gracefully - it just shifts the briefing's focus toward weather and
  flight-plan details instead of forcing this section to appear.

This mirrors how a real pilot briefing works: if NOTAM data isn't
available for a station, you don't invent one - you brief what you have.
"""

import os
import requests

REQUEST_TIMEOUT_SECONDS = 8

# Example endpoint pattern for a FAA-SWIM-backed NOTAM API. Replace this
# with whichever NOTAM provider you register for for - this is intentionally
# kept generic since providers differ in exact request format.
NOTAM_API_URL = os.environ.get("NOTAM_API_URL", "")
NOTAM_API_KEY = os.environ.get("NOTAM_API_KEY", "")


def fetch_notams(icao_code):
    """
    Attempt to fetch active NOTAMs for a single airport.

    Returns a list of plain NOTAM text strings. Returns an empty list
    (NOT an error) if no key is configured, the request fails, or there
    simply aren't any active NOTAMs - all three are normal outcomes.
    """
    # No NOTAM provider configured - skip silently. This is the expected
    # state for most people running this project from a fresh clone.
    if not NOTAM_API_URL or not NOTAM_API_KEY:
        return []

    try:
        response = requests.get(
            NOTAM_API_URL,
            params={"icao": icao_code},
            headers={"Authorization": f"Bearer {NOTAM_API_KEY}"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        # Expecting a list of NOTAM objects with a "body" or "text" field.
        # Adjust this parsing to match your chosen provider's response shape.
        notams = data.get("notams", [])
        return [n.get("body") or n.get("text", "") for n in notams if n]

    except (requests.RequestException, ValueError, AttributeError):
        # Fail softly - a missing/broken NOTAM feed should never break
        # the whole briefing.
        return []


def get_notams_for_airport(icao_code):
    """Convenience wrapper matching the shape used by other services."""
    notams = fetch_notams(icao_code)
    return {
        "icao": icao_code.upper(),
        "notams": notams,
        "available": len(notams) > 0,
    }
