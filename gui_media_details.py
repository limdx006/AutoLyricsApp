import tkinter as tk
from config import *

class MediaDetails(tk.Frame):
    """Top section of the player: Media name, artist and multiple feature buttons"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)

        # Fixed height = 30% of window height
        self.configure(height=int(WINDOW_HEIGHT * 0.3))
        self.configure(height=int(WINDOW_HEIGHT * 0.4))
        self.pack_propagate(False) # prevent content shrinking

        # Configure grid: 2 rows, 3 columns
        self.grid_rowconfigure(0, weight=3)   # first row (takes more space for potential wrapping)
        self.grid_rowconfigure(1, weight=1)   # second row

        self.grid_columnconfigure(0, weight=0)   # left button column
        self.grid_columnconfigure(1, weight=2)   # middle column (expands)
        self.grid_columnconfigure(2, weight=0)   # right button column

        # Create widgets

        # Left column: Log button (row0) and Refresh button (row1)
        self.log_button = self.create_button("\U0001F4DD", 0, 0, sticky="n")   # 📝 is U+1F4DD
        self.refresh_button = self.create_button("\u21BB", 1, 0, font_size=22)   # ⟳ is U+21BB, bigger

        # Middle column: Song name and artist name (stacked vertically)
        middle_frame = tk.Frame(self, bg=ACCENT_COLOR)
        middle_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=20)
        middle_frame.grid_rowconfigure(0, weight=2)   # song name row (more space for wrapping)
        middle_frame.grid_rowconfigure(1, weight=1)   # artist name row
        middle_frame.grid_columnconfigure(0, weight=1)   # middle column expands

        self.song_name_label = tk.Label(middle_frame, text="Song name here", 
                                        font=(FONT_FAMILY, 16, "bold"), 
                                        bg=ACCENT_COLOR, fg=COLOR_ACTIVE_FG)
        self.song_name_label.grid(row=0, column=0, sticky="")  # centered

        self.artist_name_label = tk.Label(middle_frame, text="artist name", 
                                          font=(FONT_FAMILY, 10), 
                                          bg=ACCENT_COLOR, fg=COLOR_NEARBY_FG)
        self.artist_name_label.grid(row=1, column=0, sticky="")  # centered

        # Offset label (second row, middle column)
        self.offset_label = tk.Label(self, text="offset", 
                                     font=(FONT_FAMILY, 10), 
                                     bg=ACCENT_COLOR, fg=COLOR_ACTIVE_FG)
        self.offset_label.grid(row=1, column=1, sticky="", padx=5, pady=5)

        # Right column: Pin button (row0) and Settings button (row1)
        self.pin_button = self.create_button("\U0001F4CC", 0, 2, sticky="n")   # 📌 is U+1F4CC
        self.settings_button = self.create_button("\u2699", 1, 2)   # ⚙ is U+2699

    def create_button(self, symbol, row, column, font_size=16, sticky="nsew"):
        button = tk.Label(self, text=symbol, bg=ACCENT_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, font_size))
        button.grid(row=row, column=column, padx=5, pady=5, sticky=sticky)
        button.bind("<Enter>", lambda e: e.widget.configure(bg="#1e2e4a"))  # slightly lighter on hover
        button.bind("<Leave>", lambda e: e.widget.configure(bg=ACCENT_COLOR))
        button.bind("<Button-1>", lambda e: e.widget.configure(bg=ACCENT_COLOR))  # visual feedback on click
        button.bind("<ButtonRelease-1>", lambda e: e.widget.configure(bg="#1e2e4a"))  # back to hover color after click
        return button