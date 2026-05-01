import PyInstaller.__main__

PyInstaller.__main__.run([
    'main.py',                          # Entry point
    '--onefile',                        # Single .exe file
    '--windowed',                       # No console window (GUI app)
    '--name', 'LyricsPlayer',           # Output filename
    
    # Source files
    '--add-data', 'config.py;.',
    '--add-data', 'gui.py;.',
    '--add-data', 'lyrics_utils.py;.',
    '--add-data', 'media_sync.py;.',
    
    # Icon: bundle as data AND embed in exe
    '--add-data', 'icon.ico;.',         # Runtime access
    '--icon', 'icon.ico',               # Embedded in .exe resources
    
    # Hidden imports
    '--hidden-import', 'winsdk',
    '--hidden-import', 'syncedlyrics',
    '--hidden-import', 'tkinter',
    '--hidden-import', 'cutlet',
    '--hidden-import', 'pykakasi',
    '--hidden-import', 'fugashi',
    '--hidden-import', 'unidic_lite',

    # Ensure all package data for romaji conversion is bundled
    '--collect-data', 'pykakasi',
    '--collect-data', 'unidic_lite',
    '--collect-data', 'cutlet',
    '--collect-data', 'fugashi',
])