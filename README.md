# RaceRoom Results Companion (R3E Resultate)

Eigenständige Begleit-App für **RaceRoom Racing Experience** – im Stil von „ACC Results Companion“:
Sie liest die von RaceRoom erzeugten Ergebnisdateien automatisch ein und bietet eine dauerhafte Historie aller Sitzungen samt persönlichen Bestzeiten. Optik und Update-Mechanik folgen dem Vorbild von PitBoss R3E.

## Funktionen (Version 0.4.5)

- Überarbeitete Optik: kompakte Tabellen mit feinen Gitterlinien (keine Zebra-Streifen), Zeit- und Delta-Werte in technischer Schrift (Consolas), aktiver Reiter und Auswahl in RaceRoom-Rot, Rekordwerte gelb hervorgehoben, dauerhafte Statusanzeige (Sitzungen · Runden · Datenbank)
- Automatische Überwachung des RaceRoom-Ergebnisordners (alle 5 Sekunden); neue Sitzungen erscheinen ohne Zutun
- Sitzungshistorie: Datum, Typ, Strecke, Fahrerzahl, Sitzungs-Bestzeit; Klick zeigt das vollständige Ergebnis
- Bestzeiten pro Fahrer / Strecke / Fahrzeug
- Statistik-Kopfzeile: Sitzungen, Renneinsätze, Runden gesamt, Siege (nur Rennen), Allzeit-Bestzeit
- Dunkles PitBoss-Theme (RaceRoom-Rot-Akzent, Fusion-Stil)
- Suche & Filter in der Sitzungsliste (freie Suche nach Strecke/Layout/Typ, Filter nach Sitzungstyp und Fahrer)
- Runden-für-Runden-Ansicht mit Sektorenzeiten und Delta zur besten Runde (Server-/Multiplayer-Ergebnisse)
- CSV- und HTML-Export der ausgewählten Sitzung (Semikolon-CSV, dunkel gestaltetes HTML)
- Statistik-Tab: Dashboard-Kacheln (Rennen, Siege, Podium, Zielquote, Runden, Allzeit-Bestzeit)
- Bestzeiten-Entwicklung als Diagramm je Strecke (eigene QPainter-Chart, keine Zusatzabhängigkeit)
- Unfall-/Ausfall-Analyse: DNF-Quote je Fahrer und Ausfall-Historie (nur Rennen)
- Rekord-Kacheln im Runden-Tab: Renn-Rekord, Quali-Rekord, theoretische Optimal-Runde (Summe der besten Sektoren) und Allzeit-Bestzeit der gewählten Strecke
- Farbige Delta-Anzeige je Runde: grün = Rekordklasse, amber = nah dran (innerhalb 2 % der Rekordzeit), rot = Ausrutscher (über 2 s langsamer)
- KI-Fahrer ausblenden: Haken in der Sitzungsliste; die Namen echter Fahrer legen Sie unter „Werkzeuge → Echte Fahrer festlegen …“ fest (durch Komma getrennt). Der Filter wirkt auf Sitzungsliste, Ergebnisdetails, Runden-Fahrerwahl, Bestzeiten und Exporte
- Kraftstoffrechner („Werkzeuge → Kraftstoffrechner …“): Bedarfsprognose für Rennen nach Runden oder Minuten
- Erweiterte Filter in der Sitzungsliste: Zeitraum (Datum von/bis mit Kalenderauswahl, aktivierbar über Haken), Strecke und Fahrzeug; kombinierbar mit Suche, Typ und Fahrer
- Eigenes App-Symbol (Stoppuhr mit Schriftzug, freigegebene Kombination): Fenster- und Taskleistensymbol; der Installer nutzt es ebenfalls für Programm und Desktop-Verknüpfung
- Strecken-Id-Auflösung: Einzelspieler-Ergebnisse von RaceRoom nennen die Strecke nur als interne Nummer. Die App übersetzt bekannte Ids automatisch in lesbare Namen (z. B. „Hockenheimring Classic – Grand Prix“); unbekannte Ids ordnen Sie einmalig über „Werkzeuge → Unbekannte Strecken-Ids zuordnen …“ zu – die Zuordnung wird gespeichert und auf alle vorhandenen und künftigen Sitzungen angewendet
  - Ø Rundenzeit kommt automatisch aus der eigenen Sitzungshistorie (Rundendaten, Fallback: Bestzeiten)
  - Verbrauch pro Runde und Tankgröße pflegen Sie je Strecke/Fahrzeug einmal; die Werte werden in `fuel_history.json` im App-Ordner gespeichert
  - Tank-Check zeigt sofort, ob die prognostizierte Menge in den Tank passt (wie der Sprit-Rechner in PitBoss)
