"""SQLite storage for RaceRoom Results Companion."""
import os
import sqlite3

from .parser import parse_file

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    digest TEXT UNIQUE NOT NULL,
    session_type TEXT DEFAULT '',
    timestamp TEXT DEFAULT '',
    track TEXT DEFAULT '',
    layout TEXT DEFAULT '',
    source_file TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    position INTEGER DEFAULT 0,
    name TEXT DEFAULT '',
    vehicle TEXT DEFAULT '',
    team TEXT DEFAULT '',
    laps INTEGER DEFAULT 0,
    best_lap_ms INTEGER DEFAULT 0,
    qual_ms INTEGER DEFAULT 0,
    race_time_ms INTEGER DEFAULT 0,
    finish_status TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_entries_session ON entries(session_id);
CREATE INDEX IF NOT EXISTS idx_entries_name ON entries(name);
CREATE INDEX IF NOT EXISTS idx_sessions_ts ON sessions(timestamp);
"""


class Database:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.commit()

    def close(self):
        self.conn.close()

    # ------------------------------------------------------------ ingest --

    def ingest_file(self, filepath: str) -> int:
        """Parse one result file; insert new sessions. Returns #new sessions."""
        sessions = parse_file(filepath)
        added = 0
        for sess in sessions:
            if self.insert_session(sess, os.path.abspath(filepath)):
                added += 1
        return added

    def ingest_folder(self, folder: str, extensions=(".txt", ".json", ".xml")):
        """Scan folder, ingest all result files. Returns (added, skipped, errors)."""
        added = skipped = errors = 0
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            return 0, 0, 1
        for name in names:
            if not name.lower().endswith(extensions):
                continue
            full = os.path.join(folder, name)
            if not os.path.isfile(full):
                continue
            sessions = parse_file(full)
            if not sessions:
                errors += 1
                continue
            new = False
            for sess in sessions:
                if self.insert_session(sess, os.path.abspath(full)):
                    new = True
                    added += 1
            if not new:
                skipped += 1
        self.conn.commit()
        return added, skipped, errors

    def insert_session(self, sess, source_path: str = "") -> bool:
        """Insert session if digest unknown. Returns True if inserted."""
        try:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO sessions "
                "(digest, session_type, timestamp, track, layout, source_file) "
                "VALUES (?,?,?,?,?,?)",
                (sess.digest, sess.session_type, sess.timestamp, sess.track,
                 sess.layout, sess.source_file or os.path.basename(source_path)))
            if cur.rowcount == 0:
                self.conn.commit()
                return False
            sess_id = cur.lastrowid
            self.conn.executemany(
                "INSERT INTO entries (session_id, position, name, vehicle, team,"
                " laps, best_lap_ms, qual_ms, race_time_ms, finish_status)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                [(sess_id, p.position, p.name, p.vehicle, p.team, p.laps,
                  p.best_lap_ms, p.qual_ms, p.race_time_ms, p.finish_status)
                 for p in sess.players])
            self.conn.commit()
            return True
        except sqlite3.Error:
            self.conn.rollback()
            return False

    # ------------------------------------------------------------ queries --

    def sessions(self, limit=2000):
        return self.conn.execute(
            "SELECT s.*, COUNT(e.id) AS n_players, "
            "MIN(e.best_lap_ms) AS session_best_ms "
            "FROM sessions s LEFT JOIN entries e ON e.session_id = s.id "
            "GROUP BY s.id ORDER BY s.timestamp DESC LIMIT ?", (limit,)).fetchall()

    def entries_for(self, session_id):
        return self.conn.execute(
            "SELECT * FROM entries WHERE session_id = ? "
            "ORDER BY position ASC, best_lap_ms ASC", (session_id,)).fetchall()

    def personal_bests(self, driver: str = ""):
        """Best lap per track/layout/vehicle. driver empty = all drivers."""
        q = ("SELECT e.name, s.track, s.layout, e.vehicle, "
             "MIN(e.best_lap_ms) AS best_ms, COUNT(*) AS n, "
             "MAX(s.timestamp) AS last_seen "
             "FROM entries e JOIN sessions s ON s.id = e.session_id "
             "WHERE e.best_lap_ms > 0 ")
        params = []
        if driver:
            q += "AND e.name = ? "
            params.append(driver)
        q += ("GROUP BY e.name, s.track, s.layout, e.vehicle "
              "ORDER BY s.track, s.layout, e.vehicle, best_ms ASC")
        return self.conn.execute(q, params).fetchall()

    def drivers(self):
        return [r["name"] for r in self.conn.execute(
            "SELECT DISTINCT name FROM entries WHERE name != '' ORDER BY name")]

    def stats_summary(self, driver: str = ""):
        base = "FROM entries e JOIN sessions s ON s.id = e.session_id "
        cond = "AND e.name = ? " if driver else ""
        race = "AND s.session_type LIKE 'Race%' "
        params = (driver,) if driver else ()
        row = self.conn.execute(
            f"SELECT COUNT(DISTINCT s.id) AS sessions, COUNT(e.id) AS entries, "
            f"MIN(e.best_lap_ms) AS best_ms, SUM(e.laps) AS total_laps {base} "
            f"WHERE 1=1 {cond}", params).fetchone()
        wins = self.conn.execute(
            f"SELECT COUNT(*) AS wins {base} "
            f"WHERE e.position = 1 {cond} {race}", params).fetchone()["wins"]
        races = self.conn.execute(
            f"SELECT COUNT(DISTINCT s.id) AS races {base} "
            f"WHERE 1=1 {cond} {race}", params).fetchone()["races"]
        d = dict(row)
        d["races"] = races
        return d, wins
