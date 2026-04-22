import asyncio
import syncedlyrics
import tkinter as tk
import time
import re
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)

# Global variable
current_title = None
current_artist = None
song_duration = 0
last_system_position = 0  # Position at time of last sync
last_sync_time = 0  # perf_counter() at time of last sync
max_seen_position = 0  # What our local timer calculated at last sync
last_accepted_system_pos = 0  # Track last position we actually accepted
# Pause tracking
is_paused = False
paused_position = 0
pause_start_time = 0
is_initialized = False
# Lyrics tracking
lyrics_lines = []  # List of (timestamp_seconds, text) tuples
current_lyric_index = -1


# Format time as LRC
def format_lrc_time(seconds):
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"[{minutes:02d}:{secs:05.2f}]"


# Parse LRC format
def parse_lrc(lrc_text):
    """Parse LRC format into list of (timestamp_seconds, text) tuples."""
    lines = []
    pattern = r"\[(\d{2}):(\d{2}\.\d{2,3})\](.*)"

    for line in lrc_text.strip().split("\n"):
        match = re.match(pattern, line.strip())
        if match:
            minutes = int(match.group(1))
            seconds = float(match.group(2))
            timestamp = minutes * 60 + seconds
            text = match.group(3).strip()
            if text:
                lines.append((timestamp, text))

    # Sort by timestamp
    lines.sort(key=lambda x: x[0])
    return lines


# Load lyrics into global variable
def get_current_lyric_index(position):
    """Find the lyric index that should be displayed at given position."""
    if not lyrics_lines:
        return -1

    # Find the last lyric whose timestamp is <= current position
    index = -1
    for i, (timestamp, _) in enumerate(lyrics_lines):
        if timestamp <= position:
            index = i
        else:
            break

    return index


# Update displayed lyrics based on current position
def display_lyrics(current_index):
    """Display current lyric and surrounding lines."""
    if not lyrics_lines or current_index < 0:
        return

    # Show previous, current, and next lines
    lines_to_show = []
    for offset in [-1, 0, 1]:
        idx = current_index + offset
        if 0 <= idx < len(lyrics_lines):
            timestamp, text = lyrics_lines[idx]
            prefix = "  " if offset == -1 else ">>" if offset == 0 else "  "
            lines_to_show.append(f"{prefix} [{format_lrc_time(timestamp)}] {text}")

    # Clear previous lyrics and print new ones
    print("\033[2K\033[1G", end="")  # Clear line
    print("\n".join(lines_to_show))


# High-precision async sleep for Windows (avoids 15ms asyncio granularity)
async def precise_sleep(sleep_for: float) -> None:
    await asyncio.get_running_loop().run_in_executor(None, time.sleep, sleep_for)


# Get lyrics
def get_synced_lyrics(query):
    try:
        lrc = syncedlyrics.search(query)
        return lrc if lrc else "No lyrics found."
    except Exception as e:
        return f"Error: {e}"


