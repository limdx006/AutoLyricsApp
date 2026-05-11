import time

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)

"""MEDIA SELECTOR - Scores all active Windows media sessions and returns the one
most likely to be music. This replaces the naive get_current_session() approach,
which blindly returns whatever Windows considers 'active' — often a browser tab
playing a video instead of the intended music source.

Each session is scored by multiple independent signals. The session with the
highest score wins. If all sessions score below zero, None is returned."""


# App IDs (lowercase substrings) that are almost certainly not music players
_BLACKLISTED_APPS = {
    "teams",
    "zoom",
    "discord",  # Discord can play music but often captures game audio instead
    "slack",
    "skype",
    "obs",
    "mpc-hc",   # Video player
    "vlc",      # Scored separately — VLC can play music but often plays video
    "wmplayer",
}

# App IDs known to be dedicated music sources — get a bonus
_MUSIC_APP_ALLOWLIST = {
    "spotify",
    "tidal",
    "applemusic",
    "musicbee",
    "foobar",
    "aimp",
    "winamp",
    "mediamonkey",
    "amazon music",
    "deezer",
    "soundcloud",
}

# Browser process names (lowercase substrings)
_BROWSER_APPS = {"chrome", "msedge", "firefox", "opera", "brave", "vivaldi"}

# How many seconds a position must advance between two polls to count as "moving"
_POSITION_DELTA_THRESHOLD = 0.3


def _is_browser(app_id: str) -> bool:
    low = app_id.lower()
    return any(b in low for b in _BROWSER_APPS)


def _is_blacklisted(app_id: str) -> bool:
    low = app_id.lower()
    return any(b in low for b in _BLACKLISTED_APPS)


def _is_music_app(app_id: str) -> bool:
    low = app_id.lower()
    return any(m in low for m in _MUSIC_APP_ALLOWLIST)


def _looks_like_video_title(title: str) -> bool:
    """Heuristic: titles with episode/video markers are probably not music."""
    if not title:
        return False
    low = title.lower()
    video_markers = (" - youtube", " | youtube", "episode ", "ep. ", " s0", " e0", " season ")
    return any(m in low for m in video_markers)


def _score_session(app_id: str, info, playback_info, timeline, position_moving: bool) -> int:
    """Compute a numeric confidence score for a single session.

    Higher is better. Negative scores mean the session is likely not music.
    """
    score = 0
    status = playback_info.playback_status

    # Playing right now is a strong positive signal
    if status == PlaybackStatus.PLAYING:
        score += 100

    # Paused but has track metadata — still a likely music candidate
    elif status == PlaybackStatus.PAUSED:
        score += 20

    # Metadata richness
    if info.artist and info.artist.strip():
        score += 40
    if info.album_title and info.album_title.strip():
        score += 20
    try:
        if info.thumbnail:
            score += 20
    except Exception:
        pass

    # Position is advancing — confirms live playback
    if position_moving:
        score += 30

    # Known music app — very reliable signal
    if _is_music_app(app_id):
        score += 60

    # Browser tab playing audio — could be music, but often is not
    if _is_browser(app_id):
        score -= 25

    # Title looks like a video (YouTube watch page, episode title, etc.)
    if _looks_like_video_title(info.title):
        score -= 30

    # Very long titles are unlikely to be song names
    if info.title and len(info.title) > 50:
        score -= 30

    # Blacklisted application — almost certainly not the target
    if _is_blacklisted(app_id):
        score -= 100

    # No title at all — we cannot search lyrics without one
    if not info.title or not info.title.strip():
        score -= 50

    return score


# Stores the last-known timeline position per session ID for movement detection
_last_positions: dict[str, tuple[float, float]] = {}  # app_id -> (position, wall_time)


def _check_position_moving(app_id: str, current_pos: float) -> bool:
    """Return True if the session's playback position has advanced since the last check."""
    now = time.monotonic()
    if app_id in _last_positions:
        prev_pos, prev_time = _last_positions[app_id]
        elapsed_wall = now - prev_time
        # Only judge movement if at least 0.4 s has passed to avoid false negatives
        if elapsed_wall >= 0.4:
            moving = (current_pos - prev_pos) >= _POSITION_DELTA_THRESHOLD
            _last_positions[app_id] = (current_pos, now)
            return moving
    else:
        _last_positions[app_id] = (current_pos, now)
    return False


async def get_best_session():
    """Fetch all active media sessions and return the one most likely to be music.

    Returns (session, info, score) for the winner, or (None, None, 0) if nothing
    qualifies. Sessions that score below -50 are treated as disqualified.
    """
    try:
        manager = await MediaManager.request_async()
    except Exception:
        return None, None, 0

    sessions = manager.get_sessions()
    if not sessions:
        return None, None, 0

    best_session = None
    best_info = None
    best_score = -9999

    for session in sessions:
        try:
            app_id = session.source_app_user_model_id or ""
            info = await session.try_get_media_properties_async()
            playback_info = session.get_playback_info()
            timeline = session.get_timeline_properties()
            current_pos = timeline.position.total_seconds()

            position_moving = _check_position_moving(app_id, current_pos)
            score = _score_session(app_id, info, playback_info, timeline, position_moving)

            if score > best_score:
                best_score = score
                best_session = session
                best_info = info

        except Exception:
            # Malformed or inaccessible session — skip it
            continue

    # Refuse to return a session that is almost certainly wrong
    if best_score < -50:
        return None, None, 0

    return best_session, best_info, best_score
