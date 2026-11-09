"""Tests for the per-track/per-vehicle aggregation (0.4.9)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc.database import Database
from rrc.models import Session, PlayerResult


class TestAggregate(unittest.TestCase):
    """0.4.9: Auswertung je Strecke und je Fahrzeug."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "results.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def _add(self, digest, typ, track, layout, laps, best, pos=0,
             status="", vehicle="BMW M4 GT3", name="Marcel Wijnandts"):
        sess = Session(session_type=typ, timestamp="2026-11-09 12:00:00",
                       track=track, layout=layout, source_file=digest + ".txt",
                       digest=digest)
        sess.players.append(PlayerResult(name=name, vehicle=vehicle,
                                         laps=laps, best_lap_ms=best,
                                         position=pos, finish_status=status))
        self.db.insert_session(sess, digest + ".txt")

    def test_group_by_track(self):
        self._add("d1", "Race", "Nordschleife", "VLN", laps=5, best=500000,
                  pos=1)
        self._add("d2", "Race", "Nordschleife", "VLN", laps=4, best=510000,
                  pos=2, status="Finished")
        self._add("d3", "Practice", "Oschersleben", "Grand Prix", laps=9,
                  best=106222)
        rows = self.db.aggregate("track")
        self.assertEqual(len(rows), 2)
        nord = rows[0] if rows[0]["label"].startswith("Nord") else rows[1]
        osch = rows[1] if nord is rows[0] else rows[0]
        self.assertEqual(nord["label"], "Nordschleife - VLN")
        self.assertEqual(nord["sessions"], 2)
        self.assertEqual(nord["races"], 2)
        self.assertEqual(nord["race_entries"], 2)
        self.assertEqual(nord["wins"], 1)
        self.assertEqual(nord["podium"], 2)
        self.assertEqual(nord["finishes"], 2)
        self.assertEqual(nord["dnfs"], 0)
        self.assertEqual(nord["total_laps"], 9)
        self.assertEqual(nord["best_ms"], 500000)
        self.assertAlmostEqual(nord["quote"], 100.0)
        self.assertEqual(osch["races"], 0)
        self.assertEqual(osch["quote"], 0.0)

    def test_group_by_vehicle_and_dnf(self):
        self._add("d1", "Race", "Nordschleife", "VLN", laps=5, best=500000,
                  pos=0, status="DNF", vehicle="Porsche 911 GT3 R")
        self._add("d2", "Race", "Oschersleben", "Grand Prix", laps=4,
                  best=400000, pos=1, vehicle="Porsche 911 GT3 R")
        self._add("d3", "Practice", "Oschersleben", "Grand Prix", laps=9,
                  best=106222, vehicle="BMW M4 GT3")
        rows = self.db.aggregate("vehicle")
        porsche = [r for r in rows if r["label"] == "Porsche 911 GT3 R"][0]
        self.assertEqual(porsche["sessions"], 2)
        self.assertEqual(porsche["races"], 2)
        self.assertEqual(porsche["race_entries"], 2)
        self.assertEqual(porsche["wins"], 1)
        self.assertEqual(porsche["dnfs"], 1)
        self.assertEqual(porsche["finishes"], 1)
        self.assertAlmostEqual(porsche["quote"], 50.0)

    def test_names_filter_and_empty(self):
        self._add("d1", "Race", "Nordschleife", "VLN", laps=5, best=500000,
                  pos=1, name="Marcel Wijnandts")
        self._add("d2", "Race", "Oschersleben", "Grand Prix", laps=4,
                  best=400000, pos=1, name="AI Driver")
        self.assertEqual(self.db.aggregate("track", names=["Marcel Wijnandts"]),
                         [r for r in self.db.aggregate("track")
                          if r["label"] == "Nordschleife - VLN"])
        self.assertEqual(self.db.aggregate("track", names=[]), [])

    def test_layout_id_not_in_label(self):
        """Unaufgeloeste Layout-Ids bleiben ohne Anhaengsel."""
        self._add("d1", "Race", "2578", "(Layout-Id)", laps=1, best=100000)
        rows = self.db.aggregate("track")
        self.assertEqual(rows[0]["label"], "2578")


if __name__ == "__main__":
    unittest.main(verbosity=2)
