import tkinter as tk

from config import WINDOW_WIDTH, WINDOW_HEIGHT, BG_COLOR, ACCENT_COLOR
from lyrics_utils import format_display_time, COLOR_MAP


"""GUI - Tkinter window that displays the current song, a progress bar, and synced lyrics.
All updates are driven by the async layer via root.after() calls — this class never
reads media state directly."""


class LyricsApp:
    def __init__(self, root):
        self.root = root
        self._build_window()
        self._build_info_panel()
        self._build_lyrics_panel()
        self._build_progress_bar()

        # Internal state
        self.lyric_labels = []
        self._last_highlight_index = -1
        self._anim_jobs = {}  # label index -> pending after() id
        self._last_scroll_y = (
            -1
        )  # Track last scroll position to avoid redundant scrolls

        # Pre-computed animation constants (avoid hex↔rgb conversion every frame)
        self._colors = {
            "active": COLOR_MAP["#ffffff"],
            "nearby": COLOR_MAP["#aaaaaa"],
            "far": COLOR_MAP["#555555"],
        }

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

    def _build_progress_bar(self):
        self.status_label = tk.Label(
            self.main_frame,
            text="Initializing...",
            font=("Helvetica", 9),
            bg=BG_COLOR,
            fg="#666666",
        )
        self.status_label.pack(side=tk.BOTTOM, pady=10)

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

        self.pause_btn = tk.Label(
            self.progress_frame,
            text="▌▌",
            font=("Helvetica", 10),
            bg=BG_COLOR,
            fg="#ffffff",
            cursor="hand2",
        )
        self.pause_btn.pack(expand=True)
        self.pause_btn.bind("<Button-1>", lambda e: self._on_pause_btn_clicked())
        self.pause_btn.bind("<Enter>", lambda e: self.pause_btn.config(fg="#e94560"))
        self.pause_btn.bind("<Leave>", lambda e: self.pause_btn.config(fg="#ffffff"))

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

    def set_pause_callback(self, callback):
        self._pause_callback = callback

    def _on_pause_btn_clicked(self):
        if hasattr(self, "_pause_callback") and self._pause_callback:
            self._pause_callback()

    def set_pause_button_state(self, is_paused):
        # ▶ is a narrower glyph so it needs a larger size to match ▌▌ visually
        if is_paused:
            self.pause_btn.config(text="▶", font=("Helvetica", 25), fg="#ffffff")
        else:
            self.pause_btn.config(text="▌▌", font=("Helvetica", 10), fg="#ffffff")


    def clear_lyrics(self):
        # Cancel any in-flight label animations
        for job_id in self._anim_jobs.values():
            self.root.after_cancel(job_id)
        self._anim_jobs.clear()

        for widget in self.lyrics_frame.winfo_children():
            widget.destroy()
        self.lyric_labels = []
        self._last_highlight_index = -1
        self._last_scroll_y = -1
        self.lyrics_canvas.yview_moveto(0)

    def load_lyrics(self, lyrics_data):
        self.clear_lyrics()

        # Show "no lyrics" message if empty
        if not lyrics_data:
            no_lyrics_label = tk.Label(
                self.lyrics_frame,
                text="No lyrics found\n\nTry a different song",
                font=("Helvetica", 14),
                bg=BG_COLOR,
                fg="#e94560",
                wraplength=WINDOW_WIDTH - 60,
                justify=tk.CENTER,
                pady=20,
            )
            no_lyrics_label.pack(expand=True, fill=tk.BOTH)
            self.lyrics_frame.update_idletasks()
            self._on_frame_configure()
            return

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

        self.lyrics_frame.update_idletasks()
        self._on_frame_configure()

        # Small delay ensures the canvas scroll region is fully committed
        self.lyrics_canvas.after(50, lambda: self.lyrics_canvas.yview_moveto(0))

    # animation helpers - OPTIMIZED

    def _rgb_to_hex(self, r, g, b):
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    def _animate_label(
        self,
        label_idx,
        start_rgb,
        end_rgb,
        start_size,
        end_size,
        bold,
        step,
        total_steps,
    ):
        """Advance one frame of a label's color+size transition."""
        if label_idx >= len(self.lyric_labels):
            return

        t = step / total_steps
        t_eased = 1 - (1 - t) ** 2  # Ease-out

        sr, sg, sb = start_rgb
        er, eg, eb = end_rgb
        r = sr + (er - sr) * t_eased
        g = sg + (eg - sg) * t_eased
        b = sb + (eb - sb) * t_eased
        color = self._rgb_to_hex(r, g, b)

        size = round(start_size + (end_size - start_size) * t_eased)
        font_spec = ("Helvetica", size, "bold") if bold else ("Helvetica", size)

        _, label = self.lyric_labels[label_idx]
        label.config(fg=color, font=font_spec)

        if step < total_steps:
            # OPTIMIZATION: Store callback reference to avoid lambda creation overhead
            # Use a bound method with args stored in closure
            def next_frame(
                idx=label_idx,
                sr=start_rgb,
                er=end_rgb,
                ss=start_size,
                es=end_size,
                b=bold,
                s=step + 1,
                ts=total_steps,
            ):
                self._animate_label(idx, sr, er, ss, es, b, s, ts)

            job = self.root.after(15, next_frame)

            if label_idx in self._anim_jobs:
                self.root.after_cancel(self._anim_jobs[label_idx])
            self._anim_jobs[label_idx] = job

    def _start_transition(self, label_idx, end_color_name, end_size, bold):
        """Read current state and kick off animation using pre-computed RGB values."""
        if label_idx >= len(self.lyric_labels):
            return

        _, label = self.lyric_labels[label_idx]

        # OPTIMIZATION: Parse font once, store base size
        current_font = label.cget("font")
        if isinstance(current_font, tuple):
            start_size = current_font[1]
        else:
            parts = str(current_font).split()
            start_size = int(parts[1]) if len(parts) > 1 else end_size

        current_color = label.cget("fg")
        # Map current color to RGB (fallback to far color if unknown)
        start_rgb = COLOR_MAP.get(current_color, COLOR_MAP["#555555"])
        end_rgb = self._colors[end_color_name]

        if label_idx in self._anim_jobs:
            self.root.after_cancel(self._anim_jobs[label_idx])
            del self._anim_jobs[label_idx]

        self._animate_label(
            label_idx, start_rgb, end_rgb, start_size, end_size, bold, 1, 10
        )

    def highlight_lyric(self, index):
        prev = self._last_highlight_index

        if index == prev:
            return

        self._last_highlight_index = index

        affected = set()
        for idx in (prev - 1, prev, prev + 1, index - 1, index, index + 1):
            if 0 <= idx < len(self.lyric_labels):
                affected.add(idx)

        for i in affected:
            if i == index:
                self._start_transition(i, "active", 15, True)
            elif i == index - 1 or i == index + 1:
                self._start_transition(i, "nearby", 13, False)
            else:
                self._start_transition(i, "far", 12, False)

        # Scroll so the active lyric is vertically centred
        _, label = self.lyric_labels[index]
        canvas_height = self.lyrics_canvas.winfo_height()
        label_y = label.winfo_y()
        label_height = label.winfo_height()

        scroll_pos = label_y - (canvas_height / 2) + (label_height / 2)
        max_scroll = max(0, self.lyrics_frame.winfo_height() - canvas_height)
        scroll_pos = max(0, min(scroll_pos, max_scroll))

        # OPTIMIZATION: Skip scroll if position hasn't changed meaningfully
        scroll_ratio = (
            scroll_pos / self.lyrics_frame.winfo_height()
            if self.lyrics_frame.winfo_height() > 0
            else 0
        )
        if abs(scroll_ratio - self._last_scroll_y) > 0.01:  # Only scroll if >1% change
            self._last_scroll_y = scroll_ratio
            self.lyrics_canvas.yview_moveto(scroll_ratio)
