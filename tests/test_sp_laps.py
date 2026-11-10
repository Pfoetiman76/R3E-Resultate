"""Tests for SP lap handling and the AI totalLaps artifact (0.4.8)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc.parser import parse_sp_json
from rrc.database import Database
from rrc.models import Session, PlayerResult, LapEntry


def _driver(name, total_laps, laps):
    return {"name": name, "carId": 111, "totalLaps": total_laps,
            "bestLapTimeMs": 100000, "raceTimeMs": -1, "place": 1,
            "laps": laps}


class TestSpLaps(unittest.TestCase):
    """0.4.8: SP-Runden mit gueltiger Zeit, KI-Artefakt 896/856 wird
    ignoriert."""

    def _session(self, drivers):
        data = {"header": {"time": "2026/11/07 20:44:54"},
                "event": {"trackId": 12505, "layoutId": 12506},
                "drivers": drivers}
        return parse_sp_json(data, "2026_11_07_20_44_53_Practice.txt")

    def test_valid_laps_only(self):
        """Nur Runden mit gueltiger Zeit zaehlen; ungueltige Platzhalter
        werden seit 0.4.14 mit lap_time_ms -1 mitgefuehrt (rot)."""
        s = self._session([
            _driver("Marcel Wijnandts", 2,
                    [{"number": 0, "lapTimeMs": -1},
                     {"number": 1, "lapTimeMs": 106222}]),
        ])
        p = s.players[0]
        self.assertEqual(p.laps, 1)
        self.assertEqual(len(p.laps_detail), 2)
        self.assertEqual(p.laps_detail[0].lap_time_ms, -1)   # ungueltig
        self.assertEqual(p.laps_detail[1].lap_time_ms, 106222)

    def test_invalid_laps_of_ai_not_stored(self):
        """KI-Fahrer (userId -1): ungueltige Platzhalter nicht speichern."""
        s = self._session([
            {"name": "AI Driver", "userId": -1, "carId": 111,
             "totalLaps": 2,
             "bestLapTimeMs": 100000, "raceTimeMs": -1, "place": 2,
             "laps": [{"number": 0, "lapTimeMs": -1},
                      {"number": 1, "lapTimeMs": -1}]},
        ])
        p = s.players[0]
        self.assertEqual(p.is_ai, 1)
        self.assertEqual(p.laps_detail, [])

    def test_ai_artifact_without_valid_laps(self):
        """KI-Fahrer: totalLaps 856 ohne gueltige Zeiten -> 0 Runden."""
        junk = [{"number": i, "lapTimeMs": -1} for i in range(856)]
        s = self._session([_driver("AI Driver", 856, junk)])
        p = s.players[0]
        self.assertEqual(p.laps, 0)
        self.assertEqual(p.laps_detail, [])

    def test_old_format_without_laps_array(self):
        """Altes SP-Format ohne laps-Array: plausible Rundenzahl bleibt."""
        s = self._session([
            {"name": "Marcel Wijnandts", "vehicle": "BMW M4 GT3",
             "totallaps": 4, "bestlaptimems": 512340, "racetimems": 1800000,
             "place": 1},
        ])
        self.assertEqual(s.players[0].laps, 4)
        self.assertEqual(s.players[0].laps_detail, [])

    def test_artifact_without_laps_array(self):
        """KI-Artefakt 856 auch ohne laps-Array -> 0."""
        s = self._session([
            {"name": "AI Driver", "vehicle": "BMW M4 GT3",
             "totallaps": 856, "bestlaptimems": 522100, "racetimems": -1,
             "place": 2},
        ])
        self.assertEqual(s.players[0].laps, 0)


class TestSanitizeLaps(unittest.TestCase):
    """0.4.8: Datenbank-Bereinigung bereits erfasster Sitzungen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "results.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def _insert(self, laps, detail=None):
        sess = Session(session_type="Race",
                       timestamp="2026-11-07 20:44:5" + str(abs(laps) % 10),
                       track="Testring", layout="Grand Prix",
                       source_file="a.txt", digest="d-" + str(laps) +
                       str(len(detail or [])) + str(os.getpid()))
        p = PlayerResult(name="Fahrer", vehicle="Wagen", laps=laps,
                         laps_detail=detail or [])
        sess.players.append(p)
        self.assertTrue(self.db.insert_session(sess, "a.txt"))

    def test_artifact_replaced_by_recorded_laps(self):
        detail = [LapEntry(1, 105000), LapEntry(2, 104000)]
        self._insert(856, detail)
        n = self.db.sanitize_laps()
        self.assertEqual(n, 1)
        rows = self.db.conn.execute("SELECT laps FROM entries").fetchall()
        self.assertEqual(rows[0]["laps"], 2)

    def test_artifact_without_detail_becomes_zero(self):
        self._insert(856)
        self.db.sanitize_laps()
        rows = self.db.conn.execute("SELECT laps FROM entries").fetchall()
        self.assertEqual(rows[0]["laps"], 0)

    def test_plausible_laps_untouched(self):
        self._insert(4)
        self._insert(380)  # Le Mans
        n = self.db.sanitize_laps()
        self.assertEqual(n, 0)
        rows = self.db.conn.execute("SELECT laps FROM entries"
                                    " ORDER BY laps").fetchall()
        self.assertEqual([r["laps"] for r in rows], [4, 380])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestTotalLapsDisplay(unittest.TestCase):
    """0.4.13: Anzeige 'Runden gesamt / gueltig' (SP totallaps)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "results.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def _sp_session(self, drivers, ts="2026/11/07 20:44:54",
                    src="2026_11_07_20_44_53_Practice.txt"):
        data = {"header": {"time": ts},
                "event": {"trackId": 12505, "layoutId": 12506},
                "drivers": drivers}
        return parse_sp_json(data, src)

    def test_total_laps_parsed_and_stored(self):
        laps = ([{"number": i, "lapTimeMs": -1} for i in range(6)]
                + [{"number": 6 + i, "lapTimeMs": 100000 + i} for i in range(3)])
        s = self._sp_session([_driver("Marcel Wijnandts", 9, laps)])
        p = s.players[0]
        self.assertEqual(p.laps, 3)          # gueltig
        self.assertEqual(p.total_laps, 9)   # gesamt laut Datei
        self.assertTrue(self.db.insert_session(s, s.source_file))
        row = self.db.conn.execute(
            "SELECT laps, total_laps FROM entries").fetchone()
        self.assertEqual(row["laps"], 3)
        self.assertEqual(row["total_laps"], 9)

    def test_backfill_on_known_natural_key(self):
        """Bestehende Sitzung (vor 0.4.13 ohne total_laps) erhaelt den
        Wert beim erneuten Einlesen nachgezogen — ohne neue Sitzung."""
        laps = [{"number": 0, "lapTimeMs": 106222},
                {"number": 1, "lapTimeMs": 105000},
                {"number": 2, "lapTimeMs": 104000}]
        s = self._sp_session([_driver("Marcel Wijnandts", 9, laps)])
        # Alt-Zustand nachbilden: Sitzung existiert, total_laps fehlt (-1).
        cur = self.db.conn.execute(
            "INSERT INTO sessions (digest, session_type, timestamp, track, "
            "layout, source_file) VALUES (?,?,?,?,?,?)",
            ("alt", s.session_type, s.timestamp, s.track, s.layout,
             s.source_file))
        self.db.conn.execute(
            "INSERT INTO entries (session_id, position, name, vehicle, "
            "laps, best_lap_ms, total_laps) VALUES (?,?,?,?,?,?,?)",
            (cur.lastrowid, 1, "Marcel Wijnandts", "BMW M4 GT3",
             3, 104000, -1))
        self.db.conn.commit()
        self.assertFalse(self.db.insert_session(s, s.source_file))
        self.assertEqual(len(self.db.sessions()), 1)
        row = self.db.conn.execute(
            "SELECT laps, total_laps FROM entries").fetchone()
        self.assertEqual((row["laps"], row["total_laps"]), (3, 9))

    def test_artifact_excluded_from_total(self):
        junk = [{"number": i, "lapTimeMs": -1} for i in range(856)]
        s = self._sp_session([_driver("AI Driver", 856, junk)])
        self.assertEqual(s.players[0].total_laps, 0)

    def test_old_format_total_equals_laps(self):
        s = self._sp_session([
            {"name": "Marcel Wijnandts", "vehicle": "BMW M4 GT3",
             "totallaps": 4, "bestlaptimems": 512340, "racetimems": 1800000,
             "place": 1},
        ])
        p = s.players[0]
        self.assertEqual(p.laps, 4)
        self.assertEqual(p.total_laps, 4)


class TestInvalidLapsRefresh(unittest.TestCase):
    """0.4.14: Ungueltige Runden (lap_time_ms -1) in der Rundenansicht
    sichtbar machen; Bestandssitzungen erhalten sie beim erneuten
    Einlesen nachgezogen."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "results.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def _sp_session(self, laps, ts="2026/11/09 19:00:00"):
        data = {"header": {"time": ts},
                "event": {"trackId": 12505, "layoutId": 12506},
                "drivers": [_driver("Marcel Wijnandts", len(laps), laps)]}
        return parse_sp_json(data, "2026_11_09_19_00_00_Practice.txt")

    def test_invalid_laps_persisted_and_refreshed(self):
        laps = ([{"number": 0, "lapTimeMs": 106000},
                 {"number": 1, "lapTimeMs": -1},
                 {"number": 2, "lapTimeMs": 105000},
                 {"number": 3, "lapTimeMs": -1},
                 {"number": 4, "lapTimeMs": 104000}])
        s = self._sp_session(laps)
        self.assertEqual(s.players[0].laps, 3)
        self.assertEqual(len(s.players[0].laps_detail), 5)
        self.assertTrue(self.db.insert_session(s, s.source_file))
        times = [r["lap_time_ms"] for r in self.db.conn.execute(
            "SELECT lap_time_ms FROM laps ORDER BY lap_no")]
        self.assertEqual(times, [106000, -1, 105000, -1, 104000])
        # Erneutes Einlesen (natural key bekannt): Rundendetails werden
        # erneuert, ohne eine zweite Sitzung zu erzeugen.
        self.assertFalse(self.db.insert_session(s, s.source_file))
        self.assertEqual(len(self.db.sessions()), 1)
        times = [r["lap_time_ms"] for r in self.db.conn.execute(
            "SELECT lap_time_ms FROM laps ORDER BY lap_no")]
        self.assertEqual(times, [106000, -1, 105000, -1, 104000])

    def test_backfill_laps_for_existing_session(self):
        """Alte Sitzung ohne Rundendetails erhaelt sie beim erneuten
        Einlesen nachgezogen."""
        laps = [{"number": 0, "lapTimeMs": -1},
                {"number": 1, "lapTimeMs": 106000}]
        s = self._sp_session(laps)
        cur = self.db.conn.execute(
            "INSERT INTO sessions (digest, session_type, timestamp, track, "
            "layout, source_file) VALUES (?,?,?,?,?,?)",
            ("alt", s.session_type, s.timestamp, s.track, s.layout,
             s.source_file))
        self.db.conn.execute(
            "INSERT INTO entries (session_id, position, name, vehicle, "
            "laps, best_lap_ms) VALUES (?,?,?,?,?,?)",
            (cur.lastrowid, 1, "Marcel Wijnandts", "Cayman GT4", 1, 106000))
        self.db.conn.commit()
        self.assertFalse(self.db.insert_session(s, s.source_file))
        times = [r["lap_time_ms"] for r in self.db.conn.execute(
            "SELECT lap_time_ms FROM laps ORDER BY lap_no")]
        self.assertEqual(times, [-1, 106000])
