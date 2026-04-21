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
last_system_position = 0  # Position at time of last sync
last_sync_time = 0  # perf_counter() at time of last sync
max_seen_position = 0  # What our local timer calculated at last sync
last_accepted_system_pos = 0  # Track last position we actually accepted


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
    global song_duration, last_system_position, last_sync_time
    global local_position_at_sync, max_seen_position, last_accepted_system_pos

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
                max_seen_position = system_pos
                last_accepted_system_pos = system_pos

                print(f"\n\nNow Playing: {title} - {artist}")
                print(f"Starting at: {format_lrc_time(system_pos)} / {format_lrc_time(duration)}")

                query = f"{title} {artist}"
                lyrics = get_synced_lyrics(query)
                print("\n===== LYRICS =====\n")
                print(lyrics)
                print("\n===================\n")

            else:
                local_now = local_position_at_sync + (time.perf_counter() - last_sync_time)
                
                # Update max seen
                if system_pos > max_seen_position:
                    max_seen_position = system_pos
                
                # === STALE DETECTION RULES ===
                
                # Rule 1: Exact same position as last accepted = definitely stale
                is_exact_repeat = abs(system_pos - last_accepted_system_pos) < 0.1
                
                # Rule 2: Position is behind local timer but close to max_seen = stale cache
                looks_stale = (system_pos < local_now - 1.5) and (system_pos >= max_seen_position - 2.0)
                
                # Rule 3: New low we've never seen before = real backward seek
                is_fresh_low = system_pos < (last_accepted_system_pos - 3.0)
                
                if is_exact_repeat:
                    # Windows returning same cached frame — always ignore
                    print(f"[SYNC] IGNORE repeat | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | last_accepted={format_lrc_time(last_accepted_system_pos)}")
                    
                elif looks_stale and not is_fresh_low:
                    # Old cached position behind current playback
                    print(f"[SYNC] IGNORE stale | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | max_seen={format_lrc_time(max_seen_position)}")
                    
                elif abs(system_pos - local_now) > 1.5 or is_fresh_low:
                    # Real change: forward seek, backward seek to new position, or system catch-up
                    direction = "backward" if system_pos < local_now else "forward"
                    print(f"[SYNC] ACCEPT {direction} | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | delta={system_pos - local_now:+.2f}s")
                    
                    last_system_position = system_pos
                    last_sync_time = time.perf_counter()
                    local_position_at_sync = system_pos
                    last_accepted_system_pos = system_pos
                    if system_pos > max_seen_position:
                        max_seen_position = system_pos
                else:
                    # Normal playback
                    print(f"[SYNC] OK | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | drift={system_pos - local_now:+.2f}s")

        else:
            print("[SYNC] No active session found!")

        await asyncio.sleep(1)


# Fast local timer (0.1s)
async def progress_clock():
    global local_position_at_sync, last_sync_time

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
