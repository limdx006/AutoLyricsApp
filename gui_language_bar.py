import tkinter as tk
from config import *


class ToggleSwitch(tk.Canvas):
    """Compact pill-shaped on/off switch with a smooth sliding knob (0=off, 1=on)."""

    _WIDTH = 30
    _HEIGHT = 13
    _PAD = 2
    _EASE = 0.4  # fraction of remaining distance covered per animation tick
    _ARROW_COLOR = ACCENT_COLOR  # arrow drawn in the bar's own bg so it reads clearly on the white knob

    def __init__(self, parent, bg, on_toggle=None, **kwargs):
        super().__init__(parent, width=self._WIDTH, height=self._HEIGHT, bg=bg, highlightthickness=0, **kwargs)
        self._on_toggle = on_toggle
        self.state = 0
        self._knob_d = self._HEIGHT - self._PAD * 2  # knob diameter

        self._track_id = self._rounded_rect(0, 0, self._WIDTH, self._HEIGHT, self._HEIGHT / 2, fill=COLOR_FAR_FG)
        self._knob_id = self.create_oval(
            self._PAD, self._PAD, self._PAD + self._knob_d, self._HEIGHT - self._PAD,
            fill=COLOR_ACTIVE_FG, outline="",
        )
        # Small right-pointing arrow drawn on top of the knob, shown only when on
        self._arrow_id = self.create_polygon(0, 0, 0, 0, 0, 0, fill=self._ARROW_COLOR, outline="", state="hidden")
        self._position_arrow(self._PAD, self._PAD, self._PAD + self._knob_d, self._HEIGHT - self._PAD)
        self.bind("<Button-1>", lambda e: self.toggle())

    def _rounded_rect(self, x1, y1, x2, y2, r, **kwargs):
        # Pill shape via a smoothed polygon through the four corner regions
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.create_polygon(points, smooth=True, outline="", **kwargs)

    def _position_arrow(self, x1, y1, x2, y2):
        # Small triangle centered in the knob's current bounding box, pointing right
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        s = self._knob_d * 0.3
        self.coords(self._arrow_id, cx - s, cy - s, cx - s, cy + s, cx + s, cy)

    def _off_knob_x(self):
        return self._PAD

    def _on_knob_x(self):
        return self._WIDTH - self._PAD - self._knob_d

    def toggle(self):
        """Flip the switch and animate the knob/track/arrow to the new state."""
        self.state = 0 if self.state else 1
        self.itemconfig(self._track_id, fill=ERROR_COLOR if self.state else COLOR_FAR_FG)
        self.itemconfig(self._arrow_id, state="normal" if self.state else "hidden")
        self._animate_knob()
        if self._on_toggle:
            self._on_toggle(self.state)

    def reset(self):
        """Snap back to off instantly (e.g. on song change) - no animation, no callback."""
        self.state = 0
        self.itemconfig(self._track_id, fill=COLOR_FAR_FG)
        self.itemconfig(self._arrow_id, state="hidden")
        x1 = self._off_knob_x()
        self.coords(self._knob_id, x1, self._PAD, x1 + self._knob_d, self._HEIGHT - self._PAD)
        self._position_arrow(x1, self._PAD, x1 + self._knob_d, self._HEIGHT - self._PAD)

    def _animate_knob(self):
        target = self._on_knob_x() if self.state else self._off_knob_x()
        current = self.coords(self._knob_id)[0]
        diff = target - current
        x1 = target if abs(diff) < 0.5 else current + diff * self._EASE
        x2 = x1 + self._knob_d
        self.coords(self._knob_id, x1, self._PAD, x2, self._HEIGHT - self._PAD)
        self._position_arrow(x1, self._PAD, x2, self._HEIGHT - self._PAD)
        if abs(diff) >= 0.5:
            self.after(15, self._animate_knob)


class LanguageBar(tk.Frame):
    """
    Below top section for language detect and translation
    Korean and Japanese to Romaji
    Chinese to PinYin
    """

    # Languages with no translation mode - switch stays hidden for these
    _NO_TRANSLATION_LANGUAGES = {"English", "Unknown"}
    # Display mode shown when the switch is on, per detected language
    _TRANSLATION_MODE = {"Chinese": "PinYin", "Japanese": "Romaji", "Korean": "Romaji"}

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=ACCENT_COLOR, **kwargs)
        self._current_language = "Unknown"

        # Fixed height = 10% of window height below song details
        self.configure(height=int(WINDOW_HEIGHT * 0.1))
        self.pack_propagate(False)
        # Add margin around the frame when packed
        self.pack_configure(padx=10, pady=5)

        # Layout: three columns - language info, switch button, current info.
        # minsize on column 1 reserves its width even when the switch is hidden.
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1, minsize=54)
        self.grid_columnconfigure(2, weight=1)

        # Left side: Language label and value
        left_frame = tk.Frame(self, bg=ACCENT_COLOR)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=0)
        tk.Label(
            left_frame,
            text="Language:",
            font=(FONT_FAMILY, 8, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
        ).pack()
        self.language_value_label = tk.Label(
            left_frame,
            text="Unknown",
            font=(FONT_FAMILY, 8),
            bg=ACCENT_COLOR,
            fg=COLOR_NEARBY_FG,
        )
        self.language_value_label.pack()

        # Center: "Translate" label + toggle switch. Same sticky as left/right
        # so all three tops line up; column minsize (above) reserves the
        # width even when hidden, so no fixed frame size is needed here.
        self.switch_frame = tk.Frame(self, bg=ACCENT_COLOR)
        self.switch_frame.grid(row=0, column=1, sticky="nsew")
        self._translate_label = tk.Label(
            self.switch_frame,
            text="Translate?",
            font=(FONT_FAMILY, 8, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
        )
        self.language_switch = ToggleSwitch(self.switch_frame, bg=ACCENT_COLOR, on_toggle=self._on_switch_toggle)
        self._set_switch_visible(False)

        # Right side: Current label and value
        right_frame = tk.Frame(self, bg=ACCENT_COLOR)
        right_frame.grid(row=0, column=2, sticky="nsew", padx=5, pady=0)
        tk.Label(
            right_frame,
            text="Current:",
            font=(FONT_FAMILY, 8, "bold"),
            bg=ACCENT_COLOR,
            fg=COLOR_ACTIVE_FG,
        ).pack()
        self.current_value_label = tk.Label(
            right_frame,
            text="Original",
            font=(FONT_FAMILY, 8),
            bg=ACCENT_COLOR,
            fg=COLOR_NEARBY_FG,
        )
        self.current_value_label.pack()

    def _set_switch_visible(self, visible):
        """Show/hide the label+switch contents without touching the frame itself, so the reserved column width/height never changes."""
        if visible:
            self._translate_label.pack()
            self.language_switch.pack(pady=(1, 0))
        else:
            self._translate_label.pack_forget()
            self.language_switch.pack_forget()

    def _on_switch_toggle(self, state):
        """Update the Current: label to match the switch state and detected language."""
        mode = self._TRANSLATION_MODE.get(self._current_language, "Original") if state else "Original"
        self.current_value_label.config(text=mode)

    def set_language(self, language_text):
        """Update the detected-language value, reset to Original, and show/hide the switch accordingly."""
        self.language_value_label.config(text=language_text)
        self._current_language = language_text
        self._set_switch_visible(language_text not in self._NO_TRANSLATION_LANGUAGES)
        self.language_switch.reset()
        self.current_value_label.config(text="Original")