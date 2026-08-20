import tkinter as tk
from config import *


class LanguageBar(tk.Frame):
    """
    Below top section for language detect and translation
    Korean and Japanese to Romaji
    Chinese to PinYin
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)

        # Fixed height = 10% of window height below song details
        self.configure(height=int(WINDOW_HEIGHT * 0.1))
        self.pack_propagate(False)
        # Add margin around the frame when packed
        self.pack_configure(padx=10, pady=5)

        # Layout: three columns - language info, switch button, current info
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=1)

        # Left side: Language label and value
        left_frame = tk.Frame(self, bg=ACCENT_COLOR)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=0)
        tk.Label(left_frame, text="Language:", font=(FONT_FAMILY, 8, "bold"),
                 bg=ACCENT_COLOR, fg=COLOR_ACTIVE_FG).pack()
        tk.Label(left_frame, text="Unknown", font=(FONT_FAMILY, 8),
                 bg=ACCENT_COLOR, fg=COLOR_NEARBY_FG).pack()

        # Center: Switch button (hardcoded for now)
        switch_button = tk.Button(self, text="Language Switch",
                                   bg=ACCENT_COLOR, fg=COLOR_ACTIVE_FG,
                                   font=(FONT_FAMILY, 10), borderwidth=0, relief=tk.FLAT,
                                   highlightthickness=0,
                                   activebackground="#1e2e4a",
                                   activeforeground=COLOR_ACTIVE_FG)
        switch_button.grid(row=0, column=1, sticky="n", padx=5, pady=0)

        # Right side: Current label and value
        right_frame = tk.Frame(self, bg=ACCENT_COLOR)
        right_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=0)
        tk.Label(right_frame, text="Current:", font=(FONT_FAMILY, 8, "bold"),
                 bg=ACCENT_COLOR, fg=COLOR_ACTIVE_FG).pack()
        tk.Label(right_frame, text="Unknown", font=(FONT_FAMILY, 8),
                 bg=ACCENT_COLOR, fg=COLOR_NEARBY_FG).pack()