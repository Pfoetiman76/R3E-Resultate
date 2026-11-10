"""Tests for 0.4.13: session dedupe and stable duplicate protection."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rrc.database import Database
from rrc.models import APP_VERSION, Session, PlayerResult


def _sess(digest, typ="Practice", ts="2026/11/07 20:44:54",
          track="Norisring", layout="Grand Prix", source="2026_11_07_20_44_53_Practice.txt"):
    s = Session(session_type=typ, timestamp=ts, track=track, layout=layout,
                source_file=source, digest=digest)
    s.players.append(PlayerResult(name="Marcel Wijnandts", vehicle="BMW M4 GT3",
                                  laps=3, best_lap_ms=64000, position=1))
    return s


class TestDedupe(unittest.TestCase):
    """0.4.13: Duplikate durch geänderte Id-Auflösung."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(os.path.join(self.tmp.name, "results.db"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_version(self):
        self.assertEqual(APP_VERSION, "0.4.13")

    def _insert_raw(self, digest, track, layout, vehicle=""):
        """Historischen Zustand direkt nachbilden (vor 0.4.13 konnten
        Zeilen mit gleichem natuerlichem Schluessel mehrfach entstehen)."""
        cur = self.db.conn.execute(
            "INSERT INTO sessions (digest, session_type, timestamp, track, "
            "layout, source_file) VALUES (?,?,?,?,?,?)",
            (digest, "Practice", "2026/11/07 20:44:54", track, layout,
             "2026_11_07_20_44_53_Practice.txt"))
        self.db.conn.execute(
            "INSERT INTO entries (session_id, position, name, vehicle, "
            "laps, best_lap_ms) VALUES (?,?,?,?,?,?)",
            (cur.lastrowid, 1, "Marcel Wijnandts", vehicle, 3, 64000))
        self.db.conn.commit()

    def test_dedupe_keeps_newest_row(self):
        """Simuliert: vor 0.4.7 mit numerischer Strecke gespeichert,
        spaeter erneut mit aufgeloestem Namen → zwei Zeilen, eine Datei."""
        self._insert_raw("alt", "2578", "(Layout-Id)")
        self._insert_raw("neu", "Norisring", "Grand Prix", "BMW M4 GT3")
        self.assertEqual(len(self.db.sessions()), 2)
        n = self.db.dedupe_sessions()
        self.assertEqual(n, 1)
        rows = self.db.sessions()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["track"], "Norisring")   # juengste Zeile bleibt
        veh = self.db.conn.execute("SELECT vehicle FROM entries").fetchone()
        self.assertEqual(veh["vehicle"], "BMW M4 GT3")

    def test_natural_key_prevents_insert(self):
        self.assertTrue(self.db.insert_session(_sess("d1"), "f.txt"))
        # gleiche Datei + Typ + Zeit, anderer Digest (aufgeloester Name)
        again = _sess("d2", track="Norisring 2.0")
        self.assertFalse(self.db.insert_session(again, "f.txt"))
        self.assertEqual(len(self.db.sessions()), 1)

    def test_dedupe_spares_distinct_sessions(self):
        a = _sess("a", ts="2026/11/07 20:44:54")
        b = _sess("b", ts="2026/11/08 19:00:00")
        c = _sess("c", typ="Race", ts="2026/11/07 20:44:54")  # andere Sitzung in derselben Datei
        self.db.insert_session(a, a.source_file)
        self.db.insert_session(b, b.source_file)
        self.db.insert_session(c, c.source_file)
        self.assertEqual(self.db.dedupe_sessions(), 0)
        self.assertEqual(len(self.db.sessions()), 3)

    def test_dedupe_triple(self):
        for d, track in (("d1", "2578"), ("d2", "Norisring"), ("d3", "Norisring")):
            self._insert_raw(d, track, "Grand Prix")
        self.assertEqual(len(self.db.sessions()), 3)
        self.assertEqual(self.db.dedupe_sessions(), 2)
        self.assertEqual(len(self.db.sessions()), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
