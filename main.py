"""RaceRoom Results Companion - GUI entry point.

A standalone companion app for RaceRoom Racing Experience:
- automatically records session results from the local results folder
- session history with full result details
- personal best times per track/layout/car
- basic statistics

Run: python main.py
"""
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from rrc.database import Database
from rrc.models import APP_NAME, APP_VERSION, format_time_ms
from rrc.paths import default_results_dir, default_db_path

COL_SESSIONS = ["Datum", "Typ", "Strecke", "Fahrer", "Bestzeit"]
COL_ENTRIES = ["Pos.", "Fahrer", "Fahrzeug", "Runden", "Beste Runde", "Renzeit", "Status"]
COL_BESTS = ["Fahrer", "Strecke", "Fahrzeug", "Bestzeit", "Fahrten", "Zuletzt"]


class SessionTableModel(QtCore.QAbstractTableModel):
    def __init__(self, rows):
        super().__init__()
        self.rows = rows or []

    def rowCount(self, *a):
        return len(self.rows)

    def columnCount(self, *a):
        return len(COL_SESSIONS)

    def headerData(self, sec, orient, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Horizontal:
            return COL_SESSIONS[sec]
        return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or role != QtCore.Qt.DisplayRole:
            return None
        r = self.rows[index.row()]
        c = index.column()
        if c == 0:
            return r["timestamp"]
        if c == 1:
            return r["session_type"]
        if c == 2:
            full = r["track"] + ((" - " + r["layout"]) if r["layout"] else "")
            return full
        if c == 3:
            return str(r["n_players"])
        if c == 4:
            return format_time_ms(r["session_best_ms"])
        return None


class GenericTableModel(QtCore.QAbstractTableModel):
    def __init__(self, columns, rows):
        super().__init__()
        self.columns = columns
        self.rows = rows or []

    def rowCount(self, *a):
        return len(self.rows)

    def columnCount(self, *a):
        return len(self.columns)

    def headerData(self, sec, orient, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orient == QtCore.Qt.Horizontal:
            return self.columns[sec]
        return None

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or role != QtCore.Qt.DisplayRole:
            return None
        return str(self.rows[index.row()][index.column()])


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.resize(1100, 640)

        self.results_dir = default_results_dir()
        self.db_path = default_db_path()
        self.db = Database(self.db_path)
        self.driver = ""
        self._last_dir_stamp = None

        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- Tab: Sitzungen ---
        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        self.btn_rescan = QtWidgets.QPushButton("Jetzt einlesen")
        self.btn_rescan.clicked.connect(self.rescan)
        bar = QtWidgets.QHBoxLayout()
        bar.addWidget(self.btn_rescan)
        self.lbl_dir = QtWidgets.QLabel("")
        self.lbl_dir.setStyleSheet("color: #888;")
        bar.addWidget(self.lbl_dir, 1)
        v.addLayout(bar)
        self.tbl_sessions = QtWidgets.QTableView()
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
        v.addWidget(lbl_detail)
        self.tbl_entries = QtWidgets.QTableView()
        self.entries_model = GenericTableModel(COL_ENTRIES, [])
        self.tbl_entries.setModel(self.entries_model)
        self.tbl_entries.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_entries, 1)
        self.tabs.addTab(page, "Sitzungen")

        # --- Tab: Bestzeiten ---
        page2 = QtWidgets.QWidget()
        v2 = QtWidgets.QVBoxLayout(page2)
        combo_row = QtWidgets.QHBoxLayout()
        combo_row.addWidget(QtWidgets.QLabel("Fahrer:"))
        self.cmb_driver = QtWidgets.QComboBox()
        self.cmb_driver.setMinimumWidth(220)
        self.cmb_driver.currentTextChanged.connect(self.on_driver_changed)
        combo_row.addWidget(self.cmb_driver)
        combo_row.addStretch(1)
        v2.addLayout(combo_row)
        self.tbl_bests = QtWidgets.QTableView()
        self.bests_model = GenericTableModel(COL_BESTS, [])
        self.tbl_bests.setModel(self.bests_model)
        self.tbl_bests.horizontalHeader().setStretchLastSection(True)
        v2.addWidget(self.tbl_bests, 1)
        self.lbl_stats = QtWidgets.QLabel("")
        self.lbl_stats.setStyleSheet("color: #888;")
        v2.addWidget(self.lbl_stats)
        self.tabs.addTab(page2, "Bestzeiten")

        # --- Menü ---
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

        # --- Auto-Watch ---
        self.watch_timer = QtCore.QTimer(self)
        self.watch_timer.setInterval(5000)
        self.watch_timer.timeout.connect(self.check_folder)
        self.watch_timer.start()

        self.lbl_dir.setText(self.results_dir)
        self.rescan(silent=True)

    # ------------------------------------------------------------- Logic --

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
        if not silent or added:
            self.statusBar().showMessage(
                f"Neu: {added} Sitzungen, bekannt: {skipped}, "
                f"unlesbar: {errors} ({self.results_dir})", 10000)

    def refresh(self):
        rows = self.db.sessions()
        self.sess_model.beginResetModel()
        self.sess_model.rows = [dict(r) for r in rows]
        self.sess_model.endResetModel()
        current = self.cmb_driver.currentText()
        self.cmb_driver.blockSignals(True)
        self.cmb_driver.clear()
        self.cmb_driver.addItem("(alle Fahrer)")
        for name in self.db.drivers():
            self.cmb_driver.addItem(name)
        idx = self.cmb_driver.findText(current) if current else 0
        self.cmb_driver.setCurrentIndex(max(0, idx))
        self.cmb_driver.blockSignals(False)
        self.on_driver_changed(self.cmb_driver.currentText())

    def on_session_selected(self, *_):
        indexes = self.tbl_sessions.selectionModel().selectedRows()
        if not indexes:
            return
        row = self.sess_model.rows[indexes[0].row()]
        rows = []
        for e in self.db.entries_for(row["id"]):
            rows.append([e["position"], e["name"], e["vehicle"], e["laps"],
                         format_time_ms(e["best_lap_ms"]),
                         format_time_ms(e["race_time_ms"]),
                         e["finish_status"] or ("Finished" if e["position"] else "")])
        self.entries_model.beginResetModel()
        self.entries_model.rows = rows
        self.entries_model.endResetModel()

    def on_driver_changed(self, name):
        driver = "" if name.startswith("(") else name
        rows = []
        for r in self.db.personal_bests(driver):
            rows.append([r["name"], (r["track"] + ((" - " + r["layout"]) if r["layout"] else "")),
                         r["vehicle"], format_time_ms(r["best_ms"]), r["n"], r["last_seen"]])
        self.bests_model.beginResetModel()
        self.bests_model.rows = rows
        self.bests_model.endResetModel()
        stats, wins = self.db.stats_summary(driver)
        total_laps = stats.get("total_laps") or 0
        self.lbl_stats.setText(
            f"Sitzungen: {stats['sessions']} · Fahrzeugeinsätze: {stats['entries']} "
            f"· Runden gesamt: {total_laps} · Siege: {wins} · "
            f"Allzeit-Bestzeit: {format_time_ms(stats['best_ms'])}")

    def choose_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, "RaceRoom-Ergebnisordner wählen", self.results_dir)
        if d:
            self.results_dir = d
            self.lbl_dir.setText(d)
            self.rescan()

    def closeEvent(self, ev):
        self.watch_timer.stop()
        self.db.close()
        super().closeEvent(ev)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
