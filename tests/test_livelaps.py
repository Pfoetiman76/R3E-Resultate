"""Tests fuer 0.5.0: live_laps.json — Speicher und Zusammenfuehrung."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc import livelaps
from rrc.models import APP_VERSION, Session, PlayerResult, LapEntry


def _store(started="2026-11-07 20:30:00", ended="2026-11-07 20:44:53",
           track="Norisring", layout="", laps=None):
    return {"schema_version": 1, "sessions": [{
        "started": started, "ended": ended, "session_type": "Practice",
        "track_name": track, "layout_name": layout,
        "track_id": 1690, "layout_id": 0, "player_name": "Marcel Wijnandts",
        "laps": laps if laps is not None else [
            {"lap_no": 0, "time_ms": 65100, "valid": 0,
             "ts": "2026-11-07 20:40:00", "fuel_after": 40.0},
            {"lap_no": 1, "time_ms": 64200, "valid": 1,
             "ts": "2026-11-07 20:41:00", "fuel_after": 37.0},
        ],
        "fuel": {"capacity": 60.0, "per_lap": 3.0, "start": 45.0,
                 "end": 37.0}}]}


def _sess(ts="2026/11/07 20:44:53", laps=None):
    s = Session(session_type="Practice", timestamp=ts, track="Norisring",
                layout="", source_file="2026_11_07_20_44_53_Practice.txt",
                digest="d")
    p = PlayerResult(name="Marcel Wijnandts", vehicle="BMW M4 GT3",
                     laps=2, best_lap_ms=64200, position=1)
    p.laps_detail = laps if laps is not None else [
        LapEntry(0, -1, [], valid=0),     # Platzhalter, ungueltig
        LapEntry(1, 64200, []),           # echte Zeit
    ]
    s.players.append(p)
    return s


class TestLivelaps(unittest.TestCase):

    def test_version(self):
        self.assertEqual(APP_VERSION, "0.5.0")

    def test_store_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            path = livelaps.store_path(td)
            st = _store()
            livelaps.save_store(path, st)
            self.assertTrue(os.path.exists(path))
            self.assertFalse(os.path.exists(path + ".tmp"))
            back = livelaps.load_store(path)
            self.assertEqual(back["schema_version"], 1)
            self.assertEqual(len(back["sessions"]), 1)
            self.assertEqual(back["sessions"][0]["laps"][0]["time_ms"], 65100)

    def test_korrupt_ergibt_leer(self):
        with tempfile.TemporaryDirectory() as td:
            path = livelaps.store_path(td)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("{kein gueltiges json")
            self.assertEqual(livelaps.load_store(path)["sessions"], [])
            self.assertEqual(livelaps.load_store(td + "/fehlt.json")["sessions"], [])

    def test_prune(self):
        st = {"schema_version": 1,
              "sessions": [{"n": i} for i in range(30)]}
        pr = livelaps.prune(st, keep=20)
        self.assertEqual(len(pr["sessions"]), 20)
        self.assertEqual(pr["sessions"][0]["n"], 10)
        self.assertEqual(pr["sessions"][-1]["n"], 29)

    def test_find_session_zeitfenster(self):
        st = _store()
        # Sitzungs-ENDE 20:44:53: Ergebnisdatei 20:44:53 passt
        self.assertIsNotNone(livelaps.find_session(st, "2026/11/07 20:44:53"))
        # 2 Stunden spaeter: ausserhalb [start-15min, ende+10min]
        self.assertIsNone(livelaps.find_session(st, "2026/11/07 22:44:53"))
        # 10 Minuten vor Sitzungsstart (Puffer) passt noch
        self.assertIsNotNone(livelaps.find_session(st, "2026/11/07 20:16:00"))

    def test_find_session_strecke(self):
        st = _store(track="Monza")
        self.assertIsNone(livelaps.find_session(st, "2026/11/07 20:44:53",
                                                track_name="Norisring"))
        # Gross-/Kleinschreibung ist egal
        self.assertIsNotNone(livelaps.find_session(st, "2026/11/07 20:44:53",
                                                    track_name="monza"))

    def test_fill_session_fuellt_nur_platzhalter(self):
        st = _store()
        s = _sess()
        n = livelaps.fill_session(s, st)
        self.assertEqual(n, 1)
        lp0 = s.players[0].laps_detail[0]
        self.assertEqual(lp0.lap_time_ms, 65100)
        self.assertEqual(lp0.valid, 0)
        lp1 = s.players[0].laps_detail[1]
        self.assertEqual(lp1.lap_time_ms, 64200)     # unangetastet
        self.assertEqual(lp1.valid, 1)

    def test_fill_session_ohne_zeitstempel(self):
        s = _sess(ts="")
        self.assertEqual(livelaps.fill_session(s, _store()), 0)

    def test_fill_session_kein_treffer(self):
        s = _sess(ts="2026/11/08 20:44:53")
        self.assertEqual(livelaps.fill_session(s, _store()), 0)


class TestValidColumnInDb(unittest.TestCase):
    """0.5.0: Spalte 'valid' ueberlebt den Weg durch die Datenbank."""

    def test_valid_wird_gespeichert(self):
        import tempfile
        from rrc.database import Database
        with tempfile.TemporaryDirectory() as td:
            db = Database(os.path.join(td, "res.db"))
            s = _sess()
            s.players[0].laps_detail = [
                LapEntry(1, 64200, []),                 # gueltig
                LapEntry(0, 65100, [], valid=0),         # ungueltig, mit Zeit
            ]
            self.assertTrue(db.insert_session(s, s.source_file))
            sid = db.conn.execute("SELECT id FROM sessions").fetchone()["id"]
            laps = [dict(l) for l in db.laps_for_session(sid)]
            valid = {l["lap_no"]: l["valid"] for l in laps}
            self.assertEqual(valid[0], 0)
            self.assertEqual(valid[1], 1)
            db.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
