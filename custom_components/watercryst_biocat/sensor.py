"""
Sensor-Plattform für die Watercryst BIOCAT Integration.

Diese Datei definiert alle Sensor-Entitäten, die von der Integration
erstellt werden. Die Sensoren nutzen den DataUpdateCoordinator, um
periodisch aktualisierte Daten zu erhalten.

Wichtige Konzepte:
- state_class: MEASUREMENT → HA erstellt automatisch Langzeit-Statistiken
- state_class: TOTAL_INCREASING → Für Zähler die nur steigen (z.B. Verbrauch)
- device_class: Ermöglicht automatische Einheiten-Konvertierung und Icons

Alle Entitätsnamen und Beschreibungen kommen aus den Translation-Dateien.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatercrystDataUpdateCoordinator
from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SENSOR_DAILY_CONSUMPTION,
    SENSOR_DEVICE_STATE,
    SENSOR_ERROR_MESSAGE,
    SENSOR_FLOW_RATE,
    SENSOR_LEAKAGE_LAST_RUN,
    SENSOR_SELFTEST_LAST_RUN,
    SENSOR_SELFTEST_RESULT,
    SENSOR_STAT_MONTHLY,
    SENSOR_STAT_WEEKLY,
    SENSOR_TOTAL_CONSUMPTION,
    SENSOR_WATER_HARDNESS,
    SENSOR_WATER_PRESSURE,
    SENSOR_WATER_TEMPERATURE,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class WatercrystSensorDescription(SensorEntityDescription):
    """
    Erweiterte Sensor-Beschreibung mit einer Funktion zur Wert-Extraktion.

    Das Feld 'value_fn' definiert, wie der Sensorwert aus den
    Coordinator-Daten extrahiert wird. So kann jeder Sensor flexibel
    auf seine Datenquelle zugreifen.
    """

    value_fn: Callable[[dict[str, Any]], Any]
    data_key: str = ""  # Hauptschlüssel im Coordinator-Daten-Dict


# ============================================================================
# Definition aller Sensor-Entitäten
# ============================================================================

SENSOR_DESCRIPTIONS: tuple[WatercrystSensorDescription, ...] = (
    # --- Messwerte (measurements) ---
    # Wasserdruck mit automatischer Statistik-Erfassung
    WatercrystSensorDescription(
        key=SENSOR_WATER_PRESSURE,
        translation_key=SENSOR_WATER_PRESSURE,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        data_key="measurements",
        value_fn=lambda data: data.get("measurements", {}).get("pressure"),
    ),
    # Wassertemperatur
    WatercrystSensorDescription(
        key=SENSOR_WATER_TEMPERATURE,
        translation_key=SENSOR_WATER_TEMPERATURE,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        data_key="measurements",
        value_fn=lambda data: data.get("measurements", {}).get("temperature"),
    ),
    # Wasserhärte (keine Standard device_class vorhanden)
    WatercrystSensorDescription(
        key=SENSOR_WATER_HARDNESS,
        translation_key=SENSOR_WATER_HARDNESS,
        icon="mdi:water-opacity",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°dH",
        suggested_display_precision=1,
        data_key="measurements",
        value_fn=lambda data: data.get("measurements", {}).get("hardness"),
    ),
    # Durchflussrate
    WatercrystSensorDescription(
        key=SENSOR_FLOW_RATE,
        translation_key=SENSOR_FLOW_RATE,
        icon="mdi:water-pump",
        device_class=SensorDeviceClass.VOLUME_FLOW_RATE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        suggested_display_precision=1,
        data_key="measurements",
        value_fn=lambda data: data.get("measurements", {}).get("flow_rate"),
    ),
    # --- Wasserversorgung / Verbrauch ---
    # Gesamtverbrauch (stetig steigend → total_increasing für korrekte Statistiken)
    WatercrystSensorDescription(
        key=SENSOR_TOTAL_CONSUMPTION,
        translation_key=SENSOR_TOTAL_CONSUMPTION,
        icon="mdi:water",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=0,
        data_key="water_supply",
        value_fn=lambda data: data.get("water_supply", {}).get("total_consumption"),
    ),
    # Tagesverbrauch
    WatercrystSensorDescription(
        key=SENSOR_DAILY_CONSUMPTION,
        translation_key=SENSOR_DAILY_CONSUMPTION,
        icon="mdi:water-outline",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=1,
        data_key="water_supply",
        value_fn=lambda data: data.get("water_supply", {}).get("daily_consumption"),
    ),
    # --- Selbsttest ---
    # Ergebnis des letzten Selbsttests (Text: "ok", "failed", "pending")
    WatercrystSensorDescription(
        key=SENSOR_SELFTEST_RESULT,
        translation_key=SENSOR_SELFTEST_RESULT,
        icon="mdi:clipboard-check-outline",
        data_key="selftest",
        value_fn=lambda data: data.get("selftest", {}).get("result"),
    ),
    # Zeitpunkt des letzten Selbsttests
    WatercrystSensorDescription(
        key=SENSOR_SELFTEST_LAST_RUN,
        translation_key=SENSOR_SELFTEST_LAST_RUN,
        device_class=SensorDeviceClass.TIMESTAMP,
        data_key="selftest",
        value_fn=lambda data: data.get("selftest", {}).get("last_run"),
    ),
    # --- Leckageschutz ---
    # Zeitpunkt der letzten Leckageschutz-Prüfung
    WatercrystSensorDescription(
        key=SENSOR_LEAKAGE_LAST_RUN,
        translation_key=SENSOR_LEAKAGE_LAST_RUN,
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:shield-check",
        data_key="leakage_protection",
        value_fn=lambda data: data.get("leakage_protection", {}).get("last_run"),
    ),
    # --- Gerätestatus ---
    # Aktueller Betriebszustand des Gerätes
    WatercrystSensorDescription(
        key=SENSOR_DEVICE_STATE,
        translation_key=SENSOR_DEVICE_STATE,
        icon="mdi:information-outline",
        data_key="state",
        value_fn=lambda data: data.get("state", {}).get("state"),
    ),
    # Fehlermeldungstext (leer wenn kein Fehler)
    WatercrystSensorDescription(
        key=SENSOR_ERROR_MESSAGE,
        translation_key=SENSOR_ERROR_MESSAGE,
        icon="mdi:alert-circle-outline",
        data_key="state",
        value_fn=lambda data: data.get("state", {}).get("error_message"),
    ),
    # --- Statistiken ---
    # Wöchentlicher Verbrauch
    WatercrystSensorDescription(
        key=SENSOR_STAT_WEEKLY,
        translation_key=SENSOR_STAT_WEEKLY,
        icon="mdi:chart-bar",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=0,
        data_key="statistics",
        value_fn=lambda data: data.get("statistics", {}).get("weekly_consumption"),
    ),
    # Monatlicher Verbrauch
    WatercrystSensorDescription(
        key=SENSOR_STAT_MONTHLY,
        translation_key=SENSOR_STAT_MONTHLY,
        icon="mdi:chart-areaspline",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        suggested_display_precision=0,
        data_key="statistics",
        value_fn=lambda data: data.get("statistics", {}).get("monthly_consumption"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Richtet alle Sensor-Entitäten basierend auf dem ConfigEntry ein.

    Wird von Home Assistant aufgerufen, nachdem die Integration geladen wurde.
    Erstellt für jede Sensor-Beschreibung eine WatercrystSensor-Instanz.

    Args:
        hass: Die Home Assistant Instanz.
        entry: Der ConfigEntry der Integration.
        async_add_entities: Callback zum Registrieren neuer Entitäten.
    """
    coordinator: WatercrystDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Für jede Sensor-Beschreibung eine Entität erstellen
    entities = [
        WatercrystSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)
    _LOGGER.debug("%d Sensor-Entitäten für Watercryst BIOCAT erstellt", len(entities))


