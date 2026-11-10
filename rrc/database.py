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
    finish_status TEXT DEFAULT '',
    car_id INTEGER DEFAULT 0,
    ai INTEGER DEFAULT -1,
    vehicle_class TEXT DEFAULT ''
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

# Bedingung: kein als KI erkannter Fahrer (0.4.10). ai = -1/NULL bedeutet
# "unbekannt" (Server-/Multiplayer-Formate) und bleibt sichtbar.
_AI_HIDE = "({p}ai IS NULL OR {p}ai <= 0) "


class Database:
    def __init__(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        self.path = path
        self.hide_ai = False   # KI-Fahrer ausblenden (Haken in der Sitzungsliste)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(_SCHEMA)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self._migrate_entries()
        self.conn.commit()

    def _migrate_entries(self):
        """Spalten nachruesten, die mit 0.4.10 dazukamen (car_id, ai,
        vehicle_class) — aeltere Datenbanken bleiben ohne Datenverlust
        nutzbar."""
        cols = {r[1] for r in
                self.conn.execute("PRAGMA table_info(entries)").fetchall()}
        for col, decl in (("car_id", "INTEGER DEFAULT 0"),
                          ("ai", "INTEGER DEFAULT -1"),
                          ("vehicle_class", "TEXT DEFAULT ''")):
            if col not in cols:
                self.conn.execute(
                    f"ALTER TABLE entries ADD COLUMN {col} {decl}")

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
                    " laps, best_lap_ms, qual_ms, race_time_ms, finish_status,"
                    " car_id, ai, vehicle_class)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (sess_id, p.position, p.name, p.vehicle, p.team, p.laps,
                     p.best_lap_ms, p.qual_ms, p.race_time_ms, p.finish_status,
                     getattr(p, "car_id", 0), getattr(p, "is_ai", -1),
                     getattr(p, "vehicle_class", "")))
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

    def unresolved_track_ids(self):
        """Distinct numeric track IDs without a readable name."""
        rows = self.conn.execute(
            "SELECT DISTINCT track FROM sessions "
            "WHERE layout = '(Layout-Id)' ORDER BY track").fetchall()
        return [r["track"] for r in rows]

    def unresolved_car_ids(self):
        """Distinct numeric vehicle IDs in entries."""
        rows = self.conn.execute(
            "SELECT DISTINCT vehicle FROM entries "
            "WHERE vehicle GLOB '[0-9]*' AND vehicle NOT GLOB '*[^0-9]*' "
            "ORDER BY CAST(vehicle AS INTEGER)").fetchall()
        return [r["vehicle"] for r in rows]

    def upgrade_ids(self, user_names, official=None):
        """Re-resolve numeric track and vehicle IDs against the given
        user mappings (official game data next, built-in tables as
        fallback). Returns (n_tracks, n_vehicles) updated."""
        from . import trackids
        n_tracks = n_vehicles = 0
        for tid in self.unresolved_track_ids():
            mapped = trackids.resolve_layout_with(tid, user_names, official)
            if mapped:
                self.conn.execute(
                    "UPDATE sessions SET track = ?, layout = ? "
                    "WHERE track = ? AND layout = '(Layout-Id)'",
                    (mapped[0], mapped[1], tid))
                n_tracks += 1
        for cid in self.unresolved_car_ids():
            mapped = trackids.resolve_car_with(cid, user_names, official)
            if mapped:
                self.conn.execute(
                    "UPDATE entries SET vehicle = ? WHERE vehicle = ?",
                    (mapped, cid))
                n_vehicles += 1
        self.conn.commit()
        return n_tracks, n_vehicles

    def sanitize_laps(self, threshold=500):
        """Bereinigt den KI-Artefakt in totalLaps (immer 856, ohne eine
        einzige gueltige Rundenzeit): Eintraege mit unrealistisch hoher
        Rundenzahl erhalten die Anzahl tatsaechlich gezeichneter Runden
        (Tabelle laps), sonst 0. Rueckgabe: Anzahl korrigierter Eintraege."""
        cur = self.conn.execute(
            "UPDATE entries SET laps = (SELECT COUNT(*) FROM laps l"
            " WHERE l.entry_id = entries.id AND l.lap_time_ms > 0)"
            " WHERE laps > ?", (threshold,))
        n = max(cur.rowcount, 0)
        self.conn.commit()
        return n

    def backfill_from_files(self, folder):
        """Ab 0.4.10: Bereits gespeicherte Sitzungen nachtraeglich um
        Fahrzeug, carId, KI-Kennzeichen und Fahrzeugklasse ergaenzen.
        Sitzungen, deren Eintraege (noch) ohne Fahrzeug gespeichert wurden
        (Einzelspieler-Dateien bis 0.4.9), werden aus den Originaldateien
        im Ergebnisordner neu gelesen und die Felder nachgetragen.
        Rueckgabe: Anzahl aktualisierter Eintraege."""
        import os
        if not folder or not os.path.isdir(folder):
            return 0
        from .parser import parse_file
        rows = self.conn.execute(
            "SELECT DISTINCT s.id, s.source_file FROM sessions s "
            "JOIN entries e ON e.session_id = s.id "
            "WHERE e.vehicle = ''").fetchall()
        n = 0
        for r in rows:
            path = os.path.join(folder, r["source_file"] or "")
            if not r["source_file"] or not os.path.isfile(path):
                continue
            for sess in parse_file(path):
                by_name = {}
                for p in sess.players:
                    prev = by_name.get(p.name)
                    if prev is None or p.vehicle:
                        by_name[p.name] = p
                updates = 0
                for e in self.conn.execute(
                        "SELECT id, name FROM entries WHERE session_id = ?",
                        (r["id"],)).fetchall():
                    p = by_name.get(e["name"])
                    if p is None:
                        continue
                    self.conn.execute(
                        "UPDATE entries SET vehicle = ?, car_id = ?, ai = ?, "
                        "vehicle_class = ? WHERE id = ?",
                        (p.vehicle, getattr(p, "car_id", 0),
                         getattr(p, "is_ai", -1),
                         getattr(p, "vehicle_class", ""), e["id"]))
                    updates += 1
                n += updates
        self.conn.commit()
        return n

    def sessions(self, limit=5000, search="", session_type="", driver="",
                 names=None, date_from="", date_to="", track="",
                 vehicle=""):
        """Session list, optional filters: free text (track/driver), type,
        driver, date range (YYYY-MM-DD), track, vehicle.

        Order: newest first. n_players counts all entries; driver_best_ms is the
        best lap of the (optionally filtered) driver in that session.
        names: None = alle Fahrer; Liste = nur diese Fahrer anzeigen
        (Option "KI-Fahrer ausblenden"); leere Liste = keine Treffer.
        """
        if names is not None and not names:
            return []
        q = ("SELECT s.*, COUNT(e.id) AS n_players, "
             "MIN(CASE WHEN e.best_lap_ms > 0 THEN e.best_lap_ms END) "
             "  AS session_best_ms, "
             "GROUP_CONCAT(DISTINCT CASE WHEN e.vehicle != '' "
             "  THEN e.vehicle END) AS vehicles "
             "FROM sessions s LEFT JOIN entries e ON e.session_id = s.id ")
        jparams = []
        if self.hide_ai:
            q += "AND " + _AI_HIDE.format(p="e.")
        if names is not None:
            q += "AND e.name IN (" + ",".join("?" * len(names)) + ") "
            jparams = list(names)
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
        if date_from:
            # timestamp ist 'YYYY-MM-DD HH:MM:SS' -> Stringvergleich genügt
            where.append("s.timestamp >= ?")
            params.append(f"{date_from} 00:00:00")
        if date_to:
            where.append("s.timestamp <= ?")
            params.append(f"{date_to} 23:59:59")
        if track:
            where.append("s.track = ?")
            params.append(track)
        if vehicle:
            where.append("s.id IN (SELECT session_id FROM entries "
                         "WHERE vehicle = ?)")
            params.append(vehicle)
        if where:
            q += "WHERE " + " AND ".join(where) + " "
        q += ("GROUP BY s.id")
        if names is not None or self.hide_ai:
            q += " HAVING COUNT(e.id) > 0"   # Sitzungen ohne sichtbare Fahrer weg
        q += (" ORDER BY s.timestamp DESC LIMIT ?")
        return self.conn.execute(q, jparams + params + [limit]).fetchall()

    def entries_for(self, session_id, names=None):
        """Entries of a session; names wie bei sessions() (KI-Ausblendung)."""
        q = "SELECT * FROM entries WHERE session_id = ? "
        params = [session_id]
        if self.hide_ai:
            q += "AND " + _AI_HIDE.format(p="")
        if names is not None:
            if names:
                q += "AND name IN (" + ",".join("?" * len(names)) + ") "
                params += list(names)
            else:
                q += "AND 1=0 "
        q += "ORDER BY position ASC, best_lap_ms ASC"
        return self.conn.execute(q, params).fetchall()

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

    def personal_bests(self, driver: str = "", names=None):
        """Best lap per track/layout/vehicle. driver empty = all drivers.
        names wie bei sessions() (KI-Ausblendung)."""
        q = ("SELECT e.name, s.track, s.layout, e.vehicle, e.vehicle_class, "
             "MIN(e.best_lap_ms) AS best_ms, COUNT(*) AS n, "
             "MAX(s.timestamp) AS last_seen "
             "FROM entries e JOIN sessions s ON s.id = e.session_id "
             "WHERE e.best_lap_ms > 0 ")
        params = []
        if self.hide_ai:
            q += "AND " + _AI_HIDE.format(p="e.")
        if names is not None:
            if names:
                q += "AND e.name IN (" + ",".join("?" * len(names)) + ") "
                params += list(names)
            else:
                q += "AND 1=0 "
        if driver:
            q += "AND e.name = ? "
            params.append(driver)
        q += ("GROUP BY e.name, s.track, s.layout, e.vehicle "
              "ORDER BY s.track, s.layout, e.vehicle, best_ms ASC")
        return self.conn.execute(q, params).fetchall()

    def drivers(self, names=None):
        """Distinct driver names; names-Filter fuer die KI-Ausblendung."""
        q = "SELECT DISTINCT name FROM entries WHERE name != '' "
        params = []
        if self.hide_ai:
            q += "AND " + _AI_HIDE.format(p="")
        if names is not None:
            if names:
                q += "AND name IN (" + ",".join("?" * len(names)) + ") "
                params += list(names)
            else:
                q += "AND 1=0 "
        q += "ORDER BY name"
        return [r["name"] for r in self.conn.execute(q, params)]

    def tracks(self):
        """Distinct track/layout combinations, display-ready."""
        return self.conn.execute(
            "SELECT track, layout, COUNT(*) AS n FROM sessions "
            "GROUP BY track, layout ORDER BY track, layout").fetchall()

    def vehicles_for_track(self, track):
        """Distinct vehicles driven on a track (for the fuel calculator)."""
        cond = "s.track = ? AND e.vehicle != '' "
        params = [track]
        if self.hide_ai:
            cond += "AND " + _AI_HIDE.format(p="e.")
        return [r["vehicle"] for r in self.conn.execute(
            "SELECT DISTINCT e.vehicle FROM entries e "
            "JOIN sessions s ON s.id = e.session_id "
            "WHERE " + cond + "ORDER BY e.vehicle", params)]

    def vehicles(self):
        """Distinct vehicle names in entries (for the filter combo)."""
        cond = "vehicle != '' "
        if self.hide_ai:
            cond += "AND " + _AI_HIDE.format(p="")
        rows = self.conn.execute(
            "SELECT DISTINCT vehicle FROM entries WHERE " + cond +
            "ORDER BY vehicle").fetchall()
        return [r["vehicle"] for r in rows]

    def progression(self, track, layout="", vehicle="", driver=""):
        """Best lap per session over time (for the chart)."""
        q = ("SELECT s.timestamp, MIN(e.best_lap_ms) AS best_ms "
             "FROM entries e JOIN sessions s ON s.id = e.session_id "
             "WHERE s.track = ? AND e.best_lap_ms > 0 ")
        params = [track]
        if self.hide_ai:
            q += "AND " + _AI_HIDE.format(p="e.")
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

    def _stats_conditions(self, driver: str, names):
        """Gemeinsame WHERE-Bausteine für die Statistik zurück."""
        base = "FROM entries e JOIN sessions s ON s.id = e.session_id "
        conds, params = [], []
        if self.hide_ai:
            conds.append(_AI_HIDE.format(p="e.").strip())
        if driver:
            conds.append("e.name = ?")
            params.append(driver)
        if names is not None:
            conds.append("e.name IN (" + ",".join("?" * len(names)) + ")")
            params.extend(names)
        cond = ("AND " + " AND ".join(conds) + " ") if conds else ""
        return base, cond, params

    def stats_summary(self, driver: str = "", names=None):
        """Kennzahlen für die Statistik-Kacheln.

        names: None = alle Fahrer; Liste = nur diese (KI-Ausblendung);
        leere Liste = alles 0. finishes/race_entries beziehen sich auf
        Renn-Einträge, damit die Zielquote die Ziele pro Renneinsatz
        angibt (nicht pro Sitzung).
        """
        zero = {"sessions": 0, "entries": 0, "best_ms": None,
                "total_laps": 0, "races": 0, "race_entries": 0, "wins": 0,
                "podium": 0, "finishes": 0}
        if names is not None and not names:
            return zero, 0
        base, cond, params = self._stats_conditions(driver, names)
        race = "AND s.session_type LIKE 'Race%' "
        row = self.conn.execute(
            f"SELECT COUNT(DISTINCT s.id) AS sessions, COUNT(e.id) AS entries, "
            f"MIN(CASE WHEN e.best_lap_ms > 0 THEN e.best_lap_ms END) "
            f"  AS best_ms, SUM(e.laps) AS total_laps {base} "
            f"WHERE 1=1 {cond}", params).fetchone()
        wins = self.conn.execute(
            f"SELECT COUNT(*) AS wins {base} "
            f"WHERE e.position = 1 {cond} {race}", params).fetchone()["wins"]
        races = self.conn.execute(
            f"SELECT COUNT(DISTINCT s.id) AS races {base} "
            f"WHERE 1=1 {cond} {race}", params).fetchone()["races"]
        race_entries = self.conn.execute(
            f"SELECT COUNT(*) AS race_entries {base} "
            f"WHERE 1=1 {cond} {race}", params).fetchone()["race_entries"]
        podium = self.conn.execute(
            f"SELECT COUNT(*) AS podium {base} "
            f"WHERE e.position BETWEEN 1 AND 3 {cond} {race}", params).fetchone()["podium"]
        finishes = self.conn.execute(
            f"SELECT COUNT(*) AS finishes {base} "
            f"WHERE 1=1 {cond} {race} "
            f"AND (e.finish_status = '' OR LOWER(e.finish_status) = 'finished')",
            params).fetchone()["finishes"]
        d = dict(row)
        d.update(races=races, race_entries=race_entries, wins=wins,
                 podium=podium, finishes=finishes)
        return d, wins

    def aggregate(self, by: str = "track", driver: str = "", names=None):
        """Auswertung je Strecke oder je Fahrzeug (0.4.9).

        by: 'track' gruppiert nach Strecke - Layout, 'vehicle' nach Fahrzeug.
        names: None = alle Fahrer; Liste = nur diese (KI-Ausblendung);
        leere Liste = leeres Ergebnis. Zaehlweise wie Statistik: Siege und
        Podium nur im eigenen Eintrag, Zielquote = Ziele pro Renneinsatz,
        DNF = Ausfall in Rennen. Rueckgabe: Liste von dicts mit label,
        sessions, races, race_entries, wins, podium, finishes, dnfs,
        total_laps, best_ms, avg_best_ms, quote.
        """
        if names is not None and not names:
            return []
        if by == "track":
            label = ("s.track || CASE WHEN s.layout != '' AND s.layout != "
                      "'(Layout-Id)' THEN ' - ' || s.layout ELSE '' END")
        elif by == "class":
            label = ("CASE WHEN e.vehicle_class != '' THEN e.vehicle_class "
                     "ELSE '(ohne Klasse)' END")
        else:
            label = "e.vehicle"
        conds, params = [], []
        if self.hide_ai:
            conds.append(_AI_HIDE.format(p="e.").strip())
        if driver:
            conds.append("e.name = ?")
            params.append(driver)
        if names is not None:
            conds.append("e.name IN (" + ",".join("?" * len(names)) + ")")
            params.extend(names)
        cond = ("AND " + " AND ".join(conds) + " ") if conds else ""
        q = (
            "SELECT " + label + " AS label, "
            "COUNT(DISTINCT s.id) AS sessions, "
            "COUNT(DISTINCT CASE WHEN s.session_type LIKE 'Race%' "
            "  THEN s.id END) AS races, "
            "SUM(CASE WHEN s.session_type LIKE 'Race%' THEN 1 ELSE 0 END) "
            "  AS race_entries, "
            "SUM(CASE WHEN s.session_type LIKE 'Race%' AND e.position = 1 "
            "  THEN 1 ELSE 0 END) AS wins, "
            "SUM(CASE WHEN s.session_type LIKE 'Race%' "
            "  AND e.position BETWEEN 1 AND 3 THEN 1 ELSE 0 END) AS podium, "
            "SUM(CASE WHEN s.session_type LIKE 'Race%' "
            "  AND (e.finish_status = '' OR LOWER(e.finish_status) "
            "       = 'finished') THEN 1 ELSE 0 END) AS finishes, "
            "SUM(CASE WHEN s.session_type LIKE 'Race%' "
            "  AND ((e.finish_status != '' AND LOWER(e.finish_status) "
            "       != 'finished') OR e.position = 0) THEN 1 ELSE 0 END) "
            "  AS dnfs, "
            "SUM(e.laps) AS total_laps, "
            "MIN(CASE WHEN e.best_lap_ms > 0 THEN e.best_lap_ms END) "
            "  AS best_ms, "
            "AVG(CASE WHEN e.best_lap_ms > 0 THEN e.best_lap_ms END) "
            "  AS avg_best_ms "
            "FROM entries e JOIN sessions s ON s.id = e.session_id "
            "WHERE 1=1 " + cond +
            "GROUP BY " + label +
            " ORDER BY sessions DESC, label")
        rows = self.conn.execute(q, params).fetchall()
        out = []
        for r in rows:
            re_ = r["race_entries"] or 0
            fin = r["finishes"] or 0
            out.append({
                "label": r["label"], "sessions": r["sessions"],
                "races": r["races"] or 0, "race_entries": re_,
                "wins": r["wins"] or 0, "podium": r["podium"] or 0,
                "finishes": fin, "dnfs": r["dnfs"] or 0,
                "total_laps": r["total_laps"] or 0, "best_ms": r["best_ms"],
                "avg_best_ms": r["avg_best_ms"],
                "quote": (fin * 100.0 / re_) if re_ else 0.0,
            })
        return out

    def dnf_summary(self, driver: str = "", names=None):
        """Per driver: race starts, DNFs, finish rate. Only race sessions."""
        if names is not None and not names:
            return []
        q = ("SELECT e.name, COUNT(*) AS starts, "
             "SUM(CASE WHEN (e.finish_status != '' AND LOWER(e.finish_status) "
             "             != 'finished') OR e.position = 0 THEN 1 ELSE 0 END) AS dnfs "
             "FROM entries e JOIN sessions s ON s.id = e.session_id "
             "WHERE s.session_type LIKE 'Race%' ")
        params = []
        if self.hide_ai:
            q += "AND " + _AI_HIDE.format(p="e.")
        if driver:
            q += "AND e.name = ? "
            params.append(driver)
        if names is not None:
            q += "AND e.name IN (" + ",".join("?" * len(names)) + ") "
            params.extend(names)
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
        if self.hide_ai:
            q += "AND " + _AI_HIDE.format(p="e.")
        if driver:
            q += "AND e.name = ? "
            params.append(driver)
        q += "ORDER BY s.timestamp DESC LIMIT 500"
        return self.conn.execute(q, params).fetchall()

    def totals(self):
        """Gesamtzaehler fuer die Statusleiste: (Sitzungen, Runden gesamt)."""
        n_s = self.conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        cond = ("WHERE " + _AI_HIDE.format(p="")) if self.hide_ai else ""
        n_l = self.conn.execute(
            f"SELECT COALESCE(SUM(laps), 0) FROM entries {cond}").fetchone()[0]
        return n_s, n_l

    # ------------------------------------------------ 0.4.1 Streckenrekorde --

    def track_classes(self, track, layout=""):
        """Fahrzeugklassen, die auf einer Strecke gefahren wurden
        (0.4.10, fuer die Rekord-Kacheln je Klasse)."""
        q = ("SELECT DISTINCT e.vehicle_class FROM entries e "
             "JOIN sessions s ON s.id = e.session_id "
             "WHERE s.track = ? AND e.vehicle_class != '' ")
        params = [track]
        if layout:
            q += "AND s.layout = ? "
            params.append(layout)
        if self.hide_ai:
            q += "AND " + _AI_HIDE.format(p="e.")
        q += "ORDER BY e.vehicle_class"
        return [r["vehicle_class"] for r in self.conn.execute(q, params)]

    def track_records(self, track, layout="", vehicle_class=""):
        """Streckenrekorde fuer den Runden-Tab (ueber alle Sitzungen).

        Bevorzugt echte Runden aus der laps-Tabelle; je Sitzungstyp
        Rueckfall auf die besten Runden (best_lap_ms). optimal_ms ist die
        theoretische Bestzeit aus den besten Einzelsektoren; None, wenn
        keine vollstaendigen Sektorenzeiten vorliegen.
        vehicle_class beschraenkt die Rekordberechnung auf eine Klasse
        (mehrere Klassen = je Klasse eigene Rekorde)."""
        filt = ("s.track = ?" + (" AND s.layout = ?" if layout else "")
                + (" AND " + _AI_HIDE.format(p="e.") if self.hide_ai else ""))
        params = [track] + ([layout] if layout else [])
        if vehicle_class:
            filt += "AND e.vehicle_class = ? "
            params.append(vehicle_class)

        def best_lap_of_type(type_like):
            q = ("SELECT MIN(l.lap_time_ms) FROM laps l "
                 "JOIN entries e ON e.id = l.entry_id "
                 "JOIN sessions s ON s.id = e.session_id "
                 f"WHERE {filt} AND l.lap_time_ms > 0 "
                 "AND s.session_type LIKE ?")
            v = self.conn.execute(q, params + [type_like]).fetchone()[0]
            if v:
                return v
            q = ("SELECT MIN(e.best_lap_ms) FROM entries e "
                 "JOIN sessions s ON s.id = e.session_id "
                 f"WHERE {filt} AND e.best_lap_ms > 0 "
                 "AND s.session_type LIKE ?")
            return self.conn.execute(q, params + [type_like]).fetchone()[0]

        race = best_lap_of_type("Race%")
        qualify = best_lap_of_type("Qualify%")
        q_all = ("SELECT MIN(l.lap_time_ms) FROM laps l "
                 "JOIN entries e ON e.id = l.entry_id "
                 "JOIN sessions s ON s.id = e.session_id "
                 f"WHERE {filt} AND l.lap_time_ms > 0")
        alltime = self.conn.execute(q_all, params).fetchone()[0]
        if not alltime:
            q_best = ("SELECT MIN(e.best_lap_ms) FROM entries e "
                      "JOIN sessions s ON s.id = e.session_id "
                      f"WHERE {filt} AND e.best_lap_ms > 0")
            alltime = self.conn.execute(q_best, params).fetchone()[0]
        q_opt = ("SELECT MIN(l.s1_ms), MIN(l.s2_ms), MIN(l.s3_ms) FROM laps l "
                 "JOIN entries e ON e.id = l.entry_id "
                 "JOIN sessions s ON s.id = e.session_id "
                 f"WHERE {filt} AND l.s1_ms > 0 AND l.s2_ms > 0 "
                 "AND l.s3_ms > 0")
        s1, s2, s3 = self.conn.execute(q_opt, params).fetchone()
        optimal = (s1 + s2 + s3) if (s1 and s2 and s3) else None
        return {"race_ms": race, "qualify_ms": qualify,
                "best_ms": alltime, "optimal_ms": optimal}

    # ------------------------------------------------- 0.4.0 Kraftstoff --

    def avg_lap_ms(self, track, layout="", vehicle="", driver=""):
        """Durchschnittliche Rundenzeit in ms fuer den Kraftstoffrechner.

        Bevorzugt echte Runden aus der laps-Tabelle; Fallback ist der
        Durchschnitt der besten Runden (best_lap_ms). Rueckgabe None,
        wenn ueberhaupt keine Zeiten vorliegen.
        """
        q_laps = ("SELECT AVG(l.lap_time_ms) AS avg_ms "
                  "FROM laps l "
                  "JOIN entries e ON e.id = l.entry_id "
                  "JOIN sessions s ON s.id = e.session_id "
                  "WHERE s.track = ? AND l.lap_time_ms > 0 ")
        params = [track]
        if layout:
            q_laps += "AND s.layout = ? "
            params.append(layout)
        if vehicle:
            q_laps += "AND e.vehicle = ? "
            params.append(vehicle)
        if driver:
            q_laps += "AND e.name = ? "
            params.append(driver)
        row = self.conn.execute(q_laps, params).fetchone()
        if row and row["avg_ms"]:
            return round(row["avg_ms"], 1)
        # Fallback: Durchschnitt der besten Runden (gleiche Filter).
        q_best = ("SELECT AVG(e.best_lap_ms) AS avg_ms "
                  "FROM entries e JOIN sessions s ON s.id = e.session_id "
                  "WHERE s.track = ? AND e.best_lap_ms > 0 ")
        q_best += "".join(part for part, cond in (
            ("AND s.layout = ? ", layout),
            ("AND e.vehicle = ? ", vehicle),
            ("AND e.name = ? ", driver)) if cond)
        row = self.conn.execute(q_best, params).fetchone()
        if row and row["avg_ms"]:
            return round(row["avg_ms"], 1)
        return None
