import asyncio
import threading
import tkinter as tk

from gui import LyricsApp
from media_sync import sync_song, progress_clock


"""MAIN - Entry point. Creates the Tkinter window, starts the async media sync
loops on a background thread, then hands control to the Tkinter event loop."""


def main():
    root = tk.Tk()
    app = LyricsApp(root)

    loop = asyncio.new_event_loop()

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
