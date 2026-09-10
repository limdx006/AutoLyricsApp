"""
Debug log capture and viewer.

install_log_capture() tees stdout/stderr so every existing print() call
across the app still prints to the console as usual, but is also pushed
into a bounded in-memory buffer (last MAX_LOG_LINES messages, oldest
dropped first). open_log_viewer() opens a resizable, scrollable window
showing that buffer, which keeps updating live as new lines come in -
including from background threads, since prints from the sync loops,
lyrics fetches, and auto-nudge all happen off the main thread.
"""

import sys
import re
import threading
import tkinter as tk
import ctypes
import os
from collections import deque
from config import *

MAX_LOG_LINES = 50
ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
APP_USER_MODEL_ID = "AutoLyricsApp.AutoLyricsPlayer"

# Known noisy library-internal messages to drop entirely (console + log
# buffer) - these come from syncedlyrics printing individual provider
# failures directly (e.g. Megalobiz connection timeouts) rather than
# through Python's logging module, so they can't be silenced via a
# verbosity setting. Add more patterns here if other libraries turn out
# to be similarly chatty.
_SUPPRESSED_PATTERNS = [
    re.compile(r"error occurred while searching for an LRC", re.IGNORECASE),
    re.compile(r"HTTPSConnectionPool", re.IGNORECASE),
    re.compile(r"ConnectTimeoutError", re.IGNORECASE),
    re.compile(r"Max retries exceeded with url", re.IGNORECASE),
]


def _is_suppressed(line):
    return any(p.search(line) for p in _SUPPRESSED_PATTERNS)


_log_buffer = deque(maxlen=MAX_LOG_LINES)
_log_lock = threading.Lock()
_subscribers = []  # callbacks notified with each new line, for live viewer windows
_active_window = None  # the single open LogViewerWindow, if any


class _TeeStream:
    """A stdout/stderr replacement that writes through to the original stream
    (when one exists) and also captures each line into the log buffer.
    """

    def __init__(self, original_stream):
        self._original = original_stream

    def write(self, text):
        # Drop known-noisy lines entirely, before they reach the console or
        # the log buffer - filtered per write() call, which keeps this
        # thread-safe (no shared redirection state across threads).
        lines = text.split("\n")
        kept_lines = [line for line in lines if not _is_suppressed(line)]
        filtered_text = "\n".join(kept_lines)

        if filtered_text and self._original is not None:
            try:
                self._original.write(filtered_text)
            except Exception:
                # No console attached (--windowed build) or a broken stub
                # stream - the log buffer/viewer is the only sink that
                # matters in that case, so just swallow this.
                pass

        for line in kept_lines:
            if line.strip():
                with _log_lock:
                    _log_buffer.append(line)
                for callback in list(_subscribers):
                    callback(line)

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    def isatty(self):
        try:
            return bool(self._original is not None and self._original.isatty())
        except Exception:
            return False

    def fileno(self):
        # Some libraries (progress bars, warnings machinery, etc.) probe
        # this. Without a console there genuinely is no fd, so raise the
        # same error a real headless stream would.
        if self._original is not None:
            try:
                return self._original.fileno()
            except Exception:
                pass
        raise OSError("No console attached (running as a --windowed build)")

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    @property
    def encoding(self):
        try:
            if self._original is not None:
                return self._original.encoding
        except Exception:
            pass
        return "utf-8"


def install_log_capture():
    """Redirect stdout/stderr through the tee. Call once, as early as possible at startup.

    Safe to call even when sys.stdout/sys.stderr are None, which is the
    normal case for a PyInstaller --windowed build with no console window -
    print() will simply stop reaching any OS-level console but will still
    be captured into the in-app log buffer/viewer.
    """
    sys.stdout = _TeeStream(sys.stdout)
    sys.stderr = _TeeStream(sys.stderr)


def configure_taskbar_identity():
    """Give Windows a stable identity so the taskbar uses this app's icon."""
    if os.name == "nt":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)


def get_log_lines():
    """Return a snapshot of the currently buffered lines, oldest first."""
    with _log_lock:
        return list(_log_buffer)


def apply_app_icon(window):
    """Apply the shared app icon; silently keeps the default if icon.ico isn't present yet."""
    try:
        window.iconbitmap(ICON_PATH)
    except Exception:
        pass


class LogViewerWindow(tk.Toplevel):
    """Resizable, scrollable window showing the last MAX_LOG_LINES captured log messages, updating live as new ones arrive."""

    _WIDTH = 550
    _HEIGHT = 320

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Log Viewer")
        self.minsize(400, 200)
        self.configure(bg=BG_COLOR)
        self._center_over(parent)
        apply_app_icon(self)
        # Groups this window with the main one (single taskbar entry, raised
        # together, closes together) so switching to either brings both forward.
        self.transient(parent)
        try:
            self.attributes("-topmost", parent.attributes("-topmost"))
        except tk.TclError:
            pass

        container = tk.Frame(self, bg=BG_COLOR)
        container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        scrollbar = tk.Scrollbar(container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text = tk.Text(
            container,
            wrap="word",
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
            insertbackground=COLOR_ACTIVE_FG,
            font=("Consolas", 9),
            yscrollcommand=scrollbar.set,
            state="disabled",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=4,
        )
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text.yview)

        for line in get_log_lines():
            self._append_line(line)

        _subscribers.append(self._on_new_line)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_over(self, parent):
        """Position this window centered over the main app window, instead of the screen's top-left default."""
        parent.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - self._WIDTH) // 2
        y = py + (ph - self._HEIGHT) // 2
        # Keep it fully on-screen even if that centering would push it off the edge
        x = max(0, min(x, self.winfo_screenwidth() - self._WIDTH))
        y = max(0, min(y, self.winfo_screenheight() - self._HEIGHT))
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}+{x}+{y}")

    def _append_line(self, line):
        self.text.configure(state="normal")
        self.text.insert(tk.END, line + "\n")
        # Mirror the buffer's cap in the widget itself, in case the window
        # was open before the buffer trimmed a given line.
        line_count = int(self.text.index("end-1c").split(".")[0])
        if line_count > MAX_LOG_LINES:
            self.text.delete("1.0", "2.0")
        self.text.see(tk.END)
        self.text.configure(state="disabled")

    def _on_new_line(self, line):
        # Tee.write() runs on whatever thread called print() - marshal the
        # actual widget update onto the main thread via after().
        self.after(0, lambda: self._append_line(line))

    def _on_close(self):
        if self._on_new_line in _subscribers:
            _subscribers.remove(self._on_new_line)
        self.destroy()


def open_log_viewer(parent):
    """Open the log viewer, or close it (same as clicking its own close
    button/cross) if it's already open - lets the 📝 button act as a toggle."""
    global _active_window
    if _active_window is not None and _active_window.winfo_exists():
        _active_window._on_close()
        return None
    _active_window = LogViewerWindow(parent)
    return _active_window


def set_pinned(is_pinned):
    """Sync the log window's always-on-top state with the main window's pin button."""
    if _active_window is not None and _active_window.winfo_exists():
        _active_window.attributes("-topmost", is_pinned)