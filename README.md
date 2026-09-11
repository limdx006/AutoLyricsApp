# 🎵 AutoLyricsApp
<img width="256" height="256" alt="icon" src="https://github.com/user-attachments/assets/71043c39-7800-4239-a4f3-dc04a0ac2f3e" />

A real-time desktop lyrics player built with Python that detects the currently playing music on Windows and displays **synchronised (LRC) lyrics** with smooth animations and a modern GUI.

---

## 🖼 UI Overview

<table>
  <tr>
    <td>
      <img width="361" height="732" alt="Ori" src="https://github.com/user-attachments/assets/27107514-8ec7-4b98-9097-ce2d0c13773a" />
    </td>
    <td>
      <img width="361" height="732" alt="Translated" src="https://github.com/user-attachments/assets/0e7a2d46-3349-4350-a8fe-c077b034ddac" />  
    </td>
  </tr>
</table>

---

## ✨ Features

### 🎧 Media Detection
- Picks the most likely music source out of every active Windows media session using a cheap, metadata-only scoring pass (no network calls); only handles when multiple browser tabs or apps are active at once
- Scores each session on signals like artist presence/validity, album presence, thumbnail presence, whether its position is actually advancing between two quick samples, and whether its source app is a known music app
- Known music apps (Spotify, Tidal, MusicBee, AIMP, SoundCloud, YouTube Music, etc.) get a strong bonus; browser tabs are penalised by default but recover points if their metadata still looks genuinely musical (real artist, thumbnail, album)
- Titles matching video-style patterns ("Episode", "Tutorial", "Live Stream", "Full HD", common CJK video keywords, etc.) are penalised so a YouTube video doesn't outrank an actual song
- Chat/conferencing/video-player apps (Teams, Zoom, Discord, VLC, etc.) are blacklisted outright
- Re-scoring is lazy: it only runs again when the *set* of active sessions changes, or when the currently-selected session's own song changes — otherwise the previous pick is reused instantly on every poll
- Works with any app that exposes Windows' System Media Transport Controls (Spotify, browsers, YouTube Music, etc.)
- Detects song changes, pause/resume, and playback position changes automatically; a single stray "no session" report is ignored for one extra poll before being treated as a real disappearance (guards against transient glitches, e.g. a "repeat one" restart)

### ⏱ Playback Tracking
- Combines the Windows Media session's reported position with a local `time.monotonic()`-based timer for smooth ~100ms progress-bar/lyric updates between the ~500ms Windows polls
- Whenever Windows reports a new position (play, pause, seek, or natural progression), the local timer is resynced to it immediately

### 📜 Synchronised Lyrics
- Fetches timestamped LRC lyrics automatically via the `syncedlyrics` library, retrying a few times before giving up on a track
- Parses and aligns lyrics to the current playback position in real time
- Adjustable **lyric offset** (±0.1s step buttons, or type a value directly), clamped to ±99s
- Lyric offset resets to a configurable default on each new song (the default itself can be changed from the Settings window without affecting whatever offset is currently in effect)

### 🌐 Lyric Translation
- Auto-detects the song's language by sampling a handful of lines from the lyrics (a fixed early block plus a few random lines from the middle) and classifying each by Unicode script, then taking a majority vote
- A **translation bar** below the info panel shows the detected language, the current display mode, and a toggle switch to flip between them
- Supports three languages with one-click romanisation:
  - 🇯🇵 **Japanese** → Hepburn romaji, via `cutlet`
  - 🇨🇳 **Chinese** → Pinyin with tone marks, via `pypinyin`
  - 🇰🇷 **Korean** → Revised Romanisation, via `korean-romanizer`
- The translation is computed once per song and cached — flipping the toggle back and forth afterwards is instant, with no re-processing
- The toggle only appears when the detected language actually has a translation mode — no clutter for English or undetected lyrics

