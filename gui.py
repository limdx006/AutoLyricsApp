import tkinter as tk

from config import WINDOW_WIDTH, WINDOW_HEIGHT, BG_COLOR, ACCENT_COLOR
from lyrics_utils import format_display_time


"""GUI - Tkinter window that displays the current song, a progress bar, and synced lyrics.
All updates are driven by the async layer via root.after() calls — this class never
reads media state directly."""


class LyricsApp:
    def __init__(self, root):
        self.root = root
        self._build_window()
        self._build_info_panel()
        self._build_lyrics_panel()
        self._build_hint_message()
        self._build_progress_bar()

        # Internal state
        self.lyric_labels = []
        self._last_highlight_index = -1

        # Keep lyrics_frame width in sync with canvas width
        self.lyrics_frame.bind("<Configure>", self._on_frame_configure)
        self.lyrics_canvas.bind("<Configure>", self._on_canvas_configure)

    # setup

    def _build_window(self):
        self.root.title("Lyrics Player")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.configure(bg=BG_COLOR)
        self.root.resizable(False, False)

        self.main_frame = tk.Frame(
            self.root, bg=BG_COLOR, width=WINDOW_WIDTH, height=WINDOW_HEIGHT
        )
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        self.main_frame.pack_propagate(False)

    def _build_info_panel(self):
        # Top section - song title and artist (fixed height)
        self.info_frame = tk.Frame(self.main_frame, bg=ACCENT_COLOR, height=120)
        self.info_frame.pack(fill=tk.X, padx=10, pady=10)
        self.info_frame.pack_propagate(False)

        self.title_label = tk.Label(
            self.info_frame,
            text="No song playing",
            font=("Helvetica", 16, "bold"),
            bg=ACCENT_COLOR,
            fg="#e94560",
            wraplength=WINDOW_WIDTH - 40,
        )
        self.title_label.pack(pady=(20, 5))

        self.artist_label = tk.Label(
            self.info_frame,
            text="Waiting...",
            font=("Helvetica", 12),
            bg=ACCENT_COLOR,
            fg="#a0a0a0",
        )
        self.artist_label.pack()

    def _build_lyrics_panel(self):
        # Scrollable canvas area that holds all lyric labels
        self.lyrics_container = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.lyrics_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.lyrics_canvas = tk.Canvas(
            self.lyrics_container, bg=BG_COLOR, highlightthickness=0
        )
        self.lyrics_canvas.pack(fill=tk.BOTH, expand=True)

        self.lyrics_frame = tk.Frame(self.lyrics_canvas, bg=BG_COLOR)
        self.lyrics_canvas_window = self.lyrics_canvas.create_window(
            (0, 0), window=self.lyrics_frame, anchor=tk.NW, width=WINDOW_WIDTH - 40
        )

    def _build_hint_message(self):
        """Three-part hint shown while waiting for the first sync event."""
        self.hint_container = tk.Frame(self.lyrics_frame, bg=BG_COLOR)
        self.hint_container.pack(expand=True, fill=tk.BOTH)

        # Top part - normal text
        self.hint_label_top = tk.Label(
            self.hint_container,
            text="Waiting for auto sync...\n(might take up to few minutes)",
            font=("Helvetica", 14),
            bg=BG_COLOR,
            fg="#d6e945",
            wraplength=WINDOW_WIDTH - 60,
            justify=tk.CENTER,
            pady=10,
        )
        self.hint_label_top.pack()

        # Middle part - underlined
        self.hint_label_middle = tk.Label(
            self.hint_container,
            text="Or you can manually",
            font=("Helvetica", 16, "underline"),
            bg=BG_COLOR,
            fg="#d6e945",
            wraplength=WINDOW_WIDTH - 60,
            justify=tk.CENTER,
        )
        self.hint_label_middle.pack()

        # Bottom part - normal text
        self.hint_label_bottom = tk.Label(
            self.hint_container,
            text="Drag the timeline or\nPause/Resume the song\nto start syncing",
            font=("Helvetica", 14),
            bg=BG_COLOR,
            fg="#d6e945",
            wraplength=WINDOW_WIDTH - 60,
            justify=tk.CENTER,
            pady=10,
        )
        self.hint_label_bottom.pack()

    def _build_progress_bar(self):
        # Status text sits at the very bottom
        self.status_label = tk.Label(
            self.main_frame,
            text="Initializing...",
            font=("Helvetica", 9),
            bg=BG_COLOR,
            fg="#666666",
        )
        self.status_label.pack(side=tk.BOTTOM, pady=10)

        # Time labels flank the progress bar
        self.progress_frame = tk.Frame(self.main_frame, bg=BG_COLOR, height=40)
        self.progress_frame.pack(fill=tk.X, padx=20, pady=5, side=tk.BOTTOM)
        self.progress_frame.pack_propagate(False)

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

        # Thin coloured bar drawn on a canvas for custom styling
        self.progress_canvas = tk.Canvas(
            self.main_frame, bg=BG_COLOR, height=6, highlightthickness=0
        )
        self.progress_canvas.pack(fill=tk.X, padx=20, pady=(0, 10), side=tk.BOTTOM)

        self.progress_fill = self.progress_canvas.create_rectangle(
            0, 0, 0, 6, fill="#e94560", outline=""
        )

    # canvas helpers
    def _on_frame_configure(self, event=None):
        self.lyrics_canvas.configure(scrollregion=self.lyrics_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.lyrics_canvas.itemconfig(self.lyrics_canvas_window, width=event.width)

    # public update API
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
        """Show or hide the center hint message.
        Rebuilds the widgets if they were destroyed by a previous clear_lyrics call."""
        if not show:
            # Only hide if the container still exists
            if self.hint_container.winfo_exists():
                self.hint_container.pack_forget()
            return

        # Rebuild the hint container if it was destroyed by clear_lyrics
        if not self.hint_container.winfo_exists():
            self._build_hint_message()
        else:
            self.hint_container.pack(expand=True, fill=tk.BOTH)

    def clear_lyrics(self):
        # Destroy every widget in lyrics_frame (labels, spacers, hint container)
        for widget in self.lyrics_frame.winfo_children():
            widget.destroy()
        self.lyric_labels = []
        self._last_highlight_index = -1
        self.lyrics_canvas.yview_moveto(0)

    def load_lyrics(self, lyrics_data):
        self.clear_lyrics()

        # Top spacer keeps the first lyric centred on screen
        tk.Frame(self.lyrics_frame, bg=BG_COLOR, height=250).pack(fill=tk.X)

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

        # Bottom spacer keeps the last lyric centred on screen
        tk.Frame(self.lyrics_frame, bg=BG_COLOR, height=250).pack(fill=tk.X)

        # Force layout recalculation before resetting scroll
        self.lyrics_frame.update_idletasks()
        self.lyrics_canvas.update_idletasks()
        self._on_frame_configure()

        # Small delay ensures the canvas scroll region is fully committed
        self.lyrics_canvas.after(50, lambda: self.lyrics_canvas.yview_moveto(0))

    def highlight_lyric(self, index):
        prev = self._last_highlight_index

        if index == prev:
            return

        # Only touch labels whose style actually changes between the two states
        affected = set()
        for idx in (prev - 1, prev, prev + 1, index - 1, index, index + 1):
            if 0 <= idx < len(self.lyric_labels):
                affected.add(idx)

        for i in affected:
            _, label = self.lyric_labels[i]
            if i == index:
                label.config(fg="#ffffff", font=("Helvetica", 15, "bold"))
            elif i == index - 1 or i == index + 1:
                label.config(fg="#aaaaaa", font=("Helvetica", 13))
            else:
                label.config(fg="#555555", font=("Helvetica", 12))

        self._last_highlight_index = index

        # Scroll so the active lyric is vertically centred in the canvas
        _, label = self.lyric_labels[index]
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
