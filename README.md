# 🎵 AutoLyricsApp

A real-time desktop lyrics player built with Python that detects the currently playing music on Windows and displays **synchronised (LRC) lyrics** with smooth animations and a modern GUI.

---

## 🖼 UI Overview

<div style="display: flex; gap: 10px;">
  <img width="499" height="999" alt="image" src="https://github.com/user-attachments/assets/f81236d6-ba12-4f6a-b465-139614502653" />
</div>

---

## ✨ Features

### 🎧 Media Detection
- Auto-detects currently playing music from Windows Media session
- Works with Spotify, YouTube (browser), and other apps that expose system media controls
- Detects song changes, pause/resume, and user seeks automatically

### ⏱ High-Precision Playback Tracking
- Combines Windows Media session data with a local `perf_counter()` timer
- Handles drift, frozen position states, and irregular Windows update cadence
- **Auto-nudge on startup** — performs a silent pause/resume cycle to force Windows to flush a fresh timeline position, ensuring lyrics sync correctly from the moment the app launches

### 📜 Synchronised Lyrics
- Fetches timestamped LRC lyrics automatically via the `syncedlyrics` library
- Parses and aligns lyrics to the current playback position in real time
- Adjustable **lyric offset** (±0.1s steps) to fine-tune sync per song
- Lyric offset resets to default on each new song

### 🖥 GUI (Tkinter)
- Clean dark theme
- **Song info panel** — title and artist with wrap support for long names
- **Scrolling lyrics panel** — centred, auto-scrolling, no scrollbar
- **Transport controls** — previous (◀◀), pause/resume (▌▌ / ▶), next (▶▶) buttons
- **Progress bar** — live red fill with current and total time flanking the controls
- **Refresh button (⟳)** — manually triggers a re-sync nudge mid-song
- **Settings button (⚙)** — placeholder for future settings
- **Status indicator** — shows Initialising / Syncing / Loading lyrics / Ready / Paused / Playing
- **"No lyrics found" message** when no LRC data is available for a track

### 🎬 Animations
- **Lyric highlight** — active line brightens and enlarges (ease-out, ~240ms), neighbours dim, distant lines fade to grey
- **Auto-scroll** — canvas glides smoothly to keep the active lyric centred (ease-in-out, ~240ms)
- On mid-song app start, lyrics jump directly to the correct line without animation

---

## 🧠 How It Works

### Hybrid Timing System

**Windows Media Session** provides:
- Song title and artist
- Playback position (updates only on state changes or random OS timing)
- Playback status (playing / paused)

**Local Timer** (`time.perf_counter()`) provides:
- Smooth 10ms position interpolation between Windows updates
- Drift correction when the local estimate diverges from the system position

### Sync Loop Strategy

| Loop | Interval | Responsibility |
|---|---|---|
| `progress_clock` | ~10ms | Progress bar updates, lyric highlight |
| `sync_song` | ~500ms | Song change detection, pause/resume, seek correction |

### Timeline Correction Logic (sync_song)
Classifies each incoming system position as one of:
- **Frozen** — position hasn't moved, but local time has (Windows lag) → ignore
- **Auto-refresh** — small drift from local estimate (≤3s) → accept and resync
- **User seek** — large drift from local estimate (>3s) → accept and resync

### Auto-Nudge
On first run, Windows often reports a stale or zero timeline position. The app sends a pause, then an immediate resume command to force Windows to flush the real current position before loading lyrics.

---

## 📦 Installation

### Option A — Pre-built Executable (recommended)

1. Download `LyricsPlayer.exe` from the [Releases](https://github.com/your-username/AutoLyricsApp/releases) page
2. Run it — no Python or dependencies required

---

### Option B — Run from Source

**1. Clone the repository**
```bash
git clone https://github.com/your-username/AutoLyricsApp.git
cd AutoLyricsApp
```

**2. Install dependencies**
```bash
pip install syncedlyrics winsdk pyinstaller
```

**3. Run directly**
```bash
python main.py
```

**4. Or build the exe yourself**
```bash
python build_exe.py
```
The compiled `LyricsPlayer.exe` will appear in the `dist/` folder. No Python installation is needed to run it on another machine.

---

## ⚠️ Notes / Limitations

- **Windows only** — requires Windows 10 or 11
- The media player must expose system media controls (Spotify, browsers, etc.)
- Lyrics availability depends on the `syncedlyrics` library — some songs may have no or wrong LRC data
- The auto-nudge causes a very brief (~40ms) stutter on first launch to force a position sync
   - Sometimes it stops the music, you can manually resume or press the refresh button manually

---

## 🧩 Project Structure

```
AutoLyricsApp/
├── main.py          # Entry point — window setup, async thread, button wiring
├── gui.py           # LyricsApp Tkinter class — all UI layout and animation
├── media_sync.py    # Async sync loops, timeline correction, winsdk commands
├── lyrics_utils.py  # LRC parsing, timestamp formatting, lyric index lookup
├── config.py        # Window dimensions and colour constants
├── icon.ico         # App icon (title bar, taskbar, and exe)
└── build_exe.py     # PyInstaller build script — produces a single LyricsPlayer.exe
```

---

## 📜 License

This project is mainly for personal use. Lyrics are fetched from third-party sources via the `syncedlyrics` library and may be subject to copyright.

## 🎨 Credits

- **App icon** — generated by Microsoft Copilot (AI)

## 👤 Author

Developed by Lim
