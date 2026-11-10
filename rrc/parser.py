"""Parsers for RaceRoom result files.

Supported formats (all normalized into rrc.models.Session):
- SP/local results .txt files (since May 2023, actually JSON) from
  Documents\\My Games\\SimBin\\RaceRoom Racing Experience\\UserData\\Log\\Results
- Dedicated-server result .json (top-level "Server" key)
- Multiplayer result .xml (root <MultiplayerRaceResult>)

All parsers are tolerant: unknown fields are ignored, missing fields default.
"""
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET

from . import paths
from .models import LapEntry, PlayerResult, Session

# Session type suffixes used by R3E result file names:
# e.g. 2023_06_03_14_13_21_Race1.txt
_FILENAME_RE = re.compile(
    r"^(?P<year>\d{4})_(?P<month>\d{2})_(?P<day>\d{2})_"
    r"(?P<hour>\d{2})_(?P<min>\d{2})_(?P<sec>\d{2})"
    r"(?:_(?P<type>[A-Za-z0-9]+))?"
)


def _load_id_maps():
    """Load ID mappings from the app data folder: user-defined mappings
    (track_names.json) and, if a RaceRoom installation folder is set in
    settings.json, the official game data (r3e-data.json). Returns
    (user, official); official is None when unavailable."""
    from . import trackids
    user = trackids.load_user_names(
        trackids.user_names_path(paths.default_app_dir()))
    official = None
    try:
        from . import appsettings
        settings = appsettings.load_settings(
            appsettings.settings_path(paths.default_app_dir()))
        install_dir = settings.get("r3e_install_dir") or ""
        if install_dir:
            official = trackids.load_official(install_dir)
    except Exception:
        official = None
    return user, official


def _first(d, *keys, default=None):
    """Return first present, non-None value of keys in dict d (case-insensitive fallback)."""
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None:
            return d[k]
    lower = {str(k).lower(): v for k, v in d.items()} if isinstance(d, dict) else {}
    for k in keys:
        v = lower.get(k.lower())
        if v is not None:
            return v
    return default


def _ms(value):
    try:
        v = int(round(float(value)))
        return v if v > 0 else 0
    except (TypeError, ValueError):
        return 0


def session_type_from_filename(filename: str) -> str:
    m = _FILENAME_RE.match(os.path.basename(filename))
    if m and m.group("type"):
        return m.group("type")
    return ""


def datetime_from_filename(filename: str) -> str:
    m = _FILENAME_RE.match(os.path.basename(filename))
    if not m:
        return ""
    return (f"{m.group('year')}-{m.group('month')}-{m.group('day')} "
            f"{m.group('hour')}:{m.group('min')}:{m.group('sec')}")


# ---------------------------------------------------------------- SP JSON ---

