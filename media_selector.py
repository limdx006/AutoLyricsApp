import re
import time

from winsdk.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager as MediaManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)

# Toggle to print a scoring breakdown whenever a re-score actually runs
DEBUG_MEDIA_SELECTOR = False

"""MEDIA SELECTOR - Scores all active Windows media sessions and returns the one
most likely to be music. This replaces the naive get_current_session() approach,
which blindly returns whatever Windows considers 'active' — often a browser tab
playing a video instead of the intended music source.

Each session is scored by multiple independent signals. The session with the
highest score wins. If all sessions score below -50, None is returned.

Re-scoring is lazy: a full poll only runs when something meaningful changes
(new song detected, lyrics probe result arrives, or RESCORE_INTERVAL seconds have
passed). Between those events the previous winner is returned instantly, so the
0.5 s sync_song loop has virtually no overhead from this module.

Set DEBUG_MEDIA_SELECTOR = True to print a per-session scoring breakdown to the
terminal every time a real re-score happens. Useful for tuning weights."""

# Full re-score runs at most once per this many seconds even if nothing changed
RESCORE_INTERVAL = 10.0

# How many seconds a position must advance between polls to count as "moving"
_POSITION_DELTA_THRESHOLD = 0.3

# Bonus / penalty applied based on the lyrics probe result
_LYRICS_FOUND_BONUS = 60
_LYRICS_MISSING_PENALTY = 40

_BLACKLISTED_APPS = {
    "teams",
    "zoom",
    "discord",
    "slack",
    "skype",
    "obs",
    "mpc-hc",
    "vlc",
    "wmplayer",
}

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

_BROWSER_APPS = {"chrome", "msedge", "firefox", "opera", "brave", "vivaldi"}

_JUNK_ARTISTS = {
    "youtube",
    "unknown",
    "chrome",
    "microsoft edge",
    "firefox",
    "opera",
    "brave",
    "vivaldi",
    "windows",
}

_VIDEO_TITLE_PATTERNS = [
    "episode",
    "full hd",
    "live stream",
    "breaking news",
    "tutorial",
    "reaction",
    "vlog",
    "part ",
    "ep.",
    " - youtube",
    " | youtube",
    " s0",
    " e0",
    " season ",
    "review",
    "how to",
    "full movie",
    "gameplay",
    "直播",
    "實況",
    "恐怖",
    "新聞",
    "攻略",
    "教學",
    "完整版",
]


def _is_browser(app_id: str) -> bool:
    low = app_id.lower()
    return any(b in low for b in _BROWSER_APPS)


def _is_blacklisted(app_id: str) -> bool:
    low = app_id.lower()
    return any(b in low for b in _BLACKLISTED_APPS)


def _is_music_app(app_id: str) -> bool:
    low = app_id.lower()
    return any(m in low for m in _MUSIC_APP_ALLOWLIST)


def _title_music_likelihood(title: str) -> tuple[int, list[str]]:
    """Score the title string for music-likeness.

    Returns (score_delta, debug_reasons).
    """
    if not title:
        return -50, ["-50 no title"]

    reasons = []
    delta = 0
    low = title.lower()

    for pattern in _VIDEO_TITLE_PATTERNS:
        if pattern in low:
            delta -= 30
            reasons.append(f"-30 title pattern '{pattern}'")
            break  # one penalty per title is enough

    if re.search(r"[!?]{2,}", title):
        delta -= 15
        reasons.append("-15 excessive punctuation")

    if len(title) > 60:
        delta -= 30
        reasons.append(f"-30 long title ({len(title)} chars)")

    return delta, reasons


def _score_session(
    app_id: str,
    info,
    playback_info,
    position_moving: bool,
) -> tuple[int, list[str]]:
    """Compute a confidence score for one session.

    Returns (score, debug_lines).
    """
    score = 0
    reasons = []
    status = playback_info.playback_status

    if status == PlaybackStatus.PLAYING:
        score += 100
        reasons.append("+100 playing")
    elif status == PlaybackStatus.PAUSED:
        score += 20
        reasons.append("+20 paused")

    artist = (info.artist or "").strip()
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

    title_delta, title_reasons = _title_music_likelihood(info.title)
    score += title_delta
    reasons.extend(title_reasons)

    # Lyrics availability — probe result from the background cache
    lyrics_delta, lyrics_reasons = _lyrics_score(info.title or "", artist)
    score += lyrics_delta
    reasons.extend(lyrics_reasons)

    if _is_blacklisted(app_id):
        score -= 100
        reasons.append("-100 blacklisted app")

    return score, reasons


# Keyed by session object identity so each browser tab gets its own slot
_last_positions: dict[int, tuple[float, float]] = {}


def _check_position_moving(session_key: int, current_pos: float) -> bool:
    """Return True if this session's playback position has advanced since the last check."""
    now = time.monotonic()
    if session_key in _last_positions:
        prev_pos, prev_time = _last_positions[session_key]
        if now - prev_time >= 0.4:
            moving = (current_pos - prev_pos) >= _POSITION_DELTA_THRESHOLD
            _last_positions[session_key] = (current_pos, now)
            return moving
    else:
        _last_positions[session_key] = (current_pos, now)
    return False


