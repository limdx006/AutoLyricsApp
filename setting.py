"""
Preferences window opened from the ⚙ button: two mutually-exclusive
preset lists (window size, lyric font size). Clicking a row applies it
immediately and highlights it as selected - no separate Apply/OK step.

Sticks with the main window the same way the log viewer does: same icon,
transient (grouped/raised together), centered over it on open, and its
always-on-top state kept in sync with the main window's pin button.
"""

import tkinter as tk
from config import *
from log_viewer import apply_app_icon

_active_window = None  # the single open SettingsWindow, if any


class _PresetList(tk.Frame):
    """A vertical list of mutually-exclusive selectable rows (like a radio
    group): a bullet + label per row. Clicking a row selects it, unselects
    the rest, and calls on_select with that row's value."""

    _SELECTED_BULLET = "\u25cf"    # ●
    _UNSELECTED_BULLET = "\u25cb"  # ○
    _ROW_HOVER_BG = "#1e2e4a"

    def __init__(self, parent, presets, selected_index, on_select, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)
        self._presets = presets  # list of (label, value)
        self._on_select = on_select
        self._selected_index = selected_index
        self._row_labels = []

        for i, (text, value) in enumerate(presets):
            row = tk.Label(
                self,
                text=self._row_text(i),
                font=(FONT_FAMILY, 10, "bold" if i == selected_index else "normal"),
                bg=ACCENT_COLOR,
                fg=COLOR_ACTIVE_FG if i == selected_index else COLOR_NEARBY_FG,
                anchor="w",
                padx=8,
                pady=4,
                cursor="hand2",
            )
            row.pack(fill=tk.X)
            row.bind("<Button-1>", lambda e, idx=i: self._select(idx))
            row.bind("<Enter>", lambda e, r=row: r.configure(bg=self._ROW_HOVER_BG))
            row.bind("<Leave>", lambda e, r=row: r.configure(bg=ACCENT_COLOR))
            self._row_labels.append(row)

    def _row_text(self, i):
        bullet = self._SELECTED_BULLET if i == self._selected_index else self._UNSELECTED_BULLET
        label, _ = self._presets[i]
        return f"{bullet}  {label}"

    def _select(self, index):
        if index == self._selected_index:
            return
        self._selected_index = index
        for i, row in enumerate(self._row_labels):
            row.configure(
                text=self._row_text(i),
                font=(FONT_FAMILY, 10, "bold" if i == index else "normal"),
                fg=COLOR_ACTIVE_FG if i == index else COLOR_NEARBY_FG,
            )
        self._on_select(self._presets[index][1])


class SettingsWindow(tk.Toplevel):
    """Preferences window: window-size and font-size preset lists."""

    _WIDTH = 320
    _HEIGHT = 420

    def __init__(self, parent, current_window_size, current_font_sizes, on_window_size_change, on_font_size_change):
        super().__init__(parent)
        self.title("Settings")
        self.resizable(False, False)
        self.configure(bg=BG_COLOR)
        self._center_over(parent)
        apply_app_icon(self)
        # Groups this window with the main one (single taskbar entry, raised
        # together, closes together) - same as the log viewer.
        self.transient(parent)
        try:
            self.attributes("-topmost", parent.attributes("-topmost"))
        except tk.TclError:
            pass

        tk.Label(
            self, text="Window Size ['W' x 'H']", font=(FONT_FAMILY, 11, "bold"),
            bg=BG_COLOR, fg=COLOR_ACTIVE_FG,
        ).pack(anchor="w", padx=12, pady=(12, 4))

        size_index = self._match_index(WINDOW_SIZE_PRESETS, current_window_size)
        size_list = _PresetList(self, WINDOW_SIZE_PRESETS, size_index, on_select=on_window_size_change)
        size_list.pack(fill=tk.X, padx=12)

        tk.Label(
            self, text="Lyric Font Size ['Active' | 'Nearby' | 'Far']", font=(FONT_FAMILY, 11, "bold"),
            bg=BG_COLOR, fg=COLOR_ACTIVE_FG,
        ).pack(anchor="w", padx=12, pady=(16, 4))

        font_index = self._match_index(FONT_SIZE_PRESETS, current_font_sizes)
        font_list = _PresetList(self, FONT_SIZE_PRESETS, font_index, on_select=on_font_size_change)
        font_list.pack(fill=tk.X, padx=12)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    @staticmethod
    def _match_index(presets, current_value):
        """Which preset matches the current value - defaults to 0 (the
        first preset) if nothing matches exactly, e.g. a custom value not
        represented by any preset."""
        for i, (_, value) in enumerate(presets):
            if value == current_value:
                return i
        return 0

    def _center_over(self, parent):
        """Position this window centered over the main app window."""
        parent.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw - self._WIDTH) // 2
        y = py + (ph - self._HEIGHT) // 2
        x = max(0, min(x, self.winfo_screenwidth() - self._WIDTH))
        y = max(0, min(y, self.winfo_screenheight() - self._HEIGHT))
        self.geometry(f"{self._WIDTH}x{self._HEIGHT}+{x}+{y}")

    def _on_close(self):
        global _active_window
        _active_window = None
        self.destroy()


def open_settings_window(parent, current_window_size, current_font_sizes, on_window_size_change, on_font_size_change):
    """Open the settings window, or focus the existing one if already open."""
    global _active_window
    if _active_window is not None and _active_window.winfo_exists():
        _active_window.lift()
        _active_window.focus_force()
        return _active_window
    _active_window = SettingsWindow(
        parent, current_window_size, current_font_sizes, on_window_size_change, on_font_size_change
    )
    return _active_window


def set_pinned(is_pinned):
    """Sync the settings window's always-on-top state with the main window's pin button."""
    if _active_window is not None and _active_window.winfo_exists():
        _active_window.attributes("-topmost", is_pinned)