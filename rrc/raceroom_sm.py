"""RaceRoom Shared-Memory-Reader fuer R3E-Resultate (0.5.0).

Liest den Shared-Memory-Block ``$R3E`` des Spiels, um waehrend der Fahrt
Rundenzeiten live aufzuzeichnen — einschliesslich der Zeiten UNGUELTIGER
Runden, die RaceRoom nur live anzeigt, aber nicht in die Ergebnisdatei
schreibt (dort steht lapTimeMs -1).

Struktur-Quelle: Sector3 Studios ``r3e-api/sample-c/src/r3e.h`` (Version 3.5,
#pragma pack(1)). Die ctypes-Klassen wurden aus diesem Header erzeugt und
gegen sizeof/offsetof eines mit gcc uebersetzten C-Programms geprueft
(315/315 identisch); uebernommen aus dem bewaehrten PitBoss-R3E-Reader
(eigenes Projekt von Marcel Wijnandts).

CLI:  python -m rrc.raceroom_sm   # Selbsttest gegen synthetischen Block
"""
from __future__ import annotations

import ctypes
import math
import sys

R3E_SHARED_MEMORY_NAME = "$R3E"
R3E_VERSION_MAJOR = 3
R3E_VERSION_MINOR_KNOWN = 5
R3E_NUM_DRIVERS_MAX = 128


c_int32 = ctypes.c_int32
c_float = ctypes.c_float
c_double = ctypes.c_double
c_ubyte = ctypes.c_ubyte


class R3EVec3F32(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("x", c_float),
        ("y", c_float),
        ("z", c_float),
    ]


class R3EVec3F64(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("x", c_double),
        ("y", c_double),
        ("z", c_double),
    ]


class R3EOriF32(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("pitch", c_float),
        ("yaw", c_float),
        ("roll", c_float),
    ]


class R3ESectorstarts(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("sector1", c_float),
        ("sector2", c_float),
        ("sector3", c_float),
    ]


class R3EPlayerdata(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("user_id", c_int32),
        ("game_simulation_ticks", c_int32),
        ("game_simulation_time", c_double),
        ("position", R3EVec3F64),
        ("velocity", R3EVec3F64),
        ("local_velocity", R3EVec3F64),
        ("acceleration", R3EVec3F64),
        ("local_acceleration", R3EVec3F64),
        ("orientation", R3EVec3F64),
        ("rotation", R3EVec3F64),
        ("angular_acceleration", R3EVec3F64),
        ("angular_velocity", R3EVec3F64),
        ("local_angular_velocity", R3EVec3F64),
        ("local_g_force", R3EVec3F64),
        ("steering_force", c_double),
        ("steering_force_percentage", c_double),
        ("engine_torque", c_double),
        ("current_downforce", c_double),
        ("voltage", c_double),
        ("ers_level", c_double),
        ("power_mgu_h", c_double),
        ("power_mgu_k", c_double),
        ("torque_mgu_k", c_double),
        ("suspension_deflection", c_double * 4),
        ("suspension_velocity", c_double * 4),
        ("camber", c_double * 4),
        ("ride_height", c_double * 4),
        ("front_wing_height", c_double),
        ("front_roll_angle", c_double),
        ("rear_roll_angle", c_double),
        ("third_spring_suspension_deflection_front", c_double),
        ("third_spring_suspension_velocity_front", c_double),
        ("third_spring_suspension_deflection_rear", c_double),
        ("third_spring_suspension_velocity_rear", c_double),
        ("unused1", c_double),
        ("unused2", c_double),
        ("unused3", c_double),
    ]


class R3EFlags(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("yellow", c_int32),
        ("yellowCausedIt", c_int32),
        ("yellowOvertake", c_int32),
        ("yellowPositionsGained", c_int32),
        ("sector_yellow", c_int32 * 3),
        ("closest_yellow_distance_into_track", c_float),
        ("blue", c_int32),
        ("black", c_int32),
        ("green", c_int32),
        ("checkered", c_int32),
        ("white", c_int32),
        ("black_and_white", c_int32),
    ]


class R3ECarDamage(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("engine", c_float),
        ("transmission", c_float),
        ("aerodynamics", c_float),
        ("suspension", c_float),
        ("unused1", c_float),
        ("unused2", c_float),
    ]


