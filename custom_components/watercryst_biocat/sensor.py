"""Sensor-Plattform für Watercryst BIOCAT.

Sensoren:
- /v1/measurements/direct → waterTemp, pressure, lastWaterTapVolume, lastWaterTapDuration
- /v1/statistics/cumulative/daily → Tagesverbrauch
- /v1/statistics/cumulative/total → Gesamtverbrauch (⚠️ zu verifizieren)
- /v1/state → mode.name, Timestamps (falls vorhanden)

Wochen-/Monatsverbrauch wurde in v3.0.0 entfernt.
HA berechnet diese automatisch im Energie-Dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

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
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatercrystDataCoordinator
from .const import (
    CONF_DEVICE_NAME,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    SENSOR_CONSUMPTION_DAILY,
    SENSOR_CONSUMPTION_TOTAL,
    SENSOR_LAST_LEAKAGE_TEST,
    SENSOR_LAST_SELFTEST,
    SENSOR_LAST_TAP_DURATION,
    SENSOR_LAST_TAP_VOLUME,
    SENSOR_MODE,
    SENSOR_PRESSURE,
    SENSOR_WATER_TEMP,
    URL_WATERCRYST,
)


@dataclass(frozen=True, kw_only=True)
class WatercrystSensorDescription(SensorEntityDescription):
    """Beschreibung eines Watercryst Sensors."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: list[WatercrystSensorDescription] = [
    # ─── Aus /v1/measurements/direct ─────────────────────────────────
    WatercrystSensorDescription(
        key=SENSOR_WATER_TEMP,
        translation_key="water_temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("waterTemp"),
    ),
    WatercrystSensorDescription(
        key=SENSOR_PRESSURE,
        translation_key="water_pressure",
        native_unit_of_measurement=UnitOfPressure.BAR,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda data: data.get("pressure"),
    ),
    WatercrystSensorDescription(
        key=SENSOR_LAST_TAP_VOLUME,
        translation_key="last_tap_volume",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("lastWaterTapVolume"),
    ),
    WatercrystSensorDescription(
        key=SENSOR_LAST_TAP_DURATION,
        translation_key="last_tap_duration",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("lastWaterTapDuration"),
    ),
    # ─── Statistik ───────────────────────────────────────────────────
    WatercrystSensorDescription(
        key=SENSOR_CONSUMPTION_DAILY,
        translation_key="consumption_daily",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("consumption_daily"),
    ),
    WatercrystSensorDescription(
        key=SENSOR_CONSUMPTION_TOTAL,
        translation_key="consumption_total",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("consumption_total"),
    ),
    # ─── Aus /v1/state ───────────────────────────────────────────────
    WatercrystSensorDescription(
        key=SENSOR_MODE,
        translation_key="operation_mode",
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda data: data.get("mode_name"),
    ),
    # ─── Timestamps (aus /v1/state, falls vorhanden) ────────────────
    WatercrystSensorDescription(
        key=SENSOR_LAST_LEAKAGE_TEST,
        translation_key="last_leakage_test",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:water-check",
        value_fn=lambda data: data.get("last_leakage_test"),
    ),
    WatercrystSensorDescription(
        key=SENSOR_LAST_SELFTEST,
        translation_key="last_selftest",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:test-tube",
        value_fn=lambda data: data.get("last_selftest"),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensoren einrichten."""
    coordinator: WatercrystDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        WatercrystSensor(coordinator, description, entry)
        for description in SENSOR_DESCRIPTIONS
    )


class WatercrystSensor(CoordinatorEntity[WatercrystDataCoordinator], SensorEntity):
    """Sensor für Watercryst BIOCAT Messwerte."""

    entity_description: WatercrystSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WatercrystDataCoordinator,
        description: WatercrystSensorDescription,
        entry: ConfigEntry,
    ) -> None:
        """Sensor initialisieren."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"

        device_name = entry.data.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Watercryst {device_name}",
            manufacturer="WATERCryst Wassertechnik GmbH",
            model="BIOCAT KLS",
            configuration_url=URL_WATERCRYST,
        )

    @property
    def native_value(self) -> Any:
        """Aktueller Sensorwert aus den Coordinator-Daten."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
