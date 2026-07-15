# 🎵 AutoLyricsApp
<img width="256" height="256" alt="icon" src="https://github.com/user-attachments/assets/71043c39-7800-4239-a4f3-dc04a0ac2f3e" />

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
- Auto-detects the most likely music source from all active Windows media sessions using a multi-signal scoring system — targeting 90%+ accuracy even with multiple browser tabs or apps open simultaneously
- Scores every session across signals like playback state, artist validity, album presence, thumbnail, title cleanliness, and lyrics availability — the highest-scoring session wins
- Known music apps (Spotify, Tidal, MusicBee, AIMP, etc.) receive a strong bonus; browsers are scored cautiously and recover points only if their metadata looks genuinely musical
- Titles matching video patterns ("Episode", "Tutorial", "Live Stream", "Full HD", CJK video keywords, etc.) are penalised to avoid picking up YouTube videos over music
- A background **lyrics probe** runs once per `(title, artist)` pair — sessions whose track has synced lyrics available get a score bonus; sessions with no match are penalised, making music sources rank naturally higher than video sources
- Re-scoring is lazy: a full session poll only runs on song change, when a lyrics probe result arrives, or every 10 seconds — the 0.5 s sync loop returns the cached winner instantly between those events
- Works with Spotify, YouTube Music, and other apps that expose Windows system media controls
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
  - 🇯🇵 **Japanese** → Romaji (Hepburn), powered by `cutlet` fallback
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
- **Settings button (⚙)** — opens a preferences window to adjust window size and lyric font size
- **Pin-to-top button (📌)** — toggles always-on-top mode so the window stays above other apps; icon turns red when active, dimmed when off
- **Status indicator** — shows Initialising / Syncing / Loading lyrics / Ready / Paused / Playing
- **"No lyrics found" message** when no LRC data is available for a track

### ⚙️ Settings Window
- Opens as a modal preference window from the ⚙ button
- **Window size** — 5 presets from Small (340×640) to XLarge (600×1000), plus a free-form custom input (width 300–800, height 500–1200)
- **Lyric font size** — 4 presets from Small to XLarge controlling active, nearby, and far line sizes independently, plus a custom input for all three values
- All changes apply immediately so the effect is visible before closing
- Current values are pre-selected when the window opens

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
| `media_selector` | lazy | Session scoring — re-runs on song change, lyrics probe result, or every 10 s |

### Timeline Correction Logic (sync_song)
Classifies each incoming system position as one of:
- **Frozen** — position hasn't moved, but local time has (Windows lag) → ignore
- **Auto-refresh** — small drift from local estimate (≤3s) → accept and resync
- **User seek** — large drift from local estimate (>3s) → accept and resync

### Auto-Nudge
On first launch and on every new song detection, Windows often reports a stale or zero timeline position. To fix this, the app sends a pause command followed by a resume command to force Windows to flush the real current playback position before lyrics are loaded and synced.

The nudge runs **twice** — once on first launch (to resolve the 0:00 startup bug), and again on every subsequent song change (to ensure the position is accurate before lyrics load).

**Resume reliability:** After pausing, the app re-fetches the active session from Windows and retries `try_play_async()` up to 5 times with increasing delays, verifying playback status after each attempt. If all attempts fail, music may remain paused — pressing play manually or using the ⟳ refresh button will recover.

**Backward jump verification:** If Windows suddenly reports a position significantly earlier than expected (e.g. a glitch reporting near 0:00 mid-song), the app fires a nudge to verify the real position before accepting the change. If the nudge confirms the jump was a genuine user seek, it is accepted; if the nudge returns a position close to where the local timer was, the report is treated as a glitch and ignored.

---

## 📦 Installation

1. Download `LyricsPlayer.exe` from the [Releases](https://github.com/your-username/AutoLyricsApp/releases) page
2. Run it — no Python or any dependencies required

---

## ⚠️ Notes / Limitations

- **Windows only** — requires Windows 10 or 11
- The media player must expose system media controls (Spotify, browsers, etc.)
- Lyrics availability depends on the `syncedlyrics` library — some songs may have no or wrong LRC data
- **Auto-nudge on every song change** — the app performs a pause/resume cycle on startup and on each new song to force Windows to report the correct playback position (fixes the 0:00 sync bug). The resume is retried up to 5 times with verification. In rare cases where all retries fail, music may remain paused — press play manually or use the ⟳ refresh button to recover
- **Use YouTube Music instead of YouTube** — YouTube Music lyrics tend to sync more accurately with the app, likely because the `syncedlyrics` library has better LRC data for it. Standard YouTube may have off-sync or missing lyrics

---

## 🧩 Project Structure

```
AutoLyricsApp/
├ main.py               # Entry point — window setup, async thread, button wiring
├ gui.py                # LyricsApp Tkinter class — all UI layout and animation
├ media_sync.py         # Async sync loops, timeline correction, winsdk commands
├ lyrics_utils.py       # LRC parsing, timestamp formatting, lyric index lookup
├ config.py             # Window dimensions, colour constants, and preset values
├ settings_window.py    # Modal preferences window — window size and font size
├ media_selector.py     # Multi-signal session scorer — picks the best music source from all active sessions
├ icon.ico              # App icon (title bar, taskbar, and exe)
└ build_exe.py          # PyInstaller build script — produces a single LyricsPlayer.exe
```

---

## 📚 Dependencies

The following libraries are used by this project:

| Library | Purpose |
|---|---|
| `winsdk` | Windows Media Session API access — detects the currently playing song and controls playback (pause, resume, skip) |
| `syncedlyrics` | Fetches timestamped LRC lyrics from online sources |
| `cutlet` | Japanese text → Hepburn romaji conversion (primary) |
| `fugashi` | Japanese morphological analysis — required by `cutlet` |
| `unidic-lite` | Compact Japanese dictionary — required by `fugashi` |
| `pypinyin` | Chinese text → Pinyin with tone marks |
| `korean-romanizer` | Korean Hangul → Revised Romanisation (Romaja) |
| `pyinstaller` | Bundles the app into a single `LyricsPlayer.exe` |

All dependencies are listed in `requirements.txt` and bundled automatically into the executable by `build_exe.py`.

---

## 📜 License

This project is mainly for personal use. Lyrics are fetched from third-party sources via the `syncedlyrics` library and may be subject to copyright.

## 🎨 Credits

- **App icon** — generated by Microsoft Copilot (AI)

## 👤 Author

Developed by Lim
