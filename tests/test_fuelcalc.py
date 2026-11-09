import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rrc import fuelcalc


class TestFuelCalc(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_conversions(self):
        # 60,435 s Runde -> 10 Minuten = 9,93... Runden
        self.assertAlmostEqual(fuelcalc.laps_from_minutes(10, 60.435), 9.928, places=2)
        self.assertAlmostEqual(fuelcalc.minutes_from_laps(10, 60.0), 10.0, places=6)
        self.assertEqual(fuelcalc.laps_from_minutes(10, 0), 0.0)
        self.assertEqual(fuelcalc.minutes_from_laps(5, None), 0.0)

    def test_fuel_needed(self):
        self.assertAlmostEqual(fuelcalc.fuel_needed(10, 3.25), 32.5, places=6)
        self.assertEqual(fuelcalc.fuel_needed(10, 0), 0.0)
        self.assertEqual(fuelcalc.fuel_needed(10, None), 0.0)

    def test_tank_check(self):
        self.assertTrue(fuelcalc.fits_tank(30.0, 32.0))
        self.assertFalse(fuelcalc.fits_tank(33.0, 32.0))
        self.assertTrue(fuelcalc.fits_tank(500.0, None))  # Tank unbekannt
        self.assertTrue(fuelcalc.fits_tank(30.0, 0))      # Tank nicht gepflegt

    def test_history_roundtrip(self):
        path = fuelcalc.history_path(self.tmp.name)
        self.assertEqual(fuelcalc.load_history(path), {})  # noch nichts da

        hist = {}
        fuelcalc.put_entry(hist, "Hockenheim", "Mercedes-AMG GT3 2020", 3.1, 120.0)
        fuelcalc.put_entry(hist, "Hockenheim", "Mercedes-AMG GT3 2020", 3.2, None)
        fuelcalc.save_history(path, hist)

        loaded = fuelcalc.load_history(path)
        key = fuelcalc.entry_key("Hockenheim", "Mercedes-AMG GT3 2020")
        self.assertIn(key, loaded)
        e = fuelcalc.get_entry(loaded, "Hockenheim", "Mercedes-AMG GT3 2020")
        self.assertAlmostEqual(e["fuel_l"], 3.2)   # Update greift
        self.assertAlmostEqual(e["capacity"], 120.0)  # None aendert nichts

    def test_get_entry_missing(self):
        self.assertEqual(fuelcalc.get_entry({}, "X", "Y"), {})

    def test_corrupt_history(self):
        path = fuelcalc.history_path(self.tmp.name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("{kein gueltiges json")
        self.assertEqual(fuelcalc.load_history(path), {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
