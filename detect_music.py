import asyncio
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager



async def get_current_media():
    sessions = await MediaManager.request_async()
    current_session = sessions.get_current_session()

    if current_session:
        info = await current_session.try_get_media_properties_async()

        title = info.title
        artist = info.artist

        print(f"Now Playing: {title} by {artist}")

asyncio.run(get_current_media())
