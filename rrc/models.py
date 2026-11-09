"""RaceRoom Results Companion (RRC) - parsed result models."""
APP_NAME = "RaceRoom Results Companion"
APP_VERSION = "0.2.0"

from dataclasses import dataclass, field


@dataclass
class LapEntry:
    """A single recorded lap (server results only)."""
    lap_no: int = 0
    lap_time_ms: int = 0
    sector_times_ms: list = field(default_factory=list)


@dataclass
class PlayerResult:
    name: str = ""
    vehicle: str = ""
    team: str = ""
    position: int = 0
    laps: int = 0
    best_lap_ms: int = 0
    qual_ms: int = 0
    race_time_ms: int = 0
    finish_status: str = ""
    laps_detail: list = field(default_factory=list)  # list[LapEntry]

    @property
    def finished(self) -> bool:
        return not self.finish_status or self.finish_status.lower() == "finished"


@dataclass
class Session:
    session_type: str = ""          # Race, Race2, Qualify, Practice, ...
    timestamp: str = ""             # ISO-ish local time string
    track: str = ""
    layout: str = ""
    vehicle_class: str = ""          # best-effort (from car names in entries)
    source_file: str = ""
    digest: str = ""                # dedupe key across re-ingest
    players: list = field(default_factory=list)  # list[PlayerResult]

    @property
    def track_full(self) -> str:
        return f"{self.track} - {self.layout}" if self.layout else self.track


def format_time_ms(ms) -> str:
    """Format milliseconds as m:ss.mmm; empty string for falsy values."""
    try:
        ms = int(ms)
    except (TypeError, ValueError):
        return ""
    if ms <= 0:
        return ""
    m, rem = divmod(ms, 60000)
    s, msec = divmod(rem, 1000)
    return f"{m}:{s:02d}.{msec:03d}"
