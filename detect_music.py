import asyncio
import syncedlyrics
import tkinter as tk
from tkinter import ttk
import time
import re
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)

# Tkinter default setup for displaying lyrics
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 700
BG_COLOR = "#1a1a2e"  # Dark blue-ish
ACCENT_COLOR = "#16213e"  # Slightly lighter

# Global variable
current_title = None
current_artist = None
song_duration = 0
last_system_position = 0  # Position at time of last sync
last_sync_time = 0  # perf_counter() at time of last sync
max_seen_position = 0  # What our local timer calculated at last sync
last_accepted_system_pos = 0  # Track last position we actually accepted
# Pause tracking
is_paused = False
paused_position = 0
pause_start_time = 0
is_initialized = False
# Lyrics tracking
lyrics_lines = []  # List of (timestamp_seconds, text) tuples
current_lyric_index = -1


"""TIME UTILS - Formatting and parsing for LRC timestamps, plus logic to determine which lyric line to show based on current song position."""
# Format time as LRC
def format_lrc_time(seconds):
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"[{minutes:02d}:{secs:05.2f}]"


# Format time for display without brackets
def format_display_time(seconds):
    # Format for display without brackets: MM:SS
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


"""LYRICS PARSING - Functions to parse LRC lyrics into a structured format and determine which lyric line should be displayed based on the current song position."""
# Parse LRC format
def parse_lrc(lrc_text):
    lines = []
    pattern = r'\[(\d{2}):(\d{2}\.\d{2,3})\](.*)'
    for line in lrc_text.strip().split('\n'):
        match = re.match(pattern, line.strip())
        if match:
            minutes = int(match.group(1))
            sec_ms = float(match.group(2))
            timestamp = minutes * 60 + sec_ms
            text = match.group(3).strip()
            if text:
                lines.append((timestamp, text))
    lines.sort(key=lambda x: x[0])
    return lines


# Load lyrics into global variable
def get_current_lyric_index(position):
    if not lyrics_lines:
        return -1
    index = -1
    for i, (timestamp, _) in enumerate(lyrics_lines):
        if timestamp <= position:
            index = i
        else:
            break
    return index


# Update displayed lyrics based on current position
def display_lyrics(current_index):
    """Display current lyric and surrounding lines."""
    if not lyrics_lines or current_index < 0:
        return

    # Show previous, current, and next lines
    lines_to_show = []
    for offset in [-1, 0, 1]:
        idx = current_index + offset
        if 0 <= idx < len(lyrics_lines):
            timestamp, text = lyrics_lines[idx]
            prefix = "  " if offset == -1 else ">>" if offset == 0 else "  "
            lines_to_show.append(f"{prefix} [{format_lrc_time(timestamp)}] {text}")

    # Clear previous lyrics and print new ones
    print("\033[2K\033[1G", end="")  # Clear line
    print("\n".join(lines_to_show))