def parse_sp_json(data: dict, filename: str = "") -> Session:
    """Parse single-player .txt (JSON) result file.

    Expected shape (reverse-engineered, keys tolerant):
      header.time, event.track / event.layout / event.layoutId,
      drivers: [{name, vehicle, carId, team, place, qualtimems,
                 racetimems, bestlaptimems, totallaps}]
    """
    header = data.get("header") or {}
    event = data.get("event") or {}
    ts = str(_first(header, "time", default="") or "")
    if not ts and filename:
        ts = datetime_from_filename(filename)

    sess = Session(
        session_type=session_type_from_filename(filename),
        timestamp=ts,
        track=str(_first(event, "track", default="") or ""),
        layout=str(_first(event, "layout", default="") or ""),
        source_file=os.path.basename(filename),
    )
    if not sess.track:
        layout_id = _first(event, "layoutId", "layoutid")
        if layout_id:
            # RaceRoom names tracks in SP results only by a numeric layout ID.
            # Translate it into a readable name where possible.
            from . import trackids
            user_names, official = _load_id_maps()
            mapped = trackids.resolve_layout_with(layout_id, user_names,
                                                  official)
            if mapped:
                sess.track, sess.layout = mapped[0], mapped[1]
            else:
                sess.track = str(layout_id)
                sess.layout = "(Layout-Id)"

    from . import trackids
    user_names, official = _load_id_maps()
    for d in data.get("drivers") or []:
        if not isinstance(d, dict):
            continue
        name = _first(d, "name", default="")
        if not name:
            continue
        # Fahrzeug: SP-Ergebnisse nennen das Fahrzeug nur als interne
        # Nummer (carId); aeltere/community-Formate auch als Textfeld.
        car_id = _ms(_first(d, "carId", "carid", "carid", default=0))
        vehicle = str(_first(d, "vehicle", "car", "carId", "carid",
                             default="") or "")
        if not car_id and trackids.is_id(vehicle):
            car_id = _ms(vehicle)
        if car_id:
            resolved = trackids.resolve_car_with(car_id, user_names,
                                                 official)
            if resolved:
                vehicle = resolved
        vehicle_class = (trackids.resolve_car_class(car_id, official)
                         if car_id else "")
        # KI-Fahrer: das SP-Format kennzeichnet sie mit userId -1
        uid = _first(d, "userId", "userid", default=None)
        if uid is None:
            is_ai = -1
        else:
            try:
                is_ai = 1 if int(uid) < 1 else 0
            except (TypeError, ValueError):
                is_ai = -1
        # Runden (neueres SP-Format ab Spiel 0.9.9): 'laps'-Liste je Fahrer.
        # KI-Fahrer enthaelt nur Platzhalter (lapTimeMs -1) sowie einen
        # Artefakt-Wert in totalLaps (immer 856, unabhaengig vom Fahren);
        # gezaehlt werden ausschliesslich Runden mit gueltiger Zeit.
        laps_detail = []
        for lp in d.get("laps") or []:
            if not isinstance(lp, dict):
                continue
            lt = _ms(_first(lp, "lapTimeMs", "lapTimems", "laptime",
                            default=0))
            if lt > 0:
                laps_detail.append(
                    LapEntry(_ms(_first(lp, "number", default=0)), lt, []))
        total_laps = _ms(_first(d, "totallaps", "totalLaps", "laps",
                                default=0))
        if laps_detail:
            laps = len(laps_detail)
        elif total_laps > 500:
            # KI-Artefakt (856) ohne eine einzige gueltige Rundenzeit
            laps = 0
        else:
            laps = max(total_laps, 0)
        sess.players.append(PlayerResult(
            name=str(name),
            vehicle=vehicle,
            team=str(_first(d, "team", default="") or ""),
            position=_ms(_first(d, "place", "position", default=0)),
            laps=laps,
            best_lap_ms=_ms(_first(d, "bestlaptimems", "bestLapTimeMs",
                                   "bestlap", "bestLapTime", default=0)),
            qual_ms=_ms(_first(d, "qualtimems", "qualTimeMs", default=0)),
            race_time_ms=_ms(_first(d, "racetimems", "raceTimeMs",
                                    "totalTime", default=0)),
            finish_status=str(_first(d, "finishStatus", default="") or ""),
            laps_detail=laps_detail,
            car_id=car_id,
            is_ai=is_ai,
            vehicle_class=vehicle_class,
        ))
    sess.digest = make_digest(sess, filename)
    return sess


# ------------------------------------------------- Dedicated-server JSON ---

def parse_dedicated_json(data: dict, filename: str = "") -> list:
    """Parse dedicated-server JSON (top-level 'Server' key).

    Shape: Time (epoch ms or string), Track, TrackLayout,
           Sessions: [{Type: Qualify|Race|Race2|Race3,
                       Players: [{Name, Car, FinishStatus, TotalTime,
                                  BestLapTime, Position, RaceSessionLaps}]}]
    Returns one Session per Race/Race2/Race3 plus a Qualify session.
    """
    raw_time = _first(data, "time", default=0)
    base_ts = ""
    try:
        if isinstance(raw_time, str):
            raw_time = int(re.match(r"(\d+)", raw_time).group(1))
        import datetime
        base_dt = datetime.datetime.fromtimestamp(int(raw_time) / 1000)
        base_ts = base_dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        base_ts = datetime_from_filename(filename)

    track = str(_first(data, "track", default="") or "")
    layout = str(_first(data, "trackLayout", default="") or "")

    sessions = []
    for idx, s in enumerate(data.get("Sessions") or []):
        stype = str(_first(s, "type", default="") or "")
        if not stype:
            continue
        sess = Session(
            session_type=stype,
            timestamp=base_ts,
            track=track,
            layout=layout,
            source_file=os.path.basename(filename),
        )
        for p in s.get("Players") or []:
            if not isinstance(p, dict):
                continue
            name = _first(p, "name", "driverName", default="")
            if not name:
                continue
            laps = p.get("RaceSessionLaps") or []
            laps_detail = []
            for i, lp in enumerate(laps, 1):
                if isinstance(lp, dict):
                    lt = _ms(_first(lp, "lapTime", "time", default=0))
                    sectors = [_ms(x) for x in (lp.get("SectorTimes") or [])]
                else:
                    lt = _ms(lp)
                    sectors = []
                laps_detail.append(LapEntry(i, lt, sectors))
            sess.players.append(PlayerResult(
                name=str(name),
                vehicle=str(_first(p, "car", "vehicle", default="") or ""),
                team=str(_first(p, "team", default="") or ""),
                position=_ms(_first(p, "position", default=0)),
                laps=len(laps_detail) or _ms(_first(p, "laps", default=0)),
                best_lap_ms=_ms(_first(p, "bestLapTime", default=0)),
                qual_ms=_ms(_first(p, "qualifyTime", "bestQualLapTime", default=0)),
                race_time_ms=_ms(_first(p, "totalTime", default=0)),
                finish_status=str(_first(p, "finishStatus", default="") or ""),
                laps_detail=laps_detail,
            ))
        if sess.players:
            sess.digest = make_digest(sess, filename, extra=idx)
            sessions.append(sess)
    return sessions


