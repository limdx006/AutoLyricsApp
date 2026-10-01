"""
Preferences window opened from the ⚙ button: two mutually-exclusive
preset lists (window size, lyric font size). Clicking a row applies it
immediately and highlights it as selected - no separate Apply/OK step.

Sticks with the main window the same way the log viewer does: same icon,
transient (grouped/raised together), centered over it on open, and its
always-on-top state kept in sync with the main window's pin button.
"""

import re
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox
from config import *
from log_viewer import apply_app_icon
import update_checker
import updater
from version import APP_VERSION, GITHUB_OWNER, GITHUB_REPO, RELEASE_ASSET_NAME

_active_window = None  # the single open SettingsWindow, if any


class _PresetList(tk.Frame):
    """A vertical list of mutually-exclusive selectable rows (like a radio
    group): a bullet + label per row. Clicking a row selects it, unselects
    the rest, and calls on_select with that row's value."""

    _SELECTED_BULLET = "\u25cf"    # ●
    _UNSELECTED_BULLET = "\u25cb"  # ○
    _ROW_HOVER_BG = "#1e2e4a"

    def __init__(self, parent, presets, selected_index, on_select, on_activate=None, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)
        self._presets = presets  # list of (label, value)
        self._on_select = on_select
        # Called whenever a preset row is picked - lets a sibling "Custom"
        # row (if any) know it should deselect itself.
        self._on_activate = on_activate
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
        if self._on_activate:
            self._on_activate()
        self._on_select(self._presets[index][1])

    def deselect_all(self):
        """Clear every row's bullet/highlight without firing on_select - used when a sibling Custom row becomes active instead."""
        self._selected_index = -1
        for i, row in enumerate(self._row_labels):
            row.configure(
                text=f"{self._UNSELECTED_BULLET}  {self._presets[i][0]}",
                font=(FONT_FAMILY, 10, "normal"),
                fg=COLOR_NEARBY_FG,
            )


class _CustomEntryRow(tk.Frame):
    """
    A 'Custom' row styled like the other preset rows (bullet + label), but
    with inline integer entry boxes instead of a fixed value. Digit-only
    input while typing; committing (Enter, or leaving a field) with every
    box holding a value clamps each to value_range, reflects the clamped
    value back into the box, selects this row, and fires on_commit with
    the tuple of ints.
    """

    _SELECTED_BULLET = "\u25cf"    # ●
    _UNSELECTED_BULLET = "\u25cb"  # ○

    def __init__(self, parent, label, field_count, separator, value_range,
                 initial_values, on_commit, on_activate, field_width=5, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)
        self._on_commit = on_commit
        self._on_activate = on_activate
        self._value_ranges = value_range if value_range and isinstance(value_range[0], tuple) else [value_range] * field_count

        self._bullet_label = tk.Label(
            self, text=self._UNSELECTED_BULLET, font=(FONT_FAMILY, 10),
            bg=ACCENT_COLOR, fg=COLOR_NEARBY_FG,
        )
        self._bullet_label.pack(side="left", padx=(8, 2), pady=4)

        tk.Label(
            self, text=label, font=(FONT_FAMILY, 10),
            bg=ACCENT_COLOR, fg=COLOR_NEARBY_FG,
        ).pack(side="left")

        vcmd = (self.register(self._validate_digits), "%P")
        self._vars = []
        for i in range(field_count):
            if i > 0:
                tk.Label(
                    self, text=separator, font=(FONT_FAMILY, 10),
                    bg=ACCENT_COLOR, fg=COLOR_NEARBY_FG,
                ).pack(side="left")
            initial = str(initial_values[i]) if initial_values else ""
            var = tk.StringVar(value=initial)
            entry = tk.Entry(
                self, textvariable=var, width=field_width, justify="center",
                validate="key", validatecommand=vcmd,
            )
            entry.pack(side="left", padx=2)
            entry.bind("<Return>", lambda e: self._try_commit())
            entry.bind("<FocusOut>", lambda e: self._try_commit())
            self._vars.append(var)

        # Explicit "Apply" button - same effect as pressing Enter in a
        # field, just a more discoverable trigger for applying custom values.
        self._apply_button = tk.Button(
            self,
            text="Apply",
            font=(FONT_FAMILY, 9),
            command=self._try_commit,
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=0,
            bg=COLOR_ACTIVE_FG,
            fg=COLOR_FAR_FG,
            activebackground=COLOR_FAR_FG,
            activeforeground=COLOR_ACTIVE_FG,
            padx=6,
            pady=1,
        )
        self._apply_button.pack(side="right", padx=(4, 8))
        self._apply_button.bind("<Enter>", lambda e: e.widget.configure(bg=COLOR_ARTIST_FG))
        self._apply_button.bind("<Leave>", lambda e: e.widget.configure(bg=COLOR_ACTIVE_FG))

    def _validate_digits(self, proposed):
        """Key-validation: digits only. Empty is allowed too, so the field can be cleared while typing."""
        return proposed == "" or proposed.isdigit()

    def _try_commit(self):
        """If every field currently holds a value, clamp each to value_range, reflect the clamp back, select this row, and fire on_commit."""
        if any(not var.get().isdigit() for var in self._vars):
            return  # still incomplete - wait for every field to have a value
        values = [
            max(lo, min(hi, int(var.get())))
            for var, (lo, hi) in zip(self._vars, self._value_ranges)
        ]
        for var, n in zip(self._vars, values):
            var.set(str(n))
        self.set_selected(True)
        self._on_activate()
        self._on_commit(tuple(values))

    def set_selected(self, selected):
        self._bullet_label.configure(
            text=self._SELECTED_BULLET if selected else self._UNSELECTED_BULLET,
            fg=COLOR_ACTIVE_FG if selected else COLOR_NEARBY_FG,
        )


