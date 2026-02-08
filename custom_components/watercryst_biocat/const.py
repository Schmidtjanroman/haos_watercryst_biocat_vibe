"""
Konstanten für die Watercryst BIOCAT Integration.

Diese Datei enthält alle zentralen Konstanten, die in der gesamten Integration
verwendet werden. Keine hardcodierten Strings für die Benutzeroberfläche –
alle Labels kommen aus den Translation-Dateien.
"""

from datetime import timedelta

# ============================================================================
# Grundlegende Integrations-Konstanten
# ============================================================================

# Eindeutiger Bezeichner der Integration (muss mit dem Ordnernamen übereinstimmen)
DOMAIN: str = "watercryst_biocat"

# Basis-URL der Watercryst Cloud-API
API_BASE_URL: str = "https://appapi.watercryst.com"

# ============================================================================
# Konfigurationsschlüssel (für ConfigEntry.data)
# ============================================================================

CONF_USERNAME: str = "username"
CONF_PASSWORD: str = "password"
CONF_TOKEN: str = "access_token"
CONF_REFRESH_TOKEN: str = "refresh_token"
CONF_DEVICE_ID: str = "device_id"

# ============================================================================
# Plattformen, die diese Integration registriert
# ============================================================================

PLATFORMS: list[str] = [
    "sensor",
    "binary_sensor",
    "switch",
    "button",
]

# ============================================================================
# Update-Intervall für den DataUpdateCoordinator
# ============================================================================

# Alle 60 Sekunden die API abfragen (vernünftiger Kompromiss zwischen
# Aktualität und API-Last)
UPDATE_INTERVAL: timedelta = timedelta(seconds=60)

# ============================================================================
# API-Endpunkte (relativ zur Basis-URL)
# ============================================================================

ENDPOINT_LOGIN: str = "/auth/login"
ENDPOINT_REFRESH: str = "/auth/refresh"
ENDPOINT_DEVICES: str = "/devices"
ENDPOINT_MEASUREMENTS: str = "/measurements"
ENDPOINT_STATISTICS: str = "/statistics"
ENDPOINT_ABSENCE: str = "/absence"
ENDPOINT_LEAKAGE_PROTECTION: str = "/leakageprotection"
ENDPOINT_ML_MEASUREMENT: str = "/mlmeasurement"
ENDPOINT_SELFTEST: str = "/selftest"
ENDPOINT_WATER_SUPPLY: str = "/watersupply"
ENDPOINT_ACK_EVENT: str = "/ackevent"
ENDPOINT_STATE: str = "/state"
ENDPOINT_WEBHOOKS: str = "/webhooks"

# ============================================================================
# Sensor-Schlüssel (werden als entity-Keys und für Übersetzungen verwendet)
# ============================================================================

# Messwert-Sensoren
SENSOR_WATER_CONSUMPTION: str = "water_consumption"
SENSOR_WATER_PRESSURE: str = "water_pressure"
SENSOR_WATER_TEMPERATURE: str = "water_temperature"
SENSOR_WATER_HARDNESS: str = "water_hardness"
SENSOR_FLOW_RATE: str = "flow_rate"
SENSOR_TOTAL_CONSUMPTION: str = "total_consumption"
SENSOR_DAILY_CONSUMPTION: str = "daily_consumption"

# Status-Sensoren
SENSOR_SELFTEST_RESULT: str = "selftest_result"
SENSOR_SELFTEST_LAST_RUN: str = "selftest_last_run"
SENSOR_LEAKAGE_LAST_RUN: str = "leakage_last_run"
SENSOR_ERROR_MESSAGE: str = "error_message"
SENSOR_DEVICE_STATE: str = "device_state"

# Statistik-Sensoren
SENSOR_STAT_WEEKLY: str = "stat_weekly_consumption"
SENSOR_STAT_MONTHLY: str = "stat_monthly_consumption"

# Binary-Sensoren
BINARY_SENSOR_ERROR: str = "error_state"
BINARY_SENSOR_WARNING: str = "warning_state"
BINARY_SENSOR_LEAKAGE_DETECTED: str = "leakage_detected"
BINARY_SENSOR_CONNECTIVITY: str = "connectivity"

# Switches
SWITCH_ABSENCE: str = "absence_mode"
SWITCH_LEAKAGE_PROTECTION: str = "leakage_protection"

# Buttons
BUTTON_ACK_WARNING: str = "acknowledge_warning"
BUTTON_START_SELFTEST: str = "start_selftest"

# ============================================================================
# Geräte-Informationen
# ============================================================================

MANUFACTURER: str = "Watercryst"
MODEL: str = "BIOCAT"
DEVICE_IMAGE_URL: str = (
    "https://assets.heizung-billiger.de/images/watercryst/"
    "large_default/large_default-12000273_B_.jpg@webp"
)
