"""Tests for 0.4.10: carId/AI parsing, session best, hide_ai, backfill."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc.database import Database
from rrc.models import APP_VERSION, Session, PlayerResult
from rrc.parser import parse_file


def _sp_file(path, drivers, track_id=12505, layout_id=12506):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"header": {"game": "RaceRoom Racing Experience",
                             "version": "0.9.9.22",
                             "time": "2026/11/07 20:44:54"},
                   "event": {"trackId": track_id, "layoutId": layout_id},
                   "drivers": drivers}, f)


def _driver(name, car_id=10914, user_id=5474349, laps=3, best=100000):
    return {"name": name, "userId": user_id, "carId": car_id,
            "totalLaps": laps, "laps": [],
            "bestLapTimeMs": best, "raceTimeMs": -1, "place": 1}


class TestSpCarAi(unittest.TestCase):
    """0.4.10: carId, KI-Erkennung (userId) und Fahrzeugklasse."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "results.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def _ingest(self, filename, drivers):
        path = os.path.join(self.tmp.name, filename)
        _sp_file(path, drivers)
        sess = parse_file(path)
        self.assertTrue(sess)
        self.db.insert_session(sess[0], path)
        return sess[0]

    def test_version(self):
        self.assertEqual(APP_VERSION, "0.6.0")

    def test_car_id_and_ai_parsed(self):
        s = self._ingest("2026_11_07_20_44_53_Practice.txt",
                         [_driver("Marcel Wijnandts", user_id=5474349),
                          _driver("AI Opponent", user_id=-1)])
        real, ai = s.players[0], s.players[1]
        self.assertEqual(real.car_id, 10914)
        self.assertEqual(real.is_ai, 0)
        self.assertEqual(ai.is_ai, 1)
        self.assertTrue(real.vehicle)          # Fahrzeugname oder numerische Id
        self.assertTrue("Mazda" in real.vehicle
                        or "10914" in real.vehicle)

    def test_session_best_ignores_zero_entries(self):
        """Bestzeit einer Sitzung bleibt trotz Fahrern ohne gueltige Zeit."""
        self._ingest("2026_11_07_20_44_53_Practice.txt",
                     [_driver("Marcel Wijnandts", best=106222),
                      _driver("Keine Zeit", best=-1)])
        row = self.db.sessions()[0]
        self.assertEqual(row["session_best_ms"], 106222)

    def test_hide_ai_excludes_ai(self):
        self._ingest("2026_11_07_20_44_53_Race.txt",
                     [_driver("Marcel Wijnandts", best=106222),
                      _driver("AI Fast", user_id=-1, best=99000)])
        self.db.hide_ai = True
        stats, _ = self.db.stats_summary()
        self.assertEqual(stats["entries"], 1)
        self.assertEqual(stats["best_ms"], 106222)
        self.assertEqual(self.db.drivers(), ["Marcel Wijnandts"])
        self.assertEqual(self.db.totals(), (1, 3))   # nur Marcels 3 Runden

    def test_hide_ai_keeps_unknown_format_entries(self):
        """ai = -1 (unbekannt, z. B. Server) bleibt sichtbar."""
        sess = Session(session_type="Race", timestamp="2026-11-07 12:00:00",
                       track="Testbahn", layout="", source_file="srv.json",
                       digest="srv-d1")
        sess.players.append(PlayerResult(name="Server Fahrer", vehicle="BMW",
                                          is_ai=-1))
        self.db.insert_session(sess, "srv.json")
        self.db.hide_ai = True
        self.assertEqual(self.db.drivers(), ["Server Fahrer"])

    def test_backfill_from_files(self):
        """Alte Sitzungen (Fahrzeug leer) werden aus der Datei nachgetragen."""
        path = os.path.join(self.tmp.name, "2026_11_07_20_44_53_Practice.txt")
        _sp_file(path, [_driver("Marcel Wijnandts", user_id=5474349),
                        _driver("AI Opponent", user_id=-1)])
        # simulieren: vor 0.4.10 ohne Fahrzeug und KI-Kennzeichen gespeichert
        s = parse_file(path)[0]
        for p in s.players:
            p.vehicle = ""
            p.car_id = 0
            p.is_ai = -1
            p.vehicle_class = ""
        self.db.insert_session(s, path)
        row = self.db.conn.execute(
            "SELECT vehicle, ai FROM entries LIMIT 1").fetchone()
        self.assertEqual(row["vehicle"], "")
        self.assertEqual(row["ai"], -1)
        n = self.db.backfill_from_files(self.tmp.name)
        self.assertGreaterEqual(n, 2)
        rows = self.db.conn.execute(
            "SELECT name, vehicle, car_id, ai FROM entries "
            "ORDER BY name").fetchall()
        by = {r["name"]: r for r in rows}
        self.assertEqual(by["Marcel Wijnandts"]["car_id"], 10914)
        self.assertEqual(by["Marcel Wijnandts"]["ai"], 0)
        self.assertEqual(by["AI Opponent"]["ai"], 1)
        self.assertTrue(by["Marcel Wijnandts"]["vehicle"])

    def test_aggregate_by_class(self):
        sess = Session(session_type="Race", timestamp="2026-11-07 12:00:00",
                       track="Testbahn", layout="", source_file="c1.json",
                       digest="cls-d1")
        sess.players.append(PlayerResult(name="Marcel Wijnandts",
                                         vehicle="BMW M4 GT3",
                                         vehicle_class="GT3",
                                         laps=5, best_lap_ms=100000,
                                         position=1))
        sess.players.append(PlayerResult(name="Marcel Wijnandts",
                                         vehicle="Porsche 992 Cup",
                                         vehicle_class="Porsche 911 GT3 Cup",
                                         laps=4, best_lap_ms=110000,
                                         position=1))
        self.db.insert_session(sess, "c1.json")
        rows = self.db.aggregate("class")
        labels = {r["label"]: r for r in rows}
        self.assertIn("GT3", labels)
        self.assertIn("Porsche 911 GT3 Cup", labels)
        self.assertEqual(labels["GT3"]["sessions"], 1)
        self.assertEqual(labels["GT3"]["wins"], 1)
        self.assertEqual(labels["GT3"]["total_laps"], 5)

    def test_track_records_per_class(self):
        sess = Session(session_type="Race", timestamp="2026-11-07 12:00:00",
                       track="Testbahn", layout="", source_file="c2.json",
                       digest="cls-d2")
        sess.players.append(PlayerResult(name="Marcel Wijnandts",
                                         vehicle="BMW M4 GT3",
                                         vehicle_class="GT3",
                                         best_lap_ms=100000))
        sess.players.append(PlayerResult(name="Marcel Wijnandts",
                                         vehicle="Mazda MX-5",
                                         vehicle_class="Mazda MX-5 Cup",
                                         best_lap_ms=120000))
        self.db.insert_session(sess, "c2.json")
        self.assertEqual(
            self.db.track_classes("Testbahn"), ["GT3", "Mazda MX-5 Cup"])
        rec = self.db.track_records("Testbahn", vehicle_class="GT3")
        self.assertEqual(rec["best_ms"], 100000)
        rec2 = self.db.track_records("Testbahn", vehicle_class="Mazda MX-5 Cup")
        self.assertEqual(rec2["best_ms"], 120000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
