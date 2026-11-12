"""RaceRoom Results Companion - GUI entry point.

A standalone companion app for RaceRoom Racing Experience:
- automatically records session results from the local results folder
- session history with full result details, search and filters
- lap-by-lap view with sector times (server results)
- personal best times per track/layout/car + progression chart
- statistics dashboard with finish/DNF analysis
- optional hiding of AI drivers (real-driver list, persisted)
- dark PitBoss-style theme, update check over GitHub Releases

Run: python main.py
"""
import csv
import html
import os
import subprocess
import sys

from PySide6 import QtCore, QtGui, QtWidgets

import updater
from rrc import fuelcalc
from rrc import appsettings
from rrc import trackids
from rrc import icon_gen
from rrc.charts import LineChartWidget
from rrc.database import Database
from rrc.models import APP_NAME, APP_VERSION, delta_class, format_time_ms
from rrc.paths import default_app_dir, default_results_dir, default_db_path
from rrc.theme import apply_dark_theme

COL_SESSIONS = ["Datum", "Typ", "Strecke", "Fahrzeug", "Fahrer", "Bestzeit"]
COL_ENTRIES = ["Pos.", "Fahrer", "Fahrzeug", "Runden ges./gültig", "Beste Runde", "Renzeit", "Status"]
COL_BESTS = ["Fahrer", "Strecke", "Klasse", "Fahrzeug", "Bestzeit", "Fahrten", "Zuletzt"]
COL_LAPS = ["Runde", "Zeit", "Sektor 1", "Sektor 2", "Sektor 3",
            "Delta zur besten", "Delta Rekord"]
COL_DNF = ["Fahrer", "Rennstarts", "DNF", "Zielquote %"]
COL_AGGR_NUM = ["Sitzungen", "Rennen", "Siege", "Podium", "Zielquote %",
                "Ø Bestzeit", "Allzeit-Bestzeit", "Runden", "DNF"]


class UpdateCheckWorker(QtCore.QThread):
    """Update-Pruefung im Hintergrund (blockiert die UI nicht)."""
    result = QtCore.Signal(object, str)

    def run(self):
        try:
            self.result.emit(updater.check_for_update(APP_VERSION), "")
        except Exception as e:
            self.result.emit(None, str(e))


class UpdateDownloadWorker(QtCore.QThread):
    progress = QtCore.Signal(int, int)
    finished_result = QtCore.Signal(str, str)

    def __init__(self, url, dest, parent=None):
        super().__init__(parent)
        self.url = url
        self.dest = dest

    def run(self):
        try:
            updater.download_asset(self.url, self.dest,
                                   progress_cb=lambda d, t: self.progress.emit(int(d), int(t)))
            self.finished_result.emit(self.dest, "")
        except Exception as e:
            self.finished_result.emit("", str(e))


