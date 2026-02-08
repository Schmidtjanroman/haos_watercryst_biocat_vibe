# Watercryst BIOCAT – Home Assistant Integration

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-blue.svg)](https://www.home-assistant.io/)

Custom Component zur Einbindung von **Watercryst BIOCAT** Wasseraufbereitungsgeräten in Home Assistant.

![BIOCAT Gerät](https://assets.heizung-billiger.de/images/watercryst/large_default/large_default-12000273_B_.jpg@webp)

## Funktionen

| Typ | Entität | Beschreibung |
|-----|---------|-------------|
| 🔢 Sensor | Wasserdruck | Aktueller Druck in Bar (mit Langzeit-Statistik) |
| 🔢 Sensor | Wassertemperatur | Aktuelle Temperatur in °C |
| 🔢 Sensor | Wasserhärte | Aktuelle Härte in °dH |
| 🔢 Sensor | Durchflussrate | Aktueller Durchfluss in l/min |
| 🔢 Sensor | Gesamtverbrauch | Zählerstand in Litern (total_increasing) |
| 🔢 Sensor | Tagesverbrauch | Heutiger Verbrauch in Litern |
| 🔢 Sensor | Wochen-/Monatsverbrauch | Statistik-Sensoren |
| 📝 Sensor | Gerätezustand | Aktueller Betriebsstatus |
| 📝 Sensor | Fehlermeldung | Aktive Fehlermeldung (Text) |
| 📝 Sensor | Selbsttest-Ergebnis | Ergebnis des letzten Tests |
| 🕐 Sensor | Selbsttest/Leckage zuletzt | Zeitstempel der letzten Prüfung |
| 🔴 Binary Sensor | Fehler / Warnung | Problem-Erkennung |
| 🔴 Binary Sensor | Leckage erkannt | Feuchtigkeits-Erkennung |
| 🔴 Binary Sensor | Verbindung | Geräte-Konnektivität |
| 🔀 Switch | Abwesenheitsmodus | An = Abwesend, Aus = Anwesend |
| 🔀 Switch | Leckageschutz | Ein-/Ausschalten |
| 🔘 Button | Selbsttest starten | Geräte-Selbsttest auslösen |
| 🔘 Button | Warnung bestätigen | Aktive Warnungen quittieren |

## Installation via HACS

### 1. Repository hinzufügen

1. HACS in Home Assistant öffnen
2. **Integrationen** → **⋮** (drei Punkte oben rechts) → **Benutzerdefinierte Repositories**
3. URL eingeben: `https://github.com/Schmidtjanroman/haos_watercryst_biocat_vibe`
4. Kategorie: **Integration**
5. **Hinzufügen** klicken

### 2. Integration installieren

1. In HACS nach **Watercryst BIOCAT** suchen
2. **Installieren** klicken
3. **Home Assistant neu starten**

### 3. Integration einrichten

1. **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
2. Nach **Watercryst BIOCAT** suchen
3. Benutzername und Passwort des Watercryst-Kontos eingeben
4. Die Integration erstellt automatisch alle Sensoren und Schalter

## Manuelle Installation

Falls HACS nicht verfügbar ist:

```bash
# Im Home Assistant Config-Verzeichnis:
cd /config
mkdir -p custom_components/watercryst_biocat
# Alle Dateien aus diesem Repository nach custom_components/watercryst_biocat/ kopieren
# Danach Home Assistant neu starten
```

## Übersetzungen

Die Integration unterstützt Mehrsprachigkeit über das Home Assistant i18n-System:

- `translations/en.json` – Englisch (Standard)
- `translations/de.json` – Deutsch

### Weitere Sprachen hinzufügen

Einfach eine neue JSON-Datei im `translations/`-Ordner erstellen (z.B. `fr.json` für Französisch) und die Texte übersetzen. Kein Python-Code muss geändert werden.

## Dateistruktur

```
custom_components/watercryst_biocat/
├── __init__.py          # Einstiegspunkt, DataUpdateCoordinator
├── api.py               # Asynchroner API-Client
├── config_flow.py       # GUI-basierte Einrichtung
├── const.py             # Alle Konstanten
├── manifest.json        # Integration-Metadaten
├── strings.json         # Basis-Übersetzung (Pflicht für Config Flow)
├── sensor.py            # Messwert-Sensoren
├── binary_sensor.py     # Fehler-/Warnungs-Sensoren
├── switch.py            # Abwesenheit & Leckageschutz
├── button.py            # Selbsttest & Bestätigungen
└── translations/
    ├── en.json           # Englische Übersetzungen
    └── de.json           # Deutsche Übersetzungen
```

## Hinweise

- **API-Endpunkte**: Die Endpunkte sind basierend auf REST-Standards simuliert, da keine öffentliche API-Dokumentation vorliegt. Bei Abweichungen müssen die Endpunkte in `api.py` und die Daten-Extraktion in den Entity-Dateien angepasst werden.
- **Polling-Intervall**: Standardmäßig 60 Sekunden. Kann in `const.py` über `UPDATE_INTERVAL` geändert werden.
- **Credentials**: Werden sicher im Home Assistant Credential-Store gespeichert.

## Lizenz

MIT License
