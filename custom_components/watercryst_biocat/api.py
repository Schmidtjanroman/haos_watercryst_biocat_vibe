"""API-Client für die Watercryst BIOCAT REST-API.

Authentifizierung: X-API-KEY Header
Basis-URL: https://appapi.watercryst.com
Dokumentation: https://appapi.watercryst.com/api-v1.yaml

Wichtig: Die API verträgt keine gleichzeitigen Requests.
Zwischen Abfragen sollten mindestens 2-3 Sekunden liegen.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    API_BASE_URL,
    API_HEADER_KEY,
    ENDPOINT_ABSENCE_MODE,
    ENDPOINT_ACKNOWLEDGE_WARNING,
    ENDPOINT_LEAKAGE_PROTECTION,
    ENDPOINT_MEASUREMENTS,
    ENDPOINT_SELFTEST,
    ENDPOINT_STATE,
    ENDPOINT_STATISTICS_DAILY,
    ENDPOINT_STATISTICS_MONTHLY,
    ENDPOINT_STATISTICS_WEEKLY,
    ENDPOINT_WATER_SUPPLY,
)

_LOGGER = logging.getLogger(__name__)

# Minimale Pause zwischen API-Aufrufen (Sekunden)
# Verhindert DoS / 429-Fehler bei der Watercryst API
API_REQUEST_DELAY = 2.0


class WatercrystApiError(Exception):
    """Allgemeiner API-Fehler."""


class WatercrystAuthError(WatercrystApiError):
    """Authentifizierungs-Fehler (ungültiger API-Key)."""


class WatercrystConnectionError(WatercrystApiError):
    """Verbindungs-Fehler."""


class WatercrystApiClient:
    """Client für die Watercryst BIOCAT REST-API.

    Authentifizierung erfolgt über den X-API-KEY Header.
    API-Keys werden unter https://app.watercryst.com/Device/ verwaltet.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str,
        base_url: str = API_BASE_URL,
    ) -> None:
        """Initialisierung des API-Clients.

        Args:
            session: aiohttp ClientSession für HTTP-Requests
            api_key: Der X-API-KEY von app.watercryst.com/Device/
            base_url: Basis-URL der API (Standard: https://appapi.watercryst.com)
        """
        self._session = session
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._last_request_time: float = 0
        self._request_lock = asyncio.Lock()

    @property
    def _headers(self) -> dict[str, str]:
        """Standard-Header für alle API-Requests."""
        return {
            API_HEADER_KEY: self._api_key,
            "Accept": "application/json",
        }

    async def _throttled_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> aiohttp.ClientResponse:
        """Führt einen API-Request mit Rate-Limiting durch.

        Stellt sicher, dass zwischen Requests mindestens API_REQUEST_DELAY
        Sekunden vergehen. Dies verhindert HTTP 429 Fehler.
        """
        async with self._request_lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request_time
            if elapsed < API_REQUEST_DELAY:
                await asyncio.sleep(API_REQUEST_DELAY - elapsed)

            url = f"{self._base_url}{endpoint}"
            _LOGGER.debug("API %s Request: %s", method.upper(), url)

            try:
                response = await self._session.request(
                    method,
                    url,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                    **kwargs,
                )
                self._last_request_time = asyncio.get_event_loop().time()
                return response

            except asyncio.TimeoutError as err:
                raise WatercrystConnectionError(
                    f"Timeout bei Anfrage an {url}"
                ) from err
            except aiohttp.ClientError as err:
                raise WatercrystConnectionError(
                    f"Verbindungsfehler bei {url}: {err}"
                ) from err

    async def _get(self, endpoint: str) -> Any:
        """GET-Request an die API.

        Returns:
            JSON-Response als Python-Objekt (dict, list, int, float)

        Raises:
            WatercrystAuthError: Bei ungültigem API-Key (HTTP 401/403)
            WatercrystApiError: Bei sonstigen HTTP-Fehlern
        """
        response = await self._throttled_request("get", endpoint)

        if response.status in (401, 403):
            raise WatercrystAuthError(
                "Ungültiger API-Key. Bitte unter "
                "https://app.watercryst.com/Device/ prüfen."
            )

        if response.status == 429:
            _LOGGER.warning(
                "API Rate-Limit erreicht. Erhöhe den Abfrage-Intervall."
            )
            raise WatercrystApiError("API Rate-Limit erreicht (429)")

        if response.status != 200:
            text = await response.text()
            raise WatercrystApiError(
                f"API-Fehler {response.status}: {text}"
            )

        # Manche Endpunkte geben nur eine Zahl zurück (z.B. cumulative/daily)
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await response.json()

        # Fallback: Versuche als Text zu parsen (einzelner Zahlenwert)
        text = await response.text()
        text = text.strip()
        try:
            return float(text)
        except ValueError:
            return text

    async def _put(self, endpoint: str, json_data: dict | None = None) -> Any:
        """PUT-Request an die API."""
        kwargs = {}
        if json_data is not None:
            kwargs["json"] = json_data

        response = await self._throttled_request("put", endpoint, **kwargs)

        if response.status in (401, 403):
            raise WatercrystAuthError("Ungültiger API-Key.")

        if response.status not in (200, 204):
            text = await response.text()
            raise WatercrystApiError(
                f"API-Fehler {response.status}: {text}"
            )

        if response.status == 204:
            return None

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await response.json()
        return await response.text()

    async def _post(self, endpoint: str, json_data: dict | None = None) -> Any:
        """POST-Request an die API."""
        kwargs = {}
        if json_data is not None:
            kwargs["json"] = json_data

        response = await self._throttled_request("post", endpoint, **kwargs)

        if response.status in (401, 403):
            raise WatercrystAuthError("Ungültiger API-Key.")

        if response.status not in (200, 201, 204):
            text = await response.text()
            raise WatercrystApiError(
                f"API-Fehler {response.status}: {text}"
            )

        if response.status == 204:
            return None

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await response.json()
        return await response.text()

    # ─── Datenabfrage (GET) ──────────────────────────────────────────────

    async def async_validate_api_key(self) -> bool:
        """Prüft ob der API-Key gültig ist.

        Wird im Config-Flow verwendet um den Key zu validieren.
        Ruft /v1/state auf – der leichteste Endpunkt.
        """
        try:
            await self._get(ENDPOINT_STATE)
            return True
        except WatercrystAuthError:
            return False
        except WatercrystApiError:
            # Andere Fehler (z.B. Server-Fehler) bedeuten nicht
            # zwangsläufig dass der Key ungültig ist
            return False

    async def async_get_measurements(self) -> dict[str, Any]:
        """Aktuelle Messwerte abrufen.

        Endpunkt: GET /v1/measurements/direct

        Returns:
            {
                "waterTemp": 12.5,        # Wassertemperatur in °C
                "pressure": 3.2,          # Wasserdruck in bar
                "lastWaterTapVolume": 5.3, # Letztes Zapfvolumen in Liter
                "lastWaterTapDuration": 23 # Letzte Zapfdauer in Sekunden
            }
        """
        data = await self._get(ENDPOINT_MEASUREMENTS)
        if isinstance(data, dict):
            return data
        _LOGGER.warning("Unerwartete Antwort von measurements: %s", data)
        return {}

    async def async_get_state(self) -> dict[str, Any]:
        """Gerätezustand abrufen.

        Endpunkt: GET /v1/state

        Returns:
            {
                "mode": {"name": "Normal"},
                "online": true,
                "waterProtection": {
                    "absenceModeEnabled": false,
                    "leakageProtectionEnabled": true,
                    "leakageDetected": false
                },
                "error": false,
                "warning": false
            }
        """
        data = await self._get(ENDPOINT_STATE)
        if isinstance(data, dict):
            return data
        _LOGGER.warning("Unerwartete Antwort von state: %s", data)
        return {}

    async def async_get_consumption_daily(self) -> float | None:
        """Täglichen Gesamtverbrauch in Litern abrufen.

        Endpunkt: GET /v1/statistics/cumulative/daily
        Gibt einen einzelnen Zahlenwert zurück (z.B. 109.56).
        """
        data = await self._get(ENDPOINT_STATISTICS_DAILY)
        if isinstance(data, (int, float)):
            return float(data)
        _LOGGER.warning("Unerwartete Antwort von daily stats: %s", data)
        return None

    async def async_get_consumption_weekly(self) -> float | None:
        """Wöchentlichen Gesamtverbrauch in Litern abrufen.

        Endpunkt: GET /v1/statistics/cumulative/weekly
        """
        data = await self._get(ENDPOINT_STATISTICS_WEEKLY)
        if isinstance(data, (int, float)):
            return float(data)
        return None

    async def async_get_consumption_monthly(self) -> float | None:
        """Monatlichen Gesamtverbrauch in Litern abrufen.

        Endpunkt: GET /v1/statistics/cumulative/monthly
        """
        data = await self._get(ENDPOINT_STATISTICS_MONTHLY)
        if isinstance(data, (int, float)):
            return float(data)
        return None

    # ─── Alle Daten in einem Durchlauf abrufen ───────────────────────────

    async def async_get_all_data(self) -> dict[str, Any]:
        """Ruft alle Datenquellen ab und kombiniert sie.

        Zwischen den Requests liegt automatisch eine Pause
        um die API nicht zu überlasten.

        Returns:
            Kombiniertes Dict mit allen Sensor-Daten
        """
        result: dict[str, Any] = {}

        # 1. Messwerte (waterTemp, pressure, lastWaterTapVolume, lastWaterTapDuration)
        try:
            measurements = await self.async_get_measurements()
            result.update(measurements)
        except WatercrystApiError as err:
            _LOGGER.error("Fehler bei Messwerte-Abfrage: %s", err)

        # 2. Gerätezustand (mode, online, waterProtection)
        try:
            state = await self.async_get_state()
            result["state"] = state

            # Flache Schlüssel für einfachen Zugriff
            if "mode" in state and isinstance(state["mode"], dict):
                result["mode_name"] = state["mode"].get("name", "Unbekannt")
            elif "mode" in state:
                result["mode_name"] = str(state["mode"])

            result["online"] = state.get("online", False)

            wp = state.get("waterProtection", {})
            if isinstance(wp, dict):
                result["absence_mode_enabled"] = wp.get(
                    "absenceModeEnabled", False
                )
                result["leakage_protection_enabled"] = wp.get(
                    "leakageProtectionEnabled", True
                )
                result["leakage_detected"] = wp.get(
                    "leakageDetected", False
                )

            result["error"] = state.get("error", False)
            result["warning"] = state.get("warning", False)

        except WatercrystApiError as err:
            _LOGGER.error("Fehler bei State-Abfrage: %s", err)

        # 3. Tagesverbrauch
        try:
            daily = await self.async_get_consumption_daily()
            if daily is not None:
                result["consumption_daily"] = daily
        except WatercrystApiError as err:
            _LOGGER.debug("Fehler bei Tagesverbrauch: %s", err)

        # 4. Wochenverbrauch
        try:
            weekly = await self.async_get_consumption_weekly()
            if weekly is not None:
                result["consumption_weekly"] = weekly
        except WatercrystApiError as err:
            _LOGGER.debug("Fehler bei Wochenverbrauch: %s", err)

        # 5. Monatsverbrauch
        try:
            monthly = await self.async_get_consumption_monthly()
            if monthly is not None:
                result["consumption_monthly"] = monthly
        except WatercrystApiError as err:
            _LOGGER.debug("Fehler bei Monatsverbrauch: %s", err)

        return result

    # ─── Steuerung (PUT/POST) ────────────────────────────────────────────

    async def async_set_absence_mode(self, enabled: bool) -> None:
        """Abwesenheitsmodus aktivieren/deaktivieren.

        Endpunkt: PUT /v1/state/absenceMode
        """
        _LOGGER.info("Setze Abwesenheitsmodus: %s", enabled)
        await self._put(ENDPOINT_ABSENCE_MODE, {"enabled": enabled})

    async def async_set_leakage_protection(self, enabled: bool) -> None:
        """Leckageschutz aktivieren/deaktivieren.

        Endpunkt: PUT /v1/state/leakageProtection

        WARNUNG: Bei Deaktivierung ist das Gebäude nicht
        mehr vor Leckagen geschützt!
        """
        _LOGGER.info("Setze Leckageschutz: %s", enabled)
        await self._put(ENDPOINT_LEAKAGE_PROTECTION, {"enabled": enabled})

    async def async_start_selftest(self) -> None:
        """Selbsttest starten.

        Endpunkt: POST /v1/selftest
        """
        _LOGGER.info("Starte Selbsttest")
        await self._post(ENDPOINT_SELFTEST)

    async def async_acknowledge_warning(self) -> None:
        """Warnung/Leckagealarm quittieren.

        Endpunkt: POST /v1/state/acknowledge

        WARNUNG: Vergewissern Sie sich vor dem Quittieren,
        dass die Ursache des Alarms beseitigt wurde!
        """
        _LOGGER.info("Quittiere Warnung/Alarm")
        await self._post(ENDPOINT_ACKNOWLEDGE_WARNING)

    async def async_set_water_supply(self, open_valve: bool) -> None:
        """Wasserzufuhr öffnen/schließen.

        Endpunkt: PUT /v1/waterSupply
        """
        action = "open" if open_valve else "close"
        _LOGGER.info("Setze Wasserzufuhr: %s", action)
        await self._put(ENDPOINT_WATER_SUPPLY, {"state": action})
