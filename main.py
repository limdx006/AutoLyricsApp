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



async def main():
    print("*****************************************************************")
    print("Welcome to LyricsPlayer - Auto-synced lyrics display application.")
    print("*****************************************************************")

    # title, artist = await detect_media()
    # lyrics_fetcher(title, artist)

    # Display the GUI
    root = tk.Tk()
    app = LyricsApp(root)
    root.mainloop()

    print("****************************************************")
    print("Exit successfully, Thank you for using LyricsPlayer. ")
    print("****************************************************")
        

if __name__ == "__main__":
    asyncio.run(main())
