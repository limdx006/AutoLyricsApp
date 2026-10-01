"""
Downloads a new release exe and replaces the currently running one.

Windows won't let a running process overwrite (or delete) its own .exe,
so the actual swap is done by a small generated batch script that:
  1. waits a moment for this process to fully exit (file lock to clear)
  2. replaces the old exe with the downloaded one, retrying a few times
     in case something (antivirus, Explorer) still has it briefly open
  3. relaunches it
  4. deletes itself

This only applies to a frozen (PyInstaller) build - see is_frozen().
Running from source has no exe to replace, so callers should fall back
to just pointing the user at the release page instead.
"""

import os
import sys
import subprocess
import tempfile

_DOWNLOAD_TIMEOUT = 30
_CHUNK_SIZE = 256 * 1024  # 256 KB

_SWAP_SCRIPT_TEMPLATE = """@echo off
ping 127.0.0.1 -n 3 >nul
set "NEW={new_exe}"
set "TARGET={target_exe}"
set "RETRIES=10"

:retry_move
move /y "%NEW%" "%TARGET%" >nul 2>&1
if exist "%NEW%" (
    set /a RETRIES-=1
    if %RETRIES% gtr 0 (
        ping 127.0.0.1 -n 2 >nul
        goto retry_move
    )
    exit /b 1
)

del "%~f0"
"""


def is_frozen():
    """True when running as a built --onefile exe, not `python main.py`."""
    return getattr(sys, "frozen", False)


def current_exe_path():
    """Full path to the running exe. Only meaningful when is_frozen()."""
    return sys.executable


def can_write_target():
    """Whether the exe's own folder is writable by this user - needed for
    the swap to succeed. False e.g. if installed under Program Files
    without elevation; caller should block the update flow and say so
    rather than downloading and then failing to swap."""
    target_dir = os.path.dirname(current_exe_path())
    return os.access(target_dir, os.W_OK)


def download_update(url, progress_callback=None):
    """
    Download `url` to a temp file and return its path.

    progress_callback(downloaded_bytes, total_bytes_or_None) is called as
    data arrives if provided; total is None when the server doesn't send
    Content-Length. Raises on any failure (unlike this app's other
    background checkers, a failed download needs to visibly stop the
    update flow rather than being swallowed).
    """
    import requests  # local import: only needed on this path

    response = requests.get(url, stream=True, timeout=_DOWNLOAD_TIMEOUT)
    response.raise_for_status()

    total = response.headers.get("Content-Length")
    total = int(total) if total and total.isdigit() else None

    fd, temp_path = tempfile.mkstemp(prefix="LyricsPlayer_update_", suffix=".exe")
    downloaded = 0
    try:
        with os.fdopen(fd, "wb") as f:
            for chunk in response.iter_content(chunk_size=_CHUNK_SIZE):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)
    except Exception:
        _try_remove(temp_path)
        raise

    if downloaded == 0:
        _try_remove(temp_path)
        raise RuntimeError("Downloaded file is empty")

    return temp_path


def apply_update(new_exe_path):
    """
    Launch the swap script (detached, survives this process exiting) and
    return. The caller should close the app shortly after this returns,
    so the exe's file lock releases and the swap can succeed.
    """
    if os.name != "nt":
        raise RuntimeError("Self-update is only supported on Windows")

    target = current_exe_path()
    script_path = os.path.join(tempfile.gettempdir(), "LyricsPlayer_update.bat")
    script = _SWAP_SCRIPT_TEMPLATE.format(new_exe=new_exe_path, target_exe=target)
    with open(script_path, "w") as f:
        f.write(script)

    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
        ["cmd.exe", "/c", script_path],
        creationflags=CREATE_NO_WINDOW,
    )


def _try_remove(path):
    try:
        os.remove(path)
    except OSError:
        pass