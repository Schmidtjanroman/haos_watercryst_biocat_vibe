"""
Asynchroner API-Client für die Watercryst BIOCAT Cloud-API.

Dieser Client kapselt die gesamte Kommunikation mit der Watercryst-API.
Er verwaltet die Authentifizierung (Login + Token-Refresh) und bietet
Methoden für jeden API-Endpunkt. Alle Aufrufe sind vollständig asynchron
(aiohttp), um den Home Assistant Event Loop nicht zu blockieren.

Da kein Live-Zugriff auf die API besteht, sind die Endpunkte basierend
auf REST-Standards simuliert. Die Datenstrukturen orientieren sich an
typischen IoT-Geräte-APIs.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import async_timeout

from .const import (
    API_BASE_URL,
    ENDPOINT_ABSENCE,
    ENDPOINT_ACK_EVENT,
    ENDPOINT_DEVICES,
    ENDPOINT_LEAKAGE_PROTECTION,
    ENDPOINT_LOGIN,
    ENDPOINT_MEASUREMENTS,
    ENDPOINT_ML_MEASUREMENT,
    ENDPOINT_REFRESH,
    ENDPOINT_SELFTEST,
    ENDPOINT_STATE,
    ENDPOINT_STATISTICS,
    ENDPOINT_WATER_SUPPLY,
    ENDPOINT_WEBHOOKS,
)

_LOGGER = logging.getLogger(__name__)

# Timeout für einzelne API-Aufrufe (in Sekunden)
REQUEST_TIMEOUT: int = 15


class WatercrystApiError(Exception):
    """Allgemeiner Fehler bei der Kommunikation mit der Watercryst-API."""


class WatercrystAuthError(WatercrystApiError):
    """Fehler bei der Authentifizierung (ungültige Credentials oder abgelaufener Token)."""


class WatercrystConnectionError(WatercrystApiError):
    """Netzwerk- oder Verbindungsfehler zur API."""


class WatercrystApiClient:
    """
    Asynchroner Client für die Watercryst BIOCAT Cloud-API.

    Verwaltet Authentifizierung, Token-Refresh und bietet Methoden
    für alle relevanten API-Endpunkte.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> None:
        """
        Initialisiert den API-Client.

        Args:
            session: Die aiohttp-Session (wird von Home Assistant bereitgestellt).
            username: Benutzername für die Watercryst-API.
            password: Passwort für die Watercryst-API.
        """
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._device_id: str | None = None
        self._base_url = API_BASE_URL

    # ========================================================================
    # Authentifizierung
    # ========================================================================

    async def authenticate(self) -> bool:
        """
        Führt den Login bei der Watercryst-API durch.

        Sendet Benutzername und Passwort an den Login-Endpunkt
        und speichert die erhaltenen Tokens.

        Returns:
            True bei erfolgreichem Login.

        Raises:
            WatercrystAuthError: Bei ungültigen Credentials.
            WatercrystConnectionError: Bei Netzwerkfehlern.
        """
        _LOGGER.debug("Starte Authentifizierung bei der Watercryst-API")

        payload = {
            "username": self._username,
            "password": self._password,
        }

        try:
            data = await self._request("POST", ENDPOINT_LOGIN, json_data=payload, auth_required=False)
        except WatercrystApiError as err:
            _LOGGER.error("Authentifizierung fehlgeschlagen: %s", err)
            raise WatercrystAuthError("Authentifizierung fehlgeschlagen") from err

        # Tokens aus der API-Antwort extrahieren
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")

        if not self._access_token:
            raise WatercrystAuthError("Kein Access-Token in der API-Antwort erhalten")

        _LOGGER.info("Authentifizierung bei der Watercryst-API erfolgreich")
        return True

    async def refresh_access_token(self) -> bool:
        """
        Erneuert den Access-Token über den Refresh-Token.

        Returns:
            True bei erfolgreichem Refresh.

        Raises:
            WatercrystAuthError: Wenn der Refresh fehlschlägt.
        """
        if not self._refresh_token:
            _LOGGER.warning("Kein Refresh-Token vorhanden, führe erneuten Login durch")
            return await self.authenticate()

        _LOGGER.debug("Erneuere Access-Token über Refresh-Endpunkt")

        payload = {"refresh_token": self._refresh_token}

        try:
            data = await self._request("POST", ENDPOINT_REFRESH, json_data=payload, auth_required=False)
            self._access_token = data.get("access_token")
            self._refresh_token = data.get("refresh_token", self._refresh_token)
            _LOGGER.debug("Access-Token erfolgreich erneuert")
            return True
        except WatercrystApiError:
            _LOGGER.warning("Token-Refresh fehlgeschlagen, versuche erneuten Login")
            return await self.authenticate()

    # ========================================================================
    # Geräte-Endpunkt
    # ========================================================================

    async def get_devices(self) -> list[dict[str, Any]]:
        """
        Ruft die Liste der registrierten Geräte ab.

        Returns:
            Liste von Geräte-Dictionarys mit ID, Name, Modell etc.
        """
        data = await self._request("GET", ENDPOINT_DEVICES)
        devices = data.get("devices", [])
        if devices and not self._device_id:
            # Erstes Gerät als Standard-Gerät setzen
            self._device_id = devices[0].get("id")
            _LOGGER.debug("Standard-Gerät gesetzt: %s", self._device_id)
        return devices

    @property
    def device_id(self) -> str | None:
        """Gibt die aktuelle Geräte-ID zurück."""
        return self._device_id

    @device_id.setter
    def device_id(self, value: str) -> None:
        """Setzt die Geräte-ID manuell."""
        self._device_id = value

    # ========================================================================
    # Status & Warnungen
    # ========================================================================

    async def get_state(self) -> dict[str, Any]:
        """
        Ruft den aktuellen Gerätezustand ab (Fehler, Warnungen, Status).

        Returns:
            Dict mit Statusfeldern wie 'state', 'error', 'warning', 'error_message'.
        """
        return await self._request("GET", f"{ENDPOINT_STATE}/{self._device_id}")

    async def acknowledge_event(self, event_id: str | None = None) -> dict[str, Any]:
        """
        Bestätigt (quittiert) eine Warnung oder einen Fehler.

        Args:
            event_id: Optionale ID des spezifischen Events. Ohne ID werden alle quittiert.

        Returns:
            API-Antwort nach der Bestätigung.
        """
        payload: dict[str, Any] = {"device_id": self._device_id}
        if event_id:
            payload["event_id"] = event_id
        return await self._request("POST", ENDPOINT_ACK_EVENT, json_data=payload)

    # ========================================================================
    # Abwesenheitsmodus
    # ========================================================================

    async def get_absence(self) -> dict[str, Any]:
        """
        Ruft den aktuellen Abwesenheitsstatus ab.

        Returns:
            Dict mit 'active' (bool) und ggf. Zeitstempel.
        """
        return await self._request("GET", f"{ENDPOINT_ABSENCE}/{self._device_id}")

    async def set_absence(self, active: bool) -> dict[str, Any]:
        """
        Setzt den Abwesenheitsmodus.

        Args:
            active: True = Abwesend, False = Anwesend.

        Returns:
            API-Antwort mit dem neuen Status.
        """
        payload = {"device_id": self._device_id, "active": active}
        return await self._request("POST", ENDPOINT_ABSENCE, json_data=payload)

    # ========================================================================
    # Leckageschutz
    # ========================================================================

    async def get_leakage_protection(self) -> dict[str, Any]:
        """
        Ruft den Status des Leckageschutzes ab.

        Returns:
            Dict mit 'enabled' (bool), 'sensitivity', 'last_run' etc.
        """
        return await self._request("GET", f"{ENDPOINT_LEAKAGE_PROTECTION}/{self._device_id}")

    async def set_leakage_protection(self, enabled: bool) -> dict[str, Any]:
        """
        Aktiviert oder deaktiviert den Leckageschutz.

        Args:
            enabled: True = Schutz aktiv, False = Schutz deaktiviert.

        Returns:
            API-Antwort mit dem neuen Status.
        """
        payload = {"device_id": self._device_id, "enabled": enabled}
        return await self._request("POST", ENDPOINT_LEAKAGE_PROTECTION, json_data=payload)

    async def get_ml_measurement(self) -> dict[str, Any]:
        """
        Ruft die ML-Messwerte (Machine Learning basierte Leckageerkennung) ab.

        Returns:
            Dict mit ML-Analysedaten und Schwellwerten.
        """
        return await self._request("GET", f"{ENDPOINT_ML_MEASUREMENT}/{self._device_id}")

    # ========================================================================
    # Messwerte
    # ========================================================================

    async def get_measurements(self) -> dict[str, Any]:
        """
        Ruft aktuelle Messwerte ab (Druck, Temperatur, Durchfluss etc.).

        Returns:
            Dict mit aktuellen Sensorwerten.
        """
        return await self._request("GET", f"{ENDPOINT_MEASUREMENTS}/{self._device_id}")

    # ========================================================================
    # Selbsttest
    # ========================================================================

    async def get_selftest(self) -> dict[str, Any]:
        """
        Ruft das Ergebnis des letzten Selbsttests ab.

        Returns:
            Dict mit 'result', 'last_run', 'details'.
        """
        return await self._request("GET", f"{ENDPOINT_SELFTEST}/{self._device_id}")

    async def start_selftest(self) -> dict[str, Any]:
        """
        Startet einen Selbsttest des Gerätes.

        Returns:
            API-Antwort mit Bestätigung und ggf. geschätzter Dauer.
        """
        payload = {"device_id": self._device_id}
        return await self._request("POST", ENDPOINT_SELFTEST, json_data=payload)

    # ========================================================================
    # Wasserversorgung
    # ========================================================================

    async def get_water_supply(self) -> dict[str, Any]:
        """
        Ruft Daten zur Wasserversorgung ab (Verbrauch, Parameter).

        Returns:
            Dict mit Verbrauchsdaten und konfigurierbaren Parametern.
        """
        return await self._request("GET", f"{ENDPOINT_WATER_SUPPLY}/{self._device_id}")

    async def set_water_supply_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Setzt Parameter der Wasserversorgung.

        Args:
            params: Dict mit zu ändernden Parametern.

        Returns:
            API-Antwort mit den aktualisierten Parametern.
        """
        payload = {"device_id": self._device_id, **params}
        return await self._request("POST", ENDPOINT_WATER_SUPPLY, json_data=payload)

    # ========================================================================
    # Statistiken
    # ========================================================================

    async def get_statistics(self) -> dict[str, Any]:
        """
        Ruft die Gerätestatistiken ab (wöchentlich, monatlich etc.).

        Returns:
            Dict mit verschiedenen Statistik-Datenpunkten.
        """
        return await self._request("GET", f"{ENDPOINT_STATISTICS}/{self._device_id}")

    # ========================================================================
    # Webhooks
    # ========================================================================

    async def get_webhooks(self) -> dict[str, Any]:
        """
        Ruft die aktuelle Webhook-Konfiguration ab.

        Returns:
            Dict mit registrierten Webhook-URLs und Events.
        """
        return await self._request("GET", f"{ENDPOINT_WEBHOOKS}/{self._device_id}")

    async def register_webhook(self, webhook_url: str) -> dict[str, Any]:
        """
        Registriert eine Webhook-URL für Push-Benachrichtigungen.

        Args:
            webhook_url: Die URL, an die Events gesendet werden sollen.

        Returns:
            API-Antwort mit der Webhook-Registrierung.
        """
        payload = {
            "device_id": self._device_id,
            "url": webhook_url,
            "events": ["state_change", "warning", "error", "leakage"],
        }
        return await self._request("POST", ENDPOINT_WEBHOOKS, json_data=payload)

    # ========================================================================
    # Alle Daten auf einmal abrufen (für den Coordinator)
    # ========================================================================

    async def get_all_data(self) -> dict[str, Any]:
        """
        Ruft alle relevanten Daten in einem Durchgang ab.

        Diese Methode wird vom DataUpdateCoordinator aufgerufen und
        bündelt alle API-Aufrufe. Einzelne Fehler werden abgefangen,
        damit ein fehlgeschlagener Endpunkt nicht die gesamte
        Aktualisierung blockiert.

        Returns:
            Dict mit allen gesammelten Daten, gruppiert nach Kategorie.
        """
        result: dict[str, Any] = {}

        # Jeder Endpunkt wird einzeln abgefragt; bei Fehlern wird ein
        # leeres Dict eingesetzt und der Fehler geloggt.
        endpoints = {
            "state": self.get_state,
            "measurements": self.get_measurements,
            "absence": self.get_absence,
            "leakage_protection": self.get_leakage_protection,
            "selftest": self.get_selftest,
            "water_supply": self.get_water_supply,
            "statistics": self.get_statistics,
        }

        for key, method in endpoints.items():
            try:
                result[key] = await method()
            except WatercrystApiError as err:
                _LOGGER.warning(
                    "Fehler beim Abruf von '%s': %s – verwende leere Daten",
                    key,
                    err,
                )
                result[key] = {}

        return result

    # ========================================================================
    # Interner HTTP-Request-Handler
    # ========================================================================

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        auth_required: bool = True,
    ) -> dict[str, Any]:
        """
        Führt einen HTTP-Request gegen die Watercryst-API durch.

        Behandelt automatisch:
        - Timeout (15 Sekunden)
        - 401-Fehler → automatischer Token-Refresh + Retry
        - Netzwerkfehler → WatercrystConnectionError

        Args:
            method: HTTP-Methode (GET, POST, PUT, DELETE).
            endpoint: Relativer API-Pfad.
            json_data: Optionaler JSON-Body.
            auth_required: Ob der Authorization-Header gesetzt werden soll.

        Returns:
            Die geparste JSON-Antwort als Dict.

        Raises:
            WatercrystAuthError: Bei 401/403-Fehlern nach Retry.
            WatercrystConnectionError: Bei Netzwerkproblemen.
            WatercrystApiError: Bei sonstigen API-Fehlern.
        """
        url = f"{self._base_url}{endpoint}"

        # Header mit Bearer-Token aufbauen
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if auth_required and self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        _LOGGER.debug("API-Request: %s %s", method, url)

        try:
            async with async_timeout.timeout(REQUEST_TIMEOUT):
                response = await self._session.request(
                    method,
                    url,
                    json=json_data,
                    headers=headers,
                )

            # Bei 401 (Unauthorized): Token erneuern und erneut versuchen
            if response.status == 401 and auth_required:
                _LOGGER.debug("401 erhalten – versuche Token-Refresh")
                await self.refresh_access_token()

                # Retry mit neuem Token
                headers["Authorization"] = f"Bearer {self._access_token}"
                async with async_timeout.timeout(REQUEST_TIMEOUT):
                    response = await self._session.request(
                        method,
                        url,
                        json=json_data,
                        headers=headers,
                    )

            # HTTP-Statuscodes auswerten
            if response.status in (401, 403):
                raise WatercrystAuthError(
                    f"Authentifizierung fehlgeschlagen (HTTP {response.status})"
                )

            if response.status >= 400:
                error_text = await response.text()
                raise WatercrystApiError(
                    f"API-Fehler: HTTP {response.status} – {error_text}"
                )

            # Erfolgreiche Antwort als JSON parsen
            return await response.json()

        except aiohttp.ClientConnectionError as err:
            raise WatercrystConnectionError(
                f"Verbindung zur Watercryst-API fehlgeschlagen: {err}"
            ) from err
        except TimeoutError as err:
            raise WatercrystConnectionError(
                f"Timeout bei der Verbindung zur Watercryst-API"
            ) from err