# ------------------------------------------------------- Multiplayer XML ---

def _xml_sessions(root, filename: str) -> list:
    ts_raw = root.findtext("Time") or ""
    ts = ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):([\d.]+)", ts_raw)
    if m:
        sec = int(float(m.group(6)))
        ts = (f"{m.group(1)}-{m.group(2)}-{m.group(3)} "
              f"{m.group(4)}:{m.group(5)}:{sec:02d}")
    if not ts:
        ts = datetime_from_filename(filename)

    track = (root.findtext("Track") or "").strip()
    layout = (root.findtext("TrackLayout") or "").strip()

    sessions = []
    for idx, snode in enumerate(root.findall("Sessions/Session")):
        stype = (snode.findtext("Type") or "").strip()
        if not stype:
            continue
        sess = Session(session_type=stype, timestamp=ts, track=track,
                       layout=layout, source_file=os.path.basename(filename))
        for pnode in snode.findall("Players/Player"):
            name = (pnode.findtext("Name") or pnode.findtext("DriverName") or "").strip()
            if not name:
                continue
            laps_detail = []
            for i, lp in enumerate(pnode.findall("RaceSessionLaps/Lap"), 1):
                lt = _ms(lp.findtext("Time") or lp.text or 0)
                sectors = [_ms(x.text) for x in lp.findall("SectorTimes/SectorTime")]
                laps_detail.append(LapEntry(i, lt, sectors))
            finish = (pnode.findtext("FinishStatus") or "").strip()
            sess.players.append(PlayerResult(
                name=name,
                vehicle=(pnode.findtext("Car") or "").strip(),
                team=(pnode.findtext("Team") or "").strip(),
                position=_ms(pnode.findtext("Position")),
                laps=len(laps_detail),
                best_lap_ms=_ms(pnode.findtext("BestLapTime")),
                race_time_ms=_ms(pnode.findtext("TotalTime")),
                finish_status=finish,
                laps_detail=laps_detail,
            ))
        if sess.players:
            sess.digest = make_digest(sess, filename, extra=idx)
            sessions.append(sess)
    return sessions


# -------------------------------------------------------------- Dispatch ---

def make_digest(sess: Session, filename: str = "", extra: object = "") -> str:
    h = hashlib.md5()
    h.update(str(filename).encode("utf-8", "replace"))
    h.update(str(extra).encode("utf-8", "replace"))
    h.update(sess.session_type.encode("utf-8", "replace"))
    h.update(sess.timestamp.encode("utf-8", "replace"))
    h.update(sess.track.encode("utf-8", "replace"))
    h.update(sess.layout.encode("utf-8", "replace"))
    for p in sess.players:
        h.update(p.name.encode("utf-8", "replace"))
        h.update(p.vehicle.encode("utf-8", "replace"))
        h.update(str(p.position).encode())
        h.update(str(p.best_lap_ms).encode())
    return h.hexdigest()


def parse_file(path: str):
    """Detect format and parse. Returns list[Session] (empty on failure)."""
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            text = f.read(8 * 1024 * 1024)
    except OSError:
        return []

    stripped = text.lstrip()
    sessions = []
    if stripped.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        if "Server" in data:
            sessions = parse_dedicated_json(data, path)
        else:
            s = parse_sp_json(data, path)
            if s.players:
                sessions = [s]
    elif stripped.startswith("<"):
        try:
            root = ET.fromstring(text)
        except ET.ParseError:
            return []
        root_name = root.tag.split("}")[-1]
        if root_name == "MultiplayerRaceResult":
            sessions = _xml_sessions(root, path)
    return sessions
