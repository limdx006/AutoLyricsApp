import re
import cutlet as _cutlet
import pykakasi as _pykakasi
from pypinyin import lazy_pinyin as _lazy_pinyin, Style as _Style


"""LYRICS UTILS - Pure helper functions for parsing LRC lyrics, formatting timestamps,
and finding which lyric line matches the current playback position.
None of these functions touch global state or the GUI."""

# Pre-computed RGB values for animation (avoids hex↔rgb conversion every frame)
COLOR_MAP = {
    "#ffffff": (255, 255, 255),  # active
    "#aaaaaa": (170, 170, 170),  # nearby
    "#555555": (85, 85, 85),  # far
}

# Single shared instances — initialising these is expensive so do it once at import
_cutlet_engine = _cutlet.Cutlet()
_kakasi_engine = _pykakasi.kakasi()


"""LANGUAGE DETECTION - Uses Unicode ranges to identify Japanese and Chinese text.
Japanese is identified by the presence of hiragana or katakana, which are unique to
Japanese. Chinese is identified by CJK characters without any kana."""


def detect_language(lyrics_lines):
    """Sample the first 10 lyric lines to detect the dominant language.
    Returns 'japanese', 'chinese', or 'other'."""
    sample = " ".join(text for _, text in lyrics_lines[:10])

    # Hiragana (3040–309f) and katakana (30a0–30ff) are exclusive to Japanese
    if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", sample):
        return "japanese"

    # CJK unified ideographs without any kana → Chinese
    if re.search(r"[\u4e00-\u9fff]", sample):
        return "chinese"

    return "other"


def to_romaji(text):
    """Convert Japanese text to Hepburn romaji using cutlet (primary) with pykakasi as fallback."""
    if not text:
        return text
    try:
        return _cutlet_engine.romaji(text)
    except Exception:
        # pykakasi fallback if cutlet fails
        result = _kakasi_engine.convert(text)
        return " ".join(item["hepburn"] for item in result if item["hepburn"])


def to_pinyin(text):
    """Convert Chinese text to pinyin with tone marks."""
    if not text:
        return text
    return " ".join(_lazy_pinyin(text, style=_Style.TONE))


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