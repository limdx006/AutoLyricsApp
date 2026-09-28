# Chinese/Japanese don't separate words with spaces, so a line break is allowed between any two of these characters.
_CJK_RANGES = (
    (0x3000, 0x303F),  # CJK symbols & punctuation
    (0x3040, 0x30FF),  # Hiragana / Katakana
    (0x31F0, 0x31FF),  # Katakana extensions
    (0x3400, 0x4DBF),  # CJK extension A
    (0x4E00, 0x9FFF),  # CJK unified ideographs
    (0xF900, 0xFAFF),  # CJK compatibility ideographs
    (0xFF00, 0xFFEF),  # Fullwidth / halfwidth forms
)

# Punctuation that shouldn't begin a row - glued onto the previous unit.
_NO_LINE_START = set("、。，．：；！？）］｝〕〉》」』】〟…‥ー～,.!?;:)]}”’")
# Punctuation that shouldn't end a row - glued onto the next unit.
_NO_LINE_END = set("（［｛〔〈《「『【〝“‘")


def _is_cjk(ch):
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in _CJK_RANGES)


def _split_wrap_units(text):
    """
    Split a lyric line into (unit, space_before) pairs - the smallest
    pieces a row may be broken between.

    Space-separated words (English, Korean, romaji...) stay whole, exactly
    like before. Each CJK character becomes its own unit, so a long line
    with no spaces still has somewhere to break. space_before records
    whether whitespace originally preceded the unit, so rows are re-joined
    with a space only where there was one ("我love你" stays unspaced).
    """
    units = []
    buf = ""  # current run of non-CJK characters (a "word")
    carry = ""  # opening brackets waiting to attach to the next unit
    pending_space = False

    def emit(unit):
        nonlocal carry, pending_space
        units.append((carry + unit, pending_space))
        carry = ""
        pending_space = False

    def flush():
        nonlocal buf
        if buf:
            emit(buf)
            buf = ""

    for ch in text:
        if ch.isspace():
            flush()
            pending_space = True
        elif ch in _NO_LINE_START:
            if not buf and units and not pending_space:
                # Glue onto the previous unit so it can't start a new row
                units[-1] = (units[-1][0] + ch, units[-1][1])
            else:
                buf += ch
        elif ch in _NO_LINE_END:
            flush()
            carry += ch
        elif _is_cjk(ch):
            flush()
            emit(ch)
        else:
            buf += ch

    flush()
    if carry:
        emit("")
    return units


def _split_long_unit(unit, max_width, measure):
    """Break a single unit that's wider than a whole row (e.g. a very long
    unspaced word) into chunks that each fit, splitting between characters."""
    chunks = []
    chunk = ""
    for ch in unit:
        if chunk and measure(chunk + ch) > max_width:
            chunks.append(chunk)
            chunk = ch
        else:
            chunk += ch
    chunks.append(chunk)
    return chunks
