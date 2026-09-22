import time
import requests


BASE_URL = "https://limdxlyricsapi.onrender.com"


def test_request(name, url, **kwargs):
    start = time.perf_counter()

    response = requests.get(
        url,
        timeout=30,
        **kwargs
    )

    elapsed = time.perf_counter() - start

    print(f"{name}: {elapsed:.3f} seconds")
    print(f"Status: {response.status_code}")
    print()


print("Testing Render API...")
print()

test_request(
    "Root endpoint",
    f"{BASE_URL}/"
)

test_request(
    "Songs endpoint",
    f"{BASE_URL}/songs"
)

test_request(
    "Song search",
    f"{BASE_URL}/songs/search",
    params={
        "title": "アイドル",
        "artist": "YOASOBI"
    }
)

test_request(
    "Lyrics endpoint",
    f"{BASE_URL}/songs/1/lyrics"
)