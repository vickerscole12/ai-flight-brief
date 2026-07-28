# Aero Brief, A GenAI Pre-Flight Briefing Assistant - Claude Code Experiment 

Aero Brief takes two airport codes (departure and arrival) and generates a
plain-language pre-flight briefing by combining live aviation weather data with an
LLM synthesis step.

Built as a portfolio project to demonstrate API integration, backend data
pipelines, and applied GenAI (turning structured/raw data into a readable
narrative), wrapped in a from-scratch HTML/CSS/JS front end. The AI
synthesis step uses Google's free Gemini API.

<img width="1523" height="876" alt="image" src="https://github.com/user-attachments/assets/2e33003c-e127-4bcc-8f41-37d5bd79f483" />

<img width="1527" height="799" alt="image" src="https://github.com/user-attachments/assets/b4e7f5d7-f632-4550-88ff-2a399a841c5c" />

## What it does

1. You enter two ICAO airport codes (e.g. `KJFK` and `EGLL`).
2. The backend fetches, in real time:
   - **METAR / TAF weather** for both airports, from the free public
     [aviationweather.gov API](https://aviationweather.gov/data/api/)
     (this covers airports worldwide, not just the U.S.)
   - **Airport info** (name, city, country, coordinates, elevation) from a
     small curated local dataset
   - **NOTAMs**, best-effort, if a NOTAM data provider is configured (see
     "About NOTAM coverage" below)
3. It calculates route info: great-circle distance, initial heading, and
   an estimated flight time.
4. All of that structured data is handed to Gemini, which synthesizes it
   into a single plain-English briefing.

## About NOTAM coverage

**NOTAM coverage is intentionally best-effort.** Unlike weather, there
isn't a single free, reliable, globally-comprehensive NOTAM API. The FAA
publishes an official NOTAM API, but it requires a registered developer
key and covers U.S. airports far more reliably than international ones.
Rather than fake NOTAM data or only support U.S. airports, this app:

- Attempts a live NOTAM fetch if `NOTAM_API_KEY` is configured
- Skips the NOTAM section gracefully (no errors, no placeholders) if it's
  not configured, or if there's simply nothing to report
- Shifts the AI briefing's focus toward weather hazards and flight-plan
  context whenever NOTAMs aren't available

This means the app works fully, for any airport pair worldwide, right out
of the box — NOTAMs are a bonus layer if you choose to wire up a provider.

## Tech stack

- **Python** — backend API, external data fetching, route math, and
  the Gemini API call
- **HTML** — page structure (`templates/index.html`)
- **CSS** — styling, linked as a standalone stylesheet (`static/style.css`)
- **JavaScript** — front-end interactivity, linked as a standalone script
  (`static/script.js`)

## Project structure

```
flight-briefing-app/
├── app.py                  # Flask app + /api/briefing endpoint
├── airport_service.py      # Static airport info lookups
├── weather_service.py      # Live METAR/TAF fetching
├── notam_service.py        # Best-effort NOTAM fetching
├── flight_plan.py          # Great-circle distance / bearing / time estimate
├── ai_briefing.py          # Prompt construction + Gemini API call
├── requirements.txt
├── .env.example
├── .gitignore
├── templates/
│   └── index.html
└── static/
    ├── style.css
    ├── script.js
    └── data/
        └── airports.json   # Curated local airport dataset
```

## Running it locally (VS Code)

1. **Clone the repo and open it in VS Code.**

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate      # on Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up your environment variables:**
   ```bash
   cp .env.example .env
   ```
   Then open `.env` and add your own `GEMINI_API_KEY` (get one for free,
   no credit card needed, at
   [aistudio.google.com/apikey](https://aistudio.google.com/apikey)).
   Leave the `NOTAM_*` variables blank unless you've registered for a
   NOTAM provider.

4. **Run the app:**
   ```bash
   python app.py
   ```

5. Open **http://localhost:5000** in your browser.

## Try it with

- `KJFK` → `EGLL` (New York to London — a well-covered U.S./international pair)
- `RJTT` → `WSSS` (Tokyo to Singapore — a fully international route)
- `KDEN` → `KLAX` (Denver to Los Angeles — a domestic U.S. route)

## Notes / limitations

- Flight time estimates use a flat average cruise speed and are meant to
  give a ballpark sense of trip length, not a dispatch-grade calculation.
- The curated airport dataset covers roughly 100 major world airports; an
  airport not in the list will still generate a briefing, just without
  full name/city/coordinate detail.
- This project is for portfolio/demo purposes and is **not** a real flight
  planning tool — always use official sources (like your national aviation
  authority or a certified EFB) for actual flight operations.

## Possible extensions

- Expand the local airport dataset (or swap in a live airport-info API)
- Add a caching layer so repeated requests for the same airport don't
  re-fetch weather every time
- Wire up a real NOTAM provider and expand international NOTAM coverage
- Add unit conversion (nm/km, ft/m) based on user preference
- Deploy it (e.g. Render, Railway, Fly.io) so it's live-linkable from your
  portfolio, not just runnable locally
