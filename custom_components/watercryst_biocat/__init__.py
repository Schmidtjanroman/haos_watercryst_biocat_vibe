"""
Watercryst BIOCAT Integration für Home Assistant.

Diese Datei ist der Einstiegspunkt der Integration. Sie wird beim Laden
der Integration aufgerufen und koordiniert:
- Die Initialisierung des API-Clients
- Den DataUpdateCoordinator (periodisches Polling)
- Das Laden/Entladen der Plattformen (sensor, switch, button, binary_sensor)

Der DataUpdateCoordinator sorgt dafür, dass alle Entitäten die gleichen
Daten nutzen und die API nicht für jeden Sensor einzeln abgefragt wird.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    WatercrystApiClient,
    WatercrystAuthError,
    WatercrystConnectionError,
    WatercrystApiError,
)
from .const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_DEVICE_ID,
    DOMAIN,
    PLATFORMS,
    UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Typalias für den Coordinator, um ihn in anderen Dateien einfach referenzieren zu können
type WatercrystConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: WatercrystConfigEntry) -> bool:
    """
    Richtet die Integration basierend auf einem ConfigEntry ein.

    Wird aufgerufen, nachdem der Config Flow erfolgreich abgeschlossen wurde.
    Erstellt den API-Client, authentifiziert sich und startet den Coordinator.

    Args:
        hass: Die Home Assistant Instanz.
        entry: Der ConfigEntry mit den gespeicherten Anmeldedaten.

    Returns:
        True bei erfolgreicher Einrichtung.

    Raises:
        ConfigEntryAuthFailed: Bei ungültigen Credentials (Benutzer wird informiert).
        ConfigEntryNotReady: Bei vorübergehenden Verbindungsproblemen (HA versucht es erneut).
    """
    # aiohttp-Session von Home Assistant holen (wird zentral verwaltet)
    session = async_get_clientsession(hass)

    # API-Client mit den gespeicherten Credentials erstellen
    client = WatercrystApiClient(
        session=session,
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
    )

    # Authentifizierung durchführen
    try:
        await client.authenticate()
    except WatercrystAuthError as err:
        # Ungültige Credentials → Benutzer muss sich erneut einrichten
        raise ConfigEntryAuthFailed(
            "Ungültige Anmeldedaten für die Watercryst-API"
        ) from err
    except WatercrystConnectionError as err:
        # Netzwerkfehler → Home Assistant versucht es später erneut
        raise ConfigEntryNotReady(
            "Verbindung zur Watercryst-API nicht möglich"
        ) from err

    # Geräte-ID aus der Konfiguration oder von der API holen
    if CONF_DEVICE_ID in entry.data:
        client.device_id = entry.data[CONF_DEVICE_ID]
    else:
        # Geräteliste von der API abrufen und erste Geräte-ID verwenden
        try:
            devices = await client.get_devices()
            if not devices:
                raise ConfigEntryNotReady("Keine Geräte im Watercryst-Konto gefunden")
        except WatercrystApiError as err:
            raise ConfigEntryNotReady(
                "Fehler beim Abrufen der Geräteliste"
            ) from err

    # DataUpdateCoordinator erstellen – er ruft periodisch alle Daten ab
    coordinator = WatercrystDataUpdateCoordinator(hass, client)

    # Erste Datenabfrage durchführen (muss vor dem Plattform-Setup erfolgen)
    await coordinator.async_config_entry_first_refresh()

    # Client und Coordinator im hass.data-Store ablegen, damit alle
    # Plattformen (sensor.py, switch.py etc.) darauf zugreifen können
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
    }

    # Plattformen laden (sensor, binary_sensor, switch, button)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _LOGGER.info("Watercryst BIOCAT Integration erfolgreich eingerichtet")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Entlädt die Integration und gibt Ressourcen frei.

    Wird aufgerufen, wenn der Benutzer die Integration entfernt
    oder Home Assistant herunterfährt.

    Args:
        hass: Die Home Assistant Instanz.
        entry: Der zu entladende ConfigEntry.

    Returns:
        True wenn alle Plattformen erfolgreich entladen wurden.
    """
    # Alle Plattformen entladen
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Daten aus dem Store entfernen
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN, None)
        _LOGGER.info("Watercryst BIOCAT Integration erfolgreich entladen")

    return unload_ok


class WatercrystDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """
    Koordiniert die periodische Datenabfrage bei der Watercryst-API.

    Der Coordinator ruft in einem konfigurierbaren Intervall (Standard: 60s)
    alle Daten von der API ab und verteilt sie an die Entitäten. So wird
    die API nur einmal pro Intervall abgefragt, egal wie viele Sensoren
    konfiguriert sind.

    Bei Authentifizierungsfehlern wird ein ConfigEntryAuthFailed ausgelöst,
    was Home Assistant dazu veranlasst, den Benutzer zur erneuten
    Einrichtung aufzufordern.
    """

    def __init__(self, hass: HomeAssistant, client: WatercrystApiClient) -> None:
        """
        Initialisiert den Coordinator.

        Args:
            hass: Die Home Assistant Instanz.
            client: Der Watercryst API-Client.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """
        Wird periodisch aufgerufen, um alle Daten von der API abzurufen.

        Diese Methode ist der Kern des Coordinators. Sie ruft die
        gebündelte API-Methode auf und gibt die Daten als Dict zurück.

        Returns:
            Dict mit allen gesammelten API-Daten.

        Raises:
            ConfigEntryAuthFailed: Bei Authentifizierungsfehlern.
            UpdateFailed: Bei sonstigen Fehlern.
        """
        try:
            data = await self.client.get_all_data()
            _LOGGER.debug("Daten erfolgreich von der Watercryst-API abgerufen")
            return data

        except WatercrystAuthError as err:
            # Authentifizierungsfehler → Benutzer muss Credentials prüfen
            raise ConfigEntryAuthFailed(
                "Authentifizierung bei der Watercryst-API fehlgeschlagen"
            ) from err

        except WatercrystConnectionError as err:
            # Verbindungsfehler → wird beim nächsten Intervall erneut versucht
            raise UpdateFailed(
                f"Verbindung zur Watercryst-API fehlgeschlagen: {err}"
            ) from err

        except WatercrystApiError as err:
            # Sonstige API-Fehler
            raise UpdateFailed(
                f"Fehler beim Abrufen der Watercryst-Daten: {err}"
            ) from err
