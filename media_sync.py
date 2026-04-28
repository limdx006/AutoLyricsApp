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
is_initialized = False

# Parsed lyrics for the current track
lyrics_lines = []


# High-precision async sleep for Windows (avoids 15ms asyncio granularity)
async def precise_sleep(sleep_for: float) -> None:
    await asyncio.get_running_loop().run_in_executor(None, time.sleep, sleep_for)


# Fetch synced LRC lyrics for a search query
def get_synced_lyrics(query):
    try:
        lrc = syncedlyrics.search(query)
        return (
            lrc if lrc else None
        )  # Return None instead of string for cleaner handling
    except Exception:
        return None


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
    # Send a skip-to-next command to the current media session
    sessions = await MediaManager.request_async()
    session = sessions.get_current_session()
    if session:
        await session.try_skip_next_async()


async def _prev_song_async():
    # Send a skip-to-previous command to the current media session
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


"""SYNC SONG - Polls the Windows media session every 500ms to detect song changes,
pause/resume events, and user seeks. Updates globals and schedules GUI refreshes.
The timeline correction logic below must not be modified — it handles the irregular
update cadence of the Windows media session API."""


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

                    # Auto-nudge: pause then resume to force fresh position
                    await session.try_pause_async()
                    await asyncio.sleep(0.01)

                    sessions = await MediaManager.request_async()
                    session = sessions.get_current_session()
                    if session:
                        timeline = session.get_timeline_properties()
                        system_pos = timeline.position.total_seconds()

                    await session.try_play_async()
                    await asyncio.sleep(0.01)

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

                # Handle None return cleanly
                if lrc_text:
                    lyrics_lines = parse_lrc(lrc_text)
                else:
                    lyrics_lines = []

                # Calculate the correct starting lyric index after nudge sync
                if needs_init_wait and lyrics_lines:
                    start_index = get_current_lyric_index(lyrics_lines, system_pos + 0.3)
                else:
                    start_index = -1

                # Pass a COPY of lyrics_lines and the starting index to avoid race condition
                lyrics_snapshot = lyrics_lines.copy()
                app.root.after(
                    0, lambda l=lyrics_snapshot, i=start_index: app.load_lyrics(l, i)
                )
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

            # Update progress bar every 100ms
            if int(elapsed * 10) != int(last_print * 10):
                app.root.after(
                    0, lambda e=elapsed, d=song_duration: app.update_progress(e, d)
                )
                last_print = elapsed

            # Advance lyric highlight with +0.3s offset
            if lyrics_lines:
                lyric_elapsed = max(0, elapsed + 0.3)
                new_index = get_current_lyric_index(lyrics_lines, lyric_elapsed)

                # Always update if index changed, including first sync after init
                if new_index != last_lyric_idx:
                    last_lyric_idx = new_index
                    app.root.after(0, lambda i=new_index: app.highlight_lyric(i))

        await precise_sleep(0.01)