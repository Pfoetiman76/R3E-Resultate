"""Tests for 0.4.13: diagnostics report for remote defect analysis."""
import os
import tempfile
import unittest

from rrc.database import Database
from rrc.models import APP_VERSION


class DiagnosticsReportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = os.path.join(self.tmp, "results.db")
        self.db = Database(self.path)

    def tearDown(self):
        self.db.close()
        for root, _dirs, files in os.walk(self.tmp, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            os.rmdir(root)

    def _add_session(self, timestamp, track="Norisring", session_type="Race",
                     source="race.txt", digest=None):
        cur = self.db.conn.execute(
            "INSERT INTO sessions (digest, session_type, timestamp,"
            " track, layout, source_file) VALUES (?,?,?,?,?,?)",
            (digest or f"{source}-{timestamp}-{track}", session_type,
             timestamp, track, "", source))
        return cur.lastrowid

    def _add_entry(self, session_id, best_ms, driver="Marcel",
                   vehicle="Audi RS 3 LMS", vehicle_class="TCR", ai=0):
        self.db.conn.execute(
            "INSERT INTO entries (session_id, position, name, vehicle,"
            " best_lap_ms, vehicle_class, ai) VALUES (?,?,?,?,?,?,?)",
            (session_id, 1, driver, vehicle, best_ms, vehicle_class, ai))

    def test_version_bump(self):
        self.assertEqual(APP_VERSION, "0.5.1")

    def test_report_contains_median_and_outlier(self):
        sid = self._add_session(1000)
        for i, ms in enumerate((64900, 64950, 65000, 65050, 65100, 51695)):
            self._add_entry(sid, ms, driver=f"D{i}")
        self.db.conn.commit()
        report = self.db.diagnostics_report()
        self.assertIn("Diagnosebericht", report)
        self.assertIn("Norisring", report)
        self.assertIn("Median", report)
        self.assertIn("51695", report)
        self.assertIn("64975", report)  # Median aus 64900..65100
        self.assertIn("race.txt", report)

    def test_report_ignores_invalid_laps(self):
        sid = self._add_session(2000, track="Monza", source="monza.txt")
        self._add_entry(sid, 0)
        self._add_entry(sid, -1)
        self.db.conn.commit()
        report = self.db.diagnostics_report()
        self.assertIn("Monza", report)
        block = report.split("Monza", 1)[1]
        self.assertNotIn("Median", block)
        self.assertNotIn("Beste:", block)

    def test_report_counts_duplicates(self):
        for i, ts in enumerate((100, 100, 100)):
            self._add_session(ts, source="dup.txt",
                              digest=f"dup-{i}")
        self.db.conn.commit()
        report = self.db.diagnostics_report()
        self.assertIn("Duplikate", report)
        self.assertIn("1", report.split("Duplikate:", 1)[1].split("\n", 1)[0])


if __name__ == "__main__":
    unittest.main()
