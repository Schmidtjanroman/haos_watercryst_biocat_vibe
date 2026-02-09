"""Config Flow für die Watercryst BIOCAT Integration.

Der Benutzer gibt seinen API-Key ein, der unter
https://app.watercryst.com/Device/ erstellt wurde.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import WatercrystApiClient, WatercrystApiError, WatercrystAuthError
from .const import (
    CONF_API_KEY,
    CONF_DEVICE_NAME,
    CONF_POLL_INTERVAL,
    DEFAULT_DEVICE_NAME,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Optional(CONF_DEVICE_NAME, default=DEFAULT_DEVICE_NAME): str,
    }
)

STEP_REAUTH_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
    }
)


class WatercrystBiocatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config Flow für Watercryst BIOCAT."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Schritt 1: API-Key Eingabe."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            device_name = user_input.get(CONF_DEVICE_NAME, DEFAULT_DEVICE_NAME)

            await self.async_set_unique_id(api_key[:8])
            self._abort_if_unique_id_configured()

            try:
                session = async_get_clientsession(self.hass)
                client = WatercrystApiClient(session=session, api_key=api_key)
                valid = await client.async_validate_api_key()

                if valid:
                    return self.async_create_entry(
                        title=f"BIOCAT {device_name}",
                        data={
                            CONF_API_KEY: api_key,
                            CONF_DEVICE_NAME: device_name,
                        },
                        options={
                            CONF_POLL_INTERVAL: DEFAULT_POLL_INTERVAL,
                        },
                    )
                errors["base"] = "invalid_auth"

            except WatercrystAuthError:
                errors["base"] = "invalid_auth"
            except WatercrystApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unerwarteter Fehler im Config Flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "api_key_url": "https://app.watercryst.com/Device/",
            },
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> FlowResult:
        """Re-Authentifizierung starten."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Re-Authentifizierung: Neuen API-Key eingeben."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()

            try:
                session = async_get_clientsession(self.hass)
                client = WatercrystApiClient(session=session, api_key=api_key)
                valid = await client.async_validate_api_key()

                if valid:
                    reauth_entry = self._get_reauth_entry()
                    return self.async_update_reload_and_abort(
                        reauth_entry,
                        data={**reauth_entry.data, CONF_API_KEY: api_key},
                    )
                errors["base"] = "invalid_auth"

            except WatercrystAuthError:
                errors["base"] = "invalid_auth"
            except WatercrystApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unerwarteter Fehler bei Re-Auth")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "api_key_url": "https://app.watercryst.com/Device/",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> WatercrystOptionsFlow:
        """Options Flow zurückgeben."""
        return WatercrystOptionsFlow(config_entry)


class WatercrystOptionsFlow(OptionsFlow):
    """Options Flow – Abfrage-Intervall anpassen."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialisierung."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Optionen anzeigen."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=current_interval,
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=300)),
                }
            ),
        )