class _SingleValueEntry(tk.Frame):
    """
    A single standalone float-value row (label + one entry box + Apply
    button), restricted to at most one decimal place - no preset list
    alongside it, just a plain settable value. Committing (Enter,
    focus-out, or the Apply button) with a valid number clamps it to
    value_range, rounds to one decimal, reflects that back into the box,
    and fires on_commit.
    """

    def __init__(self, parent, label, value_range, initial_value, on_commit, field_width=6, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)
        self._on_commit = on_commit
        self._value_range = value_range

        tk.Label(
            self, text=label, font=(FONT_FAMILY, 10),
            bg=ACCENT_COLOR, fg=COLOR_NEARBY_FG,
        ).pack(side="left", padx=(8, 4), pady=4)

        vcmd = (self.register(self._validate_one_decimal), "%P")
        self._var = tk.StringVar(value=self._format(initial_value))
        entry = tk.Entry(
            self, textvariable=self._var, width=field_width, justify="center",
            validate="key", validatecommand=vcmd,
        )
        entry.pack(side="left", padx=2)
        entry.bind("<Return>", lambda e: self._try_commit())
        entry.bind("<FocusOut>", lambda e: self._try_commit())

        self._apply_button = tk.Button(
            self,
            text="Apply",
            font=(FONT_FAMILY, 9),
            command=self._try_commit,
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=0,
            bg=COLOR_ACTIVE_FG,
            fg=COLOR_FAR_FG,
            activebackground=COLOR_FAR_FG,
            activeforeground=COLOR_ACTIVE_FG,
            padx=6,
            pady=1,
        )
        self._apply_button.pack(side="right", padx=(4, 8))
        self._apply_button.bind("<Enter>", lambda e: e.widget.configure(bg=COLOR_ARTIST_FG))
        self._apply_button.bind("<Leave>", lambda e: e.widget.configure(bg=COLOR_ACTIVE_FG))

    @staticmethod
    def _format(value):
        return f"{value:.1f}"

    def _validate_one_decimal(self, proposed):
        """Key-validation: optional leading '-', digits, optional '.', at most one digit after it."""
        if proposed in ("", "-"):
            return True  # allow while typing - not committable yet, but shouldn't block the keystroke
        return bool(re.fullmatch(r"-?\d*\.?\d?", proposed))

    def _try_commit(self):
        try:
            value = float(self._var.get())
        except ValueError:
            return  # incomplete (e.g. just "-" or ".") - wait for a real number
        lo, hi = self._value_range
        value = round(max(lo, min(hi, value)), 1)
        self._var.set(self._format(value))
        self._on_commit(value)


