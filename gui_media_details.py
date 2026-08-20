import tkinter as tk
from config import *
from auto_nudge import trigger_auto_nudge



class MediaDetails(tk.Frame):
    """Top section of the player: Media name, artist and multiple feature buttons"""

    def __init__(self, parent, title="Song name here", artist="artist name", **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)

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

        # Offset label (second row, middle column)
        self.offset_label = tk.Label(
            self,
            text="Offset",
            font=(FONT_FAMILY, 10),
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
        )
        self.offset_label.grid(row=1, column=1, sticky="", padx=5, pady=5)

        # Right column: Pin button (row0) and Settings button (row1)
        self.pin_button = self.create_button(
            "\U0001f4cc", 0, 2, sticky="n"
        )  # 📌 is U+1F4CC
        self.pin_button.configure(command=self._toggle_pin_top)
        self.is_pinned = False
        self.settings_button = self.create_button(
            "\u2699", 1, 2, sticky="n"
        )  # ⚙ is U+2699

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
        if self.is_pinned:
            self.pin_button.configure(fg=ERROR_COLOR)
        else:
            self.pin_button.configure(fg=COLOR_ACTIVE_FG)

    def update_song_info(self, title, artist):
        """Update the displayed song title and artist."""
        self.song_name_label.config(text=title)
        self.artist_name_label.config(text=artist)
