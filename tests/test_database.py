import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rrc.database import Database

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "test.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_ingest_folder(self):
        added, skipped, errors = self.db.ingest_folder(SAMPLES)
        # SP file: 1 session, server JSON: 2 sessions, XML: 1 session
        self.assertEqual(added, 4)
        self.assertEqual(errors, 0)
        rows = self.db.sessions()
        self.assertEqual(len(rows), 4)

    def test_dedupe(self):
        self.db.ingest_folder(SAMPLES)
        added, skipped, errors = self.db.ingest_folder(SAMPLES)
        self.assertEqual(added, 0)
        self.assertEqual(skipped, 3)

    def test_entries_for_session(self):
        self.db.ingest_folder(SAMPLES)
        rows = self.db.sessions()
        s = next(r for r in rows if r["session_type"] == "Race1")
        entries = self.db.entries_for(s["id"])
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["name"], "Marcel Wijnandts")
        self.assertEqual(entries[0]["best_lap_ms"], 512340)

    def test_personal_bests(self):
        self.db.ingest_folder(SAMPLES)
        bests = self.db.personal_bests("Marcel Wijnandts")
        self.assertTrue(all(b["name"] == "Marcel Wijnandts" for b in bests))
        # Nordschleife 512340, Hockenheim 59870, Sachsenring-Quali 79123
        got = {(b["track"], b["best_ms"]) for b in bests}
        self.assertIn(("Nordschleife", 512340), got)
        self.assertIn(("Hockenheim", 59870), got)
        self.assertIn(("Sachsenring", 79123), got)

    def test_drivers_and_stats(self):
        self.db.ingest_folder(SAMPLES)
        drivers = self.db.drivers()
        self.assertIn("Marcel Wijnandts", drivers)
        self.assertIn("Fahrer B", drivers)
        stats, wins = self.db.stats_summary("Marcel Wijnandts")
        self.assertGreaterEqual(stats["sessions"], 2)
        self.assertEqual(stats["races"], 3)  # SP Race1 + Sachsenring-Rennen + Hockenheim
        self.assertEqual(wins, 2)  # SP-Race1 + Hockenheim (in Samples Pos. 1)
        self.assertGreaterEqual(stats["total_laps"], 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
