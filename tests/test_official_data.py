"""Tests for the official RaceRoom game data (r3e-data.json, 0.4.7)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc import trackids
from rrc import appsettings

GAME_DATA = {
    "tracks": {
        "42": {"Name": "Testring",
               "layouts": [{"Id": 2578, "Name": "Grand Prix"},
                           {"Id": 13428, "Name": "Kurz"}]},
    },
    "cars": {"13524": {"Name": "Porsche 911 GT3 R"},
             "17112": {"Name": "Audi R8 LMS GT3"}},
}

OVERLAY_DATA = {
    "tracks": {"7": {"Name": "Overlay-Ring"}},
    "layouts": {"9911": {"Name": "Lang", "TrackId": 7}},
    "cars": {"555": {"Name": "Community-Wagen"}},
}


class TestOfficialData(unittest.TestCase):
    """0.4.7: loading the game's own r3e-data.json."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.install = os.path.join(self.tmp.name, "RaceRoom Racing Experience")
        self.data_dir = os.path.join(self.install, "Game", "GameData", "General")
        os.makedirs(self.data_dir)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, data):
        with open(os.path.join(self.data_dir, "r3e-data.json"), "w",
                  encoding="utf-8") as f:
            json.dump(data, f)

    def test_find_and_path(self):
        self._write(GAME_DATA)
        self.assertEqual(trackids.official_data_path(self.install),
                         os.path.join(self.data_dir, "r3e-data.json"))
        found = trackids.find_official_data(self.install)
        self.assertTrue(found and found.endswith("r3e-data.json"))
        self.assertIsNone(trackids.find_official_data(
            os.path.join(self.tmp.name, "gibtsnicht")))
        self.assertIsNone(trackids.find_official_data(""))

    def test_load_official_game_schema(self):
        self._write(GAME_DATA)
        official = trackids.load_official(self.install)
        self.assertEqual(official["layouts"][2578], ("Testring", "Grand Prix"))
        self.assertEqual(official["layouts"][13428], ("Testring", "Kurz"))
        self.assertEqual(official["cars"][13524], "Porsche 911 GT3 R")
        self.assertEqual(official["cars"][17112], "Audi R8 LMS GT3")

    def test_load_official_overlay_schema(self):
        self._write(OVERLAY_DATA)
        official = trackids.load_official(self.install)
        self.assertEqual(official["layouts"][9911], ("Overlay-Ring", "Lang"))
        self.assertEqual(official["cars"][555], "Community-Wagen")

    def test_load_official_invalid(self):
        self.assertIsNone(trackids.load_official(self.install))  # no file
        self._write({"nichts": "brauchbares"})
        self.assertIsNone(trackids.load_official(self.install))
        with open(os.path.join(self.data_dir, "r3e-data.json"), "w",
                  encoding="utf-8") as f:
            f.write("{kein json")
        self.assertIsNone(trackids.load_official(self.install))

    def test_resolution_priority(self):
        self._write(GAME_DATA)
        official = trackids.load_official(self.install)
        user = {"layouts": {"2578": ["Mein Ring", "Eigen"]},
                "cars": {"13524": "Mein Wagen"}}
        # Nutzerzuordnung hat Vorrang
        self.assertEqual(trackids.resolve_layout_with(2578, user, official),
                         ("Mein Ring", "Eigen"))
        self.assertEqual(trackids.resolve_car_with(13524, user, official),
                         "Mein Wagen")
        # offizielle Daten vor eingebauten Tabellen
        self.assertEqual(trackids.resolve_layout_with(13428, None, official),
                         ("Testring", "Kurz"))
        # eingebaute Tabelle als Fallback (Hockenheimring Classic GP)
        self.assertEqual(trackids.resolve_layout_with(12112, None, official),
                         trackids.resolve_layout(12112))
        self.assertIsNotNone(trackids.resolve_layout(12112))
        # ohne alles: None
        self.assertIsNone(trackids.resolve_layout_with(999999999))
        self.assertIsNone(trackids.resolve_car_with(999999999))


class TestOfficialUpgrade(unittest.TestCase):
    """0.4.7: upgrade_ids resolves IDs via the official game data."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_upgrade_ids_with_official(self):
        from rrc.database import Database
        from rrc.models import Session, PlayerResult
        db = Database(os.path.join(self.tmp.name, "results.db"))
        sess = Session(session_type="Race", timestamp="2026-11-09 12:00:00",
                       track="2578", layout="(Layout-Id)", source_file="a.txt",
                       digest="d-official-1")
        sess.players.append(PlayerResult(name="Marcel Wijnandts",
                                         vehicle="17112"))
        self.assertTrue(db.insert_session(sess, "a.txt"))
        official = {"layouts": {2578: ("Testring", "Grand Prix")},
                    "cars": {17112: "Audi R8 LMS GT3"}}
        n_t, n_v = db.upgrade_ids({}, official)
        self.assertEqual((n_t, n_v), (1, 1))
        rows = db.sessions()
        self.assertEqual(rows[0]["track"], "Testring")
        self.assertEqual(rows[0]["layout"], "Grand Prix")
        entries = db.entries_for(rows[0]["id"])
        self.assertEqual(entries[0]["vehicle"], "Audi R8 LMS GT3")
        self.assertEqual(db.unresolved_track_ids(), [])
        db.close()


class TestSettingsInstallDir(unittest.TestCase):
    """0.4.7: settings.json stores the RaceRoom installation folder."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_and_roundtrip(self):
        import os
        path = os.path.join(self.tmp.name, "settings.json")
        s = appsettings.load_settings(path)
        self.assertEqual(s["r3e_install_dir"], "")
        s["r3e_install_dir"] = r"C:\Spiele\RaceRoom"
        appsettings.save_settings(path, s)
        s2 = appsettings.load_settings(path)
        self.assertEqual(s2["r3e_install_dir"], r"C:\Spiele\RaceRoom")


if __name__ == "__main__":
    unittest.main(verbosity=2)
