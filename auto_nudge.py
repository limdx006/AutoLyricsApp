import asyncio
import threading
import time
from media_detect import get_playback_status, control_pause, control_play


def auto_nudge():
    """If media is playing, pause then resume after 0.5 s to force UI refresh.
    Does nothing when already paused.
    """
    try:
        status = asyncio.run(get_playback_status())
        if status == "playing":
            # pause
            asyncio.run(control_pause())
            # wait 0.5 s then resume
            time.sleep(0.5)
            asyncio.run(control_play())
    except Exception as e:
        print(f"Auto nudge failed: {e}")

def trigger_auto_nudge():
    """Run auto_nudge in a background daemon thread."""
    threading.Thread(target=auto_nudge, daemon=True).start()