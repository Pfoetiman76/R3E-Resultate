"""Live aufgezeichnete Runden (0.5.0) — Speicher und Zusammenführung.

Der Recorder (rrc/recorder.py) schreibt waehrend der Fahrt jede
abgeschlossene Runde mit ihrer GEMESSENEN Zeit in ``live_laps.json``
(dokumentiert in Dokumente\\RaceRoom Results Companion). Beim Einlesen
einer Ergebnisdatei werden ungueltige Runden (Platzhalter lapTimeMs -1)
mit diesen Live-Zeiten gefuellt, so dass die Rundenansicht sie rot
anzeigen kann.

Aufbau (schema_version 1, UTF-8, atomar geschrieben):
{"schema_version": 1, "sessions": [
  {"started": "...", "ended": "...", "session_type": "Practice",
   "track_name": "...", "layout_name": "", "track_id": 0, "layout_id": 0,
   "player_name": "...",
   "laps": [{"lap_no": 1, "time_ms": 65432, "valid": 0, "ts": "...",
             "fuel_after": 38.2}],
   "fuel": {"capacity": 60.0, "per_lap": 3.05, "start": 45.0, "end": 38.2}}]}
"""
from __future__ import annotations

import json
import os

SCHEMA_VERSION = 1
LIVE_FILENAME = "live_laps.json"


def store_path(app_dir):
    return os.path.join(app_dir, LIVE_FILENAME)


def load_store(path):
    """Liest live_laps.json; korrupte/fehlende Datei -> leerer Store."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get("sessions"), list):
            return _empty()
        return data
    except Exception:
        return _empty()


def save_store(path, data):
    """Schreibt live_laps.json atomar (erst .tmp, dann replace)."""
    data = dict(data)
    data["schema_version"] = SCHEMA_VERSION
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _empty():
    return {"schema_version": SCHEMA_VERSION, "sessions": []}


def prune(data, keep=20):
    """Nur die letzten ``keep`` Sitzungen behalten (Datei klein halten)."""
    data = dict(data)
    data["sessions"] = list(data.get("sessions", []))[-keep:]
    return data


# --------------------------------------------------------------------------- --
# Zusammenfuehren: Live-Zeiten in geparste Sitzungen einsetzen
# --------------------------------------------------------------------------- --
def _parse_ts(ts):
    """"YYYY/MM/DD HH:MM:SS" (Ergebnisdatei) oder ISO -> time.mktime-taugliche
    Tupel; bei unbekanntem Format None."""
    if not ts:
        return None
    try:
        import time
        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return time.mktime(time.strptime(str(ts), fmt))
            except ValueError:
                continue
    except Exception:
        pass
    return None


def find_session(store, file_timestamp, track_name="", layout_name=""):
    """Passende Live-Sitzung zur Ergebnisdatei suchen.

    Kriterium: Der Zeitstempel der Ergebnisdatei (Sitzungs-ENDE) liegt
    innerhalb [start - 15 min, ende + 10 min] der Live-Sitzung. Strecke
    und Layout werden zusaetzlich verglichen, wenn beide Quellen sie
    nennen (Toleranz: Gross-/Kleinschreibung)."""
    ts = _parse_ts(file_timestamp)
    if ts is None:
        return None
    cands = []
    for s in store.get("sessions", []):
        st = _parse_ts(s.get("started"))
        en = _parse_ts(s.get("ended")) or st
        if st is None:
            continue
        if not (st - 900 <= ts <= en + 600):
            continue
        t = str(s.get("track_name") or "").strip().lower()
        l = str(s.get("layout_name") or "").strip().lower()
        if t and track_name and t != str(track_name).strip().lower():
            continue
        if (l and layout_name and str(layout_name).strip().lower()
                and l != str(layout_name).strip().lower()):
            continue
        cands.append((abs(ts - (en or st)), s))
    if not cands:
        return None
    cands.sort(key=lambda e: e[0])
    return cands[0][1]


def fill_session(sess, store):
    """Ungueltige Runden einer GEPARSTEN Sitzung mit Live-Zeiten fuellen.

    Nur Runden mit lap_time_ms < 0 werden gefuellt; die Gueltigkeit wird
    als valid=0 am LapEntry markiert. Rueckgabe: Anzahl gefuellter Runden.
    """
    live = find_session(store, getattr(sess, "timestamp", ""),
                        getattr(sess, "track", ""),
                        getattr(sess, "layout", ""))
    if not live:
        return 0
    by_no = {}
    for lp in live.get("laps", []):
        try:
            by_no[int(lp.get("lap_no", -1))] = lp
        except (TypeError, ValueError):
            continue
    n = 0
    for p in sess.players:
        for lp in p.laps_detail:
            if lp.lap_time_ms > 0:
                continue
            m = by_no.get(int(lp.lap_no))
            if not m:
                continue
            t = int(m.get("time_ms", 0) or 0)
            if t <= 0:
                continue
            lp.lap_time_ms = t
            lp.valid = 0
            n += 1
    return n
