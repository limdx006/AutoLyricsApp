# 🎵 AutoLyricsApp

A real-time desktop lyrics player built with Python that detects the currently playing music on Windows and displays **synchronised (LRC) lyrics** with smooth animations and a modern GUI.

---

## 🖼 UI Overview

<table>
  <tr>
    <td>
      <img width="496" src="https://github.com/user-attachments/assets/b189f3f0-74e1-431f-ace1-d88e5bee8c45" />
    </td>
    <td>
      <img width="495" src="https://github.com/user-attachments/assets/6f6c8b59-af15-4be2-911b-720d2189167b" />
    </td>
  </tr>
</table>

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

### 🌐 Lyric Translation
- Auto-detects the song language from the lyrics text
- A **translation bar** below the info panel shows the detected language, current display mode, and toggle buttons
- Supports three languages with one-click romanisation:
  - 🇯🇵 **Japanese** → Romaji (Hepburn), powered by `cutlet` + `pykakasi` fallback
  - 🇨🇳 **Chinese** → Pinyin with tone marks, powered by `pypinyin`
  - 🇰🇷 **Korean** → Romaja (Revised Romanisation), powered by `korean-romanizer`
- Toggle buttons only appear when the detected language supports translation — no clutter for English or other songs

### 🖥 GUI (Tkinter)
- Clean dark theme
- **Song info panel** — title and artist with wrap support for long names
- **Translation bar** — shows detected language, current display mode (Original / Romaji / Pinyin / Romaja), and toggle buttons to switch between them
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

1. Download `LyricsPlayer.exe` from the [Releases](https://github.com/your-username/AutoLyricsApp/releases) page
2. Run it — no Python or any dependencies required

---

## ⚠️ Notes / Limitations

- **Windows only** — requires Windows 10 or 11
- The media player must expose system media controls (Spotify, browsers, etc.)
- Lyrics availability depends on the `syncedlyrics` library — some songs may have no or wrong LRC data
- The auto-nudge causes a very brief (~40ms) stutter on first launch to force a position sync — if the music stops, press play or use the ⟳ refresh button to re-sync manually
- **Use YouTube Music instead of YouTube** — YouTube Music lyrics tend to sync more accurately with the app, likely because the `syncedlyrics` library has better LRC data for it. Standard YouTube may have off-sync or missing lyrics
- **Multiple browser tabs** — the app reads media info from the Windows media session, which reports whichever source Windows considers active. If multiple tabs or apps are playing (or have recently played) audio, the app may pick up the wrong one — for example reading a video you are watching instead of the song you are listening to. For best results, keep only one media source active at a time

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
