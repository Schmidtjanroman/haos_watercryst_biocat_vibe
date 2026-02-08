"""
Binary-Sensor-Plattform für die Watercryst BIOCAT Integration.

Binary-Sensoren haben nur zwei Zustände: An/Aus (True/False).
Sie eignen sich perfekt für:
- Fehler-/Warnungszustand (Problem ja/nein)
- Leckage erkannt (ja/nein)
- Geräte-Konnektivität (verbunden ja/nein)

Jeder Binary-Sensor nutzt den DataUpdateCoordinator und hat eine
eigene value_fn zur Extraktion des Wertes aus den API-Daten.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatercrystDataUpdateCoordinator
from .const import (
    BINARY_SENSOR_CONNECTIVITY,
    BINARY_SENSOR_ERROR,
    BINARY_SENSOR_LEAKAGE_DETECTED,
    BINARY_SENSOR_WARNING,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class WatercrystBinarySensorDescription(BinarySensorEntityDescription):
    """
    Erweiterte Binary-Sensor-Beschreibung.

    Enthält eine value_fn die aus den Coordinator-Daten einen
    booleschen Wert extrahiert (True = Problem/Alarm, False = OK).
    """

    value_fn: Callable[[dict[str, Any]], bool | None]


# ============================================================================
# Definition aller Binary-Sensor-Entitäten
# ============================================================================

BINARY_SENSOR_DESCRIPTIONS: tuple[WatercrystBinarySensorDescription, ...] = (
    # Fehlerzustand – zeigt an, ob ein Fehler am Gerät vorliegt
    WatercrystBinarySensorDescription(
        key=BINARY_SENSOR_ERROR,
        translation_key=BINARY_SENSOR_ERROR,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.get("state", {}).get("error", False),
    ),
    # Warnungszustand – zeigt an, ob eine Warnung vorliegt
    WatercrystBinarySensorDescription(
        key=BINARY_SENSOR_WARNING,
        translation_key=BINARY_SENSOR_WARNING,
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda data: data.get("state", {}).get("warning", False),
    ),
    # Leckage erkannt – zeigt an, ob eine Leckage detektiert wurde
    WatercrystBinarySensorDescription(
        key=BINARY_SENSOR_LEAKAGE_DETECTED,
        translation_key=BINARY_SENSOR_LEAKAGE_DETECTED,
        device_class=BinarySensorDeviceClass.MOISTURE,
        value_fn=lambda data: data.get("leakage_protection", {}).get("leakage_detected", False),
    ),
    # Geräte-Konnektivität – zeigt an, ob das Gerät erreichbar ist
    WatercrystBinarySensorDescription(
        key=BINARY_SENSOR_CONNECTIVITY,
        translation_key=BINARY_SENSOR_CONNECTIVITY,
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda data: data.get("state", {}).get("connected", True),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Richtet alle Binary-Sensor-Entitäten ein.

    Args:
        hass: Die Home Assistant Instanz.
        entry: Der ConfigEntry der Integration.
        async_add_entities: Callback zum Registrieren neuer Entitäten.
    """
    coordinator: WatercrystDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = [
        WatercrystBinarySensor(coordinator, description, entry)
        for description in BINARY_SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)
    _LOGGER.debug("%d Binary-Sensor-Entitäten erstellt", len(entities))


class WatercrystBinarySensor(
    CoordinatorEntity[WatercrystDataUpdateCoordinator],
    BinarySensorEntity,
):
    """
    Repräsentiert einen Binary-Sensor der Watercryst BIOCAT Integration.

    Gibt True/False zurück basierend auf den Daten vom Coordinator.
    Die device_class bestimmt, wie der Sensor in der HA-Oberfläche
    dargestellt wird (z.B. "Problem" oder "Feuchtigkeit").
    """

    entity_description: WatercrystBinarySensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WatercrystDataUpdateCoordinator,
        description: WatercrystBinarySensorDescription,
        entry: ConfigEntry,
    ) -> None:
        """
        Initialisiert den Binary-Sensor.

        Args:
            coordinator: Der DataUpdateCoordinator.
            description: Die Sensor-Beschreibung mit value_fn.
            entry: Der ConfigEntry für die Geräte-Zuordnung.
        """
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Watercryst BIOCAT",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def is_on(self) -> bool | None:
        """
        Gibt den aktuellen Zustand des Binary-Sensors zurück.

        True = Aktiv/Problem erkannt, False = OK/Inaktiv.
        None = Zustand unbekannt (keine Daten).
        """
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
