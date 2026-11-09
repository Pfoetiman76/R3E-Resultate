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
        self.assertEqual(stats["races"], 3)
        self.assertEqual(wins, 2)
        self.assertEqual(stats["podium"], 3)   # Pos. 1/2/2 in den drei Rennen
        self.assertEqual(stats["finishes"], 3)  # alle Finished
        self.assertGreaterEqual(stats["total_laps"], 8)

    # --------------------------------------------------------- 0.3.0 NEU --

    def test_laps_stored(self):
        """Sektorenzeiten aus Server-XML/JSON muessen in der laps-Tabelle landen."""
        self.db.ingest_folder(SAMPLES)
        with_laps = self.db.sessions_with_laps()
        self.assertEqual(len(with_laps), 2)  # Sachsenring-Rennen + Hockenheim
        xml = next(r for r in with_laps if r["track"] == "Hockenheim")
        laps = self.db.laps_for_session(xml["id"])
        self.assertEqual(len(laps), 4)  # 2 Fahrer x 2 Runden
        marcel = [l for l in laps if l["name"] == "Marcel Wijnandts"]
        self.assertEqual(len(marcel), 2)
        self.assertEqual(marcel[0]["lap_time_ms"], 61000)
        self.assertEqual([marcel[0]["s1_ms"], marcel[0]["s2_ms"], marcel[0]["s3_ms"]],
                         [20000, 20000, 21000])

    def test_sessions_with_laps_excludes_sp(self):
        """SP-Ergebnisse haben keine Rundendetails -> nicht in der Runden-Liste."""
        self.db.ingest_folder(SAMPLES)
        tracks = {r["track"] for r in self.db.sessions_with_laps()}
        self.assertNotIn("Nordschleife", tracks)
        self.assertIn("Sachsenring", tracks)

    def test_search_filter(self):
        self.db.ingest_folder(SAMPLES)
        hits = self.db.sessions(search="Hockenheim")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["track"], "Hockenheim")
        self.assertEqual(len(self.db.sessions(search="gibtsnicht")), 0)
        races = self.db.sessions(session_type="Race")
        self.assertEqual({r["session_type"] for r in races}, {"Race", "Race1"})
        by_driver = self.db.sessions(driver="Fahrer B")
        self.assertTrue(all(r["n_players"] >= 1 for r in by_driver))
        self.assertEqual(len(by_driver), 2)  # Qualify + Race Sachsenring

    def test_progression(self):
        self.db.ingest_folder(SAMPLES)
        prog = self.db.progression("Hockenheim", "GP", driver="Marcel Wijnandts")
        self.assertEqual(len(prog), 1)
        self.assertEqual(prog[0]["best_ms"], 59870)
        prog_all = self.db.progression("Hockenheim", "GP")
        self.assertEqual(prog_all[0]["best_ms"], 59870)

    def test_dnf_summary_and_sessions(self):
        """Sachsenring-Rennen bekommt einen kuenstlichen DNF zur Pruefung."""
        self.db.ingest_folder(SAMPLES)
        s = next(r for r in self.db.sessions() if r["session_type"] == "Race"
                 and r["track"] == "Sachsenring")
        self.db.conn.execute(
            "UPDATE entries SET finish_status = 'Accident' "
            "WHERE session_id = ? AND name = 'Marcel Wijnandts'", (s["id"],))
        self.db.conn.commit()
        summary = self.db.dnf_summary("Marcel Wijnandts")
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["starts"], 3)
        self.assertEqual(summary[0]["dnfs"], 1)
        self.assertAlmostEqual(summary[0]["finish_rate"], 66.7, places=1)
        dnf_list = self.db.dnf_sessions("Marcel Wijnandts")
        self.assertEqual(len(dnf_list), 1)
        self.assertEqual(dnf_list[0]["finish_status"], "Accident")

    def test_tracks_listing(self):
        self.db.ingest_folder(SAMPLES)
        combos = {(r["track"], r["layout"]) for r in self.db.tracks()}
        self.assertIn(("Hockenheim", "GP"), combos)
        self.assertIn(("Nordschleife", "VLN-Gesamtstrecke"), combos)

    # --------------------------------------------------------- 0.4.0 NEU --

    def test_avg_lap_ms_from_laps(self):
        """Hockenheim: Marcels Runden 61000 + 59870 ms -> Mittel 60435."""
        self.db.ingest_folder(SAMPLES)
        avg = self.db.avg_lap_ms("Hockenheim", layout="GP",
                                 vehicle="Mercedes-AMG GT3 2020",
                                 driver="Marcel Wijnandts")
        self.assertAlmostEqual(avg, 60435.0, places=1)

    def test_avg_lap_ms_fallback_best(self):
        """Nordschleife (SP) hat keine laps -> Fallback auf best_lap_ms."""
        self.db.ingest_folder(SAMPLES)
        avg = self.db.avg_lap_ms("Nordschleife", layout="VLN-Gesamtstrecke")
        self.assertAlmostEqual(avg, (512340 + 522100) / 2, places=1)

    def test_avg_lap_ms_unknown(self):
        self.db.ingest_folder(SAMPLES)
        self.assertIsNone(self.db.avg_lap_ms("gibtsnicht"))

    def test_vehicles_for_track(self):
        self.db.ingest_folder(SAMPLES)
        vehicles = self.db.vehicles_for_track("Hockenheim")
        self.assertEqual(vehicles, ["Mercedes-AMG GT3 2020"])
        self.assertEqual(self.db.vehicles_for_track("gibtsnicht"), [])

    # --------------------------------------------------------- 0.4.1 NEU --

    def test_track_records_hockenheim(self):
        """Laps-basiert: Renn-Rekord, Allzeit, Optimal aus Sektorenbesten."""
        self.db.ingest_folder(SAMPLES)
        rec = self.db.track_records("Hockenheim", layout="GP")
        self.assertEqual(rec["race_ms"], 59870)
        self.assertIsNone(rec["qualify_ms"])   # keine Qualify-Sitzung vorhanden
        self.assertEqual(rec["best_ms"], 59870)
        # beste Sektoren: 19500 + 19800 + 20570 = 59870
        self.assertEqual(rec["optimal_ms"], 59870)

    def test_track_records_sachsenring_fallbacks(self):
        """Qualify ohne laps -> Fallback auf best_lap_ms; Optimal aus Gemisch."""
        self.db.ingest_folder(SAMPLES)
        rec = self.db.track_records("Sachsenring", layout="ADAC GT Masters")
        self.assertEqual(rec["qualify_ms"], 79123)  # Fallback best_lap_ms
        self.assertEqual(rec["race_ms"], 81234)    # echte Runde (Fahrer B)
        self.assertEqual(rec["best_ms"], 81234)
        # Sektorenbesten ueber beide Fahrer: 26500 + 26000 + 28234 = 80734
        self.assertEqual(rec["optimal_ms"], 80734)

    def test_track_records_nordschleine_fallback(self):
        """SP-Ergebnis ohne laps: Renn-Rekord aus best_lap_ms, keine Optimal."""
        self.db.ingest_folder(SAMPLES)
        rec = self.db.track_records("Nordschleife", layout="VLN-Gesamtstrecke")
        self.assertEqual(rec["race_ms"], 512340)    # Race1 zaehlt zu Race%
        self.assertEqual(rec["best_ms"], 512340)
        self.assertIsNone(rec["optimal_ms"])

    def test_track_records_empty(self):
        self.db.ingest_folder(SAMPLES)
        rec = self.db.track_records("gibtsnicht")
        self.assertIsNone(rec["race_ms"])
        self.assertIsNone(rec["qualify_ms"])
        self.assertIsNone(rec["best_ms"])
        self.assertIsNone(rec["optimal_ms"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
