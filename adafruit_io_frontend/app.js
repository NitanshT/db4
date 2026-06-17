const API_ROOT = "https://io.adafruit.com/api/v2";
const STORAGE_KEY = "mussels_to_muscles_sensor_dashboard_settings";

const SENSOR_DEFINITIONS = [
  {
    id: "temperature1",
    label: "Temp 1 Mussels",
    unit: "°C",
    inputId: "temperature1-feed",
    settingsKey: "temperature1Feed",
    defaultFeed: "temperature1",
    cssClass: "temperature",
    decimals: 2,
    color: "#C48C61",
  },
  {
    id: "temperature2",
    label: "Temp 2 Algae",
    unit: "°C",
    inputId: "temperature2-feed",
    settingsKey: "temperature2Feed",
    defaultFeed: "temperature2",
    cssClass: "temperature",
    decimals: 2,
    color: "#8B5D42",
  },
  {
    id: "light",
    label: "Light",
    unit: "lux",
    inputId: "light-feed",
    settingsKey: "lightFeed",
    defaultFeed: "light",
    cssClass: "light",
    decimals: 1,
    color: "#FBBF24",
  },
  {
    id: "od-water",
    label: "OD Water",
    unit: "OD",
    inputId: "od-water-feed",
    settingsKey: "odWaterFeed",
    defaultFeed: "od-water",
    cssClass: "light",
    decimals: 3,
    color: "#38BDF8",
  },
  {
    id: "setpoint-active",
    label: "Setpoint",
    unit: "°C",
    inputId: "setpoint-active-feed",
    settingsKey: "setpointActiveFeed",
    defaultFeed: "setpoint-active",
    cssClass: "control",
    decimals: 1,
    color: "#34D399",
  },
  {
    id: "relay-state",
    label: "Relay State",
    unit: "",
    inputId: "relay-state-feed",
    settingsKey: "relayStateFeed",
    defaultFeed: "relay-state",
    cssClass: "control",
    decimals: 0,
    color: "#FB7185",
  },
  {
    id: "test-number-active",
    label: "Test Number",
    unit: "",
    inputId: "test-number-active-feed",
    settingsKey: "testNumberActiveFeed",
    defaultFeed: "test-number-active",
    cssClass: "control",
    decimals: 0,
    color: "#B9C2D0",
  },
  {
    id: "elapsed-test-s",
    label: "Elapsed Test Time",
    unit: "s",
    inputId: "elapsed-test-s-feed",
    settingsKey: "elapsedTestSFeed",
    defaultFeed: "elapsed-test-s",
    cssClass: "control",
    decimals: 0,
    color: "#6F7D95",
  },
];

const CONTROL_FEEDS = {
  setpointTemp: "setpoint-temp",
  peltierEnable: "peltier-enable",
  autoControl: "auto-control",
  manualPeltier: "manual-peltier",
  testNumber: "test-number",
  testDurationS: "test-duration-s",
};

let refreshTimer = null;
let latestSettings = null;

const elements = {
  form: document.getElementById("settings-form"),
  username: document.getElementById("username"),
  aioKey: document.getElementById("aio-key"),
  limit: document.getElementById("limit"),
  refreshSeconds: document.getElementById("refresh-seconds"),
  saveSettings: document.getElementById("save-settings"),
  clearSettings: document.getElementById("clear-settings"),
  refreshNow: document.getElementById("refresh-now"),
  status: document.getElementById("connection-status"),
  dot: document.getElementById("connection-dot"),
  activeFeedCount: document.getElementById("active-feed-count"),
  latestUpdate: document.getElementById("latest-update"),
  totalPoints: document.getElementById("total-points"),
  sensorCards: document.getElementById("sensor-cards"),
  sensorCharts: document.getElementById("sensor-charts"),
  tableBody: document.getElementById("data-table-body"),
  setpointTempValue: document.getElementById("setpoint-temp-value"),
  peltierEnableToggle: document.getElementById("peltier-enable-toggle"),
  autoControlToggle: document.getElementById("auto-control-toggle"),
  manualPeltierToggle: document.getElementById("manual-peltier-toggle"),
  testNumberValue: document.getElementById("test-number-value"),
  testDurationValue: document.getElementById("test-duration-value"),
  sendSetpoint: document.getElementById("send-setpoint"),
  sendToggleControls: document.getElementById("send-toggle-controls"),
  sendTestSettings: document.getElementById("send-test-settings"),
  sendAllControls: document.getElementById("send-all-controls"),
};

function setStatus(type, message) {
  elements.status.textContent = message;
  elements.dot.className = "dot";
  if (type === "ok") elements.dot.classList.add("dot-ok");
  else if (type === "error") elements.dot.classList.add("dot-error");
  else elements.dot.classList.add("dot-idle");
}

