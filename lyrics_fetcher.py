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

MAX_ATTEMPT = 3

def lyrics_fetcher(title, artist):
    query = f"{title} {artist}".strip()

    for attempt in range(MAX_ATTEMPT):
        try:
            lyrics = syncedlyrics.search(query)
            print(f"Retrieved lyrics for '{query}':\n{lyrics}")
            return # Exit the function after retrieval
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for '{query}': {e}")
            if attempt < MAX_ATTEMPT - 1:
                time.sleep(1)  # Wait for 1 second before retrying

if __name__ == "__main__":
    lyrics_fetcher()