class R3ECutTrackPenalties(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("drive_through", c_float),
        ("stop_and_go", c_float),
        ("pit_stop", c_float),
        ("time_deduction", c_float),
        ("slow_down", c_float),
    ]


class R3EDrs(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("equipped", c_int32),
        ("available", c_int32),
        ("numActivationsLeft", c_int32),
        ("engaged", c_int32),
    ]


class R3EPushToPass(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("available", c_int32),
        ("engaged", c_int32),
        ("amount_left", c_int32),
        ("engaged_time_left", c_float),
        ("wait_time_left", c_float),
    ]


class R3ETireTemp(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("current_temp", c_float * 3),
        ("optimal_temp", c_float),
        ("cold_temp", c_float),
        ("hot_temp", c_float),
    ]


class R3EBrakeTemp(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("current_temp", c_float),
        ("optimal_temp", c_float),
        ("cold_temp", c_float),
        ("hot_temp", c_float),
    ]


class R3EAidSettings(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("abs", c_int32),
        ("tc", c_int32),
        ("esp", c_int32),
        ("countersteer", c_int32),
        ("cornering", c_int32),
    ]


class R3EDriverInfo(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("name", c_ubyte * 64),
        ("car_number", c_int32),
        ("class_id", c_int32),
        ("model_id", c_int32),
        ("team_id", c_int32),
        ("livery_id", c_int32),
        ("manufacturer_id", c_int32),
        ("user_id", c_int32),
        ("slot_id", c_int32),
        ("class_performance_index", c_int32),
        ("engine_type", c_int32),
        ("car_width", c_float),
        ("car_length", c_float),
        ("rating", c_float),
        ("reputation", c_float),
        ("unused1", c_float),
        ("unused2", c_float),
    ]


class R3EDriverData(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("driver_info", R3EDriverInfo),
        ("finish_status", c_int32),
        ("place", c_int32),
        ("place_class", c_int32),
        ("lap_distance", c_float),
        ("lap_distance_fraction", c_float),
        ("position", R3EVec3F32),
        ("track_sector", c_int32),
        ("completed_laps", c_int32),
        ("current_lap_valid", c_int32),
        ("lap_time_current_self", c_float),
        ("sector_time_current_self", c_float * 3),
        ("sector_time_previous_self", c_float * 3),
        ("sector_time_best_self", c_float * 3),
        ("time_delta_front", c_float),
        ("time_delta_behind", c_float),
        ("pitstop_status", c_int32),
        ("in_pitlane", c_int32),
        ("num_pitstops", c_int32),
        ("penalties", R3ECutTrackPenalties),
        ("car_speed", c_float),
        ("tire_type_front", c_int32),
        ("tire_type_rear", c_int32),
        ("tire_subtype_front", c_int32),
        ("tire_subtype_rear", c_int32),
        ("base_penalty_weight", c_float),
        ("aid_penalty_weight", c_float),
        ("drs_state", c_int32),
        ("ptp_state", c_int32),
        ("virtual_energy", c_float),
        ("penaltyType", c_int32),
        ("penaltyReason", c_int32),
        ("engineState", c_int32),
        ("orientation", R3EVec3F32),
        ("unused1", c_float),
        ("unused2", c_float),
        ("unused3", c_float),
    ]