function clampNumber(value, min, max, fallback) {
  if (!Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, value));
}

function getSettingsFromForm() {
  const settings = {
    username: elements.username.value.trim(),
    aioKey: elements.aioKey.value.trim(),
    limit: clampNumber(Number(elements.limit.value), 1, 1000, 120),
    refreshSeconds: clampNumber(Number(elements.refreshSeconds.value), 1, 600, 15),
  };

  for (const sensor of SENSOR_DEFINITIONS) {
    settings[sensor.settingsKey] = document.getElementById(sensor.inputId).value.trim();
  }

  return settings;
}

function setFormFromSettings(settings = {}) {
  elements.username.value = settings.username || "";
  elements.aioKey.value = settings.aioKey || "";
  elements.limit.value = settings.limit || 120;
  elements.refreshSeconds.value = settings.refreshSeconds || 15;

  for (const sensor of SENSOR_DEFINITIONS) {
    document.getElementById(sensor.inputId).value = settings[sensor.settingsKey] ?? sensor.defaultFeed;
  }
}

function getActiveSensors(settings) {
  return SENSOR_DEFINITIONS
    .map((sensor) => ({ ...sensor, feedKey: settings[sensor.settingsKey] }))
    .filter((sensor) => sensor.feedKey && sensor.feedKey.length > 0);
}

function saveSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(getSettingsFromForm()));
  setStatus("ok", "Settings saved locally");
}

function loadSettings() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    setFormFromSettings();
    return;
  }

  try {
    setFormFromSettings(JSON.parse(raw));
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    setFormFromSettings();
  }
}

function clearSettings() {
  localStorage.removeItem(STORAGE_KEY);
  elements.form.reset();
  setFormFromSettings();
  setStatus("idle", "Settings cleared");
}

async function fetchFeedData(settings, sensor) {
  const url = new URL(`${API_ROOT}/${encodeURIComponent(settings.username)}/feeds/${encodeURIComponent(sensor.feedKey)}/data`);
  url.searchParams.set("limit", String(settings.limit));
  url.searchParams.set("include", "value,created_at");

  const headers = {};
  if (settings.aioKey) headers["X-AIO-Key"] = settings.aioKey;

  const response = await fetch(url, { headers });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`${sensor.label}: ${response.status} ${response.statusText} ${text}`);
  }

  const data = await response.json();
  const points = data
    .map((point) => ({
      value: Number(point.value),
      createdAt: point.created_at,
      date: new Date(point.created_at),
    }))
    .filter((point) => Number.isFinite(point.value) && !Number.isNaN(point.date.getTime()))
    .sort((a, b) => a.date - b.date);

  return { sensor, points, error: null };
}

function formatValue(value, sensor) {
  const formatted = value.toFixed(sensor.decimals);
  return sensor.unit ? `${formatted} ${sensor.unit}` : formatted;
}

function formatDate(date) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

function formatShortDate(date) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
  }).format(date);
}

function calculateStats(points) {
  if (!points.length) return null;

  const values = points.map((point) => point.value);
  const latest = points[points.length - 1];

  return {
    latest,
    min: Math.min(...values),
    max: Math.max(...values),
    avg: values.reduce((sum, value) => sum + value, 0) / values.length,
  };
}

function renderSummary(results) {
  const successful = results.filter((result) => !result.error);
  const totalPoints = successful.reduce((sum, result) => sum + result.points.length, 0);
  const latestDates = successful
    .flatMap((result) => result.points.map((point) => point.date))
    .sort((a, b) => b - a);

  elements.activeFeedCount.textContent = String(results.length);
  elements.totalPoints.textContent = String(totalPoints);
  elements.latestUpdate.textContent = latestDates.length ? formatDate(latestDates[0]) : "--";
}

