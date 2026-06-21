"""Constants for the FireLabs integration."""

from datetime import timedelta

DOMAIN = "firelabs"
MANUFACTURER = "FireLabs"
DEFAULT_SCAN_INTERVAL = 5  # seconds
HTTP_TIMEOUT = 8  # seconds

# Firmware updates. The device reports its running version as `fw` in
# /api/status; the latest release is read from the model's GitHub repo, and
# install pushes the release .bin to the device's existing /update endpoint.
GITHUB_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
FIRMWARE_REPOS: dict[str, str] = {
    "S31": "FireLabsCA/firelabs-s31-firmware",
    "WX": "FireLabsCA/firelabs-weather-display",
}
RELEASE_TTL = 6 * 3600  # seconds; GitHub unauthenticated is 60 req/hr/IP
LATEST_POLL_INTERVAL = timedelta(hours=6)
OTA_DOWNLOAD_TIMEOUT = 60  # seconds to pull the .bin from GitHub
OTA_UPLOAD_TIMEOUT = 120  # seconds to upload + flash on the device
RELEASES_KEY = "firelabs_releases"  # shared release cache in hass.data
