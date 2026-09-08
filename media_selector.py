"""
Picks the correct media session when multiple are active at once (e.g. a
paused YouTube tab sitting alongside Spotify).

Two-phase selection:
  1. Cheap metadata scoring (no network calls) ranks every session by how
     "music-like" it looks - known music app, real artist/album/thumbnail,
     actively advancing position, browser/video-title penalties, etc.
  2. Starting from the top-ranked session, a real lyrics search is run for
     each candidate in turn. The first one that actually has lyrics wins -
     metadata alone can't fully distinguish e.g. two browser tabs, but
     having real lyrics is strong confirmation we picked the right source.
     If nobody has lyrics, the top-scored candidate is used anyway.

Re-scoring (and the lyrics search) only happens when the set of active
sessions changes, or when the currently selected session's song changes -
never on every poll, since it involves a real network lookup.
"""

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
)

from lyrics_fetcher import lyrics_fetcher
import asyncio

# How much a position must move between two quick samples to count as "playing"
_POSITION_DELTA_THRESHOLD = 0.3
_MOVEMENT_SAMPLE_GAP = 0.35  # seconds between those two samples

_BLACKLISTED_APPS = {
    "teams", "zoom", "discord", "slack", "skype", "obs",
    "mpc-hc", "vlc", "wmplayer", "riot", "douyin", "telegram", "messenger"
}

_MUSIC_APP_ALLOWLIST = {
    "spotify", "tidal", "applemusic", "musicbee", "foobar", "aimp",
    "winamp", "mediamonkey", "amazon music", "deezer", "soundcloud", "ytmusic",
}

_BROWSER_APPS = {"chrome", "msedge", "firefox", "opera", "brave", "vivaldi"}

_JUNK_ARTISTS = {
    "youtube", "unknown", "chrome", "microsoft edge", "firefox",
    "opera", "brave", "vivaldi", "windows",
}

_VIDEO_TITLE_PATTERNS = [
    "episode", "full hd", "live stream", "breaking news", "tutorial",
    "reaction", "vlog", "part ", "ep.", " - youtube", " | youtube",
    " s0", " e0", " season ", "review", "how to", "full movie", "gameplay",
    "直播", "實況", "恐怖", "新聞", "攻略", "教學", "完整版",
]


def _is_browser(app_id):
    return any(b in app_id for b in _BROWSER_APPS)


def _is_blacklisted(app_id):
    return any(b in app_id for b in _BLACKLISTED_APPS)


def _is_music_app(app_id):
    return any(m in app_id for m in _MUSIC_APP_ALLOWLIST)


def _looks_like_video_title(title):
    low = (title or "").lower()
    return any(p in low for p in _VIDEO_TITLE_PATTERNS)


def _get_position(session):
    """Read a session's current position in seconds, or 0.0 if unreadable."""
    try:
        return session.get_timeline_properties().position.total_seconds()
    except Exception:
        return 0.0


async def _detect_moving_sessions(sessions):
    """Sample every session's position twice with a short gap; a session
    whose position advances by more than the threshold is actively playing
    right now - a strong "this one is real" signal."""
    first = [_get_position(s) for s in sessions]
    await asyncio.sleep(_MOVEMENT_SAMPLE_GAP)
    second = [_get_position(s) for s in sessions]
    return {i for i, (a, b) in enumerate(zip(first, second)) if abs(b - a) >= _POSITION_DELTA_THRESHOLD}


async def _score_session(session, position_moving):
    """Score one session on cheap metadata signals only - no lyrics probing here."""
    app_id = (session.source_app_user_model_id or "").lower()
    try:
        info = await session.try_get_media_properties_async()
    except Exception:
        return -1000, "Undetected Song", "Unknown Artist", app_id  # unreadable - sink to the bottom

    title = info.title or "Undetected Song"
    artist = (info.artist or "").strip()

    score = 0
    reasons = []

    if artist:
        score += 40
        reasons.append("+40 artist present")
        if artist.lower() in _JUNK_ARTISTS:
            score -= 30
            reasons.append(f"-30 junk artist '{artist}'")

    if info.album_title and info.album_title.strip():
        score += 20
        reasons.append("+20 album present")

    has_thumbnail = False
    try:
        has_thumbnail = bool(info.thumbnail)
    except Exception:
        pass
    if has_thumbnail:
        score += 20
        reasons.append("+20 thumbnail present")

    if position_moving:
        score += 30
        reasons.append("+30 position moving")

    if _is_music_app(app_id):
        score += 60
        reasons.append("+60 known music app")

    if _is_browser(app_id):
        score -= 25
        reasons.append("-25 browser")
        if artist and artist.lower() not in _JUNK_ARTISTS:
            score += 20
            reasons.append("+20 browser has real artist")
        if has_thumbnail:
            score += 15
            reasons.append("+15 browser has thumbnail")
        if info.album_title and info.album_title.strip():
            score += 15
            reasons.append("+15 browser has album")

    if _looks_like_video_title(title):
        score -= 50
        reasons.append("-50 title looks like a video, not a song")

    if _is_blacklisted(app_id):
        score -= 100
        reasons.append("-100 blacklisted app")

    print(f"[Selector] '{title}' by '{artist or 'Unknown Artist'}' ({app_id or 'unknown app'}) -> score {score} [{', '.join(reasons)}]")
    return score, title, artist or "Unknown Artist", app_id


