"""
Switch-Plattform für die Watercryst BIOCAT Integration.

Switches repräsentieren umschaltbare Funktionen des Gerätes:
- Abwesenheitsmodus (On = Abwesend, Off = Anwesend)
- Leckageschutz (On = Aktiv, Off = Deaktiviert)

Jeder Switch kommuniziert direkt mit der API, um den Zustand zu ändern,
und nutzt den DataUpdateCoordinator für den aktuellen Status.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatercrystDataUpdateCoordinator
from .api import WatercrystApiClient, WatercrystApiError
from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    SWITCH_ABSENCE,
    SWITCH_LEAKAGE_PROTECTION,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class WatercrystSwitchDescription(SwitchEntityDescription):
    """
    Erweiterte Switch-Beschreibung.

    Enthält Funktionen zum Lesen des aktuellen Zustands (value_fn),
    zum Einschalten (turn_on_fn) und zum Ausschalten (turn_off_fn).
    """

    value_fn: Callable[[dict[str, Any]], bool | None]
    turn_on_fn: Callable[[WatercrystApiClient], Coroutine[Any, Any, dict[str, Any]]]
    turn_off_fn: Callable[[WatercrystApiClient], Coroutine[Any, Any, dict[str, Any]]]


# ============================================================================
# Definition der Switch-Entitäten
# ============================================================================

SWITCH_DESCRIPTIONS: tuple[WatercrystSwitchDescription, ...] = (
    # Abwesenheitsmodus: On = Abwesend (Gerät im Schutzmodus)
    WatercrystSwitchDescription(
        key=SWITCH_ABSENCE,
        translation_key=SWITCH_ABSENCE,
        icon="mdi:home-export-outline",
        device_class=SwitchDeviceClass.SWITCH,
        value_fn=lambda data: data.get("absence", {}).get("active"),
        turn_on_fn=lambda client: client.set_absence(active=True),
        turn_off_fn=lambda client: client.set_absence(active=False),
    ),
    # Leckageschutz: On = Schutz aktiviert
    WatercrystSwitchDescription(
        key=SWITCH_LEAKAGE_PROTECTION,
        translation_key=SWITCH_LEAKAGE_PROTECTION,
        icon="mdi:shield-home",
        device_class=SwitchDeviceClass.SWITCH,
        value_fn=lambda data: data.get("leakage_protection", {}).get("enabled"),
        turn_on_fn=lambda client: client.set_leakage_protection(enabled=True),
        turn_off_fn=lambda client: client.set_leakage_protection(enabled=False),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Richtet alle Switch-Entitäten ein.

    Args:
        hass: Die Home Assistant Instanz.
        entry: Der ConfigEntry der Integration.
        async_add_entities: Callback zum Registrieren neuer Entitäten.
    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: WatercrystDataUpdateCoordinator = data["coordinator"]
    client: WatercrystApiClient = data["client"]

    entities = [
        WatercrystSwitch(coordinator, client, description, entry)
        for description in SWITCH_DESCRIPTIONS
    ]

    async_add_entities(entities)
    _LOGGER.debug("%d Switch-Entitäten erstellt", len(entities))


class WatercrystSwitch(
    CoordinatorEntity[WatercrystDataUpdateCoordinator],
    SwitchEntity,
):
    """
    Repräsentiert einen Switch der Watercryst BIOCAT Integration.

    Ein Switch kann ein- und ausgeschaltet werden. Der aktuelle Zustand
    wird vom Coordinator gelesen, Zustandsänderungen werden direkt
    über den API-Client an die Cloud gesendet.
    """

    entity_description: WatercrystSwitchDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WatercrystDataUpdateCoordinator,
        client: WatercrystApiClient,
        description: WatercrystSwitchDescription,
        entry: ConfigEntry,
    ) -> None:
        """
        Initialisiert den Switch.

        Args:
            coordinator: Der DataUpdateCoordinator.
            client: Der API-Client für direkte Aufrufe.
            description: Die Switch-Beschreibung.
            entry: Der ConfigEntry.
        """
        super().__init__(coordinator)
        self.entity_description = description
        self._client = client
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
        Gibt den aktuellen Zustand des Switches zurück.

        True = Eingeschaltet, False = Ausgeschaltet, None = Unbekannt.
        """
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """
        Schaltet den Switch ein.

        Sendet den Einschalt-Befehl an die API und aktualisiert
        anschließend die Coordinator-Daten.
        """
        _LOGGER.debug("Schalte '%s' ein", self.entity_description.key)
        try:
            await self.entity_description.turn_on_fn(self._client)
            # Coordinator-Daten sofort aktualisieren, damit die UI
            # den neuen Zustand ohne Verzögerung anzeigt
            await self.coordinator.async_request_refresh()
        except WatercrystApiError as err:
            _LOGGER.error(
                "Fehler beim Einschalten von '%s': %s",
                self.entity_description.key,
                err,
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """
        Schaltet den Switch aus.

        Sendet den Ausschalt-Befehl an die API und aktualisiert
        anschließend die Coordinator-Daten.
        """
        _LOGGER.debug("Schalte '%s' aus", self.entity_description.key)
        try:
            await self.entity_description.turn_off_fn(self._client)
            await self.coordinator.async_request_refresh()
        except WatercrystApiError as err:
            _LOGGER.error(
                "Fehler beim Ausschalten von '%s': %s",
                self.entity_description.key,
                err,
            )
