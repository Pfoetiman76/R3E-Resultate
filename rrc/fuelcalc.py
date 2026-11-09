"""Kraftstoffprognose - Qt-frei und damit unit-testbar.

Vorbild ist der Spritrechner aus PitBoss R3E:
- Runden <-> Minuten werden live ineinander umgerechnet (eines ist Quelle)
- Bedarf = Runden x Verbrauch pro Runde
- Tank-Check: passt die Menge in den Tank?

Da RaceRoom-Ergebnisdateien keinen Verbrauch enthalten, pflegt der Nutzer
Verbrauch pro Runde und Tankgroesse je Strecke/Fahrzeug selbst; die Werte
werden in fuel_history.json persistiert (wie in PitBoss).
"""
import json
import os

HISTORY_FILENAME = "fuel_history.json"


def history_path(app_dir):
    return os.path.join(app_dir, HISTORY_FILENAME)


def load_history(path):
    """Liest fuel_history.json; Rueckgabe: {"track|vehicle": {...}}."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_history(path, data):
    """Schreibt fuel_history.json atomar (erst temp, dann rename)."""
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def entry_key(track, vehicle):
    """Schluessel fuer fuel_history: "track|vehicle" (wie PitBoss)."""
    return f"{track}|{vehicle}"


def get_entry(history, track, vehicle):
    """Eintrag fuer Strecke/Fahrzeug oder leeres Dict."""
    return history.get(entry_key(track, vehicle), {})


def put_entry(history, track, vehicle, fuel_per_lap, capacity):
    """Speichert Verbrauch und Tankgroesse; None-Werte werden ignoriert."""
    e = history.get(entry_key(track, vehicle), {})
    if fuel_per_lap is not None:
        e["fuel_l"] = float(fuel_per_lap)
    if capacity is not None:
        e["capacity"] = float(capacity)
    history[entry_key(track, vehicle)] = e
    return history


def laps_from_minutes(minutes, lap_s):
    """Rundenzahl fuer eine Renndauer in Minuten bei gegebener Rundenzeit."""
    if not lap_s or lap_s <= 0 or minutes is None:
        return 0.0
    return (minutes * 60.0) / lap_s


def minutes_from_laps(laps, lap_s):
    """Renndauer in Minuten fuer eine Rundenzahl."""
    if not lap_s or lap_s <= 0 or laps is None:
        return 0.0
    return (laps * lap_s) / 60.0


def fuel_needed(laps, fuel_per_lap):
    """Kraftstoffbedarf in Litern (0 bei ungueltigen Eingaben)."""
    if laps is None or fuel_per_lap is None or fuel_per_lap <= 0:
        return 0.0
    return laps * float(fuel_per_lap)


def fits_tank(fuel, capacity):
    """True, wenn die Menge in den Tank passt (Tank unendlich, wenn None/<=0)."""
    if not capacity or capacity <= 0:
        return True
    return fuel <= capacity + 1e-9
