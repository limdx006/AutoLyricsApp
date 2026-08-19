import tkinter as tk
from tkinter import font as tkfont
from config import *
from controls_panel import ControlsPanel


class LyricsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lyrics Player")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG_COLOR)

        # Lyrics display area (top 70%)
        self.label = tk.Label(self.root, text="Lyrics will be displayed here", bg=BG_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, 12))
        self.label.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Controls (bottom 30%)
        self.controls = ControlsPanel(self.root)
        self.controls.pack(side=tk.BOTTOM, fill=tk.X)


if __name__ == "__main__":
    root = tk.Tk()
    app = LyricsApp(root)
    root.mainloop()