# RaceRoom Results Companion (R3E Resultate)

Eigenständige Begleit-App für **RaceRoom Racing Experience** – im Stil von „ACC Results Companion“:
Sie liest die von RaceRoom erzeugten Ergebnisdateien automatisch ein und bietet eine dauerhafte Historie aller Sitzungen samt persönlichen Bestzeiten. Optik und Update-Mechanik folgen dem Vorbild von PitBoss R3E.

## Funktionen (Version 0.4.14)

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
- Runden gesamt / gültig (0.4.14): die Ergebnistabelle zeigt in der Spalte „Runden ges./gültig" beide Werte (z. B. 9 / 3), wenn die Ergebnisdatei mehr Runden angibt als gültige Rundenzeiten enthält — Server-Dateien ohne Gesamtangabe zeigen weiterhin nur eine Zahl; der KI-Platzhalter-Wert wird ausgeschlossen
- Lesbare Datumsfelder (0.4.14): die Datumsauswahl in der Filterzeile ist jetzt Teil des dunklen Designs — heller Eingabefeld-Hintergrund mit feinem Rahmen und reinweißer Schrift, so wie die übrigen Bedienelemente
- Diagnose-Export (0.4.13): über „Werkzeuge → Diagnose exportieren …" wird ein Klartext-Bericht erzeugt, der je Strecke den Median aller Bestzeiten sowie die fünf schnellsten Bestzeiten und Runden mit Fahrer, Fahrzeug, Klasse, KI-Kennzeichnung und Quelldatei auflistet — die Grundlage für eine fundierte Ferndiagnose auffälliger Werte
- Korrektur der Sitzungszahlen (0.4.12): verbesserte Strecken- und Fahrzeug-Übersetzungen zwischen App-Versionen hatten dazu geführt, dass bereits erfasste Sitzungen erneut gespeichert wurden — Sitzungen, Runden und Statistiken waren dadurch mehrfach gezählt (z. B. dreifache Sitzungszahl je Strecke). Beim Start werden solche Duplikate jetzt automatisch bereinigt (je Quelldatei, Typ und Zeit bleibt die vollständigste, neueste Sitzung) und künftig beim Einlesen zuverlässig verhindert; die Statusleiste meldet die Anzahl bereinigter Duplikate
- Schneller Programmstart (0.4.11): bereits eingelesene, unveränderte Ergebnisdateien werden beim Start übersprungen (Lese-Cache über Dateigröße und Änderungszeitpunkt) — der Start bleibt auch bei hunderten Dateien augenblicklich; neue und geänderte Dateien werden wie gewohnt erkannt. Die Datenbank wartet bei kurzfristigen Sperren (Antivirus, Cloud-Sync, zweite App-Instanz) bis zu zehn Sekunden statt abzustürzen und arbeitet im WAL-Modus
- Fahrzeug- und Klassen-Anzeige plus KI-Erkennung (0.4.10): Einzelspieler-Ergebnisse nennen das Fahrzeug nur als interne Nummer — die App liest und übersetzt sie jetzt automatisch (auch für bereits gespeicherte Sitzungen, die beim Start aus den Originaldateien ergänzt werden). KI-Fahrer werden anhand des internen Kennzeichens in der Datei zuverlässig erkannt und mit dem Haken „KI-Fahrer ausblenden“ auch ohne gepflegte Fahrerliste ausgeblendet; Statistik, Sitzungsliste, Bestzeiten und Auswertung zeigen dann nur noch echte Fahrer. Neu: Spalte „Fahrzeug“ in der Sitzungsliste, Spalte „Klasse“ bei den Bestzeiten, Gruppierung „nach Fahrzeugklasse“ in der Auswertung und Rekord-Kacheln je Klasse im Runden-Tab (Klassennamen erfordern die hinterlegte RaceRoom-Installation, siehe 0.4.7). Korrigiert: Bestzeit je Sitzung und Allzeit-Bestzeit bleiben nicht mehr leer, wenn einzelne Fahrer keine gültige Zeit haben
- Statistik-Aggregation (0.4.9): der neue Reiter „Auswertung“ fasst Ihre Historie wahlweise nach Strecke oder Fahrzeug zusammen — je Zeile Sitzungen, Rennen, Siege, Podium, Zielquote, Ø Bestzeit, Allzeit-Bestzeit, Runden und DNF; über „Details …“ springen Sie in die gefilterte Sitzungsliste, „CSV-Export“ sichert die Tabelle. Der KI-Fahrer-Filter wirkt auch hier
- Korrigierte Rundenzählung (0.4.8): neuere Einzelspieler-Dateien liefern für KI-Fahrer einen fehlerhaften Platzhalter-Wert von stets 856 Runden ohne eine einzige gültige Rundenzeit — die Kachel „Runden gesamt“ zählte dadurch millionenfach zu hoch. Die App zählt nur Runden mit gültiger Zeit; bereits erfasste Sitzungen werden beim Start automatisch bereinigt. Gleichzeitig werden die enthaltenen Rundenzeiten neuer Einzelspieler-Dateien ausgewertet und im Runden-Tab angezeigt
- Korrigierte Statistik (0.4.6): Zielquote berechnet sich als Ziele pro Renneinsatz (zuvor fälschlich pro Sitzung, was bei vielen Fahrern je Rennen Werte über 100 % lieferte); die KI-Fahrer-Ausblendung wirkt jetzt auch auf Statistik-Kacheln und DNF-Tabelle
- Strecken-Id-Auflösung: Einzelspieler-Ergebnisse von RaceRoom nennen die Strecke nur als interne Nummer. Die App übersetzt bekannte Ids automatisch in lesbare Namen (z. B. „Hockenheimring Classic – Grand Prix“); unbekannte Ids ordnen Sie einmalig über „Werkzeuge → Unbekannte Strecken-Ids zuordnen …“ zu – die Zuordnung wird gespeichert und auf alle vorhandenen und künftigen Sitzungen angewendet
- Offizielle Spieldatenbank (0.4.7): unter „Werkzeuge → RaceRoom-Installation wählen …“ hinterlegen Sie einmalig den RaceRoom-Installationsordner (Steam: Bibliothek → RaceRoom Racing Experience → Verwaltung → Verwalten → Lokale Dateien durchsuchen). Die App liest die mit jedem Spielupdate aktualisierte Spieldatenbank `r3e-data.json` und übersetzt damit auch neuere Strecken- und Fahrzeug-Ids automatisch; die Spieldatenbank hat Vorrang vor den eingebauten Tabellen, Ihre eigenen Zuordnungen haben weiterhin obersten Vorrang
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
| `tests/` | 121 Unit-Tests (Parser, Datenbank, Modelle, Einstellungen, Kraftstoff, Id-Auflösung, Icon, Statistik, Spieldatenbank, SP-Runden, Aggregation, KI-Erkennung, Start-Cache, Duplikat-Bereinigung, Diagnose, Rundenzahlen) |

Tests ausführen: `python -m unittest discover -s tests`

Hinweis: Rundendetails (Runden-/Sektorenzeiten) werden erst mit Version 0.3.0 in der Datenbank gespeichert; Sitzungen, die mit 0.2.0 bereits eingelesen wurden, enthalten keine Rundendaten, bis Sie die Datenbank löschen (sie wird beim nächsten Start komplett neu aufgebaut — alle Ergebnisdateien bleiben im RaceRoom-Ordner erhalten).

## Technische Hinweise

- Kernelemente (Parser, Datenbank, Updater) sind Qt-frei und damit unabhängig testbar.
- Duplikaterkennung über MD5-Digest über Datei, Sitzungstyp, Zeit, Strecke, Fahrer, Positionen und Bestzeiten.
- Fehlerhafte oder unvollständige Dateien werden übersprungen und in der Statuszeile als „unlesbar“ gezählt; die App stürzt dadurch nicht ab.

## Geplante Erweiterungen

- Bestzeiten-Vergleich gegen Mitfahrer über mehrere Sitzungen