"""LYRICS PROBE CACHE
Maps (title, artist) -> True / False / None.
  True  = lyrics found    → score bonus applied immediately next re-score
  False = no lyrics found → score penalty applied
  None  = probe not yet completed (neutral — no effect until result arrives)

The probe runs once per unique (title, artist) pair as a background task so it
never blocks the poll loop. When a result arrives it marks the selector dirty,
forcing a re-score on the next get_best_session() call so the new bonus/penalty
is applied without waiting up to RESCORE_INTERVAL seconds."""

_lyrics_probe_cache: dict[tuple[str, str], bool | None] = {}
_lyrics_probe_inflight: set[tuple[str, str]] = set()


def _lyrics_score(title: str, artist: str) -> tuple[int, list[str]]:
    """Return the score contribution from the lyrics probe cache."""
    key = (title.strip(), artist.strip())
    result = _lyrics_probe_cache.get(key)
    if result is True:
        return _LYRICS_FOUND_BONUS, [f"+{_LYRICS_FOUND_BONUS} lyrics found"]
    if result is False:
        return -_LYRICS_MISSING_PENALTY, [f"-{_LYRICS_MISSING_PENALTY} no lyrics found"]
    return 0, []  # probe still in-flight or not yet scheduled


async def _run_lyrics_probe(key: tuple[str, str]) -> None:
    """Background task: search for lyrics and write the result into the cache."""
    import asyncio
    import syncedlyrics

    title, artist = key
    query = f"{title} {artist}".strip()

    def _fetch():
        try:
            return syncedlyrics.search(query)
        except Exception:
            return None

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _fetch)

    _lyrics_probe_cache[key] = result is not None
    _lyrics_probe_inflight.discard(key)

    # Mark the selector dirty so the next call re-scores with the new info
    _mark_dirty()

    if DEBUG_MEDIA_SELECTOR:
        found = _lyrics_probe_cache[key]
        print(
            f"[MediaSelector] lyrics probe '{query}' -> {'found' if found else 'not found'} — re-score triggered"
        )


def _schedule_lyrics_probe(title: str, artist: str) -> None:
    """Fire a one-shot background lyrics probe if this pair has not been tried yet."""
    import asyncio

    key = (title.strip(), artist.strip())
    if key in _lyrics_probe_cache or key in _lyrics_probe_inflight:
        return

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return

    _lyrics_probe_inflight.add(key)
    loop.create_task(_run_lyrics_probe(key))


"""LAZY RE-SCORE STATE
A full poll across all sessions is expensive (async WinRT calls per session).
We skip it when nothing relevant has changed, returning the cached winner instead.

_dirty is set to True whenever something that could change the outcome occurs:
  - a lyrics probe result arrives
  - RESCORE_INTERVAL seconds have elapsed (catches slow changes like position moving)
  - the caller signals that the active song changed (via invalidate())

get_best_session() clears _dirty after each real poll."""

_dirty: bool = True
_last_rescore_time: float = 0.0
_cached_winner: tuple = (None, None, 0)  # (session, info, score)


def _mark_dirty() -> None:
    global _dirty
    _dirty = True


def invalidate() -> None:
    """Call this whenever the active song changes so the next poll forces a re-score."""
    _mark_dirty()


async def get_best_session():
    """Return the best media session, re-scoring only when something has changed.

    Returns (session, info, score), or (None, None, 0) if nothing qualifies.
    """
    global _dirty, _last_rescore_time, _cached_winner

    now = time.monotonic()
    interval_expired = (now - _last_rescore_time) >= RESCORE_INTERVAL

    if not _dirty and not interval_expired:
        return _cached_winner

    # --- Full re-score ---
    try:
        manager = await MediaManager.request_async()
    except Exception:
        return None, None, 0

    sessions = manager.get_sessions()
    if not sessions:
        _cached_winner = (None, None, 0)
        _dirty = False
        _last_rescore_time = now
        return _cached_winner

    best_session = None
    best_info = None
    best_score = -9999

    if DEBUG_MEDIA_SELECTOR:
        print("\n[MediaSelector] --- re-score ---")

    for session in sessions:
        try:
            app_id = session.source_app_user_model_id or "unknown"
            info = await session.try_get_media_properties_async()
            playback_info = session.get_playback_info()
            timeline = session.get_timeline_properties()
            current_pos = timeline.position.total_seconds()

            session_key = id(session)
            position_moving = _check_position_moving(session_key, current_pos)

            # Schedule a lyrics probe for this session (no-op if already done)
            _schedule_lyrics_probe(info.title or "", (info.artist or "").strip())

            score, reasons = _score_session(
                app_id, info, playback_info, position_moving
            )

            if DEBUG_MEDIA_SELECTOR:
                label = f"{app_id[:40]}  |  '{(info.title or '')[:40]}'"
                print(f"  {label}")
                print(f"    total: {score}")
                for r in reasons:
                    print(f"      {r}")

            if score > best_score:
                best_score = score
                best_session = session
                best_info = info

        except Exception:
            continue

    if DEBUG_MEDIA_SELECTOR:
        winner_id = (
            (best_session.source_app_user_model_id or "none")
            if best_session
            else "none"
        )
        print(f"  => winner: {winner_id}  score: {best_score}\n")

    if best_score < -50:
        _cached_winner = (None, None, 0)
    else:
        _cached_winner = (best_session, best_info, best_score)

    _dirty = False
    _last_rescore_time = now
    return _cached_winner
