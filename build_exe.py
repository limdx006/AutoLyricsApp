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
    '--hidden-import', 'fugashi',
    '--hidden-import', 'unidic_lite',

    # Hidden imports - pinyin conversion
    '--hidden-import', 'pypinyin',

    # Hidden imports - Korean romanization
    '--hidden-import', 'korean_romanizer',

    # Collect ALL package data for unidic-lite and its dependencies
    # This ensures the dictionary files are bundled
    '--collect-data', 'unidic_lite',
    '--collect-data', 'fugashi',
    '--collect-data', 'cutlet',
    '--collect-data', 'pykakasi',
    '--collect-data', 'pypinyin',
    '--collect-data', 'korean_romanizer',

    # Also collect binaries (compiled C extensions) for fugashi/mecab
    '--collect-binaries', 'fugashi',
    '--collect-binaries', 'mecab',

    # Collect submodules that might be dynamically imported
    '--collect-submodules', 'unidic_lite',
    '--collect-submodules', 'fugashi',
    '--collect-submodules', 'cutlet',
    '--collect-submodules', 'pykakasi',
    '--collect-submodules', 'pypinyin',
    '--collect-submodules', 'korean_romanizer',
])