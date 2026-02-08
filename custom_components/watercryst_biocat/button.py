"""
Button-Plattform für die Watercryst BIOCAT Integration.

Buttons sind Einmal-Aktionen, die keine Zustände haben:
- Selbsttest starten: Löst einen Geräte-Selbsttest aus
- Warnung bestätigen: Quittiert aktive Warnungen/Fehler

Nach dem Drücken wird die Aktion an die API gesendet und
der Coordinator aktualisiert.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatercrystDataUpdateCoordinator
from .api import WatercrystApiClient, WatercrystApiError
from .const import (
    BUTTON_ACK_WARNING,
    BUTTON_START_SELFTEST,
    DOMAIN,
    MANUFACTURER,
    MODEL,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class WatercrystButtonDescription(ButtonEntityDescription):
    """
    Erweiterte Button-Beschreibung.

    Enthält eine press_fn, die beim Drücken des Buttons aufgerufen wird
    und den entsprechenden API-Aufruf durchführt.
    """

    press_fn: Callable[[WatercrystApiClient], Coroutine[Any, Any, dict[str, Any]]]


# ============================================================================
# Definition der Button-Entitäten
# ============================================================================

BUTTON_DESCRIPTIONS: tuple[WatercrystButtonDescription, ...] = (
    # Selbsttest starten – löst den Geräte-Selbsttest aus
    WatercrystButtonDescription(
        key=BUTTON_START_SELFTEST,
        translation_key=BUTTON_START_SELFTEST,
        icon="mdi:play-circle-outline",
        device_class=ButtonDeviceClass.RESTART,
        press_fn=lambda client: client.start_selftest(),
    ),
    # Warnung bestätigen – quittiert alle aktiven Warnungen
    WatercrystButtonDescription(
        key=BUTTON_ACK_WARNING,
        translation_key=BUTTON_ACK_WARNING,
        icon="mdi:check-circle-outline",
        press_fn=lambda client: client.acknowledge_event(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Richtet alle Button-Entitäten ein.

    Args:
        hass: Die Home Assistant Instanz.
        entry: Der ConfigEntry der Integration.
        async_add_entities: Callback zum Registrieren neuer Entitäten.
    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: WatercrystDataUpdateCoordinator = data["coordinator"]
    client: WatercrystApiClient = data["client"]

    entities = [
        WatercrystButton(coordinator, client, description, entry)
        for description in BUTTON_DESCRIPTIONS
    ]

    async_add_entities(entities)
    _LOGGER.debug("%d Button-Entitäten erstellt", len(entities))


class WatercrystButton(
    CoordinatorEntity[WatercrystDataUpdateCoordinator],
    ButtonEntity,
):
    """
    Repräsentiert einen Button der Watercryst BIOCAT Integration.

    Buttons haben keinen Zustand – sie führen beim Drücken eine
    einmalige Aktion aus (z.B. Selbsttest starten, Warnung quittieren).
    """

    entity_description: WatercrystButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WatercrystDataUpdateCoordinator,
        client: WatercrystApiClient,
        description: WatercrystButtonDescription,
        entry: ConfigEntry,
    ) -> None:
        """
        Initialisiert den Button.

        Args:
            coordinator: Der DataUpdateCoordinator.
            client: Der API-Client für direkte Aufrufe.
            description: Die Button-Beschreibung.
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

    async def async_press(self) -> None:
        """
        Wird aufgerufen, wenn der Button in der HA-UI gedrückt wird.

        Führt die in der Beschreibung definierte Aktion aus und
        aktualisiert anschließend die Coordinator-Daten.
        """
        _LOGGER.debug("Button '%s' gedrückt", self.entity_description.key)
        try:
            await self.entity_description.press_fn(self._client)
            # Daten sofort aktualisieren, damit z.B. der Selftest-Status
            # schnell in der UI sichtbar wird
            await self.coordinator.async_request_refresh()
        except WatercrystApiError as err:
            _LOGGER.error(
                "Fehler beim Ausführen von '%s': %s",
                self.entity_description.key,
                err,
            )