class WatercrystSensor(CoordinatorEntity[WatercrystDataUpdateCoordinator], SensorEntity):
    """
    Repräsentiert einen einzelnen Sensor der Watercryst BIOCAT Integration.

    Erbt von CoordinatorEntity, um automatisch über neue Daten vom
    DataUpdateCoordinator informiert zu werden. Jeder Sensor hat eine
    eigene Beschreibung (WatercrystSensorDescription), die definiert,
    wie der Wert aus den Coordinator-Daten extrahiert wird.
    """

    entity_description: WatercrystSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WatercrystDataUpdateCoordinator,
        description: WatercrystSensorDescription,
        entry: ConfigEntry,
    ) -> None:
        """
        Initialisiert den Sensor.

        Args:
            coordinator: Der DataUpdateCoordinator mit den API-Daten.
            description: Die Sensor-Beschreibung mit value_fn.
            entry: Der ConfigEntry für die Geräte-Zuordnung.
        """
        super().__init__(coordinator)
        self.entity_description = description

        # Eindeutige ID: Kombination aus Entry-ID und Sensor-Key
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        # Geräte-Information für die HA-Geräteübersicht
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Watercryst BIOCAT",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def native_value(self) -> Any:
        """
        Gibt den aktuellen Sensorwert zurück.

        Nutzt die value_fn aus der Sensor-Beschreibung, um den Wert
        aus den Coordinator-Daten zu extrahieren. Wenn keine Daten
        vorhanden sind, wird None zurückgegeben.
        """
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
