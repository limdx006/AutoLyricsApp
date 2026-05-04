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

# Lazy-loaded Korean romanizer engine
_korean_romanizer = None


def _get_korean_romanizer():
    """Lazy-load the Korean romanizer to avoid import overhead if not needed."""
    global _korean_romanizer
    if _korean_romanizer is not None:
        return _korean_romanizer
    try:
        from korean_romanizer.romanizer import Romanizer

        _korean_romanizer = Romanizer
        return _korean_romanizer
    except Exception as e:
        print("korean-romanizer import failed:", e)
        _korean_romanizer = None
        return None


"""LANGUAGE DETECTION - Uses Unicode ranges to identify Japanese, Chinese, and Korean text.
Japanese is identified by the presence of hiragana or katakana, which are unique to
Japanese. Chinese is identified by CJK characters without any kana. Korean is identified
by Hangul syllables (AC00–D7AF) or Jamo (1100–11FF, 3130–318F)."""

LRC_PATTERN = re.compile(r"\[(\d{2}):(\d{2}\.\d{2,3})\](.*)")
JAPANESE_PATTERN = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
KOREAN_PATTERN = re.compile(r"[\uac00-\ud7af\u1100-\u11ff\u3130-\u318f]")
CHINESE_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def detect_language(lyrics_lines):
    """Cleaned language detection using pre-compiled patterns."""
    sample = " ".join(text for _, text in lyrics_lines[:10])

    if JAPANESE_PATTERN.search(sample): return "japanese"
    if KOREAN_PATTERN.search(sample):   return "korean"
    if CHINESE_PATTERN.search(sample):  return "chinese"
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


def to_romanized_korean(text):
    """Convert Korean Hangul text to Revised Romanization using korean-romanizer.
    Falls back to original text if the library is unavailable."""
    if not text:
        return text
    Romanizer = _get_korean_romanizer()
    if not Romanizer:
        return text
    try:
        r = Romanizer(text)
        return r.romanize()
    except Exception:
        return text


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
    for line in lrc_text.strip().split("\n"):
        match = LRC_PATTERN.match(line.strip())
        if match:
            timestamp = int(match.group(1)) * 60 + float(match.group(2))
            text = match.group(3).strip()
            if text: lines.append((timestamp, text))
    
    return sorted(lines, key=lambda x: x[0])


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
