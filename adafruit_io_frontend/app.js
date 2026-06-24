const API_ROOT = "https://io.adafruit.com/api/v2";
const STORAGE_KEY = "mussels_to_muscles_sensor_dashboard_settings";
const SNAPSHOT_STORAGE_KEY = "mussels_to_muscles_sensor_dashboard_snapshots";
const SETTINGS_PANEL_STATE_KEY = "mussels_to_muscles_sensor_dashboard_settings_panel_open";

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
    decimals: 2,
    color: "#38BDF8",
  },
  {
    id: "pwm-duty",
    label: "PWM Duty Cycle",
    unit: "%",
    inputId: "pwm-duty-feed",
    settingsKey: "pwmDutyFeed",
    defaultFeed: "pwm-duty",
    cssClass: "control",
    decimals: 1,
    color: "#38BDF8",
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
  {
    id: "setpoint-temp",
    label: "Setpoint",
    unit: "°C",
    inputId: "setpoint-temp-feed",
    settingsKey: "setpointTempFeed",
    defaultFeed: "setpoint-temp",
    cssClass: "control",
    decimals: 1,
    color: "#34D399",
  },
  {
    id: "system-enable",
    label: "System Enable",
    unit: "",
    inputId: "system-enable-feed",
    settingsKey: "systemEnableFeed",
    defaultFeed: "system-enable",
    cssClass: "control",
    decimals: 0,
    color: "#FB7185",
  },
  {
    id: "test-number",
    label: "Test Number",
    unit: "",
    inputId: "test-number-feed",
    settingsKey: "testNumberFeed",
    defaultFeed: "test-number",
    cssClass: "control",
    decimals: 0,
    color: "#B9C2D0",
  },
  {
    id: "test-duration-s",
    label: "Test Duration",
    unit: "s",
    inputId: "test-duration-s-feed",
    settingsKey: "testDurationSFeed",
    defaultFeed: "test-duration-s",
    cssClass: "control",
    decimals: 0,
    color: "#9CA3AF",
  },
];

const CONTROL_FEEDS = {
  setpointTemp: "setpoint-temp",
  systemEnable: "system-enable",
  testNumber: "test-number",
  testDurationS: "test-duration-s",
  systemReset: "system-reset",
};

const HIDDEN_TREND_SENSOR_IDS = new Set([
  "setpoint-temp",
  "system-enable",
  "test-number",
  "elapsed-test-s",
  "test-duration-s",
]);

let refreshTimer = null;
let latestSettings = null;
let experimentTimer = null;
let experimentStartTime = null;
let experimentElapsedSeconds = 0;
let experimentDurationSeconds = 0;
let latestResults = [];
let activeExperimentSession = null;
let activeExperimentSampleKeys = new Set();