### 🖥 GUI (Tkinter)
- Clean dark theme
- **Song info panel** — title and artist with wrap support for long names
- **Translation bar** — detected language, current display mode (Original / Romaji / Pinyin), and the toggle switch
- **Scrolling lyrics panel** — centred, auto-scrolling canvas, no scrollbar, eased motion
- **Transport controls** — previous (⏮), pause/resume (⏸ / ▶), next (⏭) buttons, acting on whichever session is currently selected
- **Progress bar** — live red fill with current/total time flanking the controls
- **Refresh button (⟳)** — manually triggers a re-sync nudge on the currently selected session
- **Log viewer button (📝)** — opens a live window showing the app's captured console output, for debugging without a console attached
- **Settings button (⚙)** — opens a preferences window to adjust window size, lyric font size, and default offset
- **Pin-to-top button (📌)** — toggles always-on-top mode for the main window (and keeps the log/settings windows' pinned state in sync); icon turns red when active
- **Status label** — shows Playing / Paused based on the selected session's playback state
- Placeholder text for lyrics state: "Lyrics will be displayed here" (no song yet), "Fetching lyrics..." (loading), or "Lyrics not found, maybe try another song." (no LRC match)
- The 📝 and ⚙ buttons act as toggles — pressing them again closes the window, same as its own close button

### ⚙️ Settings Window
- Opens as a preferences window from the ⚙ button, grouped with and centred over the main window
- **Window size** — 5 presets (Small 340×640, Medium 360×700, Default 400×800, Large 500×900, XLarge 600×1000), plus a custom width/height input
- **Lyric font size** — 4 presets (Small, Default, Large, XLarge), each setting the active/nearby/far line sizes together, plus a custom 3-value input (1–99 each)
- **Default lyric offset** — a single ±99s value that controls what future song changes reset the offset to, without touching whatever offset is currently in effect for the song playing right now
- All changes apply immediately so the effect is visible before closing; current values are pre-selected/pre-filled when the window opens

### 🎬 Animations
- **Auto-scroll** — the lyrics canvas glides smoothly to keep the active line centred (eased toward its target position on every ~20ms tick)
- The active/nearby/far line's colour and size change instantly when the current line changes — it's the *scroll position* that's animated, not the text itself
- Every lyric line is pre-wrapped once at the largest font size it could ever appear at, so highlighting a line never changes how the list wraps or jumps around

---

## 🧠 How It Works

### Hybrid Timing System

**Windows Media Session** provides:
- Song title and artist
- Playback position (updates only on state changes or the OS's own timing)
- Playback status (playing / paused)

**Local Timer** (`time.monotonic()`) provides:
- Smooth interpolated position between Windows updates
- An instant resync point whenever a new Windows position comes in

### Sync Loop Strategy

| Loop | Interval | Responsibility |
|---|---|---|
| UI update loop | ~100ms | Progress bar, current-time label, and lyric highlight/auto-scroll, driven from the local timer |
| Windows poll loop | ~500ms | Picks the best session, reads its position/status/title/artist, detects song changes and pause/resume |
| Session scoring | lazy | Re-runs only when the set of active sessions changes, or the selected session's own song changes — otherwise the previous pick is reused as-is |

### Auto-Nudge
Windows can report a stale or zero timeline position right when a track starts, which throws off lyric sync. To fix this, the app sends a pause command followed by a resume command shortly after fetching synced lyrics for a track, forcing Windows to flush a fresh, accurate position.

- Fires automatically once per song, right after synced lyrics are successfully found for it — targeting the exact session the lyrics were fetched for
- Also available manually via the ⟳ refresh button, targeting whichever session is currently selected
- Does nothing if the session is already paused
- If the resume doesn't verify successfully, the app retries once more shortly after; in rare cases it may still need a manual play press or another ⟳ tap

---

## 📦 Installation

1. Download the latest `LyricsPlayer *.exe` from the [Releases](https://github.com/your-username/AutoLyricsApp/releases) page
2. Run it — no Python or any dependencies required

---

## ⚠️ Notes / Limitations

- **Windows only** — requires Windows 10 or 11
- The media player must expose Windows' System Media Transport Controls (Spotify, most browsers, etc.)
- Lyrics availability depends on the `syncedlyrics` library — some songs may have no or wrong LRC data
- **Auto-nudge on song change** — the app performs a pause/resume cycle after fetching lyrics for a track to force Windows to report the correct playback position. In rare cases where the resume doesn't take, music may remain paused — press play manually or use the ⟳ refresh button to recover
- **Use YouTube Music instead of YouTube** — YouTube Music lyrics tend to sync more accurately with the app, likely because the `syncedlyrics` library has better LRC data for it. Standard YouTube may have off-sync or missing lyrics, and its titles are more likely to get scored down as "video-like"
- **Windows security warning** — Windows Defender SmartScreen may warn when running the .exe for the first time because it is not digitally signed. If you trust the app, click More info → Run anyway.

---

## 🧩 Project Structure

```
AutoLyricsApp/
├ main.py                # Entry point - picks the initial session, builds the Tk window, starts mainloop
├ gui.py                 # LyricsApp - top-level layout, wires the sub-panels together, lyrics fetch orchestration
├ gui_media_details.py   # Song info panel - title/artist, offset control, log/refresh/pin/settings buttons
├ gui_language_bar.py    # Translation bar - detected language + Original/Romaji/Pinyin toggle switch
├ gui_lyrics_display.py  # Scrolling, time-synced lyrics canvas with eased auto-scroll
├ gui_controls_panel.py  # Transport controls, progress bar, hybrid position polling/sync loop
├ media_detect.py        # winsdk session helpers - read/control a specific (or Windows' "current") session
├ media_selector.py      # Multi-signal scorer - picks the best session out of all active ones
├ local_timer.py         # Monotonic local playback clock used to interpolate between Windows updates
├ time_formatter.py      # LRC timestamp parsing/formatting, on-screen time formatting
├ language_detect.py     # Unicode-script based language detection, sampled across the lyrics
├ lyrics_fetcher.py      # syncedlyrics search + cleanup, triggers the post-fetch auto-nudge
├ lyrics_translator.py   # Romaji/Pinyin/Romaja conversion of parsed lyric lines
├ auto_nudge.py          # Pause/resume "nudge" to force Windows to flush a fresh timeline position
├ setting.py             # Preferences window - window size, font size, and default offset
├ log_viewer.py          # In-app log viewer window + stdout/stderr capture (safe under --windowed builds)
├ config.py              # Window dimensions, colour constants, and preset values
├ icon.ico               # App icon (title bar, taskbar, and exe)
└ build_exe.py           # PyInstaller build script - produces a single LyricsPlayer exe
```

---

## 📚 Dependencies

The following libraries are used by this project:

| Library | Purpose |
|---|---|
| `winsdk` | Windows Media Session API access — detects the currently playing song and controls playback (pause, resume, skip) |
| `syncedlyrics` | Fetches timestamped LRC lyrics from online sources (via HTTPS, so `requests`/`certifi` come along as transitive dependencies) |
| `cutlet` | Japanese text → Hepburn romaji conversion |
| `fugashi` | Japanese morphological analysis — required by `cutlet` |
| `unidic-lite` | Compact Japanese dictionary — required by `fugashi` |
| `pypinyin` | Chinese text → Pinyin with tone marks |
| `korean-romanizer` | Korean Hangul → Revised Romanisation (Romaja) |
| `pyinstaller` | Bundles the app into a single `LyricsPlayer` executable |

---

## 📜 License

This project is mainly for personal use. Lyrics are fetched from third-party sources via the `syncedlyrics` library and may be subject to copyright.

## 🎨 Credits

- **App icon** — generated by Microsoft Copilot (AI)

## 👤 Author

Developed by Limdx006
