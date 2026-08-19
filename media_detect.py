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
        return

    current_session = sessions.get_current_session()

    for i, session in enumerate(all_sessions):
        info = await session.try_get_media_properties_async()
        timeline = session.get_timeline_properties()

        # Check if this is the "current" (active) session
        is_current = (session == current_session)

        print(f"--- Session #{i + 1} {'[CURRENT/ACTIVE]' if is_current else '[BACKGROUND]'} ---")
        print(f"  Title:    {info.title or 'N/A'}")
        print(f"  Artist:   {info.artist or 'N/A'}")
        print(f"  Position: {timeline.position.total_seconds():.1f}s / {timeline.end_time.total_seconds():.1f}s")
        print(f"  Source:   {session.source_app_user_model_id or 'Unknown'}")

    return info.title, info.artist

if __name__ == "__main__":
    asyncio.run(detect_media())