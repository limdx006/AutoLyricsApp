import tkinter as tk

from config import WINDOW_WIDTH, WINDOW_HEIGHT, BG_COLOR, ACCENT_COLOR
from lyrics_utils import format_display_time, COLOR_MAP


class LyricsApp:
    def __init__(self, root):
        self.root = root
        self.lyric_offset = 0.3
        self.lyric_mode = "original"  # Track current lyric mode
        self._build_window()
        self._build_info_panel()
        self._build_lyrics_panel()
        self._build_progress_bar()

        self.lyric_labels = []
        self._last_highlight_index = -1
        self._anim_jobs = {}
        self._last_scroll_y = -1
        self._scroll_job = None  # Pending after() id for the scroll animation

        self._colors = {
            "active": COLOR_MAP["#ffffff"],
            "nearby": COLOR_MAP["#aaaaaa"],
            "far": COLOR_MAP["#555555"],
        }

        self.lyrics_frame.bind("<Configure>", self._on_frame_configure)
        self.lyrics_canvas.bind("<Configure>", self._on_canvas_configure)

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
        self.info_frame = tk.Frame(self.main_frame, bg=ACCENT_COLOR)
        self.info_frame.pack(fill=tk.X, padx=10, pady=10)

        self.settings_menu = tk.Menu(self.root, tearoff=0)
        self.settings_menu.add_command(
            label="Lyric Language:",
            state="disabled",
        )
        self.settings_menu.add_separator()
        
        # Add lyric mode options
        self.settings_menu.add_command(
            label="Japanese (Original)",
            command=lambda: self._on_lyric_mode_selected("original"),
        )
        self.settings_menu.add_command(
            label="Romaji (Roman Letters)",
            command=lambda: self._on_lyric_mode_selected("romaji"),
        )

        self._offset_var = tk.StringVar(value=f"{self.lyric_offset:.1f}")
        self._offset_var.trace_add("write", self._on_offset_var_changed)

        self.title_label = tk.Label(
            self.info_frame,
            text="No song playing",
            font=("Helvetica", 16, "bold"),
            bg=ACCENT_COLOR,
            fg="#e94560",
            wraplength=WINDOW_WIDTH - 80,
            justify=tk.CENTER,
        )
        self.title_label.pack(pady=(20, 4), padx=20)

        self.artist_label = tk.Label(
            self.info_frame,
            text="Waiting...",
            font=("Helvetica", 12),
            bg=ACCENT_COLOR,
            fg="#a0a0a0",
            wraplength=WINDOW_WIDTH - 80,
            justify=tk.CENTER,
        )
        self.artist_label.pack(padx=20, pady=(0, 8))

        button_row = tk.Frame(self.info_frame, bg=ACCENT_COLOR)
        button_row.pack(fill=tk.X, padx=10, pady=(0, 12))

        self.refresh_btn = tk.Label(
            button_row,
            text="⟳",
            font=("Helvetica", 18),
            bg=ACCENT_COLOR,
            fg="#ffffff",
            cursor="hand2",
        )
        self.refresh_btn.pack(side=tk.LEFT)
        self.refresh_btn.bind("<Button-1>", lambda e: self._on_refresh_btn_clicked())
        self.refresh_btn.bind("<Enter>", lambda e: self.refresh_btn.config(fg="#e94560"))
        self.refresh_btn.bind("<Leave>", lambda e: self.refresh_btn.config(fg="#ffffff"))

        offset_frame = tk.Frame(button_row, bg=ACCENT_COLOR)
        offset_frame.pack(side=tk.LEFT, expand=True)

        tk.Label(
            offset_frame,
            text="Offset:",
            font=("Helvetica", 14, "bold"),
            bg=ACCENT_COLOR,
            fg="#ffffff",
        ).pack(side=tk.LEFT, padx=(0, 6))

        tk.Button(
            offset_frame,
            text="-",
            width=2,
            command=self._decrement_lyric_offset,
        ).pack(side=tk.LEFT)

        self.offset_entry = tk.Entry(
            offset_frame,
            textvariable=self._offset_var,
            width=4,
            justify=tk.CENTER,
            font=("Helvetica", 11),
        )
        self.offset_entry.pack(side=tk.LEFT, padx=4)

        tk.Button(
            offset_frame,
            text="+",
            width=2,
            command=self._increment_lyric_offset,
        ).pack(side=tk.LEFT)

        self.settings_btn = tk.Label(
            button_row,
            text="⚙",
            font=("Helvetica", 18),
            bg=ACCENT_COLOR,
            fg="#ffffff",
            cursor="hand2",
        )
        self.settings_btn.pack(side=tk.RIGHT)
        self.settings_btn.bind("<Button-1>", self._on_settings_btn_clicked)
        self.settings_btn.bind("<Enter>", lambda e: self.settings_btn.config(fg="#e94560"))
        self.settings_btn.bind("<Leave>", lambda e: self.settings_btn.config(fg="#ffffff"))

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
        # Configure grid columns: 0 and 4 expand equally to push center content to middle
        self.progress_frame.grid_columnconfigure(0, weight=0)  # left spacer / time
        self.progress_frame.grid_columnconfigure(1, weight=1)
        self.progress_frame.grid_columnconfigure(2, weight=0)  # prev btn
        self.progress_frame.grid_columnconfigure(3, weight=0)  # pause btn (center)
        self.progress_frame.grid_columnconfigure(4, weight=0)  # next btn
        self.progress_frame.grid_columnconfigure(5, weight=1)
        self.progress_frame.grid_columnconfigure(6, weight=0)  # right spacer / time

        self.current_time_label = tk.Label(
            self.progress_frame,
            text="00:00",
            font=("Helvetica", 10),
            bg=BG_COLOR,
            fg="#ffffff",
        )
        self.current_time_label.grid(row=0, column=0, sticky=tk.W)

        self.prev_btn = tk.Label(
            self.progress_frame,
            text="◀◀",
            font=("Helvetica", 20),
            bg=BG_COLOR,
            fg="#ffffff",
            cursor="hand2",
        )
        self.prev_btn.grid(row=0, column=2, padx=10)
        self.prev_btn.bind("<Button-1>", lambda e: self._on_prev_btn_clicked())
        self.prev_btn.bind("<Enter>", lambda e: self.prev_btn.config(fg="#e94560"))
        self.prev_btn.bind("<Leave>", lambda e: self.prev_btn.config(fg="#ffffff"))

        self.pause_btn = tk.Label(
            self.progress_frame,
            text="▌▌",
            font=("Helvetica", 14),
            bg=BG_COLOR,
            fg="#ffffff",
            cursor="hand2",
        )
        self.pause_btn.grid(row=0, column=3, padx=10)
        self.pause_btn.bind("<Button-1>", lambda e: self._on_pause_btn_clicked())
        self.pause_btn.bind("<Enter>", lambda e: self.pause_btn.config(fg="#e94560"))
        self.pause_btn.bind("<Leave>", lambda e: self.pause_btn.config(fg="#ffffff"))

        self.next_btn = tk.Label(
            self.progress_frame,
            text="▶▶",
            font=("Helvetica", 20),
            bg=BG_COLOR,
            fg="#ffffff",
            cursor="hand2",
        )
        self.next_btn.grid(row=0, column=4, padx=10)
        self.next_btn.bind("<Button-1>", lambda e: self._on_next_btn_clicked())
        self.next_btn.bind("<Enter>", lambda e: self.next_btn.config(fg="#e94560"))
        self.next_btn.bind("<Leave>", lambda e: self.next_btn.config(fg="#ffffff"))

        self.total_time_label = tk.Label(
            self.progress_frame,
            text="00:00",
            font=("Helvetica", 10),
            bg=BG_COLOR,
            fg="#ffffff",
        )
        self.total_time_label.grid(row=0, column=6, sticky=tk.E)

        self.progress_canvas = tk.Canvas(
            self.main_frame, bg=BG_COLOR, height=6, highlightthickness=0
        )
        self.progress_canvas.pack(fill=tk.X, padx=20, pady=(0, 10), side=tk.BOTTOM)

        self.progress_fill = self.progress_canvas.create_rectangle(
            0, 0, 0, 6, fill="#e94560", outline=""
        )

    def _on_frame_configure(self, event=None):
        self.lyrics_canvas.configure(scrollregion=self.lyrics_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.lyrics_canvas.itemconfig(self.lyrics_canvas_window, width=event.width)

    def update_song_info(self, title, artist, duration):
        self.title_label.config(text=title or "Unknown Title")
        self.artist_label.config(text=artist or "Unknown Artist")
        self.total_time_label.config(text=format_display_time(duration))

        # Reset lyric offset to the default on each new song
        self.lyric_offset = 0.3
        if hasattr(self, "_offset_var"):
            self._offset_update_lock = True
            self._offset_var.set(f"{self.lyric_offset:.1f}")
            self._offset_update_lock = False

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

    def set_next_callback(self, callback):
        self._next_callback = callback

    def set_prev_callback(self, callback):
        self._prev_callback = callback

    def set_refresh_callback(self, callback):
        self._refresh_callback = callback

    def _on_next_btn_clicked(self):
        if hasattr(self, "_next_callback") and self._next_callback:
            self._next_callback()

    def _on_prev_btn_clicked(self):
        if hasattr(self, "_prev_callback") and self._prev_callback:
            self._prev_callback()

    def _on_refresh_btn_clicked(self):
        if hasattr(self, "_refresh_callback") and self._refresh_callback:
            self._refresh_callback()

    def _on_settings_btn_clicked(self, event=None):
        self.settings_menu.tk_popup(
            self.settings_btn.winfo_rootx(),
            self.settings_btn.winfo_rooty() + self.settings_btn.winfo_height(),
        )

    def _on_lyric_mode_selected(self, mode):
        """Handle lyric mode selection from the settings menu."""
        self.lyric_mode = mode
        # Call the callback set by media_sync if it exists
        if hasattr(self, "set_lyric_mode_callback") and self.set_lyric_mode_callback:
            self.set_lyric_mode_callback(mode)

    def _on_offset_var_changed(self, *args):
        if getattr(self, "_offset_update_lock", False):
            return

        try:
            value = float(self._offset_var.get())
        except ValueError:
            return

        value = round(value, 1)
        if value == self.lyric_offset:
            return

        self.lyric_offset = value
        self._offset_update_lock = True
        self._offset_var.set(f"{self.lyric_offset:.1f}")
        self._offset_update_lock = False

    def _apply_lyric_offset_from_entry(self):
        try:
            value = float(self._offset_var.get())
        except ValueError:
            value = self.lyric_offset

        value = round(value, 1)
        self.lyric_offset = value
        self._offset_var.set(f"{self.lyric_offset:.1f}")

    def _change_lyric_offset(self, delta: float):
        value = round(self.lyric_offset + delta, 1)
        self.lyric_offset = value
        if hasattr(self, "_offset_var"):
            self._offset_var.set(f"{self.lyric_offset:.1f}")

    def _increment_lyric_offset(self):
        self._change_lyric_offset(0.1)

    def _decrement_lyric_offset(self):
        self._change_lyric_offset(-0.1)

    def set_pause_button_state(self, is_paused):
        # ▶ is a narrower glyph so it needs a larger size to match ▌▌ visually
        if is_paused:
            self.pause_btn.config(text="▶", font=("Helvetica", 30), fg="#ffffff")
        else:
            self.pause_btn.config(text="▌▌", font=("Helvetica", 14), fg="#ffffff")

    def clear_lyrics(self):
        for job_id in self._anim_jobs.values():
            self.root.after_cancel(job_id)
        self._anim_jobs.clear()

        if self._scroll_job is not None:
            self.root.after_cancel(self._scroll_job)
            self._scroll_job = None

        for widget in self.lyrics_frame.winfo_children():
            widget.destroy()
        self.lyric_labels = []
        self._last_highlight_index = -1
        self._last_scroll_y = -1

    def load_lyrics(self, lyrics_data, initial_index=-1):
        self.clear_lyrics()

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
            self.lyrics_canvas.yview_moveto(0)
            return

        # Top spacer
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

        # Bottom spacer
        tk.Frame(self.lyrics_frame, bg=BG_COLOR, height=250).pack(fill=tk.X)

        self.lyrics_frame.update_idletasks()
        self._on_frame_configure()

        # After layout is committed, jump to the correct position
        self.lyrics_canvas.after_idle(
            lambda: self._apply_initial_position(initial_index)
        )

    def _apply_initial_position(self, initial_index):
        """After lyrics load, jump to the correct position without animation.
        If initial_index is valid (mid-song resume), scroll to that lyric instantly
        and style it as active so the user sees the right line immediately.
        If initial_index is -1 (new song from the start), just reset to top."""
        if initial_index > 0 and initial_index < len(self.lyric_labels):
            # Style the active line and its neighbours directly, no animation
            for i in range(len(self.lyric_labels)):
                _, label = self.lyric_labels[i]
                if i == initial_index:
                    label.config(fg="#ffffff", font=("Helvetica", 15, "bold"))
                elif i == initial_index - 1 or i == initial_index + 1:
                    label.config(fg="#aaaaaa", font=("Helvetica", 13))
                else:
                    label.config(fg="#555555", font=("Helvetica", 12))

            self._last_highlight_index = initial_index

            # Scroll directly to the active lyric
            _, label = self.lyric_labels[initial_index]
            canvas_height = self.lyrics_canvas.winfo_height()
            label_y = label.winfo_y()
            label_height = label.winfo_height()

            scroll_pos = label_y - (canvas_height / 2) + (label_height / 2)
            max_scroll = max(0, self.lyrics_frame.winfo_height() - canvas_height)
            scroll_pos = max(0, min(scroll_pos, max_scroll))

            frame_height = self.lyrics_frame.winfo_height()
            scroll_ratio = scroll_pos / frame_height if frame_height > 0 else 0
            self._last_scroll_y = scroll_ratio
            self.lyrics_canvas.yview_moveto(scroll_ratio)
        else:
            # New song starting from the beginning — reset to top
            self.lyrics_canvas.yview_moveto(0)
            self._last_scroll_y = 0

    def _rgb_to_hex(self, r, g, b):
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    def _animate_scroll(self, start_ratio, end_ratio, step, total_steps):
        """Smoothly interpolate the canvas scroll position from start_ratio to end_ratio."""
        t = step / total_steps
        # Ease-in-out: slow start, fast middle, slow finish
        t_eased = t * t * (3 - 2 * t)

        current_ratio = start_ratio + (end_ratio - start_ratio) * t_eased
        self.lyrics_canvas.yview_moveto(current_ratio)

        if step < total_steps:
            self._scroll_job = self.root.after(
                12,
                lambda: self._animate_scroll(
                    start_ratio, end_ratio, step + 1, total_steps
                ),
            )
        else:
            self._last_scroll_y = end_ratio
            self._scroll_job = None

    def _start_scroll(self, target_ratio):
        """Cancel any in-flight scroll animation and start a new one to target_ratio."""
        if abs(target_ratio - self._last_scroll_y) <= 0.005:
            return

        # Cancel previous scroll animation if one is running
        if self._scroll_job is not None:
            self.root.after_cancel(self._scroll_job)
            self._scroll_job = None

        start_ratio = self._last_scroll_y if self._last_scroll_y >= 0 else target_ratio
        self._last_scroll_y = target_ratio

        # 20 steps × 12ms ≈ 240ms smooth scroll
        self._animate_scroll(start_ratio, target_ratio, step=1, total_steps=20)

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

            # Cancel previous frame before scheduling next to avoid double-running
            if label_idx in self._anim_jobs:
                self.root.after_cancel(self._anim_jobs[label_idx])

            self._anim_jobs[label_idx] = self.root.after(15, next_frame)

    def _start_transition(self, label_idx, end_color_name, end_size, bold):
        if label_idx >= len(self.lyric_labels):
            return

        _, label = self.lyric_labels[label_idx]

        current_font = label.cget("font")
        if isinstance(current_font, tuple):
            start_size = current_font[1]
        else:
            parts = str(current_font).split()
            start_size = int(parts[1]) if len(parts) > 1 else end_size

        current_color = label.cget("fg")
        start_rgb = COLOR_MAP.get(current_color, COLOR_MAP["#555555"])
        end_rgb = self._colors[end_color_name]

        if label_idx in self._anim_jobs:
            self.root.after_cancel(self._anim_jobs[label_idx])
            del self._anim_jobs[label_idx]

        # 16 steps × 15ms ≈ 240ms label transition
        self._animate_label(
            label_idx, start_rgb, end_rgb, start_size, end_size, bold, 1, 16
        )

    def highlight_lyric(self, index):
        if not self.lyric_labels:
            return

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

        # Calculate target scroll ratio and animate smoothly to it
        _, label = self.lyric_labels[index]
        canvas_height = self.lyrics_canvas.winfo_height()
        label_y = label.winfo_y()
        label_height = label.winfo_height()

        scroll_pos = label_y - (canvas_height / 2) + (label_height / 2)
        max_scroll = max(0, self.lyrics_frame.winfo_height() - canvas_height)
        scroll_pos = max(0, min(scroll_pos, max_scroll))

        frame_height = self.lyrics_frame.winfo_height()
        scroll_ratio = scroll_pos / frame_height if frame_height > 0 else 0

        self._start_scroll(scroll_ratio)
