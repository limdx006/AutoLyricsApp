import tkinter as tk
import asyncio
import threading
from config import *
from media_detect import get_media_position, get_playback_status, control_play, control_pause, control_next, control_previous
from time_formatter import format_display_time
from local_timer import LocalTimer


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

        # Hybrid timer state
        self._local_timer = LocalTimer()
        self._last_windows_position = -1.0
        self._last_total_duration = 0.0
        self._has_synced = False

        self._build_timeline()
        self._build_buttons()
        self._build_status()
        # Start the two update loops
        self.after(0, self._fetch_windows_loop)   # slow: fetch from Windows every 500ms
        self.after(0, self._update_ui_loop)       # fast: update UI from local timer every 100ms

    """Construction helpers"""

    def _build_timeline(self):
        self.timeline_canvas = tk.Canvas(
            self,
            bg=ACCENT_COLOR,
            highlightthickness=1,
            highlightbackground="black",
            height=5,
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
            button_frame,
            text="00:00",
            bg=BG_COLOR,
            fg=COLOR_ACTIVE_FG,
            font=(FONT_FAMILY, 10),
        )
        self.current_time_label.grid(row=0, column=0, padx=2)

        self.prev_button = self._make_transport_button(button_frame, "\u23ee")
        self.prev_button.grid(row=0, column=2, padx=5)
        self.prev_button.configure(command=self._on_previous)

        self.play_pause_button = self._make_transport_button(button_frame, "\u23f8") # \u23f8(pause) \u25B6(play)
        self.play_pause_button.grid(row=0, column=3, padx=5, pady=4)
        self.play_pause_button.configure(command=self._on_play_pause)

        self.next_button = self._make_transport_button(button_frame, "\u23ed")
        self.next_button.grid(row=0, column=4, padx=5)
        self.next_button.configure(command=self._on_next)

        self.total_duration_label = tk.Label(
            button_frame,
            text="00:00",
            bg=BG_COLOR,
            fg=COLOR_ACTIVE_FG,
            font=(FONT_FAMILY, 10),
        )
        self.total_duration_label.grid(row=0, column=6, padx=2)

    def _make_transport_button(self, parent, symbol):
        btn = tk.Button(
            parent,
            text=symbol,
            bg=BG_COLOR,
            fg=COLOR_ACTIVE_FG,
            font=(FONT_FAMILY, 18),
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=0,
            activebackground="#24243e",
            activeforeground=COLOR_ACTIVE_FG,
        )
        btn.bind("<Enter>", lambda e: e.widget.configure(bg="#24243e"))
        btn.bind("<Leave>", lambda e: e.widget.configure(bg=BG_COLOR))
        return btn

    def _build_status(self):
        self.status_label = tk.Label(
            self, text="status", bg=BG_COLOR, fg=COLOR_STATUS_FG, font=(FONT_FAMILY, 10)
        )
        self.status_label.grid(row=2, column=0, sticky="ew", padx=5, pady=5)

    """Behavior"""

    def on_timeline_configure(self, event):
        # Initial draw will be handled by _update_ui_loop
        pass

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

    def _fetch_windows_loop(self):
        """Slow loop: fetch position from Windows media session every 500ms."""
        def fetch():
            try:
                position, total = asyncio.run(get_media_position())
            except Exception:
                position, total = 0.0, 0.0
            # Schedule processing on main thread
            self.after(0, lambda: self._process_windows_update(position, total))
        threading.Thread(target=fetch, daemon=True).start()
        self.after(500, self._fetch_windows_loop)

    def _process_windows_update(self, position, total):
        """Process the position/duration from Windows media session."""
        # Update total duration if it changed
        if total != self._last_total_duration:
            self._last_total_duration = total
            self.total_duration_label.config(text=format_display_time(total))

        # If position changed (user action or natural progression), sync local timer
        if position != self._last_windows_position:
            previous = self._last_windows_position
            self._last_windows_position = position
            print(f"[Session] Window session update from {format_display_time(previous)} to {format_display_time(position)}")
            if not self._has_synced:
                self._local_timer.start(position)
                self._has_synced = True
            else:
                self._local_timer.sync(position)
            # Immediately update UI with the fresh Windows position
            self._update_ui_from_timer()

    def _update_ui_loop(self):
        """Fast loop: update UI from local timer every ~100ms for smooth progress."""
        self._update_ui_from_timer()
        self.after(100, self._update_ui_loop)

    def _update_ui_from_timer(self):
        """Update current time label and progress bar from local timer."""
        if not self._has_synced:
            return
        position = self._local_timer.get_position()
        total = self._last_total_duration
        # Clamp position to total duration
        if total > 0 and position > total:
            position = total
        self.current_time_label.config(text=format_display_time(position))
        progress = (position / total) if total > 0 else 0.0
        self.draw_timeline_progress(progress)

    def _on_previous(self):
        """Handle previous track button click."""
        def run():
            try:
                asyncio.run(control_previous())
            except Exception as e:
                print(f"Previous track failed: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _on_next(self):
        """Handle next track button click."""
        def run():
            try:
                asyncio.run(control_next())
            except Exception as e:
                print(f"Next track failed: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _on_play_pause(self):
        """Handle play/pause button click - checks current status and toggles."""
        def run():
            try:
                status = asyncio.run(get_playback_status())
                if status == "playing":
                    asyncio.run(control_pause())
                    new_symbol = "\u25B6"  # play symbol
                else:
                    asyncio.run(control_play())
                    new_symbol = "\u23f8"  # pause symbol
                # Update button symbol on main thread
                self.after(0, lambda: self.play_pause_button.config(text=new_symbol))
            except Exception as e:
                print(f"Play/pause failed: {e}")
        threading.Thread(target=run, daemon=True).start()