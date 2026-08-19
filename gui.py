import tkinter as tk
from tkinter import font as tkfont
from config import *
from gui_controls_panel import ControlsPanel
from gui_media_details import MediaDetails

class LyricsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lyrics Player")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG_COLOR)

        # Media details area (top 30%)
        self.media_details = MediaDetails(self.root)
        self.media_details.pack(side=tk.TOP, fill=tk.X)

        # Language bar area (10% below media details area)
        self.language_bar = tk.Frame(self.root, bg=BG_COLOR, height=int(WINDOW_HEIGHT * 0.1))
        self.language_bar.pack_propagate(False)
        self.language_bar.pack(side=tk.TOP, fill=tk.X)

        # Lyrics display area (expanding middle section)
        self.lyrics_label = tk.Label(self.root, text="Lyrics will be displayed here", bg=BG_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, 12))
        self.lyrics_label.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        # Controls (bottom 25%)
        self.controls = ControlsPanel(self.root)
        self.controls.pack(side=tk.BOTTOM, fill=tk.X)