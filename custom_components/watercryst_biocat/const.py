"""Konstanten für die Watercryst BIOCAT Integration.

API-Dokumentation: https://appapi.watercryst.com/api-v1.yaml
API-Key Verwaltung: https://app.watercryst.com/Device/
"""
from __future__ import annotations

from datetime import timedelta

# Integration Domain
DOMAIN = "watercryst_biocat"

# API Konfiguration – bestätigt durch offizielle Dokumentation
API_BASE_URL = "https://appapi.watercryst.com"
API_HEADER_KEY = "x-api-key"

# API Endpunkte (bestätigt durch Community-Tests und offizielle Doku)
# GET-Endpunkte für Datenabfrage
ENDPOINT_MEASUREMENTS = "/v1/measurements/direct"
ENDPOINT_STATE = "/v1/state"
ENDPOINT_STATISTICS_DAILY = "/v1/statistics/cumulative/daily"
ENDPOINT_STATISTICS_DAILY_DIRECT = "/v1/statistics/daily/direct"
ENDPOINT_STATISTICS_WEEKLY = "/v1/statistics/cumulative/weekly"
ENDPOINT_STATISTICS_MONTHLY = "/v1/statistics/cumulative/monthly"

# PUT/POST-Endpunkte für Steuerung
ENDPOINT_ABSENCE_MODE = "/v1/state/absenceMode"
ENDPOINT_LEAKAGE_PROTECTION = "/v1/state/leakageProtection"
ENDPOINT_WATER_SUPPLY = "/v1/waterSupply"
ENDPOINT_SELFTEST = "/v1/selftest"
ENDPOINT_ACKNOWLEDGE_WARNING = "/v1/state/acknowledge"

# Update Intervall (Sekunden) – versetzt um DoS zu vermeiden
# Hinweis: Watercryst API verträgt keine gleichzeitigen Requests
UPDATE_INTERVAL_MEASUREMENTS = timedelta(seconds=30)
UPDATE_INTERVAL_STATE = timedelta(seconds=15)
UPDATE_INTERVAL_STATISTICS = timedelta(seconds=60)

# Config Flow Schlüssel
CONF_API_KEY = "api_key"
CONF_POLL_INTERVAL = "poll_interval"
CONF_DEVICE_NAME = "device_name"

# Default-Werte
DEFAULT_POLL_INTERVAL = 30
DEFAULT_DEVICE_NAME = "BIOCAT"

# Sensor-Schlüssel (aus /v1/measurements/direct Response)
SENSOR_WATER_TEMP = "waterTemp"
SENSOR_PRESSURE = "pressure"
SENSOR_LAST_TAP_VOLUME = "lastWaterTapVolume"
SENSOR_LAST_TAP_DURATION = "lastWaterTapDuration"

# Sensor-Schlüssel (aus /v1/state Response)
SENSOR_MODE = "mode_name"
SENSOR_DEVICE_STATE = "device_state"

# Statistik-Schlüssel
SENSOR_CONSUMPTION_DAILY = "consumption_daily"
SENSOR_CONSUMPTION_WEEKLY = "consumption_weekly"
SENSOR_CONSUMPTION_MONTHLY = "consumption_monthly"

# Binary Sensor Schlüssel (aus /v1/state Response)
BINARY_SENSOR_ONLINE = "online"
BINARY_SENSOR_ABSENCE_MODE = "absence_mode_enabled"
BINARY_SENSOR_LEAKAGE_DETECTED = "leakage_detected"
BINARY_SENSOR_ERROR = "error"
BINARY_SENSOR_WARNING = "warning"

# Switch Schlüssel
SWITCH_ABSENCE_MODE = "absence_mode"
SWITCH_LEAKAGE_PROTECTION = "leakage_protection"

# Button Schlüssel
BUTTON_SELFTEST = "selftest"
BUTTON_ACKNOWLEDGE = "acknowledge_warning"

# Plattformen die diese Integration registriert
PLATFORMS = ["sensor", "binary_sensor", "switch", "button"]

# Referenz-URLs
URL_API_DOCS = "https://appapi.watercryst.com"
URL_API_KEY_MANAGEMENT = "https://app.watercryst.com/Device/"
URL_WATERCRYST = "https://www.watercryst.com"
