import asyncio
import syncedlyrics
import tkinter as tk
import time
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
is_paused = False
paused_position = 0
pause_start_time = 0


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
    global is_paused, paused_position, pause_start_time

    while True:
        sessions = await MediaManager.request_async()
        session = sessions.get_current_session()

        if session:
            info = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()
            
            # Get playback status
            playback_info = session.get_playback_info()
            status = playback_info.playback_status

            title = info.title
            artist = info.artist
            system_pos = timeline.position.total_seconds()
            duration = timeline.end_time.total_seconds()

            # Detect pause/resume
            currently_playing = (status == PlaybackStatus.PLAYING)
            
            # Song changed
            if title != current_title or artist != current_artist:
                current_title = title
                current_artist = artist
                song_duration = duration
                is_paused = False
                
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
                # NEW: Handle pause state
                if not currently_playing and not is_paused:
                    # Just paused
                    is_paused = True
                    paused_position = local_position_at_sync + (time.perf_counter() - last_sync_time)
                    pause_start_time = time.perf_counter()
                    print(f"[SYNC] PAUSED at {format_lrc_time(paused_position)}")
                    
                elif currently_playing and is_paused:
                    # Just resumed
                    is_paused = False
                    # Reset sync baseline to the paused position
                    last_system_position = system_pos
                    last_sync_time = time.perf_counter()
                    local_position_at_sync = paused_position
                    last_accepted_system_pos = system_pos
                    print(f"[SYNC] RESUMED at {format_lrc_time(paused_position)} (system={format_lrc_time(system_pos)})")
                    continue  # Skip rest of loop, already synced

                # If paused, don't do stale detection — frozen position is expected
                if is_paused:
                    print(f"[SYNC] PAUSED | sys={format_lrc_time(system_pos)} | paused_at={format_lrc_time(paused_position)}")
                    
                else:
                    # Normal playback logic
                    local_now = local_position_at_sync + (time.perf_counter() - last_sync_time)
                    
                    if system_pos > max_seen_position:
                        max_seen_position = system_pos
                    
                    is_exact_repeat = abs(system_pos - last_accepted_system_pos) < 0.1
                    looks_stale = (system_pos < local_now - 1.5) and (system_pos >= max_seen_position - 2.0)
                    is_fresh_low = system_pos < (last_accepted_system_pos - 3.0)
                    
                    if is_exact_repeat:
                        print(f"[SYNC] IGNORE repeat | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | last_accepted={format_lrc_time(last_accepted_system_pos)}")
                        
                    elif looks_stale and not is_fresh_low:
                        print(f"[SYNC] IGNORE stale | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | max_seen={format_lrc_time(max_seen_position)}")
                        
                    elif abs(system_pos - local_now) > 1.5 or is_fresh_low:
                        direction = "backward" if system_pos < local_now else "forward"
                        print(f"[SYNC] ACCEPT {direction} | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | delta={system_pos - local_now:+.2f}s")
                        
                        last_system_position = system_pos
                        last_sync_time = time.perf_counter()
                        local_position_at_sync = system_pos
                        last_accepted_system_pos = system_pos
                        if system_pos > max_seen_position:
                            max_seen_position = system_pos
                    else:
                        print(f"[SYNC] OK | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | drift={system_pos - local_now:+.2f}s")

        else:
            print("[SYNC] No active session found!")

        await asyncio.sleep(1)

# Fast local timer (0.1s)
async def progress_clock():
    global local_position_at_sync, last_sync_time, is_paused, paused_position

    last_print = -1

    while True:
        if current_title:
            # If paused, show frozen position instead of advancing
            if is_paused:
                elapsed = paused_position
            else:
                elapsed = local_position_at_sync + (time.perf_counter() - last_sync_time)
            
            elapsed = min(elapsed, song_duration)

            if int(elapsed * 10) != int(last_print * 10):
                status_indicator = " ⏸" if is_paused else ""
                print(
                    f"\r{format_lrc_time(elapsed)} / {format_lrc_time(song_duration)}{status_indicator}",
                    end="",
                    flush=True
                )
                last_print = elapsed

        await precise_sleep(0.01)


async def main():
    await asyncio.gather(sync_song(), progress_clock())


asyncio.run(main())
