"""Tests for 0.4.11: ingest cache and database lock settings."""
import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc.database import Database, _PARSER_CACHE_VER
from rrc.models import APP_VERSION
from rrc import database as rrc_database


def _write_result(folder, name, best=100000):
    path = os.path.join(folder, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"header": {"game": "RaceRoom Racing Experience",
                              "version": "0.9.9.22",
                              "time": "2026/11/07 20:44:54"},
                   "event": {"trackId": 12505, "layoutId": 12506},
                   "drivers": [{"name": "Marcel Wijnandts", "userId": 1,
                                "carId": 10914, "totalLaps": 1, "laps": [],
                                "bestLapTimeMs": best, "raceTimeMs": -1,
                                "place": 1}]}, f)
    return path


class TestIngestCache(unittest.TestCase):
    """0.4.11: Unveränderte Dateien werden beim Start übersprungen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = os.path.join(self.tmp.name, "results")
        os.makedirs(self.folder)
        self.db = Database(os.path.join(self.tmp.name, "results.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_version(self):
        self.assertEqual(APP_VERSION, "0.4.14")

    def test_second_scan_skips_unchanged_files(self):
        _write_result(self.folder, "2026_11_07_20_44_53_Practice.txt")
        calls = []
        orig = rrc_database.parse_file
        rrc_database.parse_file = lambda p: calls.append(p) or orig(p)
        try:
            added, skipped, errors = self.db.ingest_folder(self.folder)
            self.assertEqual((added, errors), (1, 0))
            self.assertEqual(len(calls), 1)
            added2, skipped2, errors2 = self.db.ingest_folder(self.folder)
            self.assertEqual((added2, errors2), (0, 0))
            self.assertEqual(len(calls), 1)      # kein erneutes Parsen
            self.assertGreaterEqual(skipped2, 1)
        finally:
            rrc_database.parse_file = orig

    def test_changed_file_is_reparsed(self):
        _write_result(self.folder, "2026_11_07_20_44_53_Practice.txt")
        self.db.ingest_folder(self.folder)
        # Datei veraendern (neue Groesse) -> muss neu gelesen werden
        _write_result(self.folder, "2026_11_07_20_44_53_Practice.txt",
                      best=95000)
        os.utime(os.path.join(self.folder,
                              "2026_11_07_20_44_53_Practice.txt"),
                 (time.time() + 5, time.time() + 5))
        added, skipped, errors = self.db.ingest_folder(self.folder)
        # gleiche Quelldatei + Typ + Zeit = gleiche Sitzung, auch wenn der
        # Dateiinhalt (Bestzeit) veraendert wurde — RaceRoom-Dateien sind
        # unabhaenderlich; der Cache wird dennoch aktualisiert
        self.assertEqual(added, 0)
        row = self.db.conn.execute(
            "SELECT size FROM ingest_cache").fetchone()
        self.assertEqual(row["size"],
                         os.path.getsize(os.path.join(
                             self.folder,
                             "2026_11_07_20_44_53_Practice.txt")))

    def test_cache_version_forces_reparse(self):
        _write_result(self.folder, "2026_11_07_20_44_53_Practice.txt")
        self.db.ingest_folder(self.folder)
        self.db.conn.execute("UPDATE ingest_cache SET ver = ?",
                             (_PARSER_CACHE_VER - 1,))
        self.db.conn.commit()
        calls = []
        orig = rrc_database.parse_file
        rrc_database.parse_file = lambda p: calls.append(p) or orig(p)
        try:
            self.db.ingest_folder(self.folder)
            self.assertEqual(len(calls), 1)
        finally:
            rrc_database.parse_file = orig

    def test_lock_settings_active(self):
        self.assertEqual(
            self.db.conn.execute("PRAGMA busy_timeout").fetchone()[0], 10000)
        mode = self.db.conn.execute(
            "PRAGMA journal_mode").fetchone()[0].lower()
        self.assertEqual(mode, "wal")

    def test_parallel_reader_allowed(self):
        """Zweite Verbindung darf trotz offener erster Verbindung lesen."""
        conn2 = sqlite3.connect(self.db.path)
        try:
            self.assertEqual(
                conn2.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                0)
        finally:
            conn2.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
