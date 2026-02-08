# 🚰 Watercryst BIOCAT – Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![Version](https://img.shields.io/badge/Version-2.1.0-blue.svg)](https://github.com/Schmidtjanroman/haos_watercryst_biocat_vibe/releases)

Home Assistant Custom Component zur Überwachung und Steuerung von **Watercryst BIOCAT** Wasseraufbereitungsgeräten über die offizielle REST-API.

<p align="center">
  <img src="https://www.watercryst.com/wp-content/uploads/biocat-kls-3000.png" alt="BIOCAT KLS" width="300">
</p>

---

## ✨ Funktionen

| Typ | Entität | Beschreibung |
|-----|---------|-------------|
| 🌡️ Sensor | Wassertemperatur | Aktuelle Wassertemperatur (°C) |
| 💧 Sensor | Wasserdruck | Aktueller Wasserdruck (bar) |
| 🚿 Sensor | Letztes Zapfvolumen | Volumen des letzten Wasserzapfens (L) |
| ⏱️ Sensor | Letzte Zapfdauer | Dauer des letzten Wasserzapfens (s) |
| 📊 Sensor | Tagesverbrauch | Gesamtverbrauch heute (L) |
| 📊 Sensor | Wochenverbrauch | Gesamtverbrauch diese Woche (L) |
| 📊 Sensor | Monatsverbrauch | Gesamtverbrauch diesen Monat (L) |
| 🔄 Sensor | Betriebsmodus | Aktueller Betriebsmodus |
| 🟢 Binary Sensor | Gerät online | Verbindungsstatus |
| 🏠 Binary Sensor | Abwesenheitsmodus | Aktiv/Inaktiv |
| 💦 Binary Sensor | Leckage erkannt | Leckage-Alarm |
| ⚠️ Binary Sensor | Gerätefehler | Fehlerstatus |
| ⚠️ Binary Sensor | Gerätewarnung | Warnungsstatus |
| 🔘 Switch | Abwesenheitsmodus | Ein-/Ausschalten |
| 🛡️ Switch | Leckageschutz | Ein-/Ausschalten |
| 🚰 Switch | Wasserzufuhr | Ventil öffnen/schließen |
| ▶️ Button | Selbsttest | Selbsttest starten |
| ✅ Button | Warnung quittieren | Alarm bestätigen |

**Tagesverbrauch** kann direkt im Home Assistant **Energie-Dashboard** verwendet werden.

---

## 📋 Voraussetzungen

1. Ein **BIOCAT KLS** Gerät mit Cloud-Anbindung (App-Funktion)
2. Ein **API-Key** von [app.watercryst.com/Device/](https://app.watercryst.com/Device/)

### API-Key erstellen

1. Öffne [app.watercryst.com/Device/](https://app.watercryst.com/Device/)
2. Melde dich mit deinem Watercryst-Konto an
3. Klicke auf **"Hinzufügen"** um einen neuen API-Key zu erstellen
4. Kopiere den generierten Key (z.B. `5vwi` oder `7pFY`)

---

## 🔧 Installation

### Über HACS (empfohlen)

1. **HACS** → **Integrationen** → ⋮ (drei Punkte oben rechts) → **Benutzerdefinierte Repositories**
2. Repository-URL eingeben: `https://github.com/Schmidtjanroman/haos_watercryst_biocat_vibe`
3. Kategorie: **Integration**
4. **Watercryst BIOCAT** suchen und installieren
5. Home Assistant **neu starten**

### Manuell

1. Repository als ZIP herunterladen
2. `custom_components/watercryst_biocat/` in deinen HA-Ordner `config/custom_components/` kopieren
3. Home Assistant **neu starten**

---

## ⚙️ Konfiguration

1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. Nach **Watercryst BIOCAT** suchen
3. **API-Key** eingeben (von app.watercryst.com/Device/)
4. Optional: **Gerätename** anpassen
5. Fertig! 🎉

### Optionen

Nach der Einrichtung kannst du in den Integrationsoptionen das **Abfrage-Intervall** anpassen (Standard: 30 Sekunden, Minimum: 10 Sekunden).

> **Hinweis:** Die Watercryst-API verträgt keine zu häufigen Abfragen. Ein Intervall unter 15 Sekunden wird nicht empfohlen.

---

## 🔌 API-Referenz

Diese Integration nutzt die offizielle Watercryst REST-API:

- **Dokumentation:** [appapi.watercryst.com](https://appapi.watercryst.com/#overview)
- **OpenAPI Spec:** [api-v1.yaml](https://appapi.watercryst.com/api-v1.yaml)
- **Authentifizierung:** `X-API-KEY` Header
- **Basis-URL:** `https://appapi.watercryst.com/v1/`

### Verwendete Endpunkte

| Methode | Endpunkt | Beschreibung |
|---------|----------|-------------|
| GET | `/v1/measurements/direct` | Aktuelle Messwerte |
| GET | `/v1/state` | Gerätezustand |
| GET | `/v1/statistics/cumulative/daily` | Tagesverbrauch |
| GET | `/v1/statistics/cumulative/weekly` | Wochenverbrauch |
| GET | `/v1/statistics/cumulative/monthly` | Monatsverbrauch |
| PUT | `/v1/state/absenceMode` | Abwesenheitsmodus setzen |
| PUT | `/v1/state/leakageProtection` | Leckageschutz setzen |
| POST | `/v1/watersupply/open` | Wasserzufuhr öffnen |
| POST | `/v1/watersupply/close` | Wasserzufuhr schließen |
| POST | `/v1/selftest` | Selbsttest starten |
| POST | `/v1/state/acknowledge` | Warnung quittieren |

---

## 📁 Dateistruktur

```
custom_components/watercryst_biocat/
├── __init__.py          # Integration Setup & DataUpdateCoordinator
├── api.py               # REST-API Client (X-API-KEY Auth)
├── config_flow.py       # GUI-Setup (API-Key Eingabe)
├── const.py             # Konstanten & API-Endpunkte
├── sensor.py            # 8 Sensoren
├── binary_sensor.py     # 5 Binary Sensoren
├── switch.py            # 3 Switches
├── button.py            # 2 Buttons
├── manifest.json        # HA Integration Manifest
├── strings.json         # Basis-Übersetzungen (Config Flow)
└── translations/
    ├── en.json          # Englisch
    └── de.json          # Deutsch
```

---

## 🙏 Credits

- **API-Dokumentation:** [WATERCryst Wassertechnik GmbH](https://www.watercryst.com)
- **Community-Beiträge:** [simon42 Forum](https://community.simon42.com/t/curl-in-rest-sensor-wandeln/24438), [Loxone Forum](https://www.loxforum.com/forum/german/software-konfiguration-programm-und-visualisierung/407346-einbindung-biocut-anlage-in-loxone-via-rest-api)
- **Inspiration:** [@route662](https://github.com/route662/home-assistant-watercryst-biocat)

---

## 📄 Lizenz

MIT License – siehe [LICENSE](LICENSE)