class R3EShared(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("version_major", c_int32),
        ("version_minor", c_int32),
        ("all_drivers_offset", c_int32),
        ("driver_data_size", c_int32),
        ("game_mode", c_int32),
        ("game_paused", c_int32),
        ("game_in_menus", c_int32),
        ("game_in_replay", c_int32),
        ("game_using_vr", c_int32),
        ("game_player_in_garage", c_int32),
        ("player", R3EPlayerdata),
        ("track_name", c_ubyte * 64),
        ("layout_name", c_ubyte * 64),
        ("track_id", c_int32),
        ("layout_id", c_int32),
        ("layout_length", c_float),
        ("sector_start_factors", R3ESectorstarts),
        ("race_session_laps", c_int32 * 3),
        ("race_session_minutes", c_int32 * 3),
        ("event_index", c_int32),
        ("session_type", c_int32),
        ("session_iteration", c_int32),
        ("session_length_format", c_int32),
        ("session_pit_speed_limit", c_float),
        ("session_phase", c_int32),
        ("start_lights", c_int32),
        ("tire_wear_active", c_int32),
        ("fuel_use_active", c_int32),
        ("number_of_laps", c_int32),
        ("session_time_duration", c_float),
        ("session_time_remaining", c_float),
        ("max_incident_points", c_int32),
        ("event_unused1", c_float),
        ("event_unused2", c_float),
        ("pit_window_status", c_int32),
        ("pit_window_start", c_int32),
        ("pit_window_end", c_int32),
        ("in_pitlane", c_int32),
        ("pit_menu_selection", c_int32),
        ("pit_menu_state", c_int32 * 12),
        ("pit_state", c_int32),
        ("pit_total_duration", c_float),
        ("pit_elapsed_time", c_float),
        ("pit_action", c_int32),
        ("num_pitstops", c_int32),
        ("pit_min_duration_total", c_float),
        ("pit_min_duration_left", c_float),
        ("flags", R3EFlags),
        ("position", c_int32),
        ("position_class", c_int32),
        ("finish_status", c_int32),
        ("cut_track_warnings", c_int32),
        ("penalties", R3ECutTrackPenalties),
        ("num_penalties", c_int32),
        ("completed_laps", c_int32),
        ("current_lap_valid", c_int32),
        ("track_sector", c_int32),
        ("lap_distance", c_float),
        ("lap_distance_fraction", c_float),
        ("lap_time_best_leader", c_float),
        ("lap_time_best_leader_class", c_float),
        ("session_best_lap_sector_times", c_float * 3),
        ("lap_time_best_self", c_float),
        ("sector_time_best_self", c_float * 3),
        ("lap_time_previous_self", c_float),
        ("sector_time_previous_self", c_float * 3),
        ("lap_time_current_self", c_float),
        ("sector_time_current_self", c_float * 3),
        ("lap_time_delta_leader", c_float),
        ("lap_time_delta_leader_class", c_float),
        ("time_delta_front", c_float),
        ("time_delta_behind", c_float),
        ("time_delta_best_self", c_float),
        ("best_individual_sector_time_self", c_float * 3),
        ("best_individual_sector_time_leader", c_float * 3),
        ("best_individual_sector_time_leader_class", c_float * 3),
        ("incident_points", c_int32),
        ("lap_valid_state", c_int32),
        ("prev_lap_valid", c_int32),
        ("discharge_rate", c_float),
        ("brake_regen", c_float),
        ("unused1", c_float),
        ("vehicle_info", R3EDriverInfo),
        ("player_name", c_ubyte * 64),
        ("control_type", c_int32),
        ("car_speed", c_float),
        ("engine_rps", c_float),
        ("max_engine_rps", c_float),
        ("upshift_rps", c_float),
        ("gear", c_int32),
        ("num_gears", c_int32),
        ("car_cg_location", R3EVec3F32),
        ("car_orientation", R3EOriF32),
        ("local_acceleration", R3EVec3F32),
        ("total_mass", c_float),
        ("fuel_left", c_float),
        ("fuel_capacity", c_float),
        ("fuel_per_lap", c_float),
        ("virtual_energy_left", c_float),
        ("virtual_energy_capacity", c_float),
        ("virtual_energy_per_lap", c_float),
        ("engine_temp", c_float),
        ("engine_oil_temp", c_float),
        ("fuel_pressure", c_float),
        ("engine_oil_pressure", c_float),
        ("turbo_pressure", c_float),
        ("throttle", c_float),
        ("throttle_raw", c_float),
        ("brake", c_float),
        ("brake_raw", c_float),
        ("clutch", c_float),
        ("clutch_raw", c_float),
        ("steer_input_raw", c_float),
        ("steer_lock_degrees", c_int32),
        ("steer_wheel_range_degrees", c_int32),
        ("aid_settings", R3EAidSettings),
        ("drs", R3EDrs),
        ("pit_limiter", c_int32),
        ("push_to_pass", R3EPushToPass),
        ("brake_bias", c_float),
        ("drs_numActivationsTotal", c_int32),
        ("ptp_numActivationsTotal", c_int32),
        ("battery_soc", c_float),
        ("water_left", c_float),
        ("abs_setting", c_int32),
        ("headlights", c_int32),
        ("steer_wheel_max_rotation", c_int32),
        ("tire_type", c_int32),
        ("tire_rps", c_float * 4),
        ("tire_speed", c_float * 4),
        ("tire_grip", c_float * 4),
        ("tire_wear", c_float * 4),
        ("tire_flatspot", c_int32 * 4),
        ("tire_pressure", c_float * 4),
        ("tire_dirt", c_float * 4),
        ("tire_temp", R3ETireTemp * 4),
        ("tire_type_front", c_int32),
        ("tire_type_rear", c_int32),
        ("tire_subtype_front", c_int32),
        ("tire_subtype_rear", c_int32),
        ("brake_temp", R3EBrakeTemp * 4),
        ("brake_pressure", c_float * 4),
        ("traction_control_setting", c_int32),
        ("engine_map_setting", c_int32),
        ("engine_brake_setting", c_int32),
        ("traction_control_percent", c_float),
        ("tire_on_mtrl", c_int32 * 4),
        ("tire_load", c_float * 4),
        ("car_damage", R3ECarDamage),
        ("num_cars", c_int32),
        ("all_drivers_data_1", R3EDriverData * 128),
    ]



