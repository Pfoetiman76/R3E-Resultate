"""Tests fuer 0.6.0: Live-Tab-Logik (rrc/livetab.py) und Recorder-Anbindung."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc.livetab import (LiveState, TrackMapCollector, fmt_lap_ms,
                         fmt_sector_s, sectors_to_ms)
from rrc.models import APP_VERSION


def sample(**kw):
    """LiveSample-aehnliches Objekt mit Standardwerten."""
    base = dict(in_car=True, session_type="Practice", track_name="Norisring",
                layout_name="", track_id=1690, layout_id=0,
                player_name="Marcel Wijnandts", model_id=10914,
                speed=80.0, pos_x=0.0, pos_z=0.0,
                completed_laps=2, lap_time_current_s=41.2,
                lap_time_previous_s=63.4, prev_lap_valid=1,
                lap_time_best_s=62.1, delta_best_s=-0.8,
                sector_current=[30.1, None, None],
                sector_previous=[29.5, 31.0, 32.9],
                sector_best=[28.9, 30.2, 32.0],
                sector_starts=[0.0, 0.4, 0.7], track_sector=1,
                fuel_left=30.0, fuel_capacity=60.0, fuel_per_lap=3.0)
    base.update(kw)
    return type("S", (), base)()


class TestVersion(unittest.TestCase):
    def test_version(self):
        self.assertEqual(APP_VERSION, "0.6.0")


class TestFormatHelper(unittest.TestCase):
    def test_fmt_lap_ms(self):
        self.assertEqual(fmt_lap_ms(51234), "51.234")
        self.assertEqual(fmt_lap_ms(395123), "6:35.123")
        self.assertEqual(fmt_lap_ms(None), "")
        self.assertEqual(fmt_lap_ms(0), "")

    def test_fmt_sector_s(self):
        self.assertEqual(fmt_sector_s(31.456), "31.456")
        self.assertEqual(fmt_sector_s(None), "")
        self.assertEqual(fmt_sector_s(0.0), "")

    def test_sectors_to_ms(self):
        self.assertEqual(sectors_to_ms([30.5, 31.25, None]),
                         [30500, 31250, -1])
        self.assertEqual(sectors_to_ms(None), [-1, -1, -1])
        self.assertEqual(sectors_to_ms([1.0]), [1000, -1, -1])


class TestTrackMapCollector(unittest.TestCase):
    def test_drosselung_nur_bewegte_punkte(self):
        m = TrackMapCollector()
        s = sample(speed=10.0, pos_x=0.0, pos_z=0.0)
        self.assertTrue(m.add(s))          # erster Punkt immer
        self.assertFalse(m.add(sample(speed=10.0, pos_x=1.0, pos_z=0.0)))
        self.assertTrue(m.add(sample(speed=10.0, pos_x=10.0, pos_z=0.0)))
        self.assertEqual(len(m.points), 2)

    def test_stehendes_fahrzeug_wird_ignoriert(self):
        m = TrackMapCollector()
        self.assertFalse(m.add(sample(speed=0.0)))
        self.assertEqual(m.points, [])

    def test_normalisierung(self):
        m = TrackMapCollector()
        m.add(sample(speed=10.0, pos_x=0.0, pos_z=0.0))
        m.add(sample(speed=10.0, pos_x=100.0, pos_z=50.0))
        pts = m.normalized()
        self.assertEqual(len(pts), 2)
        self.assertEqual(pts[0], (0.0, 0.0))
        self.assertEqual(pts[1], (1.0, 1.0))
        pos = m.normalized_pos(sample(pos_x=50.0, pos_z=25.0))
        self.assertEqual(pos, (0.5, 0.5))

    def test_reset(self):
        m = TrackMapCollector()
        m.add(sample(speed=10.0))
        m.reset()
        self.assertEqual(m.points, [])

    def test_punktelimit(self):
        m = TrackMapCollector()
        for i in range(4200):
            m.add(sample(speed=10.0, pos_x=i * 10.0, pos_z=0.0))
        self.assertLessEqual(len(m.points), 4000)


class TestLiveState(unittest.TestCase):
    def test_update_ohne_sitzung(self):
        st = LiveState()
        st.update(None, "Warte auf RaceRoom-Sitzung …")
        self.assertFalse(st.active)
        self.assertEqual(st.status, "Warte auf RaceRoom-Sitzung …")
        self.assertEqual(st.laps, [])

    def test_update_mit_sitzung(self):
        st = LiveState()
        st.update(sample())
        self.assertTrue(st.active)
        self.assertEqual(st.track_label, "Norisring")
        self.assertEqual(st.lap_no, 2)
        self.assertEqual(st.last_lap_ms, 63400)
        self.assertEqual(st.best_lap_ms, 62100)
        self.assertEqual(st.sector_best, (28.9, 30.2, 32.0))
        self.assertEqual(st.fuel_left, 30.0)
        self.assertAlmostEqual(st.fuel_laps_left(), 10.0)

    def test_set_laps_reihenfolge_und_markierung(self):
        st = LiveState()
        laps = [
            {"lap_no": 1, "time_ms": 65000, "valid": 1,
             "sectors_ms": [30000, 32000, 3000], "fuel_after": 40.0},
            {"lap_no": 2, "time_ms": 63000, "valid": 1,
             "sectors_ms": [29000, 31000, 3000], "fuel_after": 37.0},
            {"lap_no": 3, "time_ms": 68000, "valid": 0,
             "sectors_ms": [-1, -1, -1], "fuel_after": 34.0},
        ]
        st.set_laps(laps)
        # neueste zuerst
        self.assertEqual([r["lap_no"] for r in st.laps], [3, 2, 1])
        self.assertFalse(st.laps[0]["valid"])
        self.assertTrue(st.laps[1]["best"])      # 63000 = Bestzeit
        self.assertFalse(st.laps[2]["best"])
        # Sitzungs-Bestzeit aus Rundenliste uebernehmen
        self.assertEqual(st.best_lap_ms, 63000)

    def test_unvollstaendige_sektoren_bleiben_negativ(self):
        self.assertEqual(sectors_to_ms([10.0, None, 12.0]),
                         [10000, -1, 12000])


class TestRecorderLiveIntegration(unittest.TestCase):
    """Recorder speist LiveState und speichert Sektoren je Runde."""

    def test_tick_aktualisiert_live_state(self):
        from rrc.recorder import LapRecorder

        class FakeReader:
            def read(self):
                return sample()

        with tempfile.TemporaryDirectory() as td:
            rec = LapRecorder(td, reader=FakeReader())
            status, _ = rec.tick()
            self.assertEqual(status, "ok")
            self.assertTrue(rec.live.active)
            self.assertEqual(rec.live.track_label, "Norisring")
            rec.close()

    def test_runde_mit_sektoren(self):
        from rrc.recorder import LapRecorder

        seq = [sample(completed_laps=0),
               sample(completed_laps=1, lap_time_previous_s=63.4,
                      prev_lap_valid=1,
                      sector_previous=[29.5, 31.0, 32.9])]

        class FakeReader:
            def __init__(self):
                self.i = 0

            def read(self):
                s = seq[min(self.i, len(seq) - 1)]
                self.i += 1
                return s

        with tempfile.TemporaryDirectory() as td:
            rec = LapRecorder(td, reader=FakeReader())
            rec.tick()
            status, msg = rec.tick()
            self.assertEqual(status, "ok")
            self.assertIn("63.400", msg.replace("63.4", "63.400"))
            cur = rec.current
            self.assertEqual(len(cur["laps"]), 1)
            self.assertEqual(cur["laps"][0]["sectors_ms"],
                             [29500, 31000, 32900])
            # Live-Zustand kennt die Runde
            self.assertEqual(rec.live.laps[0]["lap_no"], 1)
            rec.close()


if __name__ == "__main__":
    unittest.main()
