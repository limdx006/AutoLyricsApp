import asyncio
import syncedlyrics
import tkinter as tk
import time
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)

# Global variable
current_title = None
current_artist = None
song_duration = 0
last_system_position = 0      # Position at time of last sync
last_sync_time = 0            # perf_counter() at time of last sync
local_position_at_sync = 0    # What our local timer calculated at last sync


# Format time as LRC
def format_lrc_time(seconds):
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"[{minutes:02d}:{secs:05.2f}]"


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


# Sync song timing every 10s
async def sync_song():
    global current_title, current_artist
    global song_duration, last_system_position, last_sync_time, local_position_at_sync

    while True:
        sessions = await MediaManager.request_async()
        session = sessions.get_current_session()

        if session:
            info = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()

            title = info.title
            artist = info.artist
            system_pos = timeline.position.total_seconds()
            duration = timeline.end_time.total_seconds()

            # Song changed
            if title != current_title or artist != current_artist:
                current_title = title
                current_artist = artist
                song_duration = duration
                
                last_system_position = system_pos
                last_sync_time = time.perf_counter()
                local_position_at_sync = system_pos

                print(f"\n\nNow Playing: {title} - {artist}")
                print(f"Starting at: {format_lrc_time(system_pos)} / {format_lrc_time(duration)}")

                query = f"{title} {artist}"
                lyrics = get_synced_lyrics(query)
                print("\n===== LYRICS =====\n")
                print(lyrics)
                print("\n===================\n")

            else:
                # Calculate what our local timer thinks the position should be
                local_now = local_position_at_sync + (time.perf_counter() - last_sync_time)
                
                # PHYSICAL IMPOSSIBILITY CHECK:
                # If 5 seconds passed locally, system position MUST be >= local_now - 2s
                # (allowing 2s tolerance for normal drift)
                # If system_pos is way BELOW local_now, it's stale cached data — IGNORE
                
                min_expected_pos = local_now - 2.0  # Minimum realistic position
                
                if system_pos < min_expected_pos:
                    # Stale data! System returned old cached position. Ignore it.
                    # Don't print to avoid spam, or use debug mode
                    pass
                    
                elif abs(system_pos - local_now) > 3.0:
                    # Large positive jump = user seeked forward, or system finally updated
                    # after being stale for a while. Accept it.
                    last_system_position = system_pos
                    last_sync_time = time.perf_counter()
                    local_position_at_sync = system_pos
                    # print(f"[SYNC] Jump to {format_lrc_time(system_pos)}")  # optional

        await asyncio.sleep(1) 

# Fast local timer (0.1s)
async def progress_clock():
    global last_system_position, last_sync_time, local_position_at_sync

    last_print = -1

    while True:
        if current_title:
            elapsed = local_position_at_sync + (time.perf_counter() - last_sync_time)
            elapsed = min(elapsed, song_duration)

            if int(elapsed * 10) != int(last_print * 10):
                print(
                    f"\r{format_lrc_time(elapsed)} / {format_lrc_time(song_duration)}",
                    end="",
                    flush=True
                )
                last_print = elapsed

        await precise_sleep(0.01)


async def main():
    await asyncio.gather(sync_song(), progress_clock())


asyncio.run(main())
