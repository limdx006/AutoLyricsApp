import tkinter as tk
from tkinter import font as tkfont
from config import *


class LyricsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lyrics Player")

        # Set window size
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")

        # Set background color
        self.root.configure(bg=BG_COLOR)

        # Example placeholder label
        self.label = tk.Label(self.root, text="Lyrics will be displayed here", bg=BG_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, 12))
        self.label.pack(pady=20)