# --------------------------------------------------------------------------- --
# Hilfsfunktionen
# --------------------------------------------------------------------------- --


def _txt(arr) -> str:
    """Nullterminierten UTF-8-Puffer (ctypes-Array) in str wandeln."""
    try:
        return bytes(arr).split(b"\x00", 1)[0].decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _f(v, default: float = 0.0) -> float:
    try:
        x = float(v)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def _pos(v, default: float = 0.0) -> float:
    """R3E meldet 'nicht verfuegbar' als -1.0 -> auf default abbilden."""
    x = _f(v, default)
    return x if x >= 0.0 else default


# R3E-Session-Typ: 0 Practice, 1 Quali, 2 Rennen, 3 Warmup
_SESSION_TYPE_NAMES = {0: "Practice", 1: "Qualify", 2: "Race", 3: "Warmup"}


class LiveSample:
    """Schlanke Momentaufnahme der fuer die Aufzeichnung relevanten Werte.

    0.6.0: zusaetzlich Position/Streckenmeter/Geschwindigkeit fuer die
    Streckenkarte sowie Laufzeit-/Sektor-/Delta-Werte fuer den Live-Tab.
    Sektorzeiten liegen als 3er-Liste vor (Sekunden; None = nicht gesetzt).
    """

    __slots__ = ("version", "in_menus", "in_replay", "in_car",
                 "session_type", "track_name", "layout_name", "track_id",
                 "layout_id", "player_name", "model_id", "completed_laps",
                 "lap_time_previous_s", "prev_lap_valid",
                 "fuel_left", "fuel_capacity", "fuel_per_lap",
                 "lap_time_current_s", "lap_time_best_s", "delta_best_s",
                 "sector_current", "sector_previous", "sector_best",
                 "sector_starts", "track_sector",
                 "pos_x", "pos_z", "lap_dist_m", "lap_dist_fr", "speed")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


class _MemoryBasicInformation(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", ctypes.c_uint32), ("PartitionId", ctypes.c_uint16),
                ("RegionSize", ctypes.c_size_t), ("State", ctypes.c_uint32),
                ("Protect", ctypes.c_uint32), ("Type", ctypes.c_uint32)]


