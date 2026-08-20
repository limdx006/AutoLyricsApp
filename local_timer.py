import time
import threading


class LocalTimer:
    """A simple local timer that tracks elapsed time from a start point."""

    def __init__(self):
        self._start_time = 0.0
        self._start_timestamp = 0.0
        self._running = False
        self._lock = threading.Lock()

    def start(self, initial_position=0.0):
        """Start the local timer from the given position (seconds)."""
        with self._lock:
            self._start_position = initial_position
            self._start_timestamp = time.monotonic()
            self._running = True

    def stop(self):
        """Stop the local timer."""
        with self._lock:
            self._running = False

    def get_position(self):
        """Return the current estimated position in seconds."""
        with self._lock:
            if not self._running:
                return self._start_position
            elapsed = time.monotonic() - self._start_timestamp
            return self._start_position + elapsed

    def is_running(self):
        return self._running

    def sync(self, new_position):
        """Sync the local timer to a new reference position."""
        with self._lock:
            self._start_position = new_position
            self._start_timestamp = time.monotonic()