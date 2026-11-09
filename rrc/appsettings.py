"""App-Einstellungen (Qt-frei und damit unit-testbar), Version 0.4.2.

Zweck: die Option "KI-Fahrer ausblenden" mit der Liste echter
(menschlicher) Fahrer dauerhaft zu speichern. Ablage als JSON im
App-Ordner (Dokumente\\RaceRoom Results Companion\\settings.json),
atomar geschrieben wie fuel_history.json.
"""
import json
import os

SETTINGS_FILENAME = "settings.json"
DEFAULTS = {"real_drivers": [], "hide_ai": False, "r3e_install_dir": ""}


def settings_path(app_dir):
    return os.path.join(app_dir, SETTINGS_FILENAME)


def load_settings(path):
    """Liest settings.json; fehlende Schluessel ergaenzt, korrupte Datei => Defaults."""
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                data = raw
        except (OSError, ValueError):
            data = {}
    s = dict(DEFAULTS)
    s.update({k: v for k, v in data.items() if k in DEFAULTS})
    if not isinstance(s["real_drivers"], list):
        s["real_drivers"] = [d.strip() for d in str(s["real_drivers"]).split(",")
                             if d.strip()]
    s["real_drivers"] = [str(d).strip() for d in s["real_drivers"] if str(d).strip()]
    s["hide_ai"] = bool(s["hide_ai"])
    s["r3e_install_dir"] = str(s["r3e_install_dir"] or "").strip()
    return s


def save_settings(path, settings):
    """Schreibt settings.json atomar (tmp + replace); Rueckgabe: gespeicherte Werte."""
    clean = {k: settings.get(k, DEFAULTS[k]) for k in DEFAULTS}
    clean["real_drivers"] = [str(d).strip() for d in clean["real_drivers"]
                             if str(d).strip()]
    clean["hide_ai"] = bool(clean["hide_ai"])
    clean["r3e_install_dir"] = str(clean["r3e_install_dir"] or "").strip()
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return clean
