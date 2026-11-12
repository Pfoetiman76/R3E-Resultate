"""Tests fuer 0.5.0: Shared-Memory-Reader (synthetischer Speicherblock)."""
import ctypes
import os
import sys
import unittest
from ctypes import c_ubyte

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc.raceroom_sm import (R3EReader, R3EShared, R3EDriverData,
                             R3E_VERSION_MAJOR)


def _block(menus=0, replay=0, control=0, session=0, laps=3,
           prev_time=65.432, valid_state=1, fuel=38.2, cap=60.0,
           model_id=10914):
    """Synthetischer $R3E-Block (nur lesende Auswertung, kein Spiel noetig)."""
    d = R3EShared()
    d.version_major, d.version_minor = R3E_VERSION_MAJOR, 5
    d.driver_data_size = ctypes.sizeof(R3EDriverData)
    d.all_drivers_offset = R3EShared.num_cars.offset
    d.game_in_menus, d.game_in_replay = menus, replay
    d.control_type = control
    d.session_type = session
    d.track_name = (c_ubyte * 64)(*b"Norisring")
    d.layout_name = (c_ubyte * 64)()
    d.track_id, d.layout_id = 1690, 1691
    d.player_name = (c_ubyte * 64)(*b"Marcel Wijnandts")
    d.vehicle_info.model_id = model_id
    d.completed_laps = laps
    d.lap_valid_state = valid_state
    d.lap_time_previous_self = prev_time
    d.fuel_left, d.fuel_capacity, d.fuel_per_lap = fuel, cap, 3.1
    return d


class TestR3EReader(unittest.TestCase):

    def test_version(self):
        from rrc.models import APP_VERSION
        self.assertEqual(APP_VERSION, "0.5.1")

    def test_felder(self):
        d = _block()
        s = R3EReader(raw_provider=lambda: bytes(d)).read()
        self.assertEqual(s.track_name, "Norisring")
        self.assertEqual(s.track_id, 1690)
        self.assertEqual(s.player_name, "Marcel Wijnandts")
        self.assertEqual(s.model_id, 10914)
        self.assertEqual(s.session_type, "Practice")
        self.assertEqual(s.completed_laps, 3)
        self.assertAlmostEqual(s.lap_time_previous_s, 65.432, delta=1e-4)
        self.assertAlmostEqual(s.fuel_left, 38.2, delta=1e-4)
        self.assertAlmostEqual(s.fuel_capacity, 60.0, delta=1e-4)
        self.assertTrue(s.in_car)

    def test_menu_ergibt_none(self):
        d = _block(menus=1)
        self.assertIsNone(R3EReader(raw_provider=lambda: bytes(d)).read())
        d = _block(replay=1)
        self.assertIsNone(R3EReader(raw_provider=lambda: bytes(d)).read())

    def test_ungueltige_vorrunde(self):
        # lap_valid_state in (1, 2) = vorherige Runde ungueltig
        d = _block(valid_state=1)
        s = R3EReader(raw_provider=lambda: bytes(d)).read()
        self.assertEqual(s.prev_lap_valid, 0)
        d = _block(valid_state=2)
        s = R3EReader(raw_provider=lambda: bytes(d)).read()
        self.assertEqual(s.prev_lap_valid, 0)
        d = _block(valid_state=3)
        s = R3EReader(raw_provider=lambda: bytes(d)).read()
        self.assertEqual(s.prev_lap_valid, 1)

    def test_nicht_im_auto(self):
        d = _block(control=1)     # 0 = Spieler, alles andere = Nicht-Spieler
        s = R3EReader(raw_provider=lambda: bytes(d)).read()
        self.assertFalse(s.in_car)

    def test_aktiv_unbekannt(self):
        d = _block()
        d.version_major = 0     # Spiel schreibt noch nicht
        r = R3EReader(raw_provider=lambda: bytes(d))
        with self.assertRaises(RuntimeError):
            r.read()


if __name__ == "__main__":
    unittest.main(verbosity=2)
