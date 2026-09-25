import requests
import time

MY_LYRICS_API = "https://limdxlyricsapi.onrender.com"


def fetch_from_my_lyrics_api(title, artist):
    """
    Try to fetch lyrics from MyLyricsAPI.
    Returns lyrics if found, otherwise None.
    """

    total_start = time.perf_counter()

    try:
        print( f"[MyLyricsAPI] Searching for " f"'{title}' by '{artist}'" ) 
        search_start = time.perf_counter()

        response = requests.get(
            f"{MY_LYRICS_API}/songs/search",
            params={"title": title, "artist": artist},
            timeout=10,
        )

        search_time = time.perf_counter() - search_start 
        print( f"[MyLyricsAPI] Song search took " f"{search_time:.3f} seconds" )

        # Getting a response at all (even a 404) proves the API is up
        import api_status
        api_status.report_online()

        if response.status_code == 404:
            print(f"[MyLyricsAPI] Song not found: '{title}' by '{artist}'")
            return None

        response.raise_for_status()

        song = response.json()
        song_id = song["id"]

        print( f"[MyLyricsAPI] Found song ID: {song_id}" )

        lyrics_start = time.perf_counter()

        lyrics_response = requests.get(
            f"{MY_LYRICS_API}/songs/{song_id}/lyrics",
            timeout=10
        )

        lyrics_time = time.perf_counter() - lyrics_start

        print( f"[MyLyricsAPI] Lyrics request took " f"{lyrics_time:.3f} seconds" )

        if lyrics_response.status_code == 404:
            print(f"[MyLyricsAPI] Lyrics not found for song ID {song_id}")
            return None

        lyrics_response.raise_for_status()

        lyrics = lyrics_response.json()

        total_time = time.perf_counter() - total_start

        print( f"[MyLyricsAPI] Total API time: " f"{total_time:.3f} seconds" )

        return lyrics

    except requests.RequestException as e:
        total_time = time.perf_counter() - total_start
        print(f"[MyLyricsAPI] Request failed: {e}")
        return None