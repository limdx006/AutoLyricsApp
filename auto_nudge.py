import asyncio
import threading
import time
from media_detect import (
    get_playback_status, control_pause, control_play,
    get_status_for_session, control_pause_session, control_play_session,
)


def auto_nudge(duration, session=None):
    """
    If media is playing, pause then resume after the specified duration to force UI refresh.
    Does nothing when already paused.
    """
    if session is not None:
        get_status = lambda: get_status_for_session(session)
        pause = lambda: control_pause_session(session)
        play = lambda: control_play_session(session)
    else:
        get_status = get_playback_status
        pause = control_pause
        play = control_play

    try:
        status = asyncio.run(get_status())
        if status == "playing":
            print("[Nudge] Attempt auto nudge")
            # pause
            asyncio.run(pause())
            # wait for the specified duration then resume
            time.sleep(duration)
            asyncio.run(play())
            time.sleep(0.5)  # Give the media player a moment to update its state
            status = asyncio.run(get_status())
            if status == "playing":
                print("[Nudge] Resume successfully")
            else:
                print("[Nudge] Resume failed")
                print("[Nudge] Retrying auto nudge")
                trigger_auto_nudge(0.5, session)  # Retry if resume failed, on the same session
    except Exception as e:
        print(f"[Nudge] Auto nudge failed: {e}")

def trigger_auto_nudge(duration=0.3, session=None):
    """Run auto_nudge in a background daemon thread."""
    threading.Thread(target=auto_nudge, args=(duration, session), daemon=True).start()