# Sync song timing
async def sync_song():
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

                print(f"\n\nNow Playing: {title} - {artist}")
                print(f"Duration: {format_lrc_time(duration)}")

                needs_init_wait = not is_initialized and system_pos > 5.0

                if needs_init_wait:
                    print(
                        "Waiting for first sync... (drag timeline or pause/resume to refresh)"
                    )

                    initial_pos = system_pos
                    await asyncio.sleep(0.5)

                    while True:
                        sessions = await MediaManager.request_async()
                        session = sessions.get_current_session()
                        if session:
                            timeline = session.get_timeline_properties()
                            new_pos = timeline.position.total_seconds()

                            if abs(new_pos - initial_pos) > 0.9:
                                system_pos = new_pos
                                is_initialized = True
                                print(
                                    f"First sync received: {format_lrc_time(system_pos)}"
                                )
                                break
                            else:
                                print(
                                    f"\rWaiting... sys={format_lrc_time(new_pos)} | initial={format_lrc_time(initial_pos)}",
                                    end="",
                                    flush=True,
                                )

                        await asyncio.sleep(0.5)

                    print()
                else:
                    is_initialized = True
                    print(f"Starting at: {format_lrc_time(system_pos)}")

                last_system_position = system_pos
                last_sync_time = time.perf_counter()
                local_position_at_sync = system_pos
                last_accepted_system_pos = system_pos

                # Fetch and parse lyrics
                query = f"{title} {artist}"
                lrc_text = get_synced_lyrics(query)
                lyrics_lines = parse_lrc(lrc_text)

                print("\n===== LYRICS =====\n")
                if lyrics_lines:
                    print(f"Loaded {len(lyrics_lines)} lyric lines")
                else:
                    print("No synced lyrics found")
                print("\n===================\n")

            else:
                if not currently_playing and not is_paused:
                    is_paused = True
                    paused_position = local_position_at_sync + (
                        time.perf_counter() - last_sync_time
                    )
                    print(f"[SYNC] PAUSED at {format_lrc_time(paused_position)}")

                elif currently_playing and is_paused:
                    is_paused = False
                    last_system_position = system_pos
                    last_sync_time = time.perf_counter()
                    local_position_at_sync = system_pos
                    last_accepted_system_pos = system_pos
                    print(
                        f"[SYNC] RESUMED at {format_lrc_time(system_pos)} (was paused at {format_lrc_time(paused_position)})"
                    )
                    continue

                if is_paused:
                    print(
                        f"[SYNC] PAUSED | sys={format_lrc_time(system_pos)} | paused_at={format_lrc_time(paused_position)}"
                    )

                elif not is_initialized:
                    print(
                        f"\rWaiting for first sync... sys={format_lrc_time(system_pos)}",
                        end="",
                        flush=True,
                    )

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
                        print(
                            f"[SYNC] IGNORE frozen | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | last_accepted={format_lrc_time(last_accepted_system_pos)}"
                        )

                    elif is_significant_change:
                        drift_from_local = system_pos - local_now
                        is_auto_refresh = abs(drift_from_local) <= 3.0
                        is_user_seek = abs(drift_from_local) > 3.0

                        if is_auto_refresh:
                            print(
                                f"[SYNC] REFRESH | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | drift={drift_from_local:+.2f}s"
                            )
                            last_system_position = system_pos
                            last_sync_time = time.perf_counter()
                            local_position_at_sync = system_pos
                            last_accepted_system_pos = system_pos

                        elif is_user_seek:
                            direction = (
                                "backward"
                                if delta_from_last_accepted < 0
                                else "forward"
                            )
                            print(
                                f"[SYNC] ACCEPT {direction} | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | delta={delta_from_last_accepted:+.2f}s"
                            )
                            last_system_position = system_pos
                            last_sync_time = time.perf_counter()
                            local_position_at_sync = system_pos
                            last_accepted_system_pos = system_pos

                    else:
                        print(
                            f"[SYNC] OK | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | drift={system_pos - local_now:+.2f}s"
                        )

        else:
            print("[SYNC] No active session found!")

        await asyncio.sleep(0.5)  # Check every 500ms for updates


async def progress_clock():
    global local_position_at_sync, last_sync_time, is_paused, paused_position, is_initialized
    global current_lyric_index

    last_print = -1
    last_lyric_print = -1

    while True:
        if current_title and is_initialized:
            if is_paused:
                elapsed = paused_position
            else:
                elapsed = local_position_at_sync + (
                    time.perf_counter() - last_sync_time
                )

            elapsed = min(elapsed, song_duration)

            # Update timer display
            if int(elapsed * 10) != int(last_print * 10):
                status_indicator = " ⏸" if is_paused else ""
                print(
                    f"\r{format_lrc_time(elapsed)} / {format_lrc_time(song_duration)}{status_indicator}",
                    end="",
                    flush=True,
                )
                last_print = elapsed

            # Update lyrics display
            if lyrics_lines:
                new_index = get_current_lyric_index(elapsed)
                if new_index != current_lyric_index:
                    current_lyric_index = new_index
                    # Print lyrics below the timer
                    print()  # New line after timer
                    display_lyrics(current_lyric_index)
                    # Reprint timer on next line
                    print(
                        f"\r{format_lrc_time(elapsed)} / {format_lrc_time(song_duration)}{status_indicator}",
                        end="",
                        flush=True,
                    )

        await precise_sleep(0.1)  # Check lyrics every 100ms for smooth updates


async def main():
    await asyncio.gather(sync_song(), progress_clock())


asyncio.run(main())
