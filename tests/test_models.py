import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rrc.models import APP_VERSION, delta_class, format_time_ms


class TestFormatTime(unittest.TestCase):
    def test_formatting(self):
        self.assertEqual(format_time_ms(512340), "8:32.340")
        self.assertEqual(format_time_ms(59870), "0:59.870")
        self.assertEqual(format_time_ms(0), "")
        self.assertEqual(format_time_ms(None), "")
        self.assertEqual(format_time_ms(-5), "")


class TestDeltaClass(unittest.TestCase):
    def test_good(self):
        # Rekordrunde oder schneller
        self.assertEqual(delta_class(0, 60000), "good")
        self.assertEqual(delta_class(-120, 60000), "good")

    def test_near(self):
        # innerhalb 2 % der Rekordzeit
        self.assertEqual(delta_class(600, 60000), "near")
        self.assertEqual(delta_class(1200, 60000), "near")

    def test_bad(self):
        # ueber 2 Sekunden langsamer
        self.assertEqual(delta_class(2500, 60000), "bad")

    def test_neutral(self):
        # zwischen "nah dran" (bis 2 % = 1200 ms) und Ausrutscher (> 2000 ms)
        self.assertEqual(delta_class(1500, 60000), "")
        # keine Bewertung moeglich
        self.assertEqual(delta_class(500, 0), "")
        self.assertEqual(delta_class(None, 60000), "")
        self.assertEqual(delta_class("x", 60000), "")

    def test_version_format(self):
        # Tag und APP_VERSION muessen identisch sein (Updater-Regel)
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main(verbosity=2)
