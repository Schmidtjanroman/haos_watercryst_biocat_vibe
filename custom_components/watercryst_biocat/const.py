"""Konstanten für die Watercryst BIOCAT Integration.

API-Dokumentation: https://appapi.watercryst.com/api-v1.yaml
API-Key Verwaltung: https://app.watercryst.com/Device/

Hinweis zu den Endpunkten:
  ✅ = Community-getestet (Loxforum, simon42)
  ⚠️  = Logischer Endpunkt, muss gegen echte API verifiziert werden
"""
from __future__ import annotations

# Integration Domain
DOMAIN = "watercryst_biocat"

# API Konfiguration
API_BASE_URL = "https://appapi.watercryst.com"
API_HEADER_KEY = "x-api-key"

# ─── GET-Endpunkte ──────────────────────────────────────────────────
ENDPOINT_MEASUREMENTS = "/v1/measurements/direct"        # ✅ bestätigt
ENDPOINT_STATE = "/v1/state"                              # ✅ bestätigt
ENDPOINT_STATISTICS_DAILY = "/v1/statistics/cumulative/daily"  # ✅ bestätigt
ENDPOINT_STATISTICS_TOTAL = "/v1/statistics/cumulative/total"  # ⚠️ zu prüfen

# ─── PUT/POST-Endpunkte ─────────────────────────────────────────────
ENDPOINT_ABSENCE_MODE = "/v1/state/absenceMode"           # ✅ bestätigt
ENDPOINT_LEAKAGE_PROTECTION = "/v1/state/leakageProtection"  # ✅ bestätigt
ENDPOINT_WATER_SUPPLY_OPEN = "/v1/watersupply/open"       # ✅ bestätigt
ENDPOINT_WATER_SUPPLY_CLOSE = "/v1/watersupply/close"     # ✅ bestätigt
ENDPOINT_SELFTEST = "/v1/selftest"                        # ✅ bestätigt
ENDPOINT_ACKNOWLEDGE_WARNING = "/v1/state/acknowledge"    # ✅ bestätigt

# ─── ENTFERNT in v3.0.0 ─────────────────────────────────────────────
# ENDPOINT_STATISTICS_WEEKLY  – Nie Community-getestet, redundant mit HA-Statistik
# ENDPOINT_STATISTICS_MONTHLY – Nie Community-getestet, redundant mit HA-Statistik
# HA berechnet Wochen-/Monats-/Jahresstatistiken automatisch aus dem
# Tagesverbrauch-Sensor (state_class: total) im Energie-Dashboard.

# Config Flow
CONF_API_KEY = "api_key"
CONF_POLL_INTERVAL = "poll_interval"
CONF_DEVICE_NAME = "device_name"
DEFAULT_POLL_INTERVAL = 30
DEFAULT_DEVICE_NAME = "BIOCAT"

# ─── Sensor Keys ────────────────────────────────────────────────────
# Aus /v1/measurements/direct
SENSOR_WATER_TEMP = "waterTemp"
SENSOR_PRESSURE = "pressure"
SENSOR_LAST_TAP_VOLUME = "lastWaterTapVolume"
SENSOR_LAST_TAP_DURATION = "lastWaterTapDuration"

# Aus /v1/state
SENSOR_MODE = "mode_name"

# Aus /v1/statistics/cumulative/*
SENSOR_CONSUMPTION_DAILY = "consumption_daily"
SENSOR_CONSUMPTION_TOTAL = "consumption_total"

# Timestamps (dynamisch aus /v1/state extrahiert, falls vorhanden)
SENSOR_LAST_LEAKAGE_TEST = "last_leakage_test"
SENSOR_LAST_SELFTEST = "last_selftest"
SENSOR_ERROR_MESSAGE = "error_message"
SENSOR_SELFTEST_RESULT = "selftest_result"

# ─── Binary Sensor Keys ────────────────────────────────────────────
BINARY_SENSOR_ONLINE = "online"
BINARY_SENSOR_ABSENCE_MODE = "absence_mode_enabled"
BINARY_SENSOR_LEAKAGE_DETECTED = "leakage_detected"
BINARY_SENSOR_ERROR = "error"
BINARY_SENSOR_WARNING = "warning"

# ─── Switch Keys ───────────────────────────────────────────────────
SWITCH_ABSENCE_MODE = "absence_mode"
SWITCH_LEAKAGE_PROTECTION = "leakage_protection"
SWITCH_WATER_SUPPLY = "water_supply"

# ─── Button Keys ───────────────────────────────────────────────────
BUTTON_SELFTEST = "selftest"
BUTTON_ACKNOWLEDGE = "acknowledge_warning"

# Plattformen
PLATFORMS = ["sensor", "binary_sensor", "switch", "button"]

# URLs
URL_API_DOCS = "https://appapi.watercryst.com"
URL_API_KEY_MANAGEMENT = "https://app.watercryst.com/Device/"
URL_WATERCRYST = "https://www.watercryst.com"