class _UpdateSection(tk.Frame):
    """
    Bottom-of-window section: current version, a button, and a short
    status line.

    The button is "Check for Update" by default. Clicking it checks
    GitHub (bypassing the normal throttle, since this is a deliberate
    user action) and shows "Checking...' while that's in flight. If a
    newer release is found, the button switches to "Update to vX.Y.Z" -
    clicking it opens the release page in the browser for now (actual
    in-app download/install isn't built yet).
    """

    def __init__(self, parent, on_restart=None, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)
        self._latest_result = None
        # Called once the swap script is launched, to close the whole app
        # (not just this window) so the exe's file lock releases.
        self._on_restart = on_restart

        tk.Label(
            self, text=f"Version {APP_VERSION}", font=(FONT_FAMILY, 10),
            bg=ACCENT_COLOR, fg=COLOR_NEARBY_FG,
        ).pack(anchor="w", padx=8, pady=(6, 4))

        self._button = tk.Button(
            self,
            text="Check for Update",
            font=(FONT_FAMILY, 9),
            command=self._handle_click,
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=0,
            bg=COLOR_ACTIVE_FG,
            fg=COLOR_FAR_FG,
            activebackground=COLOR_FAR_FG,
            activeforeground=COLOR_ACTIVE_FG,
            padx=6,
            pady=4,
        )
        self._button.pack(anchor="w", padx=8)
        self._button.bind("<Enter>", lambda e: e.widget.configure(bg=COLOR_ARTIST_FG))
        self._button.bind("<Leave>", lambda e: e.widget.configure(bg=COLOR_ACTIVE_FG))

        self._status_label = tk.Label(
            self, text="", font=(FONT_FAMILY, 9),
            bg=ACCENT_COLOR, fg=COLOR_STATUS_FG,
        )
        self._status_label.pack(anchor="w", padx=8, pady=(4, 6))

        update_checker.subscribe(self._on_result)
        self.bind("<Destroy>", self._on_destroy)

    def _on_result(self, result):
        # Can fire from the background check thread - marshal onto the Tk main thread.
        self.after(0, lambda: self._apply_result(result))

    def _apply_result(self, result):
        if not self.winfo_exists():
            return
        self._latest_result = result
        if result is None:
            self._button.configure(text="Check for Update", state="normal")
            self._status_label.configure(text="")
        elif result.get("available"):
            self._button.configure(text=f"Update to v{result['latest_version']}", state="normal")
            self._status_label.configure(text="A new version is available", fg=GOOD_COLOR)
        elif result.get("latest_version"):
            self._button.configure(text="Check for Update", state="normal")
            self._status_label.configure(text="You're up to date", fg=COLOR_STATUS_FG)
        else:
            self._button.configure(text="Check for Update", state="normal")
            self._status_label.configure(text="Couldn't check for updates", fg=ERROR_COLOR)

    def _handle_click(self):
        if self._latest_result and self._latest_result.get("available"):
            self._handle_update_click()
            return
        self._button.configure(text="Checking...", state="disabled")
        self._status_label.configure(text="")
        update_checker.check_now(force=True)

    def _handle_update_click(self):
        """The button reads 'Update to vX.Y.Z' - actually install it, or
        fall back to just opening the release page when there's nothing
        here to replace (running from source) or nowhere safe to put it."""
        result = self._latest_result
        release_page = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
        download_url = result.get("download_url")

        if not updater.is_frozen():
            webbrowser.open(download_url or release_page)
            return

        if not download_url:
            messagebox.showerror(
                "Update",
                f"Couldn't find {RELEASE_ASSET_NAME} in the v{result['latest_version']} "
                f"release - opening the release page instead.",
            )
            webbrowser.open(release_page)
            return

        if not updater.can_write_target():
            messagebox.showerror(
                "Update",
                "LyricsPlayer doesn't have permission to update itself here - "
                "try moving it out of Program Files, or run it as administrator.",
            )
            return

        if not messagebox.askyesno(
            "Update LyricsPlayer",
            f"Update to v{result['latest_version']}?\n\nThe app will close and reopen automatically.",
        ):
            return

        self._start_download(download_url)

    def _start_download(self, url):
        self._button.configure(state="disabled")
        self._status_label.configure(text="Downloading... 0%", fg=COLOR_STATUS_FG)
        last_percent = {"value": -1}

        def on_progress(downloaded, total):
            if total:
                percent = int(downloaded * 100 / total)
                if percent == last_percent["value"]:
                    return  # skip redundant UI updates between whole percentage points
                last_percent["value"] = percent
                text = f"Downloading... {percent}%"
            else:
                text = f"Downloading... {downloaded // 1024} KB"
            self.after(0, lambda: self._status_label.configure(text=text))

        def worker():
            try:
                path = updater.download_update(url, progress_callback=on_progress)
            except Exception as e:
                print(f"[Update] Download failed: {e}")
                self.after(0, lambda: self._download_failed())
                return
            self.after(0, lambda: self._download_complete(path))

        threading.Thread(target=worker, daemon=True).start()

    def _download_failed(self):
        if not self.winfo_exists():
            return
        self._button.configure(text=f"Update to v{self._latest_result['latest_version']}", state="normal")
        self._status_label.configure(text="Download failed - try again", fg=ERROR_COLOR)

    def _download_complete(self, downloaded_path):
        if not self.winfo_exists():
            return
        self._status_label.configure(text="Installing update...", fg=COLOR_STATUS_FG)
        try:
            updater.apply_update(downloaded_path)
        except Exception as e:
            print(f"[Update] Failed to launch updater: {e}")
            self._status_label.configure(text="Update failed to start", fg=ERROR_COLOR)
            self._button.configure(text=f"Update to v{self._latest_result['latest_version']}", state="normal")
            return
        if self._on_restart:
            self.after(500, self._on_restart)  # brief pause so "Installing..." is visible

    def _on_destroy(self, _event=None):
        update_checker.unsubscribe(self._on_result)


