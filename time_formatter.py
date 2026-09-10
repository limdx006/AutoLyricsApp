import re

# Matches a single LRC timestamp tag, e.g. [02:34.50] or [02:34]
_LRC_TIME_PATTERN = re.compile(r"\[(\d{2}):(\d{2}(?:\.\d{1,3})?)\]")


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


def parse_lrc_line(line):
    """
    Parse a single raw LRC line into a list of (seconds, text) tuples.

    The lyric text itself never contains the timestamp - only the plain
    line.

    Returns an empty list for lines with no valid timestamp or no lyric
    text after the timestamp(s) (e.g. metadata tags like [ar:Artist]).
    """
    matches = list(_LRC_TIME_PATTERN.finditer(line))
    if not matches:
        return []

    text = line[matches[-1].end():].strip()
    if not text:
        return []

    entries = []
    for match in matches:
        minutes = int(match.group(1))
        secs = float(match.group(2))
        total_seconds = minutes * 60 + secs
        entries.append((total_seconds, text))
    return entries


def parse_lrc_lyrics(raw_lyrics):
    """
    Parse a full block of raw LRC-format lyrics text into a sorted list of
    (seconds, text) tuples, with all timestamp tags stripped away.
    """
    parsed = []
    if not raw_lyrics:
        return parsed

    for raw_line in raw_lyrics.splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        parsed.extend(parse_lrc_line(raw_line))

    parsed.sort(key=lambda pair: pair[0])
    return parsed