/**
 * script.js
 *
 * Handles all browser-side behavior for Aero Brief:
 *  1. Reads the departure/arrival ICAO codes from the form
 *  2. Sends them to our own Flask backend (/api/briefing)
 *  3. Renders the structured weather/NOTAM/route data
 *  4. Renders the AI-synthesized plain-language briefing
 *
 * All actual data fetching (weather, NOTAMs, airport info, and the
 * call to the Claude API) happens server-side in Python. This file
 * never calls external aviation APIs directly - it only talks to our
 * own backend, which keeps API keys safely out of the browser.
 */

const form = document.getElementById("briefing-form");
const departureInput = document.getElementById("departure");
const arrivalInput = document.getElementById("arrival");
const generateBtn = document.getElementById("generate-btn");
const formError = document.getElementById("form-error");

const loadingState = document.getElementById("loading-state");
const loadingMessage = document.getElementById("loading-message");
const resultsSection = document.getElementById("results");

const routeSummaryContent = document.querySelector("#route-summary-content");
const departureWeatherPanel = document.querySelector("#departure-weather .weather-panel__content");
const arrivalWeatherPanel = document.querySelector("#arrival-weather .weather-panel__content");
const notamPanel = document.getElementById("notam-panel");
const notamContent = notamPanel.querySelector(".notam-panel__content");
const transmissionBody = document.getElementById("transmission-body");
const transmissionTimestamp = document.getElementById("transmission-timestamp");

// A short rotation of messages so the loading state feels alive during
// the few seconds it takes to hit multiple APIs + the LLM.
const LOADING_MESSAGES = [
  "Requesting live data\u2026",
  "Pulling weather observations\u2026",
  "Checking for active NOTAMs\u2026",
  "Synthesizing your briefing\u2026",
];

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formError.hidden = true;

  const departure = departureInput.value.trim().toUpperCase();
  const arrival = arrivalInput.value.trim().toUpperCase();

  if (!isValidIcao(departure) || !isValidIcao(arrival)) {
    showError("Enter valid 4-letter ICAO airport codes for both fields (e.g. KJFK, EGLL).");
    return;
  }

  if (departure === arrival) {
    showError("Departure and arrival airports must be different.");
    return;
  }

  await requestBriefing(departure, arrival);
});

function isValidIcao(code) {
  return /^[A-Z0-9]{4}$/.test(code);
}

function showError(message) {
  formError.textContent = message;
  formError.hidden = false;
}

async function requestBriefing(departure, arrival) {
  setLoading(true);
  resultsSection.hidden = true;

  try {
    const response = await fetch("/api/briefing", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ departure, arrival }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Something went wrong generating the briefing.");
    }

    renderResults(data);
  } catch (err) {
    showError(err.message || "Couldn't reach the briefing service. Please try again.");
  } finally {
    setLoading(false);
  }
}

function setLoading(isLoading) {
  generateBtn.disabled = isLoading;
  loadingState.hidden = !isLoading;

  if (isLoading) {
    let i = 0;
    loadingMessage.textContent = LOADING_MESSAGES[0];
    // Cycle through the loading messages every 1.4s while the request is in flight.
    window._loadingInterval = setInterval(() => {
      i = (i + 1) % LOADING_MESSAGES.length;
      loadingMessage.textContent = LOADING_MESSAGES[i];
    }, 1400);
  } else {
    clearInterval(window._loadingInterval);
  }
}

function renderResults(data) {
  renderRouteSummary(data.route);
  renderWeatherPanel(departureWeatherPanel, data.departure);
  renderWeatherPanel(arrivalWeatherPanel, data.arrival);
  renderNotams(data.departure, data.arrival);
  renderTransmission(data.briefing_text);

  resultsSection.hidden = false;
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderRouteSummary(route) {
  routeSummaryContent.innerHTML = "";

  const rows = [
    ["Route", `${route.departure_icao} \u2192 ${route.arrival_icao}`],
    ["Great-circle distance", `${route.distance_nm} nm`],
    ["Estimated flight time", route.estimated_flight_time],
    ["Initial heading", `${route.initial_bearing_deg}\u00b0`],
  ];

  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "route-summary__row";
    row.innerHTML = `<span>${label}</span><span>${value}</span>`;
    routeSummaryContent.appendChild(row);
  });
}

function renderWeatherPanel(panelEl, airportData) {
  panelEl.innerHTML = "";

  const nameEl = document.createElement("p");
  nameEl.className = "weather-panel__airport-name";
  nameEl.textContent = `${airportData.airport.icao} \u2013 ${airportData.airport.name}, ${airportData.airport.city}`;
  panelEl.appendChild(nameEl);

  panelEl.appendChild(buildWeatherBlock("METAR (current)", airportData.weather.metar));
  panelEl.appendChild(buildWeatherBlock("TAF (forecast)", airportData.weather.taf));
}

function buildWeatherBlock(label, rawText) {
  const wrapper = document.createElement("div");

  if (!rawText) {
    wrapper.className = "weather-panel__unavailable";
    wrapper.textContent = `${label}: not available for this station.`;
    return wrapper;
  }

  wrapper.className = "weather-panel__code-block";
  const labelSpan = document.createElement("span");
  labelSpan.className = "weather-panel__code-label";
  labelSpan.textContent = label;

  const textNode = document.createElement("span");
  textNode.textContent = rawText;

  wrapper.appendChild(labelSpan);
  wrapper.appendChild(textNode);
  return wrapper;
}

function renderNotams(departure, arrival) {
  const allNotams = [
    ...departure.notams.map((n) => ({ icao: departure.airport.icao, text: n })),
    ...arrival.notams.map((n) => ({ icao: arrival.airport.icao, text: n })),
  ];

  // Design decision: if there are no NOTAMs available for either airport
  // (common for international stations, or if no NOTAM provider is
  // configured), hide this whole section rather than showing an empty
  // or apologetic panel. The AI briefing below picks up the slack.
  if (allNotams.length === 0) {
    notamPanel.hidden = true;
    return;
  }

  notamPanel.hidden = false;
  notamContent.innerHTML = "";

  allNotams.forEach(({ icao, text }) => {
    const item = document.createElement("div");
    item.className = "notam-panel__item";
    item.textContent = `[${icao}] ${text}`;
    notamContent.appendChild(item);
  });
}

function renderTransmission(briefingText) {
  transmissionBody.textContent = briefingText;

  const now = new Date();
  const stamp = now.toISOString().slice(0, 16).replace("T", " ") + "Z";
  transmissionTimestamp.textContent = `RECEIVED ${stamp}`;
}
