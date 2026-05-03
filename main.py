import asyncio
import threading
import tkinter as tk
import os
import sys

from gui import LyricsApp
from media_sync import (
    sync_song,
    progress_clock,
    register_pause_button,
    register_next_prev_buttons,
    register_refresh_button,
    register_lyric_mode_change,
)


def _resource_path(filename):
    """Return the correct path to a bundled file whether running from source or as a PyInstaller exe."""
    if hasattr(sys, "_MEIPASS"):
        # Running inside a PyInstaller bundle — files are extracted to a temp folder
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.dirname(__file__), filename)


"""MAIN - Entry point. Creates the Tkinter window, starts the async media sync
loops on a background thread, then hands control to the Tkinter event loop."""


def main():
    root = tk.Tk()
    app = LyricsApp(root)

    # Set window icon (title bar + taskbar)
    icon_path = _resource_path("icon.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)

    loop = asyncio.new_event_loop()

    # Wire the pause, next, previous, and refresh buttons to the async loop before the thread starts
    register_pause_button(app, loop)
    register_next_prev_buttons(app, loop)
    register_refresh_button(app, loop)
    register_lyric_mode_change(app, loop)

    def run_async():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            asyncio.gather(
                sync_song(app),
                progress_clock(app),
            )
        )

    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()

    root.mainloop()


if __name__ == "__main__":
    main()
