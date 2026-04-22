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
def get_synced_lyrics(query):
    try:
        lrc = syncedlyrics.search(query)
        return lrc if lrc else "No lyrics found."
    except Exception as e:
        return f"Error: {e}"

async def sync_song():
    global current_title, current_artist
    global song_duration, last_system_position, last_sync_time
    global local_position_at_sync, last_accepted_system_pos
    global is_paused, paused_position

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
                last_accepted_system_pos = system_pos

                print(f"\n\nNow Playing: {title} - {artist}")
                print(f"Starting at: {format_lrc_time(system_pos)} / {format_lrc_time(duration)}")

                query = f"{title} {artist}"
                lyrics = get_synced_lyrics(query)
                print("\n===== LYRICS =====\n")
                print(lyrics)
                print("\n===================\n")

            else:
                # Handle pause state
                if not currently_playing and not is_paused:
                    is_paused = True
                    paused_position = local_position_at_sync + (time.perf_counter() - last_sync_time)
                    print(f"[SYNC] PAUSED at {format_lrc_time(paused_position)}")
                    
                elif currently_playing and is_paused:
                    is_paused = False
                    last_system_position = system_pos
                    last_sync_time = time.perf_counter()
                    local_position_at_sync = system_pos
                    last_accepted_system_pos = system_pos
                    print(f"[SYNC] RESUMED at {format_lrc_time(system_pos)} (was paused at {format_lrc_time(paused_position)})")
                    continue

                if is_paused:
                    print(f"[SYNC] PAUSED | sys={format_lrc_time(system_pos)} | paused_at={format_lrc_time(paused_position)}")
                    
                else:
                    local_now = local_position_at_sync + (time.perf_counter() - last_sync_time)
                    
                    # Calculate how much system position changed from last accepted
                    delta_from_last_accepted = system_pos - last_accepted_system_pos
                    
                    # === NEW LOGIC: 0.5s check with >0.9s threshold ===
                    
                    # 1. Exact same position as last accepted, local moved past it → frozen
                    is_frozen = (
                        abs(delta_from_last_accepted) < 0.1 
                        and local_now > last_accepted_system_pos + 2.0
                    )
                    
                    # 2. Position changed by >0.9s from last accepted → user interaction or auto-refresh
                    #    But we need to check if it's a realistic jump
                    is_significant_change = abs(delta_from_last_accepted) > 0.4
                    
                    # 3. If significant change, check if it's moving in same direction as time
                    #    AND close to what local timer expects → auto-refresh (ignore)
                    #    OR far from local timer → user seek (accept)
                    if is_frozen:
                        print(f"[SYNC] IGNORE frozen | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | last_accepted={format_lrc_time(last_accepted_system_pos)}")
                        
                    elif is_significant_change:
                        # Auto-refresh: system jumps forward by ~5-10s, but local timer is close
                        # User seek: system jumps to completely different position vs local timer
                        drift_from_local = system_pos - local_now
                        
                        # If system moved in same direction and local is within 2s → auto-refresh
                        is_auto_refresh = (
                            delta_from_last_accepted > 0  # Moved forward
                            and abs(drift_from_local) < 2.0  # Close to local timer
                        )
                        
                        # If system moved backward, or jumped far from local → user seek
                        is_user_seek = (
                            delta_from_last_accepted < 0  # Backward
                            or abs(drift_from_local) > 2.0  # Far from local
                        )
                        
                        if is_auto_refresh:
                            print(f"[SYNC] IGNORE refresh | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | delta_from_last={delta_from_last_accepted:+.2f}s")
                            
                        elif is_user_seek:
                            direction = "backward" if delta_from_last_accepted < 0 else "forward"
                            print(f"[SYNC] ACCEPT {direction} | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | delta={delta_from_last_accepted:+.2f}s")
                            
                            last_system_position = system_pos
                            last_sync_time = time.perf_counter()
                            local_position_at_sync = system_pos
                            last_accepted_system_pos = system_pos
                        else:
                            print(f"[SYNC] AMBIGUOUS | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | drift={drift_from_local:+.2f}s")
                            
                    else:
                        # Small change (<0.9s) → ignore, trust local timer
                        print(f"[SYNC] OK | sys={format_lrc_time(system_pos)} | local={format_lrc_time(local_now)} | drift={system_pos - local_now:+.2f}s")

        else:
            print("[SYNC] No active session found!")

        await asyncio.sleep(0.5)




async def progress_clock():
    global local_position_at_sync, last_sync_time, is_paused, paused_position

    last_print = -1

    while True:
        if current_title:
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

        await precise_sleep(0.01)  # Sleep for 100ms to reduce CPU usage while keeping smooth updates

async def main():
    await asyncio.gather(sync_song(), progress_clock())


asyncio.run(main())
