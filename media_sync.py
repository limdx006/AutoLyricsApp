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

# Current track identity
current_title = None
current_artist = None
song_duration = 0

# Timeline sync state
last_system_position = 0  # Position at time of last sync
last_sync_time = 0  # perf_counter() at time of last sync
local_position_at_sync = 0  # Local mirror of position at last sync point
last_accepted_system_pos = 0

# Pause tracking
is_paused = False
paused_position = 0
pause_start_time = 0
is_initialized = False

# Parsed lyrics for the current track
lyrics_lines = []  # List of (timestamp_seconds, text) tuples
current_lyric_index = -1


# High-precision async sleep for Windows (avoids 15ms asyncio granularity)
async def precise_sleep(sleep_for: float) -> None:
    await asyncio.get_running_loop().run_in_executor(None, time.sleep, sleep_for)


# Fetch synced LRC lyrics for a search query
def get_synced_lyrics(query):
    try:
        lrc = syncedlyrics.search(query)
        return lrc if lrc else "No lyrics found."
    except Exception as e:
        return f"Error: {e}"


async def _toggle_play_pause_async():
    # Send a play/pause toggle to the current media session
    sessions = await MediaManager.request_async()
    session = sessions.get_current_session()
    if session:
        await session.try_toggle_play_pause_async()


def register_pause_button(app, loop):
    """Wire the GUI pause button to the async toggle so clicking it controls the media session.
    Called once from main.py after the event loop is created but before the thread starts."""
    def on_click():
        asyncio.run_coroutine_threadsafe(_toggle_play_pause_async(), loop)

    app.set_pause_callback(on_click)


"""SYNC SONG - Polls the Windows media session every 500ms to detect song changes,
pause/resume events, and user seeks. Updates globals and schedules GUI refreshes.
The timeline correction logic below must not be modified — it handles the irregular
update cadence of the Windows media session API."""


async def sync_song(app):
    global current_title, current_artist
    global song_duration, last_system_position, last_sync_time
    global local_position_at_sync, last_accepted_system_pos
    global is_paused, paused_position, is_initialized
    global lyrics_lines, current_lyric_index

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
                current_lyric_index = -1

                # Refresh song header and clear old lyrics immediately
                app.root.after(
                    0,
                    lambda t=title, a=artist, d=duration: app.update_song_info(t, a, d),
                )
                app.root.after(0, app.clear_lyrics)
                app.root.after(0, lambda: app.update_status("Loading lyrics..."))

                needs_init_wait = not is_initialized and system_pos > 5.0

                if needs_init_wait:
                    app.root.after(0, lambda: app.update_status("Syncing..."))

                    """AUTO NUDGE - Windows only updates the media session timeline position
                    when playback state changes (play/pause/seek). On app startup the position
                    can be stale or zero. Sending a quick pause then immediate resume forces
                    Windows to flush a fresh position value we can trust for syncing."""
                    await session.try_pause_async()
                    await asyncio.sleep(0.2)

                    sessions = await MediaManager.request_async()
                    session = sessions.get_current_session()
                    if session:
                        timeline = session.get_timeline_properties()
                        system_pos = timeline.position.total_seconds()

                    await session.try_play_async()
                    await asyncio.sleep(0.2)

                    sessions = await MediaManager.request_async()
                    session = sessions.get_current_session()
                    if session:
                        timeline = session.get_timeline_properties()
                        system_pos = timeline.position.total_seconds()

                    is_initialized = True
                else:
                    is_initialized = True

                last_system_position = system_pos
                last_sync_time = time.perf_counter()
                local_position_at_sync = system_pos
                last_accepted_system_pos = system_pos

                # Fetch and parse lyrics, then hand them to the GUI
                query = f"{title} {artist}"
                lrc_text = get_synced_lyrics(query)
                lyrics_lines = parse_lrc(lrc_text)

                app.root.after(0, lambda l=lyrics_lines: app.load_lyrics(l))
                app.root.after(0, lambda: app.update_status("Ready"))

            else:
                # pause detection
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

                # timeline correction (do not modify)
                if is_paused:
                    pass

                elif not is_initialized:
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

                        if is_auto_refresh:
                            last_system_position = system_pos
                            last_sync_time = time.perf_counter()
                            local_position_at_sync = system_pos
                            last_accepted_system_pos = system_pos

                        elif is_user_seek:
                            last_system_position = system_pos
                            last_sync_time = time.perf_counter()
                            local_position_at_sync = system_pos
                            last_accepted_system_pos = system_pos

                    else:
                        pass

        else:
            app.root.after(0, lambda: app.update_status("No media session"))

        await asyncio.sleep(0.5)


"""PROGRESS CLOCK - Runs at 10ms intervals to keep the progress bar and lyric highlight
smooth. Reads the shared timeline globals set by sync_song and pushes GUI updates via
root.after(). Does not call any media APIs directly."""


async def progress_clock(app):
    global local_position_at_sync, last_sync_time, is_paused, paused_position, is_initialized
    global current_lyric_index

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

            # Update progress bar every 100ms
            if int(elapsed * 10) != int(last_print * 10):
                app.root.after(
                    0, lambda e=elapsed, d=song_duration: app.update_progress(e, d)
                )
                last_print = elapsed

            # Advance lyric highlight with +0.3s offset to compensate for sync delay
            if lyrics_lines:
                lyric_elapsed = max(0, elapsed + 0.3)
                new_index = get_current_lyric_index(lyrics_lines, lyric_elapsed)
                if new_index != last_lyric_idx:
                    last_lyric_idx = new_index
                    app.root.after(0, lambda i=new_index: app.highlight_lyric(i))

        await precise_sleep(0.01)  # 10ms for smooth UI updates