import requests

MY_LYRICS_API = "http://127.0.0.1:8000"


def fetch_from_my_lyrics_api(title, artist):
    """
    Try to fetch lyrics from MyLyricsAPI.
    Returns lyrics if found, otherwise None.
    """
    try:
        response = requests.get(
            f"{MY_LYRICS_API}/songs/search",
            params={"title": title, "artist": artist},
            timeout=3,
        )
        if response.status_code == 404:
            print(f"[MyLyricsAPI] Song not found: '{title}' by '{artist}'")
            return None
        
        response.raise_for_status()
        song = response.json()
        song_id = song["id"]

        lyrics_response = requests.get(
            f"{MY_LYRICS_API}/songs/{song_id}/lyrics", timeout=3
        )
        if lyrics_response.status_code == 404:
            print(f"[MyLyricsAPI] Lyrics not found for song ID {song_id}")
            return None

        lyrics_response.raise_for_status()
        lyrics = lyrics_response.json()
        return lyrics

    except requests.RequestException as e:
        print(f"[MyLyricsAPI] Request failed: {e}")
        return None
