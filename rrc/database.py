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
CREATE TABLE IF NOT EXISTS laps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    lap_no INTEGER DEFAULT 0,
    lap_time_ms INTEGER DEFAULT 0,
    s1_ms INTEGER DEFAULT 0,
    s2_ms INTEGER DEFAULT 0,
    s3_ms INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_entries_session ON entries(session_id);
CREATE INDEX IF NOT EXISTS idx_entries_name ON entries(name);
CREATE INDEX IF NOT EXISTS idx_sessions_ts ON sessions(timestamp);
CREATE INDEX IF NOT EXISTS idx_laps_entry ON laps(entry_id);
"""

# Session types that count as "race" for statistics.
_RACE_LIKE = "Race"


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
        """Insert session if digest unknown (incl. lap details). True if inserted."""
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
            for p in sess.players:
                ecur = self.conn.execute(
                    "INSERT INTO entries (session_id, position, name, vehicle, team,"
                    " laps, best_lap_ms, qual_ms, race_time_ms, finish_status)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (sess_id, p.position, p.name, p.vehicle, p.team, p.laps,
                     p.best_lap_ms, p.qual_ms, p.race_time_ms, p.finish_status))
                if p.laps_detail:
                    self.conn.executemany(
                        "INSERT INTO laps (entry_id, lap_no, lap_time_ms,"
                        " s1_ms, s2_ms, s3_ms) VALUES (?,?,?,?,?,?)",
                        [(ecur.lastrowid, lp.lap_no, lp.lap_time_ms,
                          (lp.sector_times_ms + [0, 0, 0])[0],
                          (lp.sector_times_ms + [0, 0, 0])[1],
                          (lp.sector_times_ms + [0, 0, 0])[2])
                         for lp in p.laps_detail])
            self.conn.commit()
            return True
        except sqlite3.Error:
            self.conn.rollback()
            return False

    # ------------------------------------------------------------ queries --

    def sessions(self, limit=5000, search="", session_type="", driver=""):
        """Session list, optional filters: free text (track/driver), type, driver.

        Order: newest first. n_players counts all entries; driver_best_ms is the
        best lap of the (optionally filtered) driver in that session.
        """
        q = ("SELECT s.*, COUNT(e.id) AS n_players, "
             "MIN(e.best_lap_ms) AS session_best_ms "
             "FROM sessions s LEFT JOIN entries e ON e.session_id = s.id ")
        where, params = [], []
        if driver:
            where.append("s.id IN (SELECT session_id FROM entries WHERE name = ?)")
            params.append(driver)
        if search:
            where.append("(s.track LIKE ? OR s.layout LIKE ? OR s.session_type LIKE ?)")
            params.extend([f"%{search}%"] * 3)
        if session_type:
            where.append("s.session_type LIKE ?")
            params.append(f"{session_type}%")
        if where:
            q += "WHERE " + " AND ".join(where) + " "
        q += ("GROUP BY s.id ORDER BY s.timestamp DESC LIMIT ?")
        params.append(limit)
        return self.conn.execute(q, params).fetchall()

    def entries_for(self, session_id):
        return self.conn.execute(
            "SELECT * FROM entries WHERE session_id = ? "
            "ORDER BY position ASC, best_lap_ms ASC", (session_id,)).fetchall()

    def laps_for_session(self, session_id):
        """All laps of a session joined with driver names. Ordered by driver, lap."""
        return self.conn.execute(
            "SELECT l.*, e.name, e.vehicle FROM laps l "
            "JOIN entries e ON e.id = l.entry_id "
            "WHERE e.session_id = ? ORDER BY e.name, l.lap_no", (session_id,)).fetchall()

    def sessions_with_laps(self, limit=500):
        return self.conn.execute(
            "SELECT s.*, COUNT(l.id) AS n_laps FROM sessions s "
            "JOIN entries e ON e.session_id = s.id "
            "JOIN laps l ON l.entry_id = e.id "
            "GROUP BY s.id ORDER BY s.timestamp DESC LIMIT ?", (limit,)).fetchall()

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

    def tracks(self):
        """Distinct track/layout combinations, display-ready."""
        return self.conn.execute(
            "SELECT track, layout, COUNT(*) AS n FROM sessions "
            "GROUP BY track, layout ORDER BY track, layout").fetchall()

    def progression(self, track, layout="", vehicle="", driver=""):
        """Best lap per session over time (for the chart)."""
        q = ("SELECT s.timestamp, MIN(e.best_lap_ms) AS best_ms "
             "FROM entries e JOIN sessions s ON s.id = e.session_id "
             "WHERE s.track = ? AND e.best_lap_ms > 0 ")
        params = [track]
        if layout:
            q += "AND s.layout = ? "
            params.append(layout)
        if vehicle:
            q += "AND e.vehicle = ? "
            params.append(vehicle)
        if driver:
            q += "AND e.name = ? "
            params.append(driver)
        q += "GROUP BY s.id ORDER BY s.timestamp ASC"
        return self.conn.execute(q, params).fetchall()

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
        podium = self.conn.execute(
            f"SELECT COUNT(*) AS podium {base} "
            f"WHERE e.position BETWEEN 1 AND 3 {cond} {race}", params).fetchone()["podium"]
        finishes = self.conn.execute(
            f"SELECT COUNT(*) AS finishes {base} "
            f"WHERE 1=1 {cond} {race} "
            f"AND (e.finish_status = '' OR LOWER(e.finish_status) = 'finished')",
            params).fetchone()["finishes"]
        d = dict(row)
        d.update(races=races, wins=wins, podium=podium, finishes=finishes)
        return d, wins

    def dnf_summary(self, driver: str = ""):
        """Per driver: race starts, DNFs, finish rate. Only race sessions."""
        q = ("SELECT e.name, COUNT(*) AS starts, "
             "SUM(CASE WHEN (e.finish_status != '' AND LOWER(e.finish_status) "
             "             != 'finished') OR e.position = 0 THEN 1 ELSE 0 END) AS dnfs "
             "FROM entries e JOIN sessions s ON s.id = e.session_id "
             "WHERE s.session_type LIKE 'Race%' ")
        params = []
        if driver:
            q += "AND e.name = ? "
            params.append(driver)
        q += ("GROUP BY e.name ORDER BY dnfs DESC, starts DESC")
        rows = self.conn.execute(q, params).fetchall()
        out = []
        for r in rows:
            starts, dnfs = r["starts"], r["dnfs"] or 0
            out.append({"name": r["name"], "starts": starts, "dnfs": dnfs,
                        "finish_rate": (starts - dnfs) * 100.0 / starts if starts else 0.0})
        return out

    def dnf_sessions(self, driver: str = ""):
        """List of race sessions with a DNF (for the incident history)."""
        q = ("SELECT s.timestamp, s.track, s.layout, e.name, e.finish_status "
             "FROM entries e JOIN sessions s ON s.id = e.session_id "
             "WHERE s.session_type LIKE 'Race%' "
             "AND ((e.finish_status != '' AND LOWER(e.finish_status) != 'finished') "
             "     OR e.position = 0) ")
        params = []
        if driver:
            q += "AND e.name = ? "
            params.append(driver)
        q += "ORDER BY s.timestamp DESC LIMIT 500"
        return self.conn.execute(q, params).fetchall()