class SettingsWindow(tk.Toplevel):
    """Preferences window: window-size and font-size preset lists."""

    _WIDTH = 320
    _HEIGHT = 680  # grown to fit the Updates section - re-check if content ever changes

    def __init__(self, parent, current_window_size, current_font_sizes, current_default_offset,
                 on_window_size_change, on_font_size_change, on_default_offset_change):
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
        size_list = _PresetList(self, WINDOW_SIZE_PRESETS, size_index if size_index is not None else -1, on_select=on_window_size_change)
        size_list.pack(fill=tk.X, padx=12)
        size_custom = _CustomEntryRow(
            self, "Custom -", field_count=2, separator=" x ", value_range=((300, 3000), (570, 3000)),
            initial_values=current_window_size,
            on_commit=on_window_size_change,
            on_activate=lambda: size_list.deselect_all(),
            field_width=5,
        )
        size_custom.pack(fill=tk.X, padx=12)
        size_list._on_activate = lambda: size_custom.set_selected(False)
        self._size_list, self._size_custom = size_list, size_custom

        tk.Label(
            self, text="Lyric Font Size ['Active' | 'Nearby' | 'Far']", font=(FONT_FAMILY, 11, "bold"),
            bg=BG_COLOR, fg=COLOR_ACTIVE_FG,
        ).pack(anchor="w", padx=12, pady=(16, 4))

        font_index = self._match_index(FONT_SIZE_PRESETS, current_font_sizes)
        font_list = _PresetList(self, FONT_SIZE_PRESETS, font_index if font_index is not None else -1, on_select=on_font_size_change)
        font_list.pack(fill=tk.X, padx=12)
        font_initial = (current_font_sizes["active"], current_font_sizes["nearby"], current_font_sizes["far"]) if current_font_sizes else None
        font_custom = _CustomEntryRow(
            self, "Custom -", field_count=3, separator=" / ", value_range=(1, 99),
            initial_values=font_initial,
            on_commit=lambda values: on_font_size_change({"active": values[0], "nearby": values[1], "far": values[2]}),
            on_activate=lambda: font_list.deselect_all(),
            field_width=3,
        )
        font_custom.pack(fill=tk.X, padx=12)
        font_list._on_activate = lambda: font_custom.set_selected(False)
        self._font_list, self._font_custom = font_list, font_custom

        tk.Label(
            self, text="Default Lyric Offset (s)", font=(FONT_FAMILY, 11, "bold"),
            bg=BG_COLOR, fg=COLOR_ACTIVE_FG,
        ).pack(anchor="w", padx=12, pady=(16, 4))

        offset_row = _SingleValueEntry(
            self, "Offset:", value_range=(OFFSET_MIN, OFFSET_MAX),
            initial_value=current_default_offset,
            on_commit=on_default_offset_change,
            field_width=6,
        )
        offset_row.pack(fill=tk.X, padx=12, pady=(0, 12))
        self._offset_row = offset_row

        tk.Label(
            self, text="Updates", font=(FONT_FAMILY, 11, "bold"),
            bg=BG_COLOR, fg=COLOR_ACTIVE_FG,
        ).pack(anchor="w", padx=12, pady=(16, 4))

        update_section = _UpdateSection(self, on_restart=self._handle_update_restart)
        update_section.pack(fill=tk.X, padx=12, pady=(0, 12))
        self._update_section = update_section

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    @staticmethod
    def _match_index(presets, current_value):
        """Which preset matches the current value - returns None if
        nothing matches (e.g. the current value came from the Custom
        row), so the caller can pre-select Custom instead of guessing."""
        for i, (_, value) in enumerate(presets):
            if value == current_value:
                return i
        return None

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

    def _handle_update_restart(self):
        """Called once the update's swap script has been launched - close
        the whole app (self.master is root, not just this window) so the
        exe's file lock releases and the new version can start."""
        self.master.destroy()


def open_settings_window(parent, current_window_size, current_font_sizes, current_default_offset,
                          on_window_size_change, on_font_size_change, on_default_offset_change):
    """Open the settings window, or close it (same as clicking its own close
    button/cross) if it's already open - lets the ⚙ button act as a toggle."""
    global _active_window
    if _active_window is not None and _active_window.winfo_exists():
        _active_window._on_close()
        return None
    _active_window = SettingsWindow(
        parent, current_window_size, current_font_sizes, current_default_offset,
        on_window_size_change, on_font_size_change, on_default_offset_change,
    )
    return _active_window


def set_pinned(is_pinned):
    """Sync the settings window's always-on-top state with the main window's pin button."""
    if _active_window is not None and _active_window.winfo_exists():
        _active_window.attributes("-topmost", is_pinned)