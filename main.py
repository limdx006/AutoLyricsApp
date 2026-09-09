r"""
LyricsPlayer - Auto-synced lyrics display application.

Citation for syncedlyrics library:
@misc{syncedlyrics,
  author = {Momeni, Mohammad},
  title = {syncedlyrics},
  year = {2022},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/moehmeni/syncedlyrics}},
}
"""

import asyncio
import threading
import tkinter as tk
import os
import sys

from lyrics_fetcher import lyrics_fetcher
from media_detect import detect_media
from gui import LyricsApp
from log_viewer import install_log_capture, apply_app_icon, configure_taskbar_identity

install_log_capture()  # tee stdout/stderr into the log buffer as early as possible


async def main():
    print("*****************************************************************")
    print("Welcome to LyricsPlayer - Auto-synced lyrics display application.")
    print("*****************************************************************")

    title, artist = await detect_media()

    # Display the GUI
    configure_taskbar_identity()
    root = tk.Tk()
    apply_app_icon(root)
    app = LyricsApp(root, title, artist)
    root.mainloop()

    print("****************************************************")
    print("Exit successfully, Thank you for using LyricsPlayer. ")
    print("****************************************************")


if __name__ == "__main__":
    asyncio.run(main())