function renderSensorCards(results) {
  elements.sensorCards.innerHTML = results.map((result) => {
    const { sensor, points, error } = result;

    if (error) {
      return `
        <article class="sensor-card ${sensor.cssClass}">
          <p class="metric-label">${escapeHtml(sensor.label)}</p>
          <p class="sensor-value error-text">Error</p>
          <p class="metric-detail">${escapeHtml(error.message || String(error))}</p>
          <p class="metric-detail"><span class="feed-pill">${escapeHtml(sensor.feedKey)}</span></p>
        </article>
      `;
    }

    const stats = calculateStats(points);
    if (!stats) {
      return `
        <article class="sensor-card ${sensor.cssClass}">
          <p class="metric-label">${escapeHtml(sensor.label)}</p>
          <p class="sensor-value">--</p>
          <p class="metric-detail">No numeric data in feed.</p>
          <p class="metric-detail"><span class="feed-pill">${escapeHtml(sensor.feedKey)}</span></p>
        </article>
      `;
    }

    return `
      <article class="sensor-card ${sensor.cssClass}">
        <p class="metric-label">${escapeHtml(sensor.label)}</p>
        <p class="sensor-value">${formatValue(stats.latest.value, sensor)}</p>
        <p class="metric-detail">Last update: ${formatDate(stats.latest.date)}</p>
        <p class="metric-detail"><span class="feed-pill">${escapeHtml(sensor.feedKey)}</span></p>

        <div class="sensor-stats">
          <div class="sensor-stat">
            <span>Min</span>
            <strong>${formatValue(stats.min, sensor)}</strong>
          </div>
          <div class="sensor-stat">
            <span>Max</span>
            <strong>${formatValue(stats.max, sensor)}</strong>
          </div>
          <div class="sensor-stat">
            <span>Avg</span>
            <strong>${formatValue(stats.avg, sensor)}</strong>
          </div>
        </div>
      </article>
    `;
  }).join("");
}

function renderCharts(results) {
  elements.sensorCharts.innerHTML = results
    .filter((result) => !result.error)
    .map((result) => `
      <article class="chart-card">
        <div class="section-title">
          <div>
            <h2>${escapeHtml(result.sensor.label)} trend</h2>
            <p>${result.points.length} values loaded from <span class="feed-pill">${escapeHtml(result.sensor.feedKey)}</span></p>
          </div>
        </div>
        <div class="chart-wrap">
          <canvas id="chart-${escapeHtml(result.sensor.id)}" width="1200" height="420"></canvas>
        </div>
      </article>
    `).join("");

  for (const result of results) {
    if (result.error) continue;
    const canvas = document.getElementById(`chart-${result.sensor.id}`);
    drawChart(canvas, result.points, result.sensor);
  }
}

