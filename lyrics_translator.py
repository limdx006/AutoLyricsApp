"""
Converts a raw LRC lyrics blob's text to a romanised/phonetic script,
per detected language:
  Japanese -> Romaji (cutlet)
  Korean   -> Romaji (korean_romanizer)
  Chinese  -> PinYin with tone marks (pypinyin)

Timestamps are preserved; only the text after each timestamp is converted.
"""

from time_formatter import parse_lrc_lyrics, format_lrc_time
from pypinyin import pinyin, Style
from korean_romanizer.romanizer import Romanizer

# cutlet.Cutlet() loads a Japanese dictionary on construction, so it's built
# lazily on first actual use rather than paying that cost on every launch.
_katsu = None


def _get_katsu():
    global _katsu
    if _katsu is None:
        import cutlet
        _katsu = cutlet.Cutlet()
    return _katsu


def _to_romaji_japanese(text):
    return _get_katsu().romaji(text)


def _to_romaji_korean(text):
    return Romanizer(text).romanize()


def _to_pinyin_chinese(text):
    return " ".join(syllable[0] for syllable in pinyin(text, style=Style.TONE))


_CONVERTERS = {
    "Japanese": _to_romaji_japanese,
    "Korean": _to_romaji_korean,
    "Chinese": _to_pinyin_chinese,
}


def translate_lyrics(raw_lyrics, language):
    """
    Convert every lyric line's text to the target script for the given
    detected language. Returns raw_lyrics unchanged for languages with no
    converter (e.g. English/Unknown). If a single line fails to convert,
    that line falls back to its original text rather than failing the
    whole song.
    """
    converter = _CONVERTERS.get(language)
    if not raw_lyrics or converter is None:
        return raw_lyrics

    lines = parse_lrc_lyrics(raw_lyrics)
    if not lines:
        return raw_lyrics

    translated_rows = []
    for seconds, text in lines:
        try:
            converted = converter(text)
        except Exception as e:
            print(f"[Translate] Failed to convert line '{text}': {e}")
            converted = text
        translated_rows.append(f"{format_lrc_time(seconds)}{converted}")

    return "\n".join(translated_rows)