class GenericTableModel(QtCore.QAbstractTableModel):
    def __init__(self, columns, rows, mono_cols=()):
        super().__init__()
        self.columns = columns
        self.rows = rows or []
        self.mono_cols = set(mono_cols)   # Spalten in technischer Schrift

    def rowCount(self, *a):
        return len(self.rows)

    def columnCount(self, *a):
        return len(self.columns)

    def headerData(self, sec, orient, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Horizontal:
            return self.columns[sec]
        return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == QtCore.Qt.DisplayRole:
            return str(self.rows[index.row()][index.column()])
        if role == QtCore.Qt.FontRole and index.column() in self.mono_cols:
            f = QtGui.QFont("Consolas")
            f.setStyleHint(QtGui.QFont.Monospace)
            return f
        return None


class SessionTableModel(GenericTableModel):
    def __init__(self, rows):
        super().__init__(COL_SESSIONS, [], mono_cols=(0, 4, 5))
        self.set_rows(rows)

    def set_rows(self, rows):
        data = []
        for r in rows:
            full = r["track"] + ((" - " + r["layout"]) if r["layout"] else "")
            data.append([r["timestamp"], r["session_type"], full,
                         r["vehicles"] or "–", r["n_players"],
                         format_time_ms(r["session_best_ms"])])
        self.beginResetModel()
        self.rows = data
        self.endResetModel()
        self._raw = list(rows)


class FuelCalculatorDialog(QtWidgets.QDialog):
    """Kraftstoffprognose, nach dem Vorbild des PitBoss-Spritrechners.

    Bedienung: Runden oder Minuten eingeben - das jeweils andere Feld wird
    live mitgerechnet (eines ist die Quelle). Verbrauch pro Runde und
    Tankgroesse werden je Strecke/Fahrzeug in fuel_history.json persistiert.
    """

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kraftstoffrechner")
        self.setMinimumWidth(420)
        self.db = db
        self._updating = False   # verhindert Signal-Schleifen
        self._source = "laps"    # welches Feld zuletzt vom Nutzer editiert wurde

        self.hist_path = fuelcalc.history_path(default_app_dir())
        self.history = fuelcalc.load_history(self.hist_path)

        form = QtWidgets.QFormLayout(self)
        self.cmb_track = QtWidgets.QComboBox()
        self.cmb_vehicle = QtWidgets.QComboBox()
        self.sp_fuel = QtWidgets.QDoubleSpinBox()
        self.sp_fuel.setRange(0.0, 50.0)
        self.sp_fuel.setDecimals(2)
        self.sp_fuel.setSingleStep(0.05)
        self.sp_fuel.setSuffix(" l")
        self.sp_fuel.setMinimumWidth(90)
        self.sp_tank = QtWidgets.QDoubleSpinBox()
        self.sp_tank.setRange(0.0, 500.0)
        self.sp_tank.setDecimals(1)
        self.sp_tank.setSingleStep(5.0)
        self.sp_tank.setSuffix(" l")
        self.sp_tank.setMinimumWidth(90)
        self.sp_laps = QtWidgets.QDoubleSpinBox()
        self.sp_laps.setRange(0.0, 2000.0)
        self.sp_laps.setDecimals(1)
        self.sp_laps.setMinimumWidth(90)
        self.sp_min = QtWidgets.QDoubleSpinBox()
        self.sp_min.setRange(0.0, 1440.0)
        self.sp_min.setDecimals(1)
        self.sp_min.setMinimumWidth(90)

        form.addRow("Strecke:", self.cmb_track)
        form.addRow("Fahrzeug:", self.cmb_vehicle)
        form.addRow("Verbrauch pro Runde:", self.sp_fuel)
        form.addRow("Tankgroesse:", self.sp_tank)
        form.addRow("Runden:", self.sp_laps)
        form.addRow("Minuten:", self.sp_min)

        self.lbl_basis = QtWidgets.QLabel("")
        self.lbl_basis.setWordWrap(True)
        form.addRow(self.lbl_basis)
        self.lbl_result = QtWidgets.QLabel("")
        f = self.lbl_result.font()
        f.setPointSize(f.pointSize() + 3)
        f.setBold(True)
        self.lbl_result.setFont(f)
        form.addRow("Bedarf:", self.lbl_result)
        self.lbl_tank = QtWidgets.QLabel("")
        self.lbl_tank.setWordWrap(True)
        form.addRow(self.lbl_tank)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

        self._load_combos()
        self.cmb_track.currentTextChanged.connect(self._on_track_changed)
        self.cmb_vehicle.currentTextChanged.connect(self._on_vehicle_changed)
        self.sp_fuel.valueChanged.connect(self._recalc)
        self.sp_tank.valueChanged.connect(self._recalc)
        self.sp_laps.valueChanged.connect(lambda _v: self._on_edited("laps"))
        self.sp_min.valueChanged.connect(lambda _v: self._on_edited("minutes"))
        self._on_track_changed()

    # ------------------------------------------------------------ Laden --

    def _load_combos(self):
        self.cmb_track.blockSignals(True)
        self.cmb_track.clear()
        for r in self.db.tracks():
            label = r["track"] + ((f" - {r['layout']}") if r["layout"] else "")
            self.cmb_track.addItem(label, (r["track"], r["layout"]))
        self.cmb_track.blockSignals(False)

    def _current_track(self):
        data = self.cmb_track.currentData()
        return data if data else ("", "")

    def _on_track_changed(self, *_):
        track, _layout = self._current_track()
        vehicles = self.db.vehicles_for_track(track) or [""]
        self.cmb_vehicle.blockSignals(True)
        self.cmb_vehicle.clear()
        self.cmb_vehicle.addItems(vehicles)
        self.cmb_vehicle.blockSignals(False)
        self._on_vehicle_changed()

    def _on_vehicle_changed(self, *_):
        track, layout = self._current_track()
        vehicle = self.cmb_vehicle.currentText()
        entry = fuelcalc.get_entry(self.history, track, vehicle)
        self.sp_fuel.blockSignals(True)
        self.sp_tank.blockSignals(True)
        self.sp_fuel.setValue(float(entry.get("fuel_l", 0.0) or 0.0))
        self.sp_tank.setValue(float(entry.get("capacity", 0.0) or 0.0))
        self.sp_fuel.blockSignals(False)
        self.sp_tank.blockSignals(False)
        self._recalc()

    # ------------------------------------------------------- Rechnung --

    def _current_lap_s(self):
        """Ø Rundenzeit aus der eigenen Historie (DB), in Sekunden."""
        track, layout = self._current_track()
        avg_ms = self.db.avg_lap_ms(track, layout=layout,
                                    vehicle=self.cmb_vehicle.currentText())
        return (avg_ms / 1000.0) if avg_ms else None

    def _on_edited(self, source):
        self._source = source
        self._recalc()

    def _recalc(self, *_):
        if self._updating:
            return
        self._updating = True
        try:
            lap_s = self._current_lap_s()
            fuel_lap = self.sp_fuel.value()
            capacity = self.sp_tank.value()
            laps = self.sp_laps.value()
            minutes = self.sp_min.value()

            if lap_s:
                if self._source == "laps":
                    self.sp_min.setValue(fuelcalc.minutes_from_laps(laps, lap_s))
                else:
                    self.sp_laps.setValue(fuelcalc.laps_from_minutes(minutes, lap_s))
                laps = self.sp_laps.value()
            # ohne Rundenzeit bleiben beide Felder frei editierbar,
            # die Quelle ist dann schlicht die Rundenzahl selbst.

            fuel = fuelcalc.fuel_needed(laps, fuel_lap)
            self.lbl_result.setText(f"{fuel:.2f} l" if fuel else "-")

            if fuel and capacity:
                if fuelcalc.fits_tank(fuel, capacity):
                    self.lbl_tank.setText("Passt in den Tank.")
                    self.lbl_tank.setStyleSheet("color: #4caf50;")
                else:
                    self.lbl_tank.setText("Mehr als der Tank fasst!")
                    self.lbl_tank.setStyleSheet("color: #f44336;")
            else:
                self.lbl_tank.setText("")
                self.lbl_tank.setStyleSheet("")

            if lap_s:
                self.lbl_basis.setText(f"Ø {fuel_lap:.2f} l/Runde · Ø Runde "
                                       f"{format_time_ms(int(lap_s * 1000))} · Quelle: Datenbank")
            else:
                self.lbl_basis.setText("Ø Rundenzeit unbekannt - bitte Runden direkt eingeben.")
        finally:
            self._updating = False

    # ---------------------------------------------------- Persistenz --

    def _save_entry(self):
        track, _layout = self._current_track()
        vehicle = self.cmb_vehicle.currentText()
        if not track or not vehicle:
            return
        fuelcalc.put_entry(self.history, track, vehicle,
                           self.sp_fuel.value(), self.sp_tank.value())
        try:
            fuelcalc.save_history(self.hist_path, self.history)
        except OSError:
            pass

    def accept(self):
        self._save_entry()
        super().accept()

    def reject(self):
        self._save_entry()
        super().reject()

    def closeEvent(self, event):
        self._save_entry()
        super().closeEvent(event)


class LapTableModel(GenericTableModel):
    """Rundentabelle mit farbigen Delta-Zellen (0.4.1)."""

    def __init__(self):
        super().__init__(COL_LAPS, [])
        self.colors = {}

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.ForegroundRole:
            c = self.colors.get((index.row(), index.column()))
            return QtGui.QColor(c) if c else None
        return super().data(index, role)

    def set_rows(self, rows, colors):
        self.beginResetModel()
        self.rows = rows
        self.colors = colors
        self.endResetModel()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1180, 720)

        self.results_dir = default_results_dir()
        self.db_path = default_db_path()
        try:
            self.db = Database(self.db_path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                None, APP_NAME,
                "Die Datenbank konnte nicht geöffnet werden:\n"
                f"{e}\n\n"
                "Läuft die App möglicherweise noch in einem anderen Fenster?\n"
                "Bitte schließen Sie die andere Instanz und starten Sie "
                "erneut.")
            raise SystemExit(1)
        self._last_dir_stamp = None
        self._current_entries = []   # entries of the selected session (for export)
        self._lap_session_rows = {}  # session rows of the laps tab (0.4.1)
        self._lap_records = {}       # track records of the selected laps session
        self.settings_path = appsettings.settings_path(default_app_dir())
        self.settings = appsettings.load_settings(self.settings_path)
        self.user_names_path = trackids.user_names_path(default_app_dir())
        self.user_names = trackids.load_user_names(self.user_names_path)
        self.official = None
        install_dir = self.settings.get("r3e_install_dir") or ""
        if install_dir:
            self.official = trackids.load_official(install_dir)
        self.db.upgrade_ids(self.user_names, self.official)
        self.db.sanitize_laps()
        # 0.4.10: KI-Kennzeichen und Fahrzeugdaten aus den Originaldateien
        # nachtragen (Sitzungen, die vor 0.4.10 ohne Fahrzeug gespeichert
        # wurden) sowie Haken "KI-Fahrer ausblenden" an die Datenbank geben
        self.db.backfill_from_files(self.results_dir)
        self.db.hide_ai = bool(self.settings.get("hide_ai"))
        # 0.4.12: Sitzungs-Duplikate entfernen (entstanden durch verbesserte
        # Id-Aufloesung zwischen Versionen); die juengste Zeile bleibt.
        n_dup = self.db.dedupe_sessions()

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)
        self._build_sessions_tab()
        self._build_laps_tab()
        self._build_bests_tab()
        self._build_stats_tab()
        self._build_aggregate_tab()
        self._build_menu()

        self.lbl_perm = QtWidgets.QLabel("")
        self.statusBar().addPermanentWidget(self.lbl_perm)
        self._update_status_totals()

        self.watch_timer = QtCore.QTimer(self)
        self.watch_timer.setInterval(5000)
        self.watch_timer.timeout.connect(self.check_folder)
        self.watch_timer.start()

        self.lbl_dir.setText(self.results_dir)
        self.chk_hide_ai.blockSignals(True)
        self.chk_hide_ai.setChecked(bool(self.settings.get("hide_ai")))
        self.chk_hide_ai.blockSignals(False)

        # 0.5.0: Live-Recorder (Runden + Kraftstoff aus dem Shared
        # Memory). Laeuft nur, wenn der Haken gesetzt ist; der Zustand
        # bleibt ueber Neustarts erhalten.
        self.recorder = None
        self.record_timer = QtCore.QTimer(self)
        self.record_timer.setInterval(100)
        self.record_timer.timeout.connect(self._recorder_tick)
        self.act_record.blockSignals(True)
        self.act_record.setChecked(bool(self.settings.get("record_laps")))
        self.act_record.blockSignals(False)
        if self.settings.get("record_laps"):
            self.toggle_recording(True)

        self.rescan(silent=True)
        if n_dup:
            self.statusBar().showMessage(
                f"{n_dup} Sitzungs-Duplikate bereinigt — alle Werte "
                "entsprechend korrigiert.", 12000)
        self._auto_check_updates()

    # ------------------------------------------------------------- Tabs --

    def _build_sessions_tab(self):
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)

        top = QtWidgets.QHBoxLayout()
        self.btn_rescan = QtWidgets.QPushButton("Jetzt einlesen")
        self.btn_rescan.setObjectName("primary")
        self.btn_rescan.clicked.connect(self.rescan)
        top.addWidget(self.btn_rescan)
        self.lbl_dir = QtWidgets.QLabel("")
        self.lbl_dir.setStyleSheet("color: #9a9aa4;")
        top.addWidget(self.lbl_dir, 1)
        v.addLayout(top)

        filt = QtWidgets.QHBoxLayout()
        filt.addWidget(QtWidgets.QLabel("Suche:"))
        self.ed_search = QtWidgets.QLineEdit()
        self.ed_search.setPlaceholderText("Strecke, Layout, Sitzungstyp …")
        self.ed_search.textChanged.connect(self.refresh_sessions)
        filt.addWidget(self.ed_search, 1)
        filt.addWidget(QtWidgets.QLabel("Typ:"))
        self.cmb_type = QtWidgets.QComboBox()
        for t in ("Alle", "Race", "Qualify", "Practice"):
            self.cmb_type.addItem(t)
        self.cmb_type.currentTextChanged.connect(self.refresh_sessions)
        filt.addWidget(self.cmb_type)
        filt.addWidget(QtWidgets.QLabel("Fahrer:"))
        self.cmb_driver_sessions = QtWidgets.QComboBox()
        self.cmb_driver_sessions.setMinimumWidth(180)
        self.cmb_driver_sessions.currentTextChanged.connect(self.refresh_sessions)
        filt.addWidget(self.cmb_driver_sessions)
        self.chk_hide_ai = QtWidgets.QCheckBox("KI-Fahrer ausblenden")
        self.chk_hide_ai.setToolTip(
            "Zeigt nur die unter 'Werkzeuge → Echte Fahrer festlegen …' "
            "eingetragenen Fahrer")
        self.chk_hide_ai.toggled.connect(self.on_hide_ai_toggled)
        filt.addWidget(self.chk_hide_ai)
        v.addLayout(filt)

        # Zweite Filterzeile (0.4.5): Datum von/bis, Strecke, Fahrzeug
        filt2 = QtWidgets.QHBoxLayout()
        self.chk_date = QtWidgets.QCheckBox("Datum:")
        self.chk_date.toggled.connect(self.refresh_sessions)
        filt2.addWidget(self.chk_date)
        self.dte_from = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.dte_from.setCalendarPopup(True)
        self.dte_from.setDisplayFormat("dd.MM.yyyy")
        self.dte_from.setEnabled(False)
        self.dte_from.dateChanged.connect(self.refresh_sessions)
        filt2.addWidget(self.dte_from)
        filt2.addWidget(QtWidgets.QLabel("bis"))
        self.dte_to = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.dte_to.setCalendarPopup(True)
        self.dte_to.setDisplayFormat("dd.MM.yyyy")
        self.dte_to.setEnabled(False)
        self.dte_to.dateChanged.connect(self.refresh_sessions)
        filt2.addWidget(self.dte_to)
        # 0.5.1: Kalender-Aufklappmenü überarbeitet (Marcels Screenshot:
        # zweistellige Tageszahlen ab 10 waren abgeschnitten, Kontrast
        # zu schwach). Der Kalender erhält eine feste Mindestgröße, damit
        # jede Spalte zweistellige Zahlen sicher fasst, plus reinweiße
        # fette Tageszahlen, kräftig rote Wochenenden, gelbes „Heute“
        # und (per QSS, rrc/theme.py) RaceRoom-Rot als Auswahl-Markierung.
        for _dte in (self.dte_from, self.dte_to):
            _cal = _dte.calendarWidget()
            if _cal is not None:
                self._style_calendar(_cal)
        self.chk_date.toggled.connect(self._toggle_date_filter)
        filt2.addSpacing(12)
        filt2.addWidget(QtWidgets.QLabel("Strecke:"))
        self.cmb_track_filter = QtWidgets.QComboBox()
        self.cmb_track_filter.setMinimumWidth(170)
        self.cmb_track_filter.currentTextChanged.connect(self.refresh_sessions)
        filt2.addWidget(self.cmb_track_filter)
        filt2.addWidget(QtWidgets.QLabel("Fahrzeug:"))
        self.cmb_vehicle_filter = QtWidgets.QComboBox()
        self.cmb_vehicle_filter.setMinimumWidth(170)
        self.cmb_vehicle_filter.currentTextChanged.connect(self.refresh_sessions)
        filt2.addWidget(self.cmb_vehicle_filter)
        filt2.addStretch(1)
        v.addLayout(filt2)

        self.tbl_sessions = QtWidgets.QTableView()
        self.tbl_sessions.setAlternatingRowColors(False)
        self.sess_model = SessionTableModel([])
        self.tbl_sessions.setModel(self.sess_model)
        self.tbl_sessions.setSelectionBehavior(QtWidgets.QTableView.SelectRows)
        self.tbl_sessions.setSelectionMode(QtWidgets.QTableView.SingleSelection)
        self.tbl_sessions.horizontalHeader().setStretchLastSection(True)
        self.tbl_sessions.setColumnWidth(0, 150)
        self.tbl_sessions.setColumnWidth(2, 320)
        self.tbl_sessions.selectionModel().selectionChanged.connect(self.on_session_selected)
        v.addWidget(self.tbl_sessions, 1)

        lbl_detail = QtWidgets.QLabel("Ergebnisdetails:")
        lbl_detail.setObjectName("sectionTitle")
        v.addWidget(lbl_detail)
        self.tbl_entries = QtWidgets.QTableView()
        self.tbl_entries.setAlternatingRowColors(False)
        self.entries_model = GenericTableModel(COL_ENTRIES, [],
                                              mono_cols=(0, 3, 4, 5))
        self.tbl_entries.setModel(self.entries_model)
        self.tbl_entries.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_entries, 1)

        exp = QtWidgets.QHBoxLayout()
        self.btn_csv = QtWidgets.QPushButton("Auswahl als CSV exportieren …")
        self.btn_csv.clicked.connect(self.export_csv)
        exp.addWidget(self.btn_csv)
        self.btn_html = QtWidgets.QPushButton("Auswahl als HTML exportieren …")
        self.btn_html.clicked.connect(self.export_html)
        exp.addWidget(self.btn_html)
        exp.addStretch(1)
        v.addLayout(exp)
        self.tabs.addTab(page, "Sitzungen")

    def _build_laps_tab(self):
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Sitzung:"))
        self.cmb_lap_session = QtWidgets.QComboBox()
        self.cmb_lap_session.setMinimumWidth(420)
        self.cmb_lap_session.currentIndexChanged.connect(self.on_lap_session_changed)
        row.addWidget(self.cmb_lap_session)
        row.addWidget(QtWidgets.QLabel("Fahrer:"))
        self.cmb_lap_driver = QtWidgets.QComboBox()
        self.cmb_lap_driver.setMinimumWidth(200)
        self.cmb_lap_driver.currentIndexChanged.connect(self.on_lap_driver_changed)
        row.addWidget(self.cmb_lap_driver)
        row.addStretch(1)
        v.addLayout(row)
        self.lbl_laps_hint = QtWidgets.QLabel(
            "Runden- und Sektorenzeiten stehen nur in Dedicated-Server- und "
            "Multiplayer-Ergebnissen zur Verfügung.")
        self.lbl_laps_hint.setObjectName("hint")
        v.addWidget(self.lbl_laps_hint)

        # Rekord-Kacheln fuer die Strecke der gewaehlten Sitzung (0.4.1);
        # ab 0.4.10 je Fahrzeugklasse eine eigene Kachelreihe
        self.rec_tile_container = QtWidgets.QVBoxLayout()
        v.addLayout(self.rec_tile_container)
        self.rec_tiles = {}
        self._class_tiles = {}
        self._render_record_tiles([(None, self.db.track_records("", ""))])

        self.tbl_laps = QtWidgets.QTableView()
        self.tbl_laps.setAlternatingRowColors(False)
        self.laps_model = LapTableModel()
        self.laps_model.mono_cols = set(range(len(COL_LAPS)))
        self.tbl_laps.setModel(self.laps_model)
        self.tbl_laps.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_laps, 1)
        self.tabs.addTab(page, "Runden")

    def _build_bests_tab(self):
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        combo_row = QtWidgets.QHBoxLayout()
        lbl_driver = QtWidgets.QLabel("Fahrer:")
        lbl_driver.setObjectName("sectionTitle")
        combo_row.addWidget(lbl_driver)
        self.cmb_driver = QtWidgets.QComboBox()
        self.cmb_driver.setMinimumWidth(220)
        self.cmb_driver.currentTextChanged.connect(self.on_driver_changed_full)
        combo_row.addWidget(self.cmb_driver)
        combo_row.addStretch(1)
        v.addLayout(combo_row)
        self.tbl_bests = QtWidgets.QTableView()
        self.tbl_bests.setAlternatingRowColors(False)
        self.bests_model = GenericTableModel(COL_BESTS, [], mono_cols=(4, 5, 6))
        self.tbl_bests.setModel(self.bests_model)
        self.tbl_bests.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_bests, 1)
        self.lbl_stats = QtWidgets.QLabel("")
        self.lbl_stats.setObjectName("hint")
        v.addWidget(self.lbl_stats)
        self.tabs.addTab(page, "Bestzeiten")

    def _build_stats_tab(self):
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)

        # Dashboard-Kacheln
        grid = QtWidgets.QHBoxLayout()
        self.tiles = {}
        for key in ("Rennen", "Siege", "Podium", "Zielquote %", "Runden gesamt", "Allzeit-Bestzeit"):
            box = QtWidgets.QFrame()
            box.setFixedHeight(74)
            box.setStyleSheet(
                "QFrame { background: #202027; border: 1px solid #33333d; }")
            lay = QtWidgets.QVBoxLayout(box)
            k = QtWidgets.QLabel(key)
            k.setStyleSheet("color: #9a9aa4; font-size: 11px; font-weight: 700; "
                            "background: transparent;")
            val = QtWidgets.QLabel("–")
            is_rec = key == "Allzeit-Bestzeit"
            val.setStyleSheet(
                "color: %s; font-size: 19px; font-weight: 800; "
                "background: transparent;" % ("#e8c34a" if is_rec else "#e8e8ec"))
            lay.addWidget(k)
            lay.addWidget(val)
            grid.addWidget(box)
            self.tiles[key] = val
        v.addLayout(grid)

        # Diagramm
        chart_row = QtWidgets.QHBoxLayout()
        chart_row.addWidget(QtWidgets.QLabel("Strecke:"))
        self.cmb_chart_track = QtWidgets.QComboBox()
        self.cmb_chart_track.setMinimumWidth(320)
        self.cmb_chart_track.currentIndexChanged.connect(self.on_chart_changed)
        chart_row.addWidget(self.cmb_chart_track)
        chart_row.addStretch(1)
        v.addLayout(chart_row)
        self.chart = LineChartWidget()
        v.addWidget(self.chart, 1)

        # Unfall-/Ausfall-Analyse
        lbl_dnf = QtWidgets.QLabel("Unfälle & Ausfälle (nur Rennen):")
        lbl_dnf.setObjectName("sectionTitle")
        v.addWidget(lbl_dnf)
        self.tbl_dnf = QtWidgets.QTableView()
        self.tbl_dnf.setAlternatingRowColors(False)
        self.dnf_model = GenericTableModel(COL_DNF, [], mono_cols=(1, 2, 3))
        self.tbl_dnf.setModel(self.dnf_model)
        self.tbl_dnf.horizontalHeader().setStretchLastSection(True)
        self.tbl_dnf.setMaximumHeight(190)
        v.addWidget(self.tbl_dnf)
        self.tabs.addTab(page, "Statistik")

    def _build_aggregate_tab(self):
        """Reiter Auswertung (0.4.9): Historie je Strecke/Fahrzeug."""
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)

        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Gruppierung:"))
        self.cmb_aggr = QtWidgets.QComboBox()
        self.cmb_aggr.addItems(["nach Strecke", "nach Fahrzeug",
                                "nach Fahrzeugklasse"])
        self.cmb_aggr.currentIndexChanged.connect(self.refresh_aggregate)
        row.addWidget(self.cmb_aggr)
        btn_details = QtWidgets.QPushButton("Details …")
        btn_details.clicked.connect(self.show_aggregate_details)
        row.addWidget(btn_details)
        self.btn_aggr_details = btn_details
        btn_csv = QtWidgets.QPushButton("CSV-Export")
        btn_csv.clicked.connect(self.export_aggregate_csv)
        row.addWidget(btn_csv)
        row.addStretch(1)
        v.addLayout(row)

        self.tbl_aggr = QtWidgets.QTableView()
        self.tbl_aggr.setAlternatingRowColors(False)
        self.tbl_aggr.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl_aggr.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.aggr_model = GenericTableModel(["Strecke"] + COL_AGGR_NUM, [],
                                            mono_cols=tuple(range(1, 10)))
        self.tbl_aggr.setModel(self.aggr_model)
        self.tbl_aggr.horizontalHeader().setStretchLastSection(True)
        self.tbl_aggr.setColumnWidth(0, 380)
        v.addWidget(self.tbl_aggr)
        self.tabs.addTab(page, "Auswertung")

    def refresh_aggregate(self, *_):
        """Auswertungstabelle entsprechend der Gruppierung neu aufbauen."""
        text = self.cmb_aggr.currentText()
        by = {"nach Strecke": "track",
              "nach Fahrzeugklasse": "class"}.get(text, "vehicle")
        rows = self.db.aggregate(by, names=self._name_filter())
        cols = [{"track": "Strecke", "vehicle": "Fahrzeug",
                 "class": "Klasse"}[by]] + COL_AGGR_NUM
        data = []
        for r in rows:
            data.append([
                r["label"], r["sessions"], r["races"], r["wins"], r["podium"],
                f"{r['quote']:.1f} %".replace(".", ","),
                format_time_ms(r["avg_best_ms"]) or "–",
                format_time_ms(r["best_ms"]) or "–",
                r["total_laps"], r["dnfs"]])
        self.aggr_model.beginResetModel()
        self.aggr_model.columns = cols
        self.aggr_model.rows = data
        self.aggr_model.endResetModel()
        self._aggr_raw = rows
        self._aggr_by = by
        # "Details …" nur fuer Gruppierungen mit Sitzungs-Filter sinnvoll
        self.btn_aggr_details.setEnabled(by in ("track", "vehicle"))

    def show_aggregate_details(self):
        """Gewaehlte Gruppe im Sitzungs-Reiter filtern."""
        sel = self.tbl_aggr.selectionModel().selectedRows()
        if not sel:
            QtWidgets.QMessageBox.information(
                self, "Details",
                "Bitte wählen Sie zuerst eine Zeile aus.")
            return
        r = self._aggr_raw[sel[0].row()]
        self.tabs.setCurrentIndex(0)
        if self._aggr_by == "track":
            self.ed_search.setText(r["label"].split(" - ")[0])
            self.cmb_vehicle_filter.setCurrentIndex(0)
        else:
            self.ed_search.setText("")
            idx = max(0, self.cmb_vehicle_filter.findText(r["label"]))
            self.cmb_vehicle_filter.setCurrentIndex(idx)
        self.refresh_sessions()

    def export_aggregate_csv(self):
        """Auswertungstabelle als CSV (Semikolon, utf-8-sig) sichern."""
        if not self.aggr_model.rows:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Auswertung exportieren",
            os.path.join(default_app_dir(), "Auswertung.csv"), "*.csv")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(self.aggr_model.columns)
                w.writerows(self.aggr_model.rows)
        except OSError as e:
            QtWidgets.QMessageBox.warning(
                self, "Export", f"Export fehlgeschlagen: {e}")
            return
        self.statusBar().showMessage(f"CSV exportiert: {path}", 8000)

    def _build_menu(self):
        m = self.menuBar().addMenu("&Datei")
        act_settings = QtGui.QAction("Ergebnis-Ordner wählen …", self)
        act_settings.triggered.connect(self.choose_folder)
        m.addAction(act_settings)
        act_refresh = QtGui.QAction("Neu einlesen", self)
        act_refresh.triggered.connect(self.rescan)
        m.addAction(act_refresh)
        m.addSeparator()
        act_quit = QtGui.QAction("Beenden", self)
        act_quit.triggered.connect(self.close)
        m.addAction(act_quit)

        mw = self.menuBar().addMenu("&Werkzeuge")
        act_fuel = QtGui.QAction("Kraftstoffrechner …", self)
        act_fuel.triggered.connect(self.open_fuel_calculator)
        mw.addAction(act_fuel)
        act_drivers = QtGui.QAction("Echte Fahrer festlegen …", self)
        act_drivers.triggered.connect(self.edit_real_drivers)
        mw.addAction(act_drivers)
        act_ids = QtGui.QAction("Unbekannte Strecken-Ids zuordnen …", self)
        act_ids.triggered.connect(self.assign_track_ids)
        mw.addAction(act_ids)
        act_r3e = QtGui.QAction("RaceRoom-Installation wählen …", self)
        act_r3e.triggered.connect(self.choose_raceroom_install)
        mw.addAction(act_r3e)
        act_diag = QtGui.QAction("Diagnose exportieren …", self)
        act_diag.triggered.connect(self.export_diagnostics)
        mw.addAction(act_diag)
        mw.addSeparator()
        self.act_record = QtGui.QAction("Runden live aufzeichnen", self)
        self.act_record.setCheckable(True)
        self.act_record.toggled.connect(self.toggle_recording)
        mw.addAction(self.act_record)

        mh = self.menuBar().addMenu("&Hilfe")
        act_update = QtGui.QAction("Nach Updates suchen …", self)
        act_update.triggered.connect(self.check_updates_manual)
        mh.addAction(act_update)
        act_about = QtGui.QAction(f"Über {APP_NAME}", self)
        act_about.triggered.connect(self.show_about)
        mh.addAction(act_about)

    # ------------------------------------------------------------- Logic --

    def toggle_recording(self, on):
        """0.5.0: Live-Aufzeichnung ein-/ausschalten (Werkzeuge-Menu)."""
        self.settings["record_laps"] = bool(on)
        self._save_settings()
        if on:
            if self.recorder is None:
                try:
                    from rrc.recorder import LapRecorder
                    self.recorder = LapRecorder(default_app_dir())
                except Exception as e:
                    self.act_record.blockSignals(True)
                    self.act_record.setChecked(False)
                    self.act_record.blockSignals(False)
                    QtWidgets.QMessageBox.warning(
                        self, APP_NAME,
                        "Die Live-Aufzeichnung konnte nicht gestartet "
                        f"werden:\n{e}")
                    return
            self.record_timer.start()
            self.statusBar().showMessage(
                "Live-Aufzeichnung aktiv — bitte RaceRoom jetzt starten "
                "bzw. weiterfahren.", 10000)
        else:
            self.record_timer.stop()
            if self.recorder is not None:
                self.recorder.close()
                self.recorder = None
            self.statusBar().showMessage(
                "Live-Aufzeichnung beendet.", 8000)

    def _recorder_tick(self):
        """Timer-Rückruf (10 Hz): ein Shared-Memory-Lesevorgang."""
        if self.recorder is None:
            self.record_timer.stop()
            return
        status, msg = self.recorder.tick()
        if status == "error" and msg:
            # Reader-Fehler nur periodisch und dezent melden.
            self.statusBar().showMessage(msg, 4000)
        elif msg:
            self.statusBar().showMessage(msg, 6000)

    def open_fuel_calculator(self):
        dlg = FuelCalculatorDialog(self.db, self)
        dlg.exec()

    def _dir_stamp(self):
        try:
            names = [n for n in os.listdir(self.results_dir)
                     if n.lower().endswith((".txt", ".json", ".xml"))]
            return tuple(sorted((n, os.path.getmtime(os.path.join(self.results_dir, n)))
                                for n in names))
        except OSError:
            return None

    def check_folder(self):
        stamp = self._dir_stamp()
        if stamp != self._last_dir_stamp:
            self._last_dir_stamp = stamp
            self.rescan(silent=True)

    def rescan(self, silent=False):
        added, skipped, errors = self.db.ingest_folder(self.results_dir)
        self._last_dir_stamp = self._dir_stamp()
        self.refresh()
        self._update_status_totals()
        if not silent or added:
            self.statusBar().showMessage(
                f"Neu: {added} Sitzungen, bekannt: {skipped}, "
                f"unlesbar: {errors} ({self.results_dir})", 10000)

    def _update_status_totals(self):
        """Daueranzeige in der Statusleiste (Sitzungen/Runden/Datenbank)."""
        try:
            n_s, n_l = self.db.totals()
            self.lbl_perm.setText(
                f"{n_s} Sitzungen · {n_l} Runden erfasst · "
                f"Datenbank: {os.path.basename(self.db_path)}")
        except Exception:
            self.lbl_perm.setText("")

    def refresh(self):
        self._reload_driver_boxes()
        self.refresh_sessions()
        self._reload_lap_sessions()
        self.on_driver_changed_full(self.cmb_driver.currentText())
        self._reload_tracks()
        self._reload_filter_combos()
        self.refresh_aggregate()

    def _driver_names(self):
        return self.db.drivers(names=self._name_filter())

    def _reload_driver_boxes(self):
        names = self._driver_names()
        for combo, prev in ((self.cmb_driver, self.cmb_driver.currentText()),
                            (self.cmb_driver_sessions, self.cmb_driver_sessions.currentText())):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("(alle Fahrer)")
            for n in names:
                combo.addItem(n)
            combo.setCurrentIndex(max(0, combo.findText(prev)) if prev else 0)
            combo.blockSignals(False)

    def refresh_sessions(self, *_):
        search = self.ed_search.text().strip()
        type_sel = self.cmb_type.currentText()
        type_ = "" if type_sel in ("", "Alle") else type_sel
        driver = self.cmb_driver_sessions.currentText()
        driver = "" if driver.startswith("(") else driver
        date_from = date_to = ""
        if self.chk_date.isChecked():
            date_from = self.dte_from.date().toString("yyyy-MM-dd")
            date_to = self.dte_to.date().toString("yyyy-MM-dd")
        track = self.cmb_track_filter.currentText()
        track = "" if track.startswith("(") else track
        vehicle = self.cmb_vehicle_filter.currentText()
        vehicle = "" if vehicle.startswith("(") else vehicle
        rows = self.db.sessions(search=search, session_type=type_, driver=driver,
                                names=self._name_filter(), date_from=date_from,
                                date_to=date_to, track=track, vehicle=vehicle)
        self.sess_model.set_rows(rows)

    def _toggle_date_filter(self, checked):
        self.dte_from.setEnabled(checked)
        self.dte_to.setEnabled(checked)

    def _style_calendar(self, cal):
        """0.5.1: Kalender lesbar machen (Kontrast, Größe, „Heute“)."""
        cal.setVerticalHeaderFormat(QtWidgets.QCalendarWidget.ISOWeekNumbers)
        cal.setHorizontalHeaderFormat(QtWidgets.QCalendarWidget.ShortDayNames)
        # Mindestgröße: jede Tagesspalte muss zweistellige Zahlen fassen
        # (Marcels Screenshot: „10“ ff. waren abgeschnitten).
        cal.setMinimumSize(330, 250)
        cal.setFont(QtGui.QFont("Segoe UI", 10))
        # Werktage reinweiß und fett, Wochenende kräftig hellrot
        _wk = QtGui.QTextCharFormat()
        _wk.setForeground(QtGui.QColor("#ffffff"))
        _wk.setFontWeight(QtGui.QFont.Bold)
        _wknd = QtGui.QTextCharFormat()
        _wknd.setForeground(QtGui.QColor("#ff5a63"))
        _wknd.setFontWeight(QtGui.QFont.Bold)
        for _day in (QtCore.Qt.Monday, QtCore.Qt.Tuesday, QtCore.Qt.Wednesday,
                     QtCore.Qt.Thursday, QtCore.Qt.Friday):
            cal.setWeekdayTextFormat(_day, _wk)
        for _day in (QtCore.Qt.Saturday, QtCore.Qt.Sunday):
            cal.setWeekdayTextFormat(_day, _wknd)
        # Kopfzeile (Wochentage/Kalenderwochen) hell und lesbar
        _head = QtGui.QTextCharFormat()
        _head.setForeground(QtGui.QColor("#c9c9d2"))
        _head.setFontWeight(QtGui.QFont.DemiBold)
        cal.setHeaderTextFormat(_head)
        # „Heute“: gelbe, fette Zahl (Rahmen stellt QTextCharFormat nicht bereit)
        _today = QtGui.QTextCharFormat()
        _today.setForeground(QtGui.QColor("#e8c34a"))
        _today.setFontWeight(QtGui.QFont.Bold)
        cal.setDateTextFormat(QtCore.QDate.currentDate(), _today)

    def _reload_filter_combos(self):
        """Strecken-/Fahrzeug-Filter neu laden, Auswahl möglichst behalten."""
        seen = []
        for r in self.db.tracks():
            if r["track"] and r["track"] not in seen:
                seen.append(r["track"])
        for combo, values in ((self.cmb_track_filter, seen),
                              (self.cmb_vehicle_filter, self.db.vehicles())):
            prev = combo.currentText()
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("(alle Strecken)" if combo is self.cmb_track_filter
                          else "(alle Fahrzeuge)")
            combo.addItems(values)
            combo.setCurrentIndex(max(0, combo.findText(prev)) if prev else 0)
            combo.blockSignals(False)

    def _session_label(self, r):
        full = r["track"] + ((" - " + r["layout"]) if r["layout"] else "")
        return f"{r['timestamp']} · {r['session_type']} · {full}"

    def on_session_selected(self, *_):
        indexes = self.tbl_sessions.selectionModel().selectedRows()
        if not indexes:
            self._current_entries = []
            return
        row = self.sess_model._raw[indexes[0].row()]
        self._current_entries = [dict(e) for e in
                                  self.db.entries_for(row["id"],
                                                       names=self._name_filter())]
        rows = []
        for e in self._current_entries:
            # 0.4.13: 'gesamt / gueltig', wenn die Datei mehr Runden
            # angibt als gueltige Rundenzeiten enthielt (SP-Format).
            tot = e["total_laps"] if "total_laps" in e.keys() else -1
            lapcell = (f"{tot} / {e['laps']}"
                       if tot is not None and tot > e["laps"] else e["laps"])
            rows.append([e["position"], e["name"], e["vehicle"], lapcell,
                         format_time_ms(e["best_lap_ms"]),
                         format_time_ms(e["race_time_ms"]),
                         e["finish_status"] or ("Finished" if e["position"] else "")])
        self.entries_model.beginResetModel()
        self.entries_model.rows = rows
        self.entries_model.endResetModel()

    # ------------------------------------------------------------- Runden --

    def _reload_lap_sessions(self):
        cur = self.cmb_lap_session.currentText()
        self.cmb_lap_session.blockSignals(True)
        self.cmb_lap_session.clear()
        self._lap_session_rows = {}
        for r in self.db.sessions_with_laps():
            self.cmb_lap_session.addItem(self._session_label(r), userData=r["id"])
            self._lap_session_rows[r["id"]] = r
        if cur:
            idx = self.cmb_lap_session.findText(cur)
            if idx >= 0:
                self.cmb_lap_session.setCurrentIndex(idx)
        self.cmb_lap_session.blockSignals(False)
        self.on_lap_session_changed()

    def _render_record_tiles(self, entries):
        """Rekord-Kacheln (0.4.10) neu aufbauen: je Eintrag
        (Klassen-Caption oder None, rec-dict) eine Kachelreihe."""
        def clear(layout):
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.deleteLater()
                elif item.layout():
                    clear(item.layout())

        clear(self.rec_tile_container)
        self.rec_tiles = {}
        self._class_tiles = {}
        for caption, rec in entries:
            if caption:
                lbl = QtWidgets.QLabel(f"Klasse: {caption}")
                lbl.setStyleSheet(
                    "color: #9a9aa4; font-size: 11px; font-weight: 700; "
                    "background: transparent;")
                self.rec_tile_container.addWidget(lbl)
            row = QtWidgets.QHBoxLayout()
            tiles = {}
            for key in ("Renn-Rekord", "Quali-Rekord", "Optimal-Runde",
                        "Allzeit-Bestzeit"):
                box = QtWidgets.QFrame()
                box.setFixedHeight(64)
                box.setStyleSheet(
                    "QFrame { background: #202027; "
                    "border: 1px solid #33333d; }")
                lay = QtWidgets.QVBoxLayout(box)
                k = QtWidgets.QLabel(key)
                k.setStyleSheet(
                    "color: #9a9aa4; font-size: 11px; font-weight: 700; "
                    "background: transparent;")
                val = QtWidgets.QLabel("–")
                is_rec = key in ("Renn-Rekord", "Allzeit-Bestzeit")
                val.setStyleSheet(
                    "color: %s; font-size: 17px; font-weight: 800; "
                    "background: transparent;"
                    % ("#e8c34a" if is_rec else "#e8e8ec"))
                lay.addWidget(k)
                lay.addWidget(val)
                row.addWidget(box)
                tiles[key] = val
                if caption is None:
                    self.rec_tiles[key] = val
            row.addStretch(1)
            self.rec_tile_container.addLayout(row)
            self._class_tiles[caption] = tiles
            field = {"Renn-Rekord": "race_ms", "Quali-Rekord": "qualify_ms",
                     "Optimal-Runde": "optimal_ms",
                     "Allzeit-Bestzeit": "best_ms"}
            for key, val in tiles.items():
                val.setText(format_time_ms(rec.get(field[key])) or "–")

    def on_lap_session_changed(self, *_):
        sid = self.cmb_lap_session.currentData()
        # Rekord-Kacheln fuer die Strecke der gewaehlten Sitzung (0.4.1);
        # ab 0.4.10 je Fahrzeugklasse eine eigene Kachelreihe
        row = self._lap_session_rows.get(sid)
        if not row:
            self._render_record_tiles([(
                None, {"race_ms": None, "qualify_ms": None,
                       "best_ms": None, "optimal_ms": None})])
            self._lap_records = {}
        else:
            classes = self.db.track_classes(row["track"], row["layout"])
            if len(classes) <= 1:
                rec = self.db.track_records(row["track"], row["layout"])
                self._render_record_tiles([(None, rec)])
                self._lap_records = rec
            else:
                rows = []
                for c in classes:
                    rows.append((c, self.db.track_records(
                        row["track"], row["layout"], c)))
                self._render_record_tiles(rows)
                # Deltas bleiben gegen den Strecken-Rekord aller Klassen
                self._lap_records = self.db.track_records(
                    row["track"], row["layout"])

        self.cmb_lap_driver.blockSignals(True)
        self.cmb_lap_driver.clear()
        if sid is not None:
            for e in self.db.entries_for(sid, names=self._name_filter()):
                self.cmb_lap_driver.addItem(e["name"], userData=e["id"])
        self.cmb_lap_driver.blockSignals(False)
        self.on_lap_driver_changed()

    def on_lap_driver_changed(self, *_):
        sid = self.cmb_lap_session.currentData()
        eid = self.cmb_lap_driver.currentData()
        rows = []
        colors = {}
        rec = getattr(self, "_lap_records", {}) or {}
        record_ms = rec.get("best_ms") or 0
        if sid is not None and eid is not None:
            laps = [dict(l) for l in self.db.laps_for_session(sid) if l["entry_id"] == eid]
            # 0.4.14: Ungueltige Runden (lap_time_ms <= 0, z. B. Platzhalter
            # in SP-Dateien) anzeigen, aber rot kennzeichnen und von den
            # Bestwert-Berechnungen ausnehmen.
            # 0.5.0: Live gemessene ungueltige Runden (valid = 0) zaehlen
            # ebenfalls nicht als Bestwert, obwohl sie eine Zeit tragen.
            best = min((l["lap_time_ms"] for l in laps
                        if l["lap_time_ms"] > 0 and l.get("valid", 1)),
                       default=0)
            for i, l in enumerate(laps):
                invalid = (l["lap_time_ms"] <= 0
                           or (not l.get("valid", 1) and l["lap_time_ms"] > 0))
                if invalid:
                    # 0.5.0: Ungueltige Runden mit live gemessener Zeit
                    # zeigen die gemessene Zeit in Rot, ansonsten "–".
                    t_txt = (format_time_ms(l["lap_time_ms"])
                             if l["lap_time_ms"] > 0 else "–")
                    rows.append([l["lap_no"], t_txt,
                                 format_time_ms(l["s1_ms"]),
                                 format_time_ms(l["s2_ms"]),
                                 format_time_ms(l["s3_ms"]),
                                 "ungültig", "–"])
                    colors[(i, 0)] = "#f44336"     # Rundennr. rot
                    colors[(i, 1)] = "#f44336"     # Zeit rot
                    colors[(i, 5)] = "#f44336"     # Kennzeichnung rot
                    continue
                delta = l["lap_time_ms"] - best if best else 0
                sign = "+" if delta > 0 else ""
                d_rec = l["lap_time_ms"] - record_ms if record_ms else None
                rec_txt = ("-" if d_rec is None else
                           ("+" + f"{d_rec / 1000.0:.3f}" if d_rec > 0
                            else f"{d_rec / 1000.0:.3f}"))
                rows.append([l["lap_no"], format_time_ms(l["lap_time_ms"]),
                             format_time_ms(l["s1_ms"]), format_time_ms(l["s2_ms"]),
                             format_time_ms(l["s3_ms"]),
                             "beste" if delta == 0 else f"{sign}{delta / 1000.0:.3f}",
                             rec_txt])
                if delta == 0:
                    colors[(i, 1)] = "#4caf50"     # beste Runde der Sitzung
                    colors[(i, 5)] = "#4caf50"
                cls = delta_class(d_rec, record_ms)
                if cls == "good":
                    colors[(i, 6)] = "#4caf50"     # schneller als der Rekord
                elif cls == "near":
                    colors[(i, 6)] = "#e8c34a"     # nah dran (innerhalb 2 %)
                elif cls == "bad":
                    colors[(i, 6)] = "#f44336"     # Ausrutscher (ueber 2 s)
        self.laps_model.set_rows(rows, colors)

    # ------------------------------------------------------------- Export --

    def _selected_session(self):
        indexes = self.tbl_sessions.selectionModel().selectedRows()
        if not indexes:
            return None, None
        row = self.sess_model._raw[indexes[0].row()]
        return row, self.db.entries_for(row["id"], names=self._name_filter())

    def _export_path(self, suffix):
        row, entries = self._selected_session()
        if row is None:
            QtWidgets.QMessageBox.information(
                self, "Export", "Bitte wählen Sie zuerst eine Sitzung aus.")
            return None, None, None
        full = row["track"] + ((" - " + row["layout"]) if row["layout"] else "")
        suggestion = f"{row['timestamp'].replace(':', '')}_{full}_{row['session_type']}{suffix}"
        suggestion = "".join(c if c not in '\\/:*?"<>|' else "_" for c in suggestion)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export speichern", os.path.join(
                default_app_dir(), suggestion), f"*{suffix}")
        return row, entries, path

    def export_csv(self):
        row, entries, path = self._export_path(".csv")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["Position", "Fahrer", "Fahrzeug", "Team", "Runden",
                            "Beste Runde", "Renzeit", "Status"])
                for e in entries:
                    w.writerow([e["position"], e["name"], e["vehicle"], e["team"],
                                e["laps"], format_time_ms(e["best_lap_ms"]),
                                format_time_ms(e["race_time_ms"]),
                                e["finish_status"] or ""])
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "Export", f"Export fehlgeschlagen: {e}")
            return
        self.statusBar().showMessage(f"CSV exportiert: {path}", 8000)

    def export_html(self):
        row, entries, path = self._export_path(".html")
        if not path:
            return
        full = row["track"] + ((" - " + row["layout"]) if row["layout"] else "")
        lines = [
            "<!DOCTYPE html><html><head><meta charset='utf-8'>",
            f"<title>R3E Resultate – {html.escape(full)}</title>",
            "<style>body{font-family:Segoe UI,Arial;background:#0c0c0e;color:#f1f1f3;"
            "margin:24px}h1{font-size:20px}table{border-collapse:collapse;margin-top:12px}"
            "th,td{border:1px solid #34343c;padding:6px 12px;text-align:left}"
            "th{background:#1a1a1f;color:#8f8f99}tr:nth-child(even){background:#131316}"
            "</style></head><body>",
            f"<h1>{html.escape(full)} – {html.escape(row['session_type'])}</h1>",
            f"<p>{html.escape(row['timestamp'])} · Quelle: {html.escape(row['source_file'])}</p>",
            "<table><tr><th>Pos.</th><th>Fahrer</th><th>Fahrzeug</th><th>Runden</th>"
            "<th>Beste Runde</th><th>Renzeit</th><th>Status</th></tr>"]
        for e in entries:
            lines.append(
                "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>".format(
                    e["position"], html.escape(e["name"]), html.escape(e["vehicle"]),
                    e["laps"], format_time_ms(e["best_lap_ms"]),
                    format_time_ms(e["race_time_ms"]),
                    html.escape(e["finish_status"] or "Finished" if e["position"] else "")))
        lines.append("</table></body></html>")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError as e:
            QtWidgets.QMessageBox.warning(self, "Export", f"Export fehlgeschlagen: {e}")
            return
        self.statusBar().showMessage(f"HTML exportiert: {path}", 8000)

    # --------------------------------------------------------- Bestzeiten --

    def on_driver_changed(self, name):
        driver = "" if name.startswith("(") else name
        rows = []
        for r in self.db.personal_bests(driver, names=self._name_filter()):
            rows.append([r["name"], (r["track"] + ((" - " + r["layout"]) if r["layout"] else "")),
                         r["vehicle_class"] or "–", r["vehicle"],
                         format_time_ms(r["best_ms"]), r["n"], r["last_seen"]])
        self.bests_model.beginResetModel()
        self.bests_model.rows = rows
        self.bests_model.endResetModel()

    def _reload_tracks(self):
        cur = self.cmb_chart_track.currentText()
        self.cmb_chart_track.blockSignals(True)
        self.cmb_chart_track.clear()
        for r in self.db.tracks():
            label = r["track"] + ((" - " + r["layout"]) if r["layout"] else "")
            self.cmb_chart_track.addItem(label, userData=(r["track"], r["layout"]))
        if cur:
            idx = self.cmb_chart_track.findText(cur)
            if idx >= 0:
                self.cmb_chart_track.setCurrentIndex(idx)
        self.cmb_chart_track.blockSignals(False)
        self.on_chart_changed()

    def on_chart_changed(self, *_):
        data = self.cmb_chart_track.currentData()
        if not data:
            self.chart.set_series("", [])
            return
        track, layout = data
        driver = "" if self.cmb_driver.currentText().startswith("(") else self.cmb_driver.currentText()
        rows = self.db.progression(track, layout, driver=driver)
        points = [(r["timestamp"], r["best_ms"]) for r in rows]
        self.chart.set_series(
            f"Bestzeiten-Entwicklung: {track}" + (f" – {layout}" if layout else ""),
            points)

    # ---------------------------------------------------------- Statistik --

    def refresh_stats(self):
        driver = "" if self.cmb_driver.currentText().startswith("(") else self.cmb_driver.currentText()
        stats, _ = self.db.stats_summary(driver, names=self._name_filter())
        races = stats["races"] or 0
        race_entries = stats["race_entries"] or 0
        finishes = stats["finishes"] or 0
        # Zielquote: Ziele pro Renneinsatz (früher fälschlich pro Sitzung,
        # was bei vielen Fahrern pro Rennen Werte über 100 % erzeugte)
        quote = (100.0 * finishes / race_entries) if race_entries else 0.0
        self.tiles["Rennen"].setText(str(races))
        self.tiles["Siege"].setText(str(stats["wins"]))
        self.tiles["Podium"].setText(str(stats["podium"]))
        self.tiles["Zielquote %"].setText(f"{quote:.0f} %")
        self.tiles["Runden gesamt"].setText(str(stats["total_laps"] or 0))
        self.tiles["Allzeit-Bestzeit"].setText(format_time_ms(stats["best_ms"]))
        self.lbl_stats.setText(
            f"Sitzungen: {stats['sessions']} · Fahrzeugeinsätze: {stats['entries']}")

        rows = [[d["name"], d["starts"], d["dnfs"], f"{d['finish_rate']:.1f}"]
                for d in self.db.dnf_summary(driver, names=self._name_filter())]
        self.dnf_model.beginResetModel()
        self.dnf_model.rows = rows
        self.dnf_model.endResetModel()

    def on_driver_changed_full(self, name):
        self.on_driver_changed(name)
        self.refresh_stats()
        self.on_chart_changed()

    # ----------------------------------------------- KI-Fahrer ausblenden --

    def _name_filter(self):
        """None = alle Fahrer; sonst Liste echter Fahrer (leer = nichts).

        0.4.10: Ist der Haken gesetzt ohne gepflegte Liste, wird None
        zurueckgegeben – als KI erkannte Fahrer blendet die Datenbank
        dann automatisch aus (Kennzeichen aus der Ergebnisdatei)."""
        if not self.settings.get("hide_ai"):
            return None
        return self.settings.get("real_drivers") or None

    def _save_settings(self):
        try:
            self.settings = appsettings.save_settings(self.settings_path,
                                                      self.settings)
        except OSError:
            self.statusBar().showMessage(
                "Einstellungen konnten nicht gespeichert werden.", 8000)

    def on_hide_ai_toggled(self, checked):
        self.settings["hide_ai"] = bool(checked)
        self.db.hide_ai = bool(checked)
        self._save_settings()
        if checked and not self.settings.get("real_drivers"):
            QtWidgets.QMessageBox.information(
                self, "KI-Fahrer ausblenden",
                "KI-Fahrer in Einzelspieler-Ergebnissen werden automatisch "
                "erkannt und ausgeblendet.\n\n"
                "Die Liste unter 'Werkzeuge → Echte Fahrer festlegen …' wird "
                "nur noch für Server- und Multiplayer-Ergebnisse benötigt, "
                "in denen echte und simulierte Fahrer nicht unterscheidbar "
                "sind.")
        # Alle von der Liste abhaengigen Ansichten neu aufbauen
        self._reload_driver_boxes()
        self.refresh_sessions()
        self._reload_lap_sessions()
        self.on_driver_changed(self.cmb_driver.currentText())
        self.refresh_stats()
        self.refresh_aggregate()
        self.statusBar().showMessage(
            "KI-Fahrer ausgeblendet" if checked else "Alle Fahrer angezeigt", 5000)
        self.statusBar().showMessage(
            "KI-Fahrer ausgeblendet" if checked else "Alle Fahrer angezeigt", 5000)

    def edit_real_drivers(self):
        txt, ok = QtWidgets.QInputDialog.getMultiLineText(
            self, "Echte Fahrer festlegen",
            "Namen der echten (menschlichen) Fahrer, durch Komma getrennt.\n"
            "Bei aktivem Haken 'KI-Fahrer ausblenden' werden nur diese "
            "Fahrer angezeigt:",
            ", ".join(self.settings.get("real_drivers") or []))
        if not ok:
            return
        names = [n.strip() for n in txt.split(",") if n.strip()]
        self.settings["real_drivers"] = names
        self._save_settings()
        if self.settings.get("hide_ai"):
            self._reload_driver_boxes()
            self.refresh_sessions()
            self._reload_lap_sessions()
            self.on_driver_changed(self.cmb_driver.currentText())
            self.refresh_stats()
            self.refresh_aggregate()
        self.statusBar().showMessage(
            f"{len(names)} echte Fahrer gespeichert.", 5000)

    def assign_track_ids(self):
        """Unbekannte numerische RaceRoom-Ids einmalig benennen (0.4.4)."""
        track_ids = self.db.unresolved_track_ids()
        car_ids = self.db.unresolved_car_ids()
        if not track_ids and not car_ids:
            QtWidgets.QMessageBox.information(
                self, "Strecken-Ids",
                "Es liegen keine unbekannten Strecken- oder Fahrzeug-Ids vor. "
                "Alle Einträge sind bereits mit Namen hinterlegt.")
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Unbekannte RaceRoom-Ids zuordnen")
        form = QtWidgets.QFormLayout(dlg)
        hint = QtWidgets.QLabel(
            "RaceRoom nennt die Strecke in Einzelspieler-Ergebnissen nur als "
            "interne Nummer. Bitte tragen Sie die Namen einmalig ein - sie "
            "werden dauerhaft gespeichert und auf alle vorhandenen und "
            "künftigen Sitzungen angewendet.")
        hint.setWordWrap(True)
        form.addRow(hint)
        fields = {}
        for tid in track_ids:
            e = QtWidgets.QLineEdit()
            e.setPlaceholderText("z. B. Nürburgring - Grand Prix")
            fields[("layout", tid)] = e
            form.addRow(f"Strecken-Id {tid}:", e)
        for cid in car_ids:
            e = QtWidgets.QLineEdit()
            e.setPlaceholderText("z. B. Audi R8 LMS GT3")
            fields[("car", cid)] = e
            form.addRow(f"Fahrzeug-Id {cid}:", e)
        btns = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        dlg.resize(480, dlg.sizeHint().height())
        if dlg.exec() != QtWidgets.QDialog.Accepted:
            return
        for (kind, id_), e in fields.items():
            text = e.text().strip()
            if not text:
                continue
            if kind == "layout":
                if " - " in text:
                    track, layout = text.split(" - ", 1)
                else:
                    track, layout = text, ""
                self.user_names.setdefault("layouts", {})[id_] = [
                    track.strip(), layout.strip()]
            else:
                self.user_names.setdefault("cars", {})[id_] = text
        trackids.save_user_names(self.user_names_path, self.user_names)
        n_t, n_v = self.db.upgrade_ids(self.user_names, self.official)
        self.refresh()
        self._update_status_totals()
        self.statusBar().showMessage(
            f"{n_t} Strecken und {n_v} Fahrzeuge umbenannt.", 10000)

    def export_diagnostics(self):
        """Diagnosebericht (0.4.13) als Textdatei sichern: je Strecke
        Median und die fuenf schnellsten Bestzeiten/Runden mit Sitzungs-
        und Dateiangaben. Dient der Ferndiagnose unmoeglicher Zeiten."""
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Diagnose exportieren",
            os.path.join(default_app_dir(), "r3e-diagnose.txt"), "*.txt")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(self.db.diagnostics_report())
        except OSError as e:
            QtWidgets.QMessageBox.warning(
                self, "Diagnose", f"Export fehlgeschlagen: {e}")
            return
        QtWidgets.QMessageBox.information(
            self, "Diagnose",
            "Diagnosebericht gespeichert:\n" + path + "\n\n"
            "Bitte hängen Sie diese Textdatei im Chat an, wenn Sie bei der "
            "Fehleranalyse unterstützen möchten.")
        self.statusBar().showMessage(f"Diagnose exportiert: {path}", 8000)

    def choose_raceroom_install(self):
        """Offizielle Spieldatenbank der RaceRoom-Installation einbinden
        (0.4.7): liest r3e-data.json und loest damit Strecken-/Fahrzeug-Ids
        auf, auch solche, die aeltere als den eingebauten Tabellen sind."""
        cur = self.settings.get("r3e_install_dir") or ""
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "RaceRoom-Installationsordner wählen",
            cur or os.path.join("C:\\Program Files (x86)\\Steam\\steamapps\\common",
                                "RaceRoom Racing Experience"))
        if not d:
            return
        if not trackids.find_official_data(d):
            QtWidgets.QMessageBox.warning(
                self, "RaceRoom-Installation",
                "In diesem Ordner wurde keine Spieldatenbank (r3e-data.json) "
                "gefunden.\n\nBitte wählen Sie den RaceRoom-Installationsordner "
                "aus. Klick-Weg in Steam:\nBibliothek → RaceRoom Racing Experience "
                "→ Verwaltung (Zahnrad) → Verwalten → Lokale Dateien durchsuchen.")
            return
        self.settings["r3e_install_dir"] = d
        self._save_settings()
        self.official = trackids.load_official(d)
        n_t, n_v = self.db.upgrade_ids(self.user_names, self.official)
        self.refresh()
        self._update_status_totals()
        n_layouts = len((self.official or {}).get("layouts") or {})
        n_cars = len((self.official or {}).get("cars") or {})
        QtWidgets.QMessageBox.information(
            self, "RaceRoom-Installation",
            f"Spieldatenbank eingebunden: {n_layouts} Strecken-Layouts, "
            f"{n_cars} Fahrzeuge erkannt.\n"
            f"{n_t} Strecken und {n_v} Fahrzeuge in der Datenbank wurden "
            f"umbenannt.\n\nKünftig werden neue Ids automatisch beim Einlesen "
            f"aufgelöst.")
        self.statusBar().showMessage(
            "RaceRoom-Spieldatenbank eingebunden.", 8000)

    def choose_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "RaceRoom-Ergebnisordner wählen", self.results_dir)
        if d:
            self.results_dir = d
            self.lbl_dir.setText(d)
            self.rescan()

    # ----------------------------------------------------------- Updates --

    def check_updates_manual(self):
        self.statusBar().showMessage("Prüfe auf Updates …")
        QtWidgets.QApplication.processEvents()
        try:
            info = updater.check_for_update(APP_VERSION)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Update",
                                          f"Update-Prüfung fehlgeschlagen: {e}")
            return
        self.statusBar().clearMessage()
        if info is None:
            QtWidgets.QMessageBox.information(self, "Update",
                                             f"Sie sind aktuell (v{APP_VERSION}).")
            return
        self._show_update_dialog(info)

    def _auto_check_updates(self):
        self._upd_check = UpdateCheckWorker(self)

        def on_result(info, err):
            if err:
                self.statusBar().showMessage(f"Update-Prüfung: {err}", 8000)
            elif info is not None:
                self._show_update_dialog(info)

        self._upd_check.result.connect(on_result)
        self._upd_check.start()

    def _show_update_dialog(self, info):
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle("Update verfügbar")
        box.setText(f"Neue Version {info['version']} verfügbar.\n"
                    f"Installiert: {APP_VERSION}.")
        if info.get("notes"):
            box.setInformativeText(info["notes"][:600])
        dl_btn = None
        if info.get("asset_url"):
            dl_btn = box.addButton("Herunterladen & installieren",
                                   QtWidgets.QMessageBox.AcceptRole)
        open_btn = box.addButton("Download-Seite öffnen", QtWidgets.QMessageBox.AcceptRole)
        box.addButton("Später", QtWidgets.QMessageBox.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if dl_btn is not None and clicked is dl_btn:
            self._download_and_launch(info)
        elif clicked is open_btn:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(info["url"]))

    def _download_and_launch(self, info):
        url = info.get("asset_url") or ""
        if not url:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(info["url"]))
            return
        try:
            updates_dir = os.path.join(default_app_dir(), "updates")
            os.makedirs(updates_dir, exist_ok=True)
        except Exception:
            updates_dir = os.path.expanduser("~")
        fname = os.path.basename(url.split("?")[0]) or "R3E-Resultate-Setup.exe"
        dest = os.path.join(updates_dir, fname)

        prog = QtWidgets.QProgressDialog("Installer wird heruntergeladen …",
                                         "Abbrechen", 0, 100, self)
        prog.setWindowTitle("Update")
        prog.setMinimumDuration(0)
        prog.show()

        self._dl_worker = UpdateDownloadWorker(url, dest, self)
        self._dl_worker.progress.connect(lambda d, t: prog.setMaximum(int(t) if t else 100),
                                         QtCore.Qt.QueuedConnection)
        self._dl_worker.progress.connect(prog.setValue, QtCore.Qt.QueuedConnection)

        def on_done(path, err):
            prog.close()
            if err:
                QtWidgets.QMessageBox.warning(self, "Update",
                                              f"Download fehlgeschlagen: {err}")
                return
            QtWidgets.QMessageBox.information(
                self, "Update",
                "Installer heruntergeladen. Die App wird jetzt beendet und\n"
                "der Installer gestartet.")
            try:
                subprocess.Popen([path], cwd=os.path.dirname(path))
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "Update",
                                              f"Installer konnte nicht gestartet "
                                              f"werden: {e}")
                return
            self.close()

        self._dl_worker.finished_result.connect(on_done, QtCore.Qt.QueuedConnection)
        self._dl_worker.start()

    def show_about(self):
        QtWidgets.QMessageBox.about(
            self, APP_NAME,
            f"{APP_NAME}\nVersion {APP_VERSION}\n\n"
            f"Sitzungshistorie und Bestzeiten für RaceRoom Racing Experience.\n"
            f"Updates: https://github.com/{updater.GITHUB_REPO}/releases")

    def closeEvent(self, ev):
        self.watch_timer.stop()
        self.db.close()
        super().closeEvent(ev)


def _ensure_app_icon():
    """Erzeugt das App-Icon beim ersten Start im App-Datenordner (0.4.5)."""
    icon_path = os.path.join(default_app_dir(), "app_icon.ico")
    try:
        if not os.path.exists(icon_path):
            icon_gen.write_ico(icon_path)
        return icon_path
    except OSError:
        return None


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    icon_path = _ensure_app_icon()
    if icon_path:
        app.setWindowIcon(QtGui.QIcon(icon_path))
    apply_dark_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
