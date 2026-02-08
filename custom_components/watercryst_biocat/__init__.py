"""Watercryst BIOCAT Integration für Home Assistant.

Ermöglicht die Überwachung und Steuerung von Watercryst BIOCAT
Wasseraufbereitungsgeräten über die offizielle REST-API.

API-Dokumentation: https://appapi.watercryst.com/api-v1.yaml
API-Key Verwaltung: https://app.watercryst.com/Device/
"""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WatercrystApiClient, WatercrystApiError, WatercrystAuthError
from .const import (
    CONF_API_KEY,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

type WatercrystConfigEntry = ConfigEntry


async def async_setup_entry(
    hass: HomeAssistant, entry: WatercrystConfigEntry
) -> bool:
    """Integration über Config Entry einrichten.

    Erstellt den API-Client und DataUpdateCoordinator,
    führt den ersten Daten-Abruf durch und richtet alle
    Entitäts-Plattformen ein.
    """
    # API-Client erstellen
    session = async_get_clientsession(hass)
    api_key = entry.data[CONF_API_KEY]
    client = WatercrystApiClient(session=session, api_key=api_key)

    # API-Key Validierung
    try:
        valid = await client.async_validate_api_key()
        if not valid:
            raise ConfigEntryAuthFailed(
                "API-Key ungültig. Bitte unter "
                "https://app.watercryst.com/Device/ prüfen."
            )
    except WatercrystAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err
    except WatercrystApiError as err:
        raise ConfigEntryNotReady(
            f"Verbindung zur Watercryst API fehlgeschlagen: {err}"
        ) from err

    # Poll-Intervall aus Optionen oder Default
    poll_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)

    # DataUpdateCoordinator erstellen
    coordinator = WatercrystDataCoordinator(
        hass=hass,
        client=client,
        update_interval=timedelta(seconds=poll_interval),
        entry=entry,
    )

    # Erster Daten-Abruf
    await coordinator.async_config_entry_first_refresh()

    # Im hass.data speichern
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Plattformen einrichten
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Options-Update Listener registrieren
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: WatercrystConfigEntry
) -> bool:
    """Integration entladen."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_update_options(
    hass: HomeAssistant, entry: WatercrystConfigEntry
) -> None:
    """Optionen wurden geändert – Integration neu laden."""
    await hass.config_entries.async_reload(entry.entry_id)


class WatercrystDataCoordinator(DataUpdateCoordinator):
    """Koordinator für die zentrale Datenabfrage.

    Fragt alle API-Endpunkte in einem Zyklus ab und stellt
    die kombinierten Daten allen Entitäten bereit.
    Zwischen den einzelnen API-Aufrufen wird automatisch
    eine Pause eingehalten (siehe api.py API_REQUEST_DELAY).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        client: WatercrystApiClient,
        update_interval: timedelta,
        entry: ConfigEntry,
    ) -> None:
        """Koordinator initialisieren."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=update_interval,
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> dict:
        """Alle Daten von der API abrufen.

        Raises:
            ConfigEntryAuthFailed: Bei ungültigem API-Key
            UpdateFailed: Bei sonstigen API-Fehlern
        """
        try:
            data = await self.client.async_get_all_data()
            _LOGGER.debug("Daten empfangen: %s", list(data.keys()))
            return data

        except WatercrystAuthError as err:
            # Triggert Re-Auth Flow in der HA UI
            raise ConfigEntryAuthFailed(
                "API-Key ungültig. Bitte unter "
                "https://app.watercryst.com/Device/ prüfen."
            ) from err

        except WatercrystApiError as err:
            raise UpdateFailed(f"API-Fehler: {err}") from err
