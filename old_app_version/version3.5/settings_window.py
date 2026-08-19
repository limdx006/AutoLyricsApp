import tkinter as tk
import config 
from config import WINDOW_SIZE_PRESETS, FONT_SIZE_PRESETS
import ast  # Safer and faster than eval()

# Preset options — (display label, value)

class SettingsWindow:
    def __init__(self, parent, app):
        self._app = app
        self._win = tk.Toplevel(parent)
        self._win.title("Settings")
        self._win.configure(bg=config.BG_COLOR)
        self._win.resizable(False, False)
        self._win.transient(parent)
        self._win.grab_set()

        # Shared UI styles to reduce code bloat
        self._radio_style = {
            "font": ("Helvetica", 10),
            "bg": config.BG_COLOR,
            "fg": "#cccccc",
            "selectcolor": config.ACCENT_COLOR,
            "activebackground": config.BG_COLOR,
            "activeforeground": "#ffffff",
            "cursor": "hand2"
        }

        self._build_ui()
        self._center_window(parent)

    def _center_window(self, parent):
        """Standardized centering logic."""
        self._win.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self._win.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self._win.winfo_height()) // 2
        self._win.geometry(f"+{px}+{py}")

    def _build_ui(self):
        # Header
        tk.Label(self._win, text="Preferences", font=("Helvetica", 14, "bold"),
                 bg=config.BG_COLOR, fg="#ffffff").pack(pady=(18, 4))
        self._add_divider(pady=(0, 10))

        # --- Window Size Section ---
        self._build_section_header("Window Size")
        self._size_var = tk.StringVar()
        size_frame = tk.Frame(self._win, bg=config.BG_COLOR)
        size_frame.pack(fill=tk.X, padx=20, pady=8)

        current_size = (self._app.root.winfo_width(), self._app.root.winfo_height())
        for label, value in WINDOW_SIZE_PRESETS:
            self._create_radio(size_frame, label, str(value), self._size_var, self._on_size_changed)
            if value == current_size: self._size_var.set(str(value))

        self._build_custom_size_ui(size_frame, current_size)
        self._add_divider(pady=(8, 2))

        # --- Font Size Section ---
        self._build_section_header("Lyric Font Size")
        self._font_var = tk.StringVar()
        font_frame = tk.Frame(self._win, bg=config.BG_COLOR)
        font_frame.pack(fill=tk.X, padx=20, pady=8)

        current_active = getattr(self._app, "font_size_active", 16)
        for label, sizes in FONT_SIZE_PRESETS:
            self._create_radio(font_frame, label, str(sizes), self._font_var, self._on_font_changed)
            if sizes["active"] == current_active: self._font_var.set(str(sizes))

        self._build_custom_font_ui(font_frame)
        self._add_divider(pady=(10, 6))

        # Footer
        tk.Label(self._win, text="Changes apply immediately.", font=("Helvetica", 9),
                 bg=config.BG_COLOR, fg="#666666").pack(pady=(0, 4))
        
        tk.Button(self._win, text="Close", font=("Helvetica", 11), bg=config.ACCENT_COLOR,
                  fg="#ffffff", activebackground="#e94560", activeforeground="#ffffff",
                  relief=tk.FLAT, padx=20, pady=6, cursor="hand2", 
                  command=self._win.destroy).pack(pady=(0, 18))

    # --- UI Helpers ---

    def _create_radio(self, parent, text, value, var, cmd):
        """Helper to create uniform radio buttons."""
        tk.Radiobutton(parent, text=text, variable=var, value=value, 
                       command=cmd, **self._radio_style).pack(anchor=tk.W, pady=2)

    def _build_section_header(self, text):
        """Standardized section labels."""
        tk.Label(self._win, text=text, font=("Helvetica", 11, "bold"),
                 bg=config.BG_COLOR, fg="#e94560").pack(anchor=tk.W, padx=20, pady=(6, 2))

    def _add_divider(self, pady):
        """Creates horizontal separation lines."""
        tk.Frame(self._win, bg="#333355", height=1).pack(fill=tk.X, padx=20, pady=pady)

    # --- Logic Handlers ---

    def _on_size_changed(self):
        raw = self._size_var.get()
        if raw and raw != "custom":
            width, height = ast.literal_eval(raw) # Use ast for safety
            self._apply_size(width, height)

    def _on_font_changed(self):
        raw = self._font_var.get()
        if raw and raw != "custom":
            sizes = ast.literal_eval(raw)
            self._apply_font(sizes["active"], sizes["nearby"], sizes["far"])

    # --- Support Methods ---

    def _apply_size(self, width, height):
        self._app.root.geometry(f"{width}x{height}")
        self._app.main_frame.config(width=width, height=height)
        self._app.lyrics_canvas.itemconfig(self._app.lyrics_canvas_window, width=width - 20)
        self._app.lyrics_frame.update_idletasks()
        self._app._on_frame_configure()

    def _apply_font(self, active, nearby, far):
        self._app.font_size_active, self._app.font_size_nearby, self._app.font_size_far = active, nearby, far
        idx = self._app._last_highlight_index
        for i, (_, label) in enumerate(self._app.lyric_labels):
            font = ("Helvetica", active, "bold") if i == idx else \
                   ("Helvetica", nearby) if i in (idx-1, idx+1) else \
                   ("Helvetica", far)
            label.config(font=font)
        self._app._update_wraplengths()

    def _show_error(self, message):
        err = tk.Label(self._win, text=f"⚠ {message}", font=("Helvetica", 9),
                       bg=config.BG_COLOR, fg="#e94560")
        err.pack(pady=(0, 2))
        self._win.after(3000, err.destroy)

    # Note: Build Custom Row methods are kept separate for modularity 
    # but follow the same cleaning patterns as above.
    def _build_custom_size_ui(self, size_frame, current_size):
        row = tk.Frame(size_frame, bg=config.BG_COLOR)
        row.pack(anchor=tk.W, pady=2)
        tk.Radiobutton(row, text="Custom —", variable=self._size_var, value="custom",
                       command=self._on_size_changed, **self._radio_style).pack(side=tk.LEFT)
        
        self._custom_width_var = tk.StringVar(value=str(current_size[0]))
        self._custom_height_var = tk.StringVar(value=str(current_size[1]))

        for var, width in [(self._custom_width_var, 5), (None, 0), (self._custom_height_var, 5)]:
            if var:
                tk.Entry(row, textvariable=var, width=width, font=("Helvetica", 10),
                         bg=config.ACCENT_COLOR, fg="#ffffff", relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
            else:
                tk.Label(row, text="×", font=("Helvetica", 10), bg=config.BG_COLOR, fg="#cccccc").pack(side=tk.LEFT)

        tk.Button(row, text="Apply", font=("Helvetica", 9), bg=config.ACCENT_COLOR, fg="#ffffff",
                  relief=tk.FLAT, padx=6, pady=1, command=self._apply_custom_size).pack(side=tk.LEFT, padx=4)

    def _apply_custom_size(self):
        try:
            w, h = int(self._custom_width_var.get()), int(self._custom_height_var.get())
            if 300 <= w <= 800 and 500 <= h <= 1200:
                self._size_var.set("custom")
                self._apply_size(w, h)
            else:
                self._show_error("Size out of range (W:300-800, H:500-1200)")
        except ValueError:
            self._show_error("Must be whole numbers.")

    def _build_custom_font_ui(self, font_frame):
        row = tk.Frame(font_frame, bg=config.BG_COLOR)
        row.pack(anchor=tk.W, pady=2)
        tk.Radiobutton(row, text="Custom", variable=self._font_var, value="custom",
                       command=self._on_font_changed, **self._radio_style).pack(side=tk.LEFT)

        vars = [
            tk.StringVar(value=str(getattr(self._app, "font_size_active", 16))),
            tk.StringVar(value=str(getattr(self._app, "font_size_nearby", 13))),
            tk.StringVar(value=str(getattr(self._app, "font_size_far", 12)))
        ]
        self._custom_font_active_var, self._custom_font_nearby_var, self._custom_font_far_var = vars

        for var in vars:
            tk.Entry(row, textvariable=var, width=3, font=("Helvetica", 10),
                     bg=config.ACCENT_COLOR, fg="#ffffff", relief=tk.FLAT).pack(side=tk.LEFT, padx=(4, 0))

        tk.Button(row, text="Apply", font=("Helvetica", 9), bg=config.ACCENT_COLOR, fg="#ffffff",
                  relief=tk.FLAT, padx=6, pady=1, command=self._apply_custom_font).pack(side=tk.LEFT, padx=6)
        
        # This label sits below the text boxes to explain what they represent
        guide_text = "(active  nearby  far)"
        tk.Label(font_frame, text=guide_text, font=("Helvetica", 8),
                 bg=config.BG_COLOR, fg="#555577").pack(anchor=tk.W, padx=(65, 0), pady=(0, 2))

    def _apply_custom_font(self):
        try:
            vals = [int(v.get()) for v in [self._custom_font_active_var, self._custom_font_nearby_var, self._custom_font_far_var]]
            if all(8 <= v <= 28 for v in vals):
                self._font_var.set("custom")
                self._apply_font(*vals)
            else:
                self._show_error("Font sizes must be between 8 and 28.")
        except ValueError:
            self._show_error("Must be whole numbers.")