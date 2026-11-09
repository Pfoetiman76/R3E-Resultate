"""Default paths for RaceRoom Results Companion (Windows first, portable fallback)."""
import os

APP_DIR_NAME = "RaceRoom Results Companion"


def _windows_documents():
    """Return the Windows Documents folder path or None."""
    try:
        import ctypes
        import ctypes.wintypes
        from ctypes import windll
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        # CSIDL_PERSONAL = 5
        if windll.shfolder.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
            return buf.value
    except Exception:
        pass
    return None


def default_results_dir():
    docs = _windows_documents() or os.path.expanduser("~")
    return os.path.join(docs, "My Games", "SimBin", "RaceRoom Racing Experience",
                        "UserData", "Log", "Results")


def default_app_dir():
    base = os.path.join(_windows_documents() or os.path.expanduser("~"), APP_DIR_NAME)
    os.makedirs(base, exist_ok=True)
    return base


def default_db_path():
    return os.path.join(default_app_dir(), "results.db")
