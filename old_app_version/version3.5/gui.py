import tkinter as tk
from tkinter import font as tkfont

from config import *
from lyrics_utils import (
    format_display_time,
    COLOR_MAP,
    to_romaji,
    to_pinyin,
    to_romanized_korean,
)
from settings_window import SettingsWindow


#  Constants 
SPACER_HEIGHT = 250
LYRIC_H_MARGIN = 12
CANVAS_H_MARGIN = 8
MIN_WRAP_WIDTH = 100
FONT_FAMILY = "Helvetica"

# Animation timing
SCROLL_DURATION_MS = 100
LABEL_ANIM_DURATION_MS = 60
SCROLL_FPS = 120
LABEL_FPS = 120
SCROLL_STEP_MS = max(8, int(1000 / SCROLL_FPS))  # 16ms = ~60fps
LABEL_STEP_MS = max(8, int(1000 / LABEL_FPS))    # 16ms = ~60fps
SCROLL_STEPS = max(8, SCROLL_DURATION_MS // SCROLL_STEP_MS)
LABEL_STEPS = max(8, LABEL_ANIM_DURATION_MS // LABEL_STEP_MS)
SCROLL_THRESHOLD = 0.003
RECENTER_DEBOUNCE_MS = 100


class LyricsApp:
    """Main GUI controller for the lyrics player."""

    def __init__(self, root):
        self.root = root
        self._font_cache = {}
        self.lyric_offset = 0.3
        self.lyric_mode = "original"
        self._detected_language = "other"

        self._pinned = False

        self._build_window()
        self._build_info_panel()
        self._build_translation_bar()
        self._build_lyrics_panel()
        self._build_progress_bar()

        self.lyric_labels = []
        self._last_highlight_index = -1
        self._anim_jobs = {}
        self._last_scroll_y = -1
        self._scroll_job = None
        self._recenter_job = None

        self._colors = {
            "active": COLOR_MAP[COLOR_ACTIVE_FG],
            "nearby": COLOR_MAP[COLOR_NEARBY_FG],
            "far": COLOR_MAP[COLOR_FAR_FG],
        }

        self.font_size_active = 16
        self.font_size_nearby = 13
        self.font_size_far = 12

        self.lyrics_frame.bind("<Configure>", self._on_frame_configure)
        self.lyrics_canvas.bind("<Configure>", self._on_canvas_configure)

    #  Font Helpers 

    def _get_cached_font(self, size, bold=False):
        """Return a cached font object to avoid expensive recreation."""
        key = (size, bold)
        if key not in self._font_cache:
            weight = "bold" if bold else "normal"
            self._font_cache[key] = tkfont.Font(
                family=FONT_FAMILY, size=size, weight=weight
            )
        return self._font_cache[key]

    @property
    def _active_font(self):
        return (FONT_FAMILY, self.font_size_active, "bold")

    @property
    def _nearby_font(self):
        return (FONT_FAMILY, self.font_size_nearby)

    @property
    def _far_font(self):
        return (FONT_FAMILY, self.font_size_far)

    #  UI Helpers 

    def _bind_hover(self, widget, active_color=COLOR_ERROR_FG, inactive_color=COLOR_ACTIVE_FG):
        """Bind Enter/Leave events to toggle widget foreground color."""
        widget.bind("<Enter>", lambda e: widget.config(fg=active_color))
        widget.bind("<Leave>", lambda e: widget.config(fg=inactive_color))

    def _make_clickable_label(self, parent, text, font_size, fg=COLOR_ACTIVE_FG,
                              side=None, padx=0, pady=0, click_handler=None):
        """Create a Label with hand cursor, hover effect, and click binding."""
        label = tk.Label(
            parent, text=text, font=(FONT_FAMILY, font_size),
            bg=parent.cget("bg"), fg=fg, cursor="hand2"
        )
        if side is not None:
            label.pack(side=side, padx=padx, pady=pady)
        else:
            label.pack(padx=padx, pady=pady)
        if click_handler:
            label.bind("<Button-1>", click_handler)
        self._bind_hover(label)
        return label

    def _calc_scroll_ratio(self, label):
        """Calculate the scroll ratio to center a given label in the canvas."""
        canvas_height = self.lyrics_canvas.winfo_height()
        label_y = label.winfo_y()
        label_height = label.winfo_height()

        scroll_pos = label_y - (canvas_height / 2) + (label_height / 2)
        max_scroll = max(0, self.lyrics_frame.winfo_height() - canvas_height)
        scroll_pos = max(0, min(scroll_pos, max_scroll))

        frame_height = self.lyrics_frame.winfo_height()
        return scroll_pos / frame_height if frame_height > 0 else 0

    #  Window 

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

    #  Info Panel 

    def _build_info_panel(self):
        self.info_frame = tk.Frame(self.main_frame, bg=ACCENT_COLOR)
        self.info_frame.pack(fill=tk.X, padx=10, pady=10)

        self.settings_menu = tk.Menu(self.root, tearoff=0)

        self._offset_var = tk.StringVar(value=f"{self.lyric_offset:.1f}")
        self._offset_var.trace_add("write", self._on_offset_var_changed)

        top_button_row = tk.Frame(self.info_frame, bg=ACCENT_COLOR)
        top_button_row.pack(fill=tk.X, padx=10, pady=(10, 0))

        self.pin_btn = tk.Label(
            top_button_row,
            text="📌",
            font=(FONT_FAMILY, 14),
            bg=ACCENT_COLOR,
            fg=COLOR_FAR_FG,
            cursor="hand2",
        )
        self.pin_btn.pack(side=tk.RIGHT, padx=(0, 4))
        self.pin_btn.bind("<Button-1>", lambda e: self._toggle_pin())

        self.title_label = tk.Label(
            self.info_frame,
            text="No song playing",
            font=(FONT_FAMILY, 16, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ERROR_FG,
            wraplength=WINDOW_WIDTH - 80,
            justify=tk.CENTER,
        )
        self.title_label.pack(pady=(20, 4), padx=20)

        self.artist_label = tk.Label(
            self.info_frame,
            text="Waiting...",
            font=(FONT_FAMILY, 12),
            bg=ACCENT_COLOR,
            fg=COLOR_ARTIST_FG,
            wraplength=WINDOW_WIDTH - 80,
            justify=tk.CENTER,
        )
        self.artist_label.pack(padx=20, pady=(0, 8))

        button_row = tk.Frame(self.info_frame, bg=ACCENT_COLOR)
        button_row.pack(fill=tk.X, padx=10, pady=(0, 12))

        self.refresh_btn = self._make_clickable_label(
            button_row, "⟳", 18, side=tk.LEFT,
            click_handler=lambda e: self._on_refresh_btn_clicked()
        )

        offset_frame = tk.Frame(button_row, bg=ACCENT_COLOR)
        offset_frame.pack(side=tk.LEFT, expand=True)

        tk.Label(
            offset_frame,
            text="Offset:",
            font=(FONT_FAMILY, 14, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
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
            font=(FONT_FAMILY, 11),
        )
        self.offset_entry.pack(side=tk.LEFT, padx=4)

        tk.Button(
            offset_frame,
            text="+",
            width=2,
            command=self._increment_lyric_offset,
        ).pack(side=tk.LEFT)

        self.settings_btn = self._make_clickable_label(
            button_row, "⚙", 18, side=tk.RIGHT,
            click_handler=self._on_settings_btn_clicked
        )

    #  Translation Bar 

    def _build_translation_bar(self):
        self.translation_bar = tk.Frame(self.main_frame, bg=ACCENT_COLOR, height=32)
        self.translation_bar.pack(fill=tk.X, padx=10, pady=(0, 4))
        self.translation_bar.pack_propagate(False)

        tk.Label(
            self.translation_bar,
            text="Language:",
            font=(FONT_FAMILY, 9),
            bg=ACCENT_COLOR,
            fg=COLOR_ARTIST_FG,
        ).pack(side=tk.LEFT, padx=(10, 2))

        self.lang_value_label = tk.Label(
            self.translation_bar,
            text="—",
            font=(FONT_FAMILY, 9, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
        )
        self.lang_value_label.pack(side=tk.LEFT, padx=(0, 14))

        tk.Label(
            self.translation_bar,
            text="Current:",
            font=(FONT_FAMILY, 9),
            bg=ACCENT_COLOR,
            fg=COLOR_ARTIST_FG,
        ).pack(side=tk.LEFT, padx=(0, 2))

        self.mode_value_label = tk.Label(
            self.translation_bar,
            text="Original",
            font=(FONT_FAMILY, 9, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
        )
        self.mode_value_label.pack(side=tk.LEFT)

        self.trans_btn_original = tk.Label(
            self.translation_bar,
            text="[ Ori ]",
            font=(FONT_FAMILY, 9, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ERROR_FG,
            cursor="hand2",
        )
        self.trans_btn_original.pack(side=tk.RIGHT, padx=(0, 6))
        self.trans_btn_original.bind(
            "<Button-1>", lambda e: self._on_translation_toggle("original")
        )

        self.trans_btn_translated = tk.Label(
            self.translation_bar,
            text="[ Rom ]",
            font=(FONT_FAMILY, 9),
            bg=ACCENT_COLOR,
            fg=COLOR_FAR_FG,
            cursor="hand2",
        )
        self.trans_btn_translated.pack(side=tk.RIGHT, padx=(0, 4))
        self.trans_btn_translated.bind(
            "<Button-1>", lambda e: self._on_translation_toggle(self._translation_mode)
        )
        self.trans_btn_translated.pack_forget()

        self._translation_mode = None

    def _on_translation_toggle(self, mode):
        self._on_lyric_mode_selected(mode)
        self._update_translation_bar_state()

    def _update_translation_bar_state(self):
        """Refresh button colours and Current label to reflect the active lyric_mode."""
        is_original = self.lyric_mode == "original"
        self.trans_btn_original.config(fg=COLOR_ERROR_FG if is_original else COLOR_FAR_FG)
        self.trans_btn_translated.config(fg=COLOR_ERROR_FG if not is_original else COLOR_FAR_FG)

        mode_names = {
            "original": "Original",
            "romaji": "Romaji",
            "pinyin": "Pinyin",
            "romaja": "Romaja",
        }
        self.mode_value_label.config(text=mode_names.get(self.lyric_mode, "Original"))

    #  Lyrics Panel 

    def _build_lyrics_panel(self):
        self.lyrics_container = tk.Frame(self.main_frame, bg=BG_COLOR)
        self.lyrics_container.pack(fill=tk.BOTH, expand=True, padx=4, pady=10)

        self.lyrics_canvas = tk.Canvas(
            self.lyrics_container, bg=BG_COLOR, highlightthickness=0
        )
        self.lyrics_canvas.pack(fill=tk.BOTH, expand=True)

        self.lyrics_frame = tk.Frame(self.lyrics_canvas, bg=BG_COLOR)
        self.lyrics_canvas_window = self.lyrics_canvas.create_window(
            (0, 0), window=self.lyrics_frame, anchor=tk.NW,
            width=WINDOW_WIDTH - CANVAS_H_MARGIN
        )

    #  Progress Bar 

    def _build_progress_bar(self):
        self.status_label = tk.Label(
            self.main_frame,
            text="Initializing...",
            font=(FONT_FAMILY, 9),
            bg=BG_COLOR,
            fg=COLOR_STATUS_FG,
        )
        self.status_label.pack(side=tk.BOTTOM, pady=10)

        self.progress_frame = tk.Frame(self.main_frame, bg=BG_COLOR, height=40)
        self.progress_frame.pack(fill=tk.X, padx=20, pady=5, side=tk.BOTTOM)
        self.progress_frame.pack_propagate(False)

        for i, weight in enumerate([0, 1, 0, 0, 0, 1, 0]):
            self.progress_frame.grid_columnconfigure(i, weight=weight)
        self.progress_frame.grid_rowconfigure(0, minsize=56)

        self.current_time_label = tk.Label(
            self.progress_frame,
            text="00:00",
            font=(FONT_FAMILY, 10),
            bg=BG_COLOR,
            fg=COLOR_ACTIVE_FG,
        )
        self.current_time_label.grid(row=0, column=0, sticky=tk.W)

        self.prev_btn = self._make_clickable_label(
            self.progress_frame, "◀◀", 20,
            click_handler=lambda e: self._on_prev_btn_clicked()
        )
        self.prev_btn.grid(row=0, column=2, padx=10)

        self.pause_btn_frame = tk.Frame(self.progress_frame, bg=BG_COLOR, width=48, height=48)
        self.pause_btn_frame.grid(row=0, column=3, padx=10)
        self.pause_btn_frame.grid_propagate(False)

        self.pause_btn = tk.Label(
            self.pause_btn_frame,
            text="▌▌",
            font=(FONT_FAMILY, 14),
            bg=BG_COLOR,
            fg=COLOR_ACTIVE_FG,
            cursor="hand2",
            anchor="center",
            justify=tk.CENTER,
        )
        self.pause_btn.pack(fill=tk.BOTH, expand=True)
        self.pause_btn.bind("<Button-1>", lambda e: self._on_pause_btn_clicked())
        self._bind_hover(self.pause_btn)

        self.next_btn = self._make_clickable_label(
            self.progress_frame, "▶▶", 20,
            click_handler=lambda e: self._on_next_btn_clicked()
        )
        self.next_btn.grid(row=0, column=4, padx=10)

        self.total_time_label = tk.Label(
            self.progress_frame,
            text="00:00",
            font=(FONT_FAMILY, 10),
            bg=BG_COLOR,
            fg=COLOR_ACTIVE_FG,
        )
        self.total_time_label.grid(row=0, column=6, sticky=tk.E)

        self.progress_canvas = tk.Canvas(
            self.main_frame, bg=BG_COLOR, height=6, highlightthickness=0
        )
        self.progress_canvas.pack(fill=tk.X, padx=20, pady=(0, 10), side=tk.BOTTOM)

        self.progress_fill = self.progress_canvas.create_rectangle(
            0, 0, 0, 6, fill=COLOR_ERROR_FG, outline=""
        )

    #  Scroll / Recenter 

    def _schedule_recenter(self):
        """Debounce recenter to avoid lag during rapid resize events."""
        if getattr(self, "_recenter_job", None) is not None:
            self.root.after_cancel(self._recenter_job)
        self._recenter_job = self.root.after(RECENTER_DEBOUNCE_MS, self._recenter_active_lyric)

    def _recenter_active_lyric(self):
        """Instantly jump to center the active lyric."""
        self._recenter_job = None

        if not self.lyric_labels or self._last_highlight_index < 0:
            return

        if self._scroll_job is not None:
            self.root.after_cancel(self._scroll_job)
            self._scroll_job = None

        index = min(self._last_highlight_index, len(self.lyric_labels) - 1)
        _, label = self.lyric_labels[index]

        scroll_ratio = self._calc_scroll_ratio(label)
        self._last_scroll_y = scroll_ratio
        self.lyrics_canvas.yview_moveto(scroll_ratio)

    #  Hard Wrapping 

    def _apply_hard_wrapping(self, text, base_wrap_width):
        """Calculate exact line breaks using the active (largest) font size."""
        if not text:
            return text

        measure_font = self._get_cached_font(self.font_size_active, bold=True)
        if measure_font.measure(text) <= base_wrap_width:
            return text

        lines, current_line = [], ""
        items = text.split(" ") if " " in text else text
        delimiter = " " if " " in text else ""

        for item in items:
            test_line = current_line + (delimiter if current_line else "") + item
            if measure_font.measure(test_line) <= base_wrap_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = item

        if current_line:
            lines.append(current_line)
        return "\n".join(lines)

    def _get_base_wrap_width(self):
        """Calculate current base wrap width from canvas dimensions."""
        canvas_width = self.lyrics_canvas.winfo_width()
        if canvas_width < 50:
            canvas_width = WINDOW_WIDTH
        return max(MIN_WRAP_WIDTH, canvas_width - LYRIC_H_MARGIN)

    def _update_wraplengths(self):
        """Re-wrap all lyric labels to match current canvas width."""
        base_wrap_width = self._get_base_wrap_width()

        for _, label in self.lyric_labels:
            if hasattr(label, "original_text"):
                hard_wrapped_text = self._apply_hard_wrapping(
                    label.original_text, base_wrap_width
                )
                label.config(text=hard_wrapped_text, wraplength=0)

    #  Event Handlers 

    def _on_frame_configure(self, event=None):
        self.lyrics_canvas.configure(scrollregion=self.lyrics_canvas.bbox("all"))
        self._schedule_recenter()

    def _on_canvas_configure(self, event):
        self.lyrics_canvas.itemconfig(self.lyrics_canvas_window, width=event.width)
        self._update_wraplengths()
        self._schedule_recenter()

    #  Public Update Methods 

    def update_song_info(self, title, artist, duration):
        self.title_label.config(text=title or "Unknown Title")
        self.artist_label.config(text=artist or "Unknown Artist")
        self.total_time_label.config(text=format_display_time(duration))

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

    #  Callback Wiring 

    def set_pause_callback(self, callback):
        self._pause_callback = callback

    def set_next_callback(self, callback):
        self._next_callback = callback

    def set_prev_callback(self, callback):
        self._prev_callback = callback

    def set_refresh_callback(self, callback):
        self._refresh_callback = callback

    def _toggle_pin(self):
        """Toggle always-on-top for the main window."""
        self._pinned = not self._pinned
        self.root.attributes("-topmost", self._pinned)
        self.pin_btn.config(fg=COLOR_ERROR_FG if self._pinned else COLOR_FAR_FG)

    def _on_pause_btn_clicked(self):
        if getattr(self, "_pause_callback", None):
            self._pause_callback()

    def _on_next_btn_clicked(self):
        if getattr(self, "_next_callback", None):
            self._next_callback()

    def _on_prev_btn_clicked(self):
        if getattr(self, "_prev_callback", None):
            self._prev_callback()

    def _on_refresh_btn_clicked(self):
        if getattr(self, "_refresh_callback", None):
            self._refresh_callback()

    def _on_settings_btn_clicked(self, event=None):
        SettingsWindow(self.root, self)

    #  Lyric Mode 

    def _on_lyric_mode_selected(self, mode):
        """Handle lyric mode selection from settings menu or translation bar."""
        self.lyric_mode = mode
        self._update_translation_bar_state()
        if getattr(self, "set_lyric_mode_callback", None):
            self.set_lyric_mode_callback(mode)

    def set_detected_language(self, language):
        """Update translation bar after lyrics are loaded with detected language."""
        self._detected_language = language
        self.lyric_mode = "original"

        lang_display = {
            "japanese": ("Japanese", "romaji", "[ Rom ]"),
            "chinese": ("Chinese", "pinyin", "[ Pin ]"),
            "korean": ("Korean", "romaja", "[ Rom ]"),
            "other": ("Other", None, None),
        }
        display_name, trans_mode, btn_label = lang_display.get(
            language, ("Other", None, None)
        )

        self.lang_value_label.config(text=display_name)
        self._translation_mode = trans_mode

        if trans_mode:
            self.trans_btn_translated.config(text=btn_label)
            self.trans_btn_translated.pack(side=tk.RIGHT, padx=(0, 4))
        else:
            self.trans_btn_translated.pack_forget()

        self._update_translation_bar_state()

    #  Offset Management 

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

    def _change_lyric_offset(self, delta: float):
        value = round(self.lyric_offset + delta, 1)
        self.lyric_offset = value
        if hasattr(self, "_offset_var"):
            self._offset_var.set(f"{self.lyric_offset:.1f}")

    def _increment_lyric_offset(self):
        self._change_lyric_offset(0.1)

    def _decrement_lyric_offset(self):
        self._change_lyric_offset(-0.1)

    #  Pause Button State 

    def set_pause_button_state(self, is_paused):
        if is_paused:
            self.pause_btn.config(text="▶", font=(FONT_FAMILY, 30), fg=COLOR_ACTIVE_FG)
        else:
            self.pause_btn.config(text="▌▌", font=(FONT_FAMILY, 14), fg=COLOR_ACTIVE_FG)

    #  Lyric Loading 

    def clear_lyrics(self):
        for job_id in self._anim_jobs.values():
            self.root.after_cancel(job_id)
        self._anim_jobs.clear()

        if self._scroll_job is not None:
            self.root.after_cancel(self._scroll_job)
            self._scroll_job = None

        if getattr(self, "_recenter_job", None) is not None:
            self.root.after_cancel(self._recenter_job)
            self._recenter_job = None

        for widget in self.lyrics_frame.winfo_children():
            widget.destroy()
        self.lyric_labels = []
        self._last_highlight_index = -1
        self._last_scroll_y = -1

    def _get_display_text(self, text):
        """Apply translation based on current lyric_mode and detected language."""
        if self.lyric_mode == "romaji" and self._detected_language == "japanese":
            return to_romaji(text)
        elif self.lyric_mode == "pinyin" and self._detected_language == "chinese":
            return to_pinyin(text)
        elif self.lyric_mode == "romaja" and self._detected_language == "korean":
            return to_romanized_korean(text)
        return text

    def load_lyrics(self, lyrics_data, initial_index=-1):
        self.clear_lyrics()

        if not lyrics_data:
            no_lyrics_label = tk.Label(
                self.lyrics_frame,
                text="No lyrics found\n\nTry a different song",
                font=(FONT_FAMILY, 14),
                bg=BG_COLOR,
                fg=COLOR_ERROR_FG,
                wraplength=WINDOW_WIDTH - 60,
                justify=tk.CENTER,
                pady=20,
            )
            no_lyrics_label.pack(expand=True, fill=tk.BOTH)
            self.lyrics_frame.update_idletasks()
            self._on_frame_configure()
            self.lyrics_canvas.yview_moveto(0)
            return

        tk.Frame(self.lyrics_frame, bg=BG_COLOR, height=SPACER_HEIGHT).pack(fill=tk.X)

        base_wrap_width = self._get_base_wrap_width()

        for timestamp, text in lyrics_data:
            display_text = self._get_display_text(text)

            label = tk.Label(
                self.lyrics_frame,
                font=self._far_font,
                bg=BG_COLOR,
                fg=COLOR_MUTED_FG,
                wraplength=0,
                justify=tk.CENTER,
                pady=12,
            )
            label.original_text = display_text
            label.config(text=self._apply_hard_wrapping(display_text, base_wrap_width))
            label.pack(fill=tk.X)
            self.lyric_labels.append((timestamp, label))

        tk.Frame(self.lyrics_frame, bg=BG_COLOR, height=SPACER_HEIGHT).pack(fill=tk.X)

        self.lyrics_frame.update_idletasks()
        self._on_frame_configure()
        self.lyrics_canvas.after_idle(
            lambda: self._apply_initial_position(initial_index)
        )

    #  Initial Position 

    def _apply_initial_position(self, initial_index):
        """Jump to correct position instantly after lyrics load."""
        if initial_index > 0 and initial_index < len(self.lyric_labels):
            for i in range(len(self.lyric_labels)):
                _, label = self.lyric_labels[i]
                if i == initial_index:
                    label.config(fg=COLOR_ACTIVE_FG, font=self._active_font)
                elif i in (initial_index - 1, initial_index + 1):
                    label.config(fg=COLOR_NEARBY_FG, font=self._nearby_font)
                else:
                    label.config(fg=COLOR_FAR_FG, font=self._far_font)

            self._last_highlight_index = initial_index

            _, label = self.lyric_labels[initial_index]
            scroll_ratio = self._calc_scroll_ratio(label)
            self._last_scroll_y = scroll_ratio
            self.lyrics_canvas.yview_moveto(scroll_ratio)
        else:
            self.lyrics_canvas.yview_moveto(0)
            self._last_scroll_y = 0

    #  Color / Animation Helpers 

    def _rgb_to_hex(self, r, g, b):
        return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

    def _ease_in_out(self, t):
        return t * t * (3 - 2 * t)

    def _ease_out(self, t):
        return 1 - (1 - t) ** 2

    #  Scroll Animation 

    def _animate_scroll(self, start_ratio, end_ratio, step, total_steps):
        t = step / total_steps
        t_eased = self._ease_in_out(t)
        current_ratio = start_ratio + (end_ratio - start_ratio) * t_eased
        self.lyrics_canvas.yview_moveto(current_ratio)

        if step < total_steps:
            self._scroll_job = self.root.after(
                SCROLL_STEP_MS,
                lambda: self._animate_scroll(
                    start_ratio, end_ratio, step + 1, total_steps
                ),
            )
        else:
            self._last_scroll_y = end_ratio
            self._scroll_job = None

    def _start_scroll(self, target_ratio):
        if abs(target_ratio - self._last_scroll_y) <= SCROLL_THRESHOLD:
            return

        if self._scroll_job is not None:
            self.root.after_cancel(self._scroll_job)
            self._scroll_job = None

        start_ratio = self._last_scroll_y if self._last_scroll_y >= 0 else target_ratio
        self._last_scroll_y = target_ratio
        self._animate_scroll(start_ratio, target_ratio, step=1, total_steps=SCROLL_STEPS)

    #  Label Animation 

    def _animate_label(self, label_idx, start_rgb, end_rgb, start_size, end_size,
                       bold, step, total_steps):
        if label_idx >= len(self.lyric_labels):
            return

        t = step / total_steps
        t_eased = self._ease_out(t)

        sr, sg, sb = start_rgb
        er, eg, eb = end_rgb
        r = sr + (er - sr) * t_eased
        g = sg + (eg - sg) * t_eased
        b = sb + (eb - sb) * t_eased
        color = self._rgb_to_hex(r, g, b)

        size = round(start_size + (end_size - start_size) * t_eased)
        font_spec = (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)

        _, label = self.lyric_labels[label_idx]
        label.config(fg=color, font=font_spec)

        if step < total_steps:
            def next_frame(idx=label_idx, sr=start_rgb, er=end_rgb,
                           ss=start_size, es=end_size, b=bold,
                           s=step + 1, ts=total_steps):
                self._animate_label(idx, sr, er, ss, es, b, s, ts)

            if label_idx in self._anim_jobs:
                self.root.after_cancel(self._anim_jobs[label_idx])

            self._anim_jobs[label_idx] = self.root.after(LABEL_STEP_MS, next_frame)

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
        start_rgb = COLOR_MAP.get(current_color, COLOR_MAP[COLOR_FAR_FG])
        end_rgb = self._colors[end_color_name]

        if COLOR_MAP.get(current_color) == end_rgb:
            return

        if label_idx in self._anim_jobs:
            self.root.after_cancel(self._anim_jobs[label_idx])
            del self._anim_jobs[label_idx]

        self._animate_label(
            label_idx, start_rgb, end_rgb, start_size, end_size, bold, 1, LABEL_STEPS
        )

    #  Highlighting 

    def highlight_lyric(self, index):
        if not self.lyric_labels or index == self._last_highlight_index:
            return

        prev = self._last_highlight_index
        self._last_highlight_index = index

        affected = set()
        for idx in (prev - 1, prev, prev + 1, index - 1, index, index + 1):
            if 0 <= idx < len(self.lyric_labels):
                affected.add(idx)

        for i in affected:
            if i == index:
                self._start_transition(i, "active", self.font_size_active, True)
            elif i in (index - 1, index + 1):
                self._start_transition(i, "nearby", self.font_size_nearby, False)
            else:
                self._start_transition(i, "far", self.font_size_far, False)

        self._start_scroll_to_index(index)

    #  Dynamic Scroll 

    def _start_scroll_to_index(self, index):
        if self._scroll_job is not None:
            self.root.after_cancel(self._scroll_job)

        start_ratio = self.lyrics_canvas.yview()[0]
        self._animate_scroll_dynamic(index, start_ratio, step=1, total_steps=SCROLL_STEPS)

    def _animate_scroll_dynamic(self, target_idx, start_ratio, step, total_steps):
        self.lyrics_frame.update_idletasks()

        _, label = self.lyric_labels[target_idx]
        canvas_height = self.lyrics_canvas.winfo_height()
        frame_height = self.lyrics_frame.winfo_height()

        label_y = label.winfo_y()
        label_height = label.winfo_height()

        target_pos = label_y - (canvas_height / 2) + (label_height / 2)
        max_scroll = max(0, frame_height - canvas_height)
        target_pos = max(0, min(target_pos, max_scroll))

        end_ratio = target_pos / frame_height if frame_height > 0 else 0

        t_eased = self._ease_in_out(step / total_steps)
        current_ratio = start_ratio + (end_ratio - start_ratio) * t_eased

        self.lyrics_canvas.yview_moveto(current_ratio)
        self._last_scroll_y = current_ratio

        if step < total_steps:
            self._scroll_job = self.root.after(
                SCROLL_STEP_MS,
                lambda: self._animate_scroll_dynamic(
                    target_idx, start_ratio, step + 1, total_steps
                ),
            )
        else:
            self._scroll_job = None