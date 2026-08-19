import tkinter as tk
from config import *


class ControlsPanel(tk.Frame):
    """Bottom section of the player: timeline, transport buttons, and status label."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_COLOR, **kwargs)

        # Fixed height = 20% of window height
        self.configure(height=int(WINDOW_HEIGHT * 0.2))
        self.pack_propagate(False)  # prevent shrinking to fit contents

        # 3 rows: timeline, buttons, status
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=2)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_timeline()
        self._build_buttons()
        self._build_status()

    """Construction helpers"""
    def _build_timeline(self):
        self.timeline_canvas = tk.Canvas(
            self, bg=ACCENT_COLOR, highlightthickness=1,
            highlightbackground="black", height=5
        )
        self.timeline_canvas.grid(row=0, column=0, sticky="ew", padx=26, pady=4)
        self.timeline_canvas.bind("<Configure>", self.on_timeline_configure)

    def _build_buttons(self):
        button_frame = tk.Frame(self, bg=BG_COLOR)
        button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        # 7 columns: time | spacer | prev | play | next | spacer | duration
        for col, weight in enumerate([0, 1, 1, 1, 1, 1, 0]):
            button_frame.grid_columnconfigure(col, weight=weight)

        self.current_time_label = tk.Label(
            button_frame, text="00:30", bg=BG_COLOR, fg=COLOR_ACTIVE_FG,
            font=(FONT_FAMILY, 10)
        )
        self.current_time_label.grid(row=0, column=0, padx=2)

        self.prev_button = self._make_transport_button(button_frame, "\u23EE")
        self.prev_button.grid(row=0, column=2, padx=5)

        self.play_pause_button = self._make_transport_button(button_frame, "\u23F8")
        self.play_pause_button.grid(row=0, column=3, padx=5, pady=4)

        self.next_button = self._make_transport_button(button_frame, "\u23ED")
        self.next_button.grid(row=0, column=4, padx=5)

        self.total_duration_label = tk.Label(
            button_frame, text="04:33", bg=BG_COLOR, fg=COLOR_ACTIVE_FG,
            font=(FONT_FAMILY, 10)
        )
        self.total_duration_label.grid(row=0, column=6, padx=2)

    def _make_transport_button(self, parent, symbol):
        btn = tk.Button(
            parent, text=symbol, bg=BG_COLOR, fg=COLOR_ACTIVE_FG,
            font=(FONT_FAMILY, 18), borderwidth=0, relief=tk.FLAT,
            highlightthickness=0, activebackground="#24243e",
            activeforeground=COLOR_ACTIVE_FG
        )
        btn.bind("<Enter>", lambda e: e.widget.configure(bg="#24243e"))
        btn.bind("<Leave>", lambda e: e.widget.configure(bg=BG_COLOR))
        return btn

    def _build_status(self):
        self.status_label = tk.Label(
            self, text="status", bg=BG_COLOR, fg=COLOR_STATUS_FG,
            font=(FONT_FAMILY, 10)
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

    """Behavior"""
    def on_timeline_configure(self, event):
        self.draw_timeline_progress(0.50)

    def draw_timeline_progress(self, progress):
        self.timeline_canvas.delete("all")
        width = self.timeline_canvas.winfo_width()
        height = self.timeline_canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        progress_width = int(width * progress)
        self.timeline_canvas.create_rectangle(
            0, 0, progress_width, height, fill=ERROR_COLOR, outline=""
        )