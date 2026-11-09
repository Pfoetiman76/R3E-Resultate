# RaceRoom Results Companion

Eigenständige Begleit-App für **RaceRoom Racing Experience** – im Stil von „ACC Results Companion“:
Sie liest die von RaceRoom erzeugten Ergebnisdateien automatisch ein und bietet eine dauerhafte Historie aller Sitzungen samt persönlichen Bestzeiten.

## Funktionen (Version 0.1.0)

- Automatische Überwachung des RaceRoom-Ergebnisordners (alle 5 Sekunden); neue Sitzungen erscheinen ohne Zutun
- Sitzungshistorie: Datum, Typ, Strecke, Fahrerzahl, Sitzungs-Bestzeit; Klick zeigt das vollständige Ergebnis (Position, Fahrer, Fahrzeug, Runden, beste Runde, Renzeit, Status)
- Bestzeiten pro Fahrer / Strecke / Fahrzeug
- Statistik-Kopfzeile: Sitzungen, Renneinsätze, Runden gesamt, Siege (nur Rennen), Allzeit-Bestzeit
- SQLite-Datenbank – einmal eingelesen bleibt alles dauerhaft gespeichert; Duplikate werden erkannt
- Unterstützte Formate:
  - Lokale Einzelspieler-Ergebnisse (`.txt`, seit Mai 2023 JSON) aus `Dokumente\My Games\SimBin\RaceRoom Racing Experience\UserData\Log\Results`
  - Dedicated-Server-Ergebnisse (`.json`)
  - Multiplayer-Ergebnisse (`.xml`, `<MultiplayerRaceResult>`)

## Voraussetzungen

- Windows (getesteter Zielpfad des Ergebnisordners) – der Ordner lässt sich in der App frei wählen
- Python 3.10 oder neuer
- PySide6: `pip install PySide6`

## Start

```
python main.py
```

Der Ergebnisordner wird automatisch erkannt (standardmäßig der RaceRoom-Ordner unter Dokumente). Über **Datei → Ergebnis-Ordner wählen …** lässt er sich ändern;über **Neu einlesen** wird manuell neu gescannt.

Server- oder Multiplayer-Dateien werden einfach in denselben Ordner kopiert (oder ein beliebiger Ordner gewählt).

## Projektstruktur

| Datei | Zweck |
|---|---|
| `main.py` | PySide6-Oberfläche (Tabs: Sitzungen, Bestzeiten) |
| `rrc/parser.py` | Formatunabhängiger Parser (SP-JSON, Dedicated-JSON, Multiplayer-XML) |
| `rrc/database.py` | SQLite-Speicher mit Duplikaterkennung (Digest) |
| `rrc/models.py` | Datenmodelle + Zeitformatierung |
| `rrc/paths.py` | Standardpfade (Ergebnisordner, Datenbank) |
| `tests/` | 17 Unit-Tests (Parser + Datenbank) |

Tests ausführen: `python -m unittest discover -s tests`

## Technische Hinweise

- Kernelemente (Parser, Datenbank) sind Qt-frei und damit unabhängig testbar.
- Duplikaterkennung über MD5-Digest über Datei, Sitzungstyp, Zeit, Strecke, Fahrer, Positionen und Bestzeiten – erneutes Einlesen ändern nichts.
- `bestlaptimems`, `qualtimems`, `racetimems` werden tolerant gelesen (Groß-/Kleinschreibung, Varianten wie `bestLapTime`).
- Fehlerhafte oder unvollständige Dateien werden übersprungen und in der Statuszeile als „unlesbar“ gezählt; die App stürzt dadurch nicht ab.

## Geplante Erweiterungen (Rückmeldung willkommen)

- Runden-für-Runden-Ansicht der Server-Ergebnisse (Sektorenzeiten liegen bereits im Parser)
- CSV/HTML-Export einzelner Sitzungen
- Unfall-/Ausfallstatistik
- Kraftstoffprognose aus historischen Runden
