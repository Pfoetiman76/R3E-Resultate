import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rrc import appsettings


class TestAppSettings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_for_missing_file(self):
        path = appsettings.settings_path(self.tmp.name)
        s = appsettings.load_settings(path)
        self.assertEqual(s["real_drivers"], [])
        self.assertFalse(s["hide_ai"])

    def test_roundtrip(self):
        path = appsettings.settings_path(self.tmp.name)
        saved = appsettings.save_settings(path, {
            "real_drivers": ["Marcel Wijnandts", "Fahrer B"],
            "hide_ai": True})
        self.assertEqual(saved["real_drivers"], ["Marcel Wijnandts", "Fahrer B"])
        self.assertTrue(saved["hide_ai"])
        s = appsettings.load_settings(path)
        self.assertEqual(s["real_drivers"], ["Marcel Wijnandts", "Fahrer B"])
        self.assertTrue(s["hide_ai"])

    def test_cleanup_and_unknown_keys(self):
        path = appsettings.settings_path(self.tmp.name)
        # Leere Eintraege werden herausgefiltert, Unbekannte ignoriert
        saved = appsettings.save_settings(path, {
            "real_drivers": ["Marcel Wijnandts", "  ", ""],
            "hide_ai": True, "unbekannt": "weg"})
        self.assertEqual(saved["real_drivers"], ["Marcel Wijnandts"])
        self.assertNotIn("unbekannt", saved)  # nur bekannte Schluessel werden gespeichert
        s = appsettings.load_settings(path)
        self.assertNotIn("unbekannt", s)
        self.assertEqual(s["real_drivers"], ["Marcel Wijnandts"])

    def test_corrupt_file_yields_defaults(self):
        path = appsettings.settings_path(self.tmp.name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("{kein json")
        s = appsettings.load_settings(path)
        self.assertEqual(s, {"real_drivers": [], "hide_ai": False,
                             "r3e_install_dir": ""})

    def test_real_drivers_string_is_split(self):
        """Alte/handgeschriebene Datei mit String statt Liste wird vertragen."""
        path = appsettings.settings_path(self.tmp.name)
        with open(path, "w", encoding="utf-8") as f:
            f.write('{"real_drivers": "Marcel Wijnandts, Fahrer B", "hide_ai": true}')
        s = appsettings.load_settings(path)
        self.assertEqual(s["real_drivers"], ["Marcel Wijnandts", "Fahrer B"])
        self.assertTrue(s["hide_ai"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