"""GUI CLASS - A Tkinter-based GUI to display the current song title, artist, progress bar, and synced lyrics.
The GUI updates in real-time based on the media session's state and the current position in the song."""
class LyricsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lyrics Player")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        # Main container - tall rectangle
        self.main_frame = tk.Frame(
            root, bg=BG_COLOR, width=WINDOW_WIDTH, height=WINDOW_HEIGHT
        )
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.pack_propagate(False)

        # Top section - Song info (fixed height)
        self.info_frame = tk.Frame(self.main_frame, bg=ACCENT_COLOR, height=120)
        self.info_frame.pack(fill=tk.X, padx=10, pady=10)
        self.info_frame.pack_propagate(False)

        # Song title
        self.title_label = tk.Label(
            self.info_frame,
            text="No song playing",
            font=("Helvetica", 16, "bold"),
            bg=ACCENT_COLOR,
            fg="#e94560",
            wraplength=WINDOW_WIDTH - 40,
        )
        self.title_label.pack(pady=(20, 5))

        # Artist
        self.artist_label = tk.Label(
            self.info_frame,
            text="Waiting...",
            font=("Helvetica", 12),
            bg=ACCENT_COLOR,
            fg="#a0a0a0",
        )
        self.artist_label.pack()

        # Lyrics section - NO SCROLLBAR
        self.lyrics_container = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.lyrics_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Canvas for lyrics (no scrollbar)
        self.lyrics_canvas = tk.Canvas(
            self.lyrics_container, bg=BG_COLOR, highlightthickness=0
        )
        self.lyrics_canvas.pack(fill=tk.BOTH, expand=True)

        # Frame inside canvas for lyrics lines
        self.lyrics_frame = tk.Frame(self.lyrics_canvas, bg=BG_COLOR)
        self.lyrics_canvas_window = self.lyrics_canvas.create_window(
            (0, 0), window=self.lyrics_frame, anchor=tk.NW, width=WINDOW_WIDTH - 40
        )

        # Center hint message for initial sync wait
        self.hint_label = tk.Label(
            self.lyrics_frame,
            text=" Waiting for auto sync... \n (might take up to few minutes) \n\n Or you can manually \n Drag the timeline or \n Pause/Resume the song \n to start syncing ",
            font=("Helvetica", 14),
            bg=BG_COLOR,
            fg="#d6e945",
            wraplength=WINDOW_WIDTH - 60,
            justify=tk.CENTER,
            pady=20,
        )
        self.hint_label.pack(expand=True, fill=tk.BOTH)

        # Progress bar section - NOW AT BOTTOM
        self.progress_frame = tk.Frame(self.main_frame, bg=BG_COLOR, height=40)
        self.progress_frame.pack(fill=tk.X, padx=20, pady=5, side=tk.BOTTOM)
        self.progress_frame.pack_propagate(False)

        # Time labels
        self.current_time_label = tk.Label(
            self.progress_frame,
            text="00:00",
            font=("Helvetica", 10),
            bg=BG_COLOR,
            fg="#ffffff",
        )
        self.current_time_label.pack(side=tk.LEFT)

        self.total_time_label = tk.Label(
            self.progress_frame,
            text="00:00",
            font=("Helvetica", 10),
            bg=BG_COLOR,
            fg="#ffffff",
        )
        self.total_time_label.pack(side=tk.RIGHT)

        # Progress bar (canvas for custom styling)
        self.progress_canvas = tk.Canvas(
            self.main_frame, bg=BG_COLOR, height=6, highlightthickness=0
        )
        self.progress_canvas.pack(fill=tk.X, padx=20, pady=(0, 10), side=tk.BOTTOM)

        # Progress fill
        self.progress_fill = self.progress_canvas.create_rectangle(
            0, 0, 0, 6, fill="#e94560", outline=""
        )

        # Bottom status
        self.status_label = tk.Label(
            self.main_frame,
            text="Initializing...",
            font=("Helvetica", 9),
            bg=BG_COLOR,
            fg="#666666",
        )
        self.status_label.pack(side=tk.BOTTOM, pady=10)

        # Store lyric labels for updating
        self.lyric_labels = []

        # Bind resize
        self.lyrics_frame.bind("<Configure>", self.on_frame_configure)
        self.lyrics_canvas.bind("<Configure>", self.on_canvas_configure)

    def on_frame_configure(self, event=None):
        self.lyrics_canvas.configure(scrollregion=self.lyrics_canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.lyrics_canvas.itemconfig(self.lyrics_canvas_window, width=event.width)

    def update_song_info(self, title, artist, duration):
        self.title_label.config(text=title or "Unknown Title")
        self.artist_label.config(text=artist or "Unknown Artist")
        self.total_time_label.config(text=format_display_time(duration))

    def update_progress(self, current, total):
        self.current_time_label.config(text=format_display_time(current))

        if total > 0:
            ratio = current / total
            bar_width = ratio * (WINDOW_WIDTH - 40)
            self.progress_canvas.coords(self.progress_fill, 0, 0, bar_width, 6)

    def update_status(self, text):
        self.status_label.config(text=text)

    def show_hint(self, show=True):
        """Show or hide the center hint message."""
        if show:
            self.hint_label.pack(expand=True, fill=tk.BOTH)
        else:
            self.hint_label.pack_forget()

    def clear_lyrics(self):
        for timestamp, label in self.lyric_labels:
            label.destroy()
        self.lyric_labels = []

    def load_lyrics(self, lyrics_data):
        self.clear_lyrics()
        self.show_hint(False)  # Hide hint when lyrics load

        # Top spacer to center first lyric
        top_spacer = tk.Frame(self.lyrics_frame, bg=BG_COLOR, height=250)
        top_spacer.pack(fill=tk.X)

        for timestamp, text in lyrics_data:
            label = tk.Label(
                self.lyrics_frame,
                text=text,
                font=("Helvetica", 13),
                bg=BG_COLOR,
                fg="#888888",
                wraplength=WINDOW_WIDTH - 60,
                justify=tk.CENTER,
                pady=12,
            )
            label.pack(fill=tk.X)
            self.lyric_labels.append((timestamp, label))

        # Bottom spacer to center last lyric
        bottom_spacer = tk.Frame(self.lyrics_frame, bg=BG_COLOR, height=250)
        bottom_spacer.pack(fill=tk.X)

        self.lyrics_canvas.update_idletasks()
        self.on_frame_configure()

    def highlight_lyric(self, index):
        for i, (timestamp, label) in enumerate(self.lyric_labels):
            if i == index:
                label.config(
                    fg="#ffffff",
                    font=("Helvetica", 15, "bold")
                )
                label.update_idletasks()
                canvas_height = self.lyrics_canvas.winfo_height()
                label_y = label.winfo_y()
                label_height = label.winfo_height()

                scroll_pos = label_y - (canvas_height / 2) + (label_height / 2)
                max_scroll = max(0, self.lyrics_frame.winfo_height() - canvas_height)
                scroll_pos = max(0, min(scroll_pos, max_scroll))

                self.lyrics_canvas.yview_moveto(
                    scroll_pos / self.lyrics_frame.winfo_height()
                    if self.lyrics_frame.winfo_height() > 0
                    else 0
                )

            elif i == index - 1 or i == index + 1:
                label.config(
                    fg="#aaaaaa",
                    font=("Helvetica", 13)
                )
            else:
                label.config(
                    fg="#555555",
                    font=("Helvetica", 12)
                )

"""ASYNC FUNCTIONS - Main async loops for syncing with the media session and updating the displayed lyrics and timer. 
Includes logic to handle pauses, seeks, and potential "frozen" states where the media session position isn't updating."""
# High-precision async sleep for Windows (avoids 15ms asyncio granularity)
async def precise_sleep(sleep_for: float) -> None:
    await asyncio.get_running_loop().run_in_executor(None, time.sleep, sleep_for)


# Get lyrics
def get_synced_lyrics(query):
    try:
        lrc = syncedlyrics.search(query)
        return lrc if lrc else "No lyrics found."
    except Exception as e:
        return f"Error: {e}"


async def sync_song(app):
    global current_title, current_artist
    global song_duration, last_system_position, last_sync_time
    global local_position_at_sync, last_accepted_system_pos
    global is_paused, paused_position, is_initialized
    global lyrics_lines, current_lyric_index

    while True:
        sessions = await MediaManager.request_async()
        session = sessions.get_current_session()

        if session:
            info = await session.try_get_media_properties_async()
            timeline = session.get_timeline_properties()
            
            playback_info = session.get_playback_info()
            status = playback_info.playback_status

            title = info.title
            artist = info.artist
            system_pos = timeline.position.total_seconds()
            duration = timeline.end_time.total_seconds()

            currently_playing = (status == PlaybackStatus.PLAYING)
            
            is_new_song = title != current_title or artist != current_artist
            
            if is_new_song:
                current_title = title
                current_artist = artist
                song_duration = duration
                is_paused = False
                lyrics_lines = []
                current_lyric_index = -1
                
                # Update GUI
                app.root.after(0, lambda t=title, a=artist, d=duration: app.update_song_info(t, a, d))
                app.root.after(0, app.clear_lyrics)
                app.root.after(0, lambda: app.update_status("Loading lyrics..."))
                
                needs_init_wait = not is_initialized and system_pos > 5.0
                
                if needs_init_wait:
                    app.root.after(0, lambda: app.update_status("Waiting for sync..."))
                    
                    app.root.after(0, lambda: app.show_hint(True))  # Show center hint
                    
                    initial_pos = system_pos
                    await asyncio.sleep(0.5)
                    
                    while True:
                        sessions = await MediaManager.request_async()
                        session = sessions.get_current_session()
                        if session:
                            timeline = session.get_timeline_properties()
                            new_pos = timeline.position.total_seconds()
                            
                            if abs(new_pos - initial_pos) > 0.9:
                                system_pos = new_pos
                                is_initialized = True
                                break
                        
                        await asyncio.sleep(0.5)
                else:
                    is_initialized = True
                    app.root.after(0, lambda: app.show_hint(False))  # Hide hint for new songs

                last_system_position = system_pos
                last_sync_time = time.perf_counter()
                local_position_at_sync = system_pos
                last_accepted_system_pos = system_pos

                # Fetch and parse lyrics
                query = f"{title} {artist}"
                lrc_text = get_synced_lyrics(query)
                lyrics_lines = parse_lrc(lrc_text)
                
                # Load lyrics into GUI
                app.root.after(0, lambda l=lyrics_lines: app.load_lyrics(l))
                app.root.after(0, lambda: app.update_status("Ready"))

            else:
                if not currently_playing and not is_paused:
                    is_paused = True
                    paused_position = local_position_at_sync + (time.perf_counter() - last_sync_time)
                    app.root.after(0, lambda: app.update_status("Paused"))
                    
                elif currently_playing and is_paused:
                    is_paused = False
                    last_system_position = system_pos
                    last_sync_time = time.perf_counter()
                    local_position_at_sync = system_pos
                    last_accepted_system_pos = system_pos
                    app.root.after(0, lambda: app.update_status("Playing"))
                    continue

                if is_paused:
                    pass
                    
                elif not is_initialized:
                    pass
                    
                else:
                    local_now = local_position_at_sync + (time.perf_counter() - last_sync_time)
                    delta_from_last_accepted = system_pos - last_accepted_system_pos
                    
                    is_frozen = (
                        abs(delta_from_last_accepted) < 0.1 
                        and local_now > last_accepted_system_pos + 2.0
                    )
                    
                    is_significant_change = abs(delta_from_last_accepted) > 0.9
                    
                    if is_frozen:
                        pass
                        
                    elif is_significant_change:
                        drift_from_local = system_pos - local_now
                        is_auto_refresh = abs(drift_from_local) <= 3.0
                        is_user_seek = abs(drift_from_local) > 3.0
                        
                        if is_auto_refresh:
                            last_system_position = system_pos
                            last_sync_time = time.perf_counter()
                            local_position_at_sync = system_pos
                            last_accepted_system_pos = system_pos
                            
                        elif is_user_seek:
                            last_system_position = system_pos
                            last_sync_time = time.perf_counter()
                            local_position_at_sync = system_pos
                            last_accepted_system_pos = system_pos
                            
                    else:
                        pass

        else:
            app.root.after(0, lambda: app.update_status("No media session"))

        await asyncio.sleep(0.5)


async def progress_clock(app):
    global local_position_at_sync, last_sync_time, is_paused, paused_position, is_initialized
    global current_lyric_index

    last_print = -1
    last_lyric_idx = -1

    while True:
        if current_title and is_initialized:
            if is_paused:
                elapsed = paused_position
            else:
                elapsed = local_position_at_sync + (time.perf_counter() - last_sync_time)
            
            elapsed = min(elapsed, song_duration)

            # Update progress bar every 100ms
            if int(elapsed * 10) != int(last_print * 10):
                app.root.after(0, lambda e=elapsed, d=song_duration: app.update_progress(e, d))
                last_print = elapsed

            # Update lyrics
            if lyrics_lines:
                new_index = get_current_lyric_index(elapsed)
                if new_index != last_lyric_idx:
                    last_lyric_idx = new_index
                    app.root.after(0, lambda i=new_index: app.highlight_lyric(i))

        await precise_sleep(0.01)  # 10ms for smooth UI updates

"""MAIN FUNCTION - Initializes the Tkinter app and starts the async tasks for syncing with the media session and updating the UI."""
def main():
    root = tk.Tk()
    app = LyricsApp(root)
    
    # Start async tasks
    loop = asyncio.new_event_loop()
    
    def run_async():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(asyncio.gather(
            sync_song(app),
            progress_clock(app)
        ))
    
    import threading
    thread = threading.Thread(target=run_async, daemon=True)
    thread.start()
    
    root.mainloop()

if __name__ == "__main__":
    main()