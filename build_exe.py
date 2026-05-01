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
    
    # Hidden imports - core libraries
    '--hidden-import', 'winsdk',
    '--hidden-import', 'syncedlyrics',
    '--hidden-import', 'tkinter',
    
    # Hidden imports - romaji conversion
    '--hidden-import', 'cutlet',
    '--hidden-import', 'pykakasi',
    
    # Hidden imports - unidic-lite dependencies (CRITICAL for cutlet)
    '--hidden-import', 'fugashi',
    '--hidden-import', 'fugashi._fugashi',
    '--hidden-import', 'fugashi._fugashi_legacy',
    '--hidden-import', 'unidic_lite',
    '--hidden-import', 'mecab',
    '--hidden-import', 'mecabrc',
    
    # Collect ALL package data for romaji converters and dependencies
    '--collect-data', 'unidic_lite',    # Dictionary files for cutlet
    '--collect-data', 'fugashi',        # MeCab config/data
    '--collect-data', 'cutlet',         # Cutlet data files
    '--collect-data', 'pykakasi',       # Pykakasi data files (fallback)
    
    # Collect binaries (compiled C extensions) for fugashi/mecab
    '--collect-binaries', 'fugashi',
    '--collect-binaries', 'mecab',
    
    # Collect submodules that might be dynamically imported
    '--collect-submodules', 'unidic_lite',
    '--collect-submodules', 'fugashi',
    '--collect-submodules', 'cutlet',
    '--collect-submodules', 'pykakasi',
])