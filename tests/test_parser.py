import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rrc.parser import (datetime_from_filename, parse_file, session_type_from_filename)
from rrc.models import format_time_ms

SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


class TestHelpers(unittest.TestCase):
    def test_filename_parsing(self):
        self.assertEqual(session_type_from_filename("2023_06_03_14_13_21_Race1.txt"), "Race1")
        self.assertEqual(session_type_from_filename("2023_06_03_14_13_21_Qualify.txt"), "Qualify")
        self.assertEqual(session_type_from_filename("whatever.txt"), "")
        self.assertEqual(datetime_from_filename("2023_06_03_14_13_21_Race1.txt"),
                         "2023-06-03 14:13:21")

    def test_format_time(self):
        self.assertEqual(format_time_ms(512340), "8:32.340")
        self.assertEqual(format_time_ms(79123), "1:19.123")
        self.assertEqual(format_time_ms(0), "")
        self.assertEqual(format_time_ms(None), "")


class TestSpJson(unittest.TestCase):
    def setUp(self):
        self.sessions = parse_file(os.path.join(SAMPLES, "2023_06_03_14_13_21_Race1.txt"))
        self.assertEqual(len(self.sessions), 1)
        self.sess = self.sessions[0]

    def test_header(self):
        self.assertEqual(self.sess.session_type, "Race1")
        self.assertEqual(self.sess.timestamp, "2023/06/03 14:13:45")
        self.assertEqual(self.sess.track, "Nordschleife")
        self.assertEqual(self.sess.layout, "VLN-Gesamtstrecke")
        self.assertTrue(self.sess.digest)

    def test_players(self):
        self.assertEqual(len(self.sess.players), 2)
        p = self.sess.players[0]
        self.assertEqual(p.name, "Marcel Wijnandts")
        self.assertEqual(p.vehicle, "BMW M4 GT3")
        self.assertEqual(p.position, 1)
        self.assertEqual(p.laps, 4)
        self.assertEqual(p.best_lap_ms, 512340)
        self.assertEqual(p.race_time_ms, 1800000)

    def test_reparse_stable_digest(self):
        again = parse_file(os.path.join(SAMPLES, "2023_06_03_14_13_21_Race1.txt"))
        self.assertEqual(again[0].digest, self.sess.digest)


class TestDedicatedJson(unittest.TestCase):
    def setUp(self):
        self.sessions = parse_file(os.path.join(SAMPLES, "server_result.json"))

    def test_sessions_found(self):
        self.assertEqual(len(self.sessions), 2)
        types = sorted(s.session_type for s in self.sessions)
        self.assertEqual(types, ["Qualify", "Race"])

    def test_race_content(self):
        race = next(s for s in self.sessions if s.session_type == "Race")
        self.assertEqual(race.track, "Sachsenring")
        self.assertEqual(race.layout, "ADAC GT Masters")
        self.assertEqual(len(race.players), 2)
        winner = next(p for p in race.players if p.position == 1)
        self.assertEqual(winner.name, "Fahrer B")
        self.assertEqual(winner.best_lap_ms, 81234)
        self.assertEqual(len(winner.laps_detail), 2)
        self.assertEqual(winner.laps_detail[1].lap_time_ms, 81234)
        self.assertEqual(winner.laps_detail[0].sector_times_ms, [28000, 27000, 29500])

    def test_qualify_content(self):
        quali = next(s for s in self.sessions if s.session_type == "Qualify")
        self.assertEqual(quali.players[0].name, "Marcel Wijnandts")
        self.assertEqual(quali.players[0].best_lap_ms, 79123)


class TestMpXml(unittest.TestCase):
    def setUp(self):
        self.sessions = parse_file(os.path.join(SAMPLES, "mp_result.xml"))

    def test_content(self):
        self.assertEqual(len(self.sessions), 1)
        s = self.sessions[0]
        self.assertEqual(s.session_type, "Race")
        self.assertEqual(s.track, "Hockenheim")
        self.assertEqual(s.layout, "GP")
        self.assertEqual(s.timestamp, "2024-03-02 19:01:45")
        p = s.players[0]
        self.assertEqual(p.name, "Marcel Wijnandts")
        self.assertEqual(p.vehicle, "Mercedes-AMG GT3 2020")
        self.assertEqual(p.best_lap_ms, 59870)
        self.assertEqual(len(p.laps_detail), 2)
        self.assertEqual(p.laps_detail[1].sector_times_ms[2], 20570)
        self.assertTrue(p.finished)

    def test_lap_count(self):
        self.assertEqual(self.sessions[0].players[1].laps, 2)


class TestBadInput(unittest.TestCase):
    def test_missing_file(self):
        self.assertEqual(parse_file(os.path.join(SAMPLES, "does_not_exist.txt")), [])

    def test_garbage(self):
        path = os.path.join(SAMPLES, "_garbage.txt")
        with open(path, "w") as f:
            f.write("not a result file")
        try:
            self.assertEqual(parse_file(path), [])
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
