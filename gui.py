import tkinter as tk
from tkinter import font as tkfont
from config import *


class LyricsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lyrics Player")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG_COLOR)

        # Lyrics display area (top 70%)
        self.label = tk.Label(self.root, text="Lyrics will be displayed here", bg=BG_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, 12))
        self.label.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Controls frame (bottom 30%)
        controls_frame = tk.Frame(self.root, bg=BG_COLOR)
        controls_frame.pack(side=tk.BOTTOM, fill=tk.X)
        # Set the height of the controls frame to 30% of the window height
        controls_frame.configure(height=int(WINDOW_HEIGHT * 0.3))
        controls_frame.pack_propagate(False)  # Prevent the frame from shrinking to fit contents

        # Configure grid for controls_frame: 3 rows (timeline, buttons, status)
        controls_frame.grid_rowconfigure(0, weight=0)  # timeline - fixed height
        controls_frame.grid_rowconfigure(1, weight=2)  # buttons
        controls_frame.grid_rowconfigure(2, weight=1)  # status
        controls_frame.grid_columnconfigure(0, weight=1)

        # Timeline canvas
        self.timeline_canvas = tk.Canvas(controls_frame, bg=ACCENT_COLOR, highlightthickness=1, highlightbackground="black", height=5)
        self.timeline_canvas.grid(row=0, column=0, sticky="ew", padx=26, pady=4)
        # Bind to configure to redraw the progress bar when size changes
        self.timeline_canvas.bind("<Configure>", self.on_timeline_configure)

        # Button frame
        button_frame = tk.Frame(controls_frame, bg=BG_COLOR)
        button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        # Configure grid for button_frame: 7 columns
        button_frame.grid_columnconfigure(0, weight=0)  # current time
        button_frame.grid_columnconfigure(1, weight=1)  # spacer
        button_frame.grid_columnconfigure(2, weight=1)  # previous button
        button_frame.grid_columnconfigure(3, weight=1)  # play/pause button
        button_frame.grid_columnconfigure(4, weight=1)  # next button
        button_frame.grid_columnconfigure(5, weight=1)  # spacer
        button_frame.grid_columnconfigure(6, weight=0)  # total duration

        # Current time label
        self.current_time_label = tk.Label(button_frame, text="00:30", bg=BG_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, 10))
        self.current_time_label.grid(row=0, column=0, padx=2)

        # Previous button
        self.prev_button = tk.Button(button_frame, text="\u23EE", bg=BG_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, 18),
                                    borderwidth=0, relief=tk.FLAT, highlightthickness=0,
                                    activebackground="#24243e", activeforeground=COLOR_ACTIVE_FG)
        self.prev_button.bind("<Enter>", lambda e: e.widget.configure(bg="#24243e"))
        self.prev_button.bind("<Leave>", lambda e: e.widget.configure(bg=BG_COLOR))
        self.prev_button.grid(row=0, column=2, padx=5)
        
        # Play/Pause button
        self.play_pause_button = tk.Button(button_frame, text="\u23F8", bg=BG_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, 18),
                                          borderwidth=0, relief=tk.FLAT, highlightthickness=0,
                                          activebackground="#24243e", activeforeground=COLOR_ACTIVE_FG)
        self.play_pause_button.bind("<Enter>", lambda e: e.widget.configure(bg="#24243e"))
        self.play_pause_button.bind("<Leave>", lambda e: e.widget.configure(bg=BG_COLOR))
        self.play_pause_button.grid(row=0, column=3, padx=5, pady=4)

        # Next button
        self.next_button = tk.Button(button_frame, text="\u23ED", bg=BG_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, 18),
                                    borderwidth=0, relief=tk.FLAT, highlightthickness=0,
                                    activebackground="#24243e", activeforeground=COLOR_ACTIVE_FG)
        self.next_button.bind("<Enter>", lambda e: e.widget.configure(bg="#24243e"))
        self.next_button.bind("<Leave>", lambda e: e.widget.configure(bg=BG_COLOR))
        self.next_button.grid(row=0, column=4, padx=5)

        # Total duration label
        self.total_duration_label = tk.Label(button_frame, text="04:33", bg=BG_COLOR, fg=COLOR_ACTIVE_FG, font=(FONT_FAMILY, 10))
        self.total_duration_label.grid(row=0, column=6, padx=2)

        # Status label
        self.status_label = tk.Label(controls_frame, text="status", bg=BG_COLOR, fg=COLOR_STATUS_FG, font=(FONT_FAMILY, 10))
        self.status_label.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

    def on_timeline_configure(self, event):
        # Redraw timeline progress when canvas size changes
        self.draw_timeline_progress(0.50)

    def draw_timeline_progress(self, progress):
        self.timeline_canvas.delete("all")
        width = self.timeline_canvas.winfo_width()
        height = self.timeline_canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        progress_width = int(width * progress)
        self.timeline_canvas.create_rectangle(0, 0, progress_width, height, fill=ERROR_COLOR, outline="")