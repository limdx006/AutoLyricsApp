import asyncio
import syncedlyrics
import time

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)

from lyrics_utils import parse_lrc, get_current_lyric_index


"""MEDIA SYNC - All mutable playback state lives here as module-level globals.
The two async loops (sync_song and progress_clock) read and write these variables.
The GUI is updated exclusively via root.after() to stay thread-safe."""

# CONFIG: Set your preferred lyric mode
# Options: "original", "romaji", "english" (english uses syncedlyrics lang="en")
LYRIC_MODE = "original" 

# Current track identity
current_title = None
current_artist = None
song_duration = 0

# Function to change lyric mode at runtime
def set_lyric_mode(mode):
    """Change the lyric mode and return True if successful."""
    global LYRIC_MODE
    if mode in ["original", "romaji", "english"]:
        LYRIC_MODE = mode
        return True
    return False

def get_lyric_mode():
    """Get the current lyric mode."""
    return LYRIC_MODE

# Timeline sync state
last_system_position = 0
last_sync_time = 0
local_position_at_sync = 0
last_accepted_system_pos = 0

# Pause tracking
is_paused = False
paused_position = 0
is_initialized = False

# Parsed lyrics for the current track
lyrics_lines = []


# Initialize romaji converter (lazy load to avoid import overhead if not needed)
_romaji_engine = None
_romaji_backend = None

def get_romaji_engine():
    """Lazy-load a romaji converter using cutlet first, then pykakasi."""
    global _romaji_engine, _romaji_backend
    if _romaji_engine is not None:
        return _romaji_engine

    try:
        import cutlet
        _romaji_engine = cutlet.Cutlet()
        _romaji_backend = "cutlet"
        return _romaji_engine
    except Exception as e:
        print("cutlet initialization failed, falling back to pykakasi:", e)

    try:
        from pykakasi import kakasi
        kakasi_obj = kakasi()
        kakasi_obj.setMode("J", "a")
        kakasi_obj.setMode("K", "a")
        kakasi_obj.setMode("H", "a")
        kakasi_obj.setMode("a", "a")
        kakasi_obj.setMode("s", True)
        _romaji_engine = kakasi_obj.getConverter()
        _romaji_backend = "pykakasi"
        print("Using pykakasi for romaji conversion")
        return _romaji_engine
    except Exception as e:
        print("pykakasi initialization failed:", e)
        _romaji_engine = None
        _romaji_backend = None
        return None


def convert_to_romaji(text):
    """Convert Japanese text to romaji using the available converter."""
    engine = get_romaji_engine()
    if not engine:
        return text

    try:
        if _romaji_backend == "cutlet":
            return engine.romaji(text)
        if _romaji_backend == "pykakasi":
            return engine.do(text)
    except Exception:
        pass

    return text


# High-precision async sleep for Windows
async def precise_sleep(sleep_for: float) -> None:
    await asyncio.get_running_loop().run_in_executor(None, time.sleep, sleep_for)


async def auto_nudge(session, sleep_delay: float = 0.02):
    """Force a pause/resume cycle to refresh the current media position."""
    await session.try_pause_async()
    await precise_sleep(sleep_delay)

    sessions = await MediaManager.request_async()
    session = sessions.get_current_session()
    if session:
        timeline = session.get_timeline_properties()
        system_pos = timeline.position.total_seconds()
    else:
        return None

    await session.try_play_async()
    await precise_sleep(sleep_delay)

    sessions = await MediaManager.request_async()
    session = sessions.get_current_session()
    if session:
        timeline = session.get_timeline_properties()
        return timeline.position.total_seconds()

    return system_pos


def get_synced_lyrics(query):
    """Fetch lyrics. If romaji mode, fetch original Japanese then convert."""
    try:
        # Fetch original lyrics (no lang parameter for reliability)
        lrc = syncedlyrics.search(query)
        
        if not lrc:
            return None
            
        # If romaji mode, convert each line to romaji
        if LYRIC_MODE == "romaji":
            lines = lrc.strip().split("\n")
            converted_lines = []
            
            for line in lines:
                # Parse the timestamp part [mm:ss.xx]
                import re
                match = re.match(r"(\[\d{2}:\d{2}\.\d{2,3}\])(.*)", line)
                if match:
                    timestamp = match.group(1)
                    text = match.group(2).strip()
                    romaji_text = convert_to_romaji(text)
                    converted_lines.append(f"{timestamp}{romaji_text}")
                else:
                    converted_lines.append(line)
            
            return "\n".join(converted_lines)
        
        # If english mode, try with lang parameter (may fail, fallback to original)
        elif LYRIC_MODE == "english":
            try:
                lrc_en = syncedlyrics.search(query, lang="en")
                if lrc_en:
                    return lrc_en
            except Exception:
                pass  # Fallback to original
            return lrc
        
        # Original mode — just return as-is
        else:
            return lrc
            
    except Exception:
        return None


