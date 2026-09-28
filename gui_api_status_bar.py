"""
Thin status strip pinned to the very bottom of the window, showing the
live connectivity state of the personal LimdxLyricsAPI. Reflects
api_status.py's background health-check state:

    Online        green dot
    Starting up   orange dot   (cold-starting after being asleep)
    Offline       red dot

Hovering the strip shows a short tooltip explaining the current state.
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

# Short explanation per state, shown in the hover tooltip.
_STATUS_DESCRIPTION = {
    api_status.STATUS_ONLINE: "- Online\n- Lyrics are fetched from it first",
    api_status.STATUS_STARTING: (
        "- Starting up\n"
        "- Free server is waking from sleep (up to ~1 min)\n"
        "- syncedlyrics is used meanwhile"
    ),
    api_status.STATUS_OFFLINE: "- Offline\n- Server unreachable\n- syncedlyrics is used as fallback",
}

# Visual diameter of the dot.
_DOT_SIZE = 5
_DOT_MARGIN = 2
_CANVAS_SIZE = _DOT_SIZE + _DOT_MARGIN * 2


class ApiStatusBar(tk.Frame):
    """Very bottom strip: a small coloured dot + 'LimdxAPI: <state>' label."""

    _HEIGHT = 22

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_COLOR, **kwargs)
        self.configure(height=self._HEIGHT)
        self.pack_propagate(False)  # keep the fixed strip height regardless of contents
        self.pack_configure(padx=10, pady=(0, 4))

        self._current_status = api_status.STATUS_STARTING
        self._tooltip = None
        self._tooltip_label = None
        self._tooltip_after = None

        # Centered row: dot + label
        inner = tk.Frame(self, bg=BG_COLOR)
        inner.pack(expand=True)
        self._inner = inner

        self.dot_canvas = tk.Canvas(
            inner, width=_CANVAS_SIZE, height=_CANVAS_SIZE,
            bg=BG_COLOR, highlightthickness=0, borderwidth=0,
        )
        self.dot_canvas.pack(side=tk.LEFT, padx=(0, 5))
        self._dot_id = self.dot_canvas.create_oval(
            _DOT_MARGIN, _DOT_MARGIN, _DOT_MARGIN + _DOT_SIZE, _DOT_MARGIN + _DOT_SIZE,
            fill=_STATUS_COLOR[api_status.STATUS_STARTING], outline="",
        )

        self.text_label = tk.Label(
            inner,
            text="LimdxAPI: Starting up",
            font=(FONT_FAMILY, 8),
            bg=BG_COLOR,
            fg=COLOR_STATUS_FG,
        )
        self.text_label.pack(side=tk.LEFT)

        # Hover tooltip: bound on every part of the strip so the whole
        # thing is a hover target, not just the text.
        for widget in (self, inner, self.dot_canvas, self.text_label):
            widget.bind("<Enter>", self._schedule_tooltip)
            widget.bind("<Leave>", self._on_leave)

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
        self._current_status = status
        color = _STATUS_COLOR.get(status, _STATUS_COLOR[api_status.STATUS_STARTING])
        text = _STATUS_TEXT.get(status, "Unknown")
        self.dot_canvas.itemconfig(self._dot_id, fill=color)
        self.text_label.config(text=f"LimdxAPI: {text}")
        # Keep an already-open tooltip in sync if the status changes while hovering
        if self._tooltip_label is not None:
            self._tooltip_label.config(text=self._tooltip_text())

    def _tooltip_text(self):
        description = _STATUS_DESCRIPTION.get(self._current_status, "")
        return f"LimdxAPI status\n{description}"

    def _schedule_tooltip(self, _event=None):
        """Show the tooltip after the pointer rests on the strip."""
        self._hide_tooltip()
        self._tooltip_after = self.after(350, self._show_tooltip)

    def _show_tooltip(self):
        self._tooltip_after = None
        if self._tooltip is not None:
            return

        tooltip = tk.Toplevel(self)
        tooltip.wm_overrideredirect(True)
        tooltip.attributes("-topmost", True)
        tooltip.configure(bg=COLOR_ACTIVE_FG)
        self._tooltip_label = tk.Label(
            tooltip,
            text=self._tooltip_text(),
            justify=tk.LEFT,
            anchor="w",
            padx=7,
            pady=5,
            font=(FONT_FAMILY, 8),
            bg=COLOR_ACTIVE_FG,
            fg=ACCENT_COLOR,
            relief=tk.SOLID,
            borderwidth=1,
        )
        self._tooltip_label.pack()

        # This strip sits at the very bottom of the window
        tooltip.update_idletasks()
        tip_w, tip_h = tooltip.winfo_reqwidth(), tooltip.winfo_reqheight()
        x = self._inner.winfo_rootx() + (self._inner.winfo_width() - tip_w) // 2
        y = self.winfo_rooty() - tip_h - 4
        x = max(0, min(x, self.winfo_screenwidth() - tip_w))
        y = max(0, y)
        tooltip.geometry(f"+{x}+{y}")
        self._tooltip = tooltip

    def _on_leave(self, event):
        """Hide the tooltip - but only if the pointer actually left the whole
        strip, not just moved from one child (dot/label) to another."""
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            widget = None
        while widget is not None:
            if widget is self:
                return
            widget = getattr(widget, "master", None)
        self._hide_tooltip()

    def _hide_tooltip(self):
        """Cancel a pending tooltip or close an open one."""
        if self._tooltip_after is not None:
            self.after_cancel(self._tooltip_after)
            self._tooltip_after = None
        if self._tooltip is not None:
            self._tooltip.destroy()
            self._tooltip = None
            self._tooltip_label = None

    def _on_destroy(self, _event=None):
        api_status.unsubscribe(self._on_status_changed)
        self._hide_tooltip()