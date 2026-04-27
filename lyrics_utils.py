import re


"""LYRICS UTILS - Pure helper functions for parsing LRC lyrics, formatting timestamps,
and finding which lyric line matches the current playback position.
None of these functions touch global state or the GUI."""

# Pre-computed RGB values for animation (avoids hex↔rgb conversion every frame)
COLOR_MAP = {
    "#ffffff": (255, 255, 255),  # active
    "#aaaaaa": (170, 170, 170),  # nearby
    "#555555": (85, 85, 85),  # far
}


# Format seconds as an LRC timestamp string e.g. [02:34.50]
def format_lrc_time(seconds):
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"[{minutes:02d}:{secs:05.2f}]"


# Format seconds for on-screen display without brackets: MM:SS
def format_display_time(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


# Parse raw LRC text into a sorted list of (timestamp_seconds, text) tuples
def parse_lrc(lrc_text):
    lines = []
    pattern = r"\[(\d{2}):(\d{2}\.\d{2,3})\](.*)"
    for line in lrc_text.strip().split("\n"):
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


# Return the index of the lyric line that should be active at the given position
def get_current_lyric_index(lyrics_lines, position):
    if not lyrics_lines:
        return -1
    index = -1
    for i, (timestamp, _) in enumerate(lyrics_lines):
        if timestamp <= position:
            index = i
        else:
            break
    return index
