"""Live-Tab (0.6.0): Qt-freie Logik fuer den Reiter „Live“.

Zwei Bausteine:

TrackMapCollector — sammelt Streckenpunkte aus der Fahrzeugposition
(highgenau aus dem Shared Memory), gedrosselt: nur bei Fahrt, nur
hinreichend weit vom letzten Punkt. Die Punkte werden pro Strecke nur im
Arbeitsspeicher gehalten (keine Datenbank-Erweiterung) und auf
Normalgroesse (0..1) abgebildet, damit QPainter sie zeichnen kann.

LiveState — haelt den darzustellenden Zustand der laufenden Sitzung:
Kacheln (laufende/letzte/beste Runde, Kraftstoff), Sektorzeiten,
Rundenliste (neueste zuerst, ungueltige markiert, Bestzeit markiert) und
Statusmeldungen. Der Recorder speist ihn mit LiveSample-Objekten.
"""
from __future__ import annotations

# Kartenpunkte: nur aufnehmen, wenn das Fahrzeug mindestens so weit
# seit dem letzten Punkt zurueckgelegt hat (Meter) und so schnell faehrt.
MAP_MIN_STEP_M = 4.0
MAP_MIN_SPEED = 0.5
# Obergrenze, damit auch sehr lange Sitzungen schlank bleiben.
MAP_MAX_POINTS = 4000


class TrackMapCollector:
    """Sammelt normalisierte Streckenpunkte (x, z) einer Strecke."""

    def __init__(self):
        self.points = []          # [(x_m, z_m), ...] in Streckenmetern
        self._last = None         # (x, z) des letzten aufgenommenen Punkts
        self._min_x = self._max_x = None
        self._min_z = self._max_z = None

    def reset(self):
        self.__init__()

    def add(self, sample) -> bool:
        """Punkt aufnehmen, wenn Drosselung es zulaesst; True bei Aufnahme."""
        if sample is None:
            return False
        speed = getattr(sample, "speed", 0.0) or 0.0
        if speed < MAP_MIN_SPEED:
            return False
        x = getattr(sample, "pos_x", None)
        z = getattr(sample, "pos_z", None)
        if x is None or z is None:
            return False
        if self._last is not None:
            dx = x - self._last[0]
            dz = z - self._last[1]
            if (dx * dx + dz * dz) ** 0.5 < MAP_MIN_STEP_M:
                return False
        if len(self.points) >= MAP_MAX_POINTS:
            return False
        self.points.append((x, z))
        self._last = (x, z)
        if self._min_x is None or x < self._min_x:
            self._min_x = x
        if self._max_x is None or x > self._max_x:
            self._max_x = x
        if self._min_z is None or z < self._min_z:
            self._min_z = z
        if self._max_z is None or z > self._max_z:
            self._max_z = z
        return True

    def normalized(self):
        """Punkte auf 0..1 abbilden (Y gespiegelt: z waechst nach Sueden).

        Rueckgabe: Liste (nx, nz) oder [], solange weniger als 2 Punkte
        bzw. keine Ausdehnung bekannt ist.
        """
        if len(self.points) < 2 or self._min_x is None:
            return []
        w = (self._max_x - self._min_x) or 1.0
        h = (self._max_z - self._min_z) or 1.0
        return [((x - self._min_x) / w, (z - self._min_z) / h)
                for x, z in self.points]

    def normalized_pos(self, sample):
        """Aktuelle Fahrzeugposition normalisiert oder None."""
        if self._min_x is None or sample is None:
            return None
        x = getattr(sample, "pos_x", None)
        z = getattr(sample, "pos_z", None)
        if x is None or z is None:
            return None
        w = (self._max_x - self._min_x) or 1.0
        h = (self._max_z - self._min_z) or 1.0
        return ((x - self._min_x) / w, (z - self._min_z) / h)


