import tkinter as tk
from config import *

class MediaDetails(tk.Frame):
    """Top section of the player: Media name, artist and multiple deature buttons"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)

        # Fixed height = 30% of window height
        self.configure(height=int(WINDOW_HEIGHT * 0.3))
        self.pack_propagate(False) # prevent content shrinking

        