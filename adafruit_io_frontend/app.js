const API_ROOT = "https://io.adafruit.com/api/v2";
const STORAGE_KEY = "db4_adafruit_io_dashboard_settings";

let refreshTimer = null;
let latestSettings = null;

const elements = {
  form: document.getElementById("settings-form"),
  username: document.getElementById("username"),
  feedKey: document.getElementById("feed-key"),
  aioKey: document.getElementById("aio-key"),
  limit: document.getElementById("limit"),
  refreshSeconds: document.getElementById("refresh-seconds"),
  saveSettings: document.getElementById("save-settings"),
  clearSettings: document.getElementById("clear-settings"),
  refreshNow: document.getElementById("refresh-now"),
  status: document.getElementById("connection-status"),
  dot: document.getElementById("connection-dot"),
  currentValue: document.getElementById("current-value"),
  currentTime: document.getElementById("current-time"),
  minValue: document.getElementById("min-value"),
  maxValue: document.getElementById("max-value"),
  avgValue: document.getElementById("avg-value"),
  chart: document.getElementById("temperature-chart"),
  tableBody: document.getElementById("data-table-body"),
  chartDescription: document.getElementById("chart-description"),
};

function setStatus(type, message) {
  elements.status.textContent = message;
  elements.dot.className = "dot";
  if (type === "ok") elements.dot.classList.add("dot-ok");
  else if (type === "error") elements.dot.classList.add("dot-error");
  else elements.dot.classList.add("dot-idle");
}

function getSettingsFromForm() {
  return {
    username: elements.username.value.trim(),
    feedKey: elements.feedKey.value.trim(),
    aioKey: elements.aioKey.value.trim(),
    limit: clampNumber(Number(elements.limit.value), 1, 1000, 100),
    refreshSeconds: clampNumber(Number(elements.refreshSeconds.value), 5, 600, 15),
  };
}

function setFormFromSettings(settings) {
  if (!settings) return;
  elements.username.value = settings.username || "";
  elements.feedKey.value = settings.feedKey || "temperature";
  elements.aioKey.value = settings.aioKey || "";
  elements.limit.value = settings.limit || 100;
  elements.refreshSeconds.value = settings.refreshSeconds || 15;
}

function clampNumber(value, min, max, fallback) {
  if (!Number.isFinite(value)) return fallback;
  return Math.min(max, Math.max(min, value));
}

function saveSettings() {
  const settings = getSettingsFromForm();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  setStatus("ok", "Settings saved locally");
}

function loadSettings() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    setFormFromSettings({ feedKey: "temperature", limit: 100, refreshSeconds: 15 });
    return;
  }

  try {
    setFormFromSettings(JSON.parse(raw));
  } catch {
    localStorage.removeItem(STORAGE_KEY);
  }
}

function clearSettings() {
  localStorage.removeItem(STORAGE_KEY);
  elements.form.reset();
  setFormFromSettings({ feedKey: "temperature", limit: 100, refreshSeconds: 15 });
  setStatus("idle", "Settings cleared");
}

