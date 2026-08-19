# Window dimensions
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 800

# Colours
BG_COLOR = "#1a1a2e"  # Dark blue-ish background
ACCENT_COLOR = "#16213e"  # Slightly lighter for info panel
ERROR_COLOR = "#e94560"  # Reddish accent for errors/highlights

WINDOW_SIZE_PRESETS = [
    ("Small  — 340 × 640", (340, 640)),
    ("Medium — 360 × 700", (360, 700)),
    ("Default — 400 × 800", (400, 800)),
    ("Large  — 500 × 900", (500, 900)),
    ("XLarge   — 600 × 1000", (600, 1000)),
]

FONT_SIZE_PRESETS = [
    ("Small  — 14 / 12 / 11", {"active": 14, "nearby": 12, "far": 11}),
    ("Default — 16 / 13 / 12", {"active": 16, "nearby": 13, "far": 12}),
    ("Large  — 18 / 14 / 13", {"active": 18, "nearby": 14, "far": 13}),
    ("XLarge — 20 / 16 / 14", {"active": 20, "nearby": 16, "far": 14}),
]

FONT_FAMILY = "Helvetica"

# Color constants
COLOR_ACTIVE_FG = "#ffffff"
COLOR_NEARBY_FG = "#aaaaaa"
COLOR_FAR_FG = "#555555"
COLOR_ERROR_FG = "#e94560"
COLOR_MUTED_FG = "#888888"
COLOR_STATUS_FG = "#666666"
COLOR_ARTIST_FG = "#a0a0a0"