async def _rank_sessions(sessions):
    """Score every session and return (score, title, artist, app_id, session) tuples, best-first."""
    moving = await _detect_moving_sessions(sessions)
    ranked = []
    for i, session in enumerate(sessions):
        score, title, artist, app_id = await _score_session(session, i in moving)
        ranked.append((score, title, artist, app_id, session))

    # Prefer shorter titles
    if ranked:
        max_len = max(len(row[1]) for row in ranked)
        for i, row in enumerate(ranked):
            score, title, artist, app_id, session = row
            bonus = max(0, max_len - len(title))
            if bonus:
                ranked[i] = (score + bonus, title, artist, app_id, session)

    ranked.sort(key=lambda row: row[0], reverse=True)
    return ranked


def _find_session_with_lyrics(ranked_sessions):
    """
    Walk the ranked sessions best-first, actually searching for lyrics for
    each in turn. The first one with lyrics wins. Falls back to the
    top-scored candidate (with lyrics=None) if nobody has any.

    NOTE: does blocking network I/O (lyrics_fetcher) - call from a
    background thread, not the UI's main thread.
    """
    for score, title, artist, app_id, session in ranked_sessions:
        if title == "Undetected Song" or artist == "Unknown Artist":
            continue  # nothing meaningful to search for
        print(f"[Selector] Trying lyrics search for top candidate '{title}' by '{artist}' (score {score})")
        lyrics = lyrics_fetcher(title, artist)
        if lyrics:
            print(f"[Selector] Lyrics found for '{title}' - selecting this session")
            return session, title, artist, lyrics
        print(f"[Selector] No lyrics for '{title}' by '{artist}', trying next candidate")

    if ranked_sessions:
        score, title, artist, app_id, session = ranked_sessions[0]
        print(f"[Selector] No candidate had lyrics; defaulting to top-scored '{title}'")
        return session, title, artist, None

    return None, "Undetected Song", "Unknown Artist", None


class MediaSelector:
    """
    Tracks the currently selected session across polls so scoring (and the
    lyrics search it triggers) only runs when actually needed:
      - the set of active sessions changes (a session appeared/disappeared)
      - the currently selected session's song changes
    Otherwise the previous selection is reused as-is - cheap and instant.
    """

    def __init__(self):
        self._last_signature = None  # sorted tuple of active app_ids, last poll
        self._selected_app_id = None
        self._last_title = None
        self._last_artist = None
        self.lyrics = None  # lyrics for the currently selected song, if any were found

    async def select(self):
        """
        Return (session, title, artist, lyrics) for the currently best
        media session. session is a winsdk session object, or None if no
        media is active at all.
        """
        manager = await MediaManager.request_async()
        sessions = manager.get_sessions()

        if not sessions:
            self._reset()
            return None, "Undetected Song", "Unknown Artist", None

        signature = tuple(sorted((s.source_app_user_model_id or "") for s in sessions))

        if len(sessions) == 1:
            # Nothing to choose between - use it directly, no scoring needed.
            session = sessions[0]
            title, artist = await self._read_title_artist(session)
            if (title, artist) != (self._last_title, self._last_artist):
                self.lyrics = None  # song changed - drop any lyrics cached for the previous one
            self._last_title, self._last_artist = title, artist
            self._selected_app_id = signature[0] if signature else None
            self._last_signature = signature
            return session, title, artist, self.lyrics

        # Multiple sessions: reuse the existing pick if the session set is
        # unchanged AND the selected session's song hasn't changed.
        if signature == self._last_signature:
            current = self._find_by_app_id(sessions, self._selected_app_id)
            if current is not None:
                title, artist = await self._read_title_artist(current)
                if (title, artist) == (self._last_title, self._last_artist):
                    return current, title, artist, self.lyrics
                print(f"[Selector] Song changed on the selected session ('{title}' by '{artist}') - rescoring")
        else:
            print(f"[Selector] {len(sessions)} media sessions detected - scoring to pick the right one")

        ranked = await _rank_sessions(sessions)
        session, title, artist, lyrics = _find_session_with_lyrics(ranked)

        self._selected_app_id = (session.source_app_user_model_id or "") if session else None
        self._last_title = title
        self._last_artist = artist
        self._last_signature = signature
        self.lyrics = lyrics
        return session, title, artist, lyrics

    def _reset(self):
        self._last_signature = None
        self._selected_app_id = None
        self._last_title = None
        self._last_artist = None
        self.lyrics = None

    async def _read_title_artist(self, session):
        try:
            info = await session.try_get_media_properties_async()
            return (info.title or "Undetected Song"), (info.artist or "Unknown Artist")
        except Exception:
            return "Undetected Song", "Unknown Artist"

    def _find_by_app_id(self, sessions, app_id):
        if not app_id:
            return None
        for s in sessions:
            if (s.source_app_user_model_id or "") == app_id:
                return s
        return None


_selector = MediaSelector()


async def select_best_media():
    """
    Convenience wrapper around a shared MediaSelector instance.

    Returns (session, title, artist, lyrics). Re-scoring and the lyrics
    search only happen on multi-session detection or a song change on the
    selected session - see MediaSelector.

    NOTE: this can do blocking network I/O (a real lyrics search) when
    rescoring triggers, so call it from a background thread rather than
    directly on the UI's main thread/event loop.
    """
    return await _selector.select()