import asyncio
from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)

async def detect_media():
    """Detect and list all active media sessions from Windows."""
    sessions = await MediaManager.request_async()

    # Get all sessions, not just the current one
    all_sessions = sessions.get_sessions()

    print(f"Total active sessions found: {len(all_sessions)}\n")

    if not all_sessions:
        print("No media sessions detected.")
        return "Undetected Song", "Unknown Artist"

    current_session = sessions.get_current_session()
    info = None

    # If there is a current session, use its info
    if current_session:
        info = await current_session.try_get_media_properties_async()
    else:
        # Otherwise, use the first session's info
        info = await all_sessions[0].try_get_media_properties_async()

    title = info.title if info.title else "Undetected Song"
    artist = info.artist if info.artist else "Unknown Artist"

    # Print all sessions for debugging
    for i, session in enumerate(all_sessions):
        session_info = await session.try_get_media_properties_async()
        timeline = session.get_timeline_properties()
        is_current = (session == current_session)
        print(f"--- Session #{i + 1} {'[CURRENT/ACTIVE]' if is_current else '[BACKGROUND]'} ---")
        print(f"  Title:    {session_info.title or 'Undetected Song'}")
        print(f"  Artist:   {session_info.artist or 'Unknown Artist'}")
        print(f"  Position: {timeline.position.total_seconds():.1f}s / {timeline.end_time.total_seconds():.1f}s")
        print(f"  Source:   {session.source_app_user_model_id or 'Unknown'}")

    return title, artist

if __name__ == "__main__":
    asyncio.run(detect_media())