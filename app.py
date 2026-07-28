"""
app.py

Main Flask application for Aero Brief.

Route map:
  GET  /              -> serves the front-end page (templates/index.html)
  POST /api/briefing   -> accepts {departure, arrival} ICAO codes, gathers
                          weather/NOTAM/airport/route data, calls the AI
                          briefing synthesis, and returns everything as JSON

Run locally with:
    python app.py
"""

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

# Load variables from a local .env file (ANTHROPIC_API_KEY, and optionally
# NOTAM_API_URL / NOTAM_API_KEY) into the environment. This must happen
# before we import ai_briefing, since that module reads the API key at
# import time.
load_dotenv()

import airport_service
import weather_service
import notam_service
import flight_plan
import ai_briefing

app = Flask(__name__)


@app.route("/")
def index():
    """Serve the main (and only) page of the app."""
    return render_template("index.html")


@app.route("/api/briefing", methods=["POST"])
def get_briefing():
    """
    Main API endpoint. Expects a JSON body like:
        {"departure": "KJFK", "arrival": "EGLL"}

    Returns a JSON object containing the route summary, weather/NOTAM
    data for both airports, and the AI-generated briefing text.
    """
    body = request.get_json(silent=True) or {}
    departure_code = str(body.get("departure", "")).strip().upper()
    arrival_code = str(body.get("arrival", "")).strip().upper()

    # --- Basic input validation -------------------------------------
    if len(departure_code) != 4 or len(arrival_code) != 4:
        return jsonify({"error": "Please provide valid 4-letter ICAO codes for both airports."}), 400

    if departure_code == arrival_code:
        return jsonify({"error": "Departure and arrival airports must be different."}), 400

    # --- Gather data for each airport --------------------------------
    departure_data = gather_airport_data(departure_code)
    arrival_data = gather_airport_data(arrival_code)

    # --- Route / flight-plan math -------------------------------------
    route = flight_plan.build_route_summary(
        departure_data["airport"], arrival_data["airport"]
    )

    # --- AI synthesis ---------------------------------------------------
    try:
        briefing_text = ai_briefing.generate_briefing(departure_data, arrival_data, route)
    except Exception as exc:  # noqa: BLE001 - surface a clean error to the user
        return jsonify({
            "error": (
                "The briefing couldn't be generated. Check that GEMINI_API_KEY "
                f"is set correctly in your .env file. (Details: {exc})"
            )
        }), 502

    return jsonify({
        "route": route,
        "departure": departure_data,
        "arrival": arrival_data,
        "briefing_text": briefing_text,
    })


def gather_airport_data(icao_code):
    """
    Collect everything we know about a single airport: static info,
    live weather, and (best-effort) NOTAMs.
    """
    airport = airport_service.get_airport_info(icao_code)
    weather = weather_service.get_weather_for_airport(icao_code)
    notam_result = notam_service.get_notams_for_airport(icao_code)

    return {
        "airport": airport,
        "weather": {"metar": weather["metar"], "taf": weather["taf"]},
        "notams": notam_result["notams"],
    }


if __name__ == "__main__":
    # debug=True gives auto-reload + helpful error pages during local
    # development. Turn this off (or use a production WSGI server like
    # gunicorn) before deploying anywhere public.
    app.run(debug=True, port=5000)
