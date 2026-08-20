r"""
@misc{syncedlyrics,
  author = {Momeni, Mohammad},
  title = {syncedlyrics},
  year = {2022},
  publisher = {GitHub},
  journal = {GitHub repository},
  howpublished = {\url{https://github.com/moehmeni/syncedlyrics}},
}
"""

import time
import syncedlyrics
import re

MAX_ATTEMPT = 3


def remove_empty_lines(lyrics: str) -> str:
    """
    Remove lines that contain only a timestamp with no lyrics.
    """
    cleaned_lines = []
    # Regex matches a timestamp at the start of a line, optionally followed by whitespace only
    empty_pattern = re.compile(r"^\[\d{2}:\d{2}\.\d{2}\]\s*$")
    for line in lyrics.splitlines():
        if not empty_pattern.match(line):
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def lyrics_fetcher(title, artist):
    """
    Fetch lyrics for the given title and artist using the syncedlyrics library.
    """
    query = f"{title} {artist}".strip()
    for attempt in range(MAX_ATTEMPT):
        try:
            lyrics = syncedlyrics.search(query)
            cleaned = remove_empty_lines(lyrics)
            print(f"Retrieved lyrics for '{query}':\n{cleaned}")
            return cleaned  # Return cleaned lyrics
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for '{query}': {e}")
            if attempt < MAX_ATTEMPT - 1:
                time.sleep(1)  # Wait for 1 second before retrying


if __name__ == "__main__":
    lyrics_fetcher()