function drawChart(canvas, points, sensor) {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 28, right: 32, bottom: 54, left: 74 };

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "rgba(5, 14, 29, 0.50)";
  ctx.fillRect(0, 0, width, height);

  if (points.length < 2) {
    ctx.fillStyle = "#B9C2D0";
    ctx.font = "22px system-ui";
    ctx.fillText("Not enough data to draw chart.", 64, 80);
    return;
  }

  const values = points.map((point) => point.value);
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);
  const range = maxValue - minValue || 1;
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const xAt = (index) => padding.left + (index / (points.length - 1)) * plotWidth;
  const yAt = (value) => padding.top + (1 - ((value - minValue) / range)) * plotHeight;

  ctx.strokeStyle = "rgba(185, 194, 208, 0.20)";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#B9C2D0";
  ctx.font = "16px system-ui";

  for (let i = 0; i <= 5; i++) {
    const y = padding.top + (i / 5) * plotHeight;
    const value = maxValue - (i / 5) * range;

    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();

    ctx.fillText(`${value.toFixed(sensor.decimals)} ${sensor.unit}`, 12, y + 5);
  }

  ctx.fillText(formatShortDate(points[0].date), padding.left, height - 18);
  ctx.fillText(formatShortDate(points[points.length - 1].date), width - padding.right - 150, height - 18);

  ctx.strokeStyle = sensor.color;
  ctx.lineWidth = 4;
  ctx.beginPath();

  points.forEach((point, index) => {
    const x = xAt(index);
    const y = yAt(point.value);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.stroke();

  ctx.fillStyle = "#F4F0EA";
  points.forEach((point, index) => {
    const x = xAt(index);
    const y = yAt(point.value);
    ctx.beginPath();
    ctx.arc(x, y, 3.2, 0, Math.PI * 2);
    ctx.fill();
  });
}

function renderTable(results) {
  const rows = results
    .filter((result) => !result.error && result.points.length > 0)
    .flatMap((result) => {
      const sensor = result.sensor;
      return [...result.points].reverse().slice(0, 6).map((point) => ({ sensor, point }));
    })
    .sort((a, b) => b.point.date - a.point.date)
    .slice(0, 18);

  if (!rows.length) {
    elements.tableBody.innerHTML = `<tr><td colspan="4">No data available.</td></tr>`;
    return;
  }

  elements.tableBody.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.sensor.label)}</td>
      <td>${formatDate(row.point.date)}</td>
      <td>${formatValue(row.point.value, row.sensor)}</td>
      <td><span class="feed-pill">${escapeHtml(row.sensor.feedKey)}</span></td>
    </tr>
  `).join("");
}


async function postFeedValue(settings, feedKey, value) {
  const url = new URL(`${API_ROOT}/${encodeURIComponent(settings.username)}/feeds/${encodeURIComponent(feedKey)}/data`);

  const headers = { "Content-Type": "application/json" };
  if (settings.aioKey) headers["X-AIO-Key"] = settings.aioKey;

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({ value: String(value) }),
  });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`${feedKey}: ${response.status} ${response.statusText} ${text}`);
  }

  return response.json().catch(() => null);
}

function getControlSettings() {
  const settings = getSettingsFromForm();

  if (!settings.username) {
    throw new Error("Adafruit IO username is required");
  }

  if (!settings.aioKey) {
    throw new Error("AIO key is required to write remote-control feeds");
  }

  latestSettings = settings;
  return settings;
}

async function sendSetpoint() {
  try {
    const settings = getControlSettings();
    const value = Number(elements.setpointTempValue.value);

    if (!Number.isFinite(value)) {
      throw new Error("Setpoint must be a number");
    }

    await postFeedValue(settings, CONTROL_FEEDS.setpointTemp, value.toFixed(1));
    setStatus("ok", `Setpoint sent: ${value.toFixed(1)} °C`);
  } catch (error) {
    setStatus("error", error.message || String(error));
  }
}

async function sendToggleControls() {
  try {
    const settings = getControlSettings();

    await postFeedValue(settings, CONTROL_FEEDS.peltierEnable, elements.peltierEnableToggle.checked ? 1 : 0);
    await postFeedValue(settings, CONTROL_FEEDS.autoControl, elements.autoControlToggle.checked ? 1 : 0);
    await postFeedValue(settings, CONTROL_FEEDS.manualPeltier, elements.manualPeltierToggle.checked ? 1 : 0);

    setStatus("ok", "Toggle controls sent");
  } catch (error) {
    setStatus("error", error.message || String(error));
  }
}

async function sendTestSettings() {
  try {
    const settings = getControlSettings();
    const testNumber = Number(elements.testNumberValue.value);
    const testDuration = Number(elements.testDurationValue.value);

    if (!Number.isFinite(testNumber) || testNumber < 1) {
      throw new Error("Test number must be >= 1");
    }

    if (!Number.isFinite(testDuration) || testDuration < 10) {
      throw new Error("Test duration must be at least 10 seconds");
    }

    await postFeedValue(settings, CONTROL_FEEDS.testNumber, Math.round(testNumber));
    await postFeedValue(settings, CONTROL_FEEDS.testDurationS, Math.round(testDuration));

    setStatus("ok", `Test settings sent: test ${Math.round(testNumber)}, ${Math.round(testDuration)} s`);
  } catch (error) {
    setStatus("error", error.message || String(error));
  }
}

async function sendAllControls() {
  await sendSetpoint();
  await sendToggleControls();
  await sendTestSettings();
}

async function refreshData() {
  if (!latestSettings) return;

  const activeSensors = getActiveSensors(latestSettings);
  if (!activeSensors.length) {
    setStatus("error", "No feed keys configured");
    return;
  }

  setStatus("idle", "Loading feed data...");

  const results = [];
  for (const sensor of activeSensors) {
    try {
      results.push(await fetchFeedData(latestSettings, sensor));
    } catch (error) {
      results.push({ sensor, points: [], error });
    }
  }

  renderSummary(results);
  renderSensorCards(results);
  renderCharts(results);
  renderTable(results);

  const errors = results.filter((result) => result.error).length;
  if (errors > 0) {
    setStatus("error", `${errors} feed(s) failed. Check feed keys or AIO key.`);
  } else {
    setStatus("ok", `Connected to ${results.length} feed(s)`);
  }
}

function startAutoRefresh(settings) {
  latestSettings = settings;

  if (refreshTimer) clearInterval(refreshTimer);

  refreshData();
  refreshTimer = setInterval(refreshData, settings.refreshSeconds * 1000);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[char]);
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  const settings = getSettingsFromForm();

  if (!settings.username) {
    setStatus("error", "Adafruit IO username is required");
    return;
  }

  startAutoRefresh(settings);
});

elements.saveSettings.addEventListener("click", saveSettings);
elements.clearSettings.addEventListener("click", clearSettings);
elements.refreshNow.addEventListener("click", refreshData);
elements.sendSetpoint.addEventListener("click", sendSetpoint);
elements.sendToggleControls.addEventListener("click", sendToggleControls);
elements.sendTestSettings.addEventListener("click", sendTestSettings);
elements.sendAllControls.addEventListener("click", sendAllControls);

loadSettings();
setStatus("idle", "Enter feed settings and connect");
renderSummary([]);
renderSensorCards([]);
renderCharts([]);
renderTable([]);