async def _refresh_lyrics_async(app):
    """Refresh lyrics for the current song with the current LYRIC_MODE."""
    global lyrics_lines, current_title, current_artist, is_initialized
    
    if not current_title or not is_initialized:
        return
    
    app.root.after(0, lambda: app.update_status("Refreshing lyrics..."))
    
    query = f"{current_title} {current_artist}"
    lrc_text = get_synced_lyrics(query)
    
    if lrc_text:
        from lyrics_utils import parse_lrc
        lyrics_lines = parse_lrc(lrc_text)
        lyrics_snapshot = lyrics_lines.copy()
        app.root.after(0, lambda l=lyrics_snapshot: app.load_lyrics(l, -1))
    else:
        app.root.after(0, app.clear_lyrics)
    
    app.root.after(0, lambda: app.update_status("Ready"))


def register_lyric_mode_change(app, loop):
    """Register a callback for changing lyric mode from the GUI."""
    
    def on_mode_change(mode):
        if set_lyric_mode(mode):
            asyncio.run_coroutine_threadsafe(_refresh_lyrics_async(app), loop)
    
    # Store the callback on the app so the GUI can call it
    app.set_lyric_mode_callback = on_mode_change


async def _toggle_play_pause_async():
    sessions = await MediaManager.request_async()
    session = sessions.get_current_session()
    if session:
        await session.try_toggle_play_pause_async()


def register_pause_button(app, loop):
    """Wire the GUI pause button to the async toggle."""

    def on_click():
        asyncio.run_coroutine_threadsafe(_toggle_play_pause_async(), loop)

    app.set_pause_callback(on_click)


async def _next_song_async():
    sessions = await MediaManager.request_async()
    session = sessions.get_current_session()
    if session:
        await session.try_skip_next_async()


async def _prev_song_async():
    sessions = await MediaManager.request_async()
    session = sessions.get_current_session()
    if session:
        await session.try_skip_previous_async()


def register_next_prev_buttons(app, loop):
    """Wire the GUI next and previous buttons to their winsdk commands."""

    def on_next():
        asyncio.run_coroutine_threadsafe(_next_song_async(), loop)

    def on_prev():
        asyncio.run_coroutine_threadsafe(_prev_song_async(), loop)

    app.set_next_callback(on_next)
    app.set_prev_callback(on_prev)


def register_refresh_button(app, loop):
    """Wire the GUI refresh button to the async auto-nudge refresh."""

    def on_click():
        asyncio.run_coroutine_threadsafe(_refresh_sync_async(app), loop)

    app.set_refresh_callback(on_click)


async def _refresh_sync_async(app, sleep_delay: float = 0.1):
    sessions = await MediaManager.request_async()
    session = sessions.get_current_session()
    if not session:
        app.root.after(0, lambda: app.update_status("No media session"))
        return

    app.root.after(0, lambda: app.update_status("Refreshing..."))
    new_system_pos = await auto_nudge(session, sleep_delay=sleep_delay)

    if new_system_pos is not None:
        global last_system_position, last_sync_time, local_position_at_sync, last_accepted_system_pos
        last_system_position = new_system_pos
        last_sync_time = time.perf_counter()
        local_position_at_sync = new_system_pos
        last_accepted_system_pos = new_system_pos

    app.root.after(0, lambda: app.update_status("Ready"))


