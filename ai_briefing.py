"""
ai_briefing.py

This is the "GenAI" heart of the project. It takes the structured data
we've already gathered (weather, NOTAMs, route info) and asks an LLM to
synthesize it into a single, plain-English pre-flight briefing - the
kind of narrative summary a human dispatcher or pilot would actually
want to read, rather than a wall of raw METAR/TAF/NOTAM codes.

This version uses Google's Gemini API, which has a genuinely free,
non-expiring tier (unlike one-time trial credits) - a good fit for a
portfolio project people might come back to and click on later.

Design note on the NOTAM fallback: the prompt explicitly tells the
model whether NOTAMs were available. If they weren't (common for
non-U.S. airports, or if no NOTAM_API_KEY is configured), we instruct
the model to lean more heavily into weather hazards and route/flight-
plan context instead of inventing or guessing at NOTAM-like content.
"""

from google import genai
from google.genai import types

# The client reads its API key from the GEMINI_API_KEY environment
# variable automatically - never hardcode a key in source code.
client = genai.Client()

# Model used for the briefing synthesis. We use the "flash-latest" alias
# rather than a pinned version like "gemini-2.5-flash" - Google frequently
# retires specific model versions (sometimes with little warning), and
# this alias is automatically kept pointed at whatever current Flash
# model is active, so the app doesn't break every time that happens.
# See https://ai.google.dev/gemini-api/docs/models for details on aliases.
MODEL_NAME = "gemini-flash-latest"


def build_prompt(departure, arrival, route):
    """
    Assemble a single structured text block describing everything we
    know, to hand to the model as the user message. Keeping this as
    one clearly-labeled block (rather than scattering the data across
    many messages) makes it easy for the model to reference specific
    facts accurately.
    """
    dep_airport = departure["airport"]
    arr_airport = arrival["airport"]

    dep_notams = departure["notams"]
    arr_notams = arrival["notams"]
    notams_available = bool(dep_notams or arr_notams)

    notam_section = "No NOTAM data was available for either airport."
    if notams_available:
        lines = [f"- [{dep_airport['icao']}] {n}" for n in dep_notams]
        lines += [f"- [{arr_airport['icao']}] {n}" for n in arr_notams]
        notam_section = "\n".join(lines)

    prompt = f"""
DEPARTURE AIRPORT: {dep_airport['icao']} - {dep_airport['name']}, {dep_airport['city']}, {dep_airport['country']}
DEPARTURE COORDINATES: {dep_airport.get('lat')}, {dep_airport.get('lon')}
DEPARTURE METAR: {departure['weather']['metar'] or 'not available'}
DEPARTURE TAF: {departure['weather']['taf'] or 'not available'}

ARRIVAL AIRPORT: {arr_airport['icao']} - {arr_airport['name']}, {arr_airport['city']}, {arr_airport['country']}
ARRIVAL COORDINATES: {arr_airport.get('lat')}, {arr_airport.get('lon')}
ARRIVAL METAR: {arrival['weather']['metar'] or 'not available'}
ARRIVAL TAF: {arrival['weather']['taf'] or 'not available'}

ROUTE:
- Great-circle distance: {route['distance_nm']} nm
- Initial bearing from departure: {route['initial_bearing_deg']} degrees
- Approximate route midpoint coordinates: {route['midpoint_lat']}, {route['midpoint_lon']}
- Estimated flight time: {route['estimated_flight_time']}

NOTAMS:
{notam_section}

NOTAM DATA AVAILABLE: {"yes" if notams_available else "no"}
""".strip()

    return prompt, notams_available


SYSTEM_PROMPT = """
You are a flight dispatcher writing a plain-language pre-flight briefing
for a pilot. You will be given raw METAR/TAF weather data, route
information (including departure/arrival coordinates and the
approximate midpoint of the great-circle route), and (sometimes) NOTAM
data.

Write a clear, well-organized briefing in plain English that a pilot
could read in a couple of minutes. Structure it with these sections:

1. ROUTE OVERVIEW - state the distance, heading, and flight time
   briefly (one or two sentences - do not dwell here, the next section
   is where the real route content goes).

2. ROUTE & GEOGRAPHY - this is the section to spend the most effort on.
   Using your own knowledge of world geography and the given departure/
   arrival/midpoint coordinates, describe what a typical flight along
   this great-circle path would actually cross: which countries,
   regions, coastlines, mountain ranges, or oceans it passes over or
   near; whether it's a domestic, continental, or oceanic crossing;
   typical cruise altitude for a trip of this distance; and anything
   operationally relevant about that geography (e.g. limited diversion
   airports over open ocean or high terrain, typical oceanic track
   systems like the North Atlantic Tracks if applicable, jet stream/
   prevailing wind effects on route time, or notable time zone changes).
   Be specific and substantive here, not generic - name actual places
   and features where you can reasonably infer them from the
   coordinates given.

3. DEPARTURE WEATHER - start this section with one or two clear plain-
   English sentences that decode exactly what the current METAR states:
   wind direction/speed, visibility, sky condition/ceiling, temperature
   and dew point, and altimeter setting. Translate the raw code fully -
   do not just restate the METAR string. After that plain-English METAR
   summary, add a short TAF-based outlook if a TAF is available (how
   conditions are expected to trend over the next several hours).

4. ARRIVAL WEATHER - same treatment: a plain-English METAR decode first,
   then a TAF-based outlook if available.

5. NOTAMS / OTHER CONSIDERATIONS - if NOTAM data was available,
   summarize it plainly. If NOTAM data was NOT available, do not invent
   or guess at NOTAMs - instead, state clearly that no NOTAM data was
   available for this briefing.

Keep the tone professional but conversational, the way an experienced
dispatcher would talk to a pilot - not overly formal, not casual.
Do not use markdown formatting like asterisks or pound signs; write in
plain text with simple section headers in capital letters.
""".strip()


def generate_briefing(departure, arrival, route):
    """
    Calls the Gemini API to synthesize the gathered data into a
    plain-language briefing. Returns the briefing text as a string.
    """
    user_prompt, notams_available = build_prompt(departure, arrival, route)

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=3000,
        ),
    )

    return _extract_text(response)


def _extract_text(response):
    """
    Pull the visible text out of a Gemini response.

    Some Gemini models include internal "thinking" content alongside the
    visible answer. response.text is usually enough, but different model
    versions behind aliases (like "gemini-flash-latest") can behave
    slightly differently, so we fall back to manually walking the
    response parts and joining only the actual text pieces - this keeps
    the app working even if the model swapped in behind the alias
    changes its exact response shape.
    """
    if response.text:
        return response.text

    # Fallback: manually collect text from the response's content parts.
    try:
        candidate = response.candidates[0]
        parts = candidate.content.parts or []
        text_pieces = [part.text for part in parts if getattr(part, "text", None)]
        if text_pieces:
            return "".join(text_pieces)
    except (AttributeError, IndexError):
        pass

    return (
        "The model didn't return any briefing text for this request. "
        "Please try generating the briefing again."
    )