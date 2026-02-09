# Watercryst BIOCAT – Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Custom Component zur Einbindung von **Watercryst BIOCAT** Wasseraufbereitungsgeräten in Home Assistant.

<img src="https://assets.heizung-billiger.de/images/watercryst/large_default/large_default-12000273_B_.jpg@webp" width="300" alt="BIOCAT Gerät">

## Funktionen

| Typ | Entität | Beschreibung |
|---|---|---|
| 🔢 Sensor | Wassertemperatur | Aktuelle Temperatur in °C |
| 🔢 Sensor | Wasserdruck | Aktueller Druck in bar (mit Langzeit-Statistik) |
| 🔢 Sensor | Letztes Zapfvolumen | Letzter Wasserentnahme-Volumen in L |
| 🔢 Sensor | Letzte Zapfdauer | Dauer der letzten Entnahme in Sekunden |
| 🔢 Sensor | Tagesverbrauch | Heutiger Verbrauch in L (→ Energie-Dashboard) |
| 🔢 Sensor | **Gesamtverbrauch** | Totaler Zählerstand in L (`total_increasing`) |
| 📝 Sensor | Betriebsmodus | Aktueller Betriebsstatus |
| 🕐 Sensor | **Letzte Leckageprüfung** | Zeitstempel der letzten Prüfung ¹ |
| 🕐 Sensor | **Letzter Selbsttest** | Zeitstempel des letzten Tests ¹ |
| 🔴 Binary Sensor | Verbindung | Geräte-Konnektivität |
| 🔴 Binary Sensor | Abwesenheitsmodus aktiv | Modus-Status |
| 🔴 Binary Sensor | Leckage erkannt | Feuchtigkeits-Erkennung |
| 🔴 Binary Sensor | Fehler / Warnung | Problem-Erkennung |
| 🔀 Switch | Abwesenheitsmodus | An = Abwesend, Aus = Anwesend |
| 🔀 Switch | Leckageschutz | Ein-/Ausschalten |
| 🔀 Switch | **Wasserzufuhr** | Ventil öffnen/schließen |
| 🔘 Button | Selbsttest starten | Geräte-Selbsttest auslösen |
| 🔘 Button | Warnung bestätigen | Aktive Warnungen quittieren |

¹ Timestamp-Sensoren sind nur verfügbar wenn die API die Felder liefert. Prüfe `/v1/state` Response.

## v3.0.0 Änderungen

- **Entfernt:** Wochen- und Monatsverbrauch (redundant – HA berechnet diese automatisch im Energie-Dashboard aus dem Tagesverbrauch)
- **Neu:** Gesamtverbrauch (`/v1/statistics/cumulative/total`) als `total_increasing` Sensor
- **Neu:** Timestamp-Sensoren für letzte Leckageprüfung und letzten Selbsttest (aus `/v1/state`)
- **Optimiert:** Nur noch 3-4 API-Calls pro Zyklus statt 5 → weniger API-Last

## API-Endpunkte

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| GET | `/v1/measurements/direct` | Temperatur, Druck, Zapfvolumen/-dauer |
| GET | `/v1/state` | Modus, Online, Wasserschutz, Fehler, Timestamps |
| GET | `/v1/statistics/cumulative/daily` | Tagesverbrauch (Liter) |
| GET | `/v1/statistics/cumulative/total` | Gesamtverbrauch (Liter) |
| PUT | `/v1/state/absenceMode` | Abwesenheitsmodus setzen |
| PUT | `/v1/state/leakageProtection` | Leckageschutz setzen |
| POST | `/v1/watersupply/open` | Wasserzufuhr öffnen |
| POST | `/v1/watersupply/close` | Wasserzufuhr schließen |
| POST | `/v1/selftest` | Selbsttest starten |
| POST | `/v1/state/acknowledge` | Warnung quittieren |

## Installation via HACS

1. HACS öffnen → **Integrationen** → ⋮ → **Benutzerdefinierte Repositories**
2. URL: `https://github.com/Schmidtjanroman/haos_watercryst_biocat_vibe`
3. Kategorie: **Integration** → **Hinzufügen**
4. Nach **Watercryst BIOCAT** suchen → **Installieren**
5. **Home Assistant neu starten**
6. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen** → **Watercryst BIOCAT**
7. API-Key eingeben (erstellt unter https://app.watercryst.com/Device/)

## Manuelle Installation

```bash
cd /config
mkdir -p custom_components/watercryst_biocat
# Alle Dateien aus diesem Repository nach custom_components/watercryst_biocat/ kopieren
# Home Assistant neu starten
```

## Energie-Dashboard

Der **Tagesverbrauch**-Sensor (`state_class: total`) kann direkt im HA Energie-Dashboard als Wasserquelle verwendet werden. HA berechnet daraus automatisch Wochen-, Monats- und Jahresstatistiken.

## Dateistruktur

```
custom_components/watercryst_biocat/
├── __init__.py          # Einstiegspunkt, DataUpdateCoordinator
├── api.py               # Asynchroner API-Client mit Rate-Limiting
├── config_flow.py       # GUI-basierte Einrichtung (API-Key)
├── const.py             # Alle Konstanten und Endpunkte
├── manifest.json        # Integration-Metadaten (v3.0.0)
├── sensor.py            # 9 Sensoren (Messwerte, Statistik, Timestamps)
├── binary_sensor.py     # 5 Binary Sensoren (Status, Fehler, Leckage)
├── switch.py            # 3 Switches (Abwesenheit, Schutz, Ventil)
├── button.py            # 2 Buttons (Selbsttest, Quittieren)
├── strings.json         # Basis-Übersetzungen
└── translations/
    ├── en.json          # Englisch
    └── de.json          # Deutsch
```

## Lizenz

Dieses Projekt steht unter der GPL-3.0-Lizenz.

## Danksagungen

- **morpheus12** (simon42 Community) – Erste REST-Sensor Implementierung
- **route662** – Erste HACS Integration
- **Loxforum Community** – API-Dokumentation und Tests
