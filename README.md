# 🎵 AutoLyricsApp

A real-time desktop lyrics player built with Python that detects the currently playing music on Windows and displays **synchronised (LRC) lyrics** with smooth timing and a modern GUI.

---

### 🖼 UI Overview
- Top: Song title & artist  
- Middle: Centred scrolling lyrics  
- Bottom:
  - Progress bar
  - Current time / total time
  - Status indicator

<div style="display: flex; gap: 10px;">
  <img width="499" height="999" alt="image" src="https://github.com/user-attachments/assets/f81236d6-ba12-4f6a-b465-139614502653" />
</div>

---

## ✨ Features

- 🎧 **Auto-detect currently playing music**
  - Works with Spotify, YouTube (browser), and other supported apps
- ⏱ **High-precision playback tracking**
  - Combines Windows Media session + local timer
  - Handles drift, pause/resume, and seeking
- 📜 **Synchronised lyrics (LRC support)**
  - Automatically fetches timestamped lyrics
  - Parses and aligns lyrics in real time
- 🖥 **Modern GUI (Tkinter)**
  - Clean dark theme
  - Centred scrolling lyrics
  - Highlighted current line
- 🔄 **Real-time updates**
  - Smooth progress bar
  - Live lyric highlighting
- ⏸ **Playback state handling**
  - Pause / Resume detection
  - Seek detection (jump forward/backwards)
- 🧠 **Smart sync logic**
  - Handles system lag, frozen playback, and timing correction

---

## 🧠 How It Works

This app uses a **hybrid timing system**:

### 1. Windows Media Session (Source of Truth)
Provides:
- Song title & artist
- Playback position (only triggers when user interaction or random timing)
- Playback status (playing/paused)

### 2. Local High-Precision Timer
- Uses `time.perf_counter()` for smooth updates
- Continuously adjusts timing to prevent drift

### 🔁 Sync Strategy
- Fast loop (~10ms) → UI updates & lyric sync  
- Slow loop (~0.5s) → drift correction & song detection  

This ensures:
- ✅ Smooth update  
- ✅ Accurate timing  
- ✅ No laggy resets  

---

## 🖼 UI Overview

- **Top:** Song title & artist  
- **Middle:** Centered scrolling lyrics  
- **Bottom:**  
  - Progress bar  
  - Current time / total time
  - Play and pause button
  - Status indicator  

---

## 📦 Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/AutoLyricsApp.git
cd AutoLyricsApp
```
### 2. Run the program
- Run the version_1.0.py
- Run the main.py (separated version of 1.0 for future improvement)

---

### ⚠️ Notes / Limitations
- Works only on Windows 10/11
- Requires apps that support system media controls
- Lyrics depend on availability:
  - Some songs may not have synced (LRC) lyrics

---
 
### 🧩 Project Structure (Conceptual)
```bash
main.py
│
├── GUI (LyricsApp)
├── Media Sync (sync_song)
├── Timer Engine (progress_clock)
├── Lyrics Parser (parse_lrc)
└── Utilities (time formatting, helpers)
```

---

### 📜 License
This project is mainly for personal use.
Lyrics are fetched from third-party sources (syncedlyrics library) and may be subject to copyright.

### 👤 Author
Developed by Lim