def fmt_lap_ms(ms):
    """Rundenzeit in ms als Anzeigestring; None/<=0 -> ''."""
    if ms is None or ms <= 0:
        return ""
    s = ms / 1000.0
    if s >= 60:
        m = int(s // 60)
        return f"{m}:{s - m * 60:06.3f}"
    return f"{s:.3f}"


def fmt_sector_s(sec_s):
    """Sektorzeit in Sekunden als Anzeigestring; None -> ''."""
    if sec_s is None or sec_s <= 0:
        return ""
    return f"{sec_s:.3f}"


def sectors_to_ms(sector_seconds):
    """3 Sektorzeiten (Sekunden, None moeglich) -> ms-Liste (-1 = fehlt)."""
    out = []
    for v in (sector_seconds or [None, None, None])[:3]:
        try:
            out.append(int(round(float(v) * 1000.0)) if v else -1)
        except (TypeError, ValueError):
            out.append(-1)
    while len(out) < 3:
        out.append(-1)
    return out


class LiveState:
    """Darstellungszustand des Live-Tab; vom Recorder gespeist."""

    def __init__(self):
        self.map = TrackMapCollector()
        self.reset()

    def reset(self):
        self.active = False          # Sitzung laeuft (in Car, Daten da)
        self.track_label = ""
        self.session_type = ""
        self.current_lap_s = None
        self.lap_no = 0
        self.last_lap_ms = None
        self.last_lap_valid = True
        self.best_lap_ms = None
        self.delta_best_s = None
        self.sector_current = (None, None, None)
        self.sector_previous = (None, None, None)
        self.sector_best = (None, None, None)
        self.sector_index = 0
        self.fuel_left = None
        self.fuel_capacity = None
        self.fuel_per_lap = None
        self.speed = 0.0
        self.pos_norm = None
        self.laps = []                # neueste zuerst, siehe lap_done()
        self.status = ""

    # ----- Einspeisung ----------------------------------------------------
    def update(self, sample, status=""):
        """Neuer Tick mit frischem LiveSample (oder None: keine Sitzung)."""
        self.reset()
        self.status = status
        if sample is None or not getattr(sample, "in_car", False):
            return
        self.active = True
        self.track_label = ((sample.track_name or "?")
                            + ((" – " + sample.layout_name)
                               if getattr(sample, "layout_name", "") else ""))
        self.session_type = sample.session_type or ""
        self.current_lap_s = getattr(sample, "lap_time_current_s", 0.0) or 0.0
        self.lap_no = getattr(sample, "completed_laps", 0) or 0
        prev_ms = None
        prev_s = getattr(sample, "lap_time_previous_s", 0.0) or 0.0
        if prev_s > 0:
            prev_ms = int(round(prev_s * 1000.0))
        if prev_ms is not None:
            self.last_lap_ms = prev_ms
            self.last_lap_valid = bool(getattr(sample, "prev_lap_valid", 1))
        best_s = getattr(sample, "lap_time_best_s", None)
        if best_s:
            self.best_lap_ms = int(round(best_s * 1000.0))
        self.delta_best_s = getattr(sample, "delta_best_s", None)
        self.sector_current = tuple(
            getattr(sample, "sector_current", None) or (None,) * 3)
        self.sector_previous = tuple(
            getattr(sample, "sector_previous", None) or (None,) * 3)
        self.sector_best = tuple(
            getattr(sample, "sector_best", None) or (None,) * 3)
        self.sector_index = max(0, int(getattr(sample, "track_sector", 0) or 0))
        self.fuel_left = getattr(sample, "fuel_left", None)
        self.fuel_capacity = getattr(sample, "fuel_capacity", None)
        self.fuel_per_lap = getattr(sample, "fuel_per_lap", None)
        self.speed = getattr(sample, "speed", 0.0) or 0.0
        self.map.add(sample)
        self.pos_norm = self.map.normalized_pos(sample)

    def set_laps(self, laps):
        """Rundenliste der aktuellen Sitzung uebernehmen (aelteste zuerst,
        ungesehen vom Recorder); intern wird neueste zuerst gehalten."""
        rows = []
        best_ms = None
        for rec in laps or []:
            t = rec.get("time_ms", 0) or 0
            if t > 0 and rec.get("valid", 1) and (best_ms is None or t < best_ms):
                best_ms = t
        for rec in reversed(laps or []):
            t = rec.get("time_ms", 0) or 0
            secs = rec.get("sectors_ms", None) or [-1, -1, -1]
            rows.append({
                "lap_no": rec.get("lap_no", 0),
                "time_ms": t if t > 0 else None,
                "valid": bool(rec.get("valid", 1)),
                "sectors_ms": list(secs),
                "fuel_after": rec.get("fuel_after", -1),
                "best": bool(t and t > 0 and rec.get("valid", 1)
                             and t == best_ms),
            })
        self.laps = rows
        if best_ms and (self.best_lap_ms is None or best_ms < self.best_lap_ms):
            self.best_lap_ms = best_ms

    # ----- abgeleitete Werte ---------------------------------------------
    def fuel_laps_left(self):
        """Geschaetzte verbleibende Runden mit dem Kraftstoff (oder None)."""
        if (self.fuel_left is not None and self.fuel_per_lap
                and self.fuel_per_lap > 0):
            return self.fuel_left / self.fuel_per_lap
        return None
