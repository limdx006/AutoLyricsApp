"""
Small persisted-preferences store: window size / font size / default
offset presets, remembered across runs.

They're kept in a small JSON file under %APPDATA%, which is the standard writable,
per-user location on Windows and survives both re-launching the exe and replacing it with a new build.

Nothing here ever raises - a missing, corrupt, or unwritable settings file just means preferences fall back to defaults 
(handled by the caller), the same as a first-ever launch.
"""

import json
import os

_APP_DIR_NAME = "AutoLyricsPlayer"
_SETTINGS_FILENAME = "settings.json"


def _settings_dir():
    appdata = os.environ.get("APPDATA")
    if appdata:
        return os.path.join(appdata, _APP_DIR_NAME)
    # No APPDATA (non-Windows, e.g. running from source during dev on
    # another OS) - fall back to a dotfolder in the home directory.
    return os.path.join(os.path.expanduser("~"), f".{_APP_DIR_NAME.lower()}")


def _settings_path():
    return os.path.join(_settings_dir(), _SETTINGS_FILENAME)


def load():
    """Return the saved preferences dict, or {} if none are saved yet, or
    the file is missing/unreadable/corrupt."""
    path = _settings_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        print(f"[Prefs] Failed to load settings from '{path}': {e}")
        return {}


def save(partial_prefs):
    """Merge `partial_prefs` over whatever's already saved (so setting one
    preference never clobbers the others) and write it back to disk."""
    path = _settings_path()
    try:
        os.makedirs(_settings_dir(), exist_ok=True)
        existing = load()
        existing.update(partial_prefs)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        print(f"[Prefs] Failed to save settings to '{path}': {e}")