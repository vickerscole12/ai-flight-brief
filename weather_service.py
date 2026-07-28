"""
weather_service.py

Fetches live aviation weather (METAR and TAF) from aviationweather.gov,
the U.S. National Weather Service's public aviation weather API.

Good news for this project: this API is NOT limited to U.S. airports.
Airlines fly internationally, so global airports (EGLL in London, RJTT
in Tokyo, etc.) are also covered. It requires no API key and returns
JSON directly, which makes it the most reliable "always works" data
source in this app.

METAR = current/recent observed weather at an airport.
TAF   = forecast weather at an airport for the next 24-30 hours.
"""

import requests

BASE_URL = "https://aviationweather.gov/api/data"

# Keep network calls polite and bounded - don't let a slow/unreachable
# API hang the whole request forever.
REQUEST_TIMEOUT_SECONDS = 8


def fetch_metar(icao_code):
    """
    Fetch the latest METAR (current weather observation) for an airport.

    Returns the raw METAR string, or None if unavailable/unreachable.
    We keep this as the raw string (rather than trying to fully parse it)
    because the LLM step later is very good at interpreting raw METAR
    text into plain language - that's exactly the kind of decoding task
    an LLM is well suited for.
    """
    try:
        response = requests.get(
            f"{BASE_URL}/metar",
            params={"ids": icao_code, "format": "json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            return None

        # The API returns a list of observations; take the most recent one.
        return data[0].get("rawOb")

    except (requests.RequestException, ValueError, IndexError, KeyError):
        # Any network hiccup, bad JSON, or unexpected shape -> fail softly.
        # The rest of the app is designed to handle "no weather data" too.
        return None


def fetch_taf(icao_code):
    """
    Fetch the latest TAF (forecast) for an airport.

    Returns the raw TAF string, or None if unavailable. Not every small
    airport issues a TAF, so a missing TAF is a normal, expected case,
    not an error.
    """
    try:
        response = requests.get(
            f"{BASE_URL}/taf",
            params={"ids": icao_code, "format": "json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()

        if not data:
            return None

        return data[0].get("rawTAF")

    except (requests.RequestException, ValueError, IndexError, KeyError):
        return None


def get_weather_for_airport(icao_code):
    """
    Convenience wrapper that fetches both METAR and TAF for one airport
    and returns them together in a single dictionary.
    """
    return {
        "icao": icao_code.upper(),
        "metar": fetch_metar(icao_code),
        "taf": fetch_taf(icao_code),
    }
