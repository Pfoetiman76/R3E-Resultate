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

    # --------------------------------------------------------- 0.4.2 NEU --

    def test_ai_hide_entries_for(self):
        """KI-Ausblendung: nur echte Fahrer in der Detailtabelle."""
        self.db.ingest_folder(SAMPLES)
        s = next(r for r in self.db.sessions() if r["track"] == "Nordschleife")
        entries = self.db.entries_for(s["id"], names=["Marcel Wijnandts"])
        self.assertEqual([e["name"] for e in entries], ["Marcel Wijnandts"])
        self.assertEqual(self.db.entries_for(s["id"], names=[]), [])

    def test_ai_hide_sessions_counts(self):
        """n_players und Sitzungs-Bestzeit zaehlen nur echte Fahrer."""
        self.db.ingest_folder(SAMPLES)
        rows = self.db.sessions(names=["Marcel Wijnandts"])
        nord = next(r for r in rows if r["track"] == "Nordschleife")
        self.assertEqual(nord["n_players"], 1)      # AI Driver ausgeblendet
        self.assertEqual(nord["session_best_ms"], 512340)
        empty = self.db.sessions(names=[])
        self.assertEqual(empty, [])
        self.assertEqual(len(self.db.sessions(names=["Fahrer B"])), 2)

    def test_ai_hide_personal_bests_and_drivers(self):
        self.db.ingest_folder(SAMPLES)
        bests = self.db.personal_bests(names=["Marcel Wijnandts"])
        self.assertTrue(all(b["name"] == "Marcel Wijnandts" for b in bests))
        self.assertEqual(self.db.personal_bests(names=[]), [])
        self.assertEqual(self.db.drivers(names=["Marcel Wijnandts"]),
                         ["Marcel Wijnandts"])
        self.assertEqual(self.db.drivers(names=[]), [])

    def test_ai_hide_none_shows_all(self):
        """names=None = alter Zustand: alle Fahrer."""
        self.db.ingest_folder(SAMPLES)
        self.assertIn("Fahrer B", self.db.drivers(names=None))
        nord = next(r for r in self.db.sessions(names=None)
                    if r["track"] == "Nordschleife")
        self.assertEqual(nord["n_players"], 2)

    def test_totals(self):
        """Zaehler fuer die Statusleiste (0.4.3)."""
        self.db.ingest_folder(SAMPLES)
        self.assertEqual(self.db.totals(), (4, 16))  # SP 4+4, Sachsenring 2+2, Hockenheim 2+2


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestIdUpgrade(unittest.TestCase):
    """0.4.4: numeric track/vehicle IDs get renamed via upgrade_ids."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _db_with_legacy_session(self):
        from rrc.models import Session, PlayerResult
        db = Database(os.path.join(self.tmp.name, "results.db"))
        sess = Session(session_type="Race", timestamp="2023-06-03 14:13:21",
                       track="999999", layout="(Layout-Id)",
                       source_file="a.txt", digest="d-id-1")
        sess.players.append(PlayerResult(name="Marcel Wijnandts", vehicle="777777"))
        self.assertTrue(db.insert_session(sess, "a.txt"))
        return db

    def test_unresolved_lists(self):
        db = self._db_with_legacy_session()
        self.assertEqual(db.unresolved_track_ids(), ["999999"])
        self.assertEqual(db.unresolved_car_ids(), ["777777"])
        db.close()

    def test_upgrade_ids_renames(self):
        db = self._db_with_legacy_session()
        user = {"layouts": {"999999": ["Neue Strecke", "Grand Prix"]},
                "cars": {"777777": "Testwagen GT"}}
        n_t, n_v = db.upgrade_ids(user)
        self.assertEqual((n_t, n_v), (1, 1))
        rows = db.sessions()
        self.assertEqual(rows[0]["track"], "Neue Strecke")
        self.assertEqual(rows[0]["layout"], "Grand Prix")
        entries = db.entries_for(rows[0]["id"])
        self.assertEqual(entries[0]["vehicle"], "Testwagen GT")
        self.assertEqual(db.unresolved_track_ids(), [])
        db.close()


class TestStatsCorrection(unittest.TestCase):
    """0.4.6: Zielquote pro Renneinsatz, KI-Filter in der Statistik."""

    def setUp(self):
        import tempfile
        from rrc.models import Session, PlayerResult
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "results.db"))
        for i in range(4):
            s = Session(session_type="Race", timestamp=f"2023-06-0{i+1} 10:00:00",
                        track="Sachsenring", layout="",
                        source_file=f"g{i}.txt", digest=f"d-g{i}")
            # je Rennen: Marcel (Sieger), zwei KI-Fahrer (einer DNF)
            s.players.append(PlayerResult(name="Marcel Wijnandts",
                                          vehicle="Audi R8 LMS GT3",
                                          position=1, laps=10,
                                          best_lap_ms=80000))
            s.players.append(PlayerResult(name="KI A", vehicle="GT3",
                                          position=2, laps=9,
                                          best_lap_ms=82000))
            s.players.append(PlayerResult(name="KI B", vehicle="GT3",
                                          position=0, laps=5,
                                          best_lap_ms=0,
                                          finish_status="DNF"))
            self.db.insert_session(s, f"g{i}.txt")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_quote_per_race_entry_not_per_session(self):
        stats, _ = self.db.stats_summary()
        # 12 Renneinsaetze (4 Rennen x 3 Fahrer), davon 8 im Ziel
        # (pro Rennen fehlt der DNF-Fahrer)
        self.assertEqual(stats["race_entries"], 12)
        self.assertEqual(stats["finishes"], 8)
        quote = 100.0 * stats["finishes"] / stats["race_entries"]
        self.assertAlmostEqual(quote, 200.0 / 3.0)

    def test_wins_podium_without_driver_count_all(self):
        stats, _ = self.db.stats_summary()
        self.assertEqual(stats["wins"], 4)
        self.assertEqual(stats["podium"], 8)

    def test_names_filter_limits_stats(self):
        stats, _ = self.db.stats_summary(names=["Marcel Wijnandts"])
        self.assertEqual(stats["wins"], 4)
        self.assertEqual(stats["race_entries"], 4)
        self.assertEqual(stats["finishes"], 4)
        self.assertEqual(stats["total_laps"], 40)
        self.assertEqual(stats["entries"], 4)

    def test_names_filter_empty_list_zero(self):
        stats, _ = self.db.stats_summary(names=[])
        self.assertEqual(stats["races"], 0)
        self.assertEqual(stats["total_laps"], 0)

    def test_dnf_summary_names_filter(self):
        all_rows = self.db.dnf_summary()
        self.assertEqual(len(all_rows), 3)
        only = self.db.dnf_summary(names=["Marcel Wijnandts"])
        self.assertEqual(len(only), 1)
        self.assertEqual(only[0]["dnfs"], 0)
        self.assertEqual(only[0]["starts"], 4)

    def test_driver_and_names_combined(self):
        stats, _ = self.db.stats_summary(driver="KI B")
        self.assertEqual(stats["race_entries"], 4)
        self.assertEqual(stats["finishes"], 0)


class TestTimestampMigration(unittest.TestCase):
    """0.5.2: Schraegstrich-Zeitstempel ('YYYY/MM/DD ...') aus aelteren
    Versionen werden beim Oeffnen normalisiert; der Datums-Filter greift."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.path = os.path.join(self.tmp.name, "migrate.db")

    def tearDown(self):
        self.tmp.cleanup()

    def _insert_legacy(self):
        import sqlite3
        conn = sqlite3.connect(self.path)
        conn.execute(
            "INSERT INTO sessions (digest, session_type, timestamp, track,"
            " layout, source_file) VALUES ('d1', 'Practice',"
            " '2026/11/09 20:44:53', 'Monza', '', 'leg.txt')")
        conn.commit()
        conn.close()

    def test_migration_normalizes_legacy_rows(self):
        from rrc.database import _SCHEMA
        import sqlite3
        conn = sqlite3.connect(self.path)
        conn.executescript(_SCHEMA)
        conn.commit()
        conn.close()
        self._insert_legacy()
        db = Database(self.path)
        try:
            rows = db.sessions()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["timestamp"], "2026-11-09 20:44:53")
        finally:
            db.close()

    def test_date_filter_matches_sessions(self):
        db = Database(self.path)
        try:
            db.ingest_folder(SAMPLES)
            rows = db.sessions(date_from="2023-06-01", date_to="2023-06-30")
            self.assertTrue(rows, "Datums-Filter muss die SP-Sitzung finden")
            for r in rows:
                self.assertNotIn("/", r["timestamp"])
            # Zeitraum weit in der Zukunft -> leer (die Beispieldateien
            # enthalten Sitzungen ueber mehrere Jahre)
            self.assertEqual(db.sessions(date_from="2099-01-01"), [])
        finally:
            db.close()
