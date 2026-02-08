"""Binary Sensor Plattform für Watercryst BIOCAT.

Binäre Sensoren aus /v1/state:
- online: Gerät erreichbar
- waterProtection.absenceModeEnabled: Abwesenheitsmodus aktiv
- waterProtection.leakageDetected: Leckage erkannt
- error: Fehler vorhanden
- warning: Warnung vorhanden
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatercrystDataCoordinator
from .const import (
    BINARY_SENSOR_ABSENCE_MODE,
    BINARY_SENSOR_ERROR,
    BINARY_SENSOR_LEAKAGE_DETECTED,
    BINARY_SENSOR_ONLINE,
    BINARY_SENSOR_WARNING,
    CONF_DEVICE_NAME,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    URL_WATERCRYST,
)


@dataclass(frozen=True, kw_only=True)
class WatercrystBinarySensorDescription(BinarySensorEntityDescription):
    """Beschreibung eines Watercryst Binary Sensors."""

    value_fn: Callable[[dict[str, Any]], bool | None]


BINARY_SENSOR_DESCRIPTIONS: list[WatercrystBinarySensorDescription] = [
    WatercrystBinarySensorDescription(
        key=BINARY_SENSOR_ONLINE,
        translation_key="device_online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda data: data.get("online"),
    ),
    WatercrystBinarySensorDescription(
        key=BINARY_SENSOR_ABSENCE_MODE,
        translation_key="absence_mode_active",
        value_fn=lambda data: data.get("absence_mode_enabled"),
    ),
    WatercrystBinarySensorDescription(
        key=BINARY_SENSOR_LEAKAGE_DETECTED,
        translation_key="leakage_detected",
        device_class=BinarySensorDeviceClass.MOISTURE,
        value_fn=lambda data: data.get("leakage_detected"),
    ),
    WatercrystBinarySensorDescription(
        key=BINARY_SENSOR_ERROR,
        translation_key="device_error",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.get("error"),
    ),
    WatercrystBinarySensorDescription(
        key=BINARY_SENSOR_WARNING,
        translation_key="device_warning",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.get("warning"),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Binary Sensoren einrichten."""
    coordinator: WatercrystDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        WatercrystBinarySensor(coordinator, description, entry)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class WatercrystBinarySensor(
    CoordinatorEntity[WatercrystDataCoordinator], BinarySensorEntity
):
    """Binary Sensor für Watercryst BIOCAT."""

    entity_description: WatercrystBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WatercrystDataCoordinator,
        description: WatercrystBinarySensorDescription,
        entry: ConfigEntry,
    ) -> None:
        """Binary Sensor initialisieren."""
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
    def is_on(self) -> bool | None:
        """Aktueller Zustand."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
