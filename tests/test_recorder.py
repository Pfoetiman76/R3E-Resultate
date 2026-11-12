"""Tests fuer 0.5.0: LapRecorder — Runden, Sitzungswechsel, Kraftstoff."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc import livelaps
from rrc.models import APP_VERSION


class FakeSample:
    """Traegt nur die Felder, die LapRecorder benutzt."""

    def __init__(self, in_car=True, session_type="Practice",
                 track_name="Norisring", layout_name="",
                 track_id=1690, layout_id=0, player_name="Marcel Wijnandts",
                 model_id=10914, completed_laps=0,
                 lap_time_previous_s=0.0, prev_lap_valid=1,
                 fuel_left=45.0, fuel_capacity=60.0, fuel_per_lap=3.0):
        for k, v in locals().items():
            if k == "self":
                continue
            setattr(self, k, v)


class FakeReader:
    """Gibt eine vordefinierte Sequenz von Samples zurueck."""

    def __init__(self, seq):
        self.seq = list(seq)
        self.i = 0

    def read(self):
        if self.i >= len(self.seq):
            return None        # Sitzung beendet
        s = self.seq[self.i]
        self.i += 1
        return s


class TestLapRecorder(unittest.TestCase):

    def test_version(self):
        self.assertEqual(APP_VERSION, "0.5.1")

    def test_runde_wird_gespeichert(self):
        from rrc.recorder import LapRecorder
        with tempfile.TemporaryDirectory() as td:
            now = [1000.0]
            r = LapRecorder(td, FakeReader([
                FakeSample(completed_laps=0, fuel_left=45.0),
                FakeSample(completed_laps=1, lap_time_previous_s=65.4,
                           prev_lap_valid=0, fuel_left=42.0),
            ]), clock=lambda: now.__setitem__(0, now[0] + 1) or now[0])
            status, msg = r.tick()
            self.assertEqual(status, "ok")
            status, msg = r.tick()
            self.assertEqual(status, "ok")
            self.assertIn("65.400", msg)
            self.assertIn("ungültig", msg)
            r.close()
            st = livelaps.load_store(livelaps.store_path(td))
            self.assertEqual(len(st["sessions"]), 1)
            lap = st["sessions"][0]["laps"][0]
            self.assertEqual(lap["time_ms"], 65400)
            self.assertEqual(lap["valid"], 0)

    def test_sitzungswechsel_schliesst(self):
        from rrc.recorder import LapRecorder
        with tempfile.TemporaryDirectory() as td:
            r = LapRecorder(td, FakeReader([
                FakeSample(completed_laps=0),
                FakeSample(completed_laps=1, lap_time_previous_s=64.0,
                           fuel_left=40.0),
                FakeSample(track_id=999),          # Streckenwechsel
                FakeSample(track_id=999, completed_laps=1,
                           lap_time_previous_s=70.0, fuel_left=50.0),
            ]))
            r.tick(); r.tick(); r.tick(); r.tick()
            r.close()
            st = livelaps.load_store(livelaps.store_path(td))
            self.assertEqual(len(st["sessions"]), 2)
            self.assertEqual(st["sessions"][0]["laps"][0]["time_ms"], 64000)
            self.assertEqual(st["sessions"][1]["laps"][0]["time_ms"], 70000)

    def test_idle_ohne_spiel(self):
        from rrc.recorder import LapRecorder
        with tempfile.TemporaryDirectory() as td:
            r = LapRecorder(td, FakeReader([]))    # read() -> None
            status, msg = r.tick()
            self.assertEqual(status, "idle")

    def test_fuel_history_eintrag(self):
        from rrc.recorder import LapRecorder
        from rrc import fuelcalc
        with tempfile.TemporaryDirectory() as td:
            r = LapRecorder(td, FakeReader([
                FakeSample(completed_laps=0, fuel_left=45.0,
                           fuel_capacity=60.0),
                FakeSample(completed_laps=1, lap_time_previous_s=64.0,
                           fuel_left=42.0, fuel_capacity=60.0),
                FakeSample(completed_laps=2, lap_time_previous_s=63.0,
                           fuel_left=39.0, fuel_capacity=60.0),
                FakeSample(completed_laps=3, lap_time_previous_s=62.0,
                           fuel_left=36.0, fuel_capacity=60.0),
            ]))
            for _ in range(4):
                r.tick()
            r.close()          # Sitzungsende -> Kraftstoff-Eintrag
            hist = fuelcalc.load_history(
                os.path.join(td, "fuel_history.json"))
            self.assertEqual(len(hist), 1)
            e = next(iter(hist.values()))
            self.assertAlmostEqual(e["fuel_l"], 3.0, places=5)
            key = next(iter(hist))
            self.assertIn("Norisring", key)

    def test_fuel_history_unplausibel_verworfefen(self):
        # Verbrauch nur mit sinnvollen Werten speichern: kapazitaet 0
        # (z. B. Formel-Fahrzeug ohne Angabe) darf keinen Eintrag erzeugen.
        from rrc.recorder import LapRecorder
        from rrc import fuelcalc
        with tempfile.TemporaryDirectory() as td:
            r = LapRecorder(td, FakeReader([
                FakeSample(completed_laps=0, fuel_left=0.0, fuel_capacity=0.0),
                FakeSample(completed_laps=1, lap_time_previous_s=64.0,
                           fuel_left=0.0, fuel_capacity=0.0),
            ]))
            r.tick(); r.tick()
            r.close()
            hist = fuelcalc.load_history(
                os.path.join(td, "fuel_history.json"))
            self.assertEqual(hist, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
