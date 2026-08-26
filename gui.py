import tkinter as tk
import threading
from tkinter import font as tkfont
from config import *
from gui_controls_panel import ControlsPanel
from gui_media_details import MediaDetails
from gui_language_bar import LanguageBar
from gui_lyrics_display import LyricsDisplay
from lyrics_fetcher import lyrics_fetcher


class LyricsApp:
    def __init__(self, root, title="Song name here", artist="artist name"):
        self.root = root
        self.root.title("Lyrics Player")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)

        # Media details area (top 30%)
        self.media_details = MediaDetails(
            self.root, title, artist,
            # lyrics_display doesn't exist yet at this point - the lambda
            # defers the attribute lookup until the offset actually changes
            # (i.e. after __init__ has finished and everything is built).
            on_offset_change=lambda offset: self.lyrics_display.set_offset(offset),
        )
        self.media_details.pack(side=tk.TOP, fill=tk.X)

        # Language bar area (10% below media details area)
        self.language_bar = LanguageBar(self.root)
        self.language_bar.pack(side=tk.TOP, fill=tk.X)

        # Lyrics display area (expanding middle section) - dynamic, time-synced scrolling
        self.lyrics_display = LyricsDisplay(self.root)
        self.lyrics_display.pack(
            side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(5, 10)
        )
        # Sync the lyrics display with whatever offset is already showing
        # (e.g. DEFAULT_OFFSET from config.py) now that both widgets exist.
        self.lyrics_display.set_offset(self.media_details.get_offset())

        # Controls (bottom 25%)
        self.controls = ControlsPanel(
            self.root,
            initial_title=title,
            initial_artist=artist,
            on_song_change=self._handle_song_change,
            on_time_update=self.lyrics_display.update_time,
        )
        self.controls.pack(side=tk.BOTTOM, fill=tk.X)

        # Fetch lyrics for the initially detected song, if any
        if title and artist:
            self._fetch_lyrics_async(title, artist)

    def _handle_song_change(self, title, artist):
        """Called by ControlsPanel whenever the detected song changes."""
        self.media_details.update_song_info(title, artist)
        self._fetch_lyrics_async(title, artist)

    def _fetch_lyrics_async(self, title, artist):
        """Fetch lyrics off the main thread, then hand them to the lyrics display."""
        def fetch():
            try:
                lyrics = lyrics_fetcher(title, artist)
            except Exception as e:
                print(f"Lyrics fetch failed: {e}")
                lyrics = None
            self.root.after(0, lambda: self.lyrics_display.set_lyrics(lyrics))
        threading.Thread(target=fetch, daemon=True).start()