class R3EReader:
    """Liest ``$R3E`` und liefert ``read()`` -> LiveSample (oder None).

    raw_provider : nur Tests/Mock — liefert die Rohbytes des Blocks.
    """

    def __init__(self, raw_provider=None, k32=None):
        self._raw_provider = raw_provider
        self._k32 = k32
        self.size = ctypes.sizeof(R3EShared)
        self._head_size = R3EShared.num_cars.offset
        self._view_size = 0
        self.last_version = (0, 0)
        self.layout_warning = ""

    # ----- Rohzugriff -------------------------------------------------------
    def _read_raw(self) -> bytes:
        if self._raw_provider is not None:
            raw = bytes(self._raw_provider())
        elif sys.platform == "win32" or self._k32 is not None:
            raw = self._read_open_only()
        else:
            raise RuntimeError("RaceRoom Shared Memory ist nur unter Windows lesbar.")
        if len(raw) < self.size:
            raw = raw + bytes(self.size - len(raw))
        return raw

    def _read_open_only(self) -> bytes:
        """Windows: das Mapping des Spiels NUR OEFFNEN (OpenFileMapping,
        nur lesen) — nie selbst anlegen (ein zu kleines eigenes Mapping
        unter $R3E koennte das Spiel stoeren)."""
        k32 = self._k32 if self._k32 is not None else self._load_k32()
        FILE_MAP_READ = 0x0004
        h = k32.OpenFileMappingW(FILE_MAP_READ, False, R3E_SHARED_MEMORY_NAME)
        if not h:
            raise RuntimeError("RaceRoom Shared Memory ($R3E) nicht gefunden - laeuft RaceRoom?")
        view = None
        try:
            view = k32.MapViewOfFile(h, FILE_MAP_READ, 0, 0, 0)
            if not view:
                raise RuntimeError("RaceRoom Shared Memory ($R3E) konnte nicht eingeblendet werden.")
            mbi = _MemoryBasicInformation()
            size = self.size
            if k32.VirtualQuery(view, ctypes.byref(mbi), ctypes.sizeof(mbi)):
                size = min(self.size, int(mbi.RegionSize))
            return ctypes.string_at(view, size)
        finally:
            if view:
                k32.UnmapViewOfFile(view)
            k32.CloseHandle(h)

    @staticmethod
    def _load_k32():
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        vp, dw = ctypes.c_void_p, ctypes.c_uint32
        k32.OpenFileMappingW.argtypes = [dw, ctypes.c_int, ctypes.c_wchar_p]
        k32.OpenFileMappingW.restype = vp
        k32.MapViewOfFile.argtypes = [vp, dw, dw, dw, ctypes.c_size_t]
        k32.MapViewOfFile.restype = vp
        k32.UnmapViewOfFile.argtypes = [vp]
        k32.UnmapViewOfFile.restype = ctypes.c_int
        k32.CloseHandle.argtypes = [vp]
        k32.CloseHandle.restype = ctypes.c_int
        k32.VirtualQuery.argtypes = [vp, vp, ctypes.c_size_t]
        k32.VirtualQuery.restype = ctypes.c_size_t
        return k32

    # ----- Auswertung -------------------------------------------------------
    @staticmethod
    def _secs3(arr):
        """3 Sektorzeiten (Sekunden) aus dem Shared Memory; -1 -> None."""
        return [(_pos(v) if _pos(v) > 0 else None) for v in arr]

    def read(self):
        """LiveSample liefern; None, wenn kein Rennen laeuft (Menus/Replay)."""
        d = R3EShared.from_buffer_copy(self._read_raw())
        maj, minor = int(d.version_major), int(d.version_minor)
        self.last_version = (maj, minor)
        if maj == 0:
            raise RuntimeError("RaceRoom Shared Memory nicht aktiv (Spiel laeuft nicht oder schreibt noch nicht).")
        if maj != R3E_VERSION_MAJOR:
            raise RuntimeError(f"RaceRoom-API {maj}.{minor} wird nicht unterstuetzt (bekannt: {R3E_VERSION_MAJOR}.x).")
        self.layout_warning = ""
        if minor > R3E_VERSION_MINOR_KNOWN:
            self.layout_warning = (f"API 3.{minor} neuer als bekannt (3.{R3E_VERSION_MINOR_KNOWN}); neue Felder werden ignoriert")
        if int(d.driver_data_size) and int(d.driver_data_size) != ctypes.sizeof(R3EDriverData):
            self.layout_warning = (self.layout_warning + "; " if self.layout_warning else "") + \
                f"Fahrerblock {int(d.driver_data_size)} statt {ctypes.sizeof(R3EDriverData)} Byte"
        if int(d.game_in_menus) == 1 or int(d.game_in_replay) == 1:
            return None
        state = int(d.lap_valid_state)
        prev_valid = 1
        if state >= 0:
            prev_valid = 0 if state in (1, 2) else 1
        elif int(d.prev_lap_valid) >= 0:
            prev_valid = int(d.prev_lap_valid)
        return LiveSample(
            version=(maj, minor),
            in_menus=int(d.game_in_menus),
            in_replay=int(d.game_in_replay),
            in_car=int(d.control_type) == 0,
            session_type=_SESSION_TYPE_NAMES.get(int(d.session_type), "Practice"),
            track_name=_txt(d.track_name),
            layout_name=_txt(d.layout_name),
            track_id=int(d.track_id),
            layout_id=int(d.layout_id),
            player_name=_txt(d.player_name),
            model_id=int(d.vehicle_info.model_id),
            completed_laps=int(d.completed_laps),
            lap_time_previous_s=_pos(d.lap_time_previous_self),
            prev_lap_valid=prev_valid,
            fuel_left=_pos(d.fuel_left),
            fuel_capacity=_pos(d.fuel_capacity),
            fuel_per_lap=_pos(d.fuel_per_lap),
            # 0.6.0: Werte fuer den Live-Tab (Karte, Kacheln, Sektoren)
            lap_time_current_s=_pos(d.lap_time_current_self),
            lap_time_best_s=(_pos(d.lap_time_best_self)
                             if _pos(d.lap_time_best_self) > 0 else None),
            delta_best_s=(_f(d.time_delta_best_self)
                          if _f(d.time_delta_best_self) != 0.0 else None),
            sector_current=self._secs3(d.sector_time_current_self),
            sector_previous=self._secs3(d.sector_time_previous_self),
            sector_best=self._secs3(d.sector_time_best_self),
            sector_starts=[_f(d.sector_start_factors.sector1),
                           _f(d.sector_start_factors.sector2),
                           _f(d.sector_start_factors.sector3)],
            track_sector=int(d.track_sector),
            pos_x=_f(d.player.position.x),
            pos_z=_f(d.player.position.z),
            lap_dist_m=_pos(d.lap_distance),
            lap_dist_fr=_pos(d.lap_distance_fraction),
            speed=_pos(d.car_speed),
        )


