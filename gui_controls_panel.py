import tkinter as tk
import asyncio
import threading
from config import *
from media_detect import get_position_for_session, get_status_for_session, control_play_session, control_pause_session, control_next_session, control_previous_session
from media_selector import select_best_media
from time_formatter import format_display_time
from local_timer import LocalTimer


async def _gather_update():
    """Pick the best session (media_selector), then read its position/status - one asyncio.run() per poll instead of three."""
    session, title, artist, _lyrics = await select_best_media()
    position, total = await get_position_for_session(session)
    status = await get_status_for_session(session)
    return session, position, total, title, artist, status


class ControlsPanel(tk.Frame):
    """Bottom section of the player: timeline, transport buttons, and status label."""

    def __init__(self, parent, initial_title="", initial_artist="", on_song_change=None, on_time_update=None, **kwargs):
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
        # The winsdk session object currently selected by media_selector -
        # playback controls (prev/next/play-pause) act on this, not
        # whatever Windows itself considers "current".
        self._current_session = None
        # Guards against overlapping fetch cycles: a rescore can trigger a
        # real (slow) lyrics search, and without this the 500ms loop would
        # keep firing on top of it, causing multiple concurrent rescores.
        self._fetch_in_progress = False
        # Song info tracking
        self._last_title = initial_title
        self._last_artist = initial_artist
        self._on_song_change = on_song_change
        self._on_time_update = on_time_update
        """Consecutive polls reporting the "no session" sentinel values ("Undetected Song" / "Unknown Artist"). 
        Windows may briefly report these during transitions (e.g. a "repeat one" restart), 
        so require confirmation on the next poll before treating them as a real change."""
        self._unknown_streak = 0

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
        """Slow loop: pick the best media session and fetch its position/info/status every 500ms.
        Skips starting a new fetch while the previous one is still running (e.g. mid rescore/lyrics
        search), instead of piling up overlapping fetches on top of each other."""
        if self._fetch_in_progress:
            self.after(500, self._fetch_windows_loop)
            return
        self._fetch_in_progress = True

        def fetch():
            try:
                session, position, total, title, artist, status = asyncio.run(_gather_update())
            except Exception as e:
                print(f"[Session] Media selection failed: {e}")
                session = None
                position, total = 0.0, 0.0
                title, artist = "Undetected Song", "Unknown Artist"
                status = "stopped"

            def done():
                self._fetch_in_progress = False
                self._process_windows_update(session, position, total, title, artist, status)
            self.after(0, done)
        threading.Thread(target=fetch, daemon=True).start()
        self.after(500, self._fetch_windows_loop)

    def _process_windows_update(self, session, position, total, title, artist, status):
        """Process the position/duration/media info/status from the selected media session."""
        self._current_session = session

        # Update total duration if it changed
        if total != self._last_total_duration:
            self._last_total_duration = total
            self.total_duration_label.config(text=format_display_time(total))

        # Check for song change
        is_unknown = (title == "Undetected Song" and artist == "Unknown Artist")
        self._unknown_streak = self._unknown_streak + 1 if is_unknown else 0

        if title != self._last_title or artist != self._last_artist:
            if is_unknown and self._unknown_streak < 2:
                """
                Likely a transient session glitch (e.g. during a "repeat one" restart), 
                not a real song change. Ignore this poll: don't update last song or fire on_song_change. 
                A real disappearance will repeat and pass the streak check below.
                """
                print(f"[Session] Ignoring possible transient 'no session' report, awaiting confirmation")
            else:
                previous_title = self._last_title
                previous_artist = self._last_artist
                self._last_title = title
                self._last_artist = artist
                print(f"[Session] Detected song update {title} by {artist}")
                if self._on_song_change:
                    self._on_song_change(title, artist)

        # Sync play/pause button symbol, status label, and timer state with external playback status
        if status == "playing":
            self.play_pause_button.config(text="\u23f8")  # pause symbol
            self.status_label.config(text="Playing")
            if not self._local_timer.is_running() and self._has_synced:
                self._local_timer.start(position)
        elif status in ("paused", "stopped"):
            self.play_pause_button.config(text="\u25B6")  # play symbol
            self.status_label.config(text="Paused")
            if self._local_timer.is_running():
                self._local_timer.stop()

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
        if self._on_time_update:
            self._on_time_update(position)

    def get_current_session(self):
        """Return the winsdk session object currently selected by
        media_selector (or None)."""
        return self._current_session

    def _on_previous(self):
        """Handle previous track button click - acts on the currently selected session."""
        session = self._current_session
        def run():
            try:
                asyncio.run(control_previous_session(session))
            except Exception as e:
                print(f"Previous track failed: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _on_next(self):
        """Handle next track button click - acts on the currently selected session."""
        session = self._current_session
        def run():
            try:
                asyncio.run(control_next_session(session))
            except Exception as e:
                print(f"Next track failed: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _on_play_pause(self):
        """Handle play/pause button click - checks current status and toggles, on the currently selected session."""
        session = self._current_session
        def run():
            try:
                status = asyncio.run(get_status_for_session(session))
                if status == "playing":
                    asyncio.run(control_pause_session(session))
                    new_symbol = "\u25B6"  # play symbol
                    new_status_text = "Paused"
                    # Freeze the local timer so the displayed position/lyrics stop too
                    self.after(0, self._local_timer.stop)
                else:
                    asyncio.run(control_play_session(session))
                    new_symbol = "\u23f8"  # pause symbol
                    new_status_text = "Playing"
                    # Resume the local timer from wherever it was frozen
                    self.after(0, lambda: self._local_timer.start(self._local_timer.get_position()))
                # Update button symbol and status label on main thread - gives
                # instant feedback instead of waiting for the next 500ms poll
                # to confirm the change.
                self.after(0, lambda: self.play_pause_button.config(text=new_symbol))
                self.after(0, lambda: self.status_label.config(text=new_status_text))
            except Exception as e:
                print(f"Play/pause failed: {e}")
        threading.Thread(target=run, daemon=True).start()