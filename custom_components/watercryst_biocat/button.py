"""Button-Plattform für Watercryst BIOCAT.

Buttons für:
- Selbsttest starten (POST /v1/selftest)
- Warnung quittieren (POST /v1/state/acknowledge)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Coroutine

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatercrystDataCoordinator
from .api import WatercrystApiClient
from .const import (
    BUTTON_ACKNOWLEDGE,
    BUTTON_SELFTEST,
    CONF_DEVICE_NAME,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    URL_WATERCRYST,
)


@dataclass(frozen=True, kw_only=True)
class WatercrystButtonDescription(ButtonEntityDescription):
    """Beschreibung eines Watercryst Buttons."""

    press_fn: Callable[[WatercrystApiClient], Coroutine]


BUTTON_DESCRIPTIONS: list[WatercrystButtonDescription] = [
    WatercrystButtonDescription(
        key=BUTTON_SELFTEST,
        translation_key="start_selftest",
        icon="mdi:test-tube",
        press_fn=lambda client: client.async_start_selftest(),
    ),
    WatercrystButtonDescription(
        key=BUTTON_ACKNOWLEDGE,
        translation_key="acknowledge_warning",
        icon="mdi:check-circle-outline",
        press_fn=lambda client: client.async_acknowledge_warning(),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Buttons einrichten."""
    coordinator: WatercrystDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        WatercrystButton(coordinator, description, entry)
        for description in BUTTON_DESCRIPTIONS
    )


class WatercrystButton(
    CoordinatorEntity[WatercrystDataCoordinator], ButtonEntity
):
    """Button für Watercryst BIOCAT Aktionen."""

    entity_description: WatercrystButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WatercrystDataCoordinator,
        description: WatercrystButtonDescription,
        entry: ConfigEntry,
    ) -> None:
        """Button initialisieren."""
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

    async def async_press(self) -> None:
        """Button gedrückt."""
        await self.entity_description.press_fn(self.coordinator.client)
        await self.coordinator.async_request_refresh()
