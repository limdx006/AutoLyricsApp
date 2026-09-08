import re
import tkinter as tk
from config import *
from auto_nudge import trigger_auto_nudge
from log_viewer import open_log_viewer, set_pinned as set_log_pinned
from setting import set_pinned as set_settings_pinned



"""Matches everything the offset entry should accept while typing: an
optional leading '-' (offset can go negative), digits, and at most one
'.'. Also allows "" and "-" alone so the field can be cleared / a minus
typed first without getting rejected mid-edit."""
_OFFSET_INPUT_PATTERN = re.compile(r"^-?\d*\.?\d*$")


class MediaDetails(tk.Frame):
    """Top section of the player: Media name, artist and multiple feature buttons"""

    def __init__(self, parent, title="Song name here", artist="artist name", on_offset_change=None, on_open_settings=None, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)
        self._on_offset_change = on_offset_change
        self._on_open_settings = on_open_settings
        # Mutable so the settings window's default-offset field can change
        # what future song-changes reset to, without touching the offset
        # currently in effect for whatever song is playing right now.
        self._default_offset = DEFAULT_OFFSET

        # Fixed height = 30% of window height
        self.configure(height=int(WINDOW_HEIGHT * 0.3))
        self.pack_propagate(False)  # prevent content shrinking
        # Add margin around the frame when packed
        self.pack_configure(padx=10, pady=5)

        # Configure grid: 2 rows, 3 columns
        self.grid_rowconfigure(
            0, weight=3
        )  # first row (takes more space for potential wrapping)
        self.grid_rowconfigure(1, weight=0)  # second row (no vertical stretch)
        self.grid_columnconfigure(0, weight=0)  # left button column
        self.grid_columnconfigure(1, weight=2)  # middle column (expands)
        self.grid_columnconfigure(2, weight=0)  # right button column

        # Create widgets

        # Left column: Log button (row0) and Refresh button (row1)
        self.log_button = self.create_button(
            "\U0001f4dd", 0, 0, sticky="n"
        )  # 📝 is U+1F4DD
        self.log_button.configure(command=lambda: open_log_viewer(self.winfo_toplevel()))
        self.refresh_button = self.create_button(
            "\u27f3", 1, 0, font_size=18, sticky="n"
        )  # ⟳ is U+27F3
        self.refresh_button.configure(command=trigger_auto_nudge)

        # Middle column: Song name and artist name (stacked vertically)
        middle_frame = tk.Frame(self, bg=ACCENT_COLOR)
        middle_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=12)
        middle_frame.grid_rowconfigure(
            0, weight=2
        )  # song name row (more space for wrapping)
        middle_frame.grid_rowconfigure(1, weight=1)  # artist name row
        middle_frame.grid_columnconfigure(0, weight=1)  # middle column expands

        self.song_name_label = tk.Label(
            middle_frame,
            text=title,
            font=(FONT_FAMILY, 16, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
            wraplength=int(WINDOW_WIDTH * 0.65),
            justify="center",
        )
        self.song_name_label.grid(row=0, column=0, sticky="")  # centered

        self.artist_name_label = tk.Label(
            middle_frame,
            text=artist,
            font=(FONT_FAMILY, 10),
            bg=ACCENT_COLOR,
            fg=COLOR_NEARBY_FG,
            wraplength=int(WINDOW_WIDTH * 0.65),
            justify="center",
        )
        self.artist_name_label.grid(row=1, column=0, sticky="")  # centered

        # Offset control (second row, middle column)
        self.offset_frame = tk.Frame(self, bg=ACCENT_COLOR)
        self.offset_frame.grid(row=1, column=1, padx=5, pady=5)
        # Center the frame contents
        self.offset_label = tk.Label(
            self.offset_frame,
            text="Offset:",
            font=(FONT_FAMILY, 12, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
        )
        self.offset_label.pack(side="left", padx=2)
        self.offset_var = tk.DoubleVar(value=DEFAULT_OFFSET)
        self.offset_var.trace_add("write", self._on_offset_var_changed)
        self.minus_button = self._make_offset_button(
            self.offset_frame, "-", lambda: self._adjust_offset(-0.1)
        )
        offset_vcmd = (self.register(self._validate_offset_input), "%P")
        self.offset_entry = tk.Entry(
            self.offset_frame,
            textvariable=self.offset_var,
            width=5,
            justify="center",
            validate="key",
            validatecommand=offset_vcmd,
        )
        self.offset_entry.pack(side="left", padx=2)
        self.plus_button = self._make_offset_button(
            self.offset_frame, "+", lambda: self._adjust_offset(0.1)
        )

        # Right column: Pin button (row0) and Settings button (row1)
        self.pin_button = self.create_button(
            "\U0001f4cc", 0, 2, sticky="n"
        )  # 📌 is U+1F4CC
        self.pin_button.configure(command=self._toggle_pin_top)
        self.is_pinned = False
        self.settings_button = self.create_button(
            "\u2699", 1, 2, sticky="n"
        )  # ⚙ is U+2699
        self.settings_button.configure(command=self._handle_open_settings)

    def _handle_open_settings(self):
        if self._on_open_settings:
            self._on_open_settings()

    def _validate_offset_input(self, proposed_value):
        """Key-validation callback for the offset entry (validate="key")."""
        return bool(_OFFSET_INPUT_PATTERN.match(proposed_value))

    def _make_offset_button(self, parent, symbol, command, size=OFFSET_BUTTON_SIZE):
        """Create a fixed pixel-size square button."""
        container = tk.Frame(parent, width=size, height=size, bg=ACCENT_COLOR)
        container.pack_propagate(False)  # keep the fixed pixel size regardless of contents
        container.pack(side="left", padx=2)

        button = tk.Button(
            container,
            text=symbol,
            font=(FONT_FAMILY, 12),
            command=command,
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=0,
            bg=COLOR_ACTIVE_FG,
            fg=COLOR_FAR_FG,
            activebackground=COLOR_FAR_FG,
            activeforeground=COLOR_ACTIVE_FG,
        )
        button.pack(fill=tk.BOTH, expand=True)
        button.bind("<Enter>", lambda e: e.widget.configure(bg=COLOR_ARTIST_FG))
        button.bind("<Leave>", lambda e: e.widget.configure(bg=COLOR_ACTIVE_FG))
        return button

    def create_button(self, symbol, row, column, font_size=16, sticky="nsew"):
        button = tk.Button(
            self,
            text=symbol,
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
            font=(FONT_FAMILY, font_size),
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=0,
            activebackground="#1e2e4a",
            activeforeground=COLOR_ACTIVE_FG,
        )
        button.grid(row=row, column=column, padx=10, pady=10, sticky=sticky)
        button.bind("<Enter>", lambda e: e.widget.configure(bg="#1e2e4a"))
        button.bind("<Leave>", lambda e: e.widget.configure(bg=ACCENT_COLOR))
        return button

    def _toggle_pin_top(self):
        """Toggle pin-to-top state and update pin button icon colour."""
        self.is_pinned = not self.is_pinned
        top = self.winfo_toplevel()
        top.attributes("-topmost", self.is_pinned)
        set_log_pinned(self.is_pinned)       # keep the log window's pinned state in sync
        set_settings_pinned(self.is_pinned)  # keep the settings window's pinned state in sync
        if self.is_pinned:
            self.pin_button.configure(fg=ERROR_COLOR)
        else:
            self.pin_button.configure(fg=COLOR_ACTIVE_FG)

    def _on_offset_var_changed(self, *args):
        """Notify the on_offset_change callback whenever the offset value changes."""
        if not self._on_offset_change:
            return
        try:
            value = self.offset_var.get()
        except tk.TclError:
            # Entry box is mid-edit (e.g. empty or just "-") - not a valid
            # float yet, skip until it resolves to something parseable.
            return
        self._on_offset_change(value)

    def get_offset(self):
        """Return the current offset in seconds, or 0.0 if the entry is mid-edit."""
        try:
            return self.offset_var.get()
        except tk.TclError:
            return 0.0

    def _adjust_offset(self, delta: float):
        """Adjust the offset value by *delta* and clamp it within [OFFSET_MIN, OFFSET_MAX]."""
        # Get current value, apply delta, clamp to allowed range
        new_val = round(self.offset_var.get() + delta, 2)
        if new_val < OFFSET_MIN:
            new_val = OFFSET_MIN
        if new_val > OFFSET_MAX:
            new_val = OFFSET_MAX
        self.offset_var.set(new_val)

    def set_default_offset(self, value):
        """Update what future reset_offset() calls (i.e. song changes) reset
        to - called from the settings window. Doesn't touch the offset
        currently in effect for whatever song is playing right now."""
        self._default_offset = value

    def reset_offset(self):
        """Reset the lyric offset back to the current default offset (e.g.
        on a new song). Setting the var fires the existing trace, which
        propagates the reset to the lyrics display via on_offset_change -
        no other wiring needed.
        """
        self.offset_var.set(self._default_offset)

    def update_song_info(self, title, artist):
        """Update the displayed song title and artist, and reset the lyric
        offset to default since it's specific to the previous song."""
        self.song_name_label.config(text=title)
        self.artist_name_label.config(text=artist)
        self.reset_offset()