const elements = {
  form: document.getElementById("settings-form"),
  username: document.getElementById("username"),
  aioKey: document.getElementById("aio-key"),
  settingsToggle: document.getElementById("settings-toggle"),
  advancedSettings: document.getElementById("advanced-settings-fields"),
  limit: document.getElementById("limit"),
  refreshSeconds: document.getElementById("refresh-seconds"),
  saveSettings: document.getElementById("save-settings"),
  clearSettings: document.getElementById("clear-settings"),
  refreshNow: document.getElementById("refresh-now"),
  status: document.getElementById("connection-status"),
  dot: document.getElementById("connection-dot"),
  storedExperimentsList: document.getElementById("stored-experiments-list"),
  storageStatus: document.getElementById("storage-status"),
  experimentName: document.getElementById("experiment-name"),
  experimentNotes: document.getElementById("experiment-notes"),
  activeFeedCount: document.getElementById("active-feed-count"),
  latestUpdate: document.getElementById("latest-update"),
  totalPoints: document.getElementById("total-points"),
  sensorCards: document.getElementById("sensor-cards"),
  sensorCharts: document.getElementById("sensor-charts"),
  tableBody: document.getElementById("data-table-body"),
  setpointTempSlider: document.getElementById("setpoint-temp-slider"),
  setpointTempValue: document.getElementById("setpoint-temp-value"),
  setpointDisplay: document.getElementById("setpoint-display"),
  systemEnableToggle: document.getElementById("system-enable-toggle"),
  systemEnableDisplay: document.getElementById("system-enable-display"),
  sendSystemEnable: document.getElementById("send-system-enable"),
  testNumberSlider: document.getElementById("test-number-slider"),
  testNumberValue: document.getElementById("test-number-value"),
  testNumberDisplay: document.getElementById("test-number-display"),
  testDurationSlider: document.getElementById("test-duration-slider"),
  testDurationValue: document.getElementById("test-duration-value"),
  testDurationDisplay: document.getElementById("test-duration-display"),
  elapsedTestDisplay: document.getElementById("elapsed-test-display"),
  sendSetpoint: document.getElementById("send-setpoint"),
  sendToggleControls: document.getElementById("send-toggle-controls"),
  sendTestSettings: document.getElementById("send-test-settings"),
  sendAllControls: document.getElementById("send-all-controls"),
  startExperiment: document.getElementById("start-experiment"),
  stopExperiment: document.getElementById("stop-experiment"),
  sendSystemReset: document.getElementById("send-system-reset"),
  saveDataSnapshot: document.getElementById("save-data-snapshot"),
  exportLatestCsv: document.getElementById("export-latest-csv"),
  exportLatestJson: document.getElementById("export-latest-json"),
  exportStoredJson: document.getElementById("export-stored-json"),
  clearStoredData: document.getElementById("clear-stored-data"),
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

function createId() {
  return (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function")
    ? globalThis.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

function formatElapsedTime(totalSeconds) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
  }

  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
}

function setControlPairValue(rangeElement, numberElement, displayElement, rawValue, formatDisplay = (value) => value) {
  const min = Number(rangeElement.min);
  const max = Number(rangeElement.max);
  const fallback = Number(rangeElement.value);
  const clamped = clampNumber(Number(rawValue), min, max, fallback);

  rangeElement.value = String(clamped);
  numberElement.value = String(clamped);
  if (displayElement) displayElement.textContent = formatDisplay(clamped);

  return clamped;
}

function syncControlPair(rangeElement, numberElement, displayElement, formatDisplay = (value) => value) {
  const applyValue = (rawValue) => setControlPairValue(rangeElement, numberElement, displayElement, rawValue, formatDisplay);
  const syncNumberInput = () => {
    const rawValue = numberElement.value.trim();
    if (!rawValue) return;

    const parsedValue = Number(rawValue);
    if (!Number.isFinite(parsedValue)) return;

    rangeElement.value = String(parsedValue);
    if (displayElement) displayElement.textContent = formatDisplay(parsedValue);
  };

  rangeElement.addEventListener("input", () => applyValue(rangeElement.value));
  numberElement.addEventListener("input", syncNumberInput);
  numberElement.addEventListener("change", () => applyValue(numberElement.value));
  numberElement.addEventListener("blur", () => applyValue(numberElement.value));
  applyValue(rangeElement.value);
}

function updateSystemEnableDisplay() {
  if (!elements.systemEnableToggle || !elements.systemEnableDisplay) return;
  elements.systemEnableDisplay.textContent = elements.systemEnableToggle.checked ? "ON" : "OFF";
}

function setSettingsPanelExpanded(isExpanded) {
  if (!elements.settingsToggle || !elements.advancedSettings) return;

  elements.settingsToggle.setAttribute("aria-expanded", String(isExpanded));
  elements.settingsToggle.querySelector("span")?.replaceChildren(isExpanded ? "Hide extra settings" : "More settings");
  elements.advancedSettings.hidden = !isExpanded;
  localStorage.setItem(SETTINGS_PANEL_STATE_KEY, JSON.stringify(isExpanded));
}

function loadSettingsPanelState() {
  const raw = localStorage.getItem(SETTINGS_PANEL_STATE_KEY);
  if (raw === null) {
    setSettingsPanelExpanded(false);
    return;
  }

  try {
    setSettingsPanelExpanded(Boolean(JSON.parse(raw)));
  } catch {
    localStorage.removeItem(SETTINGS_PANEL_STATE_KEY);
    setSettingsPanelExpanded(false);
  }
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

  if (elements.systemEnableToggle) {
    settings.systemEnable = elements.systemEnableToggle.checked;
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

  if (elements.systemEnableToggle) {
    elements.systemEnableToggle.checked = Boolean(settings.systemEnable ?? false);
    updateSystemEnableDisplay();
  }

  if (elements.setpointTempSlider && elements.setpointTempValue) {
    setControlPairValue(
      elements.setpointTempSlider,
      elements.setpointTempValue,
      elements.setpointDisplay,
      settings.setpointTemp ?? 18,
      (value) => Number(value).toFixed(1),
    );
  }

  if (elements.testNumberSlider && elements.testNumberValue) {
    setControlPairValue(
      elements.testNumberSlider,
      elements.testNumberValue,
      elements.testNumberDisplay,
      settings.testNumber ?? 1,
      (value) => String(Math.round(Number(value))),
    );
  }

  if (elements.testDurationSlider && elements.testDurationValue) {
    setControlPairValue(
      elements.testDurationSlider,
      elements.testDurationValue,
      elements.testDurationDisplay,
      settings.testDurationS ?? 600,
      (value) => String(Math.round(Number(value))),
    );
  }
}

function getActiveSensors(settings) {
  return SENSOR_DEFINITIONS
    .map((sensor) => ({ ...sensor, feedKey: settings[sensor.settingsKey] }))
    .filter((sensor) => sensor.feedKey && sensor.feedKey.length > 0);
}

function getExperimentName() {
  return elements.experimentName?.value.trim() || "Untitled experiment";
}

function getExperimentNotes() {
  return elements.experimentNotes?.value.trim() || "";
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

function transformSensorValue(sensor, rawValue) {
  if (!Number.isFinite(rawValue)) {
    return rawValue;
  }

  if (sensor.id === "pwm-duty") {
    const percentValue = rawValue <= 1 && rawValue >= 0
      ? rawValue * 100
      : rawValue;
    return clampNumber(percentValue, 0, 100, 0);
  }

  if (sensor.id === "od-water") {
    return (-0.000307 * rawValue) + 1545.2;
  }

  return rawValue;
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
    .map((point) => {
      const rawValue = Number(point.value);
      return {
        value: transformSensorValue(sensor, rawValue),
        rawValue,
        createdAt: point.created_at,
        date: new Date(point.created_at),
      };
    })
    .filter((point) => Number.isFinite(point.rawValue) && Number.isFinite(point.value) && !Number.isNaN(point.date.getTime()))
    .map(({ rawValue: _rawValue, ...point }) => point)
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

function formatSnapshotDate(date) {
  return new Intl.DateTimeFormat(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
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

function buildControlSnapshot() {
  return {
    setpointTemp: Number(elements.setpointTempValue?.value ?? 18),
    systemEnable: Boolean(elements.systemEnableToggle?.checked),
    testNumber: Math.round(Number(elements.testNumberValue?.value ?? 1)),
    testDurationS: Math.round(Number(elements.testDurationValue?.value ?? 600)),
    elapsedTestS: experimentElapsedSeconds,
    capturedAt: new Date().toISOString(),
  };
}

function buildSessionSettings() {
  const settings = getSettingsFromForm();
  const safeSettings = {
    username: settings.username,
    limit: settings.limit,
    refreshSeconds: settings.refreshSeconds,
    feeds: {},
  };

  for (const sensor of SENSOR_DEFINITIONS) {
    const configuredFeedKey = settings[sensor.settingsKey] || sensor.defaultFeed;
    safeSettings.feeds[configuredFeedKey] = {
      sensorId: sensor.id,
      label: sensor.label,
      unit: sensor.unit,
      feedKey: configuredFeedKey,
    };
  }

  return safeSettings;
}

function createActiveExperimentSession() {
  return {
    id: createId(),
    experimentName: getExperimentName(),
    notes: getExperimentNotes(),
    startedAt: new Date().toISOString(),
    stoppedAt: null,
    durationSeconds: 0,
    running: true,
    settings: buildSessionSettings(),
    controlValues: {
      started: buildControlSnapshot(),
      stopped: null,
    },
    samples: {},
  };
}

function getSessionDurationSeconds(session) {
  if (!session) return 0;
  if (session.stoppedAt) return clampNumber(Number(session.durationSeconds), 0, 86400 * 365, 0);

  const startedAtMs = Date.parse(session.startedAt);
  if (Number.isNaN(startedAtMs)) return clampNumber(Number(session.durationSeconds), 0, 86400 * 365, 0);

  return Math.max(clampNumber(Number(session.durationSeconds), 0, 86400 * 365, 0), Math.floor((Date.now() - startedAtMs) / 1000));
}

function getSessionSampleCount(session) {
  if (!session?.samples) return 0;
  return Object.values(session.samples).reduce((sum, sampleGroup) => sum + (Array.isArray(sampleGroup.points) ? sampleGroup.points.length : 0), 0);
}

function normalizeStoredSession(snapshot) {
  if (!snapshot || typeof snapshot !== "object") {
    return null;
  }

  if (snapshot.samples && typeof snapshot.samples === "object") {
    return {
      ...snapshot,
      experimentName: snapshot.experimentName || snapshot.name || "Untitled experiment",
      notes: snapshot.notes || "",
      running: Boolean(snapshot.running && !snapshot.stoppedAt),
      durationSeconds: getSessionDurationSeconds(snapshot),
    };
  }

  if (Array.isArray(snapshot.results)) {
    const samples = {};

    for (const result of snapshot.results) {
      if (!result?.feedKey) continue;
      samples[result.feedKey] = {
        feedKey: result.feedKey,
        label: result.label || result.feedKey,
        unit: result.unit || "",
        sensorId: result.sensorId || result.feedKey,
        points: Array.isArray(result.points)
          ? result.points.map((point) => ({
            timestamp: point.createdAt,
            value: point.value,
          }))
          : [],
      };
    }

    return {
      id: snapshot.id || createId(),
      experimentName: snapshot.name || snapshot.experimentName || "Untitled experiment",
      notes: snapshot.notes || "",
      startedAt: snapshot.startedAt || snapshot.savedAt || new Date().toISOString(),
      stoppedAt: snapshot.stoppedAt || snapshot.savedAt || null,
      durationSeconds: clampNumber(Number(snapshot.durationSeconds), 0, 86400 * 365, 0),
      running: false,
      settings: snapshot.settings || {},
      controlValues: snapshot.controlValues || {},
      samples,
      savedAt: snapshot.savedAt || null,
    };
  }

  return null;
}

function getStoredSnapshots() {
  const raw = localStorage.getItem(SNAPSHOT_STORAGE_KEY);

  if (!raw) {
    return [];
  }

  try {
    const snapshots = JSON.parse(raw);
    if (!Array.isArray(snapshots)) return [];
    return snapshots.map(normalizeStoredSession).filter(Boolean);
  } catch {
    localStorage.removeItem(SNAPSHOT_STORAGE_KEY);
    return [];
  }
}

function updateStorageStatus() {
  if (!elements.storageStatus) return;

  if (activeExperimentSession && !activeExperimentSession.stoppedAt) {
    const sampleCount = getSessionSampleCount(activeExperimentSession);
    elements.storageStatus.textContent = `Recording in progress · ${activeExperimentSession.experimentName} · ${sampleCount} sample${sampleCount === 1 ? "" : "s"} captured so far.`;
    return;
  }

  if (activeExperimentSession?.stoppedAt) {
    const sampleCount = getSessionSampleCount(activeExperimentSession);
    elements.storageStatus.textContent = `Stopped experiment ready to save/export · ${activeExperimentSession.experimentName} · ${sampleCount} sample${sampleCount === 1 ? "" : "s"} captured.`;
    return;
  }

  const snapshots = getStoredSnapshots();
  if (!snapshots.length) {
    elements.storageStatus.textContent = "No local experiment snapshots saved yet.";
    return;
  }

  const latestSnapshot = snapshots[0];
  const sampleCount = getSessionSampleCount(latestSnapshot);
  const dateLabel = latestSnapshot.savedAt || latestSnapshot.stoppedAt || latestSnapshot.startedAt;
  elements.storageStatus.textContent = `Stored experiments · ${latestSnapshot.experimentName} · ${formatSnapshotDate(new Date(dateLabel))} · ${sampleCount} sample${sampleCount === 1 ? "" : "s"}`;
}

function setStoredSnapshots(snapshots) {
  localStorage.setItem(SNAPSHOT_STORAGE_KEY, JSON.stringify(snapshots));
  renderStoredSnapshots();
}

function renderStoredSnapshots() {
  if (!elements.storedExperimentsList) {
    return;
  }

  const snapshots = getStoredSnapshots();

  if (!snapshots.length) {
    elements.storedExperimentsList.innerHTML = "";
    updateStorageStatus();
    return;
  }

  elements.storedExperimentsList.innerHTML = snapshots.slice(0, 3).map((snapshot) => {
    const sampleCount = getSessionSampleCount(snapshot);
    const dateLabel = snapshot.savedAt || snapshot.stoppedAt || snapshot.startedAt;
    return `
      <li class="stored-experiments-item">
        <span class="stored-experiments-name">${escapeHtml(snapshot.experimentName)}</span>
        <span class="stored-experiments-meta">${formatSnapshotDate(new Date(dateLabel))}</span>
        <span class="stored-experiments-meta">${sampleCount} sample${sampleCount === 1 ? "" : "s"}</span>
        ${snapshot.notes ? `<span class="stored-experiments-notes">${escapeHtml(snapshot.notes)}</span>` : ""}
      </li>
    `;
  }).join("");

  if (snapshots.length > 3) {
    const extraCount = snapshots.length - 3;
    elements.storedExperimentsList.insertAdjacentHTML("beforeend", `
      <li class="stored-experiments-item stored-experiments-more">+${extraCount} more saved snapshot${extraCount === 1 ? "" : "s"}</li>
    `);
  }

  updateStorageStatus();
}

function updateActiveExperimentMetadata() {
  if (!activeExperimentSession) return;
  activeExperimentSession.experimentName = getExperimentName();
  activeExperimentSession.notes = getExperimentNotes();
  activeExperimentSession.durationSeconds = getSessionDurationSeconds(activeExperimentSession);
}

function serializeSession(session, extra = {}) {
  return cloneJson({
    ...session,
    experimentName: session.experimentName || "Untitled experiment",
    notes: session.notes || "",
    running: Boolean(!session.stoppedAt),
    durationSeconds: getSessionDurationSeconds(session),
    settings: session.settings || {},
    controlValues: session.controlValues || {},
    samples: session.samples || {},
    ...extra,
  });
}

function getLatestSavedSession() {
  return getStoredSnapshots()[0] || null;
}

function getSessionForExport() {
  if (activeExperimentSession?.stoppedAt) {
    updateActiveExperimentMetadata();
    return serializeSession(activeExperimentSession);
  }

  const latestSaved = getLatestSavedSession();
  if (latestSaved) {
    return serializeSession(latestSaved);
  }

  return null;
}

function addResultsToActiveExperimentSession(results) {
  if (!activeExperimentSession || activeExperimentSession.stoppedAt) {
    return;
  }

  const startedAtMs = Date.parse(activeExperimentSession.startedAt);
  const stoppedAtMs = activeExperimentSession.stoppedAt ? Date.parse(activeExperimentSession.stoppedAt) : Number.POSITIVE_INFINITY;

  for (const result of results) {
    if (result.error || !result.points.length) continue;

    const feedKey = result.sensor.feedKey;
    if (!activeExperimentSession.samples[feedKey]) {
      activeExperimentSession.samples[feedKey] = {
        feedKey,
        label: result.sensor.label,
        unit: result.sensor.unit,
        sensorId: result.sensor.id,
        points: [],
      };
    }

    for (const point of result.points) {
      const pointMs = point.date.getTime();
      if (pointMs < startedAtMs) continue;
      if (pointMs > stoppedAtMs) continue;

      const sampleKey = `${feedKey}|${point.createdAt}|${point.value}`;
      if (activeExperimentSampleKeys.has(sampleKey)) continue;

      activeExperimentSession.samples[feedKey].points.push({
        timestamp: point.createdAt,
        value: point.value,
      });
      activeExperimentSampleKeys.add(sampleKey);
    }
  }

  activeExperimentSession.durationSeconds = getSessionDurationSeconds(activeExperimentSession);
  updateStorageStatus();
}

function finalizeActiveExperimentSession() {
  if (!activeExperimentSession || activeExperimentSession.stoppedAt) {
    return activeExperimentSession;
  }

  updateActiveExperimentMetadata();
  activeExperimentSession.stoppedAt = new Date().toISOString();
  activeExperimentSession.durationSeconds = experimentElapsedSeconds;
  activeExperimentSession.running = false;
  activeExperimentSession.controlValues.stopped = buildControlSnapshot();
  updateStorageStatus();

  return activeExperimentSession;
}

function downloadTextFile(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");

  link.href = url;
  link.download = filename;
  link.click();

  URL.revokeObjectURL(url);
}

function getExportFileStem(session = null) {
  const sourceValue = session?.experimentName || getExperimentName();
  return sourceValue ? sourceValue.replace(/[^a-z0-9-_]+/gi, "_") : "experiment";
}

function buildCsvRowsFromSession(session) {
  return Object.values(session.samples || {})
    .flatMap((sampleGroup) => sampleGroup.points.map((point) => ({
      experiment_name: session.experimentName || "",
      started_at: session.startedAt || "",
      stopped_at: session.stoppedAt || "",
      feed: sampleGroup.feedKey,
      label: sampleGroup.label || "",
      unit: sampleGroup.unit || "",
      timestamp: point.timestamp,
      value: point.value,
    })))
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
}

function exportLatestCsv() {
  const session = getSessionForExport();

  if (!session) {
    throw new Error("Stop an experiment or save one locally before exporting");
  }

  const rows = buildCsvRowsFromSession(session);
  if (!rows.length) {
    throw new Error("No recorded session samples are available to export");
  }

  const header = ["experiment_name", "started_at", "stopped_at", "feed", "label", "unit", "timestamp", "value"];
  const lines = [
    header.join(","),
    ...rows.map((row) => header.map((column) => `"${String(row[column] ?? "").replace(/"/g, '""')}"`).join(",")),
  ];

  downloadTextFile(`${getExportFileStem(session)}-latest.csv`, `${lines.join("\n")}\n`, "text/csv;charset=utf-8");
}

function exportLatestJson() {
  const session = getSessionForExport();

  if (!session) {
    throw new Error("Stop an experiment or save one locally before exporting");
  }

  downloadTextFile(
    `${getExportFileStem(session)}-latest.json`,
    JSON.stringify(session, null, 2),
    "application/json;charset=utf-8",
  );
}

function exportStoredSnapshots() {
  const snapshots = getStoredSnapshots();

  if (!snapshots.length) {
    throw new Error("No stored snapshots available to export");
  }

  downloadTextFile(
    `${getExportFileStem()}-stored-snapshots.json`,
    JSON.stringify({
      exportedAt: new Date().toISOString(),
      snapshots: snapshots.map((snapshot) => serializeSession(snapshot)),
    }, null, 2),
    "application/json;charset=utf-8",
  );
}

function saveDataSnapshot() {
  if (activeExperimentSession && !activeExperimentSession.stoppedAt) {
    throw new Error("Stop the experiment before saving a snapshot");
  }

  if (!activeExperimentSession?.stoppedAt) {
    throw new Error("No stopped experiment is ready to save");
  }

  updateActiveExperimentMetadata();
  const snapshot = serializeSession(activeExperimentSession, {
    savedAt: new Date().toISOString(),
    running: false,
  });

  const snapshots = [snapshot, ...getStoredSnapshots()];
  setStoredSnapshots(snapshots);

  const sampleCount = getSessionSampleCount(snapshot);
  setStatus("ok", `Saved snapshot: ${snapshot.experimentName} · ${sampleCount} sample${sampleCount === 1 ? "" : "s"}`);
}

function clearStoredSnapshots() {
  localStorage.removeItem(SNAPSHOT_STORAGE_KEY);
  renderStoredSnapshots();
  setStatus("idle", "Stored experiment sessions cleared");
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
    .filter((result) => !result.error && !HIDDEN_TREND_SENSOR_IDS.has(result.sensor.id))
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
    if (!canvas) continue;
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
  const minValue = sensor.id === "pwm-duty" ? 0 : Math.min(...values);
  const maxValue = sensor.id === "pwm-duty" ? 100 : Math.max(...values);
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

async function publishElapsedTestTime(settings, elapsedSeconds) {
  if (!settings || !settings.username || !settings.aioKey) return;
  await postFeedValue(settings, "elapsed-test-s", elapsedSeconds);
}

function updateElapsedTestDisplay() {
  if (!elements.elapsedTestDisplay) return 0;

  if (!experimentStartTime) {
    elements.elapsedTestDisplay.textContent = formatElapsedTime(experimentElapsedSeconds);
    return experimentElapsedSeconds;
  }

  experimentElapsedSeconds = Math.max(0, Math.floor((Date.now() - experimentStartTime) / 1000));
  elements.elapsedTestDisplay.textContent = formatElapsedTime(experimentElapsedSeconds);
  return experimentElapsedSeconds;
}

async function tickExperimentClock() {
  const elapsedSeconds = updateElapsedTestDisplay();
  if (activeExperimentSession && !activeExperimentSession.stoppedAt) {
    activeExperimentSession.durationSeconds = elapsedSeconds;
    updateStorageStatus();
  }

  try {
    await publishElapsedTestTime(latestSettings, elapsedSeconds);
  } catch {
    // Keep the local clock running even if publishing fails.
  }

  if (Number.isFinite(experimentDurationSeconds) && elapsedSeconds >= experimentDurationSeconds) {
    stopExperiment();
    setStatus("ok", `Experiment completed at ${formatElapsedTime(elapsedSeconds)} and is ready to save/export`);
  }
}

function startExperimentClock() {
  experimentStartTime = Date.now();
  experimentElapsedSeconds = 0;

  if (experimentTimer) {
    clearInterval(experimentTimer);
  }

  tickExperimentClock();
  experimentTimer = setInterval(tickExperimentClock, 1000);
}

function stopExperimentClock() {
  if (experimentTimer) {
    clearInterval(experimentTimer);
    experimentTimer = null;
  }

  experimentStartTime = null;
  updateElapsedTestDisplay();
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

async function sendSystemEnable() {
  try {
    const settings = getControlSettings();

    if (!elements.systemEnableToggle) {
      throw new Error("System enable control is missing from the page");
    }

    const value = elements.systemEnableToggle.checked ? 1 : 0;
    await postFeedValue(settings, CONTROL_FEEDS.systemEnable, value);
    updateSystemEnableDisplay();

    setStatus("ok", `System enable sent: ${value ? "ON" : "OFF"}`);
  } catch (error) {
    setStatus("error", error.message || String(error));
  }
}

async function sendToggleControls() {
  await sendSystemEnable();
}

async function sendSystemReset() {
  try {
    const settings = getControlSettings();
    await postFeedValue(settings, CONTROL_FEEDS.systemReset, 1);
    setStatus("ok", "ESP32 reset command sent");
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

function startExperiment() {
  experimentDurationSeconds = clampNumber(Number(elements.testDurationValue.value), 0, 86400, 600);
  latestSettings = getSettingsFromForm();
  activeExperimentSession = createActiveExperimentSession();
  activeExperimentSampleKeys = new Set();
  startExperimentClock();
  updateStorageStatus();
  setStatus("ok", "Experiment recording started");
}

function stopExperiment() {
  stopExperimentClock();
  const session = finalizeActiveExperimentSession();

  if (session?.stoppedAt) {
    setStatus("ok", "Experiment stopped and ready to save/export");
  } else {
    setStatus("ok", "Experiment stopped");
  }
}

async function refreshData() {
  if (!latestSettings) return;

  const activeSensors = getActiveSensors(latestSettings);
  if (!activeSensors.length) {
    setStatus("error", "No feed keys configured");
    return;
  }

  setStatus("idle", "Loading feed data...");

  const results = await Promise.all(activeSensors.map(async (sensor) => {
    try {
      return await fetchFeedData(latestSettings, sensor);
    } catch (error) {
      return { sensor, points: [], error };
    }
  }));

  latestResults = results;

  addResultsToActiveExperimentSession(results);
  renderSummary(results);
  renderCharts(results);
  renderSensorCards(results);
  renderTable(results);

  const errors = results.filter((result) => result.error).length;
  if (errors > 0) {
    setStatus("error", `${errors} feed(s) failed. Check feed keys or AIO key.`);
  } else {
    setStatus("ok", `Connected to ${results.length} numeric feed(s)`);
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
elements.settingsToggle?.addEventListener("click", () => {
  const isExpanded = elements.settingsToggle.getAttribute("aria-expanded") === "true";
  setSettingsPanelExpanded(!isExpanded);
});
elements.saveDataSnapshot?.addEventListener("click", () => {
  try {
    saveDataSnapshot();
  } catch (error) {
    setStatus("error", error.message || String(error));
  }
});
elements.exportLatestCsv?.addEventListener("click", () => {
  try {
    exportLatestCsv();
    setStatus("ok", "Experiment data exported as CSV");
  } catch (error) {
    setStatus("error", error.message || String(error));
  }
});
elements.exportLatestJson?.addEventListener("click", () => {
  try {
    exportLatestJson();
    setStatus("ok", "Experiment data exported as JSON");
  } catch (error) {
    setStatus("error", error.message || String(error));
  }
});
elements.exportStoredJson?.addEventListener("click", () => {
  try {
    exportStoredSnapshots();
    setStatus("ok", "Stored experiment sessions exported as JSON");
  } catch (error) {
    setStatus("error", error.message || String(error));
  }
});
elements.clearStoredData?.addEventListener("click", clearStoredSnapshots);
elements.sendSetpoint.addEventListener("click", sendSetpoint);
if (elements.systemEnableToggle) elements.systemEnableToggle.addEventListener("change", updateSystemEnableDisplay);
if (elements.sendSystemEnable) elements.sendSystemEnable.addEventListener("click", sendSystemEnable);
elements.sendToggleControls.addEventListener("click", sendToggleControls);
elements.sendTestSettings.addEventListener("click", sendTestSettings);
elements.sendAllControls.addEventListener("click", sendAllControls);
elements.startExperiment.addEventListener("click", startExperiment);
elements.stopExperiment.addEventListener("click", stopExperiment);
elements.sendSystemReset.addEventListener("click", sendSystemReset);

if (elements.setpointTempSlider && elements.setpointTempValue) {
  syncControlPair(elements.setpointTempSlider, elements.setpointTempValue, elements.setpointDisplay, (value) => Number(value).toFixed(1));
}

if (elements.testNumberSlider && elements.testNumberValue) {
  syncControlPair(elements.testNumberSlider, elements.testNumberValue, elements.testNumberDisplay, (value) => String(Math.round(Number(value))));
}

if (elements.testDurationSlider && elements.testDurationValue) {
  syncControlPair(elements.testDurationSlider, elements.testDurationValue, elements.testDurationDisplay, (value) => String(Math.round(Number(value))));
}

loadSettings();
loadSettingsPanelState();
updateSystemEnableDisplay();
renderStoredSnapshots();
setStatus("idle", "Enter feed settings and connect");
renderSummary([]);
renderCharts([]);
renderSensorCards([]);
renderTable([]);
updateElapsedTestDisplay();
