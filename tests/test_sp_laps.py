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
        """Nur Runden mit gueltiger Zeit zaehlen; -1-Platzhalter entfallen."""
        s = self._session([
            _driver("Marcel Wijnandts", 2,
                    [{"number": 0, "lapTimeMs": -1},
                     {"number": 1, "lapTimeMs": 106222}]),
        ])
        p = s.players[0]
        self.assertEqual(p.laps, 1)
        self.assertEqual(len(p.laps_detail), 1)
        self.assertEqual(p.laps_detail[0].lap_time_ms, 106222)

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
        sess = Session(session_type="Race", timestamp="2026-11-07 20:44:53",
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