async function fetchFeedData(settings) {
  const url = new URL(`${API_ROOT}/${encodeURIComponent(settings.username)}/feeds/${encodeURIComponent(settings.feedKey)}/data`);
  url.searchParams.set("limit", String(settings.limit));
  url.searchParams.set("include", "value,created_at");

  const headers = {};
  if (settings.aioKey) {
    headers["X-AIO-Key"] = settings.aioKey;
  }

  const response = await fetch(url, { headers });

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Adafruit IO request failed: ${response.status} ${response.statusText} ${text}`);
  }

  const data = await response.json();

  return data
    .map((point) => ({
      value: Number(point.value),
      createdAt: point.created_at,
      date: new Date(point.created_at),
    }))
    .filter((point) => Number.isFinite(point.value) && !Number.isNaN(point.date.getTime()))
    .sort((a, b) => a.date - b.date);
}

function formatTemp(value) {
  return `${value.toFixed(2)} °C`;
}

function formatDate(date) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(date);
}

function updateMetrics(points) {
  if (points.length === 0) {
    elements.currentValue.textContent = "--";
    elements.currentTime.textContent = "No numeric data found";
    elements.minValue.textContent = "--";
    elements.maxValue.textContent = "--";
    elements.avgValue.textContent = "--";
    return;
  }

  const values = points.map((point) => point.value);
  const latest = points[points.length - 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const avg = values.reduce((sum, value) => sum + value, 0) / values.length;

  elements.currentValue.textContent = formatTemp(latest.value);
  elements.currentTime.textContent = `Last update: ${formatDate(latest.date)}`;
  elements.minValue.textContent = formatTemp(min);
  elements.maxValue.textContent = formatTemp(max);
  elements.avgValue.textContent = formatTemp(avg);
  elements.chartDescription.textContent = `${points.length} values loaded, oldest to newest.`;
}

function updateTable(points) {
  const recent = [...points].reverse().slice(0, 12);

  if (recent.length === 0) {
    elements.tableBody.innerHTML = `<tr><td colspan="2">No data available.</td></tr>`;
    return;
  }

  elements.tableBody.innerHTML = recent
    .map((point) => `
      <tr>
        <td>${formatDate(point.date)}</td>
        <td>${formatTemp(point.value)}</td>
      </tr>
    `)
    .join("");
}

function drawChart(points) {
  const canvas = elements.chart;
  const ctx = canvas.getContext("2d");

  const width = canvas.width;
  const height = canvas.height;
  const padding = { top: 28, right: 32, bottom: 54, left: 64 };

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

  function xAt(index) {
    return padding.left + (index / (points.length - 1)) * plotWidth;
  }

  function yAt(value) {
    return padding.top + (1 - ((value - minValue) / range)) * plotHeight;
  }

  ctx.strokeStyle = "rgba(185, 194, 208, 0.20)";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#B9C2D0";
  ctx.font = "16px system-ui";

  const gridLines = 5;
  for (let i = 0; i <= gridLines; i++) {
    const y = padding.top + (i / gridLines) * plotHeight;
    const value = maxValue - (i / gridLines) * range;

    ctx.beginPath();
    ctx.moveTo(padding.left, y);
    ctx.lineTo(width - padding.right, y);
    ctx.stroke();

    ctx.fillText(`${value.toFixed(1)} °C`, 12, y + 5);
  }

  const firstDate = points[0].date;
  const lastDate = points[points.length - 1].date;
  ctx.fillText(formatShortDate(firstDate), padding.left, height - 18);
  ctx.fillText(formatShortDate(lastDate), width - padding.right - 150, height - 18);

  const gradient = ctx.createLinearGradient(padding.left, 0, width - padding.right, 0);
  gradient.addColorStop(0, "#C48C61");
  gradient.addColorStop(0.5, "#38BDF8");
  gradient.addColorStop(1, "#6F7D95");

  ctx.strokeStyle = gradient;
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
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  });
}

function formatShortDate(date) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "short",
  }).format(date);
}

async function refreshData() {
  if (!latestSettings) return;

  try {
    setStatus("idle", "Loading feed data...");
    const points = await fetchFeedData(latestSettings);

    updateMetrics(points);
    updateTable(points);
    drawChart(points);

    setStatus("ok", `Connected to ${latestSettings.feedKey}`);
  } catch (error) {
    console.error(error);
    setStatus("error", error.message);
  }
}

function startAutoRefresh(settings) {
  latestSettings = settings;

  if (refreshTimer) {
    clearInterval(refreshTimer);
  }

  refreshData();
  refreshTimer = setInterval(refreshData, settings.refreshSeconds * 1000);
}

elements.form.addEventListener("submit", (event) => {
  event.preventDefault();
  const settings = getSettingsFromForm();

  if (!settings.username || !settings.feedKey) {
    setStatus("error", "Username and feed key are required");
    return;
  }

  startAutoRefresh(settings);
});

elements.saveSettings.addEventListener("click", saveSettings);
elements.clearSettings.addEventListener("click", clearSettings);
elements.refreshNow.addEventListener("click", refreshData);

loadSettings();
setStatus("idle", "Enter feed settings and connect");
drawChart([]);