async def sync_song(app):
    global current_title, current_artist
    global song_duration, last_system_position, last_sync_time
    global local_position_at_sync, last_accepted_system_pos
    global is_paused, paused_position, is_initialized
    global lyrics_lines

    while True:
        sessions = await MediaManager.request_async()
        session = sessions.get_current_session()

        if session:
            info = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()
            playback_info = session.get_playback_info()
            status = playback_info.playback_status

            title = info.title
            artist = info.artist
            system_pos = timeline.position.total_seconds()
            duration = timeline.end_time.total_seconds()

            currently_playing = status == PlaybackStatus.PLAYING
            is_new_song = title != current_title or artist != current_artist

            if is_new_song:
                current_title = title
                current_artist = artist
                song_duration = duration
                is_paused = False
                lyrics_lines = []

                app.root.after(
                    0,
                    lambda t=title, a=artist, d=duration: app.update_song_info(t, a, d),
                )
                app.root.after(0, app.clear_lyrics)
                app.root.after(0, lambda: app.update_status("Loading lyrics..."))

                should_initialise = not is_initialized

                if should_initialise:
                    app.root.after(0, lambda: app.update_status("Syncing..."))
                    new_system_pos = await auto_nudge(session, sleep_delay=0.02)
                    if new_system_pos is not None:
                        system_pos = new_system_pos

                is_initialized = True
                last_system_position = system_pos
                last_sync_time = time.perf_counter()
                local_position_at_sync = system_pos
                last_accepted_system_pos = system_pos

                query = f"{title} {artist}"
                lrc_text = get_synced_lyrics(query)

                if lrc_text:
                    lyrics_lines = parse_lrc(lrc_text)
                else:
                    lyrics_lines = []

                if should_initialise and lyrics_lines:
                    start_index = get_current_lyric_index(
                        lyrics_lines, system_pos + 0.3
                    )
                else:
                    start_index = -1

                lyrics_snapshot = lyrics_lines.copy()
                app.root.after(
                    0, lambda l=lyrics_snapshot, i=start_index: app.load_lyrics(l, i)
                )
                app.root.after(0, lambda: app.update_status("Ready"))

            else:
                if not currently_playing and not is_paused:
                    is_paused = True
                    paused_position = local_position_at_sync + (
                        time.perf_counter() - last_sync_time
                    )
                    app.root.after(0, lambda: app.update_status("Paused"))
                    app.root.after(0, lambda: app.set_pause_button_state(True))

                elif currently_playing and is_paused:
                    is_paused = False
                    last_system_position = system_pos
                    last_sync_time = time.perf_counter()
                    local_position_at_sync = system_pos
                    last_accepted_system_pos = system_pos
                    app.root.after(0, lambda: app.update_status("Playing"))
                    app.root.after(0, lambda: app.set_pause_button_state(False))
                    continue

                if is_paused or not is_initialized:
                    pass
                else:
                    local_now = local_position_at_sync + (
                        time.perf_counter() - last_sync_time
                    )
                    delta_from_last_accepted = system_pos - last_accepted_system_pos

                    is_frozen = (
                        abs(delta_from_last_accepted) < 0.1
                        and local_now > last_accepted_system_pos + 2.0
                    )

                    is_significant_change = abs(delta_from_last_accepted) > 0.9

                    if is_frozen:
                        pass

                    elif is_significant_change:
                        drift_from_local = system_pos - local_now
                        is_auto_refresh = abs(drift_from_local) <= 3.0
                        is_user_seek = abs(drift_from_local) > 3.0

                        if is_auto_refresh or is_user_seek:
                            last_system_position = system_pos
                            last_sync_time = time.perf_counter()
                            local_position_at_sync = system_pos
                            last_accepted_system_pos = system_pos

                    else:
                        pass

        else:
            app.root.after(0, lambda: app.update_status("No media session"))

        await asyncio.sleep(0.5)


async def progress_clock(app):
    global local_position_at_sync, last_sync_time, is_paused, paused_position, is_initialized
    global lyrics_lines

    last_print = -1
    last_lyric_idx = -1

    while True:
        if current_title and is_initialized:
            if is_paused:
                elapsed = paused_position
            else:
                elapsed = local_position_at_sync + (
                    time.perf_counter() - last_sync_time
                )

            elapsed = min(elapsed, song_duration)

            if int(elapsed * 10) != int(last_print * 10):
                app.root.after(
                    0, lambda e=elapsed, d=song_duration: app.update_progress(e, d)
                )
                last_print = elapsed

            if lyrics_lines:
                lyric_elapsed = max(0, elapsed + app.lyric_offset)
                new_index = get_current_lyric_index(lyrics_lines, lyric_elapsed)

                if new_index != last_lyric_idx:
                    last_lyric_idx = new_index
                    app.root.after(0, lambda i=new_index: app.highlight_lyric(i))

        await precise_sleep(0.01)