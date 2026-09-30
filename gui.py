import tkinter as tk
import threading
from tkinter import font as tkfont
from config import *
from gui_controls_panel import ControlsPanel
from gui_media_details import MediaDetails
from gui_language_bar import LanguageBar
from gui_lyrics_display import LyricsDisplay
from gui_api_status_bar import ApiStatusBar
from lyrics_fetcher import lyrics_fetcher
from language_detect import detect_lyrics_language
from lyrics_translator import translate_lyrics
from auto_nudge import trigger_auto_nudge
from setting import open_settings_window
import user_prefs


def _validate_window_size(value):
    """A saved window size is trusted only if it's a plausible (width,
    height) pair - guards against a corrupted/hand-edited settings file
    (or one from an older version with a different valid range)."""
    try:
        width, height = int(value[0]), int(value[1])
        if 100 <= width <= 4000 and 100 <= height <= 4000:
            return (width, height)
    except (TypeError, ValueError, IndexError, KeyError):
        pass
    return None


def _validate_font_sizes(value):
    try:
        sizes = {key: int(value[key]) for key in ("active", "nearby", "far")}
        if all(6 <= size <= 72 for size in sizes.values()):
            return sizes
    except (TypeError, ValueError, KeyError):
        pass
    return None


def _validate_offset(value):
    try:
        offset = float(value)
        if OFFSET_MIN <= offset <= OFFSET_MAX:
            return offset
    except (TypeError, ValueError):
        pass
    return None


class LyricsApp:
    def __init__(self, root, title="Song name here", artist="artist name", session=None):
        self.root = root
        self._lyrics_fetch_generation = 0
        # Per-song lyric cache: original always kept once fetched
        self._current_raw_lyrics = None
        self._translated_lyrics_cache = None
        # Tracked so the settings window knows which presets are currently selected and can highlight them accordingly
        # Restored from the saved preferences file when available
        saved_prefs = user_prefs.load()
        self._current_window_size = (
            _validate_window_size(saved_prefs.get("window_size")) or (WINDOW_WIDTH, WINDOW_HEIGHT)
        )
        self._current_font_sizes = _validate_font_sizes(saved_prefs.get("font_sizes")) or {
            "active": LyricsDisplay.FONT_SIZE_ACTIVE_DEFAULT,
            "nearby": LyricsDisplay.FONT_SIZE_NEARBY_DEFAULT,
            "far": LyricsDisplay.FONT_SIZE_FAR_DEFAULT,
        }
        self._current_default_offset = _validate_offset(saved_prefs.get("default_offset")) or DEFAULT_OFFSET
        self.root.title("Lyrics Player")
        self.root.geometry(f"{self._current_window_size[0]}x{self._current_window_size[1]}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)

        # Media details area (top 30%)
        self.media_details = MediaDetails(
            self.root, title, artist,
            # lyrics_display doesn't exist yet at this point - the lambda
            # defers the attribute lookup until the offset actually changes
            # (i.e. after __init__ has finished and everything is built).
            on_offset_change=lambda offset: self.lyrics_display.set_offset(offset),
            on_open_settings=self._open_settings,
            on_refresh=self._handle_manual_refresh,
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
        # Apply the saved default offset now that lyrics_display exists
        self.media_details.set_default_offset(self._current_default_offset)
        self.media_details.reset_offset()
        self.lyrics_display.set_offset(self.media_details.get_offset())
        # Apply the saved font sizes
        self.lyrics_display.set_font_sizes(
            self._current_font_sizes["active"],
            self._current_font_sizes["nearby"],
            self._current_font_sizes["far"],
        )

        # API status strip - packed BOTTOM *before* the controls panel below,
        # so it lands at the true bottom edge and controls sits just above it
        self.api_status_bar = ApiStatusBar(self.root)
        self.api_status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Controls (bottom 25%)
        self.controls = ControlsPanel(
            self.root,
            initial_title=title,
            initial_artist=artist,
            initial_session=session,
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
        selected_session = self.controls.get_current_session()

        def fetch():
            try:
                lyrics = lyrics_fetcher(
                    title,
                    artist,
                    session=selected_session,
                )
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

    def _handle_manual_refresh(self):
        """Refresh button: nudge the currently selected session specifically."""
        trigger_auto_nudge(session=self.controls.get_current_session())

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

    def _open_settings(self):
        """Called by the ⚙ settings button: open the settings window, wired to apply changes immediately."""
        open_settings_window(
            self.root,
            current_window_size=self._current_window_size,
            current_font_sizes=self._current_font_sizes,
            current_default_offset=self._current_default_offset,
            on_window_size_change=self._apply_window_size,
            on_font_size_change=self._apply_font_sizes,
            on_default_offset_change=self._apply_default_offset,
        )

    def _apply_window_size(self, size):
        """Called when a window-size preset is selected in the settings window."""
        self._current_window_size = size
        width, height = size
        self.root.geometry(f"{width}x{height}")
        user_prefs.save({"window_size": list(size)})

    def _apply_font_sizes(self, sizes):
        """Called when a font-size preset is selected in the settings window."""
        self._current_font_sizes = sizes
        self.lyrics_display.set_font_sizes(sizes["active"], sizes["nearby"], sizes["far"])
        user_prefs.save({"font_sizes": sizes})

    def _apply_default_offset(self, value):
        """Called when the settings window's default-offset field is committed.
        Only changes what future song-changes reset to - doesn't touch the
        offset currently in effect for whatever song is playing right now.
        """
        self._current_default_offset = value
        self.media_details.set_default_offset(value)
        user_prefs.save({"default_offset": value})