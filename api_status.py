"""
Background health checker for the personal LimdxLyricsAPI.

The API is hosted on Render's free tier, which spins the service down
after some minutes of inactivity and takes anywhere from a couple of
seconds up to roughly a minute to spin back up on the next request. A
plain "online/offline" check would misreport a sleeping-but-fine service
as dead, so this runs on a background thread and distinguishes three
states:

  STATUS_ONLINE   - responded quickly, already awake.
  STATUS_STARTING - the quick probe failed/timed out, so a slower
                    "wake it up" request is in flight. Most likely just
                    spinning back up from sleep, not actually down.
  STATUS_OFFLINE  - even the long wake-up attempt failed - genuinely
                    unreachable, not just asleep.
"""

import threading
import time
import requests

from request_api import MY_LYRICS_API

STATUS_ONLINE = "online"
STATUS_STARTING = "starting"
STATUS_OFFLINE = "offline"

_QUICK_TIMEOUT = 5  # enough for an already-awake instance to answer
_WAKE_TIMEOUT = 100  # Render free-tier cold starts can take ~30-60s+
_POLL_INTERVAL = 25  # how often to re-check once a state has settled

_status = STATUS_STARTING
_lock = threading.Lock()
_subscribers = []
_started = False


def get_status():
    with _lock:
        return _status


def subscribe(callback):
    """Register callback(status) to be notified on every status change.
    Also fires it once immediately with the current status, so a newly
    created widget doesn't have to wait for the next poll to show
    something."""
    _subscribers.append(callback)
    callback(get_status())


def unsubscribe(callback):
    if callback in _subscribers:
        _subscribers.remove(callback)


def report_online():
    """Let other code (e.g. a real lyrics request that just succeeded)
    flip the indicator to Online right away instead of waiting for the
    next scheduled poll."""
    _set_status(STATUS_ONLINE)


def _set_status(new_status):
    global _status
    with _lock:
        if new_status == _status:
            return
        _status = new_status
    print(f"[APIStatus] LimdxAPI status -> {new_status}")
    for callback in list(_subscribers):
        try:
            callback(new_status)
        except Exception as e:
            print(f"[APIStatus] Subscriber callback failed: {e}")


def _ping(timeout):
    try:
        response = requests.get(f"{MY_LYRICS_API}/", timeout=timeout)
        return response.status_code < 500
    except requests.RequestException:
        return False


def _check_loop():
    while True:
        if _ping(_QUICK_TIMEOUT):
            _set_status(STATUS_ONLINE)
        else:
            # Could just be asleep rather than actually down
            _set_status(STATUS_STARTING)
            if _ping(_WAKE_TIMEOUT):
                _set_status(STATUS_ONLINE)
            else:
                _set_status(STATUS_OFFLINE)
        time.sleep(_POLL_INTERVAL)


def start():
    """Start the background checker thread. Safe to call more than once -
    only the first call actually starts it."""
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_check_loop, daemon=True).start()