- Automatische Update-Prüfung beim Start + „Hilfe → Nach Updates suchen …“ mit Ein-Klick-Download des Installers
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

## Windows-Installer erstellen (GitHub Actions)

Der Workflow `.github/workflows/release.yml` baut bei jedem Tag `v*` (z. B. `v0.2.0`) automatisch:

1. Unit-Tests
2. PyInstaller-Build (`dist/R3EResultate`)
3. Inno-Setup-Installer (`R3E-Resultate-Setup-<Version>.exe`)
4. GitHub-Release mit dem Installer als Anhang

Klick-Weg: GitHub → **Releases** → **Draft a new release** → Tag `v0.2.0` eingeben, Ziel `main` → **Publish release**. Der Build dauert einige Minuten; danach hängt der Installer am Release. Wichtig: Tag-Name und `APP_VERSION` in `rrc/models.py` müssen identisch sein, sonst meldet der Updater fälschlich ein Update.

## Automatische Updates

- Beim App-Start wird im Hintergrund über `api.github.com/repos/Pfoetiman76/R3E-Resultate/releases/latest` geprüft (blockiert die UI nicht; ohne Token nutzbar).
- Bei einer neueren Version erscheint ein Dialog mit Änderungsnotizen und den Schaltflächen „Herunterladen & installieren“ (Installer wird geladen, App beendet sich, Installer startet) bzw. „Download-Seite öffnen“.
- Manuelle Prüfung: **Hilfe → Nach Updates suchen …**
- Netzwerkstörungen (z. B. temporäre GitHub-504-Fehler) werden mit mehreren Wiederholungen überstanden.

## Projektstruktur

| Datei | Zweck |
|---|---|
| `main.py` | PySide6-Oberfläche (Tabs: Sitzungen, Runden, Bestzeiten, Statistik; Export; Update-Dialoge) |
| `rrc/charts.py` | Bestzeiten-Diagramm (QPainter, ohne Zusatzpakete) |
| `rrc/theme.py` | Dunkles PitBoss-Theme (QSS, RaceRoom-Rot-Akzent) |
| `rrc/parser.py` | Formatunabhängiger Parser (SP-JSON, Dedicated-JSON, Multiplayer-XML) |
| `rrc/database.py` | SQLite-Speicher mit Duplikaterkennung (Digest) |
| `rrc/models.py` | Datenmodelle + Zeitformatierung + `APP_VERSION` |
| `rrc/trackids.py` | Übersetzungstabelle für RaceRoom-Strecken- und Fahrzeug-Ids + Benutzerzuordnungen |
| `rrc/icon_gen.py` | Prozeduraler Icon-Generator (reines Python, erzeugt die .ico in allen Größen) |
| `tools/make_icon.py` | Build-Hilfsskript: erzeugt `rrc/app_icon.ico` vor dem PyInstaller-Build |
| `rrc/paths.py` | Standardpfade (Ergebnisordner, Datenbank) |
| `updater.py` | GitHub-Releases-Updateprüfung + Installer-Download (bewährtes PitBoss-Modul) |
| `installer/setup.iss` | Inno-Setup-Installer |
| `installer/r3e_resultate.spec` | PyInstaller-Spezifikation |
| `.github/workflows/release.yml` | CI: Tests → EXE → Installer → Release |
| `tests/` | 75 Unit-Tests (Parser, Datenbank, Modelle, Einstellungen, Kraftstoff, Id-Auflösung, Icon) |

Tests ausführen: `python -m unittest discover -s tests`

Hinweis: Rundendetails (Runden-/Sektorenzeiten) werden erst mit Version 0.3.0 in der Datenbank gespeichert; Sitzungen, die mit 0.2.0 bereits eingelesen wurden, enthalten keine Rundendaten, bis Sie die Datenbank löschen (sie wird beim nächsten Start komplett neu aufgebaut — alle Ergebnisdateien bleiben im RaceRoom-Ordner erhalten).

## Technische Hinweise

- Kernelemente (Parser, Datenbank, Updater) sind Qt-frei und damit unabhängig testbar.
- Duplikaterkennung über MD5-Digest über Datei, Sitzungstyp, Zeit, Strecke, Fahrer, Positionen und Bestzeiten.
- Fehlerhafte oder unvollständige Dateien werden übersprungen und in der Statuszeile als „unlesbar“ gezählt; die App stürzt dadurch nicht ab.

## Geplante Erweiterungen

- Bestzeiten-Vergleich gegen Mitfahrer über mehrere Sitzungen
