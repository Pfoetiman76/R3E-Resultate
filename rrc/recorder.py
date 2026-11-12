"""Live-Recorder (0.5.0): Runden live aufzeichnen, Kraftstoff erfassen.

Laeuft als Ticker (QTimer in main.py, ~10 Hz) und liest pro Tick einmal
den RaceRoom-Shared-Memory. Bei jedem Rundenwechsel (completed_laps
steigt) wird die zuvor gefahrene Runde mit ihrer gemessenen Zeit und
ihrem Gueltigkeits-Flag in die Live-Sitzung (rrc/livelaps.py) geschrieben.

Kraftstoff: je abgeschlossener Runde wird der verbleibende Kraftstoff
notiert; beim Sitzungsende werden Verbrauch pro Runde (Mittelwert) und
Tankgroesse in fuel_history.json eingetragen (Eigentuemer dieser App,
Konzept-Thema r3e-datenkonzept).
"""
from __future__ import annotations

import time
from datetime import datetime

from . import fuelcalc
from . import livelaps
from . import trackids
from .livetab import LiveState, sectors_to_ms
from .raceroom_sm import R3EReader


class LapRecorder:
    """Protokolliert Runden aus dem Shared Memory in live_laps.json."""

    def __init__(self, app_dir, reader=None, clock=None):
        self.app_dir = app_dir
        self.path = livelaps.store_path(app_dir)
        self.reader = reader or R3EReader()
        self._clock = clock or time.time
        self.store = livelaps.load_store(self.path)
        self.current = None
        self.n_new_laps = 0
        # 0.6.0: Darstellungszustand fuer den Reiter „Live"
        self.live = LiveState()

    # ----- Sitzungsverwaltung ------------------------------------------------
    def _new_session(self, s):
        return {
            "started": datetime.fromtimestamp(self._clock()).strftime("%Y-%m-%d %H:%M:%S"),
            "ended": "",
            "session_type": s.session_type,
            "track_name": s.track_name,
            "layout_name": s.layout_name,
            "track_id": s.track_id,
            "layout_id": s.layout_id,
            "player_name": s.player_name,
            "laps": [],
            "fuel": {"capacity": s.fuel_capacity, "per_lap": 0.0,
                     "start": s.fuel_left, "end": s.fuel_left},
        }

    def _identity(self, s):
        if isinstance(s, dict):     # bereits aufgebaute Live-Sitzung
            return (s.get("track_id"), s.get("layout_id"),
                    s.get("session_type"))
        return (s.track_id, s.layout_id, s.session_type)

    def _close_session(self):
        if not self.current:
            return
        cur = self.current
        laps = cur["laps"]
        cur["ended"] = datetime.fromtimestamp(self._clock()).strftime("%Y-%m-%d %H:%M:%S")
        # Kraftstoff: Mittelwert des Verbrauchs ueber alle Rundenpaare
        fuels = [lp["fuel_after"] for lp in laps if lp.get("fuel_after", -1) >= 0]
        f = cur["fuel"]
        if len(fuels) >= 2 and f.get("capacity", 0) > 0:
            per_lap = (fuels[0] - fuels[-1]) / (len(fuels) - 1)
            if 0.05 < per_lap <= f["capacity"]:
                f["per_lap"] = round(per_lap, 3)
                self._update_fuel_history(cur)
        self.store = livelaps.prune(self.store)
        livelaps.save_store(self.path, self.store)
        self.current = None

    def _vehicle_name(self, cur):
        mid = cur.get("model_id", 0)
        if mid:
            name = trackids.resolve_car(mid)
            if name:
                return name
            return f"Fahrzeug-Id {int(mid)}"
        return "?"

    def _update_fuel_history(self, cur):
        """Verbrauch/Tankgroesse in fuel_history.json eintragen."""
        try:
            hp = fuelcalc.history_path(self.app_dir)
            hist = fuelcalc.load_history(hp)
            fuelcalc.put_entry(hist, cur["track_name"] or "?",
                               self._vehicle_name(cur),
                               cur["fuel"]["per_lap"], cur["fuel"]["capacity"])
            fuelcalc.save_history(hp, hist)
        except Exception:
            pass  # Kraftstoffverlauf ist Komfort, nie abbruchwuerdig

    # ----- Ticker ------------------------------------------------------------
    def close(self):
        """Aufzeichnung ordnungsgemäß beenden (Sitzung schließen, speichern)."""
        if self.current:
            self._close_session()
        else:
            livelaps.save_store(self.path, self.store)

    def tick(self):
        """Einmal lesen und Rundenwechsel protokollieren.

        Rueckgabe: (status, meldung) mit status in
        'ok' | 'idle' | 'error' | 'closed'."""
        try:
            s = self.reader.read()
        except Exception as e:
            if self.current:
                self._close_session()
                self.live.update(None, f"Aufzeichnung beendet ({e})")
                return "closed", f"Aufzeichnung beendet ({e})"
            self.live.update(None, str(e))
            return "error", str(e)
        if s is None or not s.in_car:
            if self.current:
                self._close_session()
                self.live.update(None, "Sitzung beendet")
                return "closed", "Sitzung beendet, Aufzeichnung gespeichert"
            self.live.update(None, "Warte auf RaceRoom-Sitzung …")
            return "idle", "Warte auf RaceRoom-Sitzung …"
        if self.current and self._identity(s) != self._identity(self.current):
            self._close_session()
        if not self.current:
            self.current = self._new_session(s)
            self.current["model_id"] = s.model_id
            self.store.setdefault("sessions", []).append(self.current)
            self.n_new_laps = 0
        cur = self.current
        cur["fuel"]["capacity"] = s.fuel_capacity or cur["fuel"]["capacity"]
        if s.completed_laps > len(cur["laps"]):
            # Neuer Wert: Runde abgeschlossen; Zeit der VORHERIGEN Runde
            # steht in lap_time_previous_self (Sekunden), ihre Sektoren-
            # Einzelseiten in sector_time_previous_self (0.6.0).
            t_ms = int(round(s.lap_time_previous_s * 1000.0))
            lap_no = len(cur["laps"]) + 1
            valid = 1 if s.prev_lap_valid else 0
            rec = {"lap_no": lap_no, "time_ms": t_ms,
                   "valid": valid,
                   "sectors_ms": sectors_to_ms(getattr(s, "sector_previous", None)),
                   "ts": datetime.fromtimestamp(self._clock()).strftime("%Y-%m-%d %H:%M:%S"),
                   "fuel_after": s.fuel_left if s.fuel_left >= 0 else -1}
            cur["laps"].append(rec)
            self.n_new_laps += 1
            livelaps.save_store(self.path, self.store)
            self.live.update(s, "")
            self.live.set_laps(cur["laps"])
            return "ok", (f"Runde {lap_no}: {t_ms / 1000.0:.3f} s"
                          + ("" if valid else " (ungültig)"))
        self.live.update(s, "")
        self.live.set_laps(cur["laps"])
        return "ok", ""
