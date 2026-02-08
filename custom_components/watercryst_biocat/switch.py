"""Switch-Plattform für Watercryst BIOCAT.

Schalter für:
- Abwesenheitsmodus (PUT /v1/state/absenceMode)
- Leckageschutz (PUT /v1/state/leakageProtection)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Coroutine

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import WatercrystDataCoordinator
from .api import WatercrystApiClient
from .const import (
    CONF_DEVICE_NAME,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    SWITCH_ABSENCE_MODE,
    SWITCH_LEAKAGE_PROTECTION,
    URL_WATERCRYST,
)


@dataclass(frozen=True, kw_only=True)
class WatercrystSwitchDescription(SwitchEntityDescription):
    """Beschreibung eines Watercryst Switches."""

    value_fn: Callable[[dict[str, Any]], bool | None]
    turn_on_fn: Callable[[WatercrystApiClient], Coroutine]
    turn_off_fn: Callable[[WatercrystApiClient], Coroutine]


SWITCH_DESCRIPTIONS: list[WatercrystSwitchDescription] = [
    WatercrystSwitchDescription(
        key=SWITCH_ABSENCE_MODE,
        translation_key="absence_mode",
        icon="mdi:home-off-outline",
        value_fn=lambda data: data.get("absence_mode_enabled"),
        turn_on_fn=lambda client: client.async_set_absence_mode(True),
        turn_off_fn=lambda client: client.async_set_absence_mode(False),
    ),
    WatercrystSwitchDescription(
        key=SWITCH_LEAKAGE_PROTECTION,
        translation_key="leakage_protection",
        icon="mdi:shield-check",
        value_fn=lambda data: data.get("leakage_protection_enabled"),
        turn_on_fn=lambda client: client.async_set_leakage_protection(True),
        turn_off_fn=lambda client: client.async_set_leakage_protection(False),
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Switches einrichten."""
    coordinator: WatercrystDataCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        WatercrystSwitch(coordinator, description, entry)
        for description in SWITCH_DESCRIPTIONS
    )


class WatercrystSwitch(
    CoordinatorEntity[WatercrystDataCoordinator], SwitchEntity
):
    """Switch für Watercryst BIOCAT Steuerung."""

    entity_description: WatercrystSwitchDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: WatercrystDataCoordinator,
        description: WatercrystSwitchDescription,
        entry: ConfigEntry,
    ) -> None:
        """Switch initialisieren."""
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
        """Aktueller Schaltzustand."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Einschalten."""
        await self.entity_description.turn_on_fn(self.coordinator.client)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Ausschalten."""
        await self.entity_description.turn_off_fn(self.coordinator.client)
        await self.coordinator.async_request_refresh()
