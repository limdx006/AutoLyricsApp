import PyInstaller.__main__
import sys

PyInstaller.__main__.run([
    'main.py',                          # Entry point
    '--onefile',                        # Single .exe file
    '--windowed',                       # No console window (GUI app)
    '--name', 'LyricsPlayer',           # Output filename
    '--add-data', 'config.py;.',        # Include source files
    '--add-data', 'gui.py;.',
    '--add-data', 'lyrics_utils.py;.',
    '--add-data', 'media_sync.py;.',
    '--hidden-import', 'winsdk',        # Ensure winsdk is bundled
    '--hidden-import', 'syncedlyrics',
    '--hidden-import', 'tkinter',
    '--icon', 'icon.ico',
])