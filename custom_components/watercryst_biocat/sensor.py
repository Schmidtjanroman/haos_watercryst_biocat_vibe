"""Sensor-Plattform für Watercryst BIOCAT.

Sensoren basierend auf den echten API-Endpunkten:
- /v1/measurements/direct → waterTemp, pressure, lastWaterTapVolume, lastWaterTapDuration
- /v1/statistics/cumulative/daily → Tagesverbrauch
- /v1/statistics/cumulative/weekly → Wochenverbrauch
- /v1/statistics/cumulative/monthly → Monatsverbrauch
- /v1/state → mode.name (Betriebsmodus)
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
    SENSOR_CONSUMPTION_MONTHLY,
    SENSOR_CONSUMPTION_WEEKLY,
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


# Sensor-Definitionen basierend auf echten API-Antworten
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
    # ─── Aus /v1/statistics/cumulative/* ──────────────────────────────
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
        key=SENSOR_CONSUMPTION_WEEKLY,
        translation_key="consumption_weekly",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("consumption_weekly"),
    ),
    WatercrystSensorDescription(
        key=SENSOR_CONSUMPTION_MONTHLY,
        translation_key="consumption_monthly",
        native_unit_of_measurement=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=0,
        value_fn=lambda data: data.get("consumption_monthly"),
    ),
    # ─── Aus /v1/state ───────────────────────────────────────────────
    WatercrystSensorDescription(
        key=SENSOR_MODE,
        translation_key="operation_mode",
        device_class=SensorDeviceClass.ENUM,
        value_fn=lambda data: data.get("mode_name"),
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
