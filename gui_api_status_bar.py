"""
Thin status strip pinned to the very bottom of the window, showing the
live connectivity state of the personal LimdxLyricsAPI. Reflects
api_status.py's background health-check state:

    Online        green dot
    Starting up   orange dot   (cold-starting after being asleep)
    Offline       red dot
"""

import tkinter as tk
from config import *
import api_status

_STATUS_TEXT = {
    api_status.STATUS_ONLINE: "Online",
    api_status.STATUS_STARTING: "Starting up",
    api_status.STATUS_OFFLINE: "Offline",
}

_STATUS_COLOR = {
    api_status.STATUS_ONLINE: GOOD_COLOR,  # green
    api_status.STATUS_STARTING: LOADING_COLOR,  # orange
    api_status.STATUS_OFFLINE: ERROR_COLOR,  # red
}

_DOT_SIZE = 4


class ApiStatusBar(tk.Frame):
    """Very bottom strip: a small coloured dot + 'LimdxAPI: <state>' label."""

    _HEIGHT = 22

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_COLOR, **kwargs)
        self.configure(height=self._HEIGHT)
        self.pack_propagate(False)  # keep the fixed strip height regardless of contents
        self.pack_configure(padx=10, pady=(0, 4))

        # Centered row: dot + label
        inner = tk.Frame(self, bg=BG_COLOR)
        inner.pack(expand=True)

        self.dot_canvas = tk.Canvas(
            inner,
            width=_DOT_SIZE,
            height=_DOT_SIZE,
            bg=BG_COLOR,
            highlightthickness=0,
        )
        self.dot_canvas.pack(side=tk.LEFT, padx=(0, 5))
        self._dot_id = self.dot_canvas.create_oval(
            0,
            0,
            _DOT_SIZE,
            _DOT_SIZE,
            fill=_STATUS_COLOR[api_status.STATUS_STARTING],
            outline="",
        )

        self.text_label = tk.Label(
            inner,
            text="LimdxAPI: Starting up",
            font=(FONT_FAMILY, 8),
            bg=BG_COLOR,
            fg=COLOR_STATUS_FG,
        )
        self.text_label.pack(side=tk.LEFT)

        # Subscribe to the background checker. Its callback can fire from
        # the checker thread, so the actual widget update is marshalled
        # onto the Tk main thread via after(0, ...).
        api_status.subscribe(self._on_status_changed)
        self.bind("<Destroy>", self._on_destroy)

    def _on_status_changed(self, status):
        self.after(0, lambda: self._apply_status(status))

    def _apply_status(self, status):
        if not self.winfo_exists():
            return
        color = _STATUS_COLOR.get(status, _STATUS_COLOR[api_status.STATUS_STARTING])
        text = _STATUS_TEXT.get(status, "Unknown")
        self.dot_canvas.itemconfig(self._dot_id, fill=color)
        self.text_label.config(text=f"LimdxAPI: {text}")

    def _on_destroy(self, _event=None):
        api_status.unsubscribe(self._on_status_changed)
