"""
Config Flow für die Watercryst BIOCAT Integration.

Dieser Config Flow ermöglicht die Einrichtung der Integration über die
Home Assistant Benutzeroberfläche. Der Benutzer gibt Benutzername und
Passwort ein; die Credentials werden validiert, bevor sie gespeichert werden.

Alle Texte (Labels, Beschreibungen, Fehlermeldungen) werden aus den
Translation-Dateien (translations/en.json, translations/de.json) geladen.
Im Python-Code gibt es KEINE hartcodierten Strings für die Benutzeroberfläche.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    WatercrystApiClient,
    WatercrystAuthError,
    WatercrystConnectionError,
)
from .const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_DEVICE_ID,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Schema für das Anmeldeformular
# Die Labels werden automatisch aus den Translation-Dateien geladen,
# basierend auf den Schlüsselnamen (username, password).
USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class WatercrystBiocatConfigFlow(ConfigFlow, domain=DOMAIN):
    """
    Config Flow Handler für die Watercryst BIOCAT Integration.

    Implementiert den Einrichtungsassistenten in der HA-Oberfläche:
    1. Benutzer gibt Credentials ein
    2. Credentials werden gegen die API validiert
    3. Bei Erfolg wird ein ConfigEntry erstellt und gespeichert
    """

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """
        Erster Schritt: Benutzername und Passwort abfragen.

        Dieser Schritt wird angezeigt, wenn der Benutzer die Integration
        über die UI hinzufügt. Er zeigt ein Formular mit den Feldern
        für Benutzername und Passwort.

        Args:
            user_input: None beim ersten Aufruf, danach die eingegebenen Daten.

        Returns:
            ConfigFlowResult: Entweder das Formular (mit Fehlern) oder
                            den erstellten ConfigEntry.
        """
        # Fehlermeldungen für die Anzeige im Formular
        errors: dict[str, str] = {}

        if user_input is not None:
            # Benutzer hat das Formular abgeschickt – Credentials validieren
            _LOGGER.debug(
                "Validiere Anmeldedaten für Benutzer: %s",
                user_input[CONF_USERNAME],
            )

            try:
                # API-Client mit den eingegebenen Daten erstellen
                session = async_get_clientsession(self.hass)
                client = WatercrystApiClient(
                    session=session,
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )

                # Authentifizierung testen
                await client.authenticate()

                # Geräteliste abrufen um die Geräte-ID zu erhalten
                devices = await client.get_devices()
                device_id = devices[0]["id"] if devices else None

            except WatercrystAuthError:
                # Falsche Anmeldedaten → Fehlermeldung im Formular anzeigen
                # Der Schlüssel "invalid_auth" wird in der Translation-Datei
                # aufgelöst, z.B. "Ungültiger Benutzername oder Passwort"
                errors["base"] = "invalid_auth"
                _LOGGER.warning("Ungültige Anmeldedaten eingegeben")

            except WatercrystConnectionError:
                # API nicht erreichbar → Verbindungsfehler anzeigen
                errors["base"] = "cannot_connect"
                _LOGGER.error("Watercryst-API nicht erreichbar")

            except Exception:
                # Unerwarteter Fehler → generische Meldung
                errors["base"] = "unknown"
                _LOGGER.exception("Unerwarteter Fehler beim Setup der Watercryst-Integration")

            else:
                # Keine Fehler → Sicherstellen, dass kein Duplikat existiert
                # Eindeutigkeits-ID basierend auf dem Benutzernamen
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()

                # ConfigEntry erstellen und Credentials sicher speichern
                # Home Assistant verschlüsselt die Daten automatisch
                entry_data = {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                }
                if device_id:
                    entry_data[CONF_DEVICE_ID] = device_id

                return self.async_create_entry(
                    title=f"BIOCAT ({user_input[CONF_USERNAME]})",
                    data=entry_data,
                )

        # Formular anzeigen (beim ersten Aufruf oder nach Fehler)
        # Die Beschreibung mit dem Produktbild wird über die Translation-Datei
        # eingebunden (description_placeholders)
        return self.async_show_form(
            step_id="user",
            data_schema=USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "device_image": (
                    "https://assets.heizung-billiger.de/images/watercryst/"
                    "large_default/large_default-12000273_B_.jpg@webp"
                ),
            },
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> ConfigFlowResult:
        """
        Re-Authentifizierung, wenn die gespeicherten Credentials ungültig werden.

        Wird automatisch von Home Assistant aufgerufen, wenn der Coordinator
        einen ConfigEntryAuthFailed-Fehler meldet.

        Args:
            entry_data: Die bisherigen Konfigurationsdaten.

        Returns:
            ConfigFlowResult: Weiterleitung zum Credential-Formular.
        """
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """
        Bestätigungsschritt für die Re-Authentifizierung.

        Zeigt das gleiche Formular wie der initiale Setup-Schritt,
        damit der Benutzer neue Credentials eingeben kann.

        Args:
            user_input: Die neu eingegebenen Credentials.

        Returns:
            ConfigFlowResult: Formular oder aktualisierter ConfigEntry.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                session = async_get_clientsession(self.hass)
                client = WatercrystApiClient(
                    session=session,
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                )
                await client.authenticate()

            except WatercrystAuthError:
                errors["base"] = "invalid_auth"
            except WatercrystConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
                _LOGGER.exception("Unerwarteter Fehler bei der Re-Authentifizierung")
            else:
                # Bestehenden ConfigEntry mit neuen Credentials aktualisieren
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=USER_DATA_SCHEMA,
            errors=errors,
        )
