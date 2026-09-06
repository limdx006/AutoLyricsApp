import tkinter as tk
import threading
from tkinter import font as tkfont
from config import *
from gui_controls_panel import ControlsPanel
from gui_media_details import MediaDetails
from gui_language_bar import LanguageBar
from gui_lyrics_display import LyricsDisplay
from lyrics_fetcher import lyrics_fetcher
from language_detect import detect_lyrics_language
from lyrics_translator import translate_lyrics
from auto_nudge import trigger_auto_nudge


class LyricsApp:
    def __init__(self, root, title="Song name here", artist="artist name"):
        self.root = root
        self._lyrics_fetch_generation = 0
        self._first_run = True
        # Per-song lyric cache: original always kept once fetched
        self._current_raw_lyrics = None
        self._translated_lyrics_cache = None
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
        self.language_bar = LanguageBar(self.root, on_translate_toggle=self._handle_translate_toggle)
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
        """Fetch lyrics off the main thread, then hand them to the lyrics display.

        Fetches run concurrently on background threads with no ordering
        guarantee, so a slow/retried fetch for a stale (title, artist) can
        finish after a newer one and clobber good lyrics with None. A
        generation token makes sure only the result of the most recently
        requested fetch is ever applied.
        """
        self.lyrics_display.show_loading()  # clear the previous song's lyrics immediately, before the fetch resolves
        self._lyrics_fetch_generation += 1
        my_generation = self._lyrics_fetch_generation

        def fetch():
            try:
                lyrics = lyrics_fetcher(title, artist)
            except Exception as e:
                print(f"Lyrics fetch failed: {e}")
                lyrics = None

            def apply():
                if my_generation != self._lyrics_fetch_generation:
                    # A newer fetch has since been kicked off - this result
                    # is stale, discard it instead of overwriting current lyrics.
                    print(f"[Lyrics] Discarding stale result for '{title}' by '{artist}'")
                    return
                # New song - drop any cached translation from the previous one
                self._current_raw_lyrics = lyrics
                self._translated_lyrics_cache = None
                self.lyrics_display.set_lyrics(lyrics)
                detected_language = detect_lyrics_language(lyrics) if lyrics else "Unknown"
                self.language_bar.set_language(detected_language)

            self.root.after(0, apply)
        threading.Thread(target=fetch, daemon=True).start()
        if self._first_run:
            trigger_auto_nudge(0.1)  # Trigger auto nudge on first run to refresh media session
            self._first_run = False  # Reset the first run flag after the initial fetch

    def _handle_translate_toggle(self, is_translated, language):
        """Called when the language bar's toggle flips: swap between the
        cached original and translated lyrics for the current song. The
        translation is only computed (and cached) the first time it's
        requested for this song - flipping back and forth after that just
        reuses both cached versions with no re-processing.
        """
        if not self._current_raw_lyrics:
            return
        if is_translated:
            if self._translated_lyrics_cache is None:
                self._translated_lyrics_cache = translate_lyrics(self._current_raw_lyrics, language)
            self.lyrics_display.set_lyrics(self._translated_lyrics_cache)
        else:
            self.lyrics_display.set_lyrics(self._current_raw_lyrics)