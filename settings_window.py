import tkinter as tk
import config

"""SETTINGS WINDOW - A modal preference window that lets the user change the window
size and lyric font size using preset values. Changes apply immediately so the user
can see the effect without closing the window. Calls back into the GUI via the
apply_callback so it never imports from gui.py directly."""

# Preset options — (display label, value)
WINDOW_SIZE_PRESETS = [
    ("Small  — 360 × 640", (360, 640)),
    ("Medium — 400 × 700", (400, 700)),
    ("Default — 400 × 800", (400, 800)),
    ("Large  — 440 × 900", (440, 900)),
    ("Wide   — 500 × 800", (500, 800)),
]

FONT_SIZE_PRESETS = [
    ("Small  — 14 / 12 / 11", {"active": 14, "nearby": 12, "far": 11}),
    ("Default — 16 / 13 / 12", {"active": 16, "nearby": 13, "far": 12}),
    ("Large  — 18 / 14 / 13", {"active": 18, "nearby": 14, "far": 13}),
    ("XLarge — 20 / 16 / 14", {"active": 20, "nearby": 16, "far": 14}),
]


class SettingsWindow:
    def __init__(self, parent, app):
        """Open the settings window as a modal on top of the main window.

        parent  — the root Tk window
        app     — the LyricsApp instance, used to read current values and apply changes
        """
        self._app = app
        self._win = tk.Toplevel(parent)
        self._win.title("Settings")
        self._win.configure(bg=config.BG_COLOR)
        self._win.resizable(False, False)
        self._win.transient(parent)  # Attach to main window
        self._win.grab_set()  # Block interaction with main window while open

        self._build_ui()

        # Centre the settings window over the main window
        self._win.update_idletasks()
        px = (
            parent.winfo_rootx() + (parent.winfo_width() - self._win.winfo_width()) // 2
        )
        py = (
            parent.winfo_rooty()
            + (parent.winfo_height() - self._win.winfo_height()) // 2
        )
        self._win.geometry(f"+{px}+{py}")

    def _build_ui(self):
        pad = {"padx": 20, "pady": 8}

        # Title
        tk.Label(
            self._win,
            text="Preferences",
            font=("Helvetica", 14, "bold"),
            bg=config.BG_COLOR,
            fg="#ffffff",
        ).pack(pady=(18, 4))

        tk.Frame(self._win, bg="#333355", height=1).pack(
            fill=tk.X, padx=20, pady=(0, 10)
        )

        # Window size section
        self._build_section_label("Window Size")

        current_size = (
            self._app.root.winfo_width(),
            self._app.root.winfo_height(),
        )
        self._size_var = tk.StringVar()

        size_frame = tk.Frame(self._win, bg=config.BG_COLOR)
        size_frame.pack(fill=tk.X, **pad)

        for label, value in WINDOW_SIZE_PRESETS:
            btn = tk.Radiobutton(
                size_frame,
                text=label,
                variable=self._size_var,
                value=str(value),
                font=("Helvetica", 10),
                bg=config.BG_COLOR,
                fg="#cccccc",
                selectcolor=config.ACCENT_COLOR,
                activebackground=config.BG_COLOR,
                activeforeground="#ffffff",
                cursor="hand2",
                command=self._on_size_changed,
            )
            btn.pack(anchor=tk.W, pady=2)
            if value == current_size:
                self._size_var.set(str(value))

        # Custom size row
        custom_size_row = tk.Frame(size_frame, bg=config.BG_COLOR)
        custom_size_row.pack(anchor=tk.W, pady=2)

        tk.Radiobutton(
            custom_size_row,
            text="Custom —",
            variable=self._size_var,
            value="custom",
            font=("Helvetica", 10),
            bg=config.BG_COLOR,
            fg="#cccccc",
            selectcolor=config.ACCENT_COLOR,
            activebackground=config.BG_COLOR,
            activeforeground="#ffffff",
            cursor="hand2",
            command=self._on_size_changed,
        ).pack(side=tk.LEFT)

        self._custom_width_var = tk.StringVar(value=str(current_size[0]))
        self._custom_height_var = tk.StringVar(value=str(current_size[1]))

        tk.Entry(
            custom_size_row,
            textvariable=self._custom_width_var,
            width=5,
            font=("Helvetica", 10),
            bg=config.ACCENT_COLOR,
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=(4, 2))

        tk.Label(
            custom_size_row,
            text="×",
            font=("Helvetica", 10),
            bg=config.BG_COLOR,
            fg="#cccccc",
        ).pack(side=tk.LEFT)

        tk.Entry(
            custom_size_row,
            textvariable=self._custom_height_var,
            width=5,
            font=("Helvetica", 10),
            bg=config.ACCENT_COLOR,
            fg="#ffffff",
            insertbackground="#ffffff",
            relief=tk.FLAT,
        ).pack(side=tk.LEFT, padx=(2, 4))

        tk.Button(
            custom_size_row,
            text="Apply",
            font=("Helvetica", 9),
            bg=config.ACCENT_COLOR,
            fg="#ffffff",
            activebackground="#e94560",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._apply_custom_size,
        ).pack(side=tk.LEFT)

        tk.Label(
            size_frame,
            text="Width: 300–800  Height: 500–1200",
            font=("Helvetica", 8),
            bg=config.BG_COLOR,
            fg="#555577",
        ).pack(anchor=tk.W, pady=(0, 2))

        tk.Frame(self._win, bg="#333355", height=1).pack(
            fill=tk.X, padx=20, pady=(8, 2)
        )

        # Font size section
        self._build_section_label("Lyric Font Size")

        current_active = getattr(self._app, "font_size_active", 16)
        self._font_var = tk.StringVar()

        font_frame = tk.Frame(self._win, bg=config.BG_COLOR)
        font_frame.pack(fill=tk.X, **pad)

        for label, sizes in FONT_SIZE_PRESETS:
            btn = tk.Radiobutton(
                font_frame,
                text=label,
                variable=self._font_var,
                value=str(sizes),
                font=("Helvetica", 10),
                bg=config.BG_COLOR,
                fg="#cccccc",
                selectcolor=config.ACCENT_COLOR,
                activebackground=config.BG_COLOR,
                activeforeground="#ffffff",
                cursor="hand2",
                command=self._on_font_changed,
            )
            btn.pack(anchor=tk.W, pady=2)
            if sizes["active"] == current_active:
                self._font_var.set(str(sizes))

        # Custom font row
        custom_font_row = tk.Frame(font_frame, bg=config.BG_COLOR)
        custom_font_row.pack(anchor=tk.W, pady=2)

        tk.Radiobutton(
            custom_font_row,
            text="Custom",
            variable=self._font_var,
            value="custom",
            font=("Helvetica", 10),
            bg=config.BG_COLOR,
            fg="#cccccc",
            selectcolor=config.ACCENT_COLOR,
            activebackground=config.BG_COLOR,
            activeforeground="#ffffff",
            cursor="hand2",
            command=self._on_font_changed,
        ).pack(side=tk.LEFT)

        self._custom_font_active_var = tk.StringVar(
            value=str(getattr(self._app, "font_size_active", 16))
        )
        self._custom_font_nearby_var = tk.StringVar(
            value=str(getattr(self._app, "font_size_nearby", 13))
        )
        self._custom_font_far_var = tk.StringVar(
            value=str(getattr(self._app, "font_size_far", 12))
        )

        for var in (
            self._custom_font_active_var,
            self._custom_font_nearby_var,
            self._custom_font_far_var,
        ):
            tk.Entry(
                custom_font_row,
                textvariable=var,
                width=3,
                font=("Helvetica", 10),
                bg=config.ACCENT_COLOR,
                fg="#ffffff",
                insertbackground="#ffffff",
                relief=tk.FLAT,
            ).pack(side=tk.LEFT, padx=(4, 0))

        tk.Button(
            custom_font_row,
            text="Apply",
            font=("Helvetica", 9),
            bg=config.ACCENT_COLOR,
            fg="#ffffff",
            activebackground="#e94560",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=6,
            pady=1,
            cursor="hand2",
            command=self._apply_custom_font,
        ).pack(side=tk.LEFT, padx=(6, 0))

        tk.Label(
            font_frame,
            text="Sizes: 8–28  (active  nearby  far)",
            font=("Helvetica", 8),
            bg=config.BG_COLOR,
            fg="#555577",
        ).pack(anchor=tk.W, pady=(0, 2))

        tk.Frame(self._win, bg="#333355", height=1).pack(
            fill=tk.X, padx=20, pady=(10, 6)
        )

        # Footer
        tk.Label(
            self._win,
            text="Changes apply immediately.",
            font=("Helvetica", 9),
            bg=config.BG_COLOR,
            fg="#666666",
        ).pack(pady=(0, 4))

        tk.Button(
            self._win,
            text="Close",
            font=("Helvetica", 11),
            bg=config.ACCENT_COLOR,
            fg="#ffffff",
            activebackground="#e94560",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=20,
            pady=6,
            cursor="hand2",
            command=self._win.destroy,
        ).pack(pady=(0, 18))

    def _build_section_label(self, text):
        tk.Label(
            self._win,
            text=text,
            font=("Helvetica", 11, "bold"),
            bg=config.BG_COLOR,
            fg="#e94560",
        ).pack(anchor=tk.W, padx=20, pady=(6, 2))

    def _on_size_changed(self):
        """Apply the selected window size preset immediately. Skips if custom is selected."""
        raw = self._size_var.get()
        if not raw or raw == "custom":
            return
        width, height = eval(raw)
        self._apply_size(width, height)

    def _apply_custom_size(self):
        """Validate and apply the custom width/height entered by the user."""
        try:
            width = int(self._custom_width_var.get())
            height = int(self._custom_height_var.get())
        except ValueError:
            self._show_error("Width and height must be whole numbers.")
            return
        if not (300 <= width <= 800):
            self._show_error("Width must be between 300 and 800.")
            return
        if not (500 <= height <= 1200):
            self._show_error("Height must be between 500 and 1200.")
            return
        self._size_var.set("custom")
        self._apply_size(width, height)

    def _apply_size(self, width, height):
        """Apply a window size to the main window and reflow lyrics."""
        self._app.root.geometry(f"{width}x{height}")
        self._app.main_frame.config(width=width, height=height)
        self._app.lyrics_canvas.itemconfig(
            self._app.lyrics_canvas_window, width=width - 20
        )
        self._app.lyrics_frame.update_idletasks()
        self._app._on_frame_configure()

    def _on_font_changed(self):
        """Apply the selected font size preset immediately. Skips if custom is selected."""
        raw = self._font_var.get()
        if not raw or raw == "custom":
            return
        sizes = eval(raw)
        self._apply_font(sizes["active"], sizes["nearby"], sizes["far"])

    def _apply_custom_font(self):
        """Validate and apply the custom font sizes entered by the user."""
        try:
            active = int(self._custom_font_active_var.get())
            nearby = int(self._custom_font_nearby_var.get())
            far = int(self._custom_font_far_var.get())
        except ValueError:
            self._show_error("Font sizes must be whole numbers.")
            return
        for name, val in (("Active", active), ("Nearby", nearby), ("Far", far)):
            if not (8 <= val <= 28):
                self._show_error(f"{name} font size must be between 8 and 28.")
                return
        self._font_var.set("custom")
        self._apply_font(active, nearby, far)

    def _apply_font(self, active, nearby, far):
        """Apply font sizes to the app state and all visible lyric labels."""
        self._app.font_size_active = active
        self._app.font_size_nearby = nearby
        self._app.font_size_far = far

        idx = self._app._last_highlight_index
        for i, (_, label) in enumerate(self._app.lyric_labels):
            if i == idx:
                label.config(font=("Helvetica", active, "bold"))
            elif i == idx - 1 or i == idx + 1:
                label.config(font=("Helvetica", nearby))
            else:
                label.config(font=("Helvetica", far))

        self._app._update_wraplengths()

    def _show_error(self, message):
        """Show a brief inline error label that disappears after 3 seconds."""
        err = tk.Label(
            self._win,
            text=f"⚠ {message}",
            font=("Helvetica", 9),
            bg=config.BG_COLOR,
            fg="#e94560",
        )
        err.pack(pady=(0, 2))
        self._win.after(3000, err.destroy)
