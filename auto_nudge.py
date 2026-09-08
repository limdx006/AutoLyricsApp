import asyncio
import threading
import time
from media_detect import get_playback_status, control_pause, control_play


def auto_nudge(duration):
    """If media is playing, pause then resume after the specified duration to force UI refresh.
    Does nothing when already paused.
    """
    try:
        status = asyncio.run(get_playback_status())
        if status == "playing":
            print("[Nudge] Attempt auto nudge")
            # pause
            asyncio.run(control_pause())
            # wait for the specified duration then resume
            time.sleep(duration)
            asyncio.run(control_play())
            time.sleep(0.5)  # Give the media player a moment to update its state
            status = asyncio.run(get_playback_status())
            if status == "playing":
                print("[Nudge] Resume successfully")
            else:
                print("[Nudge] Resume failed")
                print("[Nudge] Retrying auto nudge")
                trigger_auto_nudge(0.5)  # Retry if resume failed
    except Exception as e:
        print(f"[Nudge] Auto nudge failed: {e}")

def trigger_auto_nudge(duration=0.3):
    """Run auto_nudge in a background daemon thread."""
    threading.Thread(target=auto_nudge, args=(duration,), daemon=True).start()