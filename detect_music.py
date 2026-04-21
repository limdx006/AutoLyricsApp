import asyncio
import syncedlyrics
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)

def get_synced_lyrics(query):
    try:
        lrc = syncedlyrics.search(query)
        return lrc if lrc else "No lyrics found."

    except Exception as e:
        return f"Error: {e}"


async def get_current_media():
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()

    if current_session:
        info = await current_session.try_get_media_properties_async()

        title = info.title
        artist = info.artist

        music = f"{title} by {artist}"
        print(f"Now Playing: {music}")


        lyrics = get_synced_lyrics(music)
        print(lyrics)

    else:
        print("No Music is Playing")


asyncio.run(get_current_media())
