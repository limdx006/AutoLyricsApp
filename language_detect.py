"""
Detect the dominant language of a song's lyrics.
feature: Chinese, English, Korean, and Japanese.
"""

import re
import random

from time_formatter import parse_lrc_lyrics

# Unicode ranges used to classify each sampled line.
_HIRAGANA_KATAKANA = re.compile(r"[\u3040-\u30ff\u31f0-\u31ff]")
_HANGUL = re.compile(r"[\uac00-\ud7a3\u1100-\u11ff\u3130-\u318f]")
_HAN = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_LATIN = re.compile(r"[A-Za-z]")

# Sampling configuration (all 1-indexed positions converted to 0-indexed slices where used).
_FIXED_LINE_RANGE = (10, 12)  # lines 10-12 inclusive, 1-indexed
_RANDOM_SAMPLE_COUNT = 3
_MIDDLE_POOL_START_LINE = 13  # 1-indexed: random sample starts from here
_TAIL_MARGIN = 10  # exclude the last 10 lines from the random sample pool

UNKNOWN_LANGUAGE = "Unknown"


def _detect_line_language(text):
    """
    Classify a single line of lyric text using Unicode-script heuristics.

    Hiragana/Katakana is checked first since it's the only unambiguous
    signal for Japanese - kanji (Han characters) alone are shared with
    Chinese and can't distinguish the two on their own.
    """
    if _HIRAGANA_KATAKANA.search(text):
        return "Japanese"
    if _HANGUL.search(text):
        return "Korean"
    if _HAN.search(text):
        return "Chinese"
    if _LATIN.search(text):
        return "English"
    return None


def _sample_lines(texts):
    """
    Pick up to 6 lines to run detection on from a list of lyric line texts
    (already stripped of timestamps, in chronological order):
      - lines 10-12 (1-indexed), fixed
      - 3 random lines from the 13th line up to (len - 10)th line, 1-indexed

    Falls back to a smaller trimmed-margin sample for short lyrics where
    those ranges don't yield anything.
    """
    n = len(texts)
    sample = []

    # Fixed block: lines 10-12 (1-indexed) -> zero-indexed slice [9:12]
    fixed_start = _FIXED_LINE_RANGE[0] - 1
    fixed_end = _FIXED_LINE_RANGE[1]
    sample.extend(texts[fixed_start:fixed_end])

    # Random block: 3 lines from the middle pool (13th line, 1-indexed, up to len(lyrics) - 10th line, 1-indexed).
    pool_start = _MIDDLE_POOL_START_LINE - 1  # zero-indexed
    pool_end = n - _TAIL_MARGIN  # zero-indexed, exclusive
    pool = texts[pool_start:pool_end] if pool_end > pool_start else []

    if pool:
        k = min(_RANDOM_SAMPLE_COUNT, len(pool))
        sample.extend(random.sample(pool, k))

    """Fallback for short lyrics: neither range above produced anything
    (song too short). Trim a small margin off each end instead, so we
    still avoid the very first/last lines where possible."""
    if not sample:
        margin = min(2, n // 4)
        sample = texts[margin: n - margin] if n - 2 * margin > 0 else texts

    return sample


def detect_lyrics_language(raw_lyrics):
    """
    Detect the dominant language of a raw LRC lyrics blob.

    Returns one of "Chinese", "English", "Korean", "Japanese", or
    "Unknown" if no lines could be classified (e.g. empty/instrumental
    lyrics, or lyrics too short to sample safely).
    """
    if not raw_lyrics:
        return UNKNOWN_LANGUAGE

    lines = parse_lrc_lyrics(raw_lyrics)
    if not lines:
        return UNKNOWN_LANGUAGE

    texts = [text for _, text in lines]
    sample = _sample_lines(texts)

    votes = {}
    for text in sample:
        lang = _detect_line_language(text)
        if lang:
            votes[lang] = votes.get(lang, 0) + 1

    if not votes:
        return UNKNOWN_LANGUAGE

    # Majority vote among the sampled lines.
    return max(votes.items(), key=lambda kv: kv[1])[0]
