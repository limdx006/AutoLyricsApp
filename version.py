"""
App version and GitHub release metadata, used by update_checker.py.
"""

APP_VERSION = "4.0.1"

GITHUB_OWNER = "limdx006"
GITHUB_REPO = "AutoLyricsApp"
GITHUB_API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"

# Every release is expected to publish its built exe under this exact
# asset name, so it can be found without parsing a versioned filename.
RELEASE_ASSET_NAME = "LyricsPlayer.exe"