# --------------------------------------------------------------------------- --
# Selbsttest: synthetischer Speicherblock (ohne laufendes Spiel)
# --------------------------------------------------------------------------- --
def _selftest():
    d = R3EShared()
    d.version_major, d.version_minor = R3E_VERSION_MAJOR, 5
    d.driver_data_size = ctypes.sizeof(R3EDriverData)
    d.all_drivers_offset = R3EShared.num_cars.offset
    d.game_in_menus = d.game_in_replay = 0
    d.control_type = 0
    d.session_type = 0
    d.track_name = (c_ubyte * 64)(*b"Nuerburgring")
    d.layout_name = (c_ubyte * 64)(*b"Grand Prix")
    d.track_id, d.layout_id = 1690, 1691
    d.player_name = (c_ubyte * 64)(*b"Marcel Wijnandts")
    d.completed_laps = 3
    d.lap_valid_state = 1          # vorherige Runde war ungueltig
    d.lap_time_previous_self = 65.432
    d.fuel_left, d.fuel_capacity, d.fuel_per_lap = 38.2, 60.0, 3.1

    r = R3EReader(raw_provider=lambda: bytes(d))
    s = r.read()
    checks = [
        ("Version", r.last_version == (3, 5)),
        ("Strecke", s.track_name == "Nuerburgring" and s.layout_name == "Grand Prix"),
        ("Ids", s.track_id == 1690 and s.layout_id == 1691),
        ("Fahrer", s.player_name == "Marcel Wijnandts"),
        ("Fahrzeug-Id", s.model_id == 0),
        ("Session-Typ", s.session_type == "Practice"),
        ("Runden", s.completed_laps == 3),
        ("Zeit", abs(s.lap_time_previous_s - 65.432) < 1e-6),
        ("Ungueltig", s.prev_lap_valid == 0),
        ("Kraftstoff", abs(s.fuel_left - 38.2) < 1e-6 and abs(s.fuel_capacity - 60.0) < 1e-6),
    ]
    ok = True
    for name, cond in checks:
        if not cond:
            ok = False
            print(f"  FEHLER: {name}")
    print("R3EReader-Selbsttest:", "OK" if ok else "FEHLER")
    # In-Menus-Fall
    d.game_in_menus = 1
    r2 = R3EReader(raw_provider=lambda: bytes(d))
    assert r2.read() is None
    print("Menu-Erkennung: OK")
    return ok


if __name__ == "__main__":
    sys.exit(0 if _selftest() else 1)
