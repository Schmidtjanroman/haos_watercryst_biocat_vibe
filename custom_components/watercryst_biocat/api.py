"""API-Client für die Watercryst BIOCAT REST-API.

Authentifizierung: X-API-KEY Header
Basis-URL: https://appapi.watercryst.com
Dokumentation: https://appapi.watercryst.com/api-v1.yaml

Wichtig: Die API verträgt keine gleichzeitigen Requests.
Zwischen Abfragen sollten mindestens 2-3 Sekunden liegen.

Änderungen v3.0.0:
  - weekly/monthly Endpunkte entfernt (HA berechnet das selbst)
  - /v1/statistics/cumulative/total hinzugefügt (graceful fallback)
  - Robustes Parsing aller Felder aus /v1/state (Timestamps, Meldungen)
  - Nur noch 3-4 API-Calls pro Zyklus statt 5
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
    ENDPOINT_STATISTICS_TOTAL,
    ENDPOINT_WATER_SUPPLY_CLOSE,
    ENDPOINT_WATER_SUPPLY_OPEN,
)

_LOGGER = logging.getLogger(__name__)

# Minimale Pause zwischen API-Aufrufen (Sekunden)
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
        """Initialisierung des API-Clients."""
        self._session = session
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._last_request_time: float = 0
        self._request_lock = asyncio.Lock()
        # Flag: total-Endpunkt verfügbar (wird beim ersten 404 deaktiviert)
        self._total_endpoint_available: bool = True

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
        """Führt einen API-Request mit Rate-Limiting durch."""
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
        """GET-Request an die API."""
        response = await self._throttled_request("get", endpoint)

        if response.status in (401, 403):
            raise WatercrystAuthError(
                "Ungültiger API-Key. Bitte unter "
                "https://app.watercryst.com/Device/ prüfen."
            )

        if response.status == 429:
            _LOGGER.warning("API Rate-Limit erreicht. Erhöhe den Abfrage-Intervall.")
            raise WatercrystApiError("API Rate-Limit erreicht (429)")

        if response.status == 404:
            raise WatercrystApiError(f"Endpunkt nicht gefunden: {endpoint}")

        if response.status != 200:
            text = await response.text()
            raise WatercrystApiError(f"API-Fehler {response.status}: {text}")

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
            raise WatercrystApiError(f"API-Fehler {response.status}: {text}")

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
            raise WatercrystApiError(f"API-Fehler {response.status}: {text}")

        if response.status == 204:
            return None

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return await response.json()
        return await response.text()

    # ─── Datenabfrage (GET) ──────────────────────────────────────────

    async def async_validate_api_key(self) -> bool:
        """Prüft ob der API-Key gültig ist."""
        try:
            await self._get(ENDPOINT_STATE)
            return True
        except WatercrystAuthError:
            return False
        except WatercrystApiError:
            return False

    async def async_get_measurements(self) -> dict[str, Any]:
        """Aktuelle Messwerte abrufen.

        Endpunkt: GET /v1/measurements/direct ✅

        Returns:
            {
                "waterTemp": 12.5,
                "pressure": 3.2,
                "lastWaterTapVolume": 5.3,
                "lastWaterTapDuration": 23
            }
        """
        data = await self._get(ENDPOINT_MEASUREMENTS)
        if isinstance(data, dict):
            return data
        _LOGGER.warning("Unerwartete Antwort von measurements: %s", data)
        return {}

    async def async_get_state(self) -> dict[str, Any]:
        """Gerätezustand abrufen.

        Endpunkt: GET /v1/state ✅

        Bestätigte Felder:
            mode.name, online, waterProtection.{absenceModeEnabled,
            leakageProtectionEnabled, leakageDetected}, error, warning

        Mögliche weitere Felder (abhängig von Firmware):
            lastMicroleakageTest, lastSelftest, errorMessage,
            selftestResult, waterSupply, ...

        Die Methode async_get_all_data() extrahiert alle bekannten
        UND unbekannten Felder robust.
        """
        data = await self._get(ENDPOINT_STATE)
        if isinstance(data, dict):
            return data
        _LOGGER.warning("Unerwartete Antwort von state: %s", data)
        return {}

    async def async_get_consumption_daily(self) -> float | None:
        """Täglichen Gesamtverbrauch in Litern abrufen.

        Endpunkt: GET /v1/statistics/cumulative/daily ✅
        Gibt einen einzelnen Zahlenwert zurück (z.B. 109.56).
        """
        data = await self._get(ENDPOINT_STATISTICS_DAILY)
        if isinstance(data, (int, float)):
            return float(data)
        _LOGGER.warning("Unerwartete Antwort von daily stats: %s", data)
        return None

    async def async_get_consumption_total(self) -> float | None:
        """Totalen Gesamtverbrauch in Litern abrufen.

        Endpunkt: GET /v1/statistics/cumulative/total ⚠️
        Muss gegen die echte API verifiziert werden.
        Bei 404 wird der Endpunkt für diese Session deaktiviert.
        """
        if not self._total_endpoint_available:
            return None

        try:
            data = await self._get(ENDPOINT_STATISTICS_TOTAL)
            if isinstance(data, (int, float)):
                return float(data)
            _LOGGER.warning("Unerwartete Antwort von total stats: %s", data)
            return None
        except WatercrystApiError as err:
            if "nicht gefunden" in str(err) or "404" in str(err):
                _LOGGER.info(
                    "Endpunkt %s nicht verfügbar – wird deaktiviert. "
                    "Prüfe https://appapi.watercryst.com/api-v1.yaml",
                    ENDPOINT_STATISTICS_TOTAL,
                )
                self._total_endpoint_available = False
                return None
            raise

    # ─── Alle Daten in einem Durchlauf abrufen ───────────────────────

    async def async_get_all_data(self) -> dict[str, Any]:
        """Ruft alle Datenquellen ab und kombiniert sie.

        v3.0.0: Nur noch 3-4 API-Calls pro Zyklus:
          1. measurements (waterTemp, pressure, ...)
          2. state (mode, online, waterProtection, timestamps, ...)
          3. statistics/cumulative/daily
          4. statistics/cumulative/total (optional, graceful fallback)
        """
        result: dict[str, Any] = {}

        # 1. Messwerte
        try:
            measurements = await self.async_get_measurements()
            result.update(measurements)
        except WatercrystApiError as err:
            _LOGGER.error("Fehler bei Messwerte-Abfrage: %s", err)

        # 2. Gerätezustand – ROBUSTES PARSING aller Felder
        try:
            state = await self.async_get_state()
            result["state_raw"] = state

            # Mode
            if "mode" in state and isinstance(state["mode"], dict):
                result["mode_name"] = state["mode"].get("name", "Unbekannt")
            elif "mode" in state:
                result["mode_name"] = str(state["mode"])

            # Online-Status
            result["online"] = state.get("online", False)

            # Water Protection Block
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

            # Fehler & Warnungen
            result["error"] = state.get("error", False)
            result["warning"] = state.get("warning", False)

            # ─── Zusätzliche Felder (firmwareabhängig) ───────────
            # Fehlermeldung als Text
            for key in ("errorMessage", "error_message", "errorText"):
                if key in state and state[key]:
                    result["error_message"] = str(state[key])
                    break

            # Selbsttest-Ergebnis
            for key in ("selftestResult", "selftest_result", "lastSelftestResult"):
                if key in state and state[key]:
                    result["selftest_result"] = str(state[key])
                    break

            # Letzte Leckageprüfung (Timestamp)
            for key in (
                "lastMicroleakageTest",
                "lastLeakageTest",
                "lastMicroLeakageTest",
                "microleakageTest",
            ):
                if key in state and state[key]:
                    result["last_leakage_test"] = str(state[key])
                    break

            # Letzter Selbsttest (Timestamp)
            for key in ("lastSelftest", "lastSelfTest", "selftest"):
                if key in state and state[key]:
                    result["last_selftest"] = str(state[key])
                    break

            # Wasserzufuhr-Status
            ws = state.get("waterSupply", state.get("watersupply", {}))
            if isinstance(ws, dict):
                ws_state = ws.get("state", ws.get("status", ""))
                result["water_supply_open"] = str(ws_state).lower() in (
                    "open", "opened", "true", "1",
                )
            elif isinstance(ws, str):
                result["water_supply_open"] = ws.lower() in (
                    "open", "opened", "true",
                )
            elif isinstance(ws, bool):
                result["water_supply_open"] = ws

            # Log alle unbekannten Top-Level Felder zur Analyse
            known_keys = {
                "mode", "online", "waterProtection", "error", "warning",
                "errorMessage", "error_message", "errorText",
                "selftestResult", "selftest_result", "lastSelftestResult",
                "lastMicroleakageTest", "lastLeakageTest",
                "lastMicroLeakageTest", "microleakageTest",
                "lastSelftest", "lastSelfTest", "selftest",
                "waterSupply", "watersupply",
            }
            unknown = set(state.keys()) - known_keys
            if unknown:
                _LOGGER.info(
                    "Unbekannte Felder in /v1/state: %s – "
                    "Bitte melde diese im GitHub-Issue!",
                    {k: state[k] for k in unknown},
                )

        except WatercrystApiError as err:
            _LOGGER.error("Fehler bei State-Abfrage: %s", err)

        # 3. Tagesverbrauch
        try:
            daily = await self.async_get_consumption_daily()
            if daily is not None:
                result["consumption_daily"] = daily
        except WatercrystApiError as err:
            _LOGGER.debug("Fehler bei Tagesverbrauch: %s", err)

        # 4. Gesamtverbrauch (optional, graceful fallback)
        try:
            total = await self.async_get_consumption_total()
            if total is not None:
                result["consumption_total"] = total
        except WatercrystApiError as err:
            _LOGGER.debug("Fehler bei Gesamtverbrauch: %s", err)

        return result

    # ─── Steuerung (PUT/POST) ────────────────────────────────────────

    async def async_set_absence_mode(self, enabled: bool) -> None:
        """Abwesenheitsmodus aktivieren/deaktivieren."""
        _LOGGER.info("Setze Abwesenheitsmodus: %s", enabled)
        await self._put(ENDPOINT_ABSENCE_MODE, {"enabled": enabled})

    async def async_set_leakage_protection(self, enabled: bool) -> None:
        """Leckageschutz aktivieren/deaktivieren."""
        _LOGGER.info("Setze Leckageschutz: %s", enabled)
        await self._put(ENDPOINT_LEAKAGE_PROTECTION, {"enabled": enabled})

    async def async_open_water_supply(self) -> None:
        """Wasserzufuhr öffnen."""
        _LOGGER.info("Öffne Wasserzufuhr")
        await self._post(ENDPOINT_WATER_SUPPLY_OPEN)

    async def async_close_water_supply(self) -> None:
        """Wasserzufuhr schließen."""
        _LOGGER.info("Schließe Wasserzufuhr")
        await self._post(ENDPOINT_WATER_SUPPLY_CLOSE)

    async def async_start_selftest(self) -> None:
        """Selbsttest starten."""
        _LOGGER.info("Starte Selbsttest")
        await self._post(ENDPOINT_SELFTEST)

    async def async_acknowledge_warning(self) -> None:
        """Warnung/Leckagealarm quittieren."""
        _LOGGER.info("Quittiere Warnung/Alarm")
        await self._post(ENDPOINT_ACKNOWLEDGE_WARNING)
