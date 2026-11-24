r"""
@misc{syncedlyrics,
  author = {Momeni, Mohammad},
  title = {syncedlyrics},
  year = {2022},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/moehmeni/syncedlyrics}},
}
"""

import inspect
import logging
import re
import time

import syncedlyrics
import api_status
from request_api import fetch_from_my_lyrics_api
from auto_nudge import trigger_auto_nudge

_NO_SONG_TITLE = "Undetected Song"
_NO_ARTIST = "Unknown Artist"

# Genius only has plain text, so it can never match synced_only - skipped.
_SYNCED_PROVIDERS = ("Musixmatch", "Lrclib", "NetEase", "Megalobiz")
_PROVIDER_LOGGERS = (
    "Musixmatch", "Lrclib", "NetEase", "Megalobiz",
    "Genius", "Deezer", "Lyricsify", "Spotify",
)
_CAN_PICK_PROVIDERS = "providers" in inspect.signature(syncedlyrics.search).parameters


def remove_empty_lines(lyrics: str) -> str:
    """Remove lines that contain only a timestamp with no lyrics."""
    cleaned_lines = []
    empty_pattern = re.compile(r"^\[\d{2}:\d{2}\.\d{2}\]\s*$")
    for line in lyrics.splitlines():
        if not empty_pattern.match(line):
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def _drop_leaked_handlers():
    """syncedlyrics adds a new log handler on every search and never removes it."""
    for name in _PROVIDER_LOGGERS:
        logging.getLogger(name).handlers.clear()


def _search_syncedlyrics(query, is_current):
    """Try providers one by one. Stops early if the song changed."""
    if not _CAN_PICK_PROVIDERS:
        try:
            return syncedlyrics.search(query, synced_only=True, enhanced=False)
        except Exception as e:
            print(f"[Lyrics] syncedlyrics failed: {e}")
            return None
        finally:
            _drop_leaked_handlers()

    for name in _SYNCED_PROVIDERS:
        if not is_current():
            print("[Lyrics] Song changed - stopping search")
            return None
        try:
            lyrics = syncedlyrics.search(query, synced_only=True, providers=[name], enhanced=False)
        except Exception as e:
            print(f"[Lyrics] {name} failed: {e}")
            continue
        finally:
            _drop_leaked_handlers()
        if lyrics:
            return lyrics
    return None


def _nudge_if_current(session, is_current):
    """Nudge the player, but only if this is still the current song."""
    if session is None or not is_current():
        return
    time.sleep(0.5)  # let the player settle
    if not is_current():
        return
    print(f"[Session] Current session: {session}")
    print("[Nudge] Triggering auto nudge after lyrics fetch")
    trigger_auto_nudge(0.2, session=session)


def lyrics_fetcher(title, artist, session=None, is_current=None):
    """
    Get lyrics: MyLyricsAPI first (only if online), then syncedlyrics.
    is_current() returning False means the song changed, so stop early.
    """
    is_current = is_current or (lambda: True)
    if not title or not artist or title == _NO_SONG_TITLE or artist == _NO_ARTIST:
        print(f"[Lyrics] Skipping search - no real song detected ('{title}' by '{artist}')")
        return None
    query = f"{title} {artist}".strip()
    wall_start, cpu_start = time.perf_counter(), time.process_time()

    lyrics = None
    source = None
    status = api_status.get_status()
    if status in (api_status.STATUS_OFFLINE, api_status.STATUS_STARTING):
        print(f"[MyLyricsAPI] Skipping - status is '{status}', going straight to syncedlyrics")
    else:
        print(f"[MyLyricsAPI] Searching for '{title}' by '{artist}'")
        lyrics = fetch_from_my_lyrics_api(title, artist)
        source = "MyLyricsAPI"

    if not lyrics and is_current():
        print(f"[Lyrics] Falling back to syncedlyrics for '{query}'")
        lyrics = _search_syncedlyrics(query, is_current)
        source = "syncedlyrics"

    cleaned = remove_empty_lines(lyrics) if lyrics else None
    wall = time.perf_counter() - wall_start
    cpu = time.process_time() - cpu_start
    print(f"[Lyrics] Search took {wall:.1f}s (process CPU {cpu:.1f}s)")

    if not cleaned:
        return None
    print(f"[{source}] Retrieved lyrics for '{query}' with {len(cleaned.splitlines())} lines")
    _nudge_if_current(session, is_current)
    return cleaned


if __name__ == "__main__":
    print(lyrics_fetcher("假貴族", "門尼"))