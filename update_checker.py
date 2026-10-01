"""
Checks GitHub for a newer release than the one currently running.

check_now() does the version comparison; downloading/installing an
update is a separate step (not implemented here yet). Results are
cached via user_prefs.py so relaunching the app soon after doesn't hit
the GitHub API again for no reason - see _MIN_RECHECK_INTERVAL.
"""

import threading
import time
import requests

from version import APP_VERSION, GITHUB_API_LATEST_RELEASE, RELEASE_ASSET_NAME
import user_prefs

_TIMEOUT = 10
_MIN_RECHECK_INTERVAL = 6 * 60 * 60  # seconds - don't hit GitHub more than once per 6h

_lock = threading.Lock()
_subscribers = []
_result = None  # dict, or None if no check has completed yet this run


def _parse_version(text):
    """'v4.0.1' or '4.0.1' -> (4, 0, 1). Returns None if unparseable
    (e.g. a non-numeric pre-release tag)."""
    if not text:
        return None
    text = text.strip()
    if text[:1].lower() == "v":
        text = text[1:]
    try:
        return tuple(int(p) for p in text.split("."))
    except ValueError:
        return None


def _is_newer(latest, current):
    """Compare two version tuples left-to-right, padding the shorter one
    with zeros so (4, 1) vs (4, 1, 0) counts as equal, not newer."""
    if latest is None or current is None:
        return False
    length = max(len(latest), len(current))
    latest = latest + (0,) * (length - len(latest))
    current = current + (0,) * (length - len(current))
    return latest > current


def get_result():
    """Return the last known check result (see _run_check for the dict
    shape), or None if no check has completed yet this run."""
    with _lock:
        return _result


def subscribe(callback):
    """Register callback(result) for update-check results. Fires once
    immediately with the current result (possibly None)."""
    _subscribers.append(callback)
    callback(get_result())


def unsubscribe(callback):
    if callback in _subscribers:
        _subscribers.remove(callback)


def _set_result(result):
    global _result
    with _lock:
        _result = result
    for callback in list(_subscribers):
        try:
            callback(result)
        except Exception as e:
            print(f"[Update] Subscriber callback failed: {e}")


def _fetch_latest_release():
    """Hit the GitHub API for the latest release. Returns (tag_name,
    download_url) - either may be None on a missing asset, no releases
    published yet, or any request failure. Never raises."""
    try:
        response = requests.get(
            GITHUB_API_LATEST_RELEASE,
            timeout=_TIMEOUT,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "AutoLyricsApp-UpdateChecker",
            },
        )
        if response.status_code == 404:
            print("[Update] No GitHub releases published yet")
            return None, None
        if response.status_code == 403:
            print("[Update] GitHub API rate limit hit - will retry on the next check")
            return None, None
        response.raise_for_status()
        data = response.json()
        tag_name = data.get("tag_name")
        download_url = next(
            (a.get("browser_download_url") for a in data.get("assets", [])
             if a.get("name") == RELEASE_ASSET_NAME),
            None,
        )
        return tag_name, download_url
    except requests.RequestException as e:
        print(f"[Update] Failed to check GitHub for updates: {e}")
        return None, None
    except ValueError as e:  # malformed JSON
        print(f"[Update] Unexpected response from GitHub: {e}")
        return None, None


def _run_check():
    tag_name, download_url = _fetch_latest_release()
    latest = _parse_version(tag_name)
    current = _parse_version(APP_VERSION)

    result = {
        "current_version": APP_VERSION,
        "latest_version": tag_name.lstrip("vV") if tag_name else None,
        "download_url": download_url,
        "available": _is_newer(latest, current),
        "checked_at": time.time(),
    }
    user_prefs.save({"last_update_check": result})
    status = "update available" if result["available"] else "up to date"
    print(f"[Update] v{APP_VERSION} vs latest {tag_name or 'unknown'} - {status}")
    _set_result(result)


def check_now(force=False):
    """
    Check GitHub for a newer release, in the background.

    Any cached result is applied immediately (so subscribers get a
    last-known answer right away, even offline), then a fresh check is
    kicked off unless one already ran recently and force is False.
    """
    cached = user_prefs.load().get("last_update_check")
    if cached:
        _set_result(cached)
    if not force and cached and time.time() - cached.get("checked_at", 0) < _MIN_RECHECK_INTERVAL:
        return
    threading.Thread(target=_run_check, daemon=True).start()


if __name__ == "__main__":
    check_now(force=True)
    time.sleep(5)
    print(get_result())