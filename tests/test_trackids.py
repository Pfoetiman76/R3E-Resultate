"""Tests for rrc.trackids and ID resolution (0.4.4)."""
import json
import os
import tempfile
import unittest

from rrc import trackids


class TestBuiltinTables(unittest.TestCase):
    def test_known_layout(self):
        self.assertEqual(trackids.resolve_layout(12112),
                         ("Hockenheimring Classic", "Grand Prix"))

    def test_unknown_layout(self):
        self.assertIsNone(trackids.resolve_layout(999999999))

    def test_known_car(self):
        self.assertEqual(trackids.resolve_car(252), "Aquila CR1 Sports GT")

    def test_unknown_car(self):
        self.assertIsNone(trackids.resolve_car(999999999))

    def test_is_id(self):
        self.assertTrue(trackids.is_id("12112"))
        self.assertFalse(trackids.is_id("Hockenheim"))
        self.assertFalse(trackids.is_id(""))
        self.assertFalse(trackids.is_id("12a"))


class TestUserNames(unittest.TestCase):
    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "track_names.json")
            data = {"layouts": {"999999": ["Testbahn", "Lang"]},
                    "cars": {"888888": "Testwagen"}}
            trackids.save_user_names(p, data)
            loaded = trackids.load_user_names(p)
            self.assertEqual(loaded["layouts"]["999999"], ["Testbahn", "Lang"])
            self.assertEqual(loaded["cars"]["888888"], "Testwagen")

    def test_load_missing_file(self):
        loaded = trackids.load_user_names(os.path.join("no", "such", "file"))
        self.assertEqual(loaded, {"layouts": {}, "cars": {}})

    def test_resolve_with_user_override(self):
        user = {"layouts": {"12112": ["Eigener Name", "GP"]},
                "cars": {}}
        self.assertEqual(trackids.resolve_layout_with("12112", user),
                         ("Eigener Name", "GP"))
        self.assertEqual(trackids.resolve_layout_with(12112, None),
                         ("Hockenheimring Classic", "Grand Prix"))
        self.assertEqual(trackids.resolve_car_with("252", user),
                         "Aquila CR1 Sports GT")


if __name__ == "__main__":
    unittest.main()
