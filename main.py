"""RaceRoom Results Companion - GUI entry point.

A standalone companion app for RaceRoom Racing Experience:
- automatically records session results from the local results folder
- session history with full result details
- personal best times per track/layout/car
- basic statistics
- dark PitBoss-style theme, update check over GitHub Releases

Run: python main.py
"""
import os
import subprocess
import sys

from PySide6 import QtCore, QtGui, QtWidgets

import updater
from rrc.database import Database
from rrc.models import APP_NAME, APP_VERSION, format_time_ms
from rrc.paths import default_app_dir, default_results_dir, default_db_path
from rrc.theme import apply_dark_theme

COL_SESSIONS = ["Datum", "Typ", "Strecke", "Fahrer", "Bestzeit"]
COL_ENTRIES = ["Pos.", "Fahrer", "Fahrzeug", "Runden", "Beste Runde", "Renzeit", "Status"]
COL_BESTS = ["Fahrer", "Strecke", "Fahrzeug", "Bestzeit", "Fahrten", "Zuletzt"]


class UpdateCheckWorker(QtCore.QThread):
    """Update-Pruefung im Hintergrund (blockiert die UI nicht)."""
    result = QtCore.Signal(object, str)  # (info | None, fehler)

    def run(self):
        try:
            self.result.emit(updater.check_for_update(APP_VERSION), "")
        except Exception as e:
            self.result.emit(None, str(e))


class UpdateDownloadWorker(QtCore.QThread):
    """Laedt den Installer im Hintergrund und meldet Fortschritt."""
    progress = QtCore.Signal(int, int)
    finished_result = QtCore.Signal(str, str)  # (pfad, fehler)

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
        page.setObjectName("rootBg")
        v = QtWidgets.QVBoxLayout(page)
        self.btn_rescan = QtWidgets.QPushButton("Jetzt einlesen")
        self.btn_rescan.setObjectName("primary")
        self.btn_rescan.clicked.connect(self.rescan)
        bar = QtWidgets.QHBoxLayout()
        bar.addWidget(self.btn_rescan)
        self.lbl_dir = QtWidgets.QLabel("")
        self.lbl_dir.setStyleSheet("color: #8f8f99;")
        bar.addWidget(self.lbl_dir, 1)
        v.addLayout(bar)
        self.tbl_sessions = QtWidgets.QTableView()
        self.tbl_sessions.setAlternatingRowColors(True)
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
        self.tbl_entries.setAlternatingRowColors(True)
        self.entries_model = GenericTableModel(COL_ENTRIES, [])
        self.tbl_entries.setModel(self.entries_model)
        self.tbl_entries.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.tbl_entries, 1)
        self.tabs.addTab(page, "Sitzungen")

        # --- Tab: Bestzeiten ---
        page2 = QtWidgets.QWidget()
        v2 = QtWidgets.QVBoxLayout(page2)
        combo_row = QtWidgets.QHBoxLayout()
        lbl_driver = QtWidgets.QLabel("Fahrer:")
        lbl_driver.setObjectName("sectionTitle")
        combo_row.addWidget(lbl_driver)
        self.cmb_driver = QtWidgets.QComboBox()
        self.cmb_driver.setMinimumWidth(220)
        self.cmb_driver.currentTextChanged.connect(self.on_driver_changed)
        combo_row.addWidget(self.cmb_driver)
        combo_row.addStretch(1)
        v2.addLayout(combo_row)
        self.tbl_bests = QtWidgets.QTableView()
        self.tbl_bests.setAlternatingRowColors(True)
        self.bests_model = GenericTableModel(COL_BESTS, [])
        self.tbl_bests.setModel(self.bests_model)
        self.tbl_bests.horizontalHeader().setStretchLastSection(True)
        v2.addWidget(self.tbl_bests, 1)
        self.lbl_stats = QtWidgets.QLabel("")
        self.lbl_stats.setObjectName("hint")
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

        mh = self.menuBar().addMenu("&Hilfe")
        act_update = QtGui.QAction("Nach Updates suchen …", self)
        act_update.triggered.connect(self.check_updates_manual)
        mh.addAction(act_update)
        act_about = QtGui.QAction(f"Über {APP_NAME}", self)
        act_about.triggered.connect(self.show_about)
        mh.addAction(act_about)

        # --- Auto-Watch ---
        self.watch_timer = QtCore.QTimer(self)
        self.watch_timer.setInterval(5000)
        self.watch_timer.timeout.connect(self.check_folder)
        self.watch_timer.start()

        self.lbl_dir.setText(self.results_dir)
        self.rescan(silent=True)
        self._auto_check_updates()

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
            f"Sitzungen: {stats['sessions']} · Renneinsätze: {stats['entries']} "
            f"· Runden gesamt: {total_laps} · Siege: {wins} · "
            f"Allzeit-Bestzeit: {format_time_ms(stats['best_ms'])}")

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
        """Beim Start: im Hintergrund pruefen; nur melden, wenn es ein Update gibt."""
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


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    apply_dark